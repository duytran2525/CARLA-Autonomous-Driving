"""M56 A-SEL2 F PREPARATION (PREREG_M56_F_ASEL2_20261109.md part 1; PLAN_M56_F_NATIVE_TOOLING_20261109.md). Preparation
only: no A/B, no F event can fire (probe fixtures carry no F domain and no metric pair). Mechanism F01 first.

Per F01 scene, on Claude's own server (2610), on the candidate's R1 site lane (road / section / lane):
  1. lane-centre rows (CARLA waypoints): EGO from the section entry + 1 m, NPC on the same lane ahead (first guess:
     front gap G0 = 40 m), both through the section exit;
  2. probe 1: EGO NOMINAL 4 m/s, NPC NOMINAL vN_char (prereg: 17/5) from rest; ready time = the later of the two steady
     times (1 s within 0.05 m/s); gap(T) = NPC rear station - EGO front station along the EGO route;
  3. NPC start shifted along its lane so that gap(T) = d0 (prereg: 11.4 m) (same lane, flat straight: NPC kinematics do not
     depend on its start);
  4. probe 2 -> targets, readiness markers (runner predicate), realised d0 at readiness;
  5. sections (route stations, PREREG F part 1 / PLAN): F01_BRAKE_START on the NPC route = NPC front at ready + 3 s * vN;
     F01_END = F01_BRAKE_START + 20 m; EGO DESTINATION = EGO station of F01_END + body + 10 m. Blocked if the lane ends.
Writes outputs/m56_v2_prepare_<town>_<stamp>/<scene>/prepare.json (+ routes-f.json).
  python -I native-f-prepare.py Town06 M56-P-F01"""
import importlib.util, json, math, sys, traceback
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

here = Path(__file__).resolve().parent
TOWN, SCENES = sys.argv[1], sys.argv[2].split(',')
sys.argv = [str(here / 'native-v2-prepare.py'), TOWN]
_spec = importlib.util.spec_from_file_location('v2prep', here / 'native-v2-prepare.py')
P = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(P)  # shared root, authority, probe machinery

from native_v2_common import NO_RENDER, V6, REV, arcs, body_record, directed, load, own_server, ownership, write_ref, stream_to  # noqa: E402
from m56 import runtime  # noqa: E402
from m56.catalog import _digest  # noqa: E402
from m56.metrics import _metric_station, _speed  # noqa: E402
from m56.model import FrozenResponse, decode_record, encode_record, load_json  # noqa: E402

log = P.log


class IO:
    """lane_rows / pose_on / rear_station as in native-io-prepare.py (copied: importing that module would re-run the
    native-v2-prepare module code and its create-exclusive output root)."""
    grounds = {}

    @staticmethod
    def lane_rows(m, road, lane, s_from, s_to):
        from native_v2_common import _step, _wp_row
        w = m.get_waypoint_xodr(road, lane, s_from)
        assert w is not None, f'NO_WAYPOINT:{road}/{lane}@{s_from}'
        rows, sign = [_wp_row(w)], (1 if lane < 0 else -1)
        while (s_to - w.s) * sign > 0:
            nxt = [p for p in _step(w, True) if p.road_id == road and p.lane_id == lane]
            assert nxt, f'LANE_ENDS:{road}/{lane}@{w.s:.2f}'
            w = nxt[0]; rows.append(_wp_row(w))
        return rows

    @staticmethod
    def pose_on(world, rows, i):
        import carla
        from m56.model import Transform6
        from m56.response import _f32
        from native_v2_common import SPAWN_TILT, spawn_tilt
        a, b = rows[i], rows[i + 1]
        L = math.dist((a['x'], a['y']), (b['x'], b['y'])); along = .02
        t = Transform6(a['x'] + (b['x'] - a['x']) * along / L, a['y'] + (b['y'] - a['y']) * along / L, a['z'], 0., a['yaw'], 0.)
        g = world.ground_projection(carla.Location(t.x, t.y, t.z + 2.), 10.)
        z = (g.location.z if g is not None else t.z) + .01
        IO.grounds[id(rows)] = None if g is None else g.location.z
        pr = spawn_tilt(world.get_map(), t.x, t.y, z) if SPAWN_TILT else (0., 0.)
        return Transform6(_f32(t.x), _f32(t.y), _f32(z), _f32(pr[0]), _f32(t.yaw), _f32(pr[1]))

    @staticmethod
    def rear_station(actor, route):
        from m56.geometry import project_route, world_vertices
        s = [project_route(p, route) for p in world_vertices(actor.body, actor.pose)]
        s = [float(x) for x in s if not hasattr(x, 'reasons')]
        return min(s) if s else None
