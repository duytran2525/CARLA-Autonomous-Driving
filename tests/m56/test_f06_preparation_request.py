"""A source-owned zero-torque gear request is not the observed preparation cue."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


def preparation_case(root,defect=None):
    from tests.m56.reverse_cases import reverse_case,ground_actor
    from m56.catalog import _digest
    from m56.model import ControlPacket,ScriptState
    c=reverse_case(root,role='NPC');s=c.s
    response=replace(c.response,phases={**c.response.phases,'preparation':{
        'method':'owned-reverse-preparation-v1','request_kind':'REVERSE_PREPARATION_REQUEST'}})
    if defect=='wrong_definition':response=replace(response,phases={**response.phases,'preparation':{
        'method':'timer-is-observed-cue','request_kind':'REVERSE_PREPARATION_REQUEST'}})
    response=replace(response,hash=_digest({k:getattr(response,k) for k in
        ('actor_role','action_id','route','targets','profile','phases')}))
    fixture=replace(c.fixture,responses=(response,),proofs=())
    limits={**c.stop_proof.limits,'response_hash':response.hash}
    ref=s.source('prepare-stop-bound',limits)
    fixture=replace(fixture,proofs=(s.capability('REVERSE_STOP_BOUND','bounded-reverse-stop-v1',limits,(ref,),F(0)),))
    frames=[];hold=ControlPacket(0.,0.,.3,False,False,False,1)
    for i,f in enumerate(c.frames):
        actors=[]
        for a in f.actors:
            a=replace(a,readback=hold)
            if defect=='rolling_peer' and a.role=='EGO':
                a=replace(a,pose=replace(a.pose,x=float(F(4)+F(i,64))),arc=F(4)+F(i,64))
            if defect=='moving_npc' and a.role=='NPC':a=replace(a,velocity=(.2,0.,0.))
            actors.append(ground_actor(s,fixture,a,f.frame,f.simtime,c.ground_recipe))
        f=replace(f,actors=tuple(actors),events=(),integrity={})
        ref=s.source('prepare-observed-'+str(f.frame),{'boot':f.boot,'world':f.world,'frame':f.frame,
            'simtime':f.simtime,'actors':f.actors},f.frame,f.simtime)
        frames.append(replace(f,integrity={'frame_refs':(ref,)}))
    if defect=='short_stop':frames=frames[-10:]
    frame=frames[-1];history=s.source('prepare-history',tuple(frames))
    limits={**c.frame.integrity['reverse_corridor'].limits,'response_hash':response.hash,'actors_hash':_digest(frame.actors)}
    ref=s.source('prepare-corridor',limits,frame.frame,frame.simtime)
    corridor=s.capability('REVERSE_CORRIDOR','bounded-reverse-corridor-v1',limits,(ref,),F(0))
    traffic={'boot':frame.boot,'world':frame.world,'frame':frame.frame,'actor_id':2,
        'status':'RED' if defect=='red' else 'UNKNOWN' if defect=='unknown_priority' else 'CLEAR'}
    ref=s.source('prepare-priority',traffic,frame.frame,frame.simtime)
    request={'fixture_hash':_digest(fixture),'response_hash':response.hash,'boot':frame.boot,'world':frame.world,
        'frame':frame.frame-1 if defect=='stale_request' else frame.frame,'actor_id':2,'actors_hash':_digest(frame.actors)}
    rr=s.source('prepare-request',request,request['frame'],frame.simtime-F(1,20) if defect=='stale_request' else frame.simtime)
    cap=s.capability('REVERSE_PREPARATION_REQUEST','owned-reverse-preparation-v1',request,(rr,),F(0))
    fields={**frame.integrity,'reverse_history_ref':history,'reverse_corridor':corridor,
        'npc_controls':{**traffic,'witness_refs':(ref,)}}
    if defect!='missing_request':fields['preparation_request']=cap
    frame=replace(frame,integrity=fields)
    state=ScriptState('NPC_PREPARATION',F(0),())
    return SimpleNamespace(s=s,frame=frame,fixture=fixture,response=response,state=state)


def test_f06_owned_preparation_requests_reverse_gear_only_after_both_actual_stops(tmp_path):
    from m56.response import reverse_intent
    c=preparation_case(tmp_path/'sources');out=reverse_intent(c.frame,c.state,c.response,c.fixture)
    command=out.command
    assert (command.kind,command.cause,command.actor,command.frame,command.next_frame,command.target_kmh)==(
        'GEAR_TRANSITION','NPC_PREPARATION',2,150,151,F(0)),out.state
    assert (command.control.throttle,command.control.brake,command.control.steer,command.control.reverse,
        command.control.manual_gear_shift,command.control.gear,command.light_state)==(0.,.3,0.,True,True,-1,None)
    assert out.state.phase=='NPC_PREPARATION_REQUESTED'
    assert not out.state.events and not c.frame.events  # request != observed TRIGGER/engagement
    repeat=reverse_intent(c.frame,out.state,c.response,c.fixture)
    assert repeat.command.kind=='BLOCKED'  # no duplicate unobserved operation


@pytest.mark.parametrize('observed_cue',[False,True])
def test_f06_before_observed_preparation_holds_forward_gear_without_starting_release(tmp_path,observed_cue):
    from m56.response import step_response
    from m56.model import EventRecord
    c=preparation_case(tmp_path/'sources','missing_request')
    state=c.state
    if observed_cue:
        state=replace(state,events=(EventRecord('TRIGGER',c.frame.frame,c.frame.simtime,c.frame.integrity['frame_refs']),))
        with pytest.raises(ValueError,match='OBSERVED_PREPARATION_GEAR_REQUIRED'):
            step_response(c.frame,state,c.response)
    else:
        out=step_response(c.frame,state,c.response)
        assert (out.command.kind,out.command.target_kmh,out.state.phase)==('CONTROL',F(0),'NPC_PREPARATION')
        control=out.command.control
        assert (control.throttle,control.brake,control.steer,control.reverse,control.manual_gear_shift,control.gear)==(0.,.3,0.,False,False,1)
        assert not out.state.events  # an initialization hold never arms the 3s clock


@pytest.mark.parametrize('defect',['missing_request','short_stop','rolling_peer','moving_npc','stale_request',
    'red','unknown_priority','wrong_definition'])
def test_f06_preparation_cannot_request_gear_from_timer_or_unsafe_unbound_context(tmp_path,defect):
    from m56.response import reverse_intent
    c=preparation_case(tmp_path/'sources',defect);out=reverse_intent(c.frame,c.state,c.response,c.fixture)
    assert out.command.kind=='BLOCKED' and out.state.phase=='BLOCKED_CONTROLLER',out.state
    assert out.command.control.throttle==0 and out.command.control.brake==.3
