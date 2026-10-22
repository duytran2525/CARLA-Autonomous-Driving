"""Synthetic pure-response tests: no stock driver/native authority."""
from dataclasses import replace
from types import SimpleNamespace
from fractions import Fraction as F

import pytest


@pytest.mark.parametrize('case,want',[('current','CHANGE'),('future','NOMINAL'),('stale','NOMINAL')])
def test_replay_uses_issuing_frame_path_not_last_event_in_whole_trace(require,case,want):
    from tests.m56.response_cases import response_case
    from m56.model import EventRecord
    c=response_case('I','B',events=('SOURCE_CLEAR_CONFIRMED',),speed=4.)
    program={'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':(
        {'cause':'CHANGE','after_event':'SOURCE_CLEAR_CONFIRMED','delay_s':F(0),'requires':('LANE_CHANGE_PATH_CLEAR',)},)}
    response=replace(c.response,phases={**c.response.phases,'program':program})
    def event(frame):
        time=F(frame-80,20);ref=replace(c.ref,frame=frame,time=time)
        return EventRecord('LANE_CHANGE_PATH_CLEAR',frame,time,(ref,))
    paths=(event(100),event(101),event(102)) if case=='current' else (event(101),) if case=='future' else (event(99),)
    advance=require('m56.response','_advance_program')
    state=advance(c.frame,c.state,response,(*c.frame.events,*paths))
    assert state.phase==want


def test_a_does_not_resume_on_clear_without_stop(require):
    from tests.m56.response_cases import response_case
    c=response_case(events=('TRIGGER','CLEAR_N_CONFIRMED'))
    step=require('m56.response','step_response')
    first=step(c.frame,c.state,c.response)
    later=replace(c.frame,frame=101,simtime=F(21,20),events=())
    out=step(later,first.state,c.response)
    assert out.command.target_kmh==0
    assert out.state.phase=='WAIT_STOP_AND_CLEAR'
    assert out.command.frame==101 and out.command.next_frame==102


@pytest.mark.parametrize('category,want',[('C',F(36,5)),('L',F(18,5)),('M',F(36,5))])
def test_clm_u_units(require,category,want):
    from tests.m56.response_cases import response_case
    c=response_case(category,'B',speed=2.)
    out=require('m56.response','step_response')(c.frame,c.state,c.response)
    assert out.command.target_kmh==want
    assert out.state.phase=='YIELD'
    assert out.command.control is None  # stock follower supplies control, not a synthetic PID


def test_b_floor_violation_never_falls_back_a(require):
    from tests.m56.response_cases import response_case
    c=response_case('C','B',speed=.25)
    with pytest.raises(ValueError,match='CONTINUOUS_YIELD_SPEED_FLOOR'):
        require('m56.response','step_response')(c.frame,c.state,c.response)


def test_resume_requires_both_observed_stop_and_clear(require):
    from tests.m56.response_cases import response_case
    from m56.model import ScriptState
    c=response_case(events=('TRIGGER','STOP_AFTER_TRIGGER','CLEAR_N_CONFIRMED'))
    state=ScriptState('WAIT_STOP_AND_CLEAR',F(0),c.frame.events)
    out=require('m56.response','step_response')(c.frame,state,c.response)
    assert out.state.phase=='RESUME' and out.command.target_kmh==F(72,5)


def test_future_or_unbound_event_cannot_drive_transition(require):
    from tests.m56.response_cases import response_case
    c=response_case();event=replace(c.frame.events[0],frame=101)
    with pytest.raises(ValueError,match='EVENT'):
        require('m56.response','step_response')(replace(c.frame,events=(event,)),c.state,c.response)


