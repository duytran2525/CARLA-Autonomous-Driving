"""v9 (docs/m56/PREREG_M56_V9_IO_NOMINAL_SERIES_20261107.md): I/O nominal speeds follow the approved k series
vE(k) = 6*(5/4)^(k-1) (FILL20 dd2954c), k in [-4, 8], exact; NPC of an I scene = vE - 1. v8 set = k in {1, 2, 3}."""
from fractions import Fraction as F

from m56.response import _io_nominal_ok


def test_series_values_of_the_catalog_k_admitted():
    for k, v in ((4, F(375, 32)), (0, F(24, 5)), (-1, F(96, 25)), (-2, F(384, 125))):  # 11.71875, 4.8, 3.84, 3.072
        assert v == 6 * F(5, 4) ** (k - 1)
        assert _io_nominal_ok(v) and _io_nominal_ok(v - 1, npc=True)


def test_v8_set_is_exactly_k_1_to_3():
    v8_ego, v8_npc = {F(6), F(15, 2), F(75, 8)}, {F(5), F(13, 2), F(67, 8)}
    assert {6 * F(5, 4) ** (k - 1) for k in (1, 2, 3)} == v8_ego
    assert all(_io_nominal_ok(v) for v in v8_ego) and all(_io_nominal_ok(v, npc=True) for v in v8_npc)


def test_off_series_and_out_of_range_rejected():
    for v in (F(481, 100), F(5), F(10), F(0), F(-6), 6 * F(5, 4) ** 8, 6 * F(5, 4) ** -6):  # k = 9 and k = -5 are out of range
        assert not _io_nominal_ok(v)
    assert not _io_nominal_ok(F(24, 5), npc=True)          # 4.8 is an EGO value; the NPC of that scene is 3.8
    assert not _io_nominal_ok(F(6), npc=True)              # 6 + 1 = 7 is not in the series
    assert not _io_nominal_ok(4.8) and not _io_nominal_ok(None)  # binary64 / missing: never a rescue
