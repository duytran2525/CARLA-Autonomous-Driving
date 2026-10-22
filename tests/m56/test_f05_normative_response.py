"""F05 common queue release is fixed three seconds, never an EGO-triggered restart."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


def f05_ego_a():
    from tests.m56.response_cases import response_case
    r=response_case('F','A',events=(),speed=0.).response
    r=replace(r,targets={'HOLD':F(0),'FORWARD':F(2)},phases={'category':'F',
        'program':{'method':'ordered-event-program-v1','initial':'HOLD','transitions':(
            {'cause':'FORWARD','after_event':'NPC_ADVANCE_2M_CONFIRMED','delay_s':F(0),'requires':('TRIGGER',)},)}})
    return r,SimpleNamespace(domain=SimpleNamespace(topology={'category':'F','mechanism':'F05'}),
                             policy_hash='2'*64,environment={})


def f05_response():
    from tests.m56.response_cases import response_case
    from m56.catalog import _digest
    r=response_case('F',role='NPC',events=(),speed=0.).response
    r=replace(r,action_id='NPC_COMMON',targets={'NPC_QUEUE_HOLD':F(0),'NPC_QUEUE_FORWARD':F(2)},
        phases={'category':'F','f_script':{'mechanism':'F05','policy_hash':'2'*64},
            'program':{'method':'ordered-event-program-v1','initial':'NPC_QUEUE_HOLD','transitions':(
                {'cause':'NPC_QUEUE_FORWARD','after_event':'TRIGGER','delay_s':F(3),'requires':()},)}})
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    return r,SimpleNamespace(domain=SimpleNamespace(topology={'category':'F','mechanism':'F05'}),
                             policy_hash='2'*64,environment={})


def test_f05_ego_a_requires_actual_two_metre_body_advance():
    from m56.response import _forward_contract
    r,fixture=f05_ego_a()
    assert _forward_contract(r,fixture) is None


@pytest.mark.parametrize('fault',['initial','target','move_only','release_command','missing_trigger','delay','lateral'])
def test_f05_self_consistent_a_cannot_resume_from_release_command_or_first_move(fault):
    from m56.response import _forward_contract
    r,fixture=f05_ego_a();targets=dict(r.targets);rows=list(r.phases['program']['transitions'])
    if fault=='initial':targets['HOLD']=F(1,2)
    elif fault=='target':targets['FORWARD']=F(3)
    elif fault=='move_only':rows[0]={**rows[0],'after_event':'N_MOVE'}
    elif fault=='release_command':rows[0]={**rows[0],'after_event':'NPC_RELEASE_COMMAND'}
    elif fault=='missing_trigger':rows[0]={**rows[0],'requires':()}
    elif fault=='delay':rows[0]={**rows[0],'delay_s':F(1,20)}
    else:r=replace(r,profile={'method':'quintic-arc-v1','segments':(
        {'start_arc_m':F(0),'length_m':F(6),'start_offset_m':F(0),'end_offset_m':F(1,4)},)})
    r=replace(r,targets=targets,phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}})
    with pytest.raises(ValueError):_forward_contract(r,fixture)


def test_f05_canonical_common_hold_three_seconds_then_forward_two():
    from m56.response import _forward_contract
    r,fixture=f05_response()
    assert _forward_contract(r,fixture) is None


@pytest.mark.parametrize('fault',['initial','forward','early','late','ego_anchor','ego_guard','missing',
                                 'policy','hash','lateral','extra_phase'])
def test_self_consistent_f05_script_cannot_retime_or_condition_on_ego(fault):
    from m56.response import _forward_contract
    from m56.catalog import _digest
    r,fixture=f05_response();targets=dict(r.targets);phases=dict(r.phases);rows=list(phases['program']['transitions'])
    if fault=='initial':targets['NPC_QUEUE_HOLD']=F(1,2)
    elif fault=='forward':targets['NPC_QUEUE_FORWARD']=F(3)
    elif fault=='early':rows[0]={**rows[0],'delay_s':F(59,20)}
    elif fault=='late':rows[0]={**rows[0],'delay_s':F(61,20)}
    elif fault=='ego_anchor':rows[0]={**rows[0],'after_event':'EGO_CREEP_STOP_CONFIRMED'}
    elif fault=='ego_guard':rows[0]={**rows[0],'requires':('EGO_CREEP_STOP_CONFIRMED',)}
    elif fault=='missing':phases.pop('f_script')
    elif fault=='policy':phases['f_script']={'mechanism':'F05','policy_hash':'3'*64}
    elif fault=='extra_phase':
        targets['FASTER']=F(3);rows.append({'cause':'FASTER','after_event':'N_MOVE','delay_s':F(0),'requires':()})
    elif fault=='lateral':r=replace(r,profile={'method':'quintic-arc-v1','segments':(
        {'start_arc_m':F(0),'length_m':F(6),'start_offset_m':F(0),'end_offset_m':F(1,4)},)})
    phases['program']={**phases['program'],'transitions':tuple(rows)};r=replace(r,targets=targets,phases=phases)
    r=replace(r,hash='a'*64 if fault=='hash' else _digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    with pytest.raises(ValueError):_forward_contract(r,fixture)


@pytest.mark.parametrize('elapsed,status,target',[(F(59,20),'CLEAR',F(0)),(F(3),'CLEAR',F(36,5)),
                                                (F(61,20),'CLEAR',F(36,5)),(F(3),'RED',F(0)),
                                                (F(3),'UNKNOWN',F(0))])
def test_f05_pure_common_release_preserves_clock_and_actual_stock_priority(elapsed,status,target):
    from tests.m56.response_cases import response_case
    from m56.model import ScriptState
    from m56.response import step_response
    r,_=f05_response();c=response_case('F',role='NPC',events=('TRIGGER',),speed=0.)
    number=100+int(elapsed*20);time=c.frame.simtime+elapsed;ref=replace(c.ref,frame=number,time=time)
    frame=replace(c.frame,frame=number,simtime=time,events=(),integrity={'npc_controls':
        {'boot':c.frame.boot,'world':c.frame.world,'frame':number,'actor_id':1,'status':status,'witness_refs':(ref,)}})
    out=step_response(frame,ScriptState('NPC_QUEUE_HOLD',F(0),c.frame.events),r)
    assert out.command.kind=='CONTROL' and out.command.target_kmh==target,out
    assert out.state.phase==('NPC_QUEUE_HOLD' if elapsed<3 else 'NPC_QUEUE_FORWARD')
    assert out.command.offset==0
    if target==0:assert out.command.control.throttle==0 and out.command.control.brake==.3
    else:assert out.command.control is None