@pytest.mark.parametrize('status',['RED','UNKNOWN','STOP','YIELD'])
def test_npc_red_or_unknown_does_not_move(require,status):
    from tests.m56.response_cases import response_case
    c=response_case(role='NPC',events=())
    traffic={'boot':'boot','world':'world','frame':100,'actor_id':1,'status':status,'witness_refs':(c.ref,)}
    frame=replace(c.frame,integrity={'npc_controls':traffic})
    out=require('m56.response','step_response')(frame,c.state,c.response)
    assert out.command.target_kmh==0
    assert out.command.control.throttle==0 and out.command.control.brake==.3
    assert out.command.cause=='NPC_TRAFFIC_HOLD'


def test_npc_missing_mapping_is_not_green(require):
    from tests.m56.response_cases import response_case
    c=response_case(role='NPC',events=())
    with pytest.raises(ValueError,match='NPC_CONTROL_WITNESS_MISSING'):
        require('m56.response','step_response')(c.frame,c.state,c.response)


@pytest.mark.parametrize('category,action,event,guards',[('I','B','SOURCE_CLEAR_CONFIRMED',('LANE_CHANGE_PATH_CLEAR',)),
    ('O','A','RETURN_MARKER',('RETURN_CLEAR_CONFIRMED','RETURN_PATH_CLEAR'))])
def test_lateral_start_requires_observed_path_and_clearance(require,category,action,event,guards):
    from tests.m56.response_cases import response_case
    c=response_case(category,action,events=(event,),speed=4.)
    program={'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':(
        {'cause':'CHANGE','after_event':event,'delay_s':F(0),'requires':guards},)}
    response=replace(c.response,phases={**c.response.phases,'program':program})
    out=require('m56.response','step_response')(c.frame,c.state,response)
    assert out.state.phase=='NOMINAL'
    assert out.command.offset==0


def test_i_source_clear_before_change(require):
    from tests.m56.response_cases import response_case
    c=response_case('I','B',events=('TRIGGER',),speed=4.)
    profile={'method':'quintic-arc-v1','segments':(segment(F(0),F(12),F(0),F(3)),)}
    response=replace(c.response,profile=profile)
    with pytest.raises(ValueError,match='LANE_CHANGE_GUARD_MISSING'):
        require('m56.response','step_response')(c.frame,c.state,response)


def test_o_return_without_ahead_witness_rejected(require):
    from tests.m56.response_cases import response_case
    c=response_case('O','A',events=('TRIGGER','LANE_CHANGE_PATH_CLEAR','RETURN_MARKER'),speed=4.)
    profile={'method':'quintic-arc-v1','segments':(segment(F(0),F(1),F(0),F(3)),segment(F(2),F(6),F(3),F(0)))}
    with pytest.raises(ValueError,match='RETURN_GUARD_MISSING'):
        require('m56.response','step_response')(c.frame,c.state,replace(c.response,profile=profile))


def test_i_late_change_never_moves_frozen_start_or_extends_wait(require):
    from tests.m56.response_cases import response_case
    c=response_case('I','B',events=('TRIGGER','SOURCE_CLEAR_CONFIRMED','LANE_CHANGE_PATH_CLEAR'),speed=4.)
    profile={'method':'quintic-arc-v1','segments':(segment(F(0),F(12),F(0),F(3)),)}
    frame=replace(c.frame,frame=201,simtime=F(121,20),events=())
    state=replace(c.state,events=c.frame.events)
    with pytest.raises(ValueError,match='SOURCE_CLEAR_WAIT_EXCEEDED'):
        require('m56.response','step_response')(frame,state,replace(c.response,profile=profile))


def test_lane_change_path_clearance_cannot_be_reused_from_previous_frame(require):
    from tests.m56.response_cases import response_case
    c=response_case('I','B',events=('TRIGGER','SOURCE_CLEAR_CONFIRMED','LANE_CHANGE_PATH_CLEAR'),speed=4.)
    profile={'method':'quintic-arc-v1','segments':(segment(F(1),F(12),F(0),F(3)),)}
    frame=replace(c.frame,frame=101,simtime=F(21,20),events=())
    with pytest.raises(ValueError,match='LANE_CHANGE_PATH_STALE'):
        require('m56.response','step_response')(frame,replace(c.state,events=c.frame.events),replace(c.response,profile=profile))


