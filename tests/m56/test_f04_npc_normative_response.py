"""F04 common parked NPC emits OWNED door requests, not articulation or native API success."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest
from tests.m56.test_stock_adapter import stock_case


def f04_npc_response():
    from tests.m56.response_cases import response_case
    from m56.catalog import _digest
    r=response_case('F','NPC_COMMON',role='NPC',events=(),speed=0.).response
    r=replace(r,targets={'NPC_DOOR_CLOSED_HOLD':F(0),'NPC_DOOR_OPEN':F(0),'NPC_DOOR_CLOSED':F(0)},
        phases={'category':'F','f_script':{'mechanism':'F04','policy_hash':'2'*64},
            'door':{'method':'owned-door-request-v1','selector':'reviewed-panel-alpha'},
            'program':{'method':'ordered-event-program-v1','initial':'NPC_DOOR_CLOSED_HOLD','transitions':(
                {'cause':'NPC_DOOR_OPEN','after_event':'CAPTURE_START','delay_s':F(0),'requires':()},
                {'cause':'NPC_DOOR_CLOSED','after_event':'TRIGGER','delay_s':F(3),'requires':()},)}})
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    fixture=SimpleNamespace(domain=SimpleNamespace(topology={'category':'F','mechanism':'F04'}),environment={},policy_hash='2'*64)
    return r,fixture


def f04_npc_case():
    from tests.m56.response_cases import response_case
    from m56.model import ControlPacket
    c=response_case('F','NPC_COMMON',role='NPC',events=('CAPTURE_START',),speed=0.)
    actor=replace(c.frame.actors[0],readback=ControlPacket(0.,0.,.3,False,False,False,1))
    c.frame=replace(c.frame,actors=(actor,),integrity={'npc_controls':{'boot':c.frame.boot,'world':c.frame.world,
        'frame':c.frame.frame,'actor_id':actor.id,'status':'CLEAR','witness_refs':(c.ref,)}})
    return c


def test_f04_common_npc_policy_requires_reviewed_explicit_selector_and_fixed_actual_cue_close_clock():
    from m56.response import _forward_contract
    r,fixture=f04_npc_response()
    assert _forward_contract(r,fixture) is None
    with pytest.raises(ValueError):_forward_contract(r,replace_fixture_policy(fixture,'3'*64))


def replace_fixture_policy(fixture,policy):
    return SimpleNamespace(domain=fixture.domain,environment=fixture.environment,policy_hash=policy)


@pytest.mark.parametrize('fault',['missing_script','missing_selector','empty_selector','unknown_door_field','wrong_role','ego_action',
    'extra_metadata','changed_delay','timer_close','closed_on_command','extra_guard','positive_target','initial_target',
    'lateral','reference_switch','extra_phase','missing_close','hash_alias'])
def test_f04_self_consistent_npc_configuration_cannot_redefine_door_or_close_clock(fault):
    from m56.response import _forward_contract
    from m56.catalog import _digest
    r,fixture=f04_npc_response();phases=dict(r.phases);targets=dict(r.targets);profile=dict(r.profile)
    rows=list(phases['program']['transitions']);role=r.actor_role
    if fault=='missing_script':phases.pop('f_script')
    elif fault=='missing_selector':phases.pop('door')
    elif fault=='empty_selector':phases['door']={**phases['door'],'selector':''}
    elif fault=='unknown_door_field':phases['door']={**phases['door'],'ego_action':'A'}
    elif fault=='wrong_role':r=replace(r,action_id='A')
    elif fault=='ego_action':phases['f_script']={**phases['f_script'],'ego_action':'B'}
    elif fault=='extra_metadata':phases['ego_action']='A'
    elif fault=='changed_delay':rows[1]={**rows[1],'delay_s':F(5,2)}
    elif fault=='timer_close':rows[1]={**rows[1],'after_event':'CAPTURE_START'}
    elif fault=='closed_on_command':rows[1]={**rows[1],'after_event':'DOOR_OPEN_REQUEST'}
    elif fault=='extra_guard':rows[1]={**rows[1],'requires':('STOP_AFTER_TRIGGER',)}
    elif fault=='positive_target':targets['NPC_DOOR_OPEN']=F(1)
    elif fault=='initial_target':targets['NPC_DOOR_CLOSED_HOLD']=F(1)
    elif fault=='lateral':profile['segments']=({**profile['segments'][0],'end_offset_m':F(1,4)},)
    elif fault=='reference_switch':phases['reference_switches']=({'cause':'NPC_DOOR_CLOSED'},)
    elif fault=='extra_phase':
        targets['FORWARD']=F(2);rows.append({'cause':'FORWARD','after_event':'F04_END','delay_s':F(0),'requires':()})
    elif fault=='missing_close':rows=rows[:1]
    phases['program']={**phases['program'],'transitions':tuple(rows)}
    r=replace(r,actor_role=role,targets=targets,profile=profile,phases=phases)
    r=replace(r,hash='f'*64 if fault=='hash_alias' else _digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    with pytest.raises(ValueError):_forward_contract(r,fixture)


def test_f04_frozen_initialization_staging_does_not_change_actual_intrusion_three_second_close_clock():
    from m56.catalog import _digest
    from m56.model import ScriptState
    from m56.response import _forward_contract,step_response
    r,fixture=f04_npc_response();rows=list(r.phases['program']['transitions'])
    rows[0]={**rows[0],'delay_s':F(31,20)}
    r=replace(r,phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}})
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    assert _forward_contract(r,fixture) is None
    c=f04_npc_case();capture=c.frame.events[0];state=ScriptState('NPC_DOOR_CLOSED_HOLD',F(0),(capture,))
    for number,kind in ((130,'CONTROL'),(131,'DOOR_OPEN_REQUEST')):
        time=F(1)+F(number-100,20);ref=replace(c.ref,frame=number,time=time)
        traffic={**c.frame.integrity['npc_controls'],'frame':number,'witness_refs':(ref,)}
        out=step_response(replace(c.frame,frame=number,simtime=time,events=(),integrity={'npc_controls':traffic}),state,r)
        assert out.command.kind==kind and out.command.target_kmh==0
        state=out.state
    trigger=replace(capture,name='TRIGGER',frame=132,time=F(13,5),witness_refs=(replace(c.ref,frame=132,time=F(13,5)),))
    state=replace(state,events=(*state.events,trigger))
    for number,kind in ((191,'CONTROL'),(192,'DOOR_CLOSE_REQUEST')):
        time=F(1)+F(number-100,20);ref=replace(c.ref,frame=number,time=time)
        traffic={**c.frame.integrity['npc_controls'],'frame':number,'witness_refs':(ref,)}
        out=step_response(replace(c.frame,frame=number,simtime=time,events=(),integrity={'npc_controls':traffic}),state,r)
        assert out.command.kind==kind and out.command.target_kmh==0
        state=out.state
    assert not any(e.name=='DOOR_CLOSED_CLEAR_CONFIRMED' for e in state.events)


def test_f04_npc_open_and_close_are_once_only_requests_with_full_stationary_hold():
    from tests.m56.response_cases import response_case
    from m56.model import ScriptState,EventRecord
    from m56.response import step_response
    r,_=f04_npc_response();c=f04_npc_case()
    state=ScriptState('NPC_DOOR_CLOSED_HOLD',F(0),())
    opened=step_response(c.frame,state,r)
    assert opened.command.kind=='DOOR_OPEN_REQUEST' and opened.state.phase=='NPC_DOOR_OPEN'
    assert opened.command.target_kmh==0 and opened.command.offset==0 and opened.command.light_state is None
    assert (opened.command.control.throttle,opened.command.control.steer,opened.command.control.brake)==(0.,0.,.3)
    trigger=EventRecord('TRIGGER',100,F(1),(c.ref,))
    state=replace(opened.state,events=(*opened.state.events,trigger))
    def frame_at(number,time):
        ref=replace(c.ref,frame=number,time=time)
        traffic={**c.frame.integrity['npc_controls'],'frame':number,'witness_refs':(ref,)}
        return replace(c.frame,frame=number,simtime=time,events=(),integrity={'npc_controls':traffic})
    before=step_response(frame_at(159,F(79,20)),state,r)
    assert before.command.kind=='CONTROL' and before.state.phase=='NPC_DOOR_OPEN'
    closed=step_response(frame_at(160,F(4)),before.state,r)
    assert closed.command.kind=='DOOR_CLOSE_REQUEST' and closed.state.phase=='NPC_DOOR_CLOSED'
    after=step_response(frame_at(161,F(81,20)),closed.state,r)
    assert after.command.kind=='CONTROL' and after.command.target_kmh==0
    assert (after.command.control.throttle,after.command.control.brake)==(0.,.3)
    assert closed.command.response_hash==opened.command.response_hash==r.hash
    assert not any(e.name=='DOOR_CLOSED_CLEAR_CONFIRMED' for e in after.state.events)


@pytest.mark.parametrize('status',['RED','UNKNOWN'])
def test_f04_parked_door_clock_not_retimed_by_motor_traffic_hold(status):
    from m56.model import ScriptState
    from m56.response import step_response
    r,_=f04_npc_response();c=f04_npc_case()
    traffic={**c.frame.integrity['npc_controls'],'status':status}
    frame=replace(c.frame,integrity={'npc_controls':traffic})
    opened=step_response(frame,ScriptState('NPC_DOOR_CLOSED_HOLD',F(0),()),r)
    assert opened.command.kind=='DOOR_OPEN_REQUEST' and opened.command.cause=='NPC_DOOR_OPEN'
    ref=replace(c.ref,frame=160,time=F(4));trigger=replace(c.frame.events[0],name='TRIGGER')
    frame=replace(frame,frame=160,simtime=F(4),events=(),integrity={'npc_controls':{**traffic,'frame':160,'witness_refs':(ref,)}})
    closed=step_response(frame,replace(opened.state,events=(*opened.state.events,trigger)),r)
    assert closed.command.kind=='DOOR_CLOSE_REQUEST' and closed.command.cause=='NPC_DOOR_CLOSED'
    assert closed.command.target_kmh==0 and closed.command.control.throttle==0 and closed.command.control.brake==.3


@pytest.mark.parametrize('fault',['moving','missing_readback','reverse','manual','negative_gear','steer','handbrake'])
def test_f04_request_does_not_override_unproven_stationary_forward_actor_readback(fault):
    from tests.m56.response_cases import response_case
    from m56.model import ScriptState
    from m56.response import step_response
    r,_=f04_npc_response();c=f04_npc_case()
    actor=c.frame.actors[0]
    if fault=='moving':actor=replace(actor,velocity=(1.,0.,0.))
    elif fault=='missing_readback':actor=replace(actor,readback=None)
    else:
        field={'reverse':{'reverse':True},'manual':{'manual_gear_shift':True},'negative_gear':{'gear':-1},
               'steer':{'steer':.1},'handbrake':{'hand_brake':True}}[fault]
        actor=replace(actor,readback=replace(actor.readback,**field))
    with pytest.raises(ValueError):step_response(replace(c.frame,actors=(actor,)),ScriptState('NPC_DOOR_CLOSED_HOLD',F(0),()),r)


def test_door_request_cannot_be_routed_through_stock_pid_or_be_a_calibrated_articulation(stock_case):
    from tests.m56.response_cases import response_case
    from m56.model import ScriptState
    from m56.response import step_response,apply_intent
    r,_=f04_npc_response();c=f04_npc_case()
    request=step_response(c.frame,ScriptState('NPC_DOOR_CLOSED_HOLD',F(0),()),r).command
    s=stock_case;driver=s.create(s.actor,r,s.policy_for(r,{}));calls=tuple(s.calls)
    with pytest.raises(ValueError):apply_intent(driver,request)
    assert tuple(s.calls)==calls
