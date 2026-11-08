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
import json, math, os, sys, traceback
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
from native_v2_common import lane_width_region

SIG5 = os.environ.get('M56_SIG5', '') == '1'  # signal-phase v1 erratum 5 (2026-11-08)
E6 = os.environ.get('M56_E6', '') == '1'  # ERRATUM_M56_PREPARE_E6_NPC_APPROACH_20261108 (post-number)
TF2 = os.environ.get('M56_TF2', '') == '1'  # A-SEL2 technical fix 2: keep the cl-v1 a NPC pitch for the phased pose
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


def probe(client, proc, start, world, identity, scene, routes, rows, poses, responses, label, predicate=None, npc_gains=None,
          ego_gains=None):
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
    backend.bind(fixture, policy_maker(fixture, rows, review, source, npc_gains, ego_gains))
    if predicate:
        backend.seal_kit = PhaseObserver(predicate['light'])  # observe-only phase packets, no instrumentation
    ev = runtime.run_episode(replace(ctx, backend=backend), fixture, 'A')
    holds = sum(1 for f in ev.raw for a in f.actors if a.role == 'NPC' and a.commands
                and a.commands[0].cause == 'NPC_TRAFFIC_HOLD')
    log(event='PROBE', scene=scene, label=label, frames=len(ev.raw), npc_hold_frames=holds, predicate=predicate,
        reasons=list(ev.verdict.reasons) if ev.verdict else None)
    LAST_REASONS[:] = list(ev.verdict.reasons) if ev.verdict else []
    return ev.raw


LAST_REASONS = []
# addendum cl-v1 (docs/m56/PREREG_M56_CL_V1_SPAWN_PROBE_20261108.md), two once-only preparation retries:
# (a, addendum A) SPAWN_ERROR of a role in probe 1 -> that role takes the CARLA waypoint pitch at its start (x, y, z,
#     yaw unchanged); the first rule (z lift) is void: a lifted body falls > 0.1 m/s in frame 1 (SETTLE_MOVEMENT);
# (b) probe 1 ends READINESS_NOT_REACHED and never brings the EGO front within G + 1 m of e_entry (T_end missing, product READY_LIMIT_S 15 s) -> every
#     preparation probe of the scene runs with READY_LIMIT_S = LONG_PROBE_S. The A/B runner keeps its own 15 s.
LONG_PROBE_S = 60


