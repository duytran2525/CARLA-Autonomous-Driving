"""Build and freeze C0 PARTIAL v2 (runtime-recipe v2, prereg d1c91ac; errata 737acbc, E5).

The v1 revision cannot be re-decoded (I/O fill candidates carry parameter 'k' with unit 'index', which the model
schema rejects; finding 2026-10-23), so the v1 candidates are rebuilt in memory by the SAME catalog-recipes code path
and checked byte-for-byte against the frozen v1 file. Then only the 16 C/L candidates get the v2 runtime recipe:
  environment.readiness (targets_mps, markers_m) and environment.runtime_recipe_v2 (status, preparation record),
  NPC actor: destination on the v2 route and the v2 start (route cut) in its route_recipe.
Candidates whose preparation is BLOCKED keep their v1 content plus runtime_recipe_v2.status = BLOCKED_* (reason).
Run (main venv):  python -I native-v2-revision.py OUTDIR PREPARE_DIR [PREPARE_DIR ...]
"""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import glob, hashlib, importlib.util, json, sys

here = Path(__file__).resolve().parent
sys.path[:0] = [str(here), 'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1']
spec = importlib.util.spec_from_file_location('cr', here / 'catalog-recipes.py'); cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)
from m56.catalog import _digest, _site_digest, freeze_c0, review_sites  # noqa: E402
from m56.model import CandidateRevision, IdentityMethod, ReviewRecord, SiteRecord, encode_record  # noqa: E402

WORK = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1')
V1 = WORK / 'outputs/m56_c0_partial_20261022T120227Z/c0-partial-frozen-revision.json'
FILL = WORK / 'outputs/m56_fill20_v1_20261022T103601Z.json'
EV1 = WORK / 'outputs/m56_site_identity_evidence_20261022T104350Z.json'
EV2 = WORK / 'outputs/m56_site_identity_all_20261022T104431Z.json'
PREREG = WORK / 'docs/m56/PREREG_M56_RUNTIME_RECIPE_V2_20261023.md'
REVIEWER = 'CLAUDE_REVIEW_UNDER_DUY_DELEGATION'


def v1_candidates(out):
    b = cr.st.build(FILL, out)
    weather = {}
    for f in sorted(glob.glob(str(WORK / 'outputs/m56_native_weather_*/weather-light.json'))):
        weather.update(json.loads(Path(f).read_text(encoding='utf-8')))
    xodr = {t: v['opendrive_sha256'] for t, v in weather.items()}
    done = []
    for c in (c for c in (*b['base'].candidates, *b['additions']) if c.id not in cr.EXCLUDE):
        if c.category in 'CLM':
            dest, responses, flags, _ = cr.junction_recipe(c, xodr[c.town])
        elif c.category in 'IO':
            dest, responses, flags, _ = cr.io_recipe(c, xodr[c.town])
        else:
            dest, responses, flags, _ = cr.f_recipe(c, xodr[c.town])
        actors = tuple(replace(a, destination=dest.get(a.role), pose=None,
                               pose_recipe={'pose': 'PENDING_RUNTIME_QUERY', 'at': 'route start (arc 0) + rest height + 1 cm'})
                       for a in c.actors)
        w = weather[c.town]
        env = {**{k: v for k, v in c.environment.items() if k not in ('weather', 'light', 'weather_light')},
               'weather': w['weather'], 'light': w['light'], 'recipe_flags': tuple(flags)}
        done.append(replace(c, actors=actors, responses=responses, environment=env))
    done = [c for c in done if c.id not in cr.EXCLUDE_AFTER_RECIPE]
    m01_path = out / 'm01-r2-evidence.json'
    m01_path.write_text(json.dumps({'candidate': 'M56-P-M01', 'junction': 459, 'town': 'Town04', 'target_lane': [2, 1],
                                    'mainflow_dheading_deg': 0.0, 'branch_dheading_deg': -22.5,
                                    'rule': 'prereg R2 (dd2954c), applied to all M by Duy 2026-10-22'}, indent=1), encoding='utf-8')
    m01_ref = replace(cr.st.ref(m01_path, 'CATEGORY_EVIDENCE'), method='branch-to-mainflow-geometry-topology')
    for i, c in enumerate(done):
        if c.id == 'M56-P-M01':
            rv = ReviewRecord(_digest((c.id, c.category, c.actors)), 'CATEGORY:M', (m01_ref,), REVIEWER, '2026-10-22',
                              'APPROVED', ('R2 branch->mainflow: mainflow 0 deg, branch -22.5 deg',), b['decision_ref'])
            done[i] = replace(c, environment={**c.environment, 'category_review': encode_record(rv)})
    return done, b


