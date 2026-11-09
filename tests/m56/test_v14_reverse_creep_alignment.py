"""v14 (docs/m56/PLAN_M56_F_REVERSE_CREEP_V14_20261109.md 2): reverse/creep alignment on a native straight world-axis
route (yaw 1 deg, spawn-relative pitch/roll 0.5 deg, lateral 0.15 m); the v13 exact +x rule is kept as the old rule."""
from fractions import Fraction as F

import pytest

from m56.model import DirectedRoute, LaneRef, Transform6
from m56.response import _v13_exact_x_alignment, _v14_aligned, _v14_axis_route


def route(points, yaw):
    ts = tuple(Transform6(x, y, 0., 0., yaw, 0.) for x, y in points)
    arc, a = [F(0)], 0.
    for p, q in zip(points, points[1:]):
        a += ((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** .5; arc.append(F(round(a * 10 ** 6), 10 ** 6))
    return DirectedRoute((LaneRef('Town12', '164', 0, -2, F(0)),), ts, tuple(arc), 'a' * 64, (), arc[-1] - 5)


NATIVE = route([(4500. + .002 * i, 5000. - 2. * i) for i in range(60)], 270.3)  # -y travel, 0.06 deg drift
SPAWN = Transform6(4500., 5000., .01, .8, 270.3, -.4)


def pose(**kw):
    base = dict(x=4500.02, y=4950., z=.01, pitch=.8, yaw=270.4, roll=-.4)
    base.update(kw)
    return Transform6(**base)


def test_native_axis_route_recognised():
    assert _v14_axis_route(NATIVE) == (0, 1)


def test_native_pose_aligned():
    assert _v14_aligned(NATIVE, pose(), SPAWN)
    assert not _v13_exact_x_alignment(NATIVE, pose())  # the old rule always blocks a native route


@pytest.mark.parametrize('kw', [{'x': 4500.3}, {'pitch': 1.4}, {'roll': -1.0}, {'yaw': 268.5}, {'yaw': 90.4}])
def test_misaligned_pose_blocked(kw):
    assert not _v14_aligned(NATIVE, pose(**kw), SPAWN)


def test_non_axis_or_reversing_route_blocked():
    assert _v14_axis_route(route([(0., 0.), (10., 1.), (20., 2.)], 5.7)) is None
    assert _v14_axis_route(route([(0., 0.), (10., 0.), (5., 0.)], 0.)) is None


def test_v13_synthetic_shape_still_aligned():
    r = route([(0., 0.), (50., 0.)], 0.)
    zero = Transform6(10., 0., 0., 0., 0., 0.)
    assert _v13_exact_x_alignment(r, zero) and _v14_aligned(r, zero, zero)
