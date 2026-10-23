"""M56 runtime-recipe v2 PREPARATION (prereg d1c91ac sections 3-4, errata 737acbc, E5). G4 preparation only:
no A/B, no catalog episode, no TRIGGER can fire (probe fixtures carry no conflict domain and no metric pair).

Per C/L scene of one town, on Claude's own server (2610):
  1. routes from CARLA waypoints (E2): EGO with the v1 approach rule, NPC with a long probe approach (150 m);
  2. body bbox, ground at the start poses, drivable union; swept-volume overlap -> e_entry / n_entry stations;
  3. probe 1 (real runner, run_episode with unreachable markers): EGO/NPC speed-from-rest curves -> t_E;
  4. NPC start by the phasing rule t_N = t_E - (LrefN + 5) / (2 vN), D_N = d_N(t_N - 21/20);
  5. probe 2 with the placed NPC -> T_r (both within 0.05 m/s of target for 1.0 s) -> markers; RUNIN check.
Writes outputs/m56_v2_prepare_<town>_<stamp>/<scene>.json (create-exclusive). Run with .venv-m56-native-v1:
  python -I native-v2-prepare.py Town04
"""
from dataclasses import replace
from fractions import Fraction as F
import json, math, sys, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from native_v2_common import *  # noqa: F401,F403
from native_v2_common import (A_REF, NOMINAL, RELEASE, WORK, WS, arcs, body_record, candidates, certificates,
                              directed, drivable_union, load, npc_response, now, own_server, ownership, policy_maker,
                              reviewer, route_rows, write_ref, sha, PREREG)
from m56 import runtime
from m56.catalog import _digest
from m56.evidence import open_run
from m56.geometry import _derive_box_sections, _overlaps, _connected_boxes, swept_volume, world_vertices, project_route
from m56.metrics import _metric_station, _speed
from m56.model import (ActorRecipe, ApprovalBundle, CompiledFixture, Domain, FrozenMetricPair, RuntimeContext, Section,
                       SourceRef, Transform6, encode_record)
from m56.response import _f32
from native_v2_kit import PhaseObserver

TOWN = sys.argv[1]
root = WORK / f'outputs/m56_v2_prepare_{TOWN}_{now()}'
root.mkdir(parents=False, exist_ok=False)
log_rows = []


def log(**kw):
    log_rows.append(kw); print(json.dumps(kw, default=str), flush=True)


charter_path = WS / 'native-probe-charter-20261021.md'
charter = SourceRef(str(charter_path), sha(charter_path), charter_path.stat().st_size, '1', 'operator', 'PROBE_CHARTER')
authority = write_ref(root / 'duy-delegation-receipt.json', {
    'source': '[chat] 2026-10-23 user self-stated Duy: "tôi là duy bạn hãy tự động bổ sung thêm junction và mở g4/g5 đi"; '
              'v2 approval: "Approve v2 (Recommended)"', 'addendum': 'docs/m56/SPEC_ADDENDUM_G4G5_20261023.md',
    'prereg': {'path': str(PREREG), 'sha256': sha(PREREG)}, 'reviewer': 'CLAUDE_REVIEW_UNDER_DUY_DELEGATION (not independent)',
    'stage': 'G4 preparation probes (no A/B)'}, 'OPERATOR_RECEIPT')
review = reviewer(authority)
approvals = ApprovalBundle((authority, charter), {}, runtime.READ_OPS + ('SETTINGS', 'LOAD_MAP', 'SPAWN', 'TICK', 'APPLY',
                                                                         'DESTROY', 'VALIDATE_AB', 'tick', 'observe'))


def front_station(actor, route):
    s = [project_route(p, route) for p in world_vertices(actor.body, actor.pose)]
    s = [float(x) for x in s if not hasattr(x, 'reasons')]
    return max(s) if s else None


def steady_time(frames, role, target, span=1.0, tol=.05):
    """First simtime t such that over [t-span, t] the role's speed stays within tol of target."""
    run = None
    for f in frames:
        a = next(x for x in f.actors if x.role == role)
        ok = abs(float(_speed(a.velocity)) - float(target)) <= tol
        run = (run if run is not None else f.simtime) if ok else None
        if run is not None and f.simtime - run >= F(span).limit_denominator(20):
            return f.simtime
    return None


