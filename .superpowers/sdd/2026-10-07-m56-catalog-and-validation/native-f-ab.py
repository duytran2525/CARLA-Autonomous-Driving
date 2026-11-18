"""M56 A-SEL2 F native fixture compile (+ gated A/B). PLAN_M56_F_NATIVE_TOOLING_20261109.md step 3; PREREG F part 1. F01 only.
Own server 2610 only. Reviews: CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.

Default (no --ab): per PREPARED 'f-v1' scene of one town: compile_fixture (native same-lane routes, F01 sections, axis box
domain, dv1 drivable, reviewed proofs, NPC_COMMON F01 script bound to the fixture policy) -> freeze file -> runtime.admit ->
the consumer's own response contracts (_forward_contract, which runs _f_script_contract for the NPC) -> report. NO episode.
--ab additionally runs exactly one A then one B (P5); it REFUSES unless M56_F_PREREG names the F prereg commit and
M56_AB_AUTHORITY records who authorised the run.
  python -I native-f-ab.py REVISION.json Town13 M56-P-F01-S1 [--ab]
"""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import json, math, os, sys, traceback
sys.path.insert(0, str(Path(__file__).resolve().parent))

from native_v2_common import (NO_RENDER, WORK, WS, body_record, certificates, drivable_union, driving_boxes, load, now,
                              own_server, ownership, policy_maker, reviewer, sha, stream_to, up, write_ref)
from native_f_common import END_SECTION, f_geometry, f_npc, f_routes
KIND = {'F01': 'same-lane-lead-brake', 'F02': 'same-lane-rear-closing', 'F05': 'same-lane-queue-start',
        'F03': 'same-lane-grade-rollback'}
from native_v2_kit import Kit, q
from native_f05_kit import F05Kit
from native_f03_kit import F03Kit
from m56 import runtime
from m56.catalog import _digest
from m56.evidence import open_run
from m56.geometry import compile_fixture, project_route, world_vertices
from m56.model import (ApprovalBundle, CapabilityProof, CompiledFixture, PolicyBundle, QueryBundle, RuntimeContext, SourceRef,
                       decode_record, encode_record, load_json)
from m56.response import _forward_contract

log_rows = []
REVISION = TOWN = SCENES = AB = PROBE_A = root = authority = review = approvals = None
OPS = runtime.READ_OPS + ('SETTINGS', 'LOAD_MAP', 'SPAWN', 'TICK', 'APPLY', 'DESTROY', 'VALIDATE_AB', 'tick', 'observe')


def log(**kw):
    log_rows.append(kw); print(json.dumps(kw, default=str), flush=True)


def init(argv, out_root=None):
    """argv = [REVISION, TOWN, SCENES, (--ab)]; creates the output root and the receipt (never at import)."""
    global REVISION, TOWN, SCENES, AB, PROBE_A, root, authority, review, approvals
    REVISION, TOWN, SCENES = Path(argv[0]), argv[1], argv[2].split(',')
    AB = '--ab' in argv[3:]
    PROBE_A = '--probe-a' in argv[3:]  # F03 pre-registered A-only probe (PREREG F part 2 section 4): not an A/B
    PREREG = os.environ.get('M56_F_PREREG', '')
    AB_AUTHORITY = os.environ.get('M56_AB_AUTHORITY', '')
    if AB and not (PREREG and AB_AUTHORITY):
        sys.exit('REFUSED: --ab needs M56_F_PREREG=<F prereg commit> and M56_AB_AUTHORITY=<who authorised this A/B, quoted source>')
    root = out_root or WORK / f"outputs/m56_f_{'ab' if AB else 'probea' if PROBE_A else 'compile'}_{TOWN}_{now()}"
    root.mkdir(parents=False, exist_ok=False)
    charter_path = WS / 'native-probe-charter-20261021.md'
    charter = SourceRef(str(charter_path), sha(charter_path), charter_path.stat().st_size, '1', 'operator', 'PROBE_CHARTER')
    authority = write_ref(root / 'duy-delegation-receipt.json', {
        'source': '[chat] 2026-11-08 Duy (self-stated): "Claude soạn recipe F", "Claude đổi input F theo thang"',
        'plan': 'docs/m56/PLAN_M56_F_NATIVE_TOOLING_20261109.md', 'revision': {'path': str(REVISION), 'sha256': sha(REVISION)},
        'reviewer': 'CLAUDE_REVIEW_UNDER_DUY_DELEGATION (not independent); independent review waived by Duy 2026-10-24',
        'stage': 'F A/B' if AB else 'F fixture compile + admission only (no episode)', 'f_prereg': PREREG or None,
        'carla_no_rendering_mode': NO_RENDER, 'ab_authority': AB_AUTHORITY or None,
        'm56_code': os.environ.get('M56_CODE', str(WORK))}, 'OPERATOR_RECEIPT')
    review = reviewer(authority)
    approvals = ApprovalBundle((authority, charter), {}, OPS)