def test_quintic_fixed_marker_no_random_route(require):
    from tests.m56.response_cases import response_case
    c=response_case('I','B',events=('TRIGGER','SOURCE_CLEAR_CONFIRMED','LANE_CHANGE_PATH_CLEAR'),speed=4.)
    profile={'method':'quintic-arc-v1','segments':(segment(F(1),F(12),F(0),F(3)),)}
    response=replace(c.response,profile=profile)
    out=require('m56.response','step_response')(c.frame,c.state,response)
    assert out.command.offset==F(159,512)  # (4-1)/12 = 1/4, 3*q(1/4)
    assert response.route==c.response.route


@pytest.fixture
def switched_response():
    from tests.m56.response_cases import response_case
    c=response_case('I','B',events=('TRIGGER','SOURCE_CLEAR_CONFIRMED','LANE_CHANGE_PATH_CLEAR','TARGET_LANE_CONFIRMED'),speed=4.)
    target=replace(c.response.route,transforms=tuple(replace(t,y=3.) for t in c.response.route.transforms))
    program={'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':(
        {'cause':'CHANGE','after_event':'TARGET_LANE_CONFIRMED','delay_s':F(0),'requires':('SOURCE_CLEAR_CONFIRMED','LANE_CHANGE_PATH_CLEAR')},)}
    profile={'method':'quintic-arc-v1','segments':(segment(F(0),F(3),F(0),F(3)),)}
    reset={'method':'quintic-arc-v1','segments':(segment(F(3),F(1),F(0),F(0)),)}
    switch={'cause':'CHANGE','event':'TARGET_LANE_CONFIRMED','marker_arc_m':F(3),'route':target,'profile':reset}
    response=replace(c.response,profile=profile,phases={**c.response.phases,'program':program,'reference_switches':(switch,)})
    frame=replace(c.frame,actors=(replace(c.frame.actors[0],pose=replace(c.frame.actors[0].pose,y=3.)),))
    return SimpleNamespace(c=c,frame=frame,response=response,target=target)


def test_fixed_target_plan_switch_resets_offset_not_metric_reference(require,switched_response):
    s=switched_response;step=require('m56.response','step_response')
    out=step(s.frame,s.c.state,s.response)
    assert out.command.offset==0
    assert out.state.phase=='CHANGE'
    assert out.command.response_hash==s.response.hash
    assert s.response.route==s.c.response.route  # immutable initial reference, not overwritten


def test_discontinuous_target_plan_switch_blocks_instead_of_snapping(require,switched_response):
    s=switched_response;switch=dict(s.response.phases['reference_switches'][0])
    switch['route']=replace(s.target,transforms=tuple(replace(t,y=4.) for t in s.target.transforms))
    response=replace(s.response,phases={**s.response.phases,'reference_switches':(switch,)})
    with pytest.raises(ValueError,match='REFERENCE_SWITCH'):
        require('m56.response','step_response')(s.frame,s.c.state,response)


def test_target_plan_switch_cannot_precede_frozen_marker(require,switched_response):
    s=switched_response;frame=replace(s.frame,actors=(replace(s.frame.actors[0],pose=replace(s.frame.actors[0].pose,x=2.)),))
    with pytest.raises(ValueError,match='REFERENCE_SWITCH_BEFORE_MARKER'):
        require('m56.response','step_response')(frame,s.c.state,s.response)


def segment(start=F(10), length=F(6), initial=F(0), final=F(3, 4)):
    return dict(start_arc_m=start, length_m=length,
                start_offset_m=initial, end_offset_m=final)


def response_with(profile):
    from m56.model import FrozenResponse
    return FrozenResponse('EGO', 'B', None, {}, profile, {}, 'a'*64)


