"""v18 addendum U (docs/m56/PREREG_M56_F05_ADDENDUM_U_20261118.md): a native creep stop counts inside the 1 m
reservation (progress + uncertainty <= 1) after the observed stopping bound; the exact-1 m / zero-uncertainty old rules
are kept and reported in parallel."""
from fractions import Fraction as F
from types import SimpleNamespace

import pytest

from m56.metrics import _creep_reach, _creep_stop_old_rule, _creep_stop_within


@pytest.mark.parametrize('progress,unc,ok,old', [(F(1), F(0), True, True), (F(1), F(1, 1000), False, False),
                                                 (F(83, 100), F(1, 1000), True, False), (F(1001, 1000), F(0), False, False)])
def test_stop_within_reservation(progress, unc, ok, old):
    assert _creep_stop_within(progress, unc) is ok
    assert _creep_stop_old_rule(progress, unc) is old


def test_reach_starts_at_stopping_bound_event():
    bound = {'EGO_CREEP_STOPPING_BOUND': SimpleNamespace(frame=150)}
    assert not _creep_reach(F(7, 10), SimpleNamespace(frame=149), bound)
    assert _creep_reach(F(7, 10), SimpleNamespace(frame=150), bound)
    assert not _creep_reach(F(101, 100), SimpleNamespace(frame=151), bound)
    # no event: old rule (exact 1 m)
    assert _creep_reach(F(1), SimpleNamespace(frame=1), {}) and not _creep_reach(F(99, 100), SimpleNamespace(frame=1), {})
