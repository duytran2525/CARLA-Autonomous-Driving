"""EGO rollback/reserve response program is not normative merely by self-hashing."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


@pytest.mark.parametrize('mechanism',['F03','F06-ALT1'])
def test_frozen_ego_reverse_program_keeps_bounded_target_and_terminal_order(tmp_path,mechanism):
    from tests.m56.reverse_cases import reverse_case
    from m56.response import _forward_contract
    c=reverse_case(tmp_path/'sources',mechanism=mechanism)
    assert _forward_contract(c.response,c.fixture) is None


@pytest.mark.parametrize('mechanism',['F03','F06-ALT1'])
@pytest.mark.parametrize('fault',['initial','reverse_target','stopping_target','gear_target','forward_zero',
                                 'trigger','delay','gear_before_stop','forward_before_readback',
                                 'extra_guard','lateral','policy','hash_alias'])
def test_self_consistent_ego_reverse_program_cannot_replace_frozen_exception(tmp_path,mechanism,fault):
    from tests.m56.reverse_cases import reverse_case
    from m56.response import _forward_contract
    from m56.catalog import _digest
    c=reverse_case(tmp_path/'sources',mechanism=mechanism);r=c.response;targets=dict(r.targets)
    phases=dict(r.phases);program=dict(phases['program']);rows=list(program['transitions'])
    if fault=='initial':targets['HOLD']=F(1)
    elif fault=='reverse_target':targets['REVERSE']=F(3,5)
    elif fault=='stopping_target':targets['STOPPING']=F(1,5)
    elif fault=='gear_target':targets['FORWARD_GEAR']=F(1)
    elif fault=='forward_zero':targets['FORWARD']=F(0)
    elif fault=='trigger':rows[0]={**rows[0],'after_event':'CAPTURE_START'}
    elif fault=='delay':rows[0]={**rows[0],'delay_s':F(1,20)}
    elif fault=='gear_before_stop':rows[2]={**rows[2],'after_event':'REVERSE_STOPPING_BOUND'}
    elif fault=='forward_before_readback':rows[3]={**rows[3],'after_event':'REVERSE_STOP_CONFIRMED'}
    elif fault=='extra_guard':rows[0]={**rows[0],'requires':('NPC_STOP_CONFIRMED',)}
    elif fault=='lateral':r=replace(r,profile={'method':'quintic-arc-v1','segments':({'start_arc_m':F(0),'length_m':F(18),
        'start_offset_m':F(0),'end_offset_m':F(1,4)},)})
    elif fault=='policy':phases['reverse']={**phases['reverse'],'policy_hash':'e'*64}
    phases['program']={**program,'transitions':tuple(rows)};r=replace(r,targets=targets,phases=phases)
    r=replace(r,hash='a'*64 if fault=='hash_alias' else _digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    with pytest.raises(ValueError):_forward_contract(r,c.fixture)


@pytest.mark.parametrize('mechanism',['F03','F06-ALT1'])
def test_ego_forward_target_is_frozen_positive_not_an_invented_speed_constant(tmp_path,mechanism):
    from tests.m56.reverse_cases import reverse_case
    from m56.response import _forward_contract
    from m56.catalog import _digest
    c=reverse_case(tmp_path/'sources',mechanism=mechanism)
    r=replace(c.response,targets={**c.response.targets,'FORWARD':F(3)})
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    # Definition policy permits a positive frozen forward target. Actual driver,
    # stopping/body/response-hash certificate and source gates are separate; the
    # old c.fixture certificate MUST NOT authorize this changed response torque.
    assert _forward_contract(r,c.fixture) is None
    from m56.response import reverse_intent
    out=reverse_intent(c.frame,c.state,r,c.fixture)
    assert out.command.kind=='BLOCKED'