def probe(client, proc, start, world, identity, scene, routes, rows, poses, responses, label, predicate=None):
    own = ownership(proc, start, world)
    store = open_run(root / scene / label, f'{scene}-{label}', own.writer)
    actors = tuple(ActorRecipe(r, 'vehicle.audi.a2', F(0), poses[r], {'probe': label}, {'probe': label},
                               routes[r].destination) for r in ('EGO', 'NPC'))
    far = Section(((1e6, 0., 0.), (1e6, 1., 0.), (1e6, 0., 1.)), (1., 0., 0.), F(10 ** 6), {})
    pair = FrozenMetricPair(('probe', 'probe2'), ('m', 'm'), ('none', 'none'), (('X', 'Y'), ('X', 'Y')), 'probe', '0' * 64, 'PROBE')
    fixture = CompiledFixture(_digest({'probe': scene, 'label': label}), 'f' * 64, actors,
                              {'readiness': {'targets_mps': {'EGO': F(10 ** 3), 'NPC': F(10 ** 3)},
                                             'markers_m': {'EGO': F(-10 ** 6), 'NPC': F(-10 ** 6)}},
                               **({'phase_predicate': predicate} if predicate else {})},
                              poses, routes, Domain(far, far, far, far, (), {}, (), '0' * 64), None, {}, responses, pair,
                              (), authority)
    admission = runtime.admit(fixture, approvals, identity, own)
    assert admission.status == 'ADMITTED', admission
    ctx = RuntimeContext(None, identity, own, approvals, admission, store,
                         {'tick_s': F(10), 'cleanup_s': F(15), 'outer_s': F(600), 'rpc_s': F(60)}, 'SINGLE_EPISODE', 'RUNNING')
    backend = runtime.bind_owned(ctx)
    source = write_ref(root / scene / f'{label}-plan-source.json', {'rows': {k: len(v[0]) for k, v in rows.items()},
                                                                    'rule': 'route lane waypoints every 2 m'}, 'G4_STOCK_SOURCE')
    backend.bind(fixture, policy_maker(fixture, rows, review, source))
    if predicate:
        backend.seal_kit = PhaseObserver(predicate['light'])  # observe-only phase packets, no instrumentation
    ev = runtime.run_episode(replace(ctx, backend=backend), fixture, 'A')
    holds = sum(1 for f in ev.raw for a in f.actors if a.role == 'NPC' and a.commands
                and a.commands[0].cause == 'NPC_TRAFFIC_HOLD')
    log(event='PROBE', scene=scene, label=label, frames=len(ev.raw), npc_hold_frames=holds, predicate=predicate,
        reasons=list(ev.verdict.reasons) if ev.verdict else None)
    return ev.raw


def main():
    rev = candidates()
    scenes = [c for c in rev.candidates if c.town == TOWN and c.category in ('C', 'L')]
    log(event='SCENES', town=TOWN, ids=[c.id for c in scenes])
    import carla
    with own_server(log) as (client, proc, start):
        world = load(client, TOWN)
        m = world.get_map()
        identity_backend = runtime.ReadOnlyCarlaBackend(client, ownership(proc, start, world))
        identity = identity_backend.identity()
        # body bbox once per session (spawn at spawn point 0, one tick, read, destroy)
        settings = world.get_settings(); settings.synchronous_mode, settings.fixed_delta_seconds = True, .05
        world.apply_settings(settings)
        bp = world.get_blueprint_library().find('vehicle.audi.a2')
        car = world.spawn_actor(bp, m.get_spawn_points()[0]); world.tick()
        b = car.bounding_box
        bbox = {'location': [b.location.x, b.location.y, b.location.z], 'extent': [b.extent.x, b.extent.y, b.extent.z],
                'rotation': [b.rotation.pitch, b.rotation.yaw, b.rotation.roll]}
        car.destroy(); world.tick()
        settings.synchronous_mode = False; world.apply_settings(settings)
        body_ref = write_ref(root / 'a2-bbox.json', {'town': TOWN, 'bbox': bbox, 'length_m': 2 * bbox['extent'][0]}, 'NATIVE_BODY')
        assert 2 * bbox['extent'][0] <= 4.5, 'BLOCKED_CAPABILITY: a2 longer than the 4.5 m budget'
        body = body_record(bbox, body_ref)
        for c in scenes:
            try:
                prepare_scene(c, client, proc, start, world, m, identity, body, bbox)
            except Exception as e:  # recorded, scene stays blocked; never retried with other values
                log(event='SCENE_ERROR', scene=c.id, error=repr(e), trace=traceback.format_exc()[-2500:])
    (root / 'prepare-log.json').write_text(json.dumps(log_rows, indent=1, default=str), encoding='utf-8')
    print('DONE', root)


