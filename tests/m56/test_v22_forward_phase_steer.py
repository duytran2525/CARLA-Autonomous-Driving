"""v22 (addendum X): after the bounded reverse, the F03 forward phase is the stock PID, which steers. The v19-v21 kernel
required readback.steer == 0 in every phase (reverse_intent), so the first forward CONTROL (native steer -0.002) produced
BLOCKED REVERSE_APPLIED_CONTROL_UNPROVEN and the EGO looped GEAR_TRANSITION -> CONTROL FORWARD -> BLOCKED forever
(F03-S1 v21 arm B, frames 8123-8820). The closed-loop producer's synthetic DRIVE readback had steer 0, so it never saw it.
OLD RULE: steer must be 0 in every phase. NEW: only in the reverse phases; hand_brake is refused in every phase."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from tests.m56 import f03_cases
from tests.m56.test_f03_complete import ego_phases


def _drive(monkeypatch, **fields):
    monkeypatch.setattr(f03_cases, 'DRIVE', replace(f03_cases.DRIVE, **fields))


def test_forward_phase_accepts_the_stock_pid_steer(tmp_path, monkeypatch):
    _drive(monkeypatch, steer=-0.002)  # native F03 v21 B readback after CONTROL FORWARD: -0.00195 .. -0.00212
    c = f03_cases.joint_f03_producer(tmp_path / 'sources', 'B')  # asserts inside: no BLOCKED command on any frame
    assert [cause for _, cause in ego_phases(c.issued)] == ['HOLD', 'REVERSE', 'STOPPING', 'FORWARD_GEAR', 'FORWARD']
    assert 'DESTINATION_CONFIRMED' in {e.name for e in c.events}


def _rollback(monkeypatch, rollback, uncertainty):
    _drive(monkeypatch, steer=-0.002)
    monkeypatch.setattr(f03_cases, 'ROLLBACK_AT_FORWARD_START', rollback)  # a pure backward step on the first forward tick
    monkeypatch.setattr(f03_cases, 'REVERSE_UNCERTAINTY', uncertainty)  # the native F03 REVERSE_STOP_BOUND value is 1/100 m


@pytest.mark.parametrize('rollback', [F(1, 4000), F(1, 1000)])
def test_uphill_release_rollback_inside_the_declared_uncertainty_is_noise(tmp_path, monkeypatch, rollback):
    """Native F03 v21 B frames 8124/8125: the first forward tick rolled back 2.5e-4 m, the next 9.8e-4 m. With every b<a step a
    'reverse step' the kernel moved last_reverse past the gear frame (REVERSE_TERMINAL_GEAR_UNPROVEN) and looped again."""
    _rollback(monkeypatch, rollback, F(1, 100))
    c = f03_cases.joint_f03_producer(tmp_path / 'sources', 'B')
    assert [cause for _, cause in ego_phases(c.issued)] == ['HOLD', 'REVERSE', 'STOPPING', 'FORWARD_GEAR', 'FORWARD']
    assert 'DESTINATION_CONFIRMED' in {e.name for e in c.events}


def test_rollback_beyond_the_declared_uncertainty_still_blocks(tmp_path, monkeypatch):
    """A real backward move after the gear (0.02 m > 0.01 m) is not noise: the forward phase must not be proven."""
    _rollback(monkeypatch, F(1, 50), F(1, 100))
    with pytest.raises(AssertionError):  # the producer asserts command.kind != 'BLOCKED'
        f03_cases.joint_f03_producer(tmp_path / 'sources', 'B')


def test_zero_uncertainty_is_the_old_rule(tmp_path, monkeypatch):
    """OLD RULE (v19-v21: every b<a step is a reverse step) = uncertainty 0: the same 2.5e-4 m rollback blocks. Red-first control."""
    _rollback(monkeypatch, F(1, 4000), F(0))
    with pytest.raises(AssertionError):
        f03_cases.joint_f03_producer(tmp_path / 'sources', 'B')


def test_forward_phase_still_refuses_hand_brake(tmp_path, monkeypatch):
    _drive(monkeypatch, hand_brake=True)
    with pytest.raises(AssertionError):  # the producer asserts command.kind != 'BLOCKED'
        f03_cases.joint_f03_producer(tmp_path / 'sources', 'B')


def test_old_rule_is_the_bug(tmp_path, monkeypatch):
    """Negative control kept in the suite: with steer 0 (what the synthetic producer always used) both rules agree."""
    _drive(monkeypatch, steer=0.0)
    c = f03_cases.joint_f03_producer(tmp_path / 'sources', 'B')
    assert F(0) == 0 and 'DESTINATION_CONFIRMED' in {e.name for e in c.events}
