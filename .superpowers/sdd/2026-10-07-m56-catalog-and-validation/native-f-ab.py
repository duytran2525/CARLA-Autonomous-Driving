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
from native_f_common import f_geometry, f_npc, f_routes
from native_v2_kit import Kit, q
from m56 import runtime
from m56.catalog import _digest
from m56.evidence import open_run
from m56.geometry import compile_fixture, project_route, world_vertices
from m56.model import (ApprovalBundle, CapabilityProof, CompiledFixture, PolicyBundle, QueryBundle, RuntimeContext, SourceRef,
                       decode_record, encode_record, load_json)
from m56.response import _forward_contract

REVISION, TOWN, SCENES = Path(sys.argv[1]), sys.argv[2], sys.argv[3].split(',')
AB = '--ab' in sys.argv[4:]
PREREG = os.environ.get('M56_F_PREREG', '')
AB_AUTHORITY = os.environ.get('M56_AB_AUTHORITY', '')
if AB and not (PREREG and AB_AUTHORITY):
    sys.exit('REFUSED: --ab needs M56_F_PREREG=<F prereg commit> and M56_AB_AUTHORITY=<who authorised this A/B, quoted source>')
root = WORK / f"outputs/m56_f_{'ab' if AB else 'compile'}_{TOWN}_{now()}"
root.mkdir(parents=False, exist_ok=False)
log_rows = []


def log(**kw):
    log_rows.append(kw); print(json.dumps(kw, default=str), flush=True)


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
OPS = runtime.READ_OPS + ('SETTINGS', 'LOAD_MAP', 'SPAWN', 'TICK', 'APPLY', 'DESTROY', 'VALIDATE_AB', 'tick', 'observe')
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


