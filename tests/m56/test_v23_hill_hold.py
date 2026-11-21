"""v23 (addendum Y): F03 hill start. Native F03-S1 v22 arm B reached DESTINATION_CONFIRMED with 0 BLOCKED, but after the
forward gear the stock continuation (brake 0) gave no drive for ~0.35 s (transmission engagement) and the Ego rolled back
1.46-1.71 mm per tick (frames 8864-8870), more than the CONTINUOUS_GEOMETRY uncertainty (1e-3 m): POST_END_UNPLANNED_REVERSE.
NEW RULE: for the first response.HILL_HOLD_S of FORWARD the bounded kernel sends HILL_HOLD_CONTROL (throttle .75, brake .3),
then the stock continuation. OLD RULE (v19-v22): stock continuation from the first FORWARD tick (HILL_HOLD_S = 0 here).
The synthetic physics (f03_cases.ENGAGE_TICKS) is a model of the native delay, not a calibration of it."""
from fractions import Fraction as F

import pytest

from m56 import response as R
from m56.metrics import evaluate_episode
from tests.m56 import f03_cases


def _forward(issued):
    return [c for (role, n), c in sorted(issued.items(), key=lambda i: i[0][1]) if role == 'EGO' and c.cause == 'FORWARD']


@pytest.mark.parametrize('dispatch', ['direct', 'runtime'])
def test_forward_start_is_held_for_hill_hold_s_then_stock(tmp_path, dispatch):
    c = f03_cases.joint_f03_producer(tmp_path / 'sources', 'B', dispatch=dispatch)
    fwd, held = _forward(c.issued), int(R.HILL_HOLD_S / f03_cases.DT)
    assert held == 20 and len(fwd) > held, len(fwd)
    assert [x.control for x in fwd[:held]] == [R.HILL_HOLD_CONTROL] * held
    assert all(x.control is None for x in fwd[held:]), [x.control for x in fwd[held:]][:3]
    assert 'DESTINATION_CONFIRMED' in {e.name for e in c.events}


def test_ego_a_and_npc_are_never_held(tmp_path):
    for action in ('A', 'B'):
        c = f03_cases.joint_f03_producer(tmp_path / action, action)
        others = [x for (role, n), x in c.issued.items() if (role, action) != ('EGO', 'B')]
        assert R.HILL_HOLD_CONTROL not in {x.control for x in others}


def _engagement_delay(monkeypatch, hold):
    # native v22 B: ~0.35 s without drive after the forward gear, and the kernel did not block. Here the kernel sees the same
    # station as the consumer, so 5 ticks (7.5 mm in all) keep the cumulative rollback inside its 1/100 m envelope.
    monkeypatch.setattr(f03_cases, 'ENGAGE_TICKS', 5)
    monkeypatch.setattr(f03_cases, 'ROLLBACK_PER_TICK', F(3, 2000))  # 1.5 mm per tick, as frames 8864-8870
    monkeypatch.setattr(f03_cases, 'REVERSE_UNCERTAINTY', F(1, 100))  # native F03 REVERSE_STOP_BOUND value
    if not hold:
        monkeypatch.setattr(R, 'HILL_HOLD_S', R.Number(0))


def _reasons(tmp_path):
    c = f03_cases.complete_f03(tmp_path / 'b', 'B')
    return set(evaluate_episode(c.episode, c.fixture).reasons)


def test_engagement_delay_rollback_is_post_end_reverse_under_the_old_rule(tmp_path, monkeypatch):
    """Red-first control: the v22 failure reproduced in the synthetic loop."""
    _engagement_delay(monkeypatch, hold=False)
    assert 'POST_END_UNPLANNED_REVERSE' in _reasons(tmp_path)


def test_hill_hold_prevents_the_engagement_delay_rollback(tmp_path, monkeypatch):
    _engagement_delay(monkeypatch, hold=True)
    reasons = _reasons(tmp_path)
    assert 'POST_END_UNPLANNED_REVERSE' not in reasons, reasons
    assert not {r for r in reasons if 'COMMAND' in r}, reasons  # the consumer replays the held commands exactly
