"""M56 I/O native fixture compile (+ gated A/B), pilot O. Design docs/m56/DESIGN_M56_IO_TOOLING_20261026.md. Own server 2610 only.

Default (no --ab): per PREPARED 'io-v1' scene of one town: compile_fixture (native routes, lane boxes, sections, map
reference, metric pair, reviewed proofs) -> freeze file -> runtime.admit -> the consumer's own response contracts
(_lateral_contract / _reference_response) -> report. NO episode. Duy 2026-10-26: "dựng tooling I/O với pilot O, chỉ chuẩn bị".
--ab additionally runs exactly one A then one B (P5) and REFUSES unless M56_IO_PREREG_APPROVED names the commit of the I/O
recipe prereg Duy approved (recorded in the receipt). Reviews: CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent.
  python -I native-io-ab.py REVISION.json Town06 M56-P-O03 [--ab]
"""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import json, math, os, sys, traceback
sys.path.insert(0, str(Path(__file__).resolve().parent))

from native_v2_common import (NO_RENDER, WORK, WS, body_record, certificates, drivable_union, driving_boxes, load, now,
                              own_server, ownership, plan_rows, policy_maker, reviewer, sha, up, write_ref)
from native_io_common import io_routes, io_geometry, io_npc, io_phase_plans
from native_v2_kit import Kit, q
from m56 import runtime
from m56.catalog import _digest
from m56.evidence import open_run
from m56.geometry import compile_fixture, project_route, world_vertices
from m56.model import (ApprovalBundle, CapabilityProof, CompiledFixture, PolicyBundle, QueryBundle, RuntimeContext, SourceRef,
                       decode_record, encode_record, load_json)
from m56.response import _forward_contract, _lateral_contract, _reference_response, _program

REVISION, TOWN, SCENES = Path(sys.argv[1]), sys.argv[2], sys.argv[3].split(',')
AB = '--ab' in sys.argv[4:]
APPROVED = os.environ.get('M56_IO_PREREG_APPROVED', '')
if AB and not APPROVED:
    sys.exit('REFUSED: --ab needs M56_IO_PREREG_APPROVED=<commit of the I/O recipe prereg Duy approved>')
AB_AUTHORITY = os.environ.get('M56_AB_AUTHORITY', '')  # 2026-11-07: the run's own authority, sealed in the receipt
if AB and not AB_AUTHORITY:
    sys.exit('REFUSED: --ab needs M56_AB_AUTHORITY=<who authorised this A/B, quoted source, erratum/decision commit>')
root = WORK / f"outputs/m56_io_{'ab' if AB else 'compile'}_{TOWN}_{now()}"
root.mkdir(parents=False, exist_ok=False)
log_rows = []


def log(**kw):
    log_rows.append(kw); print(json.dumps(kw, default=str), flush=True)


