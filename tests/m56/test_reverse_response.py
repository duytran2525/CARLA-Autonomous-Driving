"""Bounded exception software contracts only; never native qualification."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


@pytest.fixture
def f06_program():
    from tests.m56.response_cases import response_case
    from m56.catalog import _digest
    from m56.model import ControlPacket,EventRecord,ScriptState
    c=response_case('F','NPC_COMMON',events=(),speed=0.,role='NPC')
    rows=({'cause':'NPC_REVERSE_TARGET','after_event':'TRIGGER','delay_s':F(3),'requires':()},
          {'cause':'NPC_STOPPING','after_event':'NPC_REVERSE_STOPPING_BOUND','delay_s':F(0),'requires':()},
          {'cause':'NPC_FORWARD_GEAR','after_event':'NPC_REVERSE_STOP_CONFIRMED','delay_s':F(0),'requires':()},
          {'cause':'NPC_FORWARD','after_event':'NPC_FORWARD_GEAR_CONFIRMED','delay_s':F(0),'requires':()})
    script={'mechanism':'F06-ALT1','policy_hash':'d'*64,'release_mode':'FIXED_OBSERVED_CUE',
            'release_s':F(3),'reverse_distance_m':F(2),'target_mps':F(1,2)}
    r=replace(c.response,targets={'NPC_PREPARATION':F(0),'NPC_REVERSE_TARGET':F(1,2),'NPC_STOPPING':F(0),'NPC_FORWARD_GEAR':F(0),'NPC_FORWARD':F(2)},
        phases={'category':'F','f_script':script,'program':{'method':'ordered-event-program-v1','initial':'NPC_PREPARATION','transitions':rows}})
    r=replace(r,hash=_digest({'actor_role':r.actor_role,'action_id':r.action_id,'route':r.route,'targets':r.targets,'profile':r.profile,'phases':r.phases}))
    cue_ref=replace(c.ref,frame=100,time=F(0));cue=EventRecord('TRIGGER',100,F(0),(cue_ref,))
    state=ScriptState('NPC_PREPARATION',F(0),(cue,))
    def frame(time,ego_action):
        number=100+int(20*time);ref=replace(c.ref,frame=number,time=time)
        npc=replace(c.frame.actors[0],id=2,readback=ControlPacket(0.,0.,.3,False,True,True,-1))
        ego=replace(npc,role='EGO',id=1,pose=replace(npc.pose,x=0.),readback=ControlPacket(0.,0.,.3,False,False,False,1))
        return replace(c.frame,frame=number,simtime=time,actors=(ego,npc),events=(),integrity={
            'frame_refs':(ref,),'ego_action_for_test_only':ego_action,
            'npc_controls':{'boot':'boot','world':'world','frame':number,'actor_id':2,'status':'CLEAR','witness_refs':(ref,)}})
    return SimpleNamespace(response=r,state=state,frame=frame)


def test_f06_fixed_release_is_action_independent(require,f06_program):
    c=f06_program;step=require('m56.response','step_response')
    early=step(c.frame(F(59,20),'A'),c.state,c.response)
    assert early.state.phase=='NPC_PREPARATION'
    assert early.command.control.throttle==0 and early.command.control.reverse and early.command.control.gear==-1
    released=step(c.frame(F(3),'B'),c.state,c.response)
    assert released.state.phase=='NPC_REVERSE_TARGET'
    assert released.command.response_hash==early.command.response_hash==c.response.hash
    # A scheduler authorizes intent only; an uncalibrated stock PID must never
    # convert it to actual reverse torque or a negative forward target.
    assert released.command.kind=='REVERSE_REQUEST' and released.command.control is None
    assert released.command.target_kmh==F(9,5)


@pytest.mark.parametrize('fault',['requested_release','interactive','program_delay','wrong_anchor','hash_label','ego_dependent'])
def test_requested_release_change_rejected(require,f06_program,fault):
    from m56.catalog import _digest
    c=f06_program;r=c.response;script=dict(r.phases['f_script']);program=dict(r.phases['program']);rows=list(program['transitions'])
    if fault=='requested_release':script['release_s']=F(61,20)
    elif fault=='interactive':script['release_mode']='GAP_OR_FIXED'
    elif fault=='program_delay':rows[0]={**rows[0],'delay_s':F(59,20)}
    elif fault=='wrong_anchor':rows[0]={**rows[0],'after_event':'GAP_RESERVE_READY'}
    elif fault=='ego_dependent':script['ego_action']='B'
    program['transitions']=tuple(rows)
    r=replace(r,phases={**r.phases,'f_script':script,'program':program})
    if fault!='hash_label':
        r=replace(r,hash=_digest({'actor_role':r.actor_role,'action_id':r.action_id,'route':r.route,'targets':r.targets,'profile':r.profile,'phases':r.phases}))
    else:r=replace(r,hash='e'*64)
    out=require('m56.response','step_response')(c.frame(F(3),'B'),c.state,r)
    assert out.state.phase=='BLOCKED_POLICY'
    assert out.command.target_kmh==0 and out.command.control.throttle==0
    assert out.command.light_state is None


def test_interactive_release_not_active(require,f06_program):
    c=f06_program;frame=c.frame(F(59,20),'B')
    npc=replace(frame.actors[1],gaps={'allocated_reserve_m':F(1),'front_gap_m':F(4)})
    frame=replace(frame,actors=(frame.actors[0],npc))
    out=require('m56.response','step_response')(frame,c.state,c.response)
    assert out.state.phase=='NPC_PREPARATION' and out.command.control.throttle==0


def test_f06_npc_hash_same_for_a_b(require,f06_program):
    c=f06_program;step=require('m56.response','step_response')
    a=step(c.frame(F(3),'A'),c.state,c.response)
    b=step(c.frame(F(3),'B'),c.state,c.response)
    assert a.command==b.command and a.state==b.state


def test_missing_stop_bound_blocks_reverse(require,tmp_path):
    from tests.m56.reverse_cases import reverse_case
    reverse=require('m56.response','reverse_intent')
    c=reverse_case(tmp_path/'sources',stop_bound=False)
    out=reverse(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER'
    assert out.command.target_kmh==0 and out.command.control.throttle==0
    assert out.command.control.gear==1 and not out.command.control.reverse


@pytest.mark.parametrize('speed,progress,phase,observed_reverse,throttle,brake',[
    (0.,F(0),'HOLD',False,.25,0.),(.2,F(1,10),'REVERSE',True,.15,0.),
    (.5,F(1,10),'REVERSE',True,0.,0.),(.8,F(1,10),'REVERSE',True,0.,.15)])
def test_correlated_bounded_reverse_regulator_never_uses_negative_pid(require,tmp_path,speed,progress,phase,observed_reverse,throttle,brake):
    from tests.m56.reverse_cases import reverse_case
    reverse=require('m56.response','reverse_intent')
    c=reverse_case(tmp_path/'sources',progress=progress,speed=speed,phase=phase,reverse=observed_reverse)
    out=reverse(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='REVERSE'
    assert out.command.kind=='REVERSE' and out.command.target_kmh==F(9,5) and out.command.offset==0
    control=out.command.control
    assert control.reverse and control.manual_gear_shift and control.gear==-1 and control.steer==0
    assert control.throttle==pytest.approx(throttle,abs=1e-15) and control.brake==pytest.approx(brake,abs=1e-15)
    assert not control.hand_brake and out.command.light_state is None


@pytest.mark.parametrize('mechanism,hard',[('F03',F(2)),('F06-ALT1',F(1))])
def test_reverse_overshoot_not_credited(require,tmp_path,mechanism,hard):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources',mechanism=mechanism,progress=hard+F(1,100),speed=.5,reverse=True,phase='REVERSE')
    out=require('m56.response','reverse_intent')(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='FAILED' and out.command.control.throttle==0
    assert out.command.control.reverse and out.command.control.gear==-1


def test_stopping_transition_precedes_possible_next_tick_boundary_crossing(require,tmp_path):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources',progress=F(3,4),speed=.5,reverse=True,phase='REVERSE')
    out=require('m56.response','reverse_intent')(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='STOPPING'
    assert out.command.control.throttle==0 and out.command.control.brake==.30
    assert out.command.control.reverse and out.command.control.manual_gear_shift and out.command.control.gear==-1


def test_gear_change_before_stop_rejected(require,tmp_path):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources',speed=.2)
    out=require('m56.response','reverse_intent')(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.control.throttle==0
    assert out.command.control.gear==1 and not out.command.control.reverse


@pytest.mark.parametrize('rear',[F(0),F(19,100)])
def test_unsafe_rear_zone_blocks(require,tmp_path,rear):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources',rear_clearance=rear)
    out=require('m56.response','reverse_intent')(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.control.throttle==0


@pytest.mark.parametrize('samples',[1,10])
def test_terminal_brake_command_is_not_observed_half_second_stop(require,tmp_path,samples):
    from tests.m56.reverse_cases import reverse_case,terminal_observation
    c=reverse_case(tmp_path/'sources',progress=F(1),speed=.5,reverse=True,phase='STOPPING')
    frame=terminal_observation(c,samples=samples)
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase=='STOPPING' and out.command.control.reverse
    assert out.command.control.throttle==0 and out.command.control.brake==.30


def test_forward_gear_requires_actual_terminal_stop_before_switch(require,tmp_path):
    from tests.m56.joint_reverse_cases import joint_reverse_case
    c=joint_reverse_case(tmp_path/'sources');frame=c.frame
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase=='WAIT_FORWARD_GEAR'
    assert out.command.kind=='GEAR_TRANSITION' and out.command.target_kmh==0
    assert not out.command.control.reverse and not out.command.control.manual_gear_shift
    assert out.command.control.gear==1 and out.command.control.throttle==0 and out.command.control.brake==.30


@pytest.mark.parametrize('mechanism',['F03','F06-ALT1'])
def test_f03_f06_forward_completion_required(require,tmp_path,mechanism):
    from tests.m56.joint_reverse_cases import joint_reverse_case
    c=joint_reverse_case(tmp_path/'sources',mechanism,'forward');frame=c.frame
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase=='FORWARD' and out.state.phase!='COMPLETE'
    assert out.command.kind=='CONTROL' and out.command.target_kmh==F(36,5) and out.command.control is None


def test_reserved_space_is_not_reused_before_observed_npc_hazard_stop(require,tmp_path):
    from tests.m56.reverse_cases import reverse_case,terminal_observation
    c=reverse_case(tmp_path/'sources',progress=F(1),speed=.5,reverse=True,phase='STOPPING')
    frame=terminal_observation(c)
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase=='STOPPING' and out.command.control.reverse and out.command.control.throttle==0


def test_npc_stop_transition_is_role_scoped_and_keeps_reverse_hold(require,f06_program):
    from m56.catalog import _digest
    from m56.model import EventRecord
    c=f06_program;r=c.response
    rows=({'cause':'NPC_REVERSE_TARGET','after_event':'TRIGGER','delay_s':F(3),'requires':()},
          {'cause':'NPC_STOPPING','after_event':'NPC_REVERSE_STOPPING_BOUND','delay_s':F(0),'requires':()},
          {'cause':'NPC_FORWARD_GEAR','after_event':'NPC_REVERSE_STOP_CONFIRMED','delay_s':F(0),'requires':()},
          {'cause':'NPC_FORWARD','after_event':'NPC_FORWARD_GEAR_CONFIRMED','delay_s':F(0),'requires':()})
    r=replace(r,targets={**r.targets,'NPC_FORWARD_GEAR':F(0)},phases={**r.phases,
        'program':{'method':'ordered-event-program-v1','initial':'NPC_PREPARATION','transitions':rows}})
    r=replace(r,hash=_digest({'actor_role':r.actor_role,'action_id':r.action_id,'route':r.route,'targets':r.targets,'profile':r.profile,'phases':r.phases}))
    frame=c.frame(F(3),'B');ref=frame.integrity['frame_refs'][0]
    state=replace(c.state,phase='NPC_REVERSE_TARGET')
    wrong=replace(frame,events=(EventRecord('EGO_REVERSE_STOPPING_BOUND',frame.frame,frame.simtime,(ref,)),))
    out=require('m56.response','step_response')(wrong,state,r)
    assert out.state.phase=='NPC_REVERSE_TARGET' and out.command.kind=='REVERSE_REQUEST'
    correct=replace(frame,events=(EventRecord('NPC_REVERSE_STOPPING_BOUND',frame.frame,frame.simtime,(ref,)),))
    out=require('m56.response','step_response')(correct,state,r)
    assert out.state.phase=='NPC_STOPPING' and out.command.control.reverse and out.command.control.brake==.30


@pytest.mark.parametrize('fault',['actor_alias','past_yaw','missing_observation','packet_disagrees'])
def test_reverse_stop_history_cannot_borrow_foreign_or_uncorrelated_packets(require,tmp_path,fault):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources');frames=list(c.frames);old=frames[0]
    if fault=='actor_alias':old=replace(old,actors=(replace(old.actors[0],id=99),old.actors[1]))
    elif fault=='past_yaw':old=replace(old,actors=(replace(old.actors[0],pose=replace(old.actors[0].pose,yaw=1.)),old.actors[1]))
    elif fault=='missing_observation':old=replace(old,integrity={})
    else:old=replace(old,actors=(replace(old.actors[0],pose=replace(old.actors[0].pose,x=4.0001)),old.actors[1]))
    if fault in ('actor_alias','past_yaw'):
        ref=c.s.source('changed-observation',{'boot':old.boot,'world':old.world,'frame':old.frame,'simtime':old.simtime,'actors':old.actors},old.frame,old.simtime)
        old=replace(old,integrity={'frame_refs':(ref,)})
    frames[0]=old;history=c.s.source('changed-history',tuple(frames))
    frame=replace(c.frame,integrity={**c.frame.integrity,'reverse_history_ref':history})
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.control.throttle==0


@pytest.mark.parametrize('fault',['raw_byte','body','policy','gain','stop_room','review','duplicate'])
def test_reverse_calibration_is_not_a_boolean_or_hash_alias(require,tmp_path,fault):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources');fixture=c.fixture;frame=c.frame;proof=c.stop_proof
    if fault=='raw_byte':
        from pathlib import Path
        path=Path(proof.raw_refs[0].uri);path.write_bytes(path.read_bytes()+b' ')
    elif fault=='body':frame=replace(frame,actors=(replace(frame.actors[0],body=replace(frame.actors[0].body,extents=(.6,.25,.25))),frame.actors[1]))
    elif fault=='policy':fixture=replace(fixture,policy_hash='e'*64)
    elif fault in ('gain','stop_room'):
        limits={**proof.limits,('gain' if fault=='gain' else 'stopping_distance_bound_m'):(F(3,5) if fault=='gain' else F(1,2))}
        ref=c.s.source('changed-calibration',limits)
        proof=c.s.capability(proof.kind,proof.method,limits,(ref,),proof.uncertainty)
        fixture=replace(fixture,proofs=(proof,))
    elif fault=='review':fixture=replace(fixture,proofs=(replace(proof,review=replace(proof.review,verdict='REJECTED')),))
    else:fixture=replace(fixture,proofs=(proof,proof))
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.control.throttle==0


@pytest.mark.parametrize('fault',['dt','future_state','unbound_trigger','missing_readback','unsafe_steer'])
def test_reverse_never_assumes_clock_cue_or_last_applied_control(require,tmp_path,fault):
    from tests.m56.reverse_cases import reverse_case
    from m56.catalog import _digest
    c=reverse_case(tmp_path/'sources');frame=c.frame;state=c.state
    if fault=='dt':frame=replace(frame,dt=F(1,10))
    elif fault=='future_state':state=replace(state,start=frame.simtime+F(1,20))
    elif fault=='unbound_trigger':state=replace(state,events=(replace(state.events[0],witness_refs=()),))
    else:
        actor=replace(frame.actors[0],readback=None if fault=='missing_readback' else replace(frame.actors[0].readback,steer=.1))
        frame=replace(frame,actors=(actor,frame.actors[1]))
        ref=c.s.source('current-observation',{'boot':frame.boot,'world':frame.world,'frame':frame.frame,'simtime':frame.simtime,'actors':frame.actors},frame.frame,frame.simtime)
        raw=replace(frame,integrity={'frame_refs':(ref,)})
        history=c.s.source('current-history',(*c.frames[:-1],raw))
        old=c.frame.integrity['reverse_corridor'];limits={**old.limits,'actors_hash':_digest(frame.actors)}
        packet=c.s.source('current-corridor',limits,frame.frame,frame.simtime)
        corridor=c.s.capability(old.kind,old.method,limits,(packet,),old.uncertainty)
        frame=replace(frame,integrity={**frame.integrity,'frame_refs':(ref,),'reverse_history_ref':history,'reverse_corridor':corridor})
    out=require('m56.response','reverse_intent')(frame,state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and (out.command.control is None or out.command.control.throttle==0)


@pytest.mark.parametrize('delay,phase,throttle',[(F(59,20),'NPC_PREPARATION',0.),(F(3),'NPC_REVERSE_TARGET',.25)])
def test_npc_reverse_request_needs_its_own_bound_and_fixed_release(require,tmp_path,delay,phase,throttle):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources',role='NPC',phase='NPC_PREPARATION',waiting_s=delay,reverse=True)
    out=require('m56.response','reverse_intent')(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase==phase
    assert out.command.control.throttle==throttle
    assert out.command.control.reverse and out.command.control.manual_gear_shift and out.command.control.gear==-1
    assert out.command.offset==0 and out.command.light_state is None


@pytest.mark.parametrize('observed_forward,phase,kind',[(False,'NPC_FORWARD_GEAR','GEAR_TRANSITION'),(True,'NPC_FORWARD','CONTROL')])
def test_npc_own_two_metre_terminal_stop_then_observed_forward_gear(require,tmp_path,observed_forward,phase,kind):
    from tests.m56.reverse_cases import reverse_case,terminal_observation
    c=reverse_case(tmp_path/'sources',role='NPC',phase='NPC_FORWARD_GEAR' if observed_forward else 'NPC_STOPPING',
                   waiting_s=F(3),progress=F(2),speed=.5,reverse=True)
    frame=terminal_observation(c,forward=observed_forward)
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase==phase and out.command.kind==kind
    if kind=='GEAR_TRANSITION':assert out.command.control.throttle==0 and out.command.control.brake==.3 and not out.command.control.reverse
    else:assert out.command.target_kmh==F(36,5) and out.command.control is None


def test_reverse_ground_contact_is_not_inferred_from_pose_or_route_valid(require,tmp_path):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources',ground=False)
    assert c.frame.actors[0].ground is None and c.frame.actors[0].route_valid
    out=require('m56.response','reverse_intent')(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.control.throttle==0


@pytest.mark.parametrize('status',['UNKNOWN','RED'])
def test_npc_fixed_release_is_not_permission_to_violate_priority(require,tmp_path,status):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources',role='NPC',phase='NPC_PREPARATION',waiting_s=F(3),reverse=True)
    traffic={**c.frame.integrity['npc_controls'],'status':status}
    frame=replace(c.frame,integrity={**c.frame.integrity,'npc_controls':traffic})
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.control.throttle==0


def test_npc_early_actual_motion_invalidates_fixed_preparation(require,tmp_path):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources',role='NPC',phase='NPC_PREPARATION',progress=F(1,10),speed=.5,reverse=True)
    out=require('m56.response','reverse_intent')(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='FAILED' and out.command.control.throttle==0


@pytest.mark.parametrize('role,phase,distance',[('EGO','FORWARD',F(1)),('NPC','NPC_FORWARD',F(2))])
def test_forward_phase_is_not_reset_back_to_reverse_gear_request(require,tmp_path,role,phase,distance):
    from tests.m56.reverse_cases import reverse_case,terminal_observation
    if role=='EGO':
        from tests.m56.joint_reverse_cases import joint_reverse_case
        c=joint_reverse_case(tmp_path/'sources',mode='forward');frame=c.frame
    else:
        c=reverse_case(tmp_path/'sources',role=role,phase=phase,waiting_s=F(3),progress=distance,speed=.5,reverse=True)
        frame=terminal_observation(c,forward=True,released=True)
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase==phase and out.command.kind=='CONTROL' and out.command.control is None
    assert out.command.target_kmh==F(36,5)


@pytest.mark.parametrize('role,phase,retreat',[('EGO','FORWARD',F(1)),('NPC','NPC_FORWARD',F(2))])
def test_forward_continues_above_reverse_speed_without_reverse_corridor_authority(require,tmp_path,role,phase,retreat):
    from tests.m56.reverse_cases import reverse_case,terminal_observation,forward_observations
    if role=='EGO':
        from tests.m56.joint_reverse_cases import joint_reverse_case
        c=joint_reverse_case(tmp_path/'sources',mode='forward')
        frame=replace(c.frame,integrity={k:v for k,v in c.frame.integrity.items() if k!='reverse_corridor'})
    else:
        c=reverse_case(tmp_path/'sources',role=role,phase=phase,waiting_s=F(3),progress=retreat,speed=.5,reverse=True)
        terminal=terminal_observation(c,forward=True,released=True)
        frame=forward_observations(c,terminal)
    assert 'reverse_corridor' not in frame.integrity
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase==phase and out.command.kind=='CONTROL' and out.command.control is None
    assert out.command.target_kmh==F(36,5) and out.command.offset==0


@pytest.mark.parametrize('role,phase',[('EGO','FORWARD'),('NPC','NPC_FORWARD')])
def test_forward_label_does_not_replace_actual_reverse_and_terminal_gear_history(require,tmp_path,role,phase):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources',role=role,phase=phase,waiting_s=F(3),reverse=False)
    out=require('m56.response','reverse_intent')(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.kind=='BLOCKED'
    assert out.command.control.throttle==0


def test_forward_motion_with_unconfirmed_terminal_stop_is_not_delegated(require,tmp_path):
    from tests.m56.reverse_cases import reverse_case,terminal_observation,forward_observations
    c=reverse_case(tmp_path/'sources',phase='FORWARD',waiting_s=F(3),progress=F(1),speed=.5,reverse=True)
    terminal=terminal_observation(c,samples=1,forward=True,released=True)
    frame=forward_observations(c,terminal)
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.kind=='BLOCKED' and out.command.control.throttle==0


@pytest.mark.parametrize('role,mode',[('EGO','release'),('NPC','release'),('EGO','forward'),('NPC','forward')])
def test_source_decoded_reverse_inputs_preserve_admitted_controller_behavior(require,tmp_path,role,mode):
    from tests.m56.reverse_cases import reverse_case,terminal_observation,forward_observations
    from m56.model import encode_record,decode_record
    phase=('NPC_PREPARATION' if role=='NPC' else 'HOLD') if mode=='release' else ('NPC_FORWARD' if role=='NPC' else 'FORWARD')
    if role=='EGO' and mode=='forward':
        from tests.m56.joint_reverse_cases import joint_reverse_case
        c=joint_reverse_case(tmp_path/'sources',mode='forward');frame=c.frame
    else:
        c=reverse_case(tmp_path/'sources',role=role,phase=phase,waiting_s=F(3),
            progress=(F(2 if role=='NPC' else 1) if mode=='forward' else F(0)),speed=.5 if mode=='forward' else 0.,reverse=True)
        frame=c.frame if mode=='release' else forward_observations(c,terminal_observation(c,forward=True,released=True))
    recorded=decode_record('FrameRecord',encode_record(frame))
    fixture=decode_record('CompiledFixture',encode_record(c.fixture))
    response=fixture.responses[0]
    out=require('m56.response','reverse_intent')(recorded,c.state,response,fixture)
    if mode=='release':
        assert out.state.phase==('NPC_REVERSE_TARGET' if role=='NPC' else 'REVERSE'),out
        assert out.command.kind=='REVERSE' and out.command.target_kmh==F(9,5)
        assert out.command.control.throttle==.25 and out.command.control.gear==-1
    else:
        assert out.state.phase==phase and out.command.kind=='CONTROL',out
        assert out.command.target_kmh==F(36,5) and out.command.control is None


@pytest.mark.parametrize('receipt',['ground','history','corridor','traffic'])
@pytest.mark.parametrize('defect',['checksum','unknown_field'])
def test_source_decoding_cannot_strip_reverse_receipt_defects(require,tmp_path,receipt,defect):
    from tests.m56.reverse_cases import reverse_case
    from m56.model import encode_record,decode_record
    c=reverse_case(tmp_path/'sources',role='NPC',phase='NPC_PREPARATION',waiting_s=F(3),reverse=True)
    raw=encode_record(c.frame)
    if receipt=='ground':target=raw['actors'][1]['ground']['limits']['recipe_ref']
    elif receipt=='history':target=raw['integrity']['reverse_history_ref']
    elif receipt=='corridor':target=raw['integrity']['reverse_corridor']['raw_refs'][0]
    else:target=raw['integrity']['npc_controls']['witness_refs'][0]
    if defect=='checksum':target['sha256']='0'*64
    else:target['unapproved_override']=True
    recorded=decode_record('FrameRecord',raw)
    fixture=decode_record('CompiledFixture',encode_record(c.fixture))
    out=require('m56.response','reverse_intent')(recorded,c.state,fixture.responses[0],fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.kind=='BLOCKED',out
    assert out.command.control.throttle==0


@pytest.mark.parametrize('defect',['checksum','packet','future'])
def test_npc_forward_priority_must_remain_source_authenticated(require,tmp_path,defect):
    from tests.m56.reverse_cases import reverse_case,terminal_observation,forward_observations
    c=reverse_case(tmp_path/'sources',role='NPC',phase='NPC_FORWARD',waiting_s=F(3),progress=F(2),speed=.5,reverse=True)
    frame=forward_observations(c,terminal_observation(c,forward=True))
    traffic=dict(frame.integrity['npc_controls']);ref=traffic['witness_refs'][0]
    if defect=='checksum':ref=replace(ref,sha256='0'*64)
    elif defect=='future':ref=replace(ref,time=ref.time+F(1,20))
    else:
        raw={k:v for k,v in traffic.items() if k!='witness_refs'}
        ref=c.s.source('forged-priority',{**raw,'status':'RED'},frame.frame,frame.simtime)
    traffic['witness_refs']=(ref,)
    frame=replace(frame,integrity={**frame.integrity,'npc_controls':traffic})
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.kind=='BLOCKED'
    assert out.command.control.throttle==0


def test_npc_source_authenticated_red_holds_after_forward_gear(require,tmp_path):
    from tests.m56.reverse_cases import reverse_case,terminal_observation,forward_observations
    c=reverse_case(tmp_path/'sources',role='NPC',phase='NPC_FORWARD',waiting_s=F(3),progress=F(2),speed=.5,reverse=True)
    frame=forward_observations(c,terminal_observation(c,forward=True))
    traffic={k:v for k,v in frame.integrity['npc_controls'].items() if k!='witness_refs'}
    traffic['status']='RED';ref=c.s.source('observed-red',traffic,frame.frame,frame.simtime)
    frame=replace(frame,integrity={**frame.integrity,'npc_controls':{**traffic,'witness_refs':(ref,)}})
    out=require('m56.response','reverse_intent')(frame,c.state,c.response,c.fixture)
    assert out.state.phase=='NPC_FORWARD' and out.command.kind=='CONTROL'
    assert out.command.cause=='NPC_TRAFFIC_HOLD' and out.command.target_kmh==0
    assert out.command.control.throttle==0 and out.command.control.brake==.3


def test_reverse_trigger_cannot_use_checksum_alias_at_matching_timestamp(require,tmp_path):
    from tests.m56.reverse_cases import reverse_case
    c=reverse_case(tmp_path/'sources')
    event=c.state.events[0];ref=replace(event.witness_refs[0],sha256='0'*64)
    state=replace(c.state,events=(replace(event,witness_refs=(ref,)),))
    out=require('m56.response','reverse_intent')(c.frame,state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.control.throttle==0
