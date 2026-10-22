"""F06 joint producer/source/public A/B pair through one real compare_ab, software ONLY.

Expected comparisons are derived by hand from the frozen 1/5 criterion and the
already-verified public metrics (A: 0 m / 1 m, B: 1 m / 2 m):
delta(0,1)=1 and delta(1,2)=1/2, both >= 1/5. Not computed with production code.
"""
from fractions import Fraction as F


def test_f06_source_decoded_pair_requires_two_full_public_actions(tmp_path):
    from dataclasses import replace
    from tests.m56.f06_cases import complete_f06
    from m56.catalog import _digest
    from m56.metrics import _source_metrics, _ab_review_subject, compare_ab
    a = complete_f06(tmp_path/'a-sources', 'A')
    b = complete_f06(tmp_path/'b-sources', 'B', a.frozen)
    assert _digest(a.fixture) == _digest(b.fixture)
    left, right = _source_metrics(a.episode, a.fixture), _source_metrics(b.episode, b.fixture)
    refs = tuple(dict.fromkeys(r for e in (a.episode, b.episode) for r in (e.fixture, e.manifest, *e.journal, *e.source)))
    review = a.sources.review(_ab_review_subject(a.episode, b.episode, a.fixture.pair, left, right),
                              'REALIZED_AB_COMPARABILITY_D09', refs)
    review = replace(review, reasons=tuple(k+': synthetic author source composition, no scientific qualification'
        for k in ('fulltrace', 'near_zero', 'nearstanding', 'identity', 'mechanism', 'comparability')))
    pair = compare_ab(a.episode, b.episode, a.fixture.pair, review)
    assert len(pair.action_proofs) == 2, pair
    for action, out in zip(('A', 'B'), pair.action_proofs):
        assert (out.spawn, out.physical, out.witness) == ('CONFIRMED', 'COMPLETE', 'VALID'), out
        events = {e.name: e for e in out.events}
        assert events['TRIGGER'].frame == 150
        assert events['NPC_REVERSE_TARGET_STOP_CONFIRMED'].frame == 301
        assert events['DESTINATION_CONFIRMED'].frame > 303
        assert out.metrics['d_reserve_reverse_m'].value == (0 if action == 'A' else 1)
        assert out.metrics['g_front_min_m'].value == (1 if action == 'A' else 2)
    assert pair.comparisons == (F(1), F(1, 2)), pair.comparisons
    assert pair.status == 'PASS', pair
    print('F06 SOFTWARE pair=', pair.status, pair.comparisons, 'author D09 only; NOT scientific qualification', flush=True)
