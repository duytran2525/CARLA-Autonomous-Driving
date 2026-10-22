"""Reverse stop-bound law v2 (D3, 2026-10-22): a new versioned method beside v1, never replacing it.

v2 = throttle clamp(hold + gain*(target - v), 0, cap) with hold 29/100, gain 1/5, cap 2/5, target 1/2 m/s;
brake/terminal brake unchanged. Constants were set after the native capability probes A2/A3/A4 (vehicle.audi.a2 does
not move in reverse at the v1 cap 1/4) and before any A/B; v1 stays valid byte for byte.
"""
from dataclasses import replace
from fractions import Fraction as F

import pytest

V2 = {'hold_throttle': F(29, 100), 'gain': F(1, 5), 'throttle_cap': F(2, 5)}


def v2_case(tmp_path, speed, progress=F(0), phase='HOLD', reverse=False, method='bounded-reverse-stop-v2', **changes):
    from tests.m56.reverse_cases import reverse_case
    c = reverse_case(tmp_path/'sources', progress=progress, speed=speed, phase=phase, reverse=reverse,
                     stop_method=method, stop_limits={**V2, **changes})
    return c, c.fixture


@pytest.mark.parametrize('speed,progress,phase,observed_reverse,throttle,brake', [
    (0., F(0), 'HOLD', False, .39, 0.), (.2, F(1, 10), 'REVERSE', True, .35, 0.),
    (.5, F(1, 10), 'REVERSE', True, .29, 0.), (.8, F(1, 10), 'REVERSE', True, .23, .15)])
def test_v2_law_feedforward_and_cap(tmp_path, speed, progress, phase, observed_reverse, throttle, brake):
    from m56.response import reverse_intent
    c, fixture = v2_case(tmp_path, speed, progress, phase, observed_reverse)
    out = reverse_intent(c.frame, c.state, c.response, fixture)
    assert out.state.phase == 'REVERSE' and out.command.kind == 'REVERSE'
    control = out.command.control
    assert control.reverse and control.manual_gear_shift and control.gear == -1 and control.steer == 0
    assert control.throttle == pytest.approx(throttle, abs=1e-15) and control.brake == pytest.approx(brake, abs=1e-15)


@pytest.mark.parametrize('changes', [{'gain': F(1, 4)}, {'throttle_cap': F(1, 2)}, {'hold_throttle': F(3, 10)},
                                     {'hold_throttle': None}])
def test_v2_constants_are_frozen(tmp_path, changes):
    from m56.response import reverse_intent
    c, fixture = v2_case(tmp_path, 0., **changes)  # hold_throttle=None removes the key
    out = reverse_intent(c.frame, c.state, c.response, fixture)
    assert out.command.kind == 'BLOCKED' and out.command.cause == 'REVERSE_STOP_BOUND_INVALID', out.command


def test_unknown_law_method_is_refused(tmp_path):
    from m56.response import reverse_intent
    c, fixture = v2_case(tmp_path, 0., method='bounded-reverse-stop-v9')
    out = reverse_intent(c.frame, c.state, c.response, fixture)
    assert out.command.kind == 'BLOCKED' and out.command.cause == 'REVERSE_STOP_BOUND_MISSING'


def test_consumer_throttle_cap_follows_the_frozen_law(tmp_path):
    from m56.metrics import _reverse_throttle_cap
    from tests.m56.reverse_cases import reverse_case
    c, fixture = v2_case(tmp_path, 0.)
    assert _reverse_throttle_cap(reverse_case(tmp_path/'v1').fixture) == F(1, 4)  # v1 unchanged
    assert _reverse_throttle_cap(fixture) == F(2, 5)
    assert _reverse_throttle_cap(replace(fixture, proofs=())) == F(1, 4)