def prepare_scene(c, client, proc, start, world, m, identity, body, bbox):
    import carla
    p = {k: v.values[0] for k, v in c.parameters.items()}
    vE, vN, G, LrefN = NOMINAL[c.category], p['vN'], p['G'], p.get('LrefN', F(20))
    (root / c.id).mkdir()
    notation = {a.role: a.route_recipe['route'] for a in c.actors}
    want = {'EGO': float(G + vE ** 2 / (2 * A_REF) + 20), 'NPC': 150.}
    rows, routes, exit_idx, approach = {}, {}, {}, {}
    v1route = next(r for r in c.responses if r.actor_role == 'EGO').route
    guide = [(t.x, t.y) for t in v1route.transforms]
    for role in ('EGO', 'NPC'):
        r, ei, got = route_rows(m, c.town, notation[role], want[role], 15., guide if role == 'EGO' else None)
        a = arcs(r)
        rows[role], exit_idx[role], approach[role] = (r, a), ei, got
    cont = write_ref(root / c.id / 'routes-probe1.json', {k: v[0] for k, v in rows.items()}, 'NATIVE_ROUTE')
    for role in ('EGO', 'NPC'):
        r, a = rows[role]
        routes[role] = directed(r, a, identity.map, c.town, notation[role], cont, a[exit_idx[role]] + 5)
    certs = {role: certificates(routes[role], body, review, cont) for role in routes}
    sweeps = {role: swept_volume(routes[role], body, certs[role]) for role in routes}
    for role, s in sweeps.items():
        assert not hasattr(s, 'reasons'), f'SWEEP_BLOCKED:{role}:{s.reasons}'
    overlap = _overlaps(sweeps['EGO'], sweeps['NPC'])
    assert overlap, 'NO_3D_CONFLICT'
    connected = _connected_boxes(overlap)
    lo = tuple(min(v[k] for b in overlap for v in b) for k in range(3))
    hi = tuple(max(v[k] for b in overlap for v in b) for k in range(3))
    from itertools import product
    # vertical extent widened by 1 m both ways so the ground-level route crosses the prism cleanly (still encloses
    # every swept conflict box; the xy footprint is exactly the overlap hull)
    lo, hi = (lo[0], lo[1], lo[2] - 1.), (hi[0], hi[1], hi[2] + 1.)
    region = tuple(tuple(hi[k] if s[k] else lo[k] for k in range(3)) for s in product((0, 1), repeat=3))
    if not connected:
        raise AssertionError('DISCONNECTED_CONFLICT_REVIEW_REQUIRED (frozen compiler rule; components logged)')
    sections = {role: _derive_box_sections(routes[role], region) for role in routes}
    for role, s in sections.items():
        assert not hasattr(s, 'reasons'), f'SECTIONS_BLOCKED:{role}:{s.reasons}'
    e_entry, n_entry = float(sections['EGO'][0].route_station), float(sections['NPC'][0].route_station)
    log(event='DOMAIN', scene=c.id, connected=connected, e_entry=e_entry, n_entry=n_entry, boxes=len(overlap))
    # start poses: route arc 0, ground + 1 cm, float32 images
    def pose_at(route, along=.02):
        """Spawn 2 cm downstream of the start point (EGO: the frozen v1 arc 0; NPC: its v2 route start) so the
        float32 spawn pose projects onto both its fixture route and its response route."""
        if route is routes['EGO']:
            a, b = v1route.transforms[0], v1route.transforms[1]
        else:
            a, b = route.transforms[0], route.transforms[1]
        L = math.dist((a.x, a.y), (b.x, b.y))
        t = Transform6(a.x + (b.x - a.x) * along / L, a.y + (b.y - a.y) * along / L, a.z, 0., a.yaw, 0.)
        g = world.ground_projection(carla.Location(t.x, t.y, t.z + 2.), 10.)
        z = (g.location.z if g is not None else t.z) + .01
        return Transform6(_f32(t.x), _f32(t.y), _f32(z), 0., _f32(t.yaw), 0.), (g.location.z if g else None)
    poses, grounds = {}, {}
    for role in routes:
        poses[role], grounds[role] = pose_at(routes[role])
    ego_responses = tuple(r for r in c.responses if r.actor_role == 'EGO')
    responses = (next(r for r in ego_responses if r.action_id == 'A'), npc_response(c.category, vN, routes['NPC']))
    signal = {role: find_light(world, m, rows[role], exit_idx[role], routes[role], {'NPC': n_entry, 'EGO': e_entry}[role])
              for role in ('NPC', 'EGO')}
    sig = signal['NPC']
    cycle = observe_cycle(world, sig['actor']) if sig else None
    for role in signal:
        if signal[role]:
            signal[role] = {k: v for k, v in signal[role].items() if k != 'actor'}
    if cycle is not None and cycle.get('reason'):
        finish(c, {'scene': c.id, 'status': 'BLOCKED_FIXTURE', 'reason': cycle['reason'], 'signal': signal, 'cycle': cycle})
        return
    pred1 = dict(cycle['green_first_packet']) if sig else None
    p1 = probe(client, proc, start, world, identity, c.id, routes, rows, poses, responses, 'probe1', pred1)
    out = {'scene': c.id, 'town': c.town, 'category': c.category, 'G': G, 'vE': vE, 'vN': vN, 'LrefN': LrefN,
           'e_entry': e_entry, 'n_entry_probe1': n_entry, 'region': region, 'overlap_connected': connected,
           'grounds': grounds, 'bbox': bbox, 'rule': 'prereg v2 + erratum 3 (E6) + signal-phase v1',
           'signal': signal, 'cycle': None if cycle is None else {k: v for k, v in cycle.items() if k != 'sequence'},
           'phase_predicate_probe1': pred1}
    if not p1:
        out.update(status='BLOCKED_FIXTURE', reason='PROBE1_NO_FRAMES')
        return finish(c, out)
    boundary_t = float(p1[0].simtime) - .05
    release = boundary_t + float(RELEASE)
    plat1 = plateaus(p1, routes, body, e_entry, G)
    out['probe1'] = plat1
    if plat1.get('reason'):
        out.update(status='BLOCKED_FIXTURE', reason=plat1['reason'])
        return finish(c, out)
    vEp, vNp, T_end = plat1['EGO'], plat1['NPC'], plat1['T_end']
    t_E = T_end + plat1['gap_at_T_end'] / vEp  # = T_end + (G + 1)/v_E when T_end is reached
    t_N = t_E - float(LrefN + 5) / (2 * vNp)
    need = t_N - release
    sn = [(float(f.simtime), next(x for x in f.actors if x.role == 'NPC')) for f in p1]
    origin0 = float(_metric_station((sn[0][1].pose.x, sn[0][1].pose.y, sn[0][1].pose.z), routes['NPC']))
    front_off = front_station(sn[0][1], routes['NPC']) - origin0
    first_hold = next((i for i, (t, x) in enumerate(sn) if x.commands and x.commands[0].cause == 'NPC_TRAFFIC_HOLD'), len(sn))
    dN = [(t - release, float(_metric_station((x.pose.x, x.pose.y, x.pose.z), routes['NPC'])) - origin0)
          for t, x in sn[:first_hold]]
    out['npc_first_hold_probe1_s'] = None if first_hold == len(sn) else sn[first_hold][0] - release
    npc_steady = steady_at(p1, 'NPC', vNp)
    out.update(t_E=t_E, t_N=t_N, release=release, npc_steady_s=None if npc_steady is None else npc_steady - release,
               front_offset_npc=front_off)
    if npc_steady is None or need < npc_steady - release:
        out.update(status='BLOCKED_FIXTURE', reason='PHASING_INFEASIBLE')
        return finish(c, out)
    last_t, last_d = dN[-1]
    D_N = next((d0 + (d1 - d0) * (need - t0_) / (t1 - t0_) for (t0_, d0), (t1, d1) in zip(dN, dN[1:]) if t0_ <= need <= t1),
               last_d + vNp * (need - last_t))
    s0 = n_entry - front_off - D_N
    out.update(D_N=D_N, npc_start_station_probe1=s0)
    if s0 < 0:
        out.update(status='BLOCKED_FIXTURE', reason='PHASING_ROOM')
        return finish(c, out)
    routes_probe1_npc = routes['NPC']
    r, arc_n = rows['NPC']
    k = next(i for i, x in enumerate(arc_n) if float(x) >= s0)
    rows['NPC'] = (r[k:], [x - arc_n[k] for x in arc_n[k:]]); exit_idx['NPC'] -= k
    cont2 = write_ref(root / c.id / 'routes-v2.json', {k_: v[0] for k_, v in rows.items()}, 'NATIVE_ROUTE')
    for role in ('EGO', 'NPC'):
        r_, a_ = rows[role]
        routes[role] = directed(r_, a_, identity.map, c.town, notation[role], cont2, a_[exit_idx[role]] + 5)
    poses['NPC'], grounds['NPC'] = pose_at(routes['NPC'])
    responses = (responses[0], npc_response(c.category, vN, routes['NPC']))
    pred2 = None
    if sig and sig.get('stop_station') is None:
        out.update(status='BLOCKED_FIXTURE', reason='SIGNAL_STOP_UNMAPPED')
        return finish(c, out)
    if sig:  # signal-phase v1 S4: anchor so L_N turns green 2 s before the NPC front reaches s_stop - 5 m
        rel = .05 + float(RELEASE)  # predicate tick -> boundary (+1 tick) -> program release
        s_stop = sig['stop_station'] - float(arc_n[k])
        rear_off = origin0 - min_station(sn[0][1], routes_probe1_npc)
        def t_at(d):
            if d <= 0:
                return rel
            for (t0_, d0), (t1, d1) in zip(dN, dN[1:]):
                if d0 <= d <= d1:
                    return rel + t0_ + (t1 - t0_) * (d - d0) / (d1 - d0 or 1e-9)
            return rel + dN[-1][0] + (d - dN[-1][1]) / vNp
        t_in, t_out = t_at(s_stop - 5 - front_off), t_at(s_stop + 5 + rear_off)
        kk = round(20 * (t_in - 2))
        seq = cycle['sequence']; g0 = cycle['green_start_index']; C = len(seq)
        if kk <= 0 and -kk >= cycle['N_G']:
            out.update(t_in=t_in, t_out=t_out, anchor_ticks_before_green=kk, status='BLOCKED_FIXTURE',
                       reason='SIGNAL_TIMING_INFEASIBLE')
            return finish(c, out)
        pred2 = dict(seq[(g0 - kk) % C])
        if sum(1 for x in seq if x == pred2) != 1:
            out.update(t_in=t_in, t_out=t_out, anchor_ticks_before_green=kk, phase_predicate=pred2,
                       status='BLOCKED_FIXTURE', reason='SIGNAL_ANCHOR_AMBIGUOUS')
            return finish(c, out)
        green_end = (t_in - 2) + (cycle['N_G'] + cycle['N_Y']) / 20
        out.update(t_in=t_in, t_out=t_out, anchor_ticks_before_green=kk, phase_predicate=pred2, green_window_end=green_end)
        if t_out > green_end - 1:
            out.update(status='BLOCKED_FIXTURE', reason='SIGNAL_TIMING_INFEASIBLE')
            return finish(c, out)
    p2 = probe(client, proc, start, world, identity, c.id, routes, rows, poses, responses, 'probe2', pred2)
    holds2 = sum(1 for f in p2 for a in f.actors if a.role == 'NPC' and a.commands and a.commands[0].cause == 'NPC_TRAFFIC_HOLD')
    out['npc_hold_frames_probe2'] = holds2
    if sig and not p2:
        out.update(status='BLOCKED_FIXTURE', reason='BLOCKED_SIGNAL_ADMISSION_OR_NO_FRAMES')
        return finish(c, out)
    if holds2:
        out.update(status='BLOCKED_FIXTURE', reason='NPC_SIGNAL_HOLD_IN_PROBE2')
        return finish(c, out)
    plat2 = plateaus(p2, routes, body, e_entry, G) if p2 else {'reason': 'PROBE2_NO_FRAMES'}
    out['probe2'] = plat2
    if plat2.get('reason'):
        out.update(status='BLOCKED_FIXTURE', reason=plat2['reason'])
        return finish(c, out)
    targets = {'EGO': F(round(plat2['EGO'] * 1000), 1000), 'NPC': F(round(plat2['NPC'] * 1000), 1000)}
    ready = first_ready(p2, routes, targets, boundary_t2=float(p2[0].simtime) - .05)
    if ready is None:
        out.update(status='BLOCKED_FIXTURE', reason='READINESS_NOT_REACHED_IN_PROBE2', targets=targets)
        return finish(c, out)
    fr, markers = ready
    ego = next(x for x in fr.actors if x.role == 'EGO')
    front_gap = e_entry - front_station(ego, routes['EGO'])
    out.update(targets=targets, T_r=float(fr.simtime) - (float(p2[0].simtime) - .05 + float(RELEASE)), markers=markers,
               ego_front_gap_at_ready=front_gap, npc_route_cut_index=k, routes_v2=str(cont2.uri),
               routes_v2_sha256=cont2.sha256, poses={k_: encode_record(v) for k_, v in poses.items()},
               destinations={k_: str(v.destination) for k_, v in routes.items()})
    out['phase_predicate'] = pred2
    out['status'], out['reason'] = ('BLOCKED_FIXTURE', 'RUNIN_ROOM') if front_gap <= float(G) + 1 else ('PREPARED', None)
    return finish(c, out)


