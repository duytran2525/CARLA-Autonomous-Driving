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

from native_v2_common import NO_RENDER, V6, NPC_PID_GRID, REV, arcs, body_record, directed, load, own_server, ownership, write_ref, stream_to  # noqa: E402
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
          'F02': {'vE': F(4), 'vN_char': F(5), 'd0': F(20)},         # + F02_RECIPE_NOTES_20261109
          'F05': {'vE': F(2), 'vN_char': F(2), 'd0': F(4)}}          # PREREG F part 1: queue, release 3 s, both 2 m/s
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


CREEP_TRIALS_S = (F(4, 5), F(6, 5), F(8, 5), F(2))  # F05 addendum U: creep start -> STOP target, one probe each
SETTLE_HOLD_FRAMES = 40  # F05: exact constant queue gap over the last 2 s of the settle probe


def staged_response(role, action, route, targets, rows):
    """Probe-only staged program (F05 creep calibration): SETTLE first, rows after CAPTURE_START; never catalog."""
    r = FrozenResponse(role, action, route, targets, ZERO,
                       {'category': 'F', 'program': {'method': 'ordered-event-program-v1', 'initial': 'SETTLE',
                                                     'transitions': rows},
                        'annex': 'F05 preparation probe, never catalog'}, '')
    return replace(r, hash=_digest({k: getattr(r, k) for k in ('actor_role', 'action_id', 'route', 'targets', 'profile', 'phases')}))


