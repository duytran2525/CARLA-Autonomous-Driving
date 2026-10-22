"""F01 producer/source/public A/B, SOFTWARE only. Expected values come from the literal kinematics, not production."""
from fractions import Fraction as F

import pytest


def front_gaps(rows, start, end):
    # Straight route: NPC rear minus EGO front, body half-length 1.75 m (o_fixture body 3.5 m). Poses are recorded as
    # binary64 floats, so the observed metric is exact arithmetic over those float values, not the ideal rationals.
    pos = lambda n, role: F(float(rows[n][role][0]))
    return [pos(n, 'NPC') - F(7, 4) - (pos(n, 'EGO') + F(7, 4)) for n in range(start, end + 1)]


@pytest.mark.parametrize('action', ['A', 'B'])
def test_f01_producer_events_and_program_commands(tmp_path, action):
    """Fast precheck: real detector + real step_response over the literal trace (no public composition)."""
    from tests.m56.f01_cases import complete_f01
    c = complete_f01(tmp_path/'sources', action, public=False)
    by = {e.name: e.frame for e in c.events}
    assert (by['F01_BRAKE_MARKER'], by['TRIGGER'], by['NPC_F01_STOP_HOLD_CONFIRMED'], by['N_MOVE']) == (140, 145, 191, 197)
    issued = {}
    for f in c.frames:
        for a in f.actors:
            for cmd in a.commands:
                issued.setdefault((a.role, cmd.cause), cmd.frame)
    assert issued[('NPC', 'NOMINAL')] == 120 and issued[('EGO', 'NOMINAL')] == 120
    assert issued[('NPC', 'F01_BRAKE')] == 140 and issued[('NPC', 'NPC_RESTART')] == 191
    assert issued[('EGO', 'YIELD')] == 145 and issued[('EGO', 'RESUME')] == 197
    if action == 'A':
        assert 'STOP_AFTER_TRIGGER' in by


def test_f01_source_decoded_pair_two_full_public_actions(tmp_path):
    from dataclasses import replace
    from tests.m56.f01_cases import complete_f01
    from m56.catalog import _digest
    from m56.metrics import _source_metrics, _ab_review_subject, compare_ab
    a = complete_f01(tmp_path/'a-sources', 'A')
    b = complete_f01(tmp_path/'b-sources', 'B', a.frozen)
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
        end = next(e.frame for e in out.events if e.name == 'F01_N_CLEAR')
        assert out.metrics['g_front_min_m'].value == min(front_gaps(c.rows, 145, end))
    # Hand-derived peak .25 s deceleration (A ~8 m/s^2, B ~2 m/s^2) over the recorded binary64 velocities.
    for c, out in zip((a, b), pair.action_proofs):
        end = next(e.frame for e in out.events if e.name == 'F01_N_CLEAR')
        v = {n: F(float(c.rows[n]['EGO'][1])) for n in range(140, end + 1)}
        peak = max((v[n - 5] - v[n]) / F(1, 4) for n in range(150, end + 1))
        assert out.metrics['a_peak_025'].value == peak
    assert abs(pair.action_proofs[0].metrics['a_peak_025'].value - 8) < F(1, 1000)
    assert abs(pair.action_proofs[1].metrics['a_peak_025'].value - 2) < F(1, 1000)
    print('F01 SOFTWARE pair=', pair.status, pair.comparisons, 'author D09 only; NOT scientific qualification', flush=True)