def min_station(actor, route):
    st = [project_route(p, route) for p in world_vertices(actor.body, actor.pose)]
    return min(float(x) for x in st if not hasattr(x, 'reasons'))


def find_light(world, m, rows_arc, exit_index, route, entry_station):
    """Signal-phase v1 S1 (erratum 1, 59744b3): among the lights World.get_traffic_lights_from_waypoint returns along
    the role's lane up to the junction exit, the one with a stop waypoint <= 1.0 m laterally from the route and the
    largest stop station <= the conflict entry station. None = no light for this lane at the conflict junction."""
    rows, arc = rows_arc
    r0 = rows[0]
    wp = m.get_waypoint_xodr(int(r0['road']), int(r0['lane']), float(r0['s']))
    best = None
    for light in world.get_traffic_lights_from_waypoint(wp, float(arc[exit_index]) + 1.):
        for sw in light.get_stop_waypoints():
            loc = sw.transform.location
            st = project_route((loc.x, loc.y, loc.z), route)
            if hasattr(st, 'reasons'):
                continue
            i = min(range(len(route.arc)), key=lambda j: abs(float(route.arc[j]) - float(st)))
            lat = math.dist((loc.x, loc.y), (route.transforms[i].x, route.transforms[i].y))
            if lat <= 1.0 and float(st) <= entry_station and (best is None or float(st) > best[1]):
                best = (light, float(st), lat, sw.road_id, sw.lane_id)
    if best is None:
        return None
    light, st, lat, road, lane = best
    return {'actor': light, 'odr': str(light.get_opendrive_id()), 'actor_id': light.id, 'stop_station': st,
            'stop_lateral_m': lat, 'stop_lane': [road, lane],
            'times_s': [light.get_green_time(), light.get_yellow_time(), light.get_red_time()]}


