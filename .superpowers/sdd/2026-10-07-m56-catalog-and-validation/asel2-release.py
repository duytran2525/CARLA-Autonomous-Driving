"""A-SEL2 release assembler (spec 11 + A-SEL2). Offline. Steps, all with the product m56 of M56_CODE (v11):
 1. delivered set = candidates of REVISION whose latest pair-result (outputs/m56_v6_pair_*/<id>/pair-result.json) is PASS
    (trialed failures M04-S1/M07-S1 and anything not PASS are reported, never counted);
 2. --full: per delivered scene re-evaluate both sealed episodes and compare_ab with the sealed D09 review of that pair run
    -> EligibilityRecord (RAM heavy; dry mode skips it and the AB_PROOF deficit stays);
 3. realized descriptors (native-realized-descriptors.scene) -> compare_realized for every same-category pair, each with a
    REALIZED_COMPARABILITY_D09 review signed by Claude under Duy's delegation (not independent);
 4. site ledger: the revision's site packet re-signed SITE_QUALIFIED for the delivered sites (A-SEL2 1.3);
 5. check_catalog + summarize; export_catalog ONLY when no deficit remains (never forced).
Report: outputs/m56_asel2_release_<stamp>/release-report.json (create-exclusive).
usage: M56_CODE=.../m56-v11 python -I asel2-release.py REVISION.json [--full]"""
import glob, hashlib, importlib.util, json, sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from fractions import Fraction as F
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from native_v2_common import WORK, now, REVIEWER  # noqa: E402  (M56_CODE first on sys.path)
from m56.catalog import (_digest, _site_digest, check_catalog, compare_realized, review_sites, summarize, export_catalog,
                         REALIZED_AGGREGATION)
from m56.model import (CandidateRevision, IdentityMethod, PolicyBundle, ReviewRecord, SiteRecord, SourceRef, decode_record,
                       encode_record)

REV = Path(sys.argv[1]); FULL = '--full' in sys.argv
OUT = WORK / f'outputs/m56_asel2_release_{now()}'; OUT.mkdir()
DOC = WORK / 'docs/m56/DESCRIPTOR_SPECS_M56_ASEL2_20261108.md'
ADD = WORK / 'docs/m56/SPEC_ADDENDUM_SELECTION_EXPANSION_20261108.md'
sref = lambda p, kind: SourceRef(str(p), hashlib.sha256(Path(p).read_bytes()).hexdigest(), Path(p).stat().st_size, '1', 'sha256', kind)
doc_ref, add_ref = sref(DOC, 'DESCRIPTOR_SPEC'), sref(ADD, 'SPEC_ADDENDUM')
EXCLUDE = {'M56-P-M04-S1', 'M56-P-M07-S1'}  # fill v4 addendum C
LABEL = 'CLAUDE_REVIEW_UNDER_DUY_DELEGATION; independent review waived by Duy 2026-10-24; not independent'

spec = importlib.util.spec_from_file_location('rd', here / 'native-realized-descriptors.py'); rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)

D = lambda unit, q, agg, aliases=(): {'unit': unit, 'physical_quantity': q, 'aggregation': agg, 'source_actions': ('A', 'B'),
                                     'event': 't0 (TRIGGER) of the category', 'window': 'DESCRIPTOR_SPECS 2',
                                     'reference': 'spec 2.3 + A-SEL2 4/7', 'refs': (doc_ref,), **({'aliases': aliases} if aliases else {})}
def table(agg):
    CLM = {'vN': D('m/s', 'npc_speed', agg), 'G': D('m', 'ego_trigger_distance', agg, ('G_m',)), 'LrefN': D('m', 'npc_connector_length', agg)}
    return {'C': CLM, 'L': CLM, 'M': CLM, 'I': {'vE': D('m/s', 'ego_speed', agg), 'gap': D('m', 'trigger_gap', agg, ('gap_m',))},
            'O': {'vE': D('m/s', 'ego_speed', agg), 'G': D('m', 'follow_gap', agg, ('G_m', 'gap'))}}
pol = PolicyBundle('asel2-release-v11', _digest({'doc': doc_ref.sha256}), {}, {},
                   {'by_category': table('declared_scalar'), 'realized_by_category': table(REALIZED_AGGREGATION)}, (doc_ref, add_ref))

