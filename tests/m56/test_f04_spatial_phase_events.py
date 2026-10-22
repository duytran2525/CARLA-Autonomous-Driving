"""Synthetic within-lane F04 pass/return source contracts, not native door/path calibration."""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

import pytest


def f04_spatial_observations(root,defect=None,npc_schedule=False):
    from tests.m56.source_cases import Sources
    from tests.m56.o_cases import o_fixture
    from tests.m56.test_f04_spatial_normative_response import f04_ego_b
    from m56.catalog import _digest
    from m56.model import ActorFrame,FrameRecord,CommandRecord,ControlPacket,FrozenMetricPair,Section,FrozenResponse
    from m56.metrics import _metric_station
    from m56.response import desired_offset
    s=Sources(root);c=o_fixture(s);ego,_=f04_ego_b();route=c.fixture.routes['EGO']
    body=replace(c.body,extents=(1.75,.5,.25))  # Explicit narrow synthetic body; not actual blueprint dimensions.
    segments=({'start_arc_m':F(3),'length_m':F(6),'start_offset_m':F(0),'end_offset_m':F(3,4)},
              {'start_arc_m':F(15),'length_m':F(6),'start_offset_m':F(3,4),'end_offset_m':F(0)})
    ego=replace(ego,route=route,profile={'method':'quintic-arc-v1','segments':segments})
    ego=replace(ego,hash=_digest({k:getattr(ego,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    npc=FrozenResponse('NPC','NPC_COMMON',route,{'PARKED':F(0)},
        {'method':'quintic-arc-v1','segments':({'start_arc_m':F(0),'length_m':F(1),'start_offset_m':F(0),'end_offset_m':F(0)},)},
        {'category':'F','program':{'method':'ordered-event-program-v1','initial':'PARKED','transitions':()}},'c'*64)
    if npc_schedule:
        from tests.m56.test_f04_npc_normative_response import f04_npc_response
        npc=replace(f04_npc_response()[0],route=route)
    npc=replace(npc,hash=_digest({k:getattr(npc,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    initial=tuple(product((-10.,190.),(-1.75,1.75),(-1.,1.)))
    end=Section(tuple(product((2.25,),(-1.75,1.75),(-1.,1.))),(1.,0.,0.),F(49,4),{})
    fixture=replace(c.fixture,responses=(ego,npc),G=None,sections={'F04_END':end},
        environment={'readiness':{'targets_mps':{'EGO':F(2),'NPC':F(0)}}},
        pair=FrozenMetricPair(('passage_time_s','e_lat_peak_m'),('s','m'),('elapsed','map_lateral_peak'),
            (('TRIGGER','F04_END'),)*2,'map:'+_digest(c.reference),'e'*64,'APPROVED_PROPOSAL_NOT_READY'),
        domain=replace(c.fixture.domain,topology={'category':'F','mechanism':'F04',
            'door_corridor':tuple(product((-2.,2.),(-1.,1.),(-1.,1.))),
            'action_regions':{'EGO_INITIAL':initial},'driving_regions':{'EGO':(initial,),'NPC':(initial,)}}))
    frames=[];hold=ControlPacket(0.,0.,.3,False,False,False,1);move=ControlPacket(.2,0.,0.,False,False,False,1)
    for number in range(98 if npc_schedule else 99,471):
        time=F(number-100,20);station=F(29,10) if number==99 else F(3)+F(number-100,20)
        x=float(station-10);arc=_metric_station((x,0.,0.),route);offset=desired_offset(arc,ego)
        y=float(offset)
        if defect=='home_displaced' and number>=460:y=.75
        if defect=='no_actual_offset':y=0.
        actual_body=replace(body,extents=(1.75,1.5,.25)) if defect=='wide_body' else body
        phase='NOMINAL' if number<=100 else 'PASS' if number<=340 else 'RETURN' if number<=465 else 'FORWARD'
        before=F(14,5) if number==99 else F(29,10) if number==100 else F(3)+F(number-101,20)
        old_arc=_metric_station((float(before-10),0.,0.),route)
        cmd=CommandRecord(1,number-1,number,'CONTROL',F(36,5) if phase in ('NOMINAL','FORWARD') else F(18,5),
                          desired_offset(old_arc,ego),None,None,phase,ego.hash)
        e=ActorFrame('EGO',1,replace(c.fixture.poses['EGO'],x=x,y=y),(2. if number<=100 else 1.,0.,0.),
            actual_body,arc,{},(cmd,),move,None,1,True,None)
        npc_phase=('NPC_DOOR_CLOSED_HOLD' if number<=98 else 'NPC_DOOR_OPEN' if number<=160 else 'NPC_DOOR_CLOSED') if npc_schedule else 'PARKED'
        npc_kind='DOOR_OPEN_REQUEST' if npc_schedule and number==99 else 'DOOR_CLOSE_REQUEST' if npc_schedule and number==161 else 'CONTROL'
        n=replace(e,role='NPC',id=2,pose=replace(e.pose,x=0.,y=0.),velocity=(0.,0.,0.),arc=F(10),
            commands=(CommandRecord(2,number-1,number,npc_kind,F(0),F(0),hold,None,npc_phase,npc.hash),),readback=hold)
        f=FrameRecord('boot','world',number,time,F(1,20),(e,n),(),{})
        ref=s.source('observed-'+str(number),{'boot':f.boot,'world':f.world,'frame':number,'simtime':time,'actors':f.actors},number,time)
        common={'fixture_hash':_digest(fixture),'frame':number,'actors_hash':_digest(f.actors)}
        opened=100<=number<161
        door=s.capability('DOOR_GEOMETRY','calibrated-door-envelope-v1',{**common,'door_state':'OPEN' if opened else 'CLOSED',
            'collider_envelope':tuple(product((0.,1.),(.5,1.5) if opened else (2.,3.),(-.5,.5)))},(ref,),F(0))
        fields={'frame_refs':(ref,),'door_geometry':door}
        if npc_schedule:
            fields['npc_controls']={'boot':f.boot,'world':f.world,'frame':number,'actor_id':2,'status':'CLEAR','witness_refs':(ref,)}
        path_limits={**common,'from_region_hash':_digest(initial),'to_region_hash':_digest(initial),
                     'route_hash':_digest(route),'minimum_clearance_m':F(1,2)}
        if defect!='missing_outbound' and not (defect=='lost_outbound' and number==200):
            fields['lane_change_path']=s.capability('LANE_CHANGE_PATH','bounded-lane-change-corridor-v1',path_limits,(ref,),F(0))
        if defect!='missing_return' and not (defect=='lost_return' and number==360):
            fields['return_path']=s.capability('RETURN_PATH','bounded-return-corridor-v1',path_limits,(ref,),F(0))
        if frames:
            limits={**common,'previous_frame':number-1,'previous_actors':_digest(frames[-1].actors),'actors':_digest(f.actors)}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',
                {k:v for k,v in limits.items() if k!='actors_hash'},(ref,),F(0))
        frames.append(replace(f,integrity=fields))
    frames=s.bind_frames(tuple(frames),fixture)
    return SimpleNamespace(s=s,frames=frames,fixture=fixture,ego=ego,npc=npc)


def test_f04_source_same_lane_paths_and_fixed_return_markers_drive_actual_producer(tmp_path):
    from m56.metrics import detect_events
    from m56.response import step_response
    from m56.model import ScriptState
    c=f04_spatial_observations(tmp_path/'sources');events=detect_events(c.frames,c.fixture);by_name={e.name:e for e in events}
    assert by_name['TRIGGER'].frame==100
    assert by_name['F04_END'].frame==321
    assert by_name['F04_OFFSET_CONFIRMED'].frame==225
    assert by_name['F04_RETURN_MARKER'].frame==340
    assert by_name['F04_RETURN_REFERENCE_MARKER'].frame==460
    assert by_name['F04_HOME_CONFIRMED'].frame==465
    assert len([e for e in events if e.name=='LANE_CHANGE_PATH_CLEAR'])>100
    assert len([e for e in events if e.name=='RETURN_PATH_CLEAR'])>100
    state=ScriptState('NOMINAL',F(-1,20),());outputs=[]
    for frame in c.frames:
        out=step_response(replace(frame,events=tuple(e for e in events if e.frame==frame.frame)),state,c.ego)
        state=out.state;outputs.append(out.command)
    assert next(cmd.frame for cmd in outputs if cmd.cause=='PASS')==100
    assert next(cmd.frame for cmd in outputs if cmd.cause=='RETURN')==340
    assert next(cmd.frame for cmd in outputs if cmd.cause=='FORWARD')==465
    assert next(cmd.offset for cmd in outputs if cmd.frame==460)==0
    assert all(cmd.target_kmh==F(18,5) for cmd in outputs if 100<=cmd.frame<465)
    assert not any(e.name=='DESTINATION_CONFIRMED' for e in events)
    # Source public W01-W05/full action and door scheduler still not admitted.


def test_f04_correct_offset_command_with_straight_observations_is_wrong_action_not_completion(tmp_path):
    from m56.metrics import detect_events,_f_action
    from m56.model import PhysicalState
    c=f04_spatial_observations(tmp_path/'sources','no_actual_offset')
    events=detect_events(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='F04_END')==321
    assert not any(e.name in ('F04_OFFSET_CONFIRMED','F04_HOME_CONFIRMED') for e in events)
    state,reasons=_f_action(c.frames,c.fixture,events)
    assert state==PhysicalState.FAILED,(state,reasons)
    assert 'SPATIAL_PASS_NOT_REALIZED' in reasons


@pytest.mark.parametrize('lost',[None,'lost_outbound','lost_return'])
def test_f04_source_phase_replay_requires_current_permission_after_pass_has_started(tmp_path,lost):
    from m56.metrics import _authenticated_events
    from m56.evidence import _phase_integrity
    c=f04_spatial_observations(tmp_path/'sources',lost)
    boundary=replace(c.frames[0],frame=98,simtime=F(-1,10),integrity={},
        actors=tuple(replace(a,commands=()) for a in c.frames[0].actors))
    episode=c.s.episode(c.frames,c.fixture,boundary)
    assert _authenticated_events(episode,c.fixture) is not None
    out=_phase_integrity(episode,c.fixture)
    assert out==(((),('FORWARD_COMMAND_REPLAY_UNPROVEN',)) if lost else ((),())),out


@pytest.mark.parametrize('defect,event',[('missing_outbound','LANE_CHANGE_PATH_CLEAR'),('missing_return','RETURN_PATH_CLEAR'),
                                        ('wide_body','LANE_CHANGE_PATH_CLEAR'),('home_displaced','F04_HOME_CONFIRMED')])
def test_f04_current_path_or_actual_home_not_inferred_from_other_lane_or_command(tmp_path,defect,event):
    from m56.metrics import detect_events
    c=f04_spatial_observations(tmp_path/'sources',defect)
    events=detect_events(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='TRIGGER')==100
    if defect=='wide_body':
        # The wide body fits at y0 before departure, but not the .75m plateau.
        assert not any(e.name==event and e.frame==220 for e in events)
    else:
        assert not any(e.name==event for e in events)
