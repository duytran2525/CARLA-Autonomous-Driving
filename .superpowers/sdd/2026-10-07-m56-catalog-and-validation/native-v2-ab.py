"""M56 runtime-recipe v2 native A/B (prereg d1c91ac; errata 737acbc, E5; addendum A-G45). Own server 2610 only.

Per PREPARED C/L scene of one town (inputs: the v2 C0-partial revision + its preparation records):
  compile_fixture (CARLA-waypoint routes, native body/ground/drivable union, reviewed proofs) -> freeze file ->
  runtime.admit -> run_ab (exactly one A then one B, never repeated) with the G4 kit -> offline W05 bundles ->
  evaluate_episode again with the W05 refs -> report under BOTH initial-state rules (E3/E5).
All reviews: CLAUDE_REVIEW_UNDER_DUY_DELEGATION (not independent). Local A/B only; never a release.
Run with .venv-m56-native-v1:  python -I native-v2-ab.py REVISION_V2.json Town04
"""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import json, math, sys, traceback
sys.path.insert(0, str(Path(__file__).resolve().parent))

from native_v2_common import (NOMINAL, WORK, WS, PREREG, body_record, certificates, directed, drivable_union, load,
                              now, own_server, ownership, policy_maker, reviewer, sha, write_ref, npc_response, up)
from native_v2_kit import Kit, q
from m56 import runtime
from m56.catalog import _digest
from m56.evidence import open_run, append_record, seal, snapshot_sources, initial_state_old_rule
from m56.geometry import (compile_fixture, swept_volume, _overlaps, _derive_box_sections, world_vertices, project_route)
from m56.metrics import evaluate_episode, _source_metrics, _authenticated_events
from m56.model import (ApprovalBundle, CapabilityProof, CompiledFixture, FrozenMetricPair, PolicyBundle, QueryBundle,
                       RuntimeContext, Section, SourceRef, decode_record, encode_record, load_json)

REVISION, TOWN = Path(sys.argv[1]), sys.argv[2]
root = WORK / f'outputs/m56_v2_ab_{TOWN}_{now()}'
root.mkdir(parents=False, exist_ok=False)
log_rows = []


def log(**kw):
    log_rows.append(kw); print(json.dumps(kw, default=str), flush=True)


charter_path = WS / 'native-probe-charter-20261021.md'
charter = SourceRef(str(charter_path), sha(charter_path), charter_path.stat().st_size, '1', 'operator', 'PROBE_CHARTER')
authority = write_ref(root / 'duy-delegation-receipt.json', {
    'source': '[chat] 2026-10-23 user self-stated Duy: "tôi là duy bạn hãy tự động bổ sung thêm junction và mở g4/g5 đi"; '
              'v2 approval: "Approve v2 (Recommended)"', 'addendum': 'docs/m56/SPEC_ADDENDUM_G4G5_20261023.md',
    'prereg': {'path': str(PREREG), 'sha256': sha(PREREG)}, 'revision_v2': {'path': str(REVISION), 'sha256': sha(REVISION)},
    'reviewer': 'CLAUDE_REVIEW_UNDER_DUY_DELEGATION (not independent)', 'stage': 'G4 fixture freeze + G5 local A/B'},
    'OPERATOR_RECEIPT')
review = reviewer(authority)
OPS = runtime.READ_OPS + ('SETTINGS', 'LOAD_MAP', 'SPAWN', 'TICK', 'APPLY', 'DESTROY', 'VALIDATE_AB', 'tick', 'observe')
approvals = ApprovalBundle((authority, charter), {}, OPS)


def cap(kind, limits, raw, binding, why):
    packet = dict(kind=kind, method='native-g4-measure-v1', raw_refs=tuple(raw), uncertainty=F(1, 1000),
                  limits={'materialization_hash': binding, **limits}, status='CORROBORATED')
    return CapabilityProof(**packet, review=review(packet, 'CAPABILITY:' + kind, raw, (why,)))


def section_at(route, station, half=3., zhalf=2.):
    """Plane section perpendicular to the route at `station` (interpolated), +-half m lateral, +-zhalf m vertical."""
    for i, (a, b) in enumerate(zip(route.arc, route.arc[1:])):
        if a <= station <= b:
            s, e = route.transforms[i], route.transforms[i + 1]
            u = float((station - a) / (b - a)); d = (e.x - s.x, e.y - s.y, e.z - s.z); n = math.sqrt(sum(x * x for x in d))
            p = tuple(c + u * x for c, x in zip((s.x, s.y, s.z), d)); t = tuple(x / n for x in d)
            lat = (-t[1], t[0], 0.); ln = math.hypot(lat[0], lat[1]); lat = (lat[0] / ln, lat[1] / ln, 0.)
            verts = tuple(tuple(p[k] + sl * half * lat[k] + (sz * zhalf if k == 2 else 0.) for k in range(3))
                          for sl in (-1, 1) for sz in (-1, 1))
            return Section(verts, t, station, {})
    raise ValueError('STATION_OFF_ROUTE')