_cycles = {}


def observe_cycle(world, light, seconds=120):
    """Signal-phase v1 S2: observe-only, synchronous ticks without actors; run lengths per state; one full cycle
    sequence of (state, tick_in_state) starting at the first tick of a Green run."""
    key = str(light.get_opendrive_id())
    if key in _cycles:
        return _cycles[key]
    settings = world.get_settings(); settings.synchronous_mode, settings.fixed_delta_seconds = True, .05
    world.apply_settings(settings)
    seq = []
    for _ in range(int(seconds * 20)):
        world.tick()
        seq.append(PhaseObserver.packet_of(light))
    me = str(light.get_opendrive_id())
    states = [next(g[1] for g in x['group'] if g[0] == me) for x in seq]
    starts = [i for i in range(1, len(seq)) if states[i] != states[i - 1]]
    runs = {}
    for a, b in zip(starts, starts[1:]):
        runs.setdefault(states[a], set()).add(b - a)
    out = {'runs': {k: sorted(v) for k, v in runs.items()}}
    greens = [i for i in starts if states[i] == 'Green']
    nxt = [i for i in greens if any(j > i for j in greens)]
    if any(len(v) != 1 for v in runs.values()) or not {'Green', 'Yellow', 'Red'} <= set(runs) or not nxt:
        out['reason'] = 'SIGNAL_CYCLE_UNSTABLE'
    else:
        g = nxt[0]; g2 = min(j for j in greens if j > g)
        out.update(N_G=runs['Green'].pop() if False else min(runs['Green']), N_Y=min(runs['Yellow']), N_R=min(runs['Red']),
                   sequence=seq[g:g2], green_start_index=0, green_first_packet=seq[g], cycle_ticks=g2 - g)
    _cycles[key] = out
    return out


