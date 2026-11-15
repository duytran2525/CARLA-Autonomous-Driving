"""v15 (docs/m56/PREREG_M56_CONSUMER_V15_DLC_FLOOR_20261115.md, Duy 2026-11-15, post-number): an EGO I/O lane change is
exactly Dlc = max(3 vE, 18 m) (io-v1.6); the NPC of an I scene keeps exactly 3 vN; the spec 7.4 rule stays as dlc_old_rule."""
from fractions import Fraction as F

from m56.response import _io_dlc, dlc_old_rule


def test_ego_floor_applies_below_6_mps_only():
    for vE, want in ((F(24, 5), F(18)), (F(96, 25), F(18)), (F(384, 125), F(18)), (F(6), F(18)), (F(15, 2), F(45, 2)),
                     (F(375, 32), F(1125, 32))):
        assert _io_dlc(vE) == want and dlc_old_rule(vE) == 3 * vE


def test_npc_keeps_three_vn():
    for vN in (F(5), F(19, 5), F(259, 125)):
        assert _io_dlc(vN, npc=True) == 3 * vN == dlc_old_rule(vN)


def test_result_is_exact_fraction():
    assert type(_io_dlc(F(24, 5))) is F and type(_io_dlc(F(15, 2))) is F