def prepare_f05(c, client, proc, start, world, m, identity, out, rows, arc, cont, note, L):
    """F05 (PREREG F part 1 section 2 + addendum U 20261118): queue d0 = 4 m at rest. (1) settle probes: both actors at
    target 0; the queue gap must be EXACTLY constant over the last 2 s (metrics._detect_f05 compares gap == queue_gap_m);
    two probes must give the identical value (sealed F01/F02 A/B settles are bit-identical, also across sessions);
    (2) four creep probes (EGO 0.5 m/s, then target 0 after CREEP_TRIALS_S) on the same poses: per trial the stop distance
    from the deciding observation to rest and the peak speed -> the CREEP_STOP_BOUND calibration (compile)."""
    from native_v2_common import RELEASE
    from m56.metrics import _route_observation, _route_ref
    inp = out['inputs']; out['recipe_rev'] = 'f-v1.2-f05u'
    # large map: stream the queue site first, else the actors are dormant and observe zero bbox extents (r18a settle1)
    q0 = rows['EGO'][min(len(rows['EGO']) - 1, 40)]
    stream_to(world, q0['x'], q0['y'], q0['z'])

    def routes_for(k):
        nr, na = rows['NPC'][k:], [a - arc['NPC'][k] for a in arc['NPC'][k:]]
        return ({'EGO': directed(rows['EGO'], arc['EGO'], identity.map, c.town, note, cont, arc['EGO'][-1] - 5),
                 'NPC': directed(nr, na, identity.map, c.town, note, cont, na[-1] - 5)},
                {'EGO': (rows['EGO'], arc['EGO']), 'NPC': (nr, na)})

    def k_at(station):
        return next(i for i, a in enumerate(arc['NPC']) if float(a) >= station)

    def gap_of(f, routes):
        try:
            return _route_observation(f, {'directed_route': routes['EGO']}, _route_ref(routes['EGO']), 'min_front_gap')
        except ValueError:  # e.g. INVALID_BODY_TRANSFORM (dormant zero bbox): recorded as no gap, never a crash
            return None

    def settle(label, k):
        routes, prow = routes_for(k)
        poses = {'EGO': IO.pose_on(world, rows['EGO'], e0), 'NPC': IO.pose_on(world, prow['NPC'][0], 0)}
        resp = (nominal_response('EGO', 'A', F(0), routes['EGO']), nominal_response('NPC', 'NPC_COMMON', F(0), routes['NPC']))
        fr = P.probe(client, proc, start, world, identity, c.id, routes, prow, poses, resp, label, None, None, None)
        if not fr:
            return {'reason': f'{label.upper()}_NO_FRAMES:' + ','.join(P.LAST_REASONS)}
        gaps = [gap_of(f, routes) for f in fr]
        still = [all(_speed(a.velocity) <= F(1, 10) for a in f.actors) for f in fr]
        last = gaps[-1]; run = 0
        for g, s in zip(reversed(gaps), reversed(still)):
            if g != last or not s:
                break
            run += 1
        res = {'routes': routes, 'prow': prow, 'poses': poses, 'frames': fr, 'gap': last, 'constant_frames': run,
               'constant_from_s': float(fr[len(fr) - run].simtime - fr[0].simtime) if run else None}
        if last is None or run < SETTLE_HOLD_FRAMES:
            res['reason'] = 'F05_QUEUE_GAP_NOT_CONSTANT'
        return res

    # r18b: an EGO at route station 0 has its rear corners before the route start -> min_front_gap None; spawn 5 m in
    e0 = next(i for i, a in enumerate(arc['EGO']) if float(a) >= 5.)
    k = k_at(float(arc['EGO'][e0]) + L + float(inp['d0']))
    s1 = settle('settle1', k)
    if s1.get('reason') is None and abs(float(s1['gap']) - float(inp['d0'])) > .3:  # same band rule as F01/F02 (0.3 m)
        out['settle1_gap_m'] = float(s1['gap'])
        k = k_at(float(arc['NPC'][k]) + float(inp['d0']) - float(s1['gap'])); s1 = settle('settle1b', k)
    out['settle1'] = {x: (str(s1[x]) if x == 'gap' else s1.get(x)) for x in ('gap', 'constant_frames', 'constant_from_s', 'reason')}
    if s1.get('reason'):
        out.update(status='BLOCKED_FIXTURE', reason=s1['reason']); return P.finish(c, out)
    if abs(float(s1['gap']) - float(inp['d0'])) > .3:
        out.update(status='BLOCKED_FIXTURE', reason='D0_OUTSIDE_BAND', d0_band_m=.3); return P.finish(c, out)
    s2 = settle('settle2', k)
    out['settle2'] = {x: (str(s2[x]) if x == 'gap' else s2.get(x)) for x in ('gap', 'constant_frames', 'constant_from_s', 'reason')}
    if s2.get('reason') or s2['gap'] != s1['gap']:
        out.update(status='BLOCKED_FIXTURE', reason=s2.get('reason') or 'F05_QUEUE_GAP_NOT_REPRODUCIBLE'); return P.finish(c, out)
    routes, prow, poses, fr = s1['routes'], s1['prow'], s1['poses'], s1['frames']
    zero = {'EGO': F(0), 'NPC': F(0)}
    rdy = P.first_ready(fr, routes, zero, boundary_t2=float(fr[0].simtime) - .05)
    if rdy is None:
        out.update(status='BLOCKED_FIXTURE', reason='READINESS_NOT_REACHED_IN_SETTLE'); return P.finish(c, out)
    frr, markers = rdy
    act = {a.role: a for a in fr[-1].actors}
    front = P.front_station(act['EGO'], routes['EGO'])
    # creep calibration (addendum U): EGO CREEP 1/2 after release, STOP 0 after release + T; NPC stays at 0
    trials = []
    for t in CREEP_TRIALS_S:
        rows_e = ({'cause': 'CREEP', 'after_event': 'CAPTURE_START', 'delay_s': RELEASE, 'requires': ()},
                  {'cause': 'STOP', 'after_event': 'CAPTURE_START', 'delay_s': RELEASE + t, 'requires': ()})
        ego_r = staged_response('EGO', 'A', routes['EGO'], {'SETTLE': F(0), 'CREEP': F(1, 2), 'STOP': F(0)}, rows_e)
        label = f'creep-{float(t):.1f}'
        cf = P.probe(client, proc, start, world, identity, c.id, routes, prow, poses,
                     (ego_r, nominal_response('NPC', 'NPC_COMMON', F(0), routes['NPC'])), label, None, None, None)
        trial = {'T_s': str(t), 'frames': len(cf or ())}
        ego = [next(a for a in f.actors if a.role == 'EGO') for f in (cf or ())]
        cause = [a.commands[0].cause if a.commands else None for a in ego]
        st = [_metric_station((a.pose.x, a.pose.y, a.pose.z), routes['EGO']) for a in ego]
        if 'CREEP' not in cause or 'STOP' not in cause or any(s is None for s in st):
            trial['reason'] = 'CREEP_PROBE_INCOMPLETE:' + ','.join(P.LAST_REASONS); trials.append(trial); continue
        i0, i1 = cause.index('CREEP'), cause.index('STOP')
        k_dec = i1 - 1  # the observation the STOP target was computed from (same latency as the product's bound event)
        rest = next((j for j in range(i1, len(ego) - 10) if all(_speed(ego[x].velocity) <= F(1, 10) for x in range(j, j + 10))), None)
        if rest is None:
            trial['reason'] = 'CREEP_PROBE_NO_REST'; trials.append(trial); continue
        speeds = [float(_speed(a.velocity)) for a in ego[i0:rest + 10]]
        trial.update(progress_at_decision_m=float(st[k_dec] - st[i0 - 1]), stop_distance_m=float(st[rest + 9] - st[k_dec]),
                     speed_at_decision_mps=float(_speed(ego[k_dec].velocity)), peak_speed_mps=max(speeds),
                     progress_total_m=float(st[rest + 9] - st[i0 - 1]))
        trials.append(trial)
    out['creep_trials'] = trials
    good = [t for t in trials if 'reason' not in t]
    if len(good) != len(CREEP_TRIALS_S):
        out.update(status='BLOCKED_FIXTURE', reason='F05_CREEP_CALIBRATION_INCOMPLETE'); return P.finish(c, out)
    unc = F(1, 100)
    bound = F(math.ceil(max(t['stop_distance_m'] for t in good) * 100), 100) + F(5, 100)
    vmax = max(F(1, 2), F(math.ceil(max(t['peak_speed_mps'] for t in good) * 100), 100) + F(1, 10))
    boundary = 1 - bound - unc - F(1, 100)
    out['creep_calibration'] = {'method': 'bounded-forward-creep-stop-v1', 'uncertainty': str(unc),
                                'stopping_distance_bound_m': str(bound), 'maximum_forward_speed_mps': str(vmax),
                                'stopping_boundary_m': str(boundary),
                                'rule': 'bound = ceil_0.01(max stop distance) + 0.05; vmax = ceil_0.01(max peak) + 0.10; '
                                        'boundary = 1 - bound - uncertainty - 0.01 (addendum U)'}
    if not F(1, 5) < boundary < 1:
        out.update(status='BLOCKED_FIXTURE', reason='F05_CREEP_BOUND_TOO_WIDE'); return P.finish(c, out)
    dest = front + 16.  # F05_END = front + 10 (exact, geometry); DESTINATION 6 m beyond (DESTINATION_ROOM >= 5)
    if dest + 30. > float(routes['EGO'].arc[-1]):
        out.update(status='BLOCKED_FIXTURE', reason='F_WINDOW_TOO_SHORT', need_ego_m=dest + 30.,
                   have_ego_m=float(routes['EGO'].arc[-1])); return P.finish(c, out)
    npc_rows = prow['NPC'][0]
    cont2 = write_ref(P.root / c.id / 'routes-f.json', {'EGO': rows['EGO'], 'NPC': npc_rows}, 'NATIVE_ROUTE')
    out.update(status='PREPARED', reason=None, targets=zero, markers=markers, T_r=float(frr.simtime) - float(fr[0].simtime),
               d0_realised_m=float(s1['gap']), queue_gap_m=encode_record(s1['gap']), lead_route_start_index=k,
               routes_f=str(cont2.uri), routes_f_sha256=cont2.sha256, poses={kk: encode_record(v) for kk, v in poses.items()},
               grounds={'EGO': IO.grounds.get(id(rows['EGO'])), 'NPC': IO.grounds.get(id(npc_rows))},
               sections_m={'F05_END': {'route': 'EGO', 'station': front + 10.}, 'DESTINATION': {'route': 'EGO', 'station': dest}},
               nominal_front_t0_m=front,
               # the runtime-observed bodies (first observation; same spawn pose -> identical across sessions, sealed F02
               # probe vs A/B 18/11); CREEP_STOP_BOUND binds this body hash, never the bare prepare bbox
               observed_bodies={a.role: encode_record(a.body) for a in fr[0].actors})
    return P.finish(c, out)