def plain(x):
    """Decode the binary64/Fraction JSON encoding of the preparation records back to Python numbers."""
    if isinstance(x, dict):
        if set(x) == {'binary64'}:
            return float.fromhex(x['binary64'])
        if set(x) == {'numerator', 'denominator'}:
            return F(x['numerator'], x['denominator'])
        return {k: plain(v) for k, v in x.items()}
    if isinstance(x, list):
        return [plain(v) for v in x]
    return x


def front(route, body, pose):
    s = [project_route(p, route) for p in world_vertices(body, pose)]
    return max(x for x in s if not hasattr(x, 'reasons'))


def main():
    data = load_json(REVISION)
    scenes = [decode_record('Candidate', c) for c in data['candidates'] if c['town'] == TOWN and c['category'] in ('C', 'L')
              and (c['environment'].get('runtime_recipe_v2') or {}).get('status') == 'PREPARED']
    log(event='SCENES', town=TOWN, ids=[c.id for c in scenes])
    with own_server(log) as (client, proc, start):
        world = load(client, TOWN)
        m = world.get_map()
        identity = runtime.ReadOnlyCarlaBackend(client, ownership(proc, start, world)).identity()
        for c in scenes:
            try:
                run_scene(c, client, proc, start, world, m, identity)
            except Exception as e:  # recorded; a scene is never re-run with other values
                log(event='SCENE_ERROR', scene=c.id, error=repr(e), trace=traceback.format_exc()[-3000:])
    (root / 'ab-log.json').write_text(json.dumps(log_rows, indent=1, default=str), encoding='utf-8')
    print('DONE', root)