INPUTS = {'F01': {'vE': F(4), 'vN_char': F(17, 5), 'd0': F(57, 5)},   # PREREG F part 1 section 1
          'F02': {'vE': F(4), 'vN_char': F(5), 'd0': F(20)}}         # + F02_RECIPE_NOTES_20261109
G0, TAIL_M = 40., 30.
ZERO = {'method': 'quintic-arc-v1', 'segments': ({'start_arc_m': F(0), 'length_m': F(1), 'start_offset_m': F(0), 'end_offset_m': F(0)},)}


def nominal_response(role, action, v, route):
    """Probe-only program: SETTLE 0, NOMINAL v after CAPTURE_START (+ the runner release), nothing else."""
    from native_v2_common import RELEASE
    program = {'method': 'ordered-event-program-v1', 'initial': 'SETTLE',
               'transitions': ({'cause': 'NOMINAL', 'after_event': 'CAPTURE_START', 'delay_s': RELEASE, 'requires': ()},)}
    r = FrozenResponse(role, action, route, {'SETTLE': F(0), 'NOMINAL': v}, ZERO,
                       {'category': 'F', 'program': program, 'annex': 'F preparation probe, never catalog'}, '')
    return replace(r, hash=_digest({k: getattr(r, k) for k in ('actor_role', 'action_id', 'route', 'targets', 'profile', 'phases')}))


def candidates_f(ids):
    out = []
    for item in load_json(REV)['candidates']:
        if item['id'] in ids:
            c = decode_record('Candidate', item)
            assert not hasattr(c, 'errors'), (item['id'], c)
            out.append(c)
    return out


