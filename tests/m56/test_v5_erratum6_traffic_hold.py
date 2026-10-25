"""Erratum 6 (2026-10-26): the producer's NPC_TRAFFIC_HOLD command (0 km/h) is a frozen-target match, not a mismatch."""
from fractions import Fraction as F
from types import SimpleNamespace

from m56.evidence import _target_integrity
from m56.model import CommandRecord


def _evidence(role, cause, kmh):
    command = CommandRecord(actor=7, frame=1, next_frame=2, kind='CONTROL', target_kmh=kmh, offset=F(0), control=None,
                            light_state=None, cause=cause, response_hash='h' * 64)
    actor = SimpleNamespace(role=role, commands=(command,))
    fixture = SimpleNamespace(responses=(SimpleNamespace(actor_role=role, hash='h' * 64,
                                                         targets={'SETTLE': F(0), 'NOMINAL': F(3)}),))
    return SimpleNamespace(raw=(SimpleNamespace(actors=(actor,)),)), fixture


def test_npc_traffic_hold_at_zero_is_a_target_match():
    assert _target_integrity(*_evidence('NPC', 'NPC_TRAFFIC_HOLD', F(0))) == ((), ())


def test_traffic_hold_still_mismatches_off_zero_or_for_ego():
    assert _target_integrity(*_evidence('NPC', 'NPC_TRAFFIC_HOLD', F(1)))[0] == ('TARGET_PROGRAM_MISMATCH',)
    assert _target_integrity(*_evidence('EGO', 'NPC_TRAFFIC_HOLD', F(0)))[0] == ('TARGET_PROGRAM_MISMATCH',)
    assert _target_integrity(*_evidence('NPC', 'NOMINAL', F(54, 5)))[0] == ()  # 3 m/s = 10.8 km/h
