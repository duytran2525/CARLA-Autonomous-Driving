"""One delivered scene's EligibilityRecord in its own process (2026-11-15). The in-process loop of asel2-release.py --full
kept about 1 GB per scene (5.6 GB -> 24 GB) and hit MemoryError on O02/O03; the steps below are moved from it unchanged.
  python -I asel2-elig-one.py SOURCE_SCENE_DIR CANDIDATE_ID DEST    -> DEST/eligibility-record.json (create-exclusive)"""
import importlib.util, json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from native_v2_common import now, REVIEWER  # noqa: E402  (M56_CODE first on sys.path)
from m56.catalog import _digest
from m56.evidence import open_run, append_record, seal, snapshot_sources
from m56.metrics import compare_ab, evaluate_episode, _ab_review_subject
from m56.model import EligibilityRecord, ReviewRecord, decode_record, encode_record, load_json

LABEL = 'CLAUDE_REVIEW_UNDER_DUY_DELEGATION; independent review waived by Duy 2026-10-24; not independent'  # = asel2-release.LABEL

sd, cid, dest = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
ps = importlib.util.spec_from_file_location('pairmod', here / 'native-v6-pair.py'); pm = importlib.util.module_from_spec(ps)
ps.loader.exec_module(pm)
dest.mkdir(parents=True)
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
rec = EligibilityRecord(cid, verdict, (a.fixture, b.fixture), (review,), (a.manifest, b.manifest))
data = json.dumps(encode_record(rec), indent=1, sort_keys=True)
assert decode_record('EligibilityRecord', json.loads(data)) == rec, 'ELIGIBILITY_ROUNDTRIP'  # the parent rebuilds it from this file
with open(dest / 'eligibility-record.json', 'x', encoding='utf-8') as f:
    f.write(data)
print(json.dumps({'id': cid, 'eligibility': verdict.status}), flush=True)
