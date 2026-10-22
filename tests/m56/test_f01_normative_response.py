"""F01 independent policy, not evidence of actual deceleration/stop/restart."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


def f01_response(action='B',role='EGO',settle=False):
    from tests.m56.response_cases import response_case
    from m56.catalog import _digest
    r=response_case('F',action,role=role).response;nominal=F(4) if role=='EGO' else F(3)
    initial='NOMINAL';targets={'NOMINAL':nominal}
    if role=='EGO':
        targets.update(YIELD=F(0) if action=='A' else F(2),RESUME=F(4))
        rows=[{'cause':'YIELD','after_event':'TRIGGER','delay_s':F(0),'requires':()},
              {'cause':'RESUME','after_event':'N_MOVE','delay_s':F(0),
               'requires':('STOP_AFTER_TRIGGER',) if action=='A' else ()}]
    else:
        targets.update(F01_BRAKE=F(0),NPC_RESTART=F(3))
        rows=[{'cause':'F01_BRAKE','after_event':'F01_BRAKE_MARKER','delay_s':F(0),'requires':()},
              {'cause':'NPC_RESTART','after_event':'NPC_F01_STOP_HOLD_CONFIRMED','delay_s':F(0),'requires':()}]
    if settle:
        initial='SETTLE';targets['SETTLE']=F(0)
        rows.insert(0,{'cause':'NOMINAL','after_event':'CAPTURE_START','delay_s':F(21,20),'requires':()})
    phases={'category':'F','program':{'method':'ordered-event-program-v1','initial':initial,'transitions':tuple(rows)}}
    if role=='NPC':phases.update(f_script={'mechanism':'F01','policy_hash':'2'*64},brake='F01_BRAKE')
    r=replace(r,action_id=action if role=='EGO' else 'NPC_COMMON',targets=targets,phases=phases)
    if role=='NPC':r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    return r,SimpleNamespace(domain=SimpleNamespace(topology={'category':'F','mechanism':'F01'}),policy_hash='2'*64,environment={})


@pytest.mark.parametrize('action,role,settle',[('A','EGO',False),('B','EGO',False),('A','EGO',True),
                                             ('NPC_COMMON','NPC',False),('NPC_COMMON','NPC',True)])
def test_f01_approved_ego_and_common_actual_stop_anchored_npc_policy(action,role,settle):
    from m56.response import _forward_contract
    r,fixture=f01_response(action,role,settle)
    assert _forward_contract(r,fixture) is None


@pytest.mark.parametrize('fault',['nominal','yield','resume','stop_guard','move_anchor','delay','hidden_guard','lateral'])
def test_self_consistent_f01_ego_program_does_not_replace_approved_reaction(fault):
    from m56.response import _forward_contract
    r,fixture=f01_response('A' if fault=='stop_guard' else 'B');targets=dict(r.targets);rows=list(r.phases['program']['transitions'])
    if fault=='nominal':targets['NOMINAL']=F(5)
    elif fault=='yield':targets['YIELD']=F(0)
    elif fault=='resume':targets['RESUME']=F(3)
    elif fault=='stop_guard':rows[1]={**rows[1],'requires':()}
    elif fault=='move_anchor':rows[1]={**rows[1],'after_event':'TRIGGER'}
    elif fault=='delay':rows[0]={**rows[0],'delay_s':F(1,20)}
    elif fault=='hidden_guard':rows[0]={**rows[0],'requires':('STOP_AFTER_TRIGGER',)}
    else:r=replace(r,profile={'method':'quintic-arc-v1','segments':({'start_arc_m':F(0),'length_m':F(18),
            'start_offset_m':F(0),'end_offset_m':F(1,4)},)})
    r=replace(r,targets=targets,phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}})
    with pytest.raises(ValueError,match='NORMATIVE'):_forward_contract(r,fixture)


@pytest.mark.parametrize('fault',['target','brake_anchor','release_command','double_hold_delay','ego_dependent',
                                 'policy','hash_alias','missing_script','brake_label','moving'])
def test_f01_npc_script_cannot_schedule_stop_from_command_or_ego_action(fault):
    from m56.response import _forward_contract
    from m56.catalog import _digest
    r,fixture=f01_response('NPC_COMMON','NPC');phases=dict(r.phases);targets=dict(r.targets)
    program=dict(phases['program']);rows=list(program['transitions'])
    if fault=='target':targets['NPC_RESTART']=F(4)
    elif fault=='brake_anchor':rows[0]={**rows[0],'after_event':'TRIGGER'}
    elif fault=='release_command':rows[1]={**rows[1],'after_event':'NPC_STOP_COMMAND'}
    elif fault=='double_hold_delay':rows[1]={**rows[1],'delay_s':F(2)}
    elif fault=='ego_dependent':rows[1]={**rows[1],'requires':('EGO_STOP_CONFIRMED',)}
    elif fault=='policy':phases['f_script']={'mechanism':'F01','policy_hash':'3'*64}
    elif fault=='missing_script':phases.pop('f_script')
    elif fault=='brake_label':phases['brake']='OTHER'
    elif fault=='moving':r=replace(r,profile={'method':'quintic-arc-v1','segments':({'start_arc_m':F(0),'length_m':F(18),
            'start_offset_m':F(0),'end_offset_m':F(1,4)},)})
    phases['program']={**program,'transitions':tuple(rows)};r=replace(r,targets=targets,phases=phases)
    r=replace(r,hash='a'*64 if fault=='hash_alias' else _digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    with pytest.raises(ValueError):_forward_contract(r,fixture)


def test_f01_actual_stop_and_restart_are_both_needed_by_pure_ego_producer():
    from m56.response import step_response
    from tests.m56.response_cases import response_case
    r,_=f01_response('A');c=response_case('F','A',events=('TRIGGER','N_MOVE'))
    first=step_response(c.frame,c.state,r)
    out=step_response(replace(c.frame,frame=101,simtime=F(21,20),events=()),first.state,r)
    assert out.state.phase=='YIELD' and out.command.target_kmh==0
