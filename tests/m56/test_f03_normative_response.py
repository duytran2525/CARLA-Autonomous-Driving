"""F03 schedules a brake, never manufactures grade rollback with a reverse drive."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


def f03_response(role='NPC',mechanism='F03',forward=True):
    from tests.m56.response_cases import response_case
    from m56.catalog import _digest
    r=response_case('F','A',role=role,events=(),speed=0.).response
    if role=='NPC':
        targets={'UNPOWERED':F(0),'F03_BRAKE':F(0)}
        initial='UNPOWERED'
        rows=({'cause':'F03_BRAKE','after_event':'TRIGGER','delay_s':F(2),'requires':()},)
        phases={'category':'F','f_script':{'mechanism':'F03','policy_hash':'2'*64},'brake':'F03_BRAKE'}
    else:
        initial='HOLD';targets={'HOLD':F(0)};rows=()
        if forward:
            targets['FORWARD']=F(2)
            end='NPC_STOP_CONFIRMED' if mechanism=='F03' else 'NPC_REVERSE_TARGET_STOP_CONFIRMED'
            rows=({'cause':'FORWARD','after_event':end,'delay_s':F(0),'requires':()},)
        phases={'category':'F'}
    phases['program']={'method':'ordered-event-program-v1','initial':initial,'transitions':rows}
    r=replace(r,action_id='NPC_COMMON' if role=='NPC' else 'A',targets=targets,phases=phases)
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    fixture=SimpleNamespace(domain=SimpleNamespace(topology={'category':'F','mechanism':mechanism}),
                            policy_hash='2'*64,environment={})
    return r,fixture


def reseal(r):
    from m56.catalog import _digest
    return replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))


@pytest.mark.parametrize('role,mechanism,forward',[('NPC','F03',True),('EGO','F03',False),('EGO','F03',True),
                                                ('EGO','F06-ALT1',False),('EGO','F06-ALT1',True)])
def test_f03_common_unpowered_then_brake_and_ego_a_hold_policy(role,mechanism,forward):
    from m56.response import _forward_contract
    r,fixture=f03_response(role,mechanism,forward)
    assert _forward_contract(r,fixture) is None


@pytest.mark.parametrize('fault',['powered','reverse','early_brake','late_brake','timer','ego_guard',
                                 'restart','brake_label','lateral','policy','hash_alias'])
def test_self_consistent_f03_npc_cannot_power_or_retime_rollback(fault):
    from m56.response import _forward_contract
    r,fixture=f03_response();targets=dict(r.targets);phases=dict(r.phases);rows=list(phases['program']['transitions'])
    if fault=='powered':targets['UNPOWERED']=F(1,5)
    elif fault=='reverse':targets['UNPOWERED']=-F(1,2)
    elif fault=='early_brake':rows[0]={**rows[0],'delay_s':F(39,20)}
    elif fault=='late_brake':rows[0]={**rows[0],'delay_s':F(41,20)}
    elif fault=='timer':rows[0]={**rows[0],'after_event':'CAPTURE_START'}
    elif fault=='ego_guard':rows[0]={**rows[0],'requires':('EGO_STOP_CONFIRMED',)}
    elif fault=='restart':
        targets['RESTART']=F(2);rows.append({'cause':'RESTART','after_event':'NPC_STOP_CONFIRMED','delay_s':F(0),'requires':()})
    elif fault=='brake_label':phases['brake']='OTHER'
    elif fault=='policy':phases['f_script']={'mechanism':'F03','policy_hash':'3'*64}
    elif fault=='lateral':r=replace(r,profile={'method':'quintic-arc-v1','segments':(
        {'start_arc_m':F(0),'length_m':F(6),'start_offset_m':F(0),'end_offset_m':F(1,4)},)})
    phases['program']={**phases['program'],'transitions':tuple(rows)}
    r=replace(r,targets=targets,phases=phases);r=reseal(r)
    if fault=='hash_alias':r=replace(r,hash='a'*64)
    with pytest.raises(ValueError):_forward_contract(r,fixture)


@pytest.mark.parametrize('mechanism',['F03','F06-ALT1'])
@pytest.mark.parametrize('fault',['initial','drive_on_trigger','stop_command','zero_forward','delay','lateral'])
def test_ego_a_holds_until_actual_peer_end_not_request_or_timer(mechanism,fault):
    from m56.response import _forward_contract
    r,fixture=f03_response('EGO',mechanism);targets=dict(r.targets);rows=list(r.phases['program']['transitions'])
    if fault=='initial':targets['HOLD']=F(1,2)
    elif fault=='drive_on_trigger':rows[0]={**rows[0],'after_event':'TRIGGER'}
    elif fault=='stop_command':rows[0]={**rows[0],'after_event':'NPC_STOP_COMMAND'}
    elif fault=='zero_forward':targets['FORWARD']=F(0)
    elif fault=='delay':rows[0]={**rows[0],'delay_s':F(1,20)}
    else:r=replace(r,profile={'method':'quintic-arc-v1','segments':(
        {'start_arc_m':F(0),'length_m':F(6),'start_offset_m':F(0),'end_offset_m':F(1,4)},)})
    r=reseal(replace(r,targets=targets,phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}}))
    with pytest.raises(ValueError):_forward_contract(r,fixture)


@pytest.mark.parametrize('elapsed,status,brake,phase',[
    (F(39,20),'CLEAR',0.,'UNPOWERED'),(F(2),'CLEAR',.3,'F03_BRAKE'),
    (F(41,20),'CLEAR',.3,'F03_BRAKE'),(F(39,20),'RED',.3,'UNPOWERED'),
    (F(2),'UNKNOWN',.3,'F03_BRAKE')])
def test_f03_actual_producer_coasts_only_until_observed_trigger_plus_two_seconds(elapsed,status,brake,phase):
    from tests.m56.response_cases import response_case
    from m56.model import ScriptState,ControlPacket
    from m56.response import step_response
    r,_=f03_response();c=response_case('F',role='NPC',events=('TRIGGER',),speed=.2)
    c.frame=replace(c.frame,actors=(replace(c.frame.actors[0],readback=ControlPacket(0.,0.,0.,False,False,False,1)),))
    number=100+int(elapsed*20);time=c.frame.simtime+elapsed
    ref=replace(c.ref,frame=number,time=time)
    frame=replace(c.frame,frame=number,simtime=time,events=(),integrity={'npc_controls':
        {'boot':c.frame.boot,'world':c.frame.world,'frame':number,'actor_id':1,'status':status,'witness_refs':(ref,)}})
    out=step_response(frame,ScriptState('UNPOWERED',F(0),c.frame.events),r)
    assert out.state.phase==phase and out.command.kind=='CONTROL',out
    assert out.command.target_kmh==0 and out.command.offset==0
    control=out.command.control
    assert control.throttle==0 and control.brake==brake and control.steer==0
    assert not control.reverse and not control.manual_gear_shift and control.gear==1
    if status!='CLEAR':assert out.command.cause=='NPC_TRAFFIC_HOLD'


@pytest.mark.parametrize('reverse,manual,gear',[(True,True,-1),(False,False,-1)])
def test_unpowered_f03_cannot_treat_observed_reverse_gear_as_grade_rollback(reverse,manual,gear):
    from tests.m56.response_cases import response_case
    from m56.response import step_response
    from m56.model import ScriptState,ControlPacket
    r,_=f03_response();c=response_case('F',role='NPC',events=(),speed=.2)
    actor=replace(c.frame.actors[0],readback=ControlPacket(0.,0.,0.,False,reverse,manual,gear))
    frame=replace(c.frame,actors=(actor,),integrity={'npc_controls':
        {'boot':c.frame.boot,'world':c.frame.world,'frame':100,'actor_id':1,'status':'CLEAR','witness_refs':(c.ref,)}})
    with pytest.raises(ValueError,match='UNPOWERED'):
        step_response(frame,ScriptState('UNPOWERED',F(0),()),r)


def f03_held_response(release_s=F(2)):
    """F03 pre-release hold (2026-10-20, F04-staging style): brake-held until CAPTURE_START+release_s, then the
    unchanged coast -> F03_BRAKE after TRIGGER+2 s."""
    r,fixture=f03_response()
    rows=({'cause':'UNPOWERED','after_event':'CAPTURE_START','delay_s':release_s,'requires':()},
          {'cause':'F03_BRAKE','after_event':'TRIGGER','delay_s':F(2),'requires':()})
    phases={**r.phases,'program':{'method':'ordered-event-program-v1','initial':'NPC_HOLD','transitions':rows}}
    r=reseal(replace(r,targets={'NPC_HOLD':F(0),'UNPOWERED':F(0),'F03_BRAKE':F(0)},phases=phases))
    return r,fixture


def test_f03_npc_pre_release_hold_variant_is_admitted():
    from m56.response import _forward_contract
    r,fixture=f03_held_response()
    assert _forward_contract(r,fixture) is None


@pytest.mark.parametrize('fault',['zero_delay','hold_moves','release_on_trigger','brake_timing','extra_row','order'])
def test_f03_pre_release_hold_cannot_change_coast_or_brake_rules(fault):
    from m56.response import _forward_contract
    r,fixture=f03_held_response();targets=dict(r.targets);rows=list(r.phases['program']['transitions'])
    if fault=='zero_delay':rows[0]={**rows[0],'delay_s':F(0)}
    elif fault=='hold_moves':targets['NPC_HOLD']=F(1,2)
    elif fault=='release_on_trigger':rows[0]={**rows[0],'after_event':'TRIGGER'}
    elif fault=='brake_timing':rows[1]={**rows[1],'delay_s':F(39,20)}
    elif fault=='extra_row':
        targets['RESTART']=F(2);rows.append({'cause':'RESTART','after_event':'NPC_STOP_CONFIRMED','delay_s':F(0),'requires':()})
    else:rows=[rows[1],rows[0]]
    r=reseal(replace(r,targets=targets,phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}}))
    with pytest.raises(ValueError):_forward_contract(r,fixture)
