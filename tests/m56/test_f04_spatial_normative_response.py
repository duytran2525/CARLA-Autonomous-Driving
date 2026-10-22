"""F04 B is a lawful within-lane pass/return, not a self-consistent arbitrary speed/lane policy."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


def f04_ego_b():
    from tests.m56.response_cases import response_case
    from m56.catalog import _digest
    r=response_case('F','B',events=(),speed=1.).response
    r=replace(r,targets={'NOMINAL':F(2),'PASS':F(1),'RETURN':F(1),'FORWARD':F(2)},
        profile={'method':'quintic-arc-v1','segments':(
            {'start_arc_m':F(0),'length_m':F(6),'start_offset_m':F(0),'end_offset_m':F(3,4)},
            {'start_arc_m':F(12),'length_m':F(6),'start_offset_m':F(3,4),'end_offset_m':F(0)},)},
        phases={'category':'F','program':{'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':(
            {'cause':'PASS','after_event':'TRIGGER','delay_s':F(0),'requires':('LANE_CHANGE_PATH_CLEAR',)},
            {'cause':'RETURN','after_event':'F04_RETURN_MARKER','delay_s':F(0),'requires':('F04_END','F04_OFFSET_CONFIRMED','RETURN_PATH_CLEAR')},
            {'cause':'FORWARD','after_event':'F04_HOME_CONFIRMED','delay_s':F(0),'requires':('F04_RETURN_REFERENCE_MARKER',)},)}})
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    fixture=SimpleNamespace(domain=SimpleNamespace(topology={'category':'F','mechanism':'F04'}),
        environment={},policy_hash='2'*64)
    return r,fixture


def test_f04_b_admits_only_nominal_two_pass_one_and_observed_within_lane_return():
    from m56.response import _forward_contract
    r,fixture=f04_ego_b()
    assert _forward_contract(r,fixture) is None


@pytest.mark.parametrize('fault',['nominal','pass_speed','return_speed','forward_speed','timer','start_delay',
    'no_path','early_return','no_passed_door','no_actual_offset','no_return_path','return_delay','no_actual_home','no_marker',
    'forward_delay','extra','offset','length','no_return'])
def test_f04_b_self_consistent_program_does_not_approve_wrong_pass_or_return(fault):
    from m56.response import _forward_contract
    from m56.catalog import _digest
    r,fixture=f04_ego_b();targets=dict(r.targets);rows=list(r.phases['program']['transitions']);segments=list(r.profile['segments'])
    if fault=='nominal':targets['NOMINAL']=F(3)
    elif fault=='pass_speed':targets['PASS']=F(2)
    elif fault=='return_speed':targets['RETURN']=F(2)
    elif fault=='forward_speed':targets['FORWARD']=F(3)
    elif fault=='timer':rows[0]={**rows[0],'after_event':'CAPTURE_START'}
    elif fault=='start_delay':rows[0]={**rows[0],'delay_s':F(1,20)}
    elif fault=='no_path':rows[0]={**rows[0],'requires':()}
    elif fault=='early_return':rows[1]={**rows[1],'after_event':'TRIGGER'}
    elif fault=='no_passed_door':rows[1]={**rows[1],'requires':('F04_OFFSET_CONFIRMED','RETURN_PATH_CLEAR')}
    elif fault=='no_actual_offset':rows[1]={**rows[1],'requires':('F04_END','RETURN_PATH_CLEAR')}
    elif fault=='no_return_path':rows[1]={**rows[1],'requires':('F04_END','F04_OFFSET_CONFIRMED')}
    elif fault=='return_delay':rows[1]={**rows[1],'delay_s':F(1,20)}
    elif fault=='no_actual_home':rows[2]={**rows[2],'after_event':'F04_END'}
    elif fault=='no_marker':rows[2]={**rows[2],'requires':()}
    elif fault=='forward_delay':rows[2]={**rows[2],'delay_s':F(1,20)}
    elif fault=='extra':
        targets['FASTER']=F(3);rows.append({'cause':'FASTER','after_event':'DESTINATION_CONFIRMED','delay_s':F(0),'requires':()})
    elif fault=='offset':segments[0]={**segments[0],'end_offset_m':F(1)};segments[1]={**segments[1],'start_offset_m':F(1)}
    elif fault=='length':segments[0]={**segments[0],'length_m':F(5)}
    else:segments=segments[:1]
    r=replace(r,targets=targets,profile={**r.profile,'segments':tuple(segments)},
        phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}})
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    with pytest.raises(ValueError):_forward_contract(r,fixture)


@pytest.mark.parametrize('returning,permission',[(False,'missing'),(False,'stale'),(False,'current'),
                                               (True,'missing'),(True,'stale'),(True,'current'),(True,'missing_offset')])
def test_f04_spatial_producer_requires_current_path_for_each_outbound_and_return_intent(returning,permission):
    from tests.m56.response_cases import response_case
    from m56.model import ScriptState
    from m56.response import step_response
    names=('TRIGGER','F04_END','F04_RETURN_MARKER','F04_OFFSET_CONFIRMED') if returning else ('TRIGGER',)
    if permission=='missing_offset':names=tuple(n for n in names if n!='F04_OFFSET_CONFIRMED')
    path='RETURN_PATH_CLEAR' if returning else 'LANE_CHANGE_PATH_CLEAR'
    c=response_case('F','B',events=(*names,path) if permission!='missing' else names,speed=1.)
    r,_=f04_ego_b();frame=c.frame
    if returning:frame=replace(frame,actors=(replace(frame.actors[0],pose=replace(frame.actors[0].pose,x=15.)),))
    if permission=='stale':
        event=frame.events[-1];ref=replace(c.ref,frame=99,time=F(19,20))
        event=replace(event,frame=99,time=F(19,20),witness_refs=(ref,))
        frame=replace(frame,events=(*frame.events[:-1],event))
    state=ScriptState('RETURN' if returning else 'PASS',F(0),())
    if permission!='current':
        with pytest.raises(ValueError):step_response(frame,state,r)
    else:
        out=step_response(frame,state,r)
        assert out.command.kind=='CONTROL' and out.command.target_kmh==F(18,5)
        assert out.command.offset==(F(3,8) if returning else F(16,27))
        assert out.state.phase==('RETURN' if returning else 'PASS')