def test_quintic_fixed_marker_clamps_and_uses_arc_not_linear_fraction(require):
    # Wrong marker/linear interpolation/extrapolation breaks literal quarter samples.
    offset = require('m56.response', 'desired_offset')
    response = response_with({'method': 'quintic-arc-v1', 'segments': (segment(),)})
    for arc, want in ((F(-3), F(0)), (F(10), F(0)),
                      (F(23, 2), F(159, 2048)), (F(13), F(3, 8)),
                      (F(29, 2), F(1377, 2048)), (F(16), F(3, 4)),
                      (F(100), F(3, 4))):
        actual = offset(arc, response)
        assert isinstance(actual, F)
        assert actual == want


def test_quintic_preserves_signed_separation_plateau_and_frozen_return(require):
    # Losing direction, restarting at a later arc, or resetting in the plateau fails.
    offset = require('m56.response', 'desired_offset')
    response = response_with({'method': 'quintic-arc-v1', 'segments': (
        segment(F(-2), F(18), F(0), F(-7, 2)),
        segment(F(20), F(6), F(-7, 2), F(0)),
    )})
    for arc, want in ((F(-2), F(0)), (F(5, 2), F(-371, 1024)),
                      (F(7), F(-7, 4)), (F(18), F(-7, 2)),
                      (F(20), F(-7, 2)), (F(23), F(-7, 4)),
                      (F(26), F(0)), (F(30), F(0))):
        assert offset(arc, response) == want
    # Out-of-order calls must not move the frozen marker or mutate the response.
    assert offset(F(5, 2), response) == F(-371, 1024)


@pytest.mark.parametrize('arc', [True, 10, 10.0, '10', None, float('nan'), float('inf')])
def test_quintic_rejects_non_number_arc_instead_of_coercing(require, arc):
    offset = require('m56.response', 'desired_offset')
    response = response_with({'method': 'quintic-arc-v1', 'segments': (segment(),)})
    with pytest.raises(ValueError):
        offset(arc, response)


@pytest.mark.parametrize('profile', [
    {},
    {'method': 'linear', 'segments': (segment(),)},
    {'method': 'quintic-arc-v1', 'segments': ()},
    {'method': 'quintic-arc-v1', 'segments': 'not-segments'},
    {'method': 'quintic-arc-v1', 'segments': (None,)},
    {'method': 'quintic-arc-v1', 'segments': (segment(),), 'adaptive': True},
    {'method': 'quintic-arc-v1', 'segments': (segment(length=F(0)),)},
    {'method': 'quintic-arc-v1', 'segments': (segment(length=F(-6)),)},
    {'method': 'quintic-arc-v1', 'segments': (segment(final=.75),)},
    {'method': 'quintic-arc-v1', 'segments': (segment(initial=True),)},
    {'method': 'quintic-arc-v1', 'segments': (segment(start='10'),)},
    {'method': 'quintic-arc-v1', 'segments': (segment(length=6),)},
    {'method': 'quintic-arc-v1', 'segments': ({'start_arc_m': F(10)},)},
    {'method': 'quintic-arc-v1', 'segments': ({**segment(), 'tolerance': F(1)},)},
    {'method': 'quintic-arc-v1', 'segments': (
        segment(), segment(F(15), F(6), F(3, 4), F(0)))},
    {'method': 'quintic-arc-v1', 'segments': (
        segment(), segment(F(20), F(6), F(1), F(0)))},
    {'method': 'quintic-arc-v1', 'segments': (
        segment(), segment(F(0), F(6), F(3, 4), F(0)))},
])
def test_quintic_validates_entire_profile_before_any_offset(require, profile):
    # Even a query before segment 1 cannot hide malformed/overlapping later input.
    offset = require('m56.response', 'desired_offset')
    with pytest.raises(ValueError):
        offset(F(-100), response_with(profile))
