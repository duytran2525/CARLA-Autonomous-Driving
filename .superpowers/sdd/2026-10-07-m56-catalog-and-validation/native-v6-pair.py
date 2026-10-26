"""v6 g (docs/m56/PREREG_M56_V6_20261026.md): pair-level result of one sealed native A/B scene, offline, no server.

Each action's EpisodeEvidence = runtime.load_episode + every sealed '<name>_ref.json' pointer of the episode (as
native-v5-reeval.py) + a FRESH sealed W05 bundle per action (same subject/areas as native-v2-ab.w05, made with the evaluating code).
A D09 review (scope REALIZED_AB_COMPARABILITY_D09, the six areas, Claude under Duy's delegation, NOT independent) is
bound to the product's _ab_review_subject digest, sealed in its own bundle, and the product's compare_ab decides.
python -I native-v6-pair.py SCENE_DIR [SCENE_DIR ...]   -> outputs/m56_v6_pair_<utc>/<scene>/{w05-A, w05-B, d09, pair-result.json}
(the A/B scene directories are only read)"""
import json, sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import REVIEWER, WORK, now  # noqa: E402  (also puts M56_CODE first on sys.path)
from m56.catalog import _digest  # noqa: E402
from m56.evidence import open_run, append_record, seal, snapshot_sources  # noqa: E402
from m56.metrics import (compare_ab, evaluate_episode, _ab_review_subject, _ab_fulltrace_review, _source_metrics,  # noqa: E402
                         _authenticated_events)
from m56.model import ReviewRecord, decode_record, load_json  # noqa: E402
from m56.runtime import load_episode, _ref  # noqa: E402

AREAS = ('fulltrace', 'near_zero', 'nearstanding', 'identity', 'mechanism', 'comparability')


def evidence(sd, action, dest, FIXTURE):
    """The episode with its sealed pointers and a FRESH W05 bundle made with the evaluating code (the W05 subject binds
    the exact source list, events and metrics, so a bundle written by another process or code version cannot be
    reused). Same subject/areas as native-v2-ab.w05; authority = the A/B's own delegation receipt (kit proof review)."""
    root = sd / 'run' / 'episodes' / sd.name / action
    ev = load_episode(root)
    if ev is None:
        raise ValueError(f'EPISODE_NOT_SEALED:{action}')
    store = SimpleNamespace(root=root)
    extra = {f.stem: _ref(store, f.name) for f in sorted(root.glob('*_ref.json'))}
    ev = replace(ev, integrity={**ev.integrity, **extra}, source=tuple(dict.fromkeys((*ev.source, *extra.values()))))
    proof = decode_record('CapabilityProof', json.loads((root / 'contact_ref.json').read_text(encoding='utf-8')))
    authority = proof.review.authority_ref
    values, events = _source_metrics(ev, FIXTURE), _authenticated_events(ev, FIXTURE)
    if values is None or events is None:
        return ev, authority, 'NOT_WRITTEN: metrics/events not admissible'
    subject = {'schema': 1, 'scope': 'EPISODE_WITNESS_W05', 'fixture': ev.fixture, 'manifest': ev.manifest,
               'journal': ev.journal, 'sources': ev.source, 'trajectory_hash': _digest(ev.raw), 'end_simtime': ev.end_simtime,
               'events': events, 'metrics': values}
    original = (ev.fixture, ev.manifest, *ev.journal, *ev.source)
    review = ReviewRecord(_digest(subject), 'EPISODE_WITNESS_W05', tuple(dict.fromkeys(original)), REVIEWER, '2026-10-26',
                          'APPROVED', tuple(f'{k}: automated consumer checks passed for this sealed episode; Claude under '
                                            'Duy delegation, not independent' for k in AREAS), authority)
    bundle = open_run(dest / f'w05-{action}', f'w05-{action}', 'm56-claude')
    append_record(bundle, 'review.json', review)
    snap = snapshot_sources(bundle, (*original, authority)).status
    seal(bundle)
    w05 = {'episode_review_ref': _ref(SimpleNamespace(root=bundle.root), 'review.json'),
           'episode_review_manifest': _ref(SimpleNamespace(root=bundle.root), 'manifest.json')}
    return replace(ev, integrity={**ev.integrity, **w05}), authority, snap


OUT = WORK / f'outputs/m56_v6_pair_{now()}'


def pair_scene(sd):
    dest = OUT / sd.name; dest.mkdir(parents=True)
    fixture = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
    (a, auth_a, w05a), (b, auth_b, w05b) = evidence(sd, 'A', dest, fixture), evidence(sd, 'B', dest, fixture)
    assert auth_a == auth_b, 'AUTHORITY_DIFFERS'
    va, vb = evaluate_episode(a, fixture), evaluate_episode(b, fixture)
    pair = fixture.pair
    out = {'scene': sd.name, 'episodes': {k: {'spawn': str(v.spawn), 'physical': str(v.physical), 'witness': str(v.witness),
                                               'reasons': list(v.reasons)} for k, v in (('A', va), ('B', vb))},
           'w05': {'A': w05a, 'B': w05b}}
    review = None
    if all(n in v.metrics for v in (va, vb) for n in pair.names):
        left, right = (tuple(v.metrics[n] for n in pair.names) for v in (va, vb))
        subject = _ab_review_subject(a, b, pair, left, right)
        refs = tuple(r for e in (a, b) for r in (e.fixture, e.manifest, *e.journal, e.integrity['trajectory_ref']))
        review = ReviewRecord(_digest(subject), 'REALIZED_AB_COMPARABILITY_D09', tuple(dict.fromkeys(refs)), REVIEWER,
                              '2026-10-26', 'APPROVED',
                              tuple(f'{k}: automated consumer checks on both sealed episodes; Claude under Duy delegation, '
                                    'not independent' for k in AREAS), auth_a)
        bundle = open_run(dest / 'd09', 'd09', 'm56-claude')
        append_record(bundle, 'review.json', review)
        out['d09_snapshot'] = snapshot_sources(bundle, (*review.refs, auth_a)).status
        seal(bundle)
        # The product's own D09 check, independent of the episode gates (which compare_ab applies first).
        out['d09_binds'] = _ab_fulltrace_review(a, b, pair, left, right, review)
    verdict = compare_ab(a, b, pair, review)
    out.update(status=verdict.status, comparisons=[None if d is None else str(d) for d in verdict.comparisons],
               metrics=[repr(m)[:400] for m in verdict.metrics], d09_written=review is not None,
               label='independent review waived by Duy 2026-10-24; CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent')
    out['source_scene_dir'] = str(sd)
    with open(dest / 'pair-result.json', 'x', encoding='utf-8') as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps({'scene': sd.name, 'status': verdict.status, 'comparisons': out['comparisons']}), flush=True)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        pair_scene(Path(p).resolve())
