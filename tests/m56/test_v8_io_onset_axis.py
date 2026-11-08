"""v8 (docs/m56/PREREG_M56_V8_IO_ONSET_AXIS_20261027.md, Duy 2026-10-27): noise-tolerant lateral onset; axis-signed
lateral separation for the O return guard."""
from fractions import Fraction as F
from types import SimpleNamespace

from m56 import metrics
from m56.model import Transform6
from m56.response import _lateral_separation


def _route(x, y, yaw):
    return SimpleNamespace(transforms=(Transform6(x, y, 0., 0., yaw, 0.),))


def test_separation_follows_the_carla_right_vector_on_every_axis():
    # right vector (-sin yaw, cos yaw): yaw 0 -> +y, yaw 180 -> -y, yaw -90 -> +x
    assert _lateral_separation(_route(0., 3.5, 0.), _route(0., 0., 0.)) == F(7, 2)
    assert _lateral_separation(_route(0., -3.5, 180.), _route(0., 0., 180.)) == F(7, 2)
    assert _lateral_separation(_route(3.5, 0., -90.), _route(0., 0., -90.)) == F(7, 2)
    assert _lateral_separation(_route(0., 3.5, -180.2), _route(0., 0., -180.2)) == -F(7, 2)


def test_sub_uncertainty_jitter_is_skipped_and_the_real_onset_found(monkeypatch):
    frames = tuple(SimpleNamespace(frame=n, integrity={'metric_context': {'map_reference': n}},
                                   actors=(SimpleNamespace(role='EGO', pose=n),)) for n in range(10, 17))
    offsets = {10: F(1, 10000), 11: F(11, 100000), 12: F(9, 100000), 13: F(10, 100000), 14: F(12, 100000),
               15: F(32, 10000), 16: F(80, 10000)}
    monkeypatch.setattr(metrics, '_map_offset', lambda pose, packet, ref: offsets[pose])
    monkeypatch.setattr(metrics, '_continuous_proof', lambda a, b, h: SimpleNamespace(uncertainty=F(1, 1000)))
    monkeypatch.setattr(metrics, '_digest', lambda x: 'h')
    fixture = SimpleNamespace(pair=SimpleNamespace(reference='map:x'))
    onset, unknown = metrics._lateral_departure(frames, fixture, frames[1:])
    assert unknown is None and onset.frame == 15  # v7 stopped at frame 11 (0.01 mm) with LANE_CHANGE_ONSET_UNCERTAIN