def prepared(dirs):
    out = {}
    for d in dirs:
        for f in Path(d).glob('M56-P-*/prepare.json'):
            data = json.loads(f.read_text(encoding='utf-8'))
            out[data['scene']] = (f, data)
    return out


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


def main(outdir, *prep_dirs):
    out = Path(outdir); out.mkdir(parents=False, exist_ok=False)
    # Rebuild in memory against the v1 receipts themselves: st.build/m01 rewrite the SAME deterministic bytes into
    # the v1 directory; sha256 is checked before/after and the original bytes are restored on any difference.
    guard = {n: (V1.parent / n).read_bytes() for n in ('duy-decision-receipt.json', 'm01-r2-evidence.json')}
    try:
        done, b = v1_candidates(V1.parent)
    finally:
        changed = [n for n, data in guard.items() if (V1.parent / n).read_bytes() != data]
        for n in changed:
            (V1.parent / n).write_bytes(guard[n])
        assert not changed, f'V1_RECEIPT_BYTES_CHANGED_RESTORED:{changed}'
    # byte check against the frozen v1 file (candidates only; the receipt is v1's own)
    v1 = json.loads(V1.read_text(encoding='utf-8'))['candidates']
    mine = json.loads(json.dumps([encode_record(c) for c in done], default=str))
    mism = [c['id'] for c, d in zip(v1, mine) if c != d]
    assert len(v1) == len(mine) and not mism, f'V1_REBUILD_MISMATCH:{mism[:5]} {len(v1)} {len(mine)}'
    preps = prepared(prep_dirs)
    prereg_sha = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    report = []
    for i, c in enumerate(done):
        if c.category not in ('C', 'L'):
            continue
        f, p = preps.get(c.id, (None, None))
        if p is None:
            status = {'status': 'BLOCKED_FIXTURE', 'reason': 'NOT_PREPARED', 'prereg_sha256': prereg_sha}
            done[i] = replace(c, environment={**c.environment, 'runtime_recipe_v2': status})
            report.append({'id': c.id, **status}); continue
        pref = {'prepare_json': str(f), 'prepare_sha256': hashlib.sha256(f.read_bytes()).hexdigest(), 'prereg_sha256': prereg_sha}
        if p['status'] != 'PREPARED':
            status = {'status': p['status'], 'reason': p.get('reason'), **pref}
            done[i] = replace(c, environment={**c.environment, 'runtime_recipe_v2': status})
            report.append({'id': c.id, **{k: v for k, v in status.items() if k != 'prepare_json'}}); continue
        vN = c.parameters['vN'].values[0]
        markers = {k: plain(v) for k, v in p['markers'].items()}
        # E6 (erratum 3): readiness targets = the measured stock plateaus from probe 2 (v2.0 wrongly used the nominal
        # speeds here; Duy 2026-10-24 allowed exactly one run of the corrected v2.1 fixtures)
        readiness = {'targets_mps': {k: plain(v) for k, v in p['targets'].items()}, 'markers_m': markers}
        actors = tuple(replace(a, destination=F(p['destinations'][a.role]),
                               route_recipe={**a.route_recipe, **({'v2_start': 'probe-1 route cut at station '
                                                                    f"{plain(p['npc_start_station_probe1'])!r} (phasing rule, prereg 3)"}
                                                                   if a.role == 'NPC' else {'v2_start': 'frozen v1 arc 0'}),
                                             'v2_routes_sha256': p['routes_v2_sha256']})
                       for a in c.actors)
        status = {'status': 'PREPARED', **pref}
        phase = {'phase_predicate': p['phase_predicate']} if p.get('phase_predicate') else {}  # signal-phase v1 S5
        if p.get('phase_predicate') and p.get('phase_wait_limit_s') and float(plain(p['phase_wait_limit_s'])) > 60:
            phase['phase_wait_limit_s'] = F(str(round(float(plain(p['phase_wait_limit_s'])), 3)))  # v4 P2
        responses = c.responses
        if p.get('recipe') == 'v3':  # V3.1 (ab1fb09): same targets/profile/phases, route = the fixture EGO route
            from native_v2_common import v2_routes
            routes, _, _ = v2_routes(p, {a.role: a.route_recipe['route'] for a in c.actors}, c.town, plain)
            responses = tuple(cr.hashed(replace(r, route=routes['EGO'])) if r.actor_role == 'EGO' else r for r in c.responses)
            status['recipe'] = 'v3'
        done[i] = replace(c, actors=actors, responses=responses,
                          environment={**c.environment, 'readiness': readiness, 'runtime_recipe_v2': status, **phase})
        report.append({'id': c.id, 'status': 'PREPARED', 'markers': {k: str(v) for k, v in markers.items()}})
    revision = CandidateRevision('retained-23+fill20-v1-minus-F02-F03+recipes+runtime-recipe-v4', tuple(done), 'x' * 64, None)
    # identity ledger exactly as v1 (touching-cross-section-v1)
    ev = (cr.st.ref(EV1, 'IDENTITY_EVIDENCE'), cr.st.ref(EV2, 'IDENTITY_EVIDENCE')); dref = b['decision_ref']
    rules = {'id': 'touching-cross-section-v1', 'rule': 'same physical place iff modelled XODR cross-sections touch/overlap',
             'evidence_sha256': [r.sha256 for r in ev]}
    method = IdentityMethod('touching-cross-section-v1', '1', _digest(rules), rules)
    sites, assignments = {}, {}
    for c in done:
        if c.site_id not in sites:
            rec = SiteRecord(c.site_id, 'JUNCTION' if c.site_id.startswith('P0') else 'NONJUNCTION',
                             {'town': c.town, 'site': c.site_id}, {'method_hash': method.hash}, ev, None)
            rv = ReviewRecord(_site_digest(rec), 'SITE_IDENTITY', ev, REVIEWER, '2026-10-22', 'APPROVED',
                              ('distinct physical place under touching-cross-section-v1',), dref)
            sites[c.site_id] = replace(rec, review=rv)
        assignments[c.id] = c.site_id
    packet_path = out / 'site-ledger-packet.json'
    packet_path.write_text(json.dumps({'method_hash': method.hash, 'records': [encode_record(x) for x in sites.values()],
                                       'assignments': assignments}, indent=1, sort_keys=True, default=str), encoding='utf-8')
    pref = cr.st.ref(packet_path, 'IDENTITY_LEDGER_PACKET')
    ledger = review_sites(revision, method, (ReviewRecord(pref.sha256, 'IDENTITY_LEDGER', (pref,), REVIEWER, '2026-10-23',
                                                          'APPROVED', ('ledger for the v2 revision (sites unchanged)',), dref),))
    addendum = cr.st.ref(WORK / 'docs/m56/SPEC_ADDENDUM_C0_PARTIAL_20261022.md', 'SPEC_ADDENDUM')
    receipt = out / 'duy-v2-receipt.json'
    receipt.write_text(json.dumps({'source': '[chat] 2026-10-23, user self-stated as Duy',
                                   'quote': 'Approve v2 (Recommended)', 'v2.1': '[chat] 2026-10-24 Duy: Cho chạy v2.1 (Recommended): fix E6 targets, run C01/C02 A/B exactly once', 'question': 'runtime-recipe v2 version after C0, '
                                   'pre-registered before any CARLA run, Claude phasing rule disclosed',
                                   'prereg_sha256': prereg_sha, 'revision_id': revision.revision_id}, indent=1), encoding='utf-8')
    rref = cr.st.ref(receipt, 'OPERATOR_RECEIPT')
    review = ReviewRecord(_digest({'revision': revision, 'sites': ledger}), 'C0', (addendum, pref, rref), REVIEWER, '2026-10-23',
                          'APPROVED', ('C0 partial v2 = v1 + runtime-recipe v2 for C/L under Duy approval of v2; '
                                       'review by Claude under delegation, not independent',), rref)
    frozen = freeze_c0(revision, ledger, review, partial=addendum)
    if hasattr(frozen, 'reasons'):
        print('FREEZE_BLOCKED', list(frozen.reasons)); return
    data = json.dumps(encode_record(frozen), indent=1, sort_keys=True, default=str).encode()
    with open(out / 'c0-partial-v2-frozen-revision.json', 'xb') as f:
        f.write(data)
    (out / 'v2-report.json').write_text(json.dumps(report, indent=1, default=str), encoding='utf-8')
    print('C0_PARTIAL_V2_FROZEN', frozen.c0_receipt.kind, len(frozen.candidates), hashlib.sha256(data).hexdigest())
    print(json.dumps(report, default=str)[:3000])


if __name__ == '__main__':
    main(*sys.argv[1:])