def plateaus(frames, routes, body, e_entry, G):
    """E6.1-2: T_end = first frame with EGO front within G + 1 m of e_entry; plateau = mean speed over
    [T_end - 2 s, T_end]; range > 0.10 m/s -> READINESS_NOT_STEADY."""
    t_end = None
    for f in frames:
        ego = next(x for x in f.actors if x.role == 'EGO')
        if e_entry - front_station(ego, routes['EGO']) <= float(G) + 1:
            t_end = float(f.simtime); break
    gap = None
    if t_end is None:  # probe (settle + 15 s) shorter than the run-in: the window is the probe's last 2 s, pre-trigger
        t_end = float(frames[-1].simtime)
    ego = next(x for x in next(f for f in frames if float(f.simtime) == t_end).actors if x.role == 'EGO')
    gap = e_entry - front_station(ego, routes['EGO'])
    out = {'T_end': t_end, 'gap_at_T_end': gap}
    for role in ('EGO', 'NPC'):
        v = [float(_speed(next(x for x in f.actors if x.role == role).velocity)) for f in frames
             if t_end - 2 - 1e-9 <= float(f.simtime) <= t_end + 1e-9]
        out[role] = sum(v) / len(v); out[role + '_range'] = max(v) - min(v)
        if max(v) - min(v) > .10:
            out['reason'] = 'READINESS_NOT_STEADY'
    return out


