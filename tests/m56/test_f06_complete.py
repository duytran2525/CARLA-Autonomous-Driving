"""Full joint F06 public SOFTWARE evidence; no native qualification."""
from fractions import Fraction as F

import pytest


@pytest.mark.parametrize('action',['A','B'])
def test_f06_joint_producer_reaches_independent_forward_destination_with_public_witness(tmp_path,action):
    from tests.m56.f06_cases import complete_f06
    from m56.metrics import evaluate_episode
    c=complete_f06(tmp_path/'sources',action)
    verdict=evaluate_episode(c.episode,c.fixture)
    assert (verdict.spawn,verdict.physical,verdict.witness)==('CONFIRMED','COMPLETE','VALID'),verdict
    events={e.name:e for e in verdict.events}
    assert events['TRIGGER'].frame==150
    assert events['NPC_REVERSE_TARGET_STOP_CONFIRMED'].frame==301
    assert events['DESTINATION_CONFIRMED'].frame>303
    assert verdict.metrics['d_reserve_reverse_m'].value==(0 if action=='A' else 1)
    assert verdict.metrics['g_front_min_m'].value==(1 if action=='A' else 2)
    assert all(m.status=='VALID' for m in verdict.metrics.values())
    assert events['DESTINATION_CONFIRMED'].time>events['NPC_REVERSE_TARGET_STOP_CONFIRMED'].time
    # Body/corridor/ground/stopping certificates are synthetic author receipts;
    # actual stock/native dynamics/visible gear cue remain separately blocked.