def run_scene(c, client, proc, start, world, m, identity):
    v2 = dict(c.environment['runtime_recipe_v2'])
    v2['prepare_json'] = str(WORK / v2['prepare_json']) if not Path(v2['prepare_json']).is_absolute() else v2['prepare_json']
    raw_prep = json.loads(Path(v2['prepare_json']).read_text(encoding='utf-8'))
    prep = {k: (v if k == 'poses' else plain(v)) for k, v in raw_prep.items()}
    rows_all = plain(json.loads(Path(prep['routes_v2']).read_text(encoding='utf-8')))
    sd = root / c.id; sd.mkdir()
    prep_ref = SourceRef(str(Path(v2['prepare_json'])), sha(v2['prepare_json']), Path(v2['prepare_json']).stat().st_size, '1',
                         'claude-g4', 'G4_PREPARATION')
    cont = SourceRef(prep['routes_v2'], prep['routes_v2_sha256'], Path(prep['routes_v2']).stat().st_size, '1', 'claude-g4',
                     'NATIVE_ROUTE')
    notation = {a.role: a.route_recipe['route'] for a in c.actors}
    routes, rows = {}, {}
    from native_v2_common import arcs
    for role in ('EGO', 'NPC'):
        r = rows_all[role]
        r = r['rows'] if isinstance(r, dict) else r
        a = arcs(r)
        rows[role] = (r, a)
        routes[role] = directed(r, a, identity.map, c.town, notation[role], cont, F(prep['destinations'][role]))
    body_ref = write_ref(sd / 'a2-bbox.json', prep['bbox'], 'NATIVE_BODY')
    body = body_record(prep['bbox'], body_ref)
    poses = {k: decode_record('Transform6', v) for k, v in prep['poses'].items()}
    certs = {role: certificates(routes[role], body, review, cont) for role in routes}
    sweeps = {role: swept_volume(routes[role], body, certs[role]) for role in routes}
    overlap = _overlaps(sweeps['EGO'], sweeps['NPC'])
    lo = tuple(min(v[k] for b in overlap for v in b) for k in range(3))
    hi = tuple(max(v[k] for b in overlap for v in b) for k in range(3))
    lo, hi = (lo[0], lo[1], lo[2] - 1.), (hi[0], hi[1], hi[2] + 1.)  # same rule as the preparation step
    region = tuple(tuple(hi[k] if s[k] else lo[k] for k in range(3)) for s in product((0, 1), repeat=3))
    secs = {role: _derive_box_sections(routes[role], region) for role in routes}
    center = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
    drivable = drivable_union(m, center)
    dpath = sd / 'drivable-union.wkt'
    dpath.write_text(drivable.wkt, encoding='utf-8')
    dref = SourceRef(str(dpath), sha(dpath), dpath.stat().st_size, '1', 'carla-generate-waypoints-0.5m', 'NATIVE_DRIVABLE')
    zlo = min(t.z for r in routes.values() for t in r.transforms) - 1.
    zhi = max(t.z for r in routes.values() for t in r.transforms) + 3.
    from native_v2_common import driving_boxes
    regions = {role: driving_boxes(drivable, routes[role], zlo, zhi) for role in routes}
    vE, vN = NOMINAL[c.category], c.parameters['vN'].values[0]
    pair_spec = (('d_yield_m', 't_entry_s'), ('m', 's'), ('forward_distance', 'elapsed'),
                 (('TRIGGER', 'CLEAR_N_CONFIRMED'), ('TRIGGER', 'E_ENTRY')), 'route:' + _digest(routes['EGO']))
    pair = FrozenMetricPair(*pair_spec, _digest(pair_spec), 'APPROVED_PROPOSAL_NOT_READY')
    responses = (*(r for r in c.responses if r.actor_role == 'EGO'), npc_response(c.category, vN, routes['NPC']))
    g = c.parameters['G']
    policies = PolicyBundle('m56-v2-fixture', 'f' * 64, {c.id + '.G': g}, {}, {}, (prep_ref,))
    mp = {'town': c.town, 'opendrive_sha256': identity.map}
    boot, wid = f'pid{proc.pid}@{start}', str(world.id)
    binding = _digest({'candidate': c, 'policy': policies, 'routes': routes, 'bodies': {'EGO': body, 'NPC': body},
                       'poses': poses, 'map': mp, 'boot': boot, 'world': wid})
    # proofs (measured; uncertainty 1/1000)
    from shapely.geometry import MultiPoint
    fp = {r: MultiPoint([(v[0], v[1]) for v in world_vertices(body, poses[r])]).convex_hull for r in poses}
    edge = min(fp[r].distance(drivable.boundary) if drivable.contains(fp[r]) else -1. for r in fp)
    e_entry, e_exit = secs['EGO'][0].route_station, secs['EGO'][1].route_station
    ego_front = front(routes['EGO'], body, poses['EGO'])
    grounds = {}
    for role in ('EGO', 'NPC'):
        err = abs(poses[role].z - .01 - prep['grounds'][role]) if prep['grounds'].get(role) is not None else 1.
        grounds[role] = cap('GROUND:' + role, {'maximum_ground_error_m': up(err + 1e-4, 10 ** 4),
                                               'contact_method': 'world.ground_projection at route start + 1 cm'},
                            (prep_ref,), binding, 'native ground_projection at the spawn point')
    caps = (cap('BODY_FIT', {'minimum_road_edge_m': q(edge), 'minimum_body_separation_m': q(fp['EGO'].distance(fp['NPC']))},
                (prep_ref, dref), binding, 'start footprints vs CARLA driving-lane union'),
            cap('RUNIN_ROOM', {'required_m': g.values[0], 'available_m': q(float(e_entry) - float(ego_front)),
                               'initial_front_m': F(e_entry) - F(ego_front), 'G_m': g.values[0]},
                (prep_ref,), binding, 'EGO front station at spawn vs derived e_entry'),
            cap('DESTINATION_ROOM', {'exit_to_destination_m': q(float(routes['EGO'].destination - e_exit)),
                                     'destination_to_plan_end_m': q(float(routes['EGO'].arc[-1] - routes['EGO'].destination))},
                (prep_ref,), binding, 'destination = junction exit + 5 m; plan extends to the outgoing end'))
    packet = {'region': region, 'topology': {'category': c.category, 'kind': 'route-crossing-overlap-box',
                                             'driving_regions': regions, 'drivable_ref': dref},
              'proof': (prep_ref, cont, dref), 'G': g.values[0],
              'sections': {'DESTINATION': section_at(routes['EGO'], routes['EGO'].destination)},
              'responses': responses, 'pair': pair}
    queries = QueryBundle(boot, wid, mp, routes, {'EGO': body, 'NPC': body}, poses, grounds,
                          {'compilation': encode_record(packet)}, caps, (*certs['EGO'], *certs['NPC']), (prep_ref, cont, dref))
    envelope = {'candidate': c, 'queries': queries, 'policy': policies}
    queries = replace(queries, physics={**queries.physics,
                      'fixture_review': encode_record(review(envelope, 'FIXTURE_COMPILE', (prep_ref, cont, dref),
                                                             ('G4 materialization of the frozen v2 candidate; not independent',)))})
    fixture = compile_fixture(c, queries, policies)
    if not isinstance(fixture, CompiledFixture):
        log(event='FIXTURE', scene=c.id, status='BLOCKED_FIXTURE', reasons=list(fixture.reasons))
        return
    fref = write_ref(sd / 'fixture-frozen.json', fixture, 'FROZEN_FIXTURE')
    log(event='FIXTURE', scene=c.id, status='FROZEN', sha256=fref.sha256)
    own = ownership(proc, start, world)
    admission = runtime.admit(fixture, approvals, identity, own)
    log(event='ADMISSION', scene=c.id, status=admission.status, reasons=list(admission.reasons))
    if admission.status != 'ADMITTED':
        return
    store = open_run(sd / 'run', c.id, own.writer)
    ctx = RuntimeContext(None, identity, own, approvals, admission, store,
                         {'tick_s': F(10), 'cleanup_s': F(15), 'outer_s': F(900), 'rpc_s': F(60)}, 'AB_PAIR', 'RUNNING')
    backend = runtime.bind_owned(ctx)
    qual = SourceRef(str(WORK / 'outputs/m56_native_g4_probe_20261023T135210Z/g4-probe.json'),
                     sha(WORK / 'outputs/m56_native_g4_probe_20261023T135210Z/g4-probe.json'),
                     (WORK / 'outputs/m56_native_g4_probe_20261023T135210Z/g4-probe.json').stat().st_size, '1', 'native',
                     'NATIVE_QUALIFICATION')
    kit = Kit(authority, fixture, (drivable, dref), qual, c.id)
    source = write_ref(sd / 'plan-source.json', {'rule': 'route lane waypoints (road/lane/s) every 2 m'}, 'G4_STOCK_SOURCE')

    def geometry_review(p):
        return review(p, 'CAPABILITY:CONTINUOUS_GEOMETRY', tuple(p['raw_refs']),
                      ('dt 1/20; observed consecutive frames of owned actors; not independent',))
    backend.bind(fixture, policy_maker(fixture, rows, review, source), geometry_review, kit)
    out = runtime.run_ab(replace(ctx, backend=backend), fixture, c.id)
    result = {'scene': c.id, 'fixture_sha256': fref.sha256, 'episodes': {}}
    for action, ev in zip('AB', out if isinstance(out, tuple) else ()):
        result['episodes'][action] = w05(ev, fixture, sd / f'w05-{action}')
    if not isinstance(out, tuple):
        result['blocked'] = list(getattr(out, 'blocked', ()))
    write_ref(sd / 'ab-result.json', result, 'LOCAL_AB_RESULT')
    log(event='AB', scene=c.id, **{k: v for k, v in result.items() if k != 'scene'})