charter_path = WS / 'native-probe-charter-20261021.md'
charter = SourceRef(str(charter_path), sha(charter_path), charter_path.stat().st_size, '1', 'operator', 'PROBE_CHARTER')
authority = write_ref(root / 'duy-delegation-receipt.json', {
    'source': '[chat] 2026-10-26 Duy: "Tiếp tục dựng tooling I/O với pilot O, chỉ chuẩn bị"',
    'design': 'docs/m56/DESIGN_M56_IO_TOOLING_20261026.md', 'revision': {'path': str(REVISION), 'sha256': sha(REVISION)},
    'reviewer': 'CLAUDE_REVIEW_UNDER_DUY_DELEGATION (not independent); independent review waived by Duy 2026-10-24',
    'stage': 'I/O A/B' if AB else 'I/O fixture compile + admission only (no episode)',
    'io_prereg_approved': APPROVED or None, 'carla_no_rendering_mode': NO_RENDER,
    'ab_authority': AB_AUTHORITY or None,
    'kit_lateral_bound': 'pointwise (post-number, 2026-11-06)' if os.environ.get('M56_IO_KAPPA') == 'pointwise' else 'window-max-sum (io-v1.2)',
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
    routes, rows, cont = io_routes(prep, plain, c.town)
    d = F(rr['catalog_offset_m'])
    # the revision's responses sit on exactly these native routes (switch routes included)
    to = {'TARGET_LANE_CONFIRMED': routes['EGO_TARGET'], 'RETURN_LANE_CONFIRMED': routes['EGO']}
    assert all(_digest(r.route) == _digest(routes['EGO']) and all(_digest(s['route']) == _digest(to[s['event']])
               for s in r.phases.get('reference_switches', ())) for r in c.responses), 'IO_RESPONSE_ROUTES_MISMATCH'
    geo = io_geometry(c, prep, routes, d, plain)
    assert not geo.get('reason'), geo
    body = body_record(prep['bbox'], write_ref(sd / 'a2-bbox.json', prep['bbox'], 'NATIVE_BODY'))
    poses = {k: decode_record('Transform6', v) for k, v in prep['poses'].items()}
    froutes = {'EGO': routes['EGO'], 'NPC': routes['NPC']}
    certs = {role: certificates(froutes[role], body, review, cont) for role in froutes}
    pts = [(t.x, t.y) for r in routes.values() for t in r.transforms]
    center = ((min(p[0] for p in pts) + max(p[0] for p in pts)) / 2, (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2)
    radius = max(math.dist(p, center) for p in pts) + 20.  # the union covers every route point (O routes are ~200 m)
    drivable = drivable_union(m, center, radius, world, froutes)
    dpath = sd / 'drivable-union.wkt'; dpath.write_text(drivable.wkt, encoding='utf-8')
    dref = SourceRef(str(dpath), sha(dpath), dpath.stat().st_size, '1', 'carla-generate-waypoints-0.5m', 'NATIVE_DRIVABLE')
    z_lo, z_hi = geo['z']
    driving = {role: driving_boxes(drivable, froutes[role], z_lo, z_hi) for role in froutes}
    responses = (*c.responses, io_npc(c, routes))
    policies = PolicyBundle('m56-io-fixture', 'f' * 64, {}, {}, {}, (prep_ref,))
    mp = {'town': c.town, 'opendrive_sha256': identity.map}
    boot, wid = f'pid{proc.pid}@{start}', str(world.id)
    binding = _digest({'candidate': c, 'policy': policies, 'routes': froutes, 'bodies': {'EGO': body, 'NPC': body},
                       'poses': poses, 'map': mp, 'boot': boot, 'world': wid})
    from shapely.geometry import MultiPoint
    fp = {r: MultiPoint([(v[0], v[1]) for v in world_vertices(body, poses[r])]).convex_hull for r in poses}
    edge = min(fp[r].distance(drivable.boundary) if drivable.contains(fp[r]) else -1. for r in fp)
    ego_front = max(float(s) for s in (project_route(v, froutes['EGO']) for v in world_vertices(body, poses['EGO']))
                    if not hasattr(s, 'reasons'))
    grounds = {}
    for role in ('EGO', 'NPC'):
        g = (prep.get('grounds') or {}).get(role)
        err = abs(poses[role].z - .01 - g) if g is not None else 1.
        grounds[role] = cap('GROUND:' + role, {'maximum_ground_error_m': up(err + 1e-4, 10 ** 4),
                                               'contact_method': 'world.ground_projection at route start + 1 cm'},
                            (prep_ref,), binding, 'native ground_projection at the spawn point')
    ego = froutes['EGO']
    room = q(float(geo['decision']) - ego_front)
    need = F(math.ceil((prep['ego_front_at_ready'] - ego_front) * 10000), 10000)  # rounded up (adverse)
    caps = (cap('BODY_FIT', {'minimum_road_edge_m': q(edge), 'minimum_body_separation_m': q(fp['EGO'].distance(fp['NPC']))},
                (prep_ref, dref), binding, 'start footprints vs CARLA driving-lane union'),
            # O has no G: the run-in requirement is readiness before the decision. required = G = the probe-2 distance
            # from the spawn front to the front at readiness; available = initial front = spawn front -> O_DECISION.
            cap('RUNIN_ROOM', {'required_m': need, 'available_m': room, 'initial_front_m': room, 'G_m': need},
                (prep_ref,), binding, 'EGO front at spawn vs O_DECISION; readiness distance measured in probe 2'),
            cap('DESTINATION_ROOM', {'exit_to_destination_m': q(float(ego.destination - geo['X'])),
                                     'destination_to_plan_end_m': q(float(ego.arc[-1] - ego.destination))},
                (prep_ref,), binding, 'exit = X; destination = X + 5 m; plan extends 15 m further'))
    topology = {'category': c.category, 'kind': 'lane-change-pass', 'action_regions': geo['regions'],
                'driving_regions': driving, 'drivable_ref': dref, 'lane_geometry': geo['lane_geometry'],
                'map_reference': geo['map_reference'], 'io_axis': geo['axis'], 'io_dlc': frozen_dlc(c)}
    packet = {'region': geo['region'], 'topology': topology, 'proof': (prep_ref, cont, dref), 'G': None,
              'sections': geo['sections'], 'responses': responses, 'pair': geo['pair']}
    queries = QueryBundle(boot, wid, mp, froutes, {'EGO': body, 'NPC': body}, poses, grounds,
                          {'compilation': encode_record(packet)}, caps, (*certs['EGO'], *certs['NPC']), (prep_ref, cont, dref))
    envelope = {'candidate': c, 'queries': queries, 'policy': policies}
    queries = replace(queries, physics={**queries.physics, 'fixture_review': encode_record(review(
        envelope, 'FIXTURE_COMPILE', (prep_ref, cont, dref), ('I/O materialization of the frozen candidate; not independent',)))})
    fixture = compile_fixture(c, queries, policies)
    return fixture, (drivable, dref), rows, prep, raw_prep, geo


def io_policy(fixture, rows, source, fref, npc_gains, ego_gains):
    """policy_maker + the lateral keys the product's stock driver needs for a lane change: fixture_ref (the frozen fixture
    file) and phase_plans (one stock plan per reference switch, io_phase_plans)."""
    base = policy_maker(fixture, rows, review, source, npc_gains, ego_gains)

    def policy_for(response, actor):
        b = dict(base(response, actor).event_specs['stock_binding']); b.pop('review')
        if response.phases.get('reference_switches') or any(s['start_offset_m'] != s['end_offset_m']
                                                            for s in response.profile['segments']):
            b.update(fixture_ref=fref, phase_plans=io_phase_plans(response, rows))
        r = review(b, 'STOCK_FORWARD_BINDING', (source, fref))
        return PolicyBundle('m56-v2', 'f' * 64, {}, {'stock_binding': {**b, 'review': r}}, {}, (source, fref))
    return policy_for


def frozen_dlc(c):
    """Dlc of an O scene: the spec 7.4 catalog parameter when present (O01-O03, bytes unchanged); a fill-catalog scene has
    none, so the length of its frozen EGO A lane-change segment (= 3 vE; io-v1.3 3.a)."""
    if 'Dlc' in c.parameters:
        return c.parameters['Dlc'].values[0]
    a = next(r for r in c.responses if r.actor_role == 'EGO' and r.action_id == 'A')
    return next(s['length_m'] for s in a.profile['segments'] if s['end_offset_m'] != s['start_offset_m'])


def run_scene(c, client, proc, start, world, m, identity):
    sd = root / c.id; sd.mkdir()
    fixture, drivable, rows, prep, raw_prep, geo = compile_scene(c, world, m, identity, proc, start, sd)
    if not isinstance(fixture, CompiledFixture):
        log(event='FIXTURE', scene=c.id, status='BLOCKED_FIXTURE', reasons=list(fixture.reasons)); return
    fref = write_ref(sd / 'fixture-frozen.json', fixture, 'FROZEN_FIXTURE')
    log(event='FIXTURE', scene=c.id, status='FROZEN', sha256=fref.sha256, separation_m=str(geo['separation_m']),
        sections={k: str(v.route_station) for k, v in fixture.sections.items()})
    checks = {}
    for r in fixture.responses:  # the consumer's own frozen-response contracts on the compiled fixture
        try:
            _lateral_contract(r, fixture); _forward_contract(r, fixture)  # lateral + normative (evidence integrity)
            for cause in (_program(r)['initial'], *(t['cause'] for t in _program(r)['transitions'])):
                _reference_response(r, cause)
            checks[f'{r.actor_role}:{r.action_id}'] = 'OK'
        except ValueError as e:
            checks[f'{r.actor_role}:{r.action_id}'] = str(e)
    own = ownership(proc, start, world)
    admission = runtime.admit(fixture, approvals, identity, own)
    log(event='ADMISSION', scene=c.id, status=admission.status, reasons=list(admission.reasons), response_checks=checks)
    if not AB or admission.status != 'ADMITTED' or any(v != 'OK' for v in checks.values()):
        return
    store = open_run(sd / 'run', c.id, own.writer)
    ctx = RuntimeContext(None, identity, own, approvals, admission, store,
                         {'tick_s': F(5), 'cleanup_s': F(15), 'outer_s': F(300), 'rpc_s': F(60)}, 'AB_PAIR', 'RUNNING')
    backend = runtime.bind_owned(ctx)
    qual_path = WORK / 'outputs/m56_native_g4_probe_20261023T135210Z/g4-probe.json'
    qual = SourceRef(str(qual_path), sha(qual_path), qual_path.stat().st_size, '1', 'native', 'NATIVE_QUALIFICATION')
    kit = Kit(authority, fixture, drivable, qual, c.id)
    source = write_ref(sd / 'plan-source.json', {'rule': 'route lane waypoints (road/lane/s) every 2 m; per switch: the '
                                                         'switched lane from its marker'}, 'G4_STOCK_SOURCE')

    def geometry_review(p):
        return review(p, 'CAPABILITY:CONTINUOUS_GEOMETRY', tuple(p['raw_refs']),
                      ('dt 1/20; observed consecutive frames of owned actors; not independent',))
    gains = {k: (None if raw_prep.get(k) is None else tuple(F(g) for g in raw_prep[k])) for k in ('npc_longitudinal', 'ego_longitudinal')}
    frows = {'EGO': rows['EGO'], 'NPC': rows['NPC'], 'EGO_TARGET': rows['EGO_TARGET']}
    backend.bind(fixture, io_policy(fixture, frows, source, fref, gains['npc_longitudinal'], gains['ego_longitudinal']),
                 geometry_review, kit)
    out = runtime.run_ab(replace(ctx, backend=backend), fixture, c.id)
    log(event='AB', scene=c.id, sealed=isinstance(out, tuple), blocked=list(getattr(out, 'blocked', ())) if not isinstance(out, tuple) else [])


def main():
    data = load_json(REVISION)
    scenes = [decode_record('Candidate', c) for c in data['candidates'] if c['town'] == TOWN and c['id'] in SCENES
              and (c['environment'].get('runtime_recipe_v2') or {}).get('recipe') == 'io-v1'
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
    (root / 'io-log.json').write_text(json.dumps(log_rows, indent=1, default=str), encoding='utf-8')
    print('DONE', root)


if __name__ == '__main__':
    main()