def prepare_f(c, client, proc, start, world, m, identity, body, bbox):
    mech = (c.environment.get('mechanism') or c.slot).replace('-ALT1', '')
    assert mech in INPUTS, f'F_MECHANISM_NOT_IN_PART1:{mech}'
    inp = INPUTS[mech]; L = 2 * bbox['extent'][0]
    rr = c.actors[0].route_recipe; road = int(rr['road']); lane = int(rr['lanes'][0] if isinstance(rr['lanes'], (list, tuple)) else rr['lanes'])
    sg = 1 if lane < 0 else -1
    import xodr_routes as xr
    secs = xr.roads(c.town)[road].find('lanes').findall('laneSection')
    lo = float(secs[rr['section']].get('s')); hi = float(secs[rr['section'] + 1].get('s')) if rr['section'] + 1 < len(secs) else xr.length(c.town, road)
    entry, exit_ = (lo + 1., hi - 1.) if sg > 0 else (hi - 1., lo + 1.)
    (P.root / c.id).mkdir(parents=False, exist_ok=True)
    out = {'scene': c.id, 'town': c.town, 'category': 'F', 'mechanism': mech, 'recipe': 'f-v1', 'inputs': inp, 'bbox': bbox,
           'site': {'road': road, 'lane': lane, 'section': rr['section'], 'entry_s': entry, 'exit_s': exit_},
           'map_hash': identity.map, 'carla_no_rendering_mode': NO_RENDER, **({'m56_recipe': 'v6'} if V6 else {})}
    rows = {'EGO': IO.lane_rows(m, road, lane, entry, exit_)}
    rows['NPC'] = list(rows['EGO'])
    arc = {k: arcs(v) for k, v in rows.items()}
    cont = write_ref(P.root / c.id / 'routes-f-probe1.json', rows, 'NATIVE_ROUTE')
    note = f'{road}/{lane}'
    # F01: the NPC leads (its route is cut at its start). F02 (F02 recipe notes 1): the EGO leads; both share the whole
    # lane route (the rear-gap metric projects the NPC onto the EGO route) and the EGO spawns at its start station.
    lead, follow = ('NPC', 'EGO') if mech == 'F01' else ('EGO', 'NPC')

    def routes_for(lead_station):
        k = next(i for i, a in enumerate(arc[lead]) if float(a) >= lead_station)
        if mech == 'F01':
            nr, na = rows['NPC'][k:], [a - arc['NPC'][k] for a in arc['NPC'][k:]]
        else:
            nr, na = rows['NPC'], arc['NPC']
        r = {'EGO': directed(rows['EGO'], arc['EGO'], identity.map, c.town, note, cont, arc['EGO'][-1] - 5),
             'NPC': directed(nr, na, identity.map, c.town, note, cont, na[-1] - 5)}
        return r, {'EGO': (rows['EGO'], arc['EGO']), 'NPC': (nr, na)}, k

    def poses_for(prow, k):
        if mech == 'F01':
            return {'EGO': IO.pose_on(world, rows['EGO'], 0), 'NPC': IO.pose_on(world, prow['NPC'][0], 0)}
        return {'EGO': IO.pose_on(world, rows['EGO'], k), 'NPC': IO.pose_on(world, rows['NPC'], 0)}
    first = float(G0 + L)  # lead origin station on the follower route (front gap G0)
    routes, prow, k1 = routes_for(first)
    poses = poses_for(prow, k1)
    mid = rows['EGO'][len(rows['EGO']) // 2]
    stream_to(world, mid['x'], mid['y'], mid['z'])

    def run(label, rts, pr, ps):
        resp = (nominal_response('EGO', 'A', inp['vE'], rts['EGO']), nominal_response('NPC', 'NPC_COMMON', inp['vN_char'], rts['NPC']))
        return P.probe(client, proc, start, world, identity, c.id, rts, pr, ps, resp, label, None, None, None)
    p1 = run('probe1', routes, prow, poses)
    if not p1:
        out.update(status='BLOCKED_FIXTURE', reason='PROBE1_NO_FRAMES:' + ','.join(P.LAST_REASONS)); return P.finish(c, out)
    tE = P.steady_time(p1, 'EGO', inp['vE']); tN = P.steady_time(p1, 'NPC', inp['vN_char'])
    out.update(probe1_steady_s={'EGO': tE and float(tE), 'NPC': tN and float(tN)})
    if tE is None or tN is None:
        out.update(status='BLOCKED_FIXTURE', reason='PROBE1_NOT_STEADY'); return P.finish(c, out)
    T = max(tE, tN)
    fr = next(f for f in p1 if f.simtime >= T)
    act = {a.role: a for a in fr.actors}
    gap = IO.rear_station(act[lead], routes[follow]) - P.front_station(act[follow], routes[follow])
    # F02 recipe notes 2: gap at readiness d0 + (vN - vE) * 1 s, so TRIGGER (gap 20 m) comes 1 s after readiness
    target = float(inp['d0']) + (float(inp['vN_char'] - inp['vE']) if mech == 'F02' else 0.)
    shift = target - gap
    out.update(probe1_gap_at_ready_m=gap, lead_shift_m=shift, target_gap_at_ready_m=target, lead=lead)
    routes2, prow2, k2 = routes_for(first + shift)
    poses2 = poses_for(prow2, k2)
    p2 = run('probe2', routes2, prow2, poses2)
    if not p2:
        out.update(status='BLOCKED_FIXTURE', reason='PROBE2_NO_FRAMES:' + ','.join(P.LAST_REASONS)); return P.finish(c, out)
    targets = {'EGO': inp['vE'], 'NPC': inp['vN_char']}
    ready = P.first_ready(p2, routes2, targets, boundary_t2=float(p2[0].simtime) - .05)
    if ready is None:
        out.update(status='BLOCKED_FIXTURE', reason='READINESS_NOT_REACHED_IN_PROBE2'); return P.finish(c, out)
    frr, markers = ready
    act = {a.role: a for a in frr.actors}; ego, npc = act['EGO'], act['NPC']
    d0r = IO.rear_station(act[lead], routes2[follow]) - P.front_station(act[follow], routes2[follow])
    ego_front = P.front_station(ego, routes2['EGO'])
    extra = {}
    if mech == 'F01':
        npc_front = P.front_station(npc, routes2['NPC'])
        brake = npc_front + 3 * float(inp['vN_char']); end = brake + 20.
        ego_end = ego_front + (end - npc_front) + d0r + L + 10.
        sections = {'F01_BRAKE_START': {'route': 'NPC', 'station': brake}, 'F01_END': {'route': 'NPC', 'station': end},
                    'DESTINATION': {'route': 'EGO', 'station': ego_end}}
        npc_need = end + TAIL_M
    else:  # F02 recipe notes 3: nominal EGO front at TRIGGER; F02_END = front + 60 (metrics.py); DESTINATION = F02_END + 5
        t_trig = (d0r - 20.) / float(inp['vN_char'] - inp['vE'])
        front_t0 = ego_front + float(inp['vE']) * max(t_trig, 0.)
        end = front_t0 + 60.; ego_end = end + 5.
        sections = {'F02_END': {'route': 'EGO', 'station': end}, 'DESTINATION': {'route': 'EGO', 'station': ego_end}}
        extra = {'nominal_front_t0_m': front_t0, 'nominal_trigger_after_ready_s': t_trig}
        npc_need = 0.
    if npc_need > float(routes2['NPC'].arc[-1]) or ego_end + 15. > float(routes2['EGO'].arc[-1]):
        out.update(status='BLOCKED_FIXTURE', reason='F_WINDOW_TOO_SHORT', need_ego_m=ego_end + 15., have_ego_m=float(routes2['EGO'].arc[-1]))
        return P.finish(c, out)
    npc_rows = prow2['NPC'][0]
    cont2 = write_ref(P.root / c.id / 'routes-f.json', {'EGO': rows['EGO'], 'NPC': npc_rows}, 'NATIVE_ROUTE')
    out.update(status='PREPARED', reason=None, targets=targets, markers=markers, T_r=float(frr.simtime) - float(p2[0].simtime),
               d0_realised_m=d0r, lead_route_start_index=k2, routes_f=str(cont2.uri), routes_f_sha256=cont2.sha256,
               poses={k: encode_record(v) for k, v in poses2.items()},
               grounds={'EGO': IO.grounds.get(id(rows['EGO'])), 'NPC': IO.grounds.get(id(npc_rows))},
               sections_m=sections, **extra)
    return P.finish(c, out)


def main():
    scenes = candidates_f(SCENES)
    log(event='SCENES', town=TOWN, ids=[c.id for c in scenes])
    with own_server(log) as (client, proc, start):
        world = load(client, TOWN); m = world.get_map()
        identity = runtime.ReadOnlyCarlaBackend(client, ownership(proc, start, world)).identity()
        s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = True, .05; world.apply_settings(s)
        _sp0 = m.get_spawn_points()[0].location; stream_to(world, _sp0.x, _sp0.y, _sp0.z)
        car = world.spawn_actor(world.get_blueprint_library().find('vehicle.audi.a2'), m.get_spawn_points()[0]); world.tick()
        b = car.bounding_box
        assert min(b.extent.x, b.extent.y, b.extent.z) > 0, 'BODY_BBOX_ZERO (dormant actor)'
        bbox = {'location': [b.location.x, b.location.y, b.location.z], 'extent': [b.extent.x, b.extent.y, b.extent.z],
                'rotation': [b.rotation.pitch, b.rotation.yaw, b.rotation.roll]}
        car.destroy(); world.tick(); s.synchronous_mode = False; world.apply_settings(s)
        body = body_record(bbox, write_ref(P.root / 'a2-bbox.json', {'town': TOWN, 'bbox': bbox}, 'NATIVE_BODY'))
        for c in scenes:
            try:
                prepare_f(c, client, proc, start, world, m, identity, body, bbox)
            except Exception as e:  # recorded, scene stays blocked; never retried with other values
                log(event='SCENE_ERROR', scene=c.id, error=repr(e), trace=traceback.format_exc()[-2500:])
    (P.root / 'prepare-log.json').write_text(json.dumps(P.log_rows, indent=1, default=str), encoding='utf-8')
    print('DONE', P.root)


if __name__ == '__main__':
    main()