def prepare_f(c, client, proc, start, world, m, identity, body, bbox):
    mech = (c.environment.get('mechanism') or c.slot).replace('-ALT1', '')
    assert mech in INPUTS, f'F_MECHANISM_NOT_IN_PART1:{mech}'
    inp = INPUTS[mech]; L = 2 * bbox['extent'][0]
    if 'd0' in c.parameters:  # addendum F01-v2 (2026-11-14): the candidate's declared d0 (F01-S2: 31/2), not the table
        inp = {**inp, 'd0': F(c.parameters['d0'].values[0])}
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
    if mech == 'F05':  # addendum U (20261118): standing queue, own branch; F01/F02 below unchanged
        return prepare_f05(c, client, proc, start, world, m, identity, out, rows, arc, cont, note, L)
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

    def run(label, rts, pr, ps, ng=None, eg=None):
        resp = (nominal_response('EGO', 'A', inp['vE'], rts['EGO']), nominal_response('NPC', 'NPC_COMMON', inp['vN_char'], rts['NPC']))
        return P.probe(client, proc, start, world, identity, c.id, rts, pr, ps, resp, label, None, ng, eg)
    p1 = run('probe1', routes, prow, poses)
    if not p1:
        out.update(status='BLOCKED_FIXTURE', reason='PROBE1_NO_FRAMES:' + ','.join(P.LAST_REASONS)); return P.finish(c, out)
    # f-v1.1 (2026-11-14, Claude under Duy delegation, POST-NUMBER rule, principle 6; batch log 14/11): f-v1 required
    # |v - nominal| <= 0.05 m/s, which the stock controller never reaches (it settles ~0.14 m/s low: F01/F02 r8 blocked).
    # Now exactly the I/O rule (native-io-prepare.py): plateau (range <= 0.10 over 2 s), PID grids, readiness targets =
    # the probe-2 plateau. F has no decision station, so the plateau window is each probe's last 2 s (e_entry far away).
    out['recipe_rev'] = 'f-v1.1'
    FAR = 1e9
    ego_gains, npc_gains, grid = None, None, []
    plat = P.plateaus(p1, routes, body, FAR, 0, npc_until='last')
    grid.append({'who': 'stock', 'EGO_range': plat.get('EGO_range'), 'NPC_range': plat.get('NPC_range')})
    if plat.get('EGO_range', 1.) > .10:
        for ei, eg in enumerate(NPC_PID_GRID[1:], 1):
            q = run(f'probe1-egopid{ei}', routes, prow, poses, None, eg)
            pq = P.plateaus(q, routes, body, FAR, 0, npc_until='last') if q else {}
            grid.append({'who': 'EGO', 'gains': [str(x) for x in eg], 'EGO_range': pq.get('EGO_range')})
            if q and pq.get('EGO_range', 1.) <= .10:
                ego_gains, p1, plat = eg, q, pq; break
    if plat.get('NPC') is None:
        for gi, ng in enumerate(NPC_PID_GRID[1:], 1):
            q = run(f'probe1-pid{gi}', routes, prow, poses, ng, ego_gains)
            pq = P.plateaus(q, routes, body, FAR, 0, npc_until='last') if q else {}
            grid.append({'who': 'NPC', 'gains': [str(x) for x in ng], 'NPC_range': pq.get('NPC_range')})
            if q and pq.get('NPC') is not None:
                npc_gains, p1, plat = ng, q, pq; break
    out.update(pid_grid=grid, ego_longitudinal=None if ego_gains is None else [str(x) for x in ego_gains],
               npc_longitudinal=None if npc_gains is None else [str(x) for x in npc_gains], probe1=plat)
    if plat.get('reason') or plat.get('NPC') is None:
        out.update(status='BLOCKED_FIXTURE', reason=plat.get('reason') or 'READINESS_NOT_STEADY'); return P.finish(c, out)
    tE = P.steady_at(p1, 'EGO', plat['EGO']); tN = P.steady_at(p1, 'NPC', plat['NPC'])
    out.update(probe1_steady_s={'EGO': tE, 'NPC': tN})
    if tE is None or tN is None:
        out.update(status='BLOCKED_FIXTURE', reason='PROBE1_NOT_STEADY'); return P.finish(c, out)
    # f-v1.2 (2026-11-14, Duy [chat] "b"; POST-NUMBER, principle 6): f-v1.1 took the probe-1 gap at max(steady_at), but
    # probe 2 is ready at first_ready (~2.6 s earlier), so d0 at readiness came out 12.96 m, not 11.4 m. Probe 1 now uses
    # the same first_ready rule (speeds do not depend on the lead's start, so probe 2 is ready at the same elapsed time).
    out['recipe_rev'] = 'f-v1.2'
    t1 = {'EGO': F(round(plat['EGO'] * 1000), 1000), 'NPC': F(round(plat['NPC'] * 1000), 1000)}
    r1 = P.first_ready(p1, routes, t1, boundary_t2=float(p1[0].simtime) - .05)
    if r1 is None:
        out.update(status='BLOCKED_FIXTURE', reason='READINESS_NOT_REACHED_IN_PROBE1'); return P.finish(c, out)
    act = {a.role: a for a in r1[0].actors}
    gap = IO.rear_station(act[lead], routes[follow]) - P.front_station(act[follow], routes[follow])
    # F02 recipe notes 2: gap at readiness d0 + (vN - vE) * 1 s, so TRIGGER (gap 20 m) comes 1 s after readiness
    target = float(inp['d0']) + (float(inp['vN_char'] - inp['vE']) if mech == 'F02' else 0.)
    shift = target - gap
    out.update(probe1_ready_s=float(r1[0].simtime) - float(p1[0].simtime), probe1_gap_at_ready_m=gap, lead_shift_m=shift,
               target_gap_at_ready_m=target, lead=lead)

    def probe_at(shift, label):
        """One readiness probe with the lead shifted by `shift`; everything downstream comes from this probe only."""
        routes2, prow2, k2 = routes_for(first + shift)
        poses2 = poses_for(prow2, k2)
        p2 = run(label, routes2, prow2, poses2, npc_gains, ego_gains)
        if not p2:
            return {'reason': f'{label.upper()}_NO_FRAMES:' + ','.join(P.LAST_REASONS)}
        plat2 = P.plateaus(p2, routes2, body, FAR, 0, npc_until='last')
        if plat2.get('reason'):
            return {'reason': plat2['reason'], 'plat': plat2}
        targets = {'EGO': F(round(plat2['EGO'] * 1000), 1000), 'NPC': F(round(plat2['NPC'] * 1000), 1000)}  # f-v1.1
        ready = P.first_ready(p2, routes2, targets, boundary_t2=float(p2[0].simtime) - .05)
        if ready is None:
            return {'reason': f'READINESS_NOT_REACHED_IN_{label.upper()}', 'plat': plat2}
        a = {x.role: x for x in ready[0].actors}
        d0r = IO.rear_station(a[lead], routes2[follow]) - P.front_station(a[follow], routes2[follow])
        return {'routes2': routes2, 'prow2': prow2, 'k2': k2, 'poses2': poses2, 'p2': p2, 'plat': plat2, 'targets': targets,
                'ready': ready, 'act': a, 'd0r': d0r, 'shift': shift}
    # f-v1.2 band, fixed before any native run: route rows are 0.2 m apart and routes_for snaps the lead to the next row
    # (miss up to +0.2 m), plus the 0.1 m station tolerance of first_ready -> |d0_r - target| <= 0.3 m. At most ONE
    # corrective re-probe (label probe2b, shift += residual); still outside -> BLOCKED_FIXTURE D0_OUTSIDE_BAND.
    BAND = .3
    pr = probe_at(shift, 'probe2')
    out['probe2'] = pr.get('plat')
    if pr.get('reason'):
        out.update(status='BLOCKED_FIXTURE', reason=pr['reason']); return P.finish(c, out)
    out['probe2_d0_m'] = pr['d0r']
    if abs(pr['d0r'] - target) > BAND:
        pr = probe_at(pr['shift'] + (target - pr['d0r']), 'probe2b')
        out['probe2b'] = pr.get('plat')
        if pr.get('reason'):
            out.update(status='BLOCKED_FIXTURE', reason=pr['reason']); return P.finish(c, out)
        out['probe2b_d0_m'] = pr['d0r']
        if abs(pr['d0r'] - target) > BAND:
            out.update(status='BLOCKED_FIXTURE', reason='D0_OUTSIDE_BAND', d0_band_m=BAND); return P.finish(c, out)
    out.update(d0_band_m=BAND, lead_shift_final_m=pr['shift'])
    routes2, prow2, k2, poses2, p2 = pr['routes2'], pr['prow2'], pr['k2'], pr['poses2'], pr['p2']
    targets, (frr, markers), act, d0r = pr['targets'], pr['ready'], pr['act'], pr['d0r']
    ego, npc = act['EGO'], act['NPC']
    ego_front = P.front_station(ego, routes2['EGO'])
    extra = {}
    if mech == 'F01':
        npc_front = P.front_station(npc, routes2['NPC'])
        brake = npc_front + 3 * float(inp['vN_char']); end = brake + 20.
        # addendum F01-v2: run-out after F01_END 10 -> 6 m (v13 DESTINATION_ROOM needs >= 5); S1's EGO B lost ~0.6 m/s
        # of gap after RESUME, so every metre of run-out past the window is gap spent for nothing
        ego_end = ego_front + (end - npc_front) + d0r + L + 6.
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
