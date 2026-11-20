"""v21 (addendum W, docs/m56/PREREG_M56_V21_ADDENDUM_W_20261120.md): the reverse/creep direction checks use a running
envelope with the proof's declared uncertainty instead of zero tolerance (F03 v20 B blocked on a +2.19e-4 m forward
step, F05 v20 B on a -1.16e-7 m backward step). Red under v20 (no _envelope_violation), green under v21."""
from fractions import Fraction as F

U = F(1, 100)


def test_zero_tolerance_is_the_v20_rule():
    from m56.response import _envelope_violation
    assert _envelope_violation((F(5), F(6), F(6), F(7)), 1, 0) is None
    assert _envelope_violation((F(5), F(6), F(6) - F(1, 10**7), F(7)), 1, 0) == 2
    assert _envelope_violation((F(8), F(7), F(7) + F(1, 10**4)), -1, 0) == 2


def test_observed_native_noise_is_within_the_declared_uncertainty():
    from m56.response import _envelope_violation
    # F05 v20 rerun B, frames 3769 -> 3770: -1.164e-7 m at the first CREEP command
    assert _envelope_violation((F(50206386, 10**7), F(50206384, 10**7), F(503, 100)), 1, U) is None
    # F03 v20 B, frames 7557 -> 7558: +2.187e-4 m under brake after reversing 0.477 m
    assert _envelope_violation((F(80371, 10**4), F(78, 10), F(75606, 10**4), F(75608, 10**4)), -1, U) is None


def test_wrong_way_motion_beyond_the_uncertainty_still_fails():
    from m56.response import _envelope_violation
    assert _envelope_violation((F(5), F(6), F(6) - U - F(1, 10**6)), 1, U) == 2
    assert _envelope_violation((F(8), F(7), F(7) + U + F(1, 10**6)), -1, U) == 2


def test_slow_drift_accumulates_against_the_envelope_not_per_step():
    from m56.response import _envelope_violation
    # every step 0.009 m back (each within U), so a per-step tolerance would never fail; the envelope fails at 0.018 m
    drift = tuple(F(6) - k * F(9, 1000) for k in range(5))
    assert _envelope_violation(drift, 1, U) == 2
    assert _envelope_violation(tuple(F(7) + k * F(9, 1000) for k in range(5)), -1, U) == 2