def main():
    rev = candidates()
    rev = candidates(('C', 'L', 'M'))
    scenes = [c for c in rev.candidates if c.town == TOWN and c.category in ('C', 'L', 'M')
              and (len(sys.argv) < 3 or c.id in sys.argv[2].split(','))]
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
        from native_v2_common import stream_to  # A-SEL2 large maps: a dormant actor reports a zero bounding box
        _sp0 = m.get_spawn_points()[0].location; stream_to(world, _sp0.x, _sp0.y, _sp0.z)
        car = world.spawn_actor(bp, m.get_spawn_points()[0]); world.tick()
        assert min(car.bounding_box.extent.x, car.bounding_box.extent.y, car.bounding_box.extent.z) > 0, 'BODY_BBOX_ZERO (dormant actor)'
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
    guide = [(t.x, t.y, t.z) for t in v1route.transforms]
    for role in ('EGO', 'NPC'):
        r, ei, got = route_rows(m, c.town, notation[role], want[role], 15. if role == 'EGO' else 15. + 60. * float(vN),
                                guide if role == 'EGO' else None)
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
    component = None
    if not connected and c.category in ('C', 'L'):  # v5 C4 (prereg eda7680): the reviewed component selection rule
        from m56.geometry import select_conflict_component
        chosen = select_conflict_component(overlap, routes['EGO'], routes['NPC'])
        assert not hasattr(chosen, 'reasons'), f'C4_SELECTION_BLOCKED:{chosen.reasons}'
        component = {'selected_boxes': len(chosen[0]), 'unselected_boxes': len(chosen[1]), 'all_boxes': len(overlap)}
        overlap, connected = chosen[0], True
    lo = tuple(min(v[k] for b in overlap for v in b) for k in range(3))
    hi = tuple(max(v[k] for b in overlap for v in b) for k in range(3))
    from itertools import product
    # vertical extent widened by 1 m both ways so the ground-level route crosses the prism cleanly (still encloses
    # every swept conflict box; the xy footprint is exactly the overlap hull)
    region, lane_W, lane_widths = lane_width_region(m, {r_: rows[r_][0] for r_ in rows}, lo, hi)  # V3.2
    if c.category == 'M':  # v4 P3: the domain IS the merge transition box; the conflict = overlap clipped to it
        from native_v2_common import merge_transition_region
        from m56.model import Sweep
        region, lane_widths = merge_transition_region(m, {r_: rows[r_][0] for r_ in rows}, exit_idx['EGO'])
        lane_W = max(lane_widths.values())
        overlap = _overlaps(Sweep(overlap, (), ()), Sweep((region,), (), ()))
        assert overlap, 'M_NO_CONFLICT_IN_TRANSITION'
        connected = _connected_boxes(overlap)
    if not connected:
        raise AssertionError('DISCONNECTED_CONFLICT_REVIEW_REQUIRED (frozen compiler rule; components logged)')
    sections = {role: _derive_box_sections(routes[role], region) for role in routes}
    for role, s in sections.items():
        assert not hasattr(s, 'reasons'), f'SECTIONS_BLOCKED:{role}:{s.reasons}'
    e_entry, n_entry = float(sections['EGO'][0].route_station), float(sections['NPC'][0].route_station)
    log(event='DOMAIN', scene=c.id, connected=connected, e_entry=e_entry, n_entry=n_entry, boxes=len(overlap))
    from native_v2_common import stream_to
    streamed = stream_to(world, (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)  # A-SEL2 large maps
    if streamed:
        log(event='STREAM_TO', scene=c.id, **streamed)
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
    # v6: probe 1 keeps the v5 NPC program. Its route is the long pre-phasing one (before the start and erratum-4 cuts),
    # so curves outside the final route would wrongly block (C05, L01 on 2026-10-26); the prereg defines TURN/PARK on the
    # final frozen route only, and both act after the box exit, i.e. never on the phasing a probe measures.
    v6p = None
    responses = (next(r for r in ego_responses if r.action_id == 'A'), npc_response(c.category, vN, routes['NPC'], v6p))
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
    # v4 P2: phase-predicate wait limit = max(60 s, observed cycle + 2 s), recorded; the runner reads it from the
    # fixture environment (product change after suite 9), and preparation probes apply the same value here.
    wait_s = max(60., cycle['cycle_ticks'] / 20 + 2.) if sig else 60.
    runtime.PHASE_LIMIT_S = wait_s
    runtime.READY_LIMIT_S = 15
    p1 = probe(client, proc, start, world, identity, c.id, routes, rows, poses, responses, 'probe1', pred1)
    cl_v1 = {}
    lifted = [r_ for r_ in ('EGO', 'NPC') if f'SPAWN_ERROR:{r_}' in LAST_REASONS]
    if not p1 and lifted:  # cl-v1 a, addendum A: the lift fell > 0.1 m/s in frame 1 (product SETTLE_MOVEMENT);
        # instead the role keeps x, y, z (ground + 1 cm), yaw and takes the CARLA waypoint pitch at its start
        for r_ in lifted:
            q_ = poses[r_]
            wp = m.get_waypoint(carla.Location(q_.x, q_.y, q_.z))
            pitch = (wp.transform.rotation.pitch + 180.) % 360. - 180.
            cl_v1[r_] = {'pitch_deg': pitch, 'waypoint': [wp.road_id, wp.lane_id, wp.is_junction]}
            poses[r_] = Transform6(q_.x, q_.y, q_.z, _f32(pitch), q_.yaw, 0.)
        log(event='CL_V1_SPAWN_PITCH', scene=c.id, **cl_v1)
        p1 = probe(client, proc, start, world, identity, c.id, routes, rows, poses, responses, 'probe1-pitch', pred1)
    if p1 and 'READINESS_NOT_REACHED' in LAST_REASONS and not any(e_entry - front_station(next(x for x in f.actors if x.role == 'EGO'), routes['EGO']) <= float(G) + 1
                      for f in p1):  # cl-v1 b
        runtime.READY_LIMIT_S = LONG_PROBE_S
        cl_v1['probe_ready_limit_s'] = LONG_PROBE_S
        log(event='CL_V1_LONG_PROBE', scene=c.id, frames_short=len(p1))
        p1 = probe(client, proc, start, world, identity, c.id, routes, rows, poses, responses, 'probe1-long', pred1)
    out = {'scene': c.id, 'town': c.town, 'category': c.category, 'G': G, 'vE': vE, 'vN': vN, 'LrefN': LrefN,
           'e_entry': e_entry, 'n_entry_probe1': n_entry, 'region': region, 'overlap_connected': connected,
           'grounds': grounds, 'bbox': bbox, 'rule': 'prereg v2 + erratum 3 (E6) + signal-phase v1 + v3 + v4 (P1, P2, P3) + v5 (P-NPC, C4)',
           'recipe': 'v3', 'map_hash': identity.map, 'lane_W': lane_W, 'lane_widths': lane_widths,
           'npc_outgoing_wanted_m': 15. + 60. * float(vN),
           'signal': signal, 'cycle': None if cycle is None else {k: v for k, v in cycle.items() if k != 'sequence'},
           'phase_predicate_probe1': pred1, 'phase_wait_limit_s': wait_s, 'conflict_component': component,
           'carla_no_rendering_mode': NO_RENDER, **({'m56_recipe': 'v6'} if V6 else {}), **({'cl_v1': cl_v1} if cl_v1 else {})}
    if not p1:
        out.update(status='BLOCKED_FIXTURE', reason='PROBE1_NO_FRAMES')
        return finish(c, out)
    # v5 P-NPC (prereg eda7680): the first grid entry (entry 0 = stock, probe 1 itself) whose probe 1 has an NPC
    # 2 s window (unheld, > 0.5 m/s, range <= 0.10) that is steady before the NPC must be present (need). EGO keeps
    # the stock PID: an EGO window failure is final. Every grid probe is recorded.
    # v5 erratum 2 (2d27616): when the stock EGO window of probe 1 is not steady, the first EGO grid entry whose probe-1
    # E6 window has range <= 0.10 (NPC stock); then the NPC grid runs with that EGO entry. Every probe is recorded.
    ego_gains, ego_grid = None, []
    plat0 = plateaus(p1, routes, body, e_entry, G, npc_until='last')
    ego_grid.append({'gains': [str(g) for g in NPC_PID_GRID[0]], 'EGO_range': plat0.get('EGO_range')})
    if plat0.get('EGO_range', 1.) > .10:
        for ei, eg in enumerate(NPC_PID_GRID[1:], 1):
            q = probe(client, proc, start, world, identity, c.id, routes, rows, poses, responses, f'probe1-egopid{ei}', pred1,
                      None, eg)
            pq = plateaus(q, routes, body, e_entry, G, npc_until='last') if q else {}
            ego_grid.append({'gains': [str(g) for g in eg], 'EGO_range': pq.get('EGO_range')})
            if q and pq.get('EGO_range', 1.) <= .10:
                ego_gains, p1 = eg, q; break
    out['ego_pid_grid'] = ego_grid
    out['ego_longitudinal'] = None if ego_gains is None else [str(g) for g in ego_gains]
    npc_gains, grid = None, []
    for gi, gains in enumerate(NPC_PID_GRID):
        if gi:
            p1 = probe(client, proc, start, world, identity, c.id, routes, rows, poses, responses, f'probe1-pid{gi}',
                       pred1, gains, ego_gains)
            if not p1:
                grid.append({'gains': [str(g) for g in gains], 'reason': 'PROBE1_NO_FRAMES'}); continue
        boundary_t = float(p1[0].simtime) - .05
        release = boundary_t + float(RELEASE)
        plat1 = plateaus(p1, routes, body, e_entry, G, npc_until='last')
        row = {'gains': [str(g) for g in gains], 'EGO_range': plat1.get('EGO_range'), 'NPC': plat1.get('NPC'),
               'NPC_range': plat1.get('NPC_range'), 'reason': plat1.get('reason')}
        grid.append(row)
        if plat1.get('EGO_range', 1.) > .10:
            break  # EGO stock PID not steady: no NPC gain can fix it
        if plat1.get('NPC') is None:
            continue
        t_E = plat1['T_end'] + plat1['gap_at_T_end'] / plat1['EGO']
        need = t_E - float(LrefN + 5) / (2 * plat1['NPC']) - release
        st = steady_at(p1, 'NPC', plat1['NPC'])
        row['npc_steady_s'], row['need_s'] = (None if st is None else st - release), need
        if st is not None and need >= st - release:
            npc_gains = gains; break
    out['npc_pid_grid'] = grid
    out['npc_longitudinal'] = None if npc_gains is None else [str(g) for g in npc_gains]
    out['probe1'] = plat1
    if plat1.get('reason') or npc_gains is None:
        out.update(status='BLOCKED_FIXTURE', reason=plat1.get('reason') or 'PHASING_INFEASIBLE')
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
    if s0 < 0 and E6:  # erratum E6: extend the NPC approach upstream by the missing room (+20 m) and shift the stations
        extra = -s0 + 20.
        r_new, ei_new, got_new = route_rows(m, c.town, notation['NPC'], 150. + extra, 15. + 60. * float(vN), None)
        a_new = arcs(r_new)
        shift = float(a_new[ei_new]) - float(rows['NPC'][1][exit_idx['NPC']])
        out['e6'] = {'extra_m': extra, 'approach_got_m': got_new, 'shift_m': shift, 's0_before': s0}
        log(event='E6_NPC_APPROACH', scene=c.id, **out['e6'])
        if shift > 0:
            rows['NPC'] = (r_new, a_new); exit_idx['NPC'] = ei_new
            n_entry += shift; s0 += shift
            if sig and sig.get('stop_station') is not None:
                sig['stop_station'] += shift
            out.update(npc_start_station_probe1=s0, n_entry_e6=n_entry)
    if s0 < 0:
        out.update(status='BLOCKED_FIXTURE', reason='PHASING_ROOM')
        return finish(c, out)
    routes_probe1_npc = routes['NPC']
    r, arc_n = rows['NPC']
    k = next(i for i, x in enumerate(arc_n) if float(x) >= s0)
    rows['NPC'] = (r[k:], [x - arc_n[k] for x in arc_n[k:]]); exit_idx['NPC'] -= k
    end = npc_route_end(rows['NPC'], exit_idx['NPC'], vN, region if c.category == 'M' else None)
    out['npc_route_end_e4'] = end
    if end.get('reason'):
        out.update(status='BLOCKED_FIXTURE', reason=end['reason'])
        return finish(c, out)
    if end.get('cut_index') is not None:
        r4, a4 = rows['NPC']; rows['NPC'] = (r4[:end['cut_index'] + 1], a4[:end['cut_index'] + 1])
    cont2 = write_ref(root / c.id / 'routes-v2.json', {k_: v[0] for k_, v in rows.items()}, 'NATIVE_ROUTE')
    for role in ('EGO', 'NPC'):
        r_, a_ = rows[role]
        routes[role] = directed(r_, a_, identity.map, c.town, notation[role], cont2, a_[exit_idx[role]] + 5)
    poses['NPC'], grounds['NPC'] = pose_at(routes['NPC'])
    if TF2 and 'NPC' in cl_v1:  # technical fix 2: the cl-v1 a waypoint pitch also for the phased (probe 2) NPC pose
        q_ = poses['NPC']; wp_ = m.get_waypoint(carla.Location(q_.x, q_.y, q_.z))
        pitch_ = (wp_.transform.rotation.pitch + 180.) % 360. - 180.
        poses['NPC'] = Transform6(q_.x, q_.y, q_.z, _f32(pitch_), q_.yaw, 0.)
        cl_v1['NPC_phased'] = {'pitch_deg': pitch_, 'waypoint': [wp_.road_id, wp_.lane_id, wp_.is_junction]}
        log(event='TF2_NPC_PITCH', scene=c.id, **cl_v1['NPC_phased'])
    v6p = None
    if V6:  # prereg v6 a+d on the final (phased, erratum-4 cut) NPC route
        v6p = v6_npc_program(routes['NPC'], vN, region, 2 * bbox['extent'][0], cut=end.get('cut_index') is not None)
        out['v6_npc_program'] = v6p
        if v6p.get('reason'):
            out.update(status='BLOCKED_FIXTURE', reason=v6p['reason'])
            return finish(c, out)
    responses = (responses[0], npc_response(c.category, vN, routes['NPC'], v6p))
    pred2 = None
    if SIG5 and sig and sig.get('stop_station') is not None and sig['stop_station'] < float(arc_n[k]):
        # signal-phase v1 erratum 5 (docs/m56/ERRATUM_M56_SIGNAL_PHASE_V1_E5_20261108.md): S1 ran on the long probe-1
        # route and chose a light whose stop line lies BEHIND the phased NPC start, so it can never gate the NPC.
        # Re-run S1 with the same criteria on the phased route; stations go back to probe-1 coordinates for S4.
        new = find_light(world, m, rows['NPC'], exit_idx['NPC'], routes['NPC'], n_entry - float(arc_n[k]))
        out['signal_e5'] = {'old': {a_: b_ for a_, b_ in sig.items() if a_ != 'actor'}, 'phased_start_m': float(arc_n[k]),
                            'new': new and {a_: b_ for a_, b_ in new.items() if a_ != 'actor'}}
        log(event='SIGNAL_E5', scene=c.id, **out['signal_e5'])
        if new is None:
            out.update(status='BLOCKED_FIXTURE', reason='SIGNAL_E5_NO_LIGHT')
            return finish(c, out)
        new['stop_station'] += float(arc_n[k])
        cycle = observe_cycle(world, new['actor'])
        if cycle.get('reason'):
            out.update(status='BLOCKED_FIXTURE', reason=cycle['reason'])
            return finish(c, out)
        sig = new
        out['signal'] = {**signal, 'NPC': {a_: b_ for a_, b_ in new.items() if a_ != 'actor'}}
        out['cycle'] = {a_: b_ for a_, b_ in cycle.items() if a_ != 'sequence'}
        wait_s = max(60., cycle['cycle_ticks'] / 20 + 2.)
        runtime.PHASE_LIMIT_S = wait_s
        out['phase_wait_limit_s'] = wait_s
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
        unique = lambda j: sum(1 for x in seq if x == seq[(g0 - j) % C]) == 1
        old_rule = 'UNIQUE' if unique(kk) else 'SIGNAL_ANCHOR_AMBIGUOUS'  # old S4 rule, reported (erratum 4)
        # erratum 4 (7374ed7): nearest earlier unique tick k' >= k, green still >= 1 s before t_in
        k2 = next((j for j in range(kk, round(20 * t_in) - 20 + 1) if unique(j)), None)
        out.update(t_in=t_in, t_out=t_out, anchor_ticks_before_green=kk, anchor_old_rule=old_rule, anchor_k2=k2)
        if k2 is None:
            out.update(status='BLOCKED_FIXTURE', reason='SIGNAL_ANCHOR_AMBIGUOUS' if unique(kk) is False else
                       'SIGNAL_TIMING_INFEASIBLE')
            return finish(c, out)
        pred2 = dict(seq[(g0 - k2) % C])
        green_end = (t_in - 2 - (k2 - kk) / 20) + (cycle['N_G'] + cycle['N_Y']) / 20
        out.update(phase_predicate=pred2, green_window_end=green_end)
        if t_out > green_end - 1:
            out.update(status='BLOCKED_FIXTURE', reason='SIGNAL_TIMING_INFEASIBLE')
            return finish(c, out)
    p2 = probe(client, proc, start, world, identity, c.id, routes, rows, poses, responses, 'probe2', pred2, npc_gains, ego_gains)
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


def npc_route_end(rows_arc, exit_index, vN, region=None, budget=2.5, window=10., margin=1.):
    """v5 erratum 4: s* = first station after the NPC destination with vN^2 * kappa > budget (kappa = |dyaw| over the
    neighbouring rows, as native_v2_kit.Kit.kappa); the route ends at s* - window - margin, which must be >= destination
    + 5 m, else NPC_ROUTE_CURVATURE. Destination = junction exit + 5 m (M: also >= transition-box exit + 5 m)."""
    rows, arc = rows_arc
    a = [float(x) for x in arc]
    dest = a[exit_index] + 5.
    if region is not None:
        from m56.geometry import _derive_box_sections
        from native_v2_common import directed
        secs = _derive_box_sections(directed(rows, arc, 'e4', 'e4', '0/-1', (), F(str(round(dest, 3)))), region)
        if not hasattr(secs, 'reasons'):
            dest = max(dest, float(secs[1].route_station) + 5.)
    v2 = float(vN) ** 2
    first = None
    for i in range(1, len(rows) - 1):
        if a[i] <= dest:
            continue
        kap = abs(math.radians((rows[i + 1]['yaw'] - rows[i - 1]['yaw'] + 180) % 360 - 180)) / (a[i + 1] - a[i - 1])
        if v2 * kap > budget:
            first = a[i]; break
    if first is None:
        return {'rule': 'erratum 4', 'destination_m': dest, 'curve_station_m': None, 'cut_index': None}
    s_end = first - window - margin
    if s_end < dest + 5.:
        return {'rule': 'erratum 4', 'destination_m': dest, 'curve_station_m': first, 'reason': 'NPC_ROUTE_CURVATURE'}
    cut = max(i for i, x in enumerate(a) if x <= s_end)
    return {'rule': 'erratum 4', 'destination_m': dest, 'curve_station_m': first, 'route_end_m': a[cut], 'cut_index': cut}


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


def plateaus(frames, routes, body, e_entry, G, npc_until='T_end'):
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
    v = [float(_speed(next(x for x in f.actors if x.role == 'EGO').velocity)) for f in frames
         if t_end - 2 - 1e-9 <= float(f.simtime) <= t_end + 1e-9]
    out['EGO'] = sum(v) / len(v); out['EGO_range'] = max(v) - min(v)
    if max(v) - min(v) > .10:
        out['reason'] = 'READINESS_NOT_STEADY'
    # v4 P1 (ccea1cc): the NPC plateau is the mean of the LATEST 2 s NPC window (unheld, range <= 0.10) ending no
    # later than `npc_until` (probe 1: its last frame; probe 2: the EGO T_end); none -> READINESS_NOT_STEADY.
    # The E6 value of the old rule (NPC over the EGO window) is kept for reporting.
    vo = [float(_speed(next(x for x in f.actors if x.role == 'NPC').velocity)) for f in frames
          if t_end - 2 - 1e-9 <= float(f.simtime) <= t_end + 1e-9]
    out['NPC_old_rule'] = sum(vo) / len(vo); out['NPC_old_rule_range'] = max(vo) - min(vo)
    until = float(frames[-1].simtime) if npc_until == 'last' else t_end
    rows = [(float(f.simtime), next(x for x in f.actors if x.role == 'NPC')) for f in frames]
    best = None
    for t_hi, _ in rows:
        if t_hi > until + 1e-9:
            break
        w = [(t, a) for t, a in rows if t_hi - 2 - 1e-9 <= t <= t_hi + 1e-9]
        if rows[0][0] > t_hi - 2 + 1e-9:
            continue
        sp = [float(_speed(a.velocity)) for _, a in w]
        held = any(a.commands and a.commands[0].cause == 'NPC_TRAFFIC_HOLD' for _, a in w)
        if not held and max(sp) - min(sp) <= .10 and min(sp) > .5:
            best = (t_hi, sum(sp) / len(sp), max(sp) - min(sp))
    if best is None:
        out['NPC'] = None; out['reason'] = 'READINESS_NOT_STEADY'
    else:
        out['NPC_window_end'], out['NPC'], out['NPC_range'] = best
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
