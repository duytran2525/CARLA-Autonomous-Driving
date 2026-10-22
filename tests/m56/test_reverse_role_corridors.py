"""Joint EGO/NPC reverse needs distinct current role-owned corridor receipts."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


@pytest.mark.parametrize('role',['EGO','NPC'])
def test_joint_role_corridor_selects_own_proof_without_overwriting_other_actor_authority(tmp_path,role):
    from tests.m56.reverse_cases import reverse_case
    from m56.response import reverse_intent
    c=reverse_case(tmp_path/'sources',role=role,waiting_s=F(3) if role=='NPC' else F(0))
    proof=c.frame.integrity['reverse_corridor']
    fields={k:v for k,v in c.frame.integrity.items() if k!='reverse_corridor'}
    fields['reverse_corridors']={role:proof}
    out=reverse_intent(replace(c.frame,integrity=fields),c.state,c.response,c.fixture)
    assert out.command.kind=='REVERSE',out.state
    assert out.command.actor==(1 if role=='EGO' else 2)
    assert out.command.target_kmh==F(9,5)
    assert out.command.control.reverse and out.command.control.manual_gear_shift and out.command.control.gear==-1


@pytest.mark.parametrize('fault',['missing_own','foreign_key','mixed_legacy','not_mapping'])
def test_role_corridor_cannot_use_other_actor_or_ambiguous_legacy_authority(tmp_path,fault):
    from tests.m56.reverse_cases import reverse_case
    from m56.response import reverse_intent
    c=reverse_case(tmp_path/'sources');proof=c.frame.integrity['reverse_corridor']
    fields={k:v for k,v in c.frame.integrity.items() if k!='reverse_corridor'}
    fields['reverse_corridors']={} if fault=='missing_own' else {'PEDESTRIAN':proof} if fault=='foreign_key' else {'EGO':proof}
    if fault=='mixed_legacy':fields['reverse_corridor']=proof
    elif fault=='not_mapping':fields['reverse_corridors']=(proof,)
    out=reverse_intent(replace(c.frame,integrity=fields),c.state,c.response,c.fixture)
    assert out.command.kind=='BLOCKED' and out.state.phase=='BLOCKED_CONTROLLER'