def cap(kind, limits, raw, binding, why, method='native-g4-measure-v1'):
    packet = dict(kind=kind, method=method, raw_refs=tuple(raw), uncertainty=F(1, 1000),
                  limits={'materialization_hash': binding, **limits}, status='CORROBORATED')
    return CapabilityProof(**packet, review=review(packet, 'CAPABILITY:' + kind, raw, (why,)))


def plain(x):
    if isinstance(x, dict):
        if set(x) == {'binary64'}:
            return float.fromhex(x['binary64'])
        if set(x) == {'numerator', 'denominator'}:
            return F(x['numerator'], x['denominator'])
        return {k: plain(v) for k, v in x.items()}
    if isinstance(x, list):
        return [plain(v) for v in x]
    return x


def scene_routes(c):
    rr = c.environment['runtime_recipe_v2']
    raw_prep = json.loads(Path(rr['prepare_json']).read_text(encoding='utf-8'))
    prep = {k: (v if k == 'poses' else plain(v)) for k, v in raw_prep.items()}
    return prep, raw_prep, f_routes(prep, plain, c.town)


def native_drivable(world, m, c, routes, sd):
    pts = [(t.x, t.y) for r in routes.values() for t in r.transforms]
    center = ((min(p[0] for p in pts) + max(p[0] for p in pts)) / 2, (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2)
    radius = max(math.dist(p, center) for p in pts) + 20.
    zs = [t.z for r in routes.values() for t in r.transforms]
    streamed = stream_to(world, center[0], center[1], sum(zs) / len(zs))
    if streamed:
        log(event='STREAM_TO', scene=c.id, **streamed)
    drivable = drivable_union(m, center, radius, world, routes)
    dpath = sd / 'drivable-union.wkt'; dpath.write_text(drivable.wkt, encoding='utf-8')
    return drivable, SourceRef(str(dpath), sha(dpath), dpath.stat().st_size, '1', 'carla-generate-waypoints-0.5m', 'NATIVE_DRIVABLE')


def compile_scene(c, identity, boot, wid, sd, drivable_pair, scene=None):
    """CARLA-free given the drivable union (geometry, SourceRef); scene = scene_routes(c)."""
    rr = c.environment['runtime_recipe_v2']
    prep, raw_prep, (routes, rows, cont) = scene or scene_routes(c)
    assert prep['map_hash'] == identity.map, 'MAP_HASH_CHANGED'
    prep_ref = SourceRef(rr['prepare_json'], sha(rr['prepare_json']), Path(rr['prepare_json']).stat().st_size, '1',
                         'claude-g4', 'G4_PREPARATION')
    assert all(_digest(r.route) == _digest(routes['EGO']) for r in c.responses), 'F_RESPONSE_ROUTE_MISMATCH'
    geo = f_geometry(prep, routes, plain)
    assert not geo.get('reason'), geo
    body = body_record(prep['bbox'], write_ref(sd / 'a2-bbox.json', prep['bbox'], 'NATIVE_BODY'))
    poses = {k: decode_record('Transform6', v) for k, v in prep['poses'].items()}
    certs = {role: certificates(routes[role], body, review, cont) for role in routes}
    drivable, dref = drivable_pair
    z_lo, z_hi = geo['z']
    driving = {role: driving_boxes(drivable, routes[role], z_lo, z_hi) for role in routes}
    policies = PolicyBundle('m56-f-fixture', 'f' * 64, {}, {}, {}, (prep_ref,))
    mech = c.environment['mechanism']
    npc = f_npc(mech, c.parameters['vN_char'].values[0] if 'vN_char' in c.parameters else None, routes['NPC'], _digest(policies))
    responses = c.responses
    if mech == 'F03':  # EGO B reverse.policy_hash = this fixture's policy (response._ego_reverse_contract); rehashed
        from native_f_common import hashed
        responses = tuple(hashed(replace(r, phases={**r.phases, 'reverse': {**r.phases['reverse'], 'policy_hash': _digest(policies)}}))
                          if r.action_id == 'B' else r for r in c.responses)
    mp = {'town': c.town, 'opendrive_sha256': identity.map}
    binding = _digest({'candidate': c, 'policy': policies, 'routes': routes, 'bodies': {'EGO': body, 'NPC': body},
                       'poses': poses, 'map': mp, 'boot': boot, 'world': wid})
    from shapely.geometry import MultiPoint
    fp = {r: MultiPoint([(v[0], v[1]) for v in world_vertices(body, poses[r])]).convex_hull for r in poses}
    edge = min(fp[r].distance(drivable.boundary) if drivable.contains(fp[r]) else -1. for r in fp)
    ego_front = max(float(s) for s in (project_route(v, routes['EGO']) for v in world_vertices(body, poses['EGO']))
                    if not hasattr(s, 'reasons'))
    grounds = {}
    for role in ('EGO', 'NPC'):
        g = (prep.get('grounds') or {}).get(role)
        err = abs(poses[role].z - .01 - g) if g is not None else 1.
        grounds[role] = cap('GROUND:' + role, {'maximum_ground_error_m': up(err + 1e-4, 10 ** 4),
                                               'contact_method': 'world.ground_projection at route start + 1 cm'},
                            (prep_ref,), binding, 'native ground_projection at the spawn point')
    ego, sec = routes['EGO'], geo['sections']
    # run-in reference (EGO station frame): F01 the brake-start section; F02 the nominal EGO front at TRIGGER
    mark, mark_name = ((sec['F01_BRAKE_START'].route_station, 'F01_BRAKE_START') if mech == 'F01'
                       else (None, None) if mech == 'F03'  # set below (addendum A2)
                       else (geo['topology_extra']['nominal_front_t0_m'], 'nominal EGO front at TRIGGER'))
    need = F(math.ceil((float(prep['markers']['EGO']) - ego_front) * 10000), 10000)  # readiness distance, rounded up
    if mech == 'F05':  # addendum U: standing queue, no run-in; required = readiness station tolerance 0.1 m, ref F05_END
        mark, mark_name, need = sec['F05_END'].route_station, 'F05_END (standing queue)', F(1, 10)
    if mech == 'F03':  # addendum A2: standing EGO; reference = NPC rear at spawn (EGO frame), exit = EGO front at ready
        mark, mark_name, need = prep['npc_rear_spawn_m'], 'NPC rear at spawn (standing EGO)', F(1, 10)
    room = q(float(mark) - ego_front)
    end_name = END_SECTION.get(mech)
    exit_m = prep['ego_front_ready_m'] if mech == 'F03' else sec[end_name].route_station
    if mech == 'F03':
        end_name = 'the EGO front at readiness'
    caps = (cap('BODY_FIT', {'minimum_road_edge_m': q(edge), 'minimum_body_separation_m': q(fp['EGO'].distance(fp['NPC']))},
                (prep_ref, dref), binding, 'start footprints vs CARLA driving-lane union'),
            # F has no G: run-in = readiness before the mechanism reference (EGO station frame). required = the probe-2
            # readiness distance of the EGO front; available = spawn front -> reference.
            cap('RUNIN_ROOM', {'required_m': need, 'available_m': room, 'initial_front_m': room, 'G_m': need},
                (prep_ref,), binding, f'EGO front at spawn vs {mark_name}; readiness distance measured in probe 2'),
            cap('DESTINATION_ROOM', {'exit_to_destination_m': q(float(ego.destination) - float(exit_m)),
                                     'destination_to_plan_end_m': q(float(ego.arc[-1] - ego.destination))},
                (prep_ref,), binding, f'destination after {end_name} (EGO frame); plan extends >= 15 m further'))
    topology = {'category': 'F', 'mechanism': mech, 'kind': KIND[mech], 'driving_regions': driving,
                'drivable_ref': dref, **geo['topology_extra']}
    packet = {'region': geo['region'], 'topology': topology, 'proof': (prep_ref, cont, dref), 'G': None,
              'sections': sec, 'responses': (*responses, npc), 'pair': geo['pair']}
    def build(caps):
        queries = QueryBundle(boot, wid, mp, routes, {'EGO': body, 'NPC': body}, poses, grounds,
                              {'compilation': encode_record(packet)}, caps, (*certs['EGO'], *certs['NPC']), (prep_ref, cont, dref))
        envelope = {'candidate': c, 'queries': queries, 'policy': policies}
        queries = replace(queries, physics={**queries.physics, 'fixture_review': encode_record(review(
            envelope, 'FIXTURE_COMPILE', (prep_ref, cont, dref), ('F materialization of the frozen candidate; not independent',)))})
        return compile_fixture(c, queries, policies)
    fixture = build(caps)
    if mech == 'F05' and isinstance(fixture, CompiledFixture):  # addendum U: two passes, the stop proof binds pass-1 hashes
        from m56.response import _reverse_recipe_hash
        proof = creep_stop_bound(raw_prep, prep, fixture, sd, prep_ref)
        second = build((*caps, proof))
        assert isinstance(second, CompiledFixture) and _reverse_recipe_hash(second) == _reverse_recipe_hash(fixture), 'F05_RECIPE_HASH_MOVED'
        log(event='CREEP_BOUND', scene=c.id, limits={k: str(v) for k, v in proof.limits.items()}, uncertainty=str(proof.uncertainty))
        fixture = second
    if mech == 'F03' and isinstance(fixture, CompiledFixture):  # PREREG F part 2 section 4: two passes, as F05
        from m56.response import _reverse_recipe_hash
        proof = reverse_stop_bound(raw_prep, prep, fixture, sd)
        second = build((*caps, proof))
        assert isinstance(second, CompiledFixture) and _reverse_recipe_hash(second) == _reverse_recipe_hash(fixture), 'F03_RECIPE_HASH_MOVED'
        log(event='REVERSE_BOUND', scene=c.id, limits={k: str(v) for k, v in proof.limits.items()}, uncertainty=str(proof.uncertainty))
        fixture = second
    return fixture, (drivable, dref), rows, raw_prep


def reverse_stop_bound(raw_prep, prep, fixture, sd):
    """F03 REVERSE_STOP_BOUND (bounded-reverse-stop-v2, response._reverse_inputs): the prepare's four direct-API reverse
    probes of the kernel law on the frozen EGO pose (prepare.json reverse_calibration); body = the runtime-observed EGO
    body; hard 2 m; the raw source is exactly _payload(limits)."""
    from m56.evidence import _payload
    from m56.response import REVERSE_LAWS, _reverse_recipe_hash, _reverse_body_hash
    cal = prep['reverse_calibration']; method = cal['method']
    b = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
    body = decode_record('BodyRecord', raw_prep['observed_bodies']['EGO'])
    limits = {'actor_role': 'EGO', 'response_hash': b.hash, 'route_hash': _digest(b.route), 'body_hash': _reverse_body_hash(body),
              'fixture_recipe_hash': _reverse_recipe_hash(fixture), **REVERSE_LAWS[method], 'hard_limit_m': F(2),
              'stopping_boundary_m': F(cal['stopping_boundary_m']), 'stopping_distance_bound_m': F(cal['stopping_distance_bound_m']),
              'maximum_reverse_speed_mps': F(cal['maximum_reverse_speed_mps'])}
    data = _payload(limits); path = sd / 'reverse-stop-bound.json'
    with open(path, 'xb') as f:
        f.write(data)
    raw = SourceRef(str(path), sha(path), len(data), '1', 'claude-g4', 'NATIVE_CALIBRATION')
    packet = dict(kind='REVERSE_STOP_BOUND', method=method, raw_refs=(raw,), uncertainty=F(cal['uncertainty']), limits=limits,
                  status='CORROBORATED')
    why = ('stop distance / peak speed of 4 direct-API reverse probes (kernel law v2) on the frozen EGO pose + margins (PREREG '
           'F part 2 section 4); a measured bound, not a certificate; Claude review under Duy delegation, not independent')
    return CapabilityProof(**packet, review=review(packet, 'CAPABILITY:REVERSE_STOP_BOUND', (raw,), (why,)))


def creep_stop_bound(raw_prep, prep, fixture, sd, prep_ref):
    """F05 CREEP_STOP_BOUND (bounded-forward-creep-stop-v1, response._creep_stop_proof): the prepare's four creep
    probes on the frozen poses (calibration numbers in prepare.json creep_calibration); body = the runtime-observed EGO body
    of the settle probe (bit-identical across sessions); the raw source is exactly _payload(limits)."""
    from m56.evidence import _payload
    from m56.response import _reverse_recipe_hash, _reverse_body_hash
    cal = prep['creep_calibration']
    b = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
    body = decode_record('BodyRecord', raw_prep['observed_bodies']['EGO'])
    stock = {'lateral': {'K_P': F(39, 20), 'K_I': F(1, 20), 'K_D': F(1, 5)},
             'longitudinal': {'K_P': F(1), 'K_I': F(1, 20), 'K_D': F(0)}, 'dt_s': F(1, 20),
             'max_throttle': F(3, 4), 'max_brake': F(3, 10), 'max_steering': F(4, 5)}
    limits = {'actor_role': 'EGO', 'response_hash': b.hash, 'route_hash': _digest(b.route), 'body_hash': _reverse_body_hash(body),
              'fixture_recipe_hash': _reverse_recipe_hash(fixture), 'stock_config_hash': _digest(stock),
              'target_mps': F(1, 2), 'terminal_brake': F(3, 10), 'hard_limit_m': F(1),
              'stopping_boundary_m': F(cal['stopping_boundary_m']), 'stopping_distance_bound_m': F(cal['stopping_distance_bound_m']),
              'maximum_forward_speed_mps': F(cal['maximum_forward_speed_mps'])}
    data = _payload(limits); path = sd / 'creep-stop-bound.json'
    with open(path, 'xb') as f:
        f.write(data)
    raw = SourceRef(str(path), sha(path), len(data), '1', 'claude-g4', 'NATIVE_CALIBRATION')
    packet = dict(kind='CREEP_STOP_BOUND', method='bounded-forward-creep-stop-v1', raw_refs=(raw,),
                  uncertainty=F(cal['uncertainty']), limits=limits, status='CORROBORATED')
    why = ('stop distance / peak speed of 4 native creep probes on the frozen poses + margins (addendum U); a measured '
           'bound, not a certificate; Claude review under Duy delegation, not independent')
    return CapabilityProof(**packet, review=review(packet, 'CAPABILITY:CREEP_STOP_BOUND', (raw, prep_ref), (why,)))


def run_scene(c, client, proc, start, world, m, identity):
    sd = root / c.id; sd.mkdir()
    scene = scene_routes(c)
    dp = native_drivable(world, m, c, scene[2][0], sd)
    fixture, drivable, rows, raw_prep = compile_scene(c, identity, f'pid{proc.pid}@{start}', str(world.id), sd, dp, scene)
    if not isinstance(fixture, CompiledFixture):
        log(event='FIXTURE', scene=c.id, status='BLOCKED_FIXTURE', reasons=list(fixture.reasons)); return
    fref = write_ref(sd / 'fixture-frozen.json', fixture, 'FROZEN_FIXTURE')
    log(event='FIXTURE', scene=c.id, status='FROZEN', sha256=fref.sha256,
        sections={k: str(v.route_station) for k, v in fixture.sections.items()})
    checks = {}
    for r in fixture.responses:
        try:
            _forward_contract(r, fixture); checks[f'{r.actor_role}:{r.action_id}'] = 'OK'
        except ValueError as e:
            checks[f'{r.actor_role}:{r.action_id}'] = str(e)
    own = ownership(proc, start, world)
    admission = runtime.admit(fixture, approvals, identity, own)
    log(event='ADMISSION', scene=c.id, status=admission.status, reasons=list(admission.reasons), response_checks=checks)
    if not (AB or PROBE_A) or admission.status != 'ADMITTED' or any(v != 'OK' for v in checks.values()):
        return
    if PROBE_A and fixture.domain.topology.get('mechanism') != 'F03':
        return
    store = open_run(sd / ('probe-a' if PROBE_A else 'run'), c.id, own.writer)
    ctx = RuntimeContext(None, identity, own, approvals, admission, store,
                         {'tick_s': F(5), 'cleanup_s': F(15), 'outer_s': F(1500), 'rpc_s': F(60)},
                         'SINGLE_EPISODE' if PROBE_A else 'AB_PAIR', 'RUNNING')
    backend = runtime.bind_owned(ctx)
    qual_path = WORK / 'outputs/m56_native_g4_probe_20261023T135210Z/g4-probe.json'
    qual = SourceRef(str(qual_path), sha(qual_path), qual_path.stat().st_size, '1', 'native', 'NATIVE_QUALIFICATION')
    mech_k = fixture.domain.topology.get('mechanism')
    if mech_k == 'F03':
        kit = F03Kit(authority, fixture, drivable, qual, c.id, b_fields_in_a=PROBE_A)
    else:
        kit = (F05Kit if mech_k == 'F05' else Kit)(authority, fixture, drivable, qual, c.id)
    source = write_ref(sd / 'plan-source.json', {'rule': 'route lane waypoints (road/lane/s) every 2 m'}, 'G4_STOCK_SOURCE')

    def geometry_review(p):
        return review(p, 'CAPABILITY:CONTINUOUS_GEOMETRY', tuple(p['raw_refs']),
                      ('dt 1/20; observed consecutive frames of owned actors; not independent',))
    # f-v1.1: the PID gains the preparation chose (None = stock), exactly as native-io-ab.py
    gains = {k: (None if raw_prep.get(k) is None else tuple(F(g) for g in raw_prep[k])) for k in ('npc_longitudinal', 'ego_longitudinal')}
    backend.bind(fixture, policy_maker(fixture, rows, review, source, gains['npc_longitudinal'], gains['ego_longitudinal']),
                 geometry_review, kit)
    if PROBE_A:  # one EGO-hold episode on the frozen fixture (pre-registered probe), never paired, never an A/B
        ev = runtime.run_episode(replace(ctx, backend=backend), fixture, 'A')
        log(event='PROBE_A', scene=c.id, frames=len(ev.raw), reasons=list(ev.verdict.reasons) if ev.verdict else None,
            store=str(store.root))
        return
    out = runtime.run_ab(replace(ctx, backend=backend), fixture, c.id)
    log(event='AB', scene=c.id, sealed=isinstance(out, tuple), blocked=list(getattr(out, 'blocked', ())) if not isinstance(out, tuple) else [])


def main():
    init(sys.argv[1:])
    data = load_json(REVISION)
    scenes = [decode_record('Candidate', c) for c in data['candidates'] if c['town'] == TOWN and c['id'] in SCENES
              and (c['environment'].get('runtime_recipe_v2') or {}).get('recipe') == 'f-v1'
              and c['environment']['runtime_recipe_v2'].get('status') == 'PREPARED']
    log(event='SCENES', town=TOWN, ids=[c.id for c in scenes], ab=AB)
    with own_server(log) as (client, proc, start):
        world = load(client, TOWN); m = world.get_map()
        identity = runtime.ReadOnlyCarlaBackend(client, ownership(proc, start, world)).identity()
        for c in scenes:
            try:
                run_scene(c, client, proc, start, world, m, identity)
            except Exception as e:  # recorded; a scene is never re-run with other values
                log(event='SCENE_ERROR', scene=c.id, error=repr(e), trace=traceback.format_exc()[-3000:])
    (root / 'f-log.json').write_text(json.dumps(log_rows, indent=1, default=str), encoding='utf-8')
    print('DONE', root)


if __name__ == '__main__':
    main()