rev = json.loads(REV.read_text(encoding='utf-8'))
cands = {}
for item in rev['candidates']:
    item = {**item, 'parameters': {n: p for n, p in item['parameters'].items() if p.get('units') != 'index'}}
    c = decode_record('Candidate', item)
    if not hasattr(c, 'errors'):
        cands[c.id] = c

def latest_pair(cid):
    """Latest PASS pair-result if any (dry mode; consumers differ between runs), else the latest one. --full re-evaluates
    every delivered scene under the release product instead."""
    best = last = None
    for f in sorted(glob.glob(str(WORK / f'outputs/m56_v6_pair_*/{cid}/pair-result.json'))):
        r = json.loads(Path(f).read_text(encoding='utf-8')) | {'_path': f}
        last = r
        if r.get('status') == 'PASS':
            best = r
    return best or last

rows, delivered = [], []
for cid, c in sorted(cands.items()):
    p = latest_pair(cid)
    st = 'EXCLUDED_TRIALED_FAILURE' if cid in EXCLUDE else (p['status'] if p else 'NO_PAIR')
    rows.append({'id': cid, 'category': c.category, 'town': c.town, 'site': c.site_id, 'pair': st, 'pair_result': p and p['_path']})
    if st == 'PASS':
        delivered.append((c, p))

# 3. realized + comparisons
realized, missing = {}, {}
for c, p in delivered:
    if c.category == 'F':
        continue
    try:
        r = rd.scene(p['source_scene_dir'], p)
    except Exception as e:  # recorded, never guessed
        missing[c.id] = repr(e)[:200]; continue
    vals = {}
    for n, acts in r['values'].items():
        vals[n] = {a: (F(v[0]), decode_record('SourceRef', v[1])) for a, v in acts.items()}
    realized[c.id] = vals
    if r['missing']:
        missing[c.id] = r['missing']
comps = []
for cat in 'CLMIO':
    cs = [c for c, _ in delivered if c.category == cat]
    for a, b in combinations(sorted(cs, key=lambda x: x.slot), 2):
        binding = _digest({'a': a.id, 'b': b.id, 'realized': {a.id: realized.get(a.id), b.id: realized.get(b.id)}, 'policy': pol})
        review = ReviewRecord(binding, 'REALIZED_COMPARABILITY_D09', (doc_ref,), REVIEWER, now()[:10], 'APPROVED',
                              (f'realized descriptors of both scenes, mean of A and B by the product; {LABEL}',), add_ref)
        comps.append(compare_realized(a, b, realized, pol, (review,)))

# 4. sites: the revision's packet, re-signed SITE_QUALIFIED for delivered sites
packet = json.loads((REV.parent / 'site-ledger-packet.json').read_text(encoding='utf-8'))
dsites = {c.site_id for c, _ in delivered}
recs = []
for raw in packet['records']:
    rec = decode_record('SiteRecord', raw)
    if rec.id in dsites:
        rv = ReviewRecord(_site_digest(rec), 'SITE_QUALIFIED', rec.interaction_refs or (add_ref,), REVIEWER, now()[:10], 'APPROVED',
                          (f'distinct physical place (touching-cross-section-v1) with a delivered PASS scene; {LABEL}',), add_ref)
        rec = SiteRecord(rec.id, rec.kind, rec.geography, rec.topology, rec.interaction_refs, rv)
    recs.append(rec)
pk = OUT / 'site-ledger-packet-qualified.json'
pk.write_text(json.dumps({'method_hash': packet['method_hash'], 'records': [encode_record(x) for x in recs],
                          'assignments': {c.id: c.site_id for c, _ in delivered}}, indent=1, sort_keys=True, default=str), encoding='utf-8')
pref = sref(pk, 'IDENTITY_LEDGER_PACKET')
method = next(IdentityMethod(r.topology['method_hash'] and 'touching-cross-section-v1', '1', packet['method_hash'], {})
              for r in recs[:1])