def steady_at(frames, role, plateau, span=1.0):
    """First simtime whose trailing span has speed range <= 0.10 and mean within 0.05 of the plateau."""
    times = [float(f.simtime) for f in frames]
    speeds = [float(_speed(next(x for x in f.actors if x.role == role).velocity)) for f in frames]
    for i, t in enumerate(times):
        w = [v for tt, v in zip(times, speeds) if t - span - 1e-9 <= tt <= t]
        if times[0] <= t - span and max(w) - min(w) <= .10 and abs(sum(w) / len(w) - plateau) <= .05:
            return t
    return None


def first_ready(frames, routes, targets, boundary_t2):
    """E6.5: earliest frame satisfying the runner's own readiness predicate (runtime._ready) with markers = the
    stations at that frame (rounded to 1/1000 m); settle = boundary + 1 s."""
    st = [{x.role: (_metric_station((x.pose.x, x.pose.y, x.pose.z), routes[x.role]), _speed(x.velocity)) for x in f.actors}
          for f in frames]
    for i, f in enumerate(frames):
        if float(f.simtime) - boundary_t2 < 1 + .5 or i < 10:
            continue
        markers = {r: F(round(float(st[i][r][0]) * 1000), 1000) for r in targets if st[i][r][0] is not None}
        if len(markers) != 2:
            continue
        ok = True
        for j in range(i - 10, i + 1):
            for r in targets:
                station, speed = st[j][r]
                expected = markers[r] - targets[r] * (frames[i].simtime - frames[j].simtime)
                if station is None or abs(speed - targets[r]) > F(1, 10) or abs(station - expected) > F(1, 10):
                    ok = False
        if ok:
            return f, markers
    return None

def finish(c, out):
    write_ref(root / c.id / 'prepare.json', out, 'G4_PREPARATION')
    log(event='SCENE', scene=c.id, status=out['status'], reason=out.get('reason'),
        **{k: out.get(k) for k in ('t_E', 't_N', 'D_N', 'T_r', 'ego_front_gap_at_ready', 'npc_front_gap_at_ready')})


if __name__ == '__main__':
    main()
