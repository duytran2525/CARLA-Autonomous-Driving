"""v7 (docs/m56/PREREG_M56_V7_FIT_20261026.md): rotation-aware CONTINUOUS_FIT."""
from types import SimpleNamespace

from shapely.geometry import LineString
from shapely.prepared import prep

from m56.evidence import _oriented_fit
from m56.model import BodyRecord, SourceRef, Transform6

REF = SourceRef('synthetic://v7', 'a' * 64, 1, 'test', 'literal', 'SYNTHETIC_TEST')
BODY = BodyRecord((0., 0., 0.), (0., 0., 0.), (1.85, .9, .75), (), 'vehicle.audi.a2', {}, {}, REF)


def actor(x, y, yaw):
    return SimpleNamespace(body=BODY, pose=Transform6(x, y, 0., 0., yaw, 0.))


# a 4.0 m wide lane along the 45 degree diagonal
LANE = prep(LineString([(-50., -50.), (50., 50.)]).buffer(2.))


def test_a_diagonal_body_centred_in_its_lane_fits():
    # v6 would fail here: the axis-aligned box of a 3.7 x 1.8 m body at 45 deg is about 3.9 x 3.9 m
    assert _oriented_fit(actor(0., 0., 45.), actor(.2, .2, 45.), LANE, .151)


def test_a_body_off_the_lane_does_not_fit():
    assert not _oriented_fit(actor(1.2, -1.2, 45.), actor(1.4, -1.0, 45.), LANE, .151)


def test_the_margin_is_enforced():
    # half width 0.9 m in a 2 m half-lane leaves 1.1 m: fits at 1.0 m margin, not at 1.2 m
    assert _oriented_fit(actor(0., 0., 45.), actor(0., 0., 45.), LANE, 1.0)
    assert not _oriented_fit(actor(0., 0., 45.), actor(0., 0., 45.), LANE, 1.2)
