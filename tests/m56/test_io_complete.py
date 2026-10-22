"""Source-backed parallel cut-in composition; synthetic software evidence only."""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

import pytest


def _complete_i(root,action='B',shared_geometry=None):
    from tests.m56.source_cases import Sources
    from m56.model import (BodyRecord,Transform6,DirectedRoute,Section,Domain,FrozenMetricPair,
        FrozenResponse,CompiledFixture,ActorRecipe,ActorFrame,FrameRecord,CommandRecord,
        ControlPacket,EventRecord,ScriptState,CapabilityProof,ReviewRecord)
    from m56.catalog import _digest
    from m56.metrics import detect_events
    from m56.response import desired_offset,step_response
    s=Sources(root)
    geometry=shared_geometry or s.source('geometry',{'scope':'synthetic exact horizontal parallel lanes'})
    if shared_geometry is not None:s.refs.append(shared_geometry)
    body=BodyRecord((0.,0.,0.),(0.,0.,0.),(.5,.25,.25),(),'vehicle.audi.a2',{}, {},geometry)
    def route(y):
        return DirectedRoute((),(Transform6(0.,y,0.,0.,0.,0.),Transform6(100.,y,0.,0.,0.,0.)),(F(0),F(100)),'b'*64,(geometry,),F(65))
    routes={'EGO':route(0.),'NPC':route(-3.)}
    def profile(start,length,a,b):
        return {'method':'quintic-arc-v1','segments':({'start_arc_m':F(start),'length_m':F(length),'start_offset_m':F(a),'end_offset_m':F(b)},)}
    def row(cause,event,guards=(),delay=F(0)):
        return {'cause':cause,'after_event':event,'requires':guards,'delay_s':delay}
    ego=FrozenResponse('EGO','B',routes['EGO'],{'SETTLE':F(0),'NOMINAL':F(6),'CHANGE':F(6),'TARGET':F(6)},profile(30,18,0,-3),
        {'category':'I','program':{'method':'ordered-event-program-v1','initial':'SETTLE','transitions':(
            row('NOMINAL','CAPTURE_START',delay=F(21,20)),row('CHANGE','SOURCE_CLEAR_CONFIRMED',('TRIGGER','LANE_CHANGE_PATH_CLEAR')),
            row('TARGET','TARGET_LANE_CONFIRMED',('REFERENCE_MARKER:TARGET',)))},'reference_switches':(
                {'cause':'TARGET','event':'TARGET_LANE_CONFIRMED','marker_arc_m':F(48),'route':route(-3.),'profile':profile(48,1,0,0)},)},'a'*64)
    ego_b=ego
    ego_a=replace(ego,action_id='A',hash='f'*64,targets={'SETTLE':F(0),'NOMINAL':F(6),'STOP':F(0),'RESUME':F(6)},
        profile=profile(0,1,0,0),phases={'category':'I','program':{'method':'ordered-event-program-v1',
            'initial':'SETTLE','transitions':(row('NOMINAL','CAPTURE_START',delay=F(21,20)),
                row('STOP','TRIGGER'),row('RESUME','SOURCE_CLEAR_CONFIRMED',('STOP_AFTER_TRIGGER','NPC_TARGET_LANE_CONFIRMED')))}})
    ego=ego_a if action=='A' else ego_b
    npc=FrozenResponse('NPC','NPC_COMMON',routes['NPC'],{'SETTLE':F(0),'NOMINAL':F(5),'NPC_TARGET':F(5)},profile(F(35,2),15,0,3),
        {'category':'I','program':{'method':'ordered-event-program-v1','initial':'SETTLE','transitions':(
            row('NOMINAL','CAPTURE_START',delay=F(21,20)),row('NPC_TARGET','NPC_TARGET_LANE_CONFIRMED',('REFERENCE_MARKER:NPC:NPC_TARGET',)))},
         'reference_switches':({'cause':'NPC_TARGET','event':'NPC_TARGET_LANE_CONFIRMED','marker_arc_m':F(65,2),'route':route(0.),'profile':profile(F(65,2),1,0,0)},)},'c'*64)
    def box(y):return tuple(product((-2.,102.),(y-1.5,y+1.5),(-1.,1.)))
    initial,target=box(0.),box(-3.)
    def section(x):return Section(tuple(product((float(x),),(-5.,2.),(-1.,1.))),(1.,0.,0.),F(x),{})
    intrusion=Section(tuple(product((-2.,102.),(-1.5,),(-1.,1.))),(0.,1.,0.),F(0),{})
    domain=Domain(section(1),section(2),section(1),section(2),(),{'category':'I','source_region':target,
        'action_regions':{'EGO_INITIAL':initial,'EGO_TARGET':target},'npc_regions':{'NPC_INITIAL':target,'NPC_TARGET':initial},
        'driving_regions':{'EGO':(initial,target),'NPC':(initial,target)}},(geometry,),'d'*64)
    reference={'method':'segment-map-normal-v1','route':routes['EGO'],'normals':((0.,1.,0.),),'refs':(geometry,)}
    pair=FrozenMetricPair(('v_mean_E','e_lat_peak'),('m/s','m'),('mean_speed','map_lateral_peak'),(('TRIGGER','X_END'),)*2,
                         'map:'+_digest(reference),'e'*64,'APPROVED_PROPOSAL_NOT_READY')
    poses={'EGO':Transform6(0.,0.,0.,0.,0.,0.),'NPC':Transform6(10.,-3.,0.,0.,0.,0.)}
    actors=tuple(ActorRecipe(role,'vehicle.audi.a2',F(0),pose,{'kind':'synthetic'},{'kind':'synthetic'},F(65)) for role,pose in poses.items())
    fixture=CompiledFixture('1'*64,'2'*64,actors,{'readiness':{'targets_mps':{'EGO':F(6),'NPC':F(5)},
        'markers_m':{'EGO':F(33,10),'NPC':F(51,4)}}},poses,routes,domain,None,
        {'I_SOURCE_BOUNDARY':intrusion,'X':section(60),'DESTINATION':section(65)},(ego_a,ego_b,npc),pair,(),geometry)
    responses=(ego,npc);frames=[];forward=ControlPacket(.2,0.,0.,False,False,False,1);hold=ControlPacket(0.,0.,.3,False,False,False,1)
    def cap(kind,method,limits,ref):
        packet=dict(kind=kind,method=method,raw_refs=(ref,),uncertainty=F(0),limits=limits,status='CORROBORATED')
        review=ReviewRecord(_digest(packet),'CAPABILITY:'+kind,(ref,),'SYNTHETIC_AUTHOR','2026-10-11','APPROVED',('literal exact sample only',),ref)
        return CapabilityProof(**packet,review=review)
    for i in range(271 if action=='A' else 251):
        frame=100+i;time=F(i,20);ref=replace(geometry,frame=frame,time=time);packets=[]
        for identity,(role,response) in enumerate(zip(('EGO','NPC'),responses),1):
            station=(F(3,10)*max(0,i-20) if role=='EGO' else F(10)+F(1,4)*max(0,i-20))
            lateral=desired_offset(station,response)
            pose=replace(poses[role],x=float(station),y=float(F(0 if role=='EGO' else -3)+lateral))
            control=hold if i<=20 else forward
            command=CommandRecord(identity,frame-1,frame,'CONTROL',F(0),F(0),control,None,'SETTLE',response.hash)
            packets.append(ActorFrame(role,identity,pose,(0. if i<=20 else float(6 if role=='EGO' else 5),0.,0.),body,station,{},(command,),control,None,1,True,None))
        f=FrameRecord('boot','world',frame,time,F(1,20),tuple(packets),(),{'frame_refs':(ref,),
            'metric_context':{'reference':pair.reference,'pair_hash':pair.hash,'map_reference':reference,'uncertainty':{name:F(0) for name in pair.names}},
            'npc_controls':{'boot':'boot','world':'world','frame':frame,'actor_id':2,'status':'CLEAR','witness_refs':(ref,)}})
        if frames:
            limits={'fixture_hash':_digest(fixture),'previous_actors':_digest(frames[-1].actors),'actors':_digest(f.actors),'previous_frame':frame-1,'frame':frame}
            f=replace(f,integrity={**f.integrity,'continuous_geometry':cap('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,ref)})
        limits={'fixture_hash':_digest(fixture),'frame':frame,'actors_hash':_digest(f.actors),'from_region_hash':_digest(initial),
                'to_region_hash':_digest(target),'route_hash':_digest(routes['EGO']),'minimum_clearance_m':F(1)}
        f=replace(f,integrity={**f.integrity,'lane_change_path':cap('LANE_CHANGE_PATH','bounded-lane-change-corridor-v1',limits,ref)})
        frames.append(f)
    events=detect_events(tuple(frames),fixture)
    if action=='A':
        # NPC motion is common and independent of Ego. Derive release from its
        # observed merge/clear holds and Ego's actual .50s STOP, not a preset time.
        by_name={e.name:e for e in events}
        stop=by_name['TRIGGER'].frame+1
        resume=max(stop+10,by_name['SOURCE_CLEAR_CONFIRMED'].frame,by_name['NPC_TARGET_LANE_CONFIRMED'].frame)
        corrected=[]
        for f in frames:
            ego_actor,npc_actor=f.actors
            lost=F(3,10)*min(max(0,f.frame-stop+1),resume-stop+1)
            station=ego_actor.arc-lost;stopped=stop<=f.frame<=resume
            ego_actor=replace(ego_actor,pose=replace(ego_actor.pose,x=float(station)),arc=station,
                velocity=(0. if stopped else ego_actor.velocity[0],0.,0.),readback=hold if stopped else ego_actor.readback)
            f=replace(f,actors=(ego_actor,npc_actor))
            if corrected:
                ref=f.integrity['frame_refs'][0]
                limits={'fixture_hash':_digest(fixture),'previous_actors':_digest(corrected[-1].actors),
                    'actors':_digest(f.actors),'previous_frame':f.frame-1,'frame':f.frame}
                f=replace(f,integrity={**f.integrity,'continuous_geometry':cap('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,ref)})
            corrected.append(f)
        frames=corrected;events=detect_events(tuple(frames),fixture)
        assert any(e.name=='STOP_AFTER_TRIGGER' for e in events)
    required={'TRIGGER','SOURCE_CLEAR_CONFIRMED','NPC_TARGET_LANE_CONFIRMED',
              'REFERENCE_MARKER:NPC:NPC_TARGET','X_END','DESTINATION_CONFIRMED'}
    required|=({'STOP_AFTER_TRIGGER'} if action=='A' else
               {'LANE_CHANGE_ONSET','TARGET_LANE_CONFIRMED','REFERENCE_MARKER:TARGET'})
    assert required<={e.name for e in events}
    boundary=replace(frames[0],frame=99,simtime=-F(1,20),actors=tuple(replace(a,commands=()) for a in frames[0].actors))
    capture=EventRecord('CAPTURE_START',99,-F(1,20),(replace(geometry,frame=99,time=-F(1,20)),))
    states={r.actor_role:ScriptState('SETTLE',-F(1,20),(capture,)) for r in responses}
    commands={a.role:CommandRecord(a.id,99,100,'CONTROL',F(0),F(0),hold,None,'SETTLE',r.hash) for a,r in zip(boundary.actors,responses)}
    produced=[]
    for f in frames:
        actors=tuple(replace(a,commands=(replace(commands[a.role],control=a.readback),)) for a in f.actors)
        f=replace(f,actors=actors,events=tuple(e for e in events if e.frame==f.frame))
        produced.append(replace(f,events=()))
        for r in responses:
            out=step_response(f,states[r.actor_role],r);states[r.actor_role]=out.state;commands[r.actor_role]=out.command
    episode=s.complete(tuple(produced),fixture,boundary,120,131)
    return SimpleNamespace(episode=episode,fixture=fixture,sources=s)


@pytest.fixture(scope='module')
def complete_i_b(tmp_path_factory):
    return _complete_i(tmp_path_factory.mktemp('i-composition')/'sources')


@pytest.fixture(scope='module')
def complete_i_a(tmp_path_factory,complete_i_b):
    return _complete_i(tmp_path_factory.mktemp('i-a-composition')/'sources','A',complete_i_b.fixture.freeze_ref)


def test_source_producer_public_witness_completes_stop_then_merged_cut_in(complete_i_a):
    from m56.evidence import check_integrity
    from m56.metrics import evaluate_episode,_authenticated_events
    c=complete_i_a;out=check_integrity(c.episode,c.fixture)
    assert out.status=='WITNESS_VALID',out.reasons
    verdict=evaluate_episode(c.episode,c.fixture)
    assert (verdict.spawn,verdict.physical,verdict.witness)==('CONFIRMED','COMPLETE','VALID'),verdict.reasons
    assert verdict.metrics['e_lat_peak'].value==0 and 0<verdict.metrics['v_mean_E'].value<6
    events=_authenticated_events(c.episode,c.fixture)
    merge=max(e.frame for e in events if e.name in ('SOURCE_CLEAR_CONFIRMED','NPC_TARGET_LANE_CONFIRMED'))
    commands=[a.commands[0] for f in c.episode.raw for a in f.actors if a.role=='EGO']
    assert next(cmd.frame for cmd in commands if cmd.cause=='RESUME')>=merge
    assert all(cmd.offset==0 for cmd in commands)


def test_source_cut_in_ab_does_not_turn_two_valid_actions_into_automatic_pass(complete_i_a,complete_i_b):
    from m56.catalog import _digest
    from m56.metrics import _source_metrics,_ab_review_subject,_ab_fulltrace_review,compare_ab
    a,b=complete_i_a,complete_i_b
    assert _digest(a.fixture)==_digest(b.fixture)
    left,right=_source_metrics(a.episode,a.fixture),_source_metrics(b.episode,b.fixture)
    refs=tuple(dict.fromkeys(r for e in (a.episode,b.episode) for r in (e.fixture,e.manifest,*e.journal,*e.source)))
    review=a.sources.review(_ab_review_subject(a.episode,b.episode,a.fixture.pair,left,right),
        'REALIZED_AB_COMPARABILITY_D09',refs)
    review=replace(review,reasons=tuple(k+': synthetic software contract only, not scientific qualification'
        for k in ('fulltrace','near_zero','nearstanding','identity','mechanism','comparability')))
    out=compare_ab(a.episode,b.episode,a.fixture.pair,review)
    assert out.status=='NUMERIC_FAILED',out
    assert out.comparisons[0]<F(1,5) and out.comparisons[1]==1
    assert _ab_fulltrace_review(a.episode,b.episode,a.fixture.pair,left,right,review)
    assert compare_ab(a.episode,b.episode,a.fixture.pair,None).status=='NUMERIC_FAILED'
    assert compare_ab(a.episode,a.episode,a.fixture.pair,review).status=='INVALID'


def test_source_producer_public_witness_completes_supported_cut_in(complete_i_b):
    from m56.evidence import check_integrity
    from m56.metrics import evaluate_episode
    c=complete_i_b;out=check_integrity(c.episode,c.fixture)
    assert out.status=='WITNESS_VALID',out.reasons
    verdict=evaluate_episode(c.episode,c.fixture)
    assert (verdict.spawn,verdict.physical,verdict.witness)==('CONFIRMED','COMPLETE','VALID'),verdict.reasons
    assert verdict.metrics['v_mean_E'].value==6 and verdict.metrics['e_lat_peak'].value==3
