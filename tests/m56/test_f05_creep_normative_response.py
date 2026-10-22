"""F05 B must remain bounded creep/STOP/observed-clear release, not another wait policy."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


def f05_ego_b():
    from tests.m56.response_cases import response_case
    from m56.catalog import _digest
    r=response_case('F','B',events=(),speed=0.).response
    r=replace(r,targets={'HOLD':F(0),'CREEP':F(1,2),'CREEP_STOP':F(0),'FORWARD':F(2)},
        phases={'category':'F','program':{'method':'ordered-event-program-v1','initial':'HOLD','transitions':(
            {'cause':'CREEP','after_event':'TRIGGER','delay_s':F(0),'requires':()},
            {'cause':'CREEP_STOP','after_event':'EGO_CREEP_STOPPING_BOUND','delay_s':F(0),'requires':()},
            {'cause':'FORWARD','after_event':'N_MOVE','delay_s':F(0),
             'requires':('TRIGGER','EGO_CREEP_STOP_CONFIRMED','QUEUE_CLEAR_CONFIRMED')},)}})
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    fixture=SimpleNamespace(domain=SimpleNamespace(topology={'category':'F','mechanism':'F05'}),
        policy_hash='2'*64,environment={})
    return r,fixture


def test_f05_b_frozen_creep_stop_and_clear_release_program_is_admitted_not_completion():
    from m56.response import _forward_contract
    r,fixture=f05_ego_b()
    assert _forward_contract(r,fixture) is None
    # Event names do not establish actual 1m bounds/STOP/clearance/qualification.


@pytest.mark.parametrize('fault',['initial','creep_speed','stop_target','forward_speed','timer_creep','creep_delay',
    'creep_guard','timer_stop','stop_delay','release_timer','missing_stop','missing_clear','missing_trigger',
    'release_delay','extra_phase','lateral'])
def test_f05_b_self_consistent_definition_cannot_remove_bounded_creep_or_stop_clear(fault):
    from m56.response import _forward_contract
    from m56.catalog import _digest
    r,fixture=f05_ego_b();targets=dict(r.targets);rows=list(r.phases['program']['transitions'])
    if fault=='initial':targets['HOLD']=F(1,2)
    elif fault=='creep_speed':targets['CREEP']=F(1)
    elif fault=='stop_target':targets['CREEP_STOP']=F(1,10)
    elif fault=='forward_speed':targets['FORWARD']=F(3)
    elif fault=='timer_creep':rows[0]={**rows[0],'after_event':'CAPTURE_START'}
    elif fault=='creep_delay':rows[0]={**rows[0],'delay_s':F(1,20)}
    elif fault=='creep_guard':rows[0]={**rows[0],'requires':('N_MOVE',)}
    elif fault=='timer_stop':rows[1]={**rows[1],'after_event':'TRIGGER','delay_s':F(2)}
    elif fault=='stop_delay':rows[1]={**rows[1],'delay_s':F(1,20)}
    elif fault=='release_timer':rows[2]={**rows[2],'after_event':'TRIGGER','delay_s':F(3)}
    elif fault in ('missing_stop','missing_clear','missing_trigger'):
        key={'missing_stop':'EGO_CREEP_STOP_CONFIRMED','missing_clear':'QUEUE_CLEAR_CONFIRMED',
             'missing_trigger':'TRIGGER'}[fault]
        rows[2]={**rows[2],'requires':tuple(k for k in rows[2]['requires'] if k!=key)}
    elif fault=='release_delay':rows[2]={**rows[2],'delay_s':F(1,20)}
    elif fault=='extra_phase':
        targets['FASTER']=F(3);rows.append({'cause':'FASTER','after_event':'F05_END','delay_s':F(0),'requires':()})
    else:r=replace(r,profile={'method':'quintic-arc-v1','segments':(
        {'start_arc_m':F(0),'length_m':F(6),'start_offset_m':F(0),'end_offset_m':F(1,4)},)})
    r=replace(r,targets=targets,phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}})
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    with pytest.raises(ValueError):_forward_contract(r,fixture)


@pytest.mark.parametrize('last,missing,phase,target',[
    (120,None,'CREEP',F(9,5)),
    (186,'EGO_CREEP_STOP_CONFIRMED','CREEP_STOP',F(0)),
    (186,'QUEUE_CLEAR_CONFIRMED','CREEP_STOP',F(0)),
    (186,None,'FORWARD',F(36,5)),
])
def test_f05_b_pure_intent_does_not_resume_without_both_observed_stop_and_clear(tmp_path,last,missing,phase,target):
    from tests.m56.creep_cases import creep_case
    from m56.metrics import detect_events
    from m56.response import step_response
    from m56.model import ScriptState
    c=creep_case(tmp_path/'sources',last=last)
    events=tuple(e for e in detect_events(c.frames,c.fixture) if e.name!=missing)
    frame=replace(c.frame,events=events)
    state=ScriptState('HOLD' if last==120 else 'CREEP_STOP',F(0),())
    out=step_response(frame,state,c.response)
    assert (out.state.phase,out.command.target_kmh,out.command.kind)==(phase,target,'CONTROL')
    assert out.command.offset==0
    if target==0:assert out.command.control.throttle==0 and out.command.control.brake==.3
