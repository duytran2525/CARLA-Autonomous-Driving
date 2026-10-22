"""Real forward producer must have bounded F05 context BEFORE requesting stock torque."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


def observed_step(c,phase='HOLD',event_override=None):
    from m56.metrics import detect_events
    from m56.model import ScriptState
    from m56.response import step_response
    events=detect_events(c.frames,c.fixture) if event_override is None else event_override
    return step_response(replace(c.frame,events=events),ScriptState(phase,F(0),()),c.response)


def test_f05_named_trigger_alone_cannot_request_creep_without_source_bound_stopping_admission():
    from tests.m56.test_f05_creep_normative_response import f05_ego_b
    from tests.m56.response_cases import response_case
    from m56.model import ScriptState
    from m56.response import step_response
    c=response_case('F','B',events=('TRIGGER',),speed=0.)
    with pytest.raises(ValueError):step_response(c.frame,ScriptState('HOLD',F(0),()),f05_ego_b()[0])


@pytest.mark.parametrize('last,phase,target,final',[(120,'HOLD',F(9,5),'CREEP'),(150,'CREEP',F(9,5),'CREEP'),
    (151,'CREEP',F(0),'CREEP_STOP'),(171,'CREEP_STOP',F(0),'CREEP_STOP'),(186,'CREEP_STOP',F(36,5),'FORWARD')])
def test_f05_source_admitted_stock_creep_stops_before_hard_marker_then_actual_stop_clear_releases(tmp_path,last,phase,target,final):
    from tests.m56.creep_cases import creep_case
    c=creep_case(tmp_path/'sources',last=last)
    out=observed_step(c,phase)
    assert out.state.phase==final and out.command.kind=='CONTROL' and out.command.target_kmh==target
    assert out.command.offset==0 and out.command.light_state is None
    if target==0:assert out.command.control.throttle==0 and out.command.control.brake==.3
    else:assert out.command.control is None  # Still stock forward, no invented regulator.


@pytest.mark.parametrize('fault',['missing_fixture','missing_bound','unsafe_bound','wrong_body','wrong_response',
    'missing_path','path_hash_alias','fixture_hash_alias','history_hash_alias','future_history','missing_ground',
    'overspeed','reverse','steer','handbrake'])
def test_f05_stop_capability_or_current_packet_failures_do_not_get_stock_creep_torque(tmp_path,fault):
    from tests.m56.creep_cases import creep_case
    c=creep_case(tmp_path/'sources',fault if fault in ('missing_fixture','missing_bound','unsafe_bound','wrong_body','wrong_response','missing_path','path_hash_alias') else None,last=150)
    frame=c.frame;fields=dict(frame.integrity);ego,npc=frame.actors
    if fault=='fixture_hash_alias':fields['creep_fixture_ref']=replace(fields['creep_fixture_ref'],sha256='f'*64)
    elif fault=='history_hash_alias':fields['creep_history_ref']=replace(fields['creep_history_ref'],sha256='f'*64)
    elif fault=='future_history':frame=replace(frame,frame=149,simtime=F(49,20))
    elif fault=='missing_ground':ego=replace(ego,ground=None)
    elif fault=='overspeed':ego=replace(ego,velocity=(.75,0.,0.))
    elif fault in ('reverse','steer','handbrake'):
        ego=replace(ego,readback=replace(ego.readback,**{'reverse':{'reverse':True},'steer':{'steer':.1},'handbrake':{'hand_brake':True}}[fault]))
    c.frame=replace(frame,actors=(ego,npc),integrity=fields)
    with pytest.raises(ValueError):observed_step(c,'CREEP')


def test_f05_missing_bound_event_cannot_keep_creeping_at_certified_predictive_boundary(tmp_path):
    from tests.m56.creep_cases import creep_case
    from m56.metrics import detect_events
    c=creep_case(tmp_path/'sources',last=151)
    events=tuple(e for e in detect_events(c.frames,c.fixture) if e.name!='EGO_CREEP_STOPPING_BOUND')
    with pytest.raises(ValueError):observed_step(c,'CREEP',events)


def test_f05_named_stop_and_old_clear_do_not_release_current_rolling_body(tmp_path):
    from tests.m56.creep_cases import creep_case
    from m56.model import EventRecord
    from m56.metrics import detect_events
    c=creep_case(tmp_path/'sources','rolling_stop',last=186)
    events=detect_events(c.frames,c.fixture)
    refs=c.frame.integrity['frame_refs']
    events=(*events,EventRecord('EGO_CREEP_STOP_CONFIRMED',186,c.frame.simtime,refs),
            EventRecord('QUEUE_CLEAR_CONFIRMED',186,c.frame.simtime,refs))
    with pytest.raises(ValueError):observed_step(c,'CREEP_STOP',events)
