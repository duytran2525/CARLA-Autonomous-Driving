"""F03 closed-loop producer/source/public A/B, SOFTWARE only.

NPC and Ego-A commands are checked against the literal schedule inside the producer. Ego-B is the bounded reverse
kernel's own output, so it is checked by properties (start at TRIGGER, hard limit, gear only after own stop and the
peer stop, forward after gear). Metric expectations come from the recorded binary64 poses, not production metrics.
"""
from fractions import Fraction as F

import pytest

from tests.m56.f03_cases import TRIGGER_FRAME as TRIGGER, NPC_STOP_FRAME as NPC_STOP  # hand-derived, see f03_cases


def x_of(frame, role):
    return F(float(next(a for a in frame.actors if a.role == role).pose.x))


def expected_metrics(frames, body):
    # Flat Ego route along +x, both bodies yaw/pitch 0: front gap = NPC rear - Ego front over the recorded poses.
    window = [f for f in frames if TRIGGER <= f.frame <= NPC_STOP]
    xs = [x_of(f, 'EGO') for f in window]
    reverse = sum((max(F(0), a - b) for a, b in zip(xs, xs[1:])), F(0))
    half = F(float(body.extents[0]))
    gap = min(x_of(f, 'NPC') - x_of(f, 'EGO') - 2 * half for f in window)
    return reverse, gap


def ego_phases(issued):
    seq = []
    for (role, n), command in sorted(issued.items(), key=lambda item: item[0][1]):
        if role == 'EGO' and (not seq or seq[-1][1] != command.cause):
            seq.append((n, command.cause))
    return seq


@pytest.mark.parametrize('action', ['A', 'B'])
def test_f03_closed_loop_producer_events_and_commands(tmp_path, action):
    from tests.m56.f03_cases import joint_f03_producer
    c = joint_f03_producer(tmp_path/'sources', action)  # NPC/Ego-A literals and TRIGGER/NPC_STOP asserted inside
    by = {e.name: e.frame for e in c.events}
    assert 'DESTINATION_CONFIRMED' in by, sorted(by.items(), key=lambda x: x[1])
    seq = ego_phases(c.issued)
    if action == 'A':
        assert seq == [(99, 'HOLD'), (NPC_STOP, 'FORWARD')], seq
        return
    assert [cause for _, cause in seq] == ['HOLD', 'REVERSE', 'STOPPING', 'FORWARD_GEAR', 'FORWARD'], seq
    at = dict((cause, n) for n, cause in seq)
    assert at['REVERSE'] == TRIGGER, seq
    xs = {f.frame: x_of(f, 'EGO') for f in c.frames}
    assert F(4) - min(xs.values()) <= 2  # hard reverse limit, recorded poses
    last_retreat = max(n for n in xs if n - 1 in xs and xs[n] < xs[n - 1])
    assert last_retreat + 10 <= NPC_STOP, last_retreat  # own stop held .5 s inside the metric window
    assert at['FORWARD_GEAR'] >= NPC_STOP and xs[at['FORWARD_GEAR']] == xs[at['FORWARD_GEAR'] - 1], seq
    assert at['FORWARD'] > at['FORWARD_GEAR'], seq


def test_f03_source_decoded_pair_two_full_public_actions(tmp_path):
    from dataclasses import replace
    from tests.m56.f03_cases import complete_f03
    from m56.catalog import _digest
    from m56.metrics import _source_metrics, _ab_review_subject, compare_ab
    a = complete_f03(tmp_path/'a-sources', 'A')
    b = complete_f03(tmp_path/'b-sources', 'B', a.frozen)
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
        events = {e.name: e.frame for e in out.events}
        assert (events['TRIGGER'], events['NPC_STOP_CONFIRMED']) == (TRIGGER, NPC_STOP), events
        assert 'DESTINATION_CONFIRMED' in events, events
        reverse, gap = expected_metrics(c.episode.raw, c.frozen.body)
        assert out.metrics['d_reverse_m'].value == reverse
        assert out.metrics['g_front_min_m'].value == gap
    assert pair.action_proofs[0].metrics['d_reverse_m'].value == 0
    print('F03 SOFTWARE pair=', pair.status, pair.comparisons, 'author D09 only; NOT scientific qualification', flush=True)