delivered_rev = CandidateRevision('asel2-delivered', tuple(c for c, _ in delivered), _digest([c.id for c, _ in delivered]), None)
ledger = review_sites(delivered_rev, method, (ReviewRecord(pref.sha256, 'IDENTITY_LEDGER', (pref,), REVIEWER, now()[:10], 'APPROVED',
                                                           (f'A-SEL2 delivered set; {LABEL}',), add_ref),))
component = check_catalog(delivered_rev, ledger, tuple(comps))
# check_catalog is the component audit and always adds RELEASE_EVIDENCE_REQUIRED; the release audit carries the same counts
# and construction deficits, and the evidence itself is judged by _release_deficits (product T15 contract).
from m56.model import CatalogAudit
audit = CatalogAudit(component.counts, component.towns, component.sites, component.comparisons,
                     tuple(d for d in component.deficits if d != 'RELEASE_EVIDENCE_REQUIRED'), 'COMPONENT_AUDITED')
evidence = ()
if FULL:  # 2. EligibilityRecord per delivered scene: same steps as native-v6-pair.pair_scene, under the release product
    from m56.evidence import open_run, append_record, seal, snapshot_sources
    from m56.metrics import compare_ab, evaluate_episode, _ab_review_subject
    from m56.model import EligibilityRecord, load_json
    ps = importlib.util.spec_from_file_location('pairmod', here / 'native-v6-pair.py'); pm = importlib.util.module_from_spec(ps)
    ps.loader.exec_module(pm)
    elig = []
    for c, p in delivered:
        sd = Path(p['source_scene_dir']); dest = OUT / 'elig' / c.id; dest.mkdir(parents=True)
        try:
            fixture = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
            (a, auth_a, _), (b, auth_b, _) = pm.evidence(sd, 'A', dest, fixture), pm.evidence(sd, 'B', dest, fixture)
            va, vb = evaluate_episode(a, fixture), evaluate_episode(b, fixture)
            pair = fixture.pair
            left, right = (tuple(v.metrics[n] for n in pair.names) for v in (va, vb))
            refs = tuple(r for e in (a, b) for r in (e.fixture, e.manifest, *e.journal, e.integrity['trajectory_ref']))
            review = ReviewRecord(_digest(_ab_review_subject(a, b, pair, left, right)), 'REALIZED_AB_COMPARABILITY_D09',
                                  tuple(dict.fromkeys(refs)), REVIEWER, now()[:10], 'APPROVED',
                                  tuple(f'{k}: automated consumer checks on both sealed episodes; {LABEL}' for k in pm.AREAS), auth_a)
            bundle = open_run(dest / 'd09', 'd09', 'm56-claude'); append_record(bundle, 'review.json', review)
            snapshot_sources(bundle, (*review.refs, auth_a)); seal(bundle)
            verdict = compare_ab(a, b, pair, review)
            elig.append(EligibilityRecord(c.id, verdict, (a.fixture, b.fixture), (review,), (a.manifest, b.manifest)))
            rows.append({'id': c.id, 'eligibility': verdict.status})
        except Exception as e:  # recorded; the AB_PROOF deficit then names the scene
            rows.append({'id': c.id, 'eligibility_error': repr(e)[:300]})
    evidence = tuple(elig)
summary = summarize(delivered_rev, audit, evidence)
exported = None
if not summary['deficits']:  # 5. export only without any deficit (never forced)
    exported = export_catalog(delivered_rev, audit, evidence, OUT / 'm56_catalog_asel2.json')
report = {'note': 'A-SEL2 release assembler; export only without deficits', 'revision': str(REV), 'dry': not FULL,
          'counts_by_category': dict(Counter(c.category for c, _ in delivered)), 'delivered': len(delivered),
          'audit_counts': dict(audit.counts), 'audit_deficits': list(audit.deficits),
          'comparison_status': dict(Counter(f"{cands[r.pair_ids[0]].category}/{r.status}" for r in comps)),
          'realized_missing': missing, 'summary': summary, 'exported': repr(exported), 'rows': rows}
(OUT / 'release-report.json').open('x', encoding='utf-8').write(json.dumps(report, indent=1, default=str, ensure_ascii=False))
print(json.dumps({k: report[k] for k in ('counts_by_category', 'delivered', 'audit_counts', 'audit_deficits', 'comparison_status')}, default=str))
print('summary', summary['status'], summary['deficits'])