def compile_scene(c, world, m, identity, proc, start, sd):
    rr = c.environment['runtime_recipe_v2']
    raw_prep = json.loads(Path(rr['prepare_json']).read_text(encoding='utf-8'))
    prep = {k: (v if k == 'poses' else plain(v)) for k, v in raw_prep.items()}
    assert prep['map_hash'] == identity.map, 'MAP_HASH_CHANGED'
    prep_ref = SourceRef(rr['prepare_json'], sha(rr['prepare_json']), Path(rr['prepare_json']).stat().st_size, '1',
                         'claude-g4', 'G4_PREPARATION')
    routes, rows, cont = f_routes(prep, plain, c.town)
    assert all(_digest(r.route) == _digest(routes['EGO']) for r in c.responses), 'F_RESPONSE_ROUTE_MISMATCH'
    geo = f_geometry(prep, routes, plain)
    assert not geo.get('reason'), geo
    body = body_record(prep['bbox'], write_ref(sd / 'a2-bbox.json', prep['bbox'], 'NATIVE_BODY'))
    poses = {k: decode_record('Transform6', v) for k, v in prep['poses'].items()}
    certs = {role: certificates(routes[role], body, review, cont) for role in routes}
    pts = [(t.x, t.y) for r in routes.values() for t in r.transforms]
    center = ((min(p[0] for p in pts) + max(p[0] for p in pts)) / 2, (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2)
    radius = max(math.dist(p, center) for p in pts) + 20.
    zs = [t.z for r in routes.values() for t in r.transforms]
    streamed = stream_to(world, center[0], center[1], sum(zs) / len(zs))
    if streamed:
        log(event='STREAM_TO', scene=c.id, **streamed)
    drivable = drivable_union(m, center, radius, world, routes)
    dpath = sd / 'drivable-union.wkt'; dpath.write_text(drivable.wkt, encoding='utf-8')
    dref = SourceRef(str(dpath), sha(dpath), dpath.stat().st_size, '1', 'carla-generate-waypoints-0.5m', 'NATIVE_DRIVABLE')
    z_lo, z_hi = geo['z']
    driving = {role: driving_boxes(drivable, routes[role], z_lo, z_hi) for role in routes}
    policies = PolicyBundle('m56-f-fixture', 'f' * 64, {}, {}, {}, (prep_ref,))
    mech = c.environment['mechanism']
    npc = f_npc(mech, c.parameters['vN_char'].values[0], routes['NPC'], _digest(policies))
    mp = {'town': c.town, 'opendrive_sha256': identity.map}
    boot, wid = f'pid{proc.pid}@{start}', str(world.id)
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
    brake = sec['F01_BRAKE_START'].route_station
    need = F(math.ceil((float(prep['markers']['EGO']) - ego_front) * 10000), 10000)  # readiness distance, rounded up
    room = q(float(brake) - ego_front)
    caps = (cap('BODY_FIT', {'minimum_road_edge_m': q(edge), 'minimum_body_separation_m': q(fp['EGO'].distance(fp['NPC']))},
                (prep_ref, dref), binding, 'start footprints vs CARLA driving-lane union'),
            # F has no G: run-in = readiness before the brake-start section (EGO station frame). required = the probe-2
            # readiness distance of the EGO front; available = spawn front -> F01_BRAKE_START.
            cap('RUNIN_ROOM', {'required_m': need, 'available_m': room, 'initial_front_m': room, 'G_m': need},
                (prep_ref,), binding, 'EGO front at spawn vs F01_BRAKE_START; readiness distance measured in probe 2'),
            cap('DESTINATION_ROOM', {'exit_to_destination_m': q(float(ego.destination - sec['F01_END'].route_station)),
                                     'destination_to_plan_end_m': q(float(ego.arc[-1] - ego.destination))},
                (prep_ref,), binding, 'destination = F01_END + body + 10 m (EGO frame); plan extends >= 15 m further'))
    topology = {'category': 'F', 'mechanism': mech, 'kind': 'same-lane-lead-brake', 'driving_regions': driving,
                'drivable_ref': dref}
    packet = {'region': geo['region'], 'topology': topology, 'proof': (prep_ref, cont, dref), 'G': None,
              'sections': sec, 'responses': (*c.responses, npc), 'pair': geo['pair']}
    queries = QueryBundle(boot, wid, mp, routes, {'EGO': body, 'NPC': body}, poses, grounds,
                          {'compilation': encode_record(packet)}, caps, (*certs['EGO'], *certs['NPC']), (prep_ref, cont, dref))
    envelope = {'candidate': c, 'queries': queries, 'policy': policies}
    queries = replace(queries, physics={**queries.physics, 'fixture_review': encode_record(review(
        envelope, 'FIXTURE_COMPILE', (prep_ref, cont, dref), ('F materialization of the frozen candidate; not independent',)))})
    return compile_fixture(c, queries, policies), (drivable, dref), rows, raw_prep


def run_scene(c, client, proc, start, world, m, identity):
    sd = root / c.id; sd.mkdir()
    fixture, drivable, rows, raw_prep = compile_scene(c, world, m, identity, proc, start, sd)
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
    if not AB or admission.status != 'ADMITTED' or any(v != 'OK' for v in checks.values()):
        return
    store = open_run(sd / 'run', c.id, own.writer)
    ctx = RuntimeContext(None, identity, own, approvals, admission, store,
                         {'tick_s': F(5), 'cleanup_s': F(15), 'outer_s': F(1500), 'rpc_s': F(60)}, 'AB_PAIR', 'RUNNING')
    backend = runtime.bind_owned(ctx)
    qual_path = WORK / 'outputs/m56_native_g4_probe_20261023T135210Z/g4-probe.json'
    qual = SourceRef(str(qual_path), sha(qual_path), qual_path.stat().st_size, '1', 'native', 'NATIVE_QUALIFICATION')
    kit = Kit(authority, fixture, drivable, qual, c.id)
    source = write_ref(sd / 'plan-source.json', {'rule': 'route lane waypoints (road/lane/s) every 2 m'}, 'G4_STOCK_SOURCE')

    def geometry_review(p):
        return review(p, 'CAPABILITY:CONTINUOUS_GEOMETRY', tuple(p['raw_refs']),
                      ('dt 1/20; observed consecutive frames of owned actors; not independent',))
    backend.bind(fixture, policy_maker(fixture, rows, review, source), geometry_review, kit)
    out = runtime.run_ab(replace(ctx, backend=backend), fixture, c.id)
    log(event='AB', scene=c.id, sealed=isinstance(out, tuple), blocked=list(getattr(out, 'blocked', ())) if not isinstance(out, tuple) else [])


def main():
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
