"""F02 producer/source/public A/B, SOFTWARE only. Expected values come from the literal kinematics, not production."""
from fractions import Fraction as F

import pytest


def rear_gap(rows, n):
    # Straight route: EGO rear minus NPC front, body half-length 1.75 m, over the recorded binary64 poses.
    return F(float(rows[n]['EGO'][0])) - F(7, 4) - (F(float(rows[n]['NPC'][0])) + F(7, 4))


def trapezoid_mean(rows, start, end):
    speed = lambda n: F(float(rows[n]['EGO'][1]))  # recorded binary64 velocities
    total = sum((speed(n) + speed(n + 1)) / 2 * F(1, 20) for n in range(start, end))
    return total / (F(end - start, 20))


@pytest.mark.parametrize('action', ['A', 'B'])
def test_f02_producer_events_and_program_commands(tmp_path, action):
    from tests.m56.f02_cases import complete_f02
    c = complete_f02(tmp_path/'sources', action, public=False)
    by = {e.name: e.frame for e in c.events}
    assert by['TRIGGER'] == 150 and rear_gap(c.rows, 150) == 20
    issued = {}
    for f in c.frames:
        for a in f.actors:
            for cmd in a.commands:
                issued.setdefault((a.role, cmd.cause), cmd.frame)
    assert issued[('EGO', 'NOMINAL')] == 120 and issued[('NPC', 'NOMINAL')] == 120 and issued[('EGO', 'ACTION')] == 150


def test_f02_source_decoded_pair_two_full_public_actions(tmp_path):
    from dataclasses import replace
    from tests.m56.f02_cases import complete_f02
    from m56.catalog import _digest
    from m56.metrics import _source_metrics, _ab_review_subject, compare_ab
    a = complete_f02(tmp_path/'a-sources', 'A')
    b = complete_f02(tmp_path/'b-sources', 'B', a.frozen)
    assert _digest(a.fixture) == _digest(b.fixture)
    left, right = _source_metrics(a.episode, a.fixture), _source_metrics(b.episode, b.fixture)
    refs = tuple(dict.fromkeys(r for e in (a.episode, b.episode) for r in (e.fixture, e.manifest, *e.journal, *e.source)))
    review = a.sources.review(_ab_review_subject(a.episode, b.episode, a.fixture.pair, left, right),
                              'REALIZED_AB_COMPARABILITY_D09', refs)
    review = replace(review, reasons=tuple(k + ': synthetic author source composition, no scientific qualification'
                                           for k in ('fulltrace', 'near_zero', 'nearstanding', 'identity', 'mechanism', 'comparability')))
    pair = compare_ab(a.episode, b.episode, a.fixture.pair, review)
    assert len(pair.action_proofs) == 2, pair
    for c, out in zip((a, b), pair.action_proofs):
        assert (out.spawn, out.physical, out.witness) == ('CONFIRMED', 'COMPLETE', 'VALID'), out
        end = next(e.frame for e in out.events if e.name == 'F02_END')
        assert out.metrics['v_mean_E'].value == trapezoid_mean(c.rows, 150, end)
        assert out.metrics['g_rear_min_m'].value == min(rear_gap(c.rows, n) for n in range(150, end + 1))
    print('F02 SOFTWARE pair=', pair.status, pair.comparisons, 'author D09 only; NOT scientific qualification', flush=True)