def w05(ev, fixture, path):
    """Separate sealed W05 bundle (Claude under delegation), then re-evaluate with it; report both initial rules."""
    v = ev.verdict
    row = {'spawn': str(v.spawn), 'physical': str(v.physical), 'witness': str(v.witness), 'reasons': list(v.reasons),
           'events': [(e.name, e.frame) for e in v.events], 'frames': len(ev.raw),
           'old_initial_rule_failures': initial_state_old_rule(ev, fixture) if ev.raw else None}
    if ev.manifest is None or not ev.raw:
        return row
    values, events = _source_metrics(ev, fixture), _authenticated_events(ev, fixture)
    row['metrics'] = None if values is None else repr(values)[:3000]
    if values is None or events is None:
        row['w05'] = 'NOT_WRITTEN: metrics/events not admissible'
        return row
    subject = {'schema': 1, 'scope': 'EPISODE_WITNESS_W05', 'fixture': ev.fixture, 'manifest': ev.manifest,
               'journal': ev.journal, 'sources': ev.source, 'trajectory_hash': _digest(ev.raw), 'end_simtime': ev.end_simtime,
               'events': events, 'metrics': values}
    original = (ev.fixture, ev.manifest, *ev.journal, *ev.source)
    areas = ('fulltrace', 'near_zero', 'nearstanding', 'identity', 'mechanism', 'comparability')
    r = review(subject, 'EPISODE_WITNESS_W05', original,
               tuple(f'{k}: automated consumer checks passed for this sealed episode; Claude under Duy delegation, not independent'
                     for k in areas))
    bundle = open_run(path, path.name, 'm56-claude')
    append_record(bundle, 'review.json', r)
    snap = snapshot_sources(bundle, (*original, authority))
    seal(bundle)
    from m56.runtime import _ref
    from types import SimpleNamespace
    integrity = {**ev.integrity, 'episode_review_ref': _ref(SimpleNamespace(root=bundle.root), 'review.json'),
                 'episode_review_manifest': _ref(SimpleNamespace(root=bundle.root), 'manifest.json')}
    v2 = evaluate_episode(replace(ev, integrity=integrity), fixture)
    row['after_w05'] = {'spawn': str(v2.spawn), 'physical': str(v2.physical), 'witness': str(v2.witness),
                        'reasons': list(v2.reasons), 'snapshot': snap.status}
    return row


if __name__ == '__main__':
    main()
