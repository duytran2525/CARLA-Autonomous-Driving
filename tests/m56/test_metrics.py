"""Offline event/metric kernels. Literal traces never represent native evidence."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


@pytest.fixture
def clear_frames():
    from m56.model import FrameRecord, EventRecord, SourceRef
    entry_ref=SourceRef('synthetic://entry','a'*64,1,'test','literal','SYNTHETIC_TEST',99,F(-1,20))
    entry=EventRecord('NPC_ENTRY',99,F(-1,20),(entry_ref,))
    frames=[]
    for i in range(6):
        time=F(i,20);frame=100+i
        ref=replace(entry_ref,uri=f'synthetic://frame/{frame}',frame=frame,time=time)
        # Producer-owned, frame-correlated derived predicate, not native authority.
        predicate={'value':True,'frame':frame,'time':time,'fixture_hash':'b'*64,'witness_refs':(ref,)}
        frames.append(FrameRecord('SYNTHETIC_BOOT','SYNTHETIC_WORLD',frame,time,F(1,20),(),
                      (entry,) if i==0 else (),{'predicates':{'NPC_WHOLE_BODY_CLEAR':predicate}}))
    return tuple(frames)


def test_clear_timestamp_is_confirmation_frame(require,clear_frames):
    confirm=require('m56.metrics','confirm_hold')
    out=confirm(clear_frames,'NPC_WHOLE_BODY_CLEAR',F(1,4))
    assert out.name=='CLEAR_N_CONFIRMED'
    assert out.frame==105
    assert out.time==F(1,4)
    assert out.witness_refs


def test_actual_duration_below_hold_not_confirmed(require,clear_frames):
    confirm=require('m56.metrics','confirm_hold')
    assert confirm(clear_frames[:-1],'NPC_WHOLE_BODY_CLEAR',F(1,4)) is None


def test_false_sample_resets_hold(require,clear_frames):
    confirm=require('m56.metrics','confirm_hold')
    frames=list(clear_frames);f=frames[2]
    p={**f.integrity['predicates']['NPC_WHOLE_BODY_CLEAR'],'value':False}
    frames[2]=replace(f,integrity={'predicates':{'NPC_WHOLE_BODY_CLEAR':p}})
    assert confirm(tuple(frames),'NPC_WHOLE_BODY_CLEAR',F(1,4)) is None


def test_frame_gap_unknown_not_never_event(require,clear_frames):
    confirm=require('m56.metrics','confirm_hold')
    assert confirm(clear_frames[:2]+clear_frames[3:],'NPC_WHOLE_BODY_CLEAR',F(1,4)) is None


def test_clear_without_recorded_entry_never_confirms(require,clear_frames):
    confirm=require('m56.metrics','confirm_hold')
    frames=tuple(replace(f,events=()) for f in clear_frames)
    assert confirm(frames,'NPC_WHOLE_BODY_CLEAR',F(1,4)) is None


@pytest.fixture
def crossing_trace():
    from types import SimpleNamespace
    from m56.model import (SourceRef,BodyRecord,Transform6,DirectedRoute,Section,Domain,
        FrozenMetricPair,CompiledFixture,ActorFrame,FrameRecord,CapabilityProof,ReviewRecord)
    from m56.catalog import _digest
    ref=SourceRef('synthetic://trace','a'*64,1,'test','literal','SYNTHETIC_TEST')
    body=BodyRecord((0.,0.,0.),(0.,0.,0.),(.5,.25,.25),(),'vehicle.audi.a2',{}, {},ref)
    route=DirectedRoute((),(Transform6(0.,0.,0.,0.,0.,0.),Transform6(30.,0.,0.,0.,0.,0.)),
                        (F(0),F(30)),'b'*64,(ref,),F(20))
    def section(x):
        return Section(tuple((float(x),y,z) for y in (-1.,1.) for z in (-1.,1.)),
                       (1.,0.,0.),F(x),{'z_min':F(-1),'z_max':F(1)})
    domain=Domain(section(10),section(12),section(10),section(12),
                  tuple((x,y,z) for x in (10.,12.) for y in (-1.,1.) for z in (-1.,1.)),
                  {'kind':'synthetic'},(ref,),'c'*64)
    pair=FrozenMetricPair(('d_yield_m','t_entry_s'),('m','s'),('forward_distance','elapsed'),
                (('TRIGGER','CLEAR_N_CONFIRMED'),('TRIGGER','E_ENTRY')),
                'route:'+_digest(route),'d'*64,'APPROVED_PROPOSAL_NOT_READY')
    fixture=CompiledFixture('e'*64,'f'*64,(),{}, {},{'EGO':route,'NPC':route},domain,F(3),{},(),pair,(),ref)
    frames=[]
    for i,(ego,npc) in enumerate(zip((0.,6.,7.,9.,10.,11.,12.,13.,14.),
                                     (9.,10.,12.,13.5,13.5,13.5,13.5,13.5,13.5))):
        actors=tuple(ActorFrame(role,j,Transform6(x,0.,0.,0.,0.,0.),(1.,0.,0.),body,F(x),{},(),None,None,10,True,None)
                     for j,(role,x) in enumerate((('EGO',ego),('NPC',npc)),1))
        raw=replace(ref,frame=100+i,time=F(i,20))
        frame=FrameRecord('SYNTHETIC_BOOT','SYNTHETIC_WORLD',100+i,F(i,20),F(1,20),actors,(),
              {'frame_refs':(raw,),'metric_context':{'reference':pair.reference,'pair_hash':pair.hash,
               'directed_route':route,'uncertainty':{'d_yield_m':F(1,20),'t_entry_s':F(0)}}})
        if frames:
            payload={'kind':'CONTINUOUS_GEOMETRY','method':'bounded-interframe-body-v1','raw_refs':(raw,),
                     'uncertainty':F(1,1000),'limits':{'fixture_hash':_digest(fixture),
                     'previous_actors':_digest(frames[-1].actors),'actors':_digest(actors),
                     'previous_frame':frame.frame-1,'frame':frame.frame},'status':'CORROBORATED'}
            review=ReviewRecord(_digest(payload),'CAPABILITY:CONTINUOUS_GEOMETRY',(raw,),
                                'SYNTHETIC_TEST','2026-10-08','APPROVED',('literal observation proof',),raw)
            proof=CapabilityProof(**payload,review=review)
            frame=replace(frame,integrity={**frame.integrity,'continuous_geometry':proof})
        frames.append(frame)
    return SimpleNamespace(frames=tuple(frames),fixture=fixture)


def test_first_bracketed_crossings_and_wholebody_confirmation(require,crossing_trace):
    detect=require('m56.metrics','detect_events')
    c=crossing_trace
    events={e.name:e for e in detect(c.frames,c.fixture)}
    assert events['TRIGGER'].frame==102
    assert events['NPC_ENTRY'].frame==101
    assert events['E_ENTRY'].frame==104
    assert events['CLEAR_N_CONFIRMED'].frame==108
    assert events['CLEAR_N_CONFIRMED'].time==F(2,5)


def test_missing_bracket_no_trigger(require,crossing_trace):
    detect=require('m56.metrics','detect_events')
    c=crossing_trace
    assert 'TRIGGER' not in {e.name for e in detect(c.frames[2:],c.fixture)}


def test_rear_body_and_sweep_required(require,crossing_trace):
    detect=require('m56.metrics','detect_events')
    c=crossing_trace
    no_bounds=tuple(replace(f,integrity={'frame_refs':f.integrity['frame_refs']}) for f in c.frames)
    assert 'CLEAR_N_CONFIRMED' not in {e.name for e in detect(no_bounds,c.fixture)}


def test_lateral_escape_never_clears(require,crossing_trace):
    detect=require('m56.metrics','detect_events')
    c=crossing_trace
    frames=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],route_valid=False))) for f in c.frames)
    assert 'CLEAR_N_CONFIRMED' not in {e.name for e in detect(frames,c.fixture)}


def test_common_clm_windows_use_actual_distance_and_elapsed(require,crossing_trace):
    detect=require('m56.metrics','detect_events');measure=require('m56.metrics','measure')
    c=crossing_trace
    out=measure(c.frames,c.fixture.pair,detect(c.frames,c.fixture))
    assert [(m.name,m.value,m.status) for m in out]==[
        ('d_yield_m',F(7),'VALID'),('t_entry_s',F(1,10),'VALID')]
    assert out[0].frames==tuple(range(102,109))
    assert out[1].frames==(102,103,104)
    assert out[0].uncertainty==F(1,20)


def test_never_clear_is_incomplete_not_60s(require,crossing_trace):
    detect=require('m56.metrics','detect_events');measure=require('m56.metrics','measure')
    c=crossing_trace;frames=c.frames[:-1]
    out=measure(frames,c.fixture.pair,detect(frames,c.fixture))
    assert out[0].value is None and out[0].status=='INCOMPLETE'
    assert out[1].value==F(1,10)


def test_metric_frame_gap_is_unknown_not_physical_never_event(require,crossing_trace):
    measure=require('m56.metrics','measure')
    c=crossing_trace
    out=measure(c.frames[:3]+c.frames[4:],c.fixture.pair,())
    assert all(m.value is None and m.status=='UNKNOWN' for m in out)


def test_metric_reference_and_event_frame_must_match(require,crossing_trace):
    detect=require('m56.metrics','detect_events');measure=require('m56.metrics','measure')
    c=crossing_trace;events=detect(c.frames,c.fixture)
    changed=replace(c.fixture.pair,reference='spawn-biased-reference')
    assert all(m.status=='UNKNOWN' for m in measure(c.frames,changed,events))
    stale=tuple(replace(e,time=e.time+F(1,20)) if e.name=='TRIGGER' else e for e in events)
    assert all(m.status=='UNKNOWN' for m in measure(c.frames,c.fixture.pair,stale))


@pytest.fixture
def rebind_trace():
    """Synthetic source/interval producer; no native observation or authority."""
    from m56.model import CapabilityProof,ReviewRecord
    from m56.catalog import _digest
    def bind(frames,fixture):
        result=[]
        for f in frames:
            raw=f.integrity['frame_refs'][0]
            integrity={k:v for k,v in f.integrity.items() if k!='continuous_geometry'}
            if result:
                payload={'kind':'CONTINUOUS_GEOMETRY','method':'bounded-interframe-body-v1','raw_refs':(raw,),
                         'uncertainty':F(1,1000),'limits':{'fixture_hash':_digest(fixture),
                         'previous_actors':_digest(result[-1].actors),'actors':_digest(f.actors),
                         'previous_frame':result[-1].frame,'frame':f.frame},'status':'CORROBORATED'}
                review=ReviewRecord(_digest(payload),'CAPABILITY:CONTINUOUS_GEOMETRY',(raw,),
                                    'SYNTHETIC_TEST','2026-10-08','APPROVED',('literal proof',),raw)
                integrity['continuous_geometry']=CapabilityProof(**payload,review=review)
            result.append(replace(f,integrity=integrity))
        return tuple(result)
    return bind


@pytest.fixture
def io_trace(crossing_trace,rebind_trace):
    from m56.model import FrozenMetricPair,Section
    from types import SimpleNamespace
    c=crossing_trace
    pair=FrozenMetricPair(('v_mean_E','e_lat_peak'),('m/s','m'),('mean_speed','map_lateral_peak'),
                         (('TRIGGER','X_END'),)*2,'initial-map-lane','d'*64,'APPROVED_PROPOSAL_NOT_READY')
    boundary=Section(tuple((x,0.,z) for x in (0.,30.) for z in (-1.,1.)),
                     (0.,1.,0.),F(0),{'z_min':F(-1),'z_max':F(1)})
    decision=replace(c.fixture.domain.e_entry,route_station=F(2),
                     vertices=tuple((2.,y,z) for _,y,z in c.fixture.domain.e_entry.vertices))
    end=replace(decision,route_station=F(3),vertices=tuple((3.,y,z) for _,y,z in decision.vertices))
    fixture=replace(c.fixture,G=None,pair=pair,sections={'I_SOURCE_BOUNDARY':boundary,'X':end},
                    domain=replace(c.fixture.domain,topology={'category':'I'}))
    frames=[]
    for i,f in enumerate(c.frames[:4]):
        e,n=f.actors
        e=replace(e,pose=replace(e.pose,x=float(i+1)),arc=F(i+1))
        n=replace(n,pose=replace(n.pose,x=5.,y=(-.5,-.125,.5,.5)[i]),arc=F(5))
        frames.append(replace(f,actors=(e,n)))
    return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture,decision=decision)


@pytest.fixture
def io_action_trace(io_trace,rebind_trace):
    from m56.model import FrozenResponse,CommandRecord,ControlPacket
    from types import SimpleNamespace
    c=io_trace
    def build(category='I',action='B',missing_regions=False):
        def box(y0,y1):
            return tuple((x,y,z) for x in (0.,30.) for y in (y0,y1) for z in (-1.,1.))
        topology={'category':category,'action_regions':{'EGO_INITIAL':box(-1.,1.),'EGO_TARGET':box(-3.,-1.5)}}
        if missing_regions:
            topology.pop('action_regions')
        response=FrozenResponse('EGO',action,c.fixture.routes['EGO'],{}, {},{},'a'*64)
        sections={'X':c.fixture.sections['X'],('I_SOURCE_BOUNDARY' if category=='I' else 'O_DECISION'):
                   c.fixture.sections['I_SOURCE_BOUNDARY'] if category=='I' else c.decision}
        fixture=replace(c.fixture,responses=(response,),sections=sections,domain=replace(c.fixture.domain,topology=topology))
        frames=[]
        for f in c.frames:
            ego=f.actors[0];control=ControlPacket(.2,0.,0.,False,False,False,1)
            command=CommandRecord(ego.id,f.frame-1,f.frame,'CONTROL',F(9),F(0),control,None,'SYNTHETIC',response.hash)
            frames.append(replace(f,actors=(replace(ego,commands=(command,),readback=control),f.actors[1])))
        return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)
    return build


@pytest.mark.parametrize('category,action',[('I','B'),('O','A')])
def test_io_metric_end_cannot_replace_actual_lane_change(require,io_action_trace,category,action):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=io_action_trace(category,action);events=detect(c.frames,c.fixture)
    assert 'X_END' in {e.name for e in events}
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='FAILED'
    assert 'MANEUVER_NOT_COMPLETE_BY_X' in reasons


def test_i_a_metric_end_without_stop_failed(require,io_action_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=io_action_trace('I','A');state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='FAILED'
    assert 'STOP_REQUIRED_BEFORE_X' in reasons


def test_io_missing_reviewed_regions_unknown_not_lane_failure(require,io_action_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=io_action_trace(missing_regions=True);state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='UNKNOWN'
    assert 'ACTION_REGIONS_UNPROVEN' in reasons


def test_i_b_cannot_change_before_actual_source_clear(require,io_action_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=io_action_trace('I','B')
    end=replace(c.fixture.sections['X'],vertices=tuple((3.,y,z) for y in (-4.,2.) for z in (-1.,1.)))
    fixture=replace(c.fixture,sections={**c.fixture.sections,'X':end})
    frames=tuple(replace(f,actors=(replace(f.actors[0],pose=replace(f.actors[0].pose,y=y)),f.actors[1]))
                 for f,y in zip(c.frames,(0.,-1.6,-2.25,-2.25)))
    frames=rebind_trace(frames,fixture);events=detect(frames,fixture)
    assert 'X_END' in {e.name for e in events}
    assert 'SOURCE_CLEAR_CONFIRMED' not in {e.name for e in events}
    state,reasons=audit(frames,fixture,events)
    assert state=='FAILED'
    assert 'CHANGED_BEFORE_SOURCE_CLEAR' in reasons


def test_o_b_follow_requires_actual_bumper_gap_not_only_lane_or_target(require,io_action_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=io_action_trace('O','B');state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='FAILED'
    assert 'FOLLOW_GAP_VIOLATION' in reasons


def test_confirmed_wrong_lane_is_not_erased_by_unknown_follow_gap(require,io_action_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=io_action_trace('O','B')
    sections={key:replace(section,vertices=tuple((float(section.route_station),y,z) for y in (-4.,2.) for z in (-1.,1.)))
              for key,section in c.fixture.sections.items()}
    fixture=replace(c.fixture,sections=sections)
    frames=tuple(replace(f,actors=(replace(f.actors[0],pose=replace(f.actors[0].pose,y=-2.25)),
                                  replace(f.actors[1],pose=replace(f.actors[1].pose,x=40.),arc=F(40)))) for f in c.frames)
    frames=rebind_trace(frames,fixture)
    state,reasons=audit(frames,fixture,detect(frames,fixture))
    assert state=='FAILED'
    assert 'UNPLANNED_LANE_CHANGE' in reasons
    assert 'FOLLOW_GAP_UNKNOWN' in reasons


@pytest.fixture
def io_wait_trace(io_action_trace,rebind_trace):
    from types import SimpleNamespace
    def build(action='A',behind=False,count=30):
        c=io_action_trace('I',action)
        def box(y0,y1):
            return tuple((x,y,z) for x in (0.,30.) for y in (y0,y1) for z in (-1.,1.))
        sections={**c.fixture.sections,'X':replace(c.fixture.sections['X'],route_station=F(25),
                    vertices=tuple((25.,y,z) for y in (-4.,4.) for z in (-1.,1.)))}
        topology={**c.fixture.domain.topology,'source_region':box(-3.5,0.),
                  'action_regions':{'EGO_INITIAL':box(0.,3.5),'EGO_TARGET':box(-3.5,0.)}}
        fixture=replace(c.fixture,sections=sections,domain=replace(c.fixture.domain,topology=topology))
        frames=[]
        for i in range(count):
            f=c.frames[0];e,n=f.actors;number=100+i;time=F(i,20)
            x=2.+(.1*max(0,i-13) if action=='A' else .1*i)
            speed=0. if action=='A' and i<=13 else 2.
            e=replace(e,pose=replace(e.pose,x=x,y=1.5),arc=F(x),velocity=(speed,0.,0.),
                      commands=tuple(replace(command,frame=number-1,next_frame=number) for command in e.commands))
            ny=-.5 if i==0 else -.125 if action=='B' or i==1 else 1.5
            nx=1. if behind else 8.
            n=replace(n,pose=replace(n.pose,x=nx,y=ny),arc=F(nx),velocity=(0.,0.,0.))
            ref=replace(f.integrity['frame_refs'][0],frame=number,time=time)
            frames.append(replace(f,frame=number,simtime=time,actors=(e,n),integrity={'frame_refs':(ref,)}))
        return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)
    return build


def test_i_a_resume_needs_actual_npc_merged_ahead_not_just_source_clear(require,io_wait_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=io_wait_trace(behind=True);events=detect(c.frames,c.fixture)
    assert 'SOURCE_CLEAR_CONFIRMED' in {e.name for e in events}
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='FAILED'
    assert 'RESUMED_BEFORE_NPC_MERGED_AHEAD' in reasons


def test_i_a_source_clear_and_actual_merge_do_not_require_a_fake_wait(require,io_wait_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=io_wait_trace();state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='INCOMPLETE'  # no X or destination yet
    assert 'RESUMED_BEFORE_NPC_MERGED_AHEAD' not in reasons


@pytest.mark.parametrize('count,status',[(82,'INCOMPLETE'),(83,'FAILED')])
def test_i_b_source_clear_wait_cannot_exceed_four_seconds(require,io_wait_trace,count,status):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=io_wait_trace(action='B',count=count);state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state==status
    assert ('SOURCE_CLEAR_WAIT_EXCEEDED' in reasons)==(status=='FAILED')


@pytest.fixture
def i_change_trace(io_wait_trace,rebind_trace,frame_capability):
    from types import SimpleNamespace
    from m56.catalog import _digest
    def build(fault=None):
        c=io_wait_trace(action='B',count=23)
        end=replace(c.fixture.sections['X'],route_station=F(89,8),
                    vertices=tuple((11.125,y,z) for y in (-4.,4.) for z in (-1.,1.)))
        initial_route=replace(c.fixture.routes['EGO'],transforms=tuple(replace(p,y=1.5) for p in c.fixture.routes['EGO'].transforms))
        reference={'method':'segment-map-normal-v1','route':initial_route,'normals':((0.,1.,0.),),'refs':initial_route.continuity}
        pair=replace(c.fixture.pair,reference='map:'+_digest(reference))
        fixture=replace(c.fixture,pair=pair,sections={**c.fixture.sections,'X':end})
        frames=[]
        for i,f in enumerate(c.frames):
            e,n=f.actors;x=2.+.5*i
            y=1.5 if i<=8 else (1.,.5,-.5,-1.75)[min(i-9,3)]
            if fault=='early_lateral' and 4<=i<=8:
                y=1.375
            e=replace(e,pose=replace(e.pose,x=x,y=y),arc=F(x),velocity=(10.,0.,0.))
            n=replace(n,pose=replace(n.pose,x=16.,y=-.5 if i==0 else -.125 if i==1 else 1.5),arc=F(16))
            frames.append(replace(f,actors=(e,n),integrity={**f.integrity,'metric_context':{
                'pair_hash':pair.hash,'reference':pair.reference,'map_reference':reference}}))
        frames=rebind_trace(tuple(frames),fixture);regions=fixture.domain.topology['action_regions']
        if fault!='missing':
            recorded=[]
            for f in frames:
                limits={'from_region_hash':_digest(regions['EGO_INITIAL']),'to_region_hash':_digest(regions['EGO_TARGET']),
                        'route_hash':_digest(fixture.routes['EGO']),'minimum_clearance_m':F(1)}
                if f.frame==110:
                    if fault=='wrong_region':limits['to_region_hash']='0'*64
                    elif fault=='clearance':limits['minimum_clearance_m']=F(1,5)
                f=frame_capability(f,fixture,'lane_change_path','LANE_CHANGE_PATH','bounded-lane-change-corridor-v1',limits)
                if fault=='stale_frame' and f.frame==110:
                    proof=f.integrity['lane_change_path']
                    f=replace(f,integrity={**f.integrity,'lane_change_path':replace(proof,limits={**proof.limits,'frame':109})})
                recorded.append(f)
            frames=tuple(recorded)
        return SimpleNamespace(frames=frames,fixture=fixture)
    return build


@pytest.mark.parametrize('fault',['missing','wrong_region','clearance','stale_frame'])
def test_i_source_clear_and_arrival_do_not_replace_independent_change_path(require,i_change_trace,fault):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=i_change_trace(fault);events=detect(c.frames,c.fixture)
    assert {'SOURCE_CLEAR_CONFIRMED','X_END'}.issubset({e.name for e in events})
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='UNKNOWN'
    assert 'LANE_CHANGE_PATH_UNPROVEN' in reasons


def test_i_cannot_begin_lateral_motion_before_source_clear_while_body_still_initial(require,i_change_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=i_change_trace('early_lateral');events=detect(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='SOURCE_CLEAR_CONFIRMED')==107
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='FAILED'
    assert 'CHANGED_BEFORE_SOURCE_CLEAR' in reasons


def test_recurring_path_events_do_not_invalidate_unique_metric_endpoints(require,i_change_trace):
    c=i_change_trace();frames=tuple(replace(f,integrity={**f.integrity,'metric_context':{
        **f.integrity['metric_context'],'uncertainty':{'v_mean_E':F(0),'e_lat_peak':F(0)}}}) for f in c.frames)
    events=require('m56.metrics','detect_events')(frames,c.fixture)
    values=require('m56.metrics','measure')(frames,c.fixture.pair,events)
    assert [(v.value,v.status) for v in values]==[(F(10),'VALID'),(F(13,4),'VALID')]
    trigger=next(e for e in events if e.name=='TRIGGER')
    assert all(v.status=='UNKNOWN' for v in require('m56.metrics','measure')(frames,c.fixture.pair,(*events,trigger)))


def test_io_path_events_are_recomputed_per_frame_not_cached_flags(require,i_change_trace,rebind_trace):
    c=i_change_trace();detect=require('m56.metrics','detect_events')
    events=detect(c.frames,c.fixture)
    path=tuple(e.frame for e in events if e.name=='LANE_CHANGE_PATH_CLEAR')
    assert path==tuple(range(101,123))
    frames=list(c.frames);f=frames[115-100]
    frames[115-100]=replace(f,integrity={k:v for k,v in f.integrity.items() if k!='lane_change_path'})
    events=detect(tuple(frames),c.fixture)
    assert 115 not in {e.frame for e in events if e.name=='LANE_CHANGE_PATH_CLEAR'}
    assert 116 in {e.frame for e in events if e.name=='LANE_CHANGE_PATH_CLEAR'}


def test_target_lane_confirmation_requires_whole_body_margin_and_quarter_second(require,i_change_trace):
    c=i_change_trace();events=require('m56.metrics','detect_events')(c.frames,c.fixture)
    target=next((e for e in events if e.name=='TARGET_LANE_CONFIRMED'),None)
    assert target is not None
    assert target.frame==116 and target.time==F(4,5)
    assert {r.frame for r in target.witness_refs}.issuperset(range(111,117))


def test_target_lane_confirmation_resets_on_boundary_return(require,i_change_trace,rebind_trace):
    c=i_change_trace();frames=list(c.frames);f=frames[14];e,n=f.actors
    frames[14]=replace(f,actors=(replace(e,pose=replace(e.pose,y=0.)),n))
    frames=rebind_trace(tuple(frames),c.fixture)
    events=require('m56.metrics','detect_events')(frames,c.fixture)
    target=next((e for e in events if e.name=='TARGET_LANE_CONFIRMED'),None)
    assert target is not None and target.frame==120


def test_lane_change_onset_is_observed_displacement_not_late_target_arrival(require,i_change_trace):
    c=i_change_trace();events=require('m56.metrics','detect_events')(c.frames,c.fixture)
    onset=next((e for e in events if e.name=='LANE_CHANGE_ONSET'),None)
    assert onset is not None and onset.frame==109 and onset.time==F(9,20)
    assert next(e.frame for e in events if e.name=='TARGET_LANE_CONFIRMED')==116


def test_npc_target_lane_hold_is_distinct_from_ego_target_confirmation(require,i_change_trace,rebind_trace):
    c=i_change_trace();regions=c.fixture.domain.topology['action_regions']
    fixture=replace(c.fixture,domain=replace(c.fixture.domain,topology={**c.fixture.domain.topology,
        'npc_regions':{'NPC_INITIAL':regions['EGO_TARGET'],'NPC_TARGET':regions['EGO_INITIAL']}}))
    frames=rebind_trace(c.frames,fixture)
    events=require('m56.metrics','detect_events')(frames,fixture)
    event=next((e for e in events if e.name=='NPC_TARGET_LANE_CONFIRMED'),None)
    assert event is not None and event.frame==107 and event.time==F(7,20)
    assert next(e.frame for e in events if e.name=='TARGET_LANE_CONFIRMED')==116


def test_i_bound_change_path_does_not_claim_full_action_success(require,i_change_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=i_change_trace();state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='UNKNOWN'
    assert reasons==('IO_FULL_ACTION_REVIEW_PENDING',)


@pytest.fixture
def o_return_trace(io_action_trace,rebind_trace,frame_capability):
    from types import SimpleNamespace
    from m56.catalog import _digest
    def build(early=False,no_path=False,unsafe_marker=False,outbound_fault=None,return_fault=None):
        c=io_action_trace('O','A')
        def box(y0,y1):
            return tuple((x,y,z) for x in (0.,30.) for y in (y0,y1) for z in (-1.,1.))
        route=replace(c.fixture.routes['EGO'],transforms=tuple(replace(p,y=1.5) for p in c.fixture.routes['EGO'].transforms))
        reference={'method':'segment-map-normal-v1','route':route,'normals':((0.,1.,0.),),'refs':route.continuity}
        def section(x):
            return replace(c.fixture.sections['X'],route_station=F(x),vertices=tuple((float(x),y,z) for y in (-4.,4.) for z in (-1.,1.)))
        fixture=replace(c.fixture,routes={**c.fixture.routes,'EGO':route},pair=replace(c.fixture.pair,reference='map:'+_digest(reference)),
            responses=tuple(replace(r,route=route) for r in c.fixture.responses),
            sections={'O_DECISION':section(2),'O_RETURN_START':section(14),'X':section(18)},
            domain=replace(c.fixture.domain,topology={'category':'O',
                'action_regions':{'EGO_INITIAL':box(0.,3.5),'EGO_TARGET':box(-3.5,0.)}}))
        frames=[];start=14 if early else 17
        for i in range(29):
            f=c.frames[0];e,n=f.actors;number=100+i;time=F(i,20);x=1.+.8*i
            y=(1.5,1.5,.5,-.5)[i] if i<4 else -1.75
            if i>=start:
                y=(-1.5,-1.,-.5,.5,1.5)[min(i-start,4)]
            if outbound_fault=='early' and i==1:
                y=1.25
            e=replace(e,pose=replace(e.pose,x=x,y=y),arc=F(x),velocity=(16.,0.,0.),
                      commands=tuple(replace(cmd,frame=number-1,next_frame=number) for cmd in e.commands))
            nx=12.5 if unsafe_marker else 5.
            n=replace(n,pose=replace(n.pose,x=nx,y=1.5),arc=F(nx),velocity=(0.,0.,0.))
            ref=replace(f.integrity['frame_refs'][0],frame=number,time=time)
            frames.append(replace(f,frame=number,simtime=time,actors=(e,n),integrity={'frame_refs':(ref,),
                    'metric_context':{'reference':fixture.pair.reference,'pair_hash':fixture.pair.hash,'map_reference':reference}}))
        frames=rebind_trace(tuple(frames),fixture)
        if not no_path:
            frames=tuple(frame_capability(f,fixture,'return_path','RETURN_PATH','bounded-return-corridor-v1',
                           {'minimum_clearance_m':F(1)}) for f in frames)
        if return_fault is not None:
            recorded=[]
            for f in frames:
                if f.frame==119 and return_fault=='dropped':
                    f=replace(f,integrity={k:v for k,v in f.integrity.items() if k!='return_path'})
                elif f.frame==119 and return_fault=='stale':
                    proof=f.integrity['return_path']
                    f=replace(f,integrity={**f.integrity,'return_path':replace(proof,limits={**proof.limits,'actors_hash':'0'*64})})
                recorded.append(f)
            frames=tuple(recorded)
        if outbound_fault!='missing':
            regions=fixture.domain.topology['action_regions'];recorded=[]
            for f in frames:
                limits={'from_region_hash':_digest(regions['EGO_INITIAL']),'to_region_hash':_digest(regions['EGO_TARGET']),
                        'route_hash':_digest(fixture.routes['EGO']),'minimum_clearance_m':F(1)}
                if outbound_fault=='wrong_region' and f.frame==103:
                    limits['from_region_hash']='0'*64
                recorded.append(frame_capability(f,fixture,'lane_change_path','LANE_CHANGE_PATH',
                                                'bounded-lane-change-corridor-v1',limits))
            frames=tuple(recorded)
        return SimpleNamespace(frames=frames,fixture=fixture)
    return build


@pytest.mark.parametrize('fault',['missing','wrong_region'])
def test_o_safe_return_cannot_replace_outbound_path_witness(require,o_return_trace,fault):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=o_return_trace(outbound_fault=fault);events=detect(c.frames,c.fixture)
    assert {'RETURN_MARKER','RETURN_CLEAR_CONFIRMED','X_END'}.issubset({e.name for e in events})
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='UNKNOWN'
    assert 'OUTBOUND_PATH_UNPROVEN' in reasons


def test_o_cannot_depart_on_frame_before_decision_has_been_observed(require,o_return_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=o_return_trace(outbound_fault='early');events=detect(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='TRIGGER')==101
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='FAILED'
    assert 'OUTBOUND_BEFORE_DECISION' in reasons


@pytest.mark.parametrize('fault',['dropped','stale'])
def test_o_return_path_must_cover_actual_return_after_fixed_marker(require,o_return_trace,fault):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=o_return_trace(return_fault=fault);events=detect(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='RETURN_MARKER')==116
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='UNKNOWN'
    assert 'RETURN_PATH_UNPROVEN' in reasons


def test_known_early_return_not_erased_by_missing_outbound_proof(require,o_return_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=o_return_trace(early=True,outbound_fault='missing')
    state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='FAILED'
    assert {'RETURN_STARTED_BEFORE_FIXED_MARKER','OUTBOUND_PATH_UNPROVEN'}.issubset(reasons)


def test_o_return_marker_is_actual_frozen_front_crossing(require,o_return_trace):
    detect=require('m56.metrics','detect_events');c=o_return_trace()
    events={e.name:e for e in detect(c.frames,c.fixture)}
    assert events['RETURN_MARKER'].frame==116
    assert events['X_END'].frame==122


def test_o_actual_return_cannot_start_early_while_body_still_in_target_lane(require,o_return_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=o_return_trace(early=True);events=detect(c.frames,c.fixture)
    assert 'X_END' in {e.name for e in events}
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='FAILED'
    assert 'RETURN_STARTED_BEFORE_FIXED_MARKER' in reasons
    assert 'MANEUVER_NOT_COMPLETE_BY_X' not in reasons


def test_o_return_marker_cannot_be_moved_to_later_safe_gap(require,o_return_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=o_return_trace(unsafe_marker=True);state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='FAILED'
    assert 'RETURN_MARKER_CLEARANCE_NOT_MET' in reasons


def test_o_safe_gap_is_not_independent_return_path_proof(require,o_return_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=o_return_trace(no_path=True);state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='UNKNOWN'
    assert 'RETURN_PATH_UNPROVEN' in reasons


def test_o_recorded_safe_return_does_not_become_episode_pass(require,o_return_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_io_action')
    c=o_return_trace();events=detect(c.frames,c.fixture)
    assert {'RETURN_MARKER','RETURN_CLEAR_CONFIRMED','X_END'}.issubset({e.name for e in events})
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='UNKNOWN'
    assert reasons==('IO_FULL_ACTION_REVIEW_PENDING',)


def test_i_intrusion_not_lane_id(require,io_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=io_trace
    events={e.name:e for e in detect(c.frames,c.fixture)}
    assert events['TRIGGER'].frame==101  # body intrudes while NPC origin is still y<0
    assert events['X_END'].frame==103  # front crosses earlier, rear does not
    fixed=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],pose=replace(f.actors[1].pose,y=-.5)))) for f in c.frames)
    assert 'TRIGGER' not in {e.name for e in detect(rebind_trace(fixed,c.fixture),c.fixture)}


def test_o_trigger_shared_with_follow(require,io_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=io_trace
    fixture=replace(c.fixture,sections={'O_DECISION':c.decision,'X':c.fixture.sections['X']},
                    domain=replace(c.fixture.domain,topology={'category':'O'}))
    # No lateral motion or passing needed; the same frozen marker applies to A/B.
    frames=tuple(replace(f,actors=(replace(f.actors[0],velocity=(2.5,0.,0.)),f.actors[1])) for f in c.frames)
    events={e.name:e for e in detect(rebind_trace(frames,fixture),fixture)}
    assert events['TRIGGER'].frame==101
    assert events['X_END'].frame==103
    assert 'E_ENTRY' not in events and 'CLEAR_N_CONFIRMED' not in events


@pytest.mark.parametrize('change',['no_previous_witness','outside_finite_boundary','wrong_height','stale_bound'])
def test_io_crossing_requires_finite_correlated_bracket(require,io_trace,rebind_trace,change):
    detect=require('m56.metrics','detect_events');c=io_trace
    frames=c.frames
    if change=='no_previous_witness':
        frames=(replace(frames[0],integrity={}),)+frames[1:]
    elif change in ('outside_finite_boundary','wrong_height'):
        coordinate={'x':40.} if change=='outside_finite_boundary' else {'z':5.}
        frames=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],pose=replace(f.actors[1].pose,**coordinate)))) for f in frames)
        frames=rebind_trace(frames,c.fixture)
    else:
        frames=tuple(replace(f,integrity={k:v for k,v in f.integrity.items() if k!='continuous_geometry'}) for f in frames)
    assert 'TRIGGER' not in {e.name for e in detect(frames,c.fixture)}


@pytest.fixture
def io_metric_trace(io_trace):
    from types import SimpleNamespace
    from m56.catalog import _digest
    from m56.model import EventRecord
    c=io_trace
    reference={'method':'segment-map-normal-v1','route':c.fixture.routes['EGO'],
               'normals':((0.,1.,0.),),'refs':c.fixture.routes['EGO'].continuity}
    pair=replace(c.fixture.pair,reference='map:'+_digest(reference))
    frames=[]
    for i,f in enumerate(c.frames[1:]):
        ego=replace(f.actors[0],pose=replace(f.actors[0].pose,y=(.25,.5,1.)[i]),
                    velocity=((3.,5.,7.)[i],0.,0.))
        context={'reference':pair.reference,'pair_hash':pair.hash,'map_reference':reference,
                 'uncertainty':{'v_mean_E':F(1,100),'e_lat_peak':F(1,100)}}
        frames.append(replace(f,actors=(ego,f.actors[1]),integrity={**f.integrity,'metric_context':context}))
    events=tuple(EventRecord(name,f.frame,f.simtime,f.integrity['frame_refs'])
                 for name,f in (('TRIGGER',frames[0]),('X_END',frames[-1])))
    return SimpleNamespace(frames=tuple(frames),pair=pair,events=events,reference=reference)


def test_map_reference_not_spawn_bias(require,io_metric_trace):
    measure=require('m56.metrics','measure');c=io_metric_trace
    out=measure(c.frames,c.pair,c.events)
    assert [(v.value,v.status) for v in out]==[(F(5),'VALID'),(F(1),'VALID')]
    assert all(v.frames==(101,102,103) for v in out)
    assert out[1].value!=F(3,4)  # never subtract the initial .25m offset


def test_map_reference_cannot_reset_to_target_lane(require,io_metric_trace):
    measure=require('m56.metrics','measure');c=io_metric_trace
    route=c.reference['route']
    changed={**c.reference,'route':replace(route,transforms=tuple(replace(p,y=1.) for p in route.transforms))}
    frames=tuple(replace(f,integrity={**f.integrity,'metric_context':{
        **f.integrity['metric_context'],'map_reference':changed}}) for f in c.frames)
    assert measure(frames,c.pair,c.events)[1].status=='UNKNOWN'


def test_mean_speed_uses_magnitude_not_longitudinal_component(require,io_metric_trace):
    measure=require('m56.metrics','measure');c=io_metric_trace
    frames=tuple(replace(f,actors=(replace(f.actors[0],velocity=(3.,4.,0.)),f.actors[1])) for f in c.frames)
    assert measure(frames,c.pair,c.events)[0].value==5


@pytest.mark.parametrize('fault',['zero_duration','nan_velocity','ambiguous_map'])
def test_metric_missing_or_ambiguous_geometry_is_unknown(require,io_metric_trace,fault):
    measure=require('m56.metrics','measure');c=io_metric_trace
    frames=c.frames;events=c.events;pair=c.pair
    if fault=='zero_duration':
        events=(events[0],replace(events[1],frame=events[0].frame,time=events[0].time))
        assert measure(frames,pair,events)[0].status=='UNKNOWN'
    elif fault=='nan_velocity':
        frames=(replace(frames[0],actors=(replace(frames[0].actors[0],velocity=(float('nan'),0.,0.)),frames[0].actors[1])),)+frames[1:]
        assert measure(frames,pair,events)[0].status=='UNKNOWN'
    else:
        from m56.catalog import _digest
        route=c.reference['route'];a,b=route.transforms
        route=replace(route,transforms=(a,b,a),arc=(F(0),F(30),F(60)))
        reference={**c.reference,'route':route,'normals':((0.,1.,0.),(0.,-1.,0.))}
        pair=replace(pair,reference='map:'+_digest(reference))
        frames=tuple(replace(f,integrity={**f.integrity,'metric_context':{
            **f.integrity['metric_context'],'reference':pair.reference,'map_reference':reference}}) for f in frames)
        assert measure(frames,pair,events)[1].status=='UNKNOWN'


def test_forward_distance_rejects_forged_actor_arc(require,crossing_trace):
    detect=require('m56.metrics','detect_events');measure=require('m56.metrics','measure');c=crossing_trace
    frames=tuple(replace(f,actors=(replace(f.actors[0],arc=F(i*100)),f.actors[1])) for i,f in enumerate(c.frames))
    out=measure(frames,c.fixture.pair,detect(c.frames,c.fixture))
    assert out[0].value is None and out[0].status=='UNKNOWN'


@pytest.fixture
def reverse_metric_trace(crossing_trace):
    from types import SimpleNamespace
    from m56.model import EventRecord
    c=crossing_trace
    pair=replace(c.fixture.pair,names=('d_reverse','g_front_min'),units=('m','m'),
                 estimators=('reverse_distance','min_front_gap'),window=(('START','END'),)*2)
    frames=[]
    for i,f in enumerate(c.frames[:3]):
        e,n=f.actors
        e=replace(e,pose=replace(e.pose,x=(5.,4.,4.5)[i]),arc=F((5.,4.,4.5)[i]))
        n=replace(n,pose=replace(n.pose,x=8.),arc=F(8))
        frames.append(replace(f,actors=(e,n),integrity={**f.integrity,'metric_context':{
            **f.integrity['metric_context'],'uncertainty':{'d_reverse':F(1,100),'g_front_min':F(1,100)}}}))
    events=tuple(EventRecord(name,f.frame,f.simtime,f.integrity['frame_refs'])
                 for name,f in (('START',frames[0]),('END',frames[-1])))
    return SimpleNamespace(frames=tuple(frames),pair=pair,events=events)


def test_reverse_sum_does_not_net_out_forward_motion(require,reverse_metric_trace):
    measure=require('m56.metrics','measure');c=reverse_metric_trace
    out=measure(c.frames,c.pair,c.events)
    assert [(m.value,m.status) for m in out]==[(F(1),'VALID'),(F(2),'VALID')]
    # Measurement records reverse travel; action oscillation is separately a physical verdict.


def test_signed_bumper_overlap_is_failure_not_absolute_gap(require,reverse_metric_trace):
    measure=require('m56.metrics','measure');c=reverse_metric_trace
    frames=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],pose=replace(f.actors[1].pose,x=5.5),arc=F(11,2)))) for f in c.frames)
    out=measure(frames,c.pair,c.events)
    assert out[1].value==F(-1,2) and out[1].status=='FAILED'


def test_rear_gap_projects_both_bodies_on_one_directed_reference(require,reverse_metric_trace):
    measure=require('m56.metrics','measure');c=reverse_metric_trace
    pair=replace(c.pair,names=('d_reverse','g_rear_min'),estimators=('reverse_distance','min_rear_gap'))
    frames=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],pose=replace(f.actors[1].pose,x=1.),arc=F(1))),
                 integrity={**f.integrity,'metric_context':{**f.integrity['metric_context'],
                 'uncertainty':{'d_reverse':F(1,100),'g_rear_min':F(1,100)}}}) for f in c.frames)
    assert measure(frames,pair,c.events)[1].value==2


def test_hold_duration_cannot_be_shortened_by_caller(require,clear_frames):
    confirm=require('m56.metrics','confirm_hold')
    with pytest.raises(ValueError,match='HOLD_DURATION_POLICY'):
        confirm(clear_frames,'NPC_WHOLE_BODY_CLEAR',F(1,10))


def test_stop_requires_half_second_and_front_margin(require,crossing_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=crossing_trace
    def trace(x,velocity):
        result=[]
        for i in range(11):
            f=c.frames[0];raw=replace(f.integrity['frame_refs'][0],frame=100+i,time=F(i,20))
            e=replace(f.actors[0],pose=replace(f.actors[0].pose,x=x),arc=F(x),velocity=velocity)
            result.append(replace(f,frame=100+i,simtime=F(i,20),actors=(e,f.actors[1]),integrity={'frame_refs':(raw,)}))
        return rebind_trace(tuple(result),c.fixture)
    events={e.name:e for e in detect(trace(8.,(0.,0.,0.)),c.fixture)}
    assert events['STOP_CONFIRMED'].frame==110
    assert events['STOP_CONFIRMED'].time==F(1,2)
    assert 'STOP_CONFIRMED' not in {e.name for e in detect(trace(9.25,(0.,0.,0.)),c.fixture)}
    assert 'STOP_CONFIRMED' not in {e.name for e in detect(trace(8.,(0.,.11,0.)),c.fixture)}


def test_destination_is_wholebody_hold_not_plan_queue(require,crossing_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=crossing_trace
    destination=replace(c.fixture.domain.e_exit,route_station=F(20),
        vertices=tuple((20.,y,z) for _,y,z in c.fixture.domain.e_exit.vertices))
    fixture=replace(c.fixture,sections={'DESTINATION':destination})
    def trace(x):
        return rebind_trace(tuple(replace(f,actors=(replace(f.actors[0],pose=replace(f.actors[0].pose,x=x),arc=F(x),plan_queue=0),f.actors[1]))
                                  for f in c.frames[:6]),fixture)
    assert 'DESTINATION_CONFIRMED' not in {e.name for e in detect(trace(20.25),fixture)}
    events={e.name:e for e in detect(trace(21.),fixture)}
    assert events['DESTINATION_CONFIRMED'].frame==105
    assert 'DESTINATION_CONFIRMED' not in {e.name for e in detect(trace(21.)[:-1],fixture)}


def test_source_clear_requires_wholebody_half_meter_hold(require,io_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=io_trace
    from itertools import product
    fixture=replace(c.fixture,domain=replace(c.fixture.domain,topology={
        'category':'I','source_region':tuple(product((0.,30.),(-3.,0.),(-1.,1.)))}))
    def trace(y):
        frames=[]
        for i in range(8):
            f=c.frames[min(i,3)];raw=replace(f.integrity['frame_refs'][0],frame=100+i,time=F(i,20))
            n=replace(f.actors[1],pose=replace(f.actors[1].pose,y=(-.5,-.125)[i] if i<2 else y))
            frames.append(replace(f,frame=100+i,simtime=F(i,20),actors=(f.actors[0],n),integrity={'frame_refs':(raw,)}))
        return rebind_trace(tuple(frames),fixture)
    events={e.name:e for e in detect(trace(1.),fixture)}
    assert events['SOURCE_CLEAR_CONFIRMED'].frame==107
    assert 'SOURCE_CLEAR_CONFIRMED' not in {e.name for e in detect(trace(.5),fixture)}


def test_return_clear_needs_body_gap_hold_and_separate_path_proof(require,io_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=io_trace
    from m56.model import CapabilityProof,ReviewRecord
    from m56.catalog import _digest
    fixture=replace(c.fixture,sections={'O_DECISION':c.decision,'X':c.fixture.sections['X']},
                    domain=replace(c.fixture.domain,topology={'category':'O'}))
    frames=[]
    for i in range(8):
        f=c.frames[min(i,3)];raw=replace(f.integrity['frame_refs'][0],frame=100+i,time=F(i,20))
        e=replace(f.actors[0],pose=replace(f.actors[0].pose,x=(1.,2.)[i] if i<2 else 7.),arc=F((1,2)[i] if i<2 else 7))
        n=replace(f.actors[1],pose=replace(f.actors[1].pose,y=0.))
        frames.append(replace(f,frame=100+i,simtime=F(i,20),actors=(e,n),integrity={'frame_refs':(raw,)}))
    frames=rebind_trace(tuple(frames),fixture)
    assert 'RETURN_CLEAR_CONFIRMED' not in {e.name for e in detect(frames,fixture)}
    witnessed=[]
    for f in frames:
        refs=f.integrity['frame_refs']
        packet={'kind':'RETURN_PATH','method':'bounded-return-corridor-v1','raw_refs':refs,
                'uncertainty':F(1,1000),'limits':{'fixture_hash':_digest(fixture),
                'actors_hash':_digest(f.actors),'frame':f.frame,'minimum_clearance_m':F(1)},'status':'CORROBORATED'}
        review=ReviewRecord(_digest(packet),'CAPABILITY:RETURN_PATH',refs,'SYNTHETIC_TEST','2026-10-08',
                            'APPROVED',('analytic free corridor',),refs[0])
        proof=CapabilityProof(**packet,review=review)
        witnessed.append(replace(f,integrity={**f.integrity,'return_path':proof}))
    events={e.name:e for e in detect(tuple(witnessed),fixture)}
    assert events['RETURN_CLEAR_CONFIRMED'].frame==107
    assert 'RETURN_CLEAR_CONFIRMED' not in {e.name for e in detect(tuple(witnessed[:-1]),fixture)}


def test_missing_actor_witness_is_unknown_not_incomplete(require,crossing_trace):
    detect=require('m56.metrics','detect_events');measure=require('m56.metrics','measure');c=crossing_trace
    frames=(replace(c.frames[0],integrity={}),)+c.frames[1:]
    events=detect(frames,c.fixture)
    assert 'WITNESS_UNKNOWN' in {e.name for e in events}
    assert all(v.status=='UNKNOWN' for v in measure(frames,c.fixture.pair,events))


def test_oblique_finite_section_projects_onto_its_plane(require):
    corridor=require('m56.metrics','_section_corridor')
    from m56.model import Section
    section=Section(((-1.,1.,-1.),(-1.,1.,1.),(1.,-1.,-1.),(1.,-1.,1.)),
                    (1.,1.,0.),F(0),{})
    assert corridor(((10.,10.,0.),),section) is True  # longitudinal advance, zero lateral offset
    assert corridor(((10.,0.,0.),),section) is False  # projection (5,-5) outside finite section


def test_missing_continuous_witness_is_unknown_not_never_clear(require,crossing_trace):
    detect=require('m56.metrics','detect_events');measure=require('m56.metrics','measure');c=crossing_trace
    frames=tuple(replace(f,integrity={k:v for k,v in f.integrity.items() if k!='continuous_geometry'}) for f in c.frames)
    events=detect(frames,c.fixture)
    assert 'WITNESS_UNKNOWN' in {e.name for e in events}
    assert all(m.status=='UNKNOWN' for m in measure(frames,c.fixture.pair,events))


def test_actor_identity_change_never_brackets_crossing(require,crossing_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=crossing_trace
    frames=tuple(replace(f,actors=(replace(f.actors[0],id=99) if f.frame>=102 else f.actors[0],f.actors[1])) for f in c.frames)
    events=detect(rebind_trace(frames,c.fixture),c.fixture)
    assert 'WITNESS_UNKNOWN' in {e.name for e in events}
    assert 'TRIGGER' not in {e.name for e in events}


def test_event_reference_must_correlate_with_its_timestamp(require,crossing_trace):
    detect=require('m56.metrics','detect_events');measure=require('m56.metrics','measure');c=crossing_trace
    events=detect(c.frames,c.fixture)
    stale=tuple(replace(e,witness_refs=(replace(e.witness_refs[0],frame=0,time=F(0)),)) if e.name=='TRIGGER' else e for e in events)
    assert all(m.status=='UNKNOWN' for m in measure(c.frames,c.fixture.pair,stale))


def test_missing_source_before_absent_endpoint_is_unknown(require,crossing_trace):
    measure=require('m56.metrics','measure');c=crossing_trace
    frames=tuple(replace(f,integrity={}) for f in c.frames)
    assert all(m.status=='UNKNOWN' for m in measure(frames,c.fixture.pair,()))


def test_forward_metric_does_not_clamp_beyond_frozen_route(require,reverse_metric_trace):
    measure=require('m56.metrics','measure');c=reverse_metric_trace
    frames=tuple(replace(f,actors=(replace(f.actors[0],pose=replace(f.actors[0].pose,x=40.),arc=F(30)),f.actors[1])) for f in c.frames)
    assert measure(frames,c.pair,c.events)[0].status=='UNKNOWN'


def test_geometry_blocks_clear_even_with_valid_lane_flag_and_rebound_receipt(require,crossing_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=crossing_trace
    for change in ('lateral','rear'):
        frames=[]
        for f in c.frames:
            n=f.actors[1]
            if f.frame>=103:
                if change=='lateral':
                    n=replace(n,pose=replace(n.pose,y=4.))
                else:
                    n=replace(n,body=replace(n.body,bbox_offset=(-2.,0.,0.)))
            frames.append(replace(f,actors=(f.actors[0],n)))
        events=detect(rebind_trace(tuple(frames),c.fixture),c.fixture)
        assert 'CLEAR_N_CONFIRMED' not in {e.name for e in events}


@pytest.fixture
def f_policies(reverse_metric_trace):
    from m56.model import PolicyBundle,ReviewRecord
    from m56.catalog import _digest
    from types import SimpleNamespace
    c=reverse_metric_trace;ref=c.frames[0].integrity['frame_refs'][0]
    policies=PolicyBundle('synthetic-f-contracts','f'*64,{}, {},{},(ref,))
    definitions={
        'F01':(('a_peak_025','g_front_min_m'),('m/s^2','m'),('peak_decel_025','min_front_gap'),(('TRIGGER','F01_N_CLEAR'),)*2),
        'F02':(('v_mean_E','g_rear_min_m'),('m/s','m'),('mean_speed','min_rear_gap'),(('TRIGGER','F02_END'),)*2),
        'F03':(('d_reverse_m','g_front_min_m'),('m','m'),('reverse_distance','min_front_gap'),(('TRIGGER','NPC_STOP_CONFIRMED'),)*2),
        'F04':(('passage_time_s','e_lat_peak_m'),('s','m'),('elapsed','map_lateral_peak'),(('TRIGGER','F04_END'),)*2),
        'F05':(('d_pre_move_m','t_queue_exit_s'),('m','s'),('forward_distance','elapsed'),(('TRIGGER','N_MOVE'),('N_MOVE','F05_END'))),
        'F06-ALT1':(('d_reserve_reverse_m','g_front_min_m'),('m','m'),('reverse_distance','min_front_gap'),(('TRIGGER','NPC_REVERSE_TARGET_STOP_CONFIRMED'),)*2),
    }
    def approve(mechanism,reference=c.pair.reference):
        names,units,estimators,window=definitions[mechanism]
        binding={'mechanism':mechanism,'names':names,'units':units,'estimators':estimators,'window':window,
                 'reference':reference,'policy_hash':policies.hash,'receipt_refs':policies.receipt_refs}
        digest=_digest(binding)
        review=ReviewRecord(digest,'F_PAIR:'+mechanism,(ref,),'SYNTHETIC_TEST','2026-10-08','APPROVED',
                            ('frozen proposal only; not a mechanism finding',),ref)
        return replace(policies,descriptor_specs={mechanism:{'reference':reference,'review':review}})
    return SimpleNamespace(approve=approve,definitions=definitions,policies=policies)


def test_f06_alt1_uses_common_stop_window(require,f_policies,reverse_metric_trace):
    pairfn=require('m56.metrics','f_pair');measure=require('m56.metrics','measure');c=reverse_metric_trace
    p=pairfn('F06-ALT1',f_policies.approve('F06-ALT1'))
    assert p.names==('d_reserve_reverse_m','g_front_min_m')
    assert p.window==(('TRIGGER','NPC_REVERSE_TARGET_STOP_CONFIRMED'),)*2
    frames=tuple(replace(f,integrity={**f.integrity,'metric_context':{**f.integrity['metric_context'],
        'pair_hash':p.hash,'uncertainty':{'d_reserve_reverse_m':F(1,100),'g_front_min_m':F(1,100)}}}) for f in c.frames)
    events=(replace(c.events[0],name='TRIGGER'),replace(c.events[1],name='NPC_REVERSE_TARGET_STOP_CONFIRMED'))
    values=measure(frames,p,events)
    assert tuple(v.value for v in values)==(F(1),F(2))
    assert all(v.status=='VALID' for v in values)
    # These supplied events test estimator windows, NOT cue/target-stop detection (separate tests).


def test_old_f06_timepair_not_qualifier(require,f_policies):
    pairfn=require('m56.metrics','f_pair')
    from m56.model import BlockedFixture
    for name in ('F06','F06-R1','parking-completion-time'):
        assert isinstance(pairfn(name,f_policies.approve('F06-ALT1')),BlockedFixture)
    assert isinstance(pairfn('F06-ALT1',f_policies.policies),BlockedFixture)


def test_same_metrics_not_mechanism_certificate(require,f_policies):
    pairfn=require('m56.metrics','f_pair')
    for name,definition in f_policies.definitions.items():
        pair=pairfn(name,f_policies.approve(name))
        assert (pair.names,pair.units,pair.estimators,pair.window)==definition
        assert pair.approval_level=='APPROVED_PROPOSAL_NOT_READY'
    assert pairfn('F03',f_policies.approve('F03')).estimators==pairfn('F06-ALT1',f_policies.approve('F06-ALT1')).estimators


@pytest.fixture
def f01_trace(crossing_trace,f_policies,rebind_trace,require):
    from m56.model import FrozenResponse,CommandRecord,ControlPacket
    from types import SimpleNamespace
    c=crossing_trace;p=require('m56.metrics','f_pair')('F01',f_policies.approve('F01',c.fixture.pair.reference))
    response=FrozenResponse('NPC','NPC_COMMON',c.fixture.routes['NPC'],{}, {},{'brake':'F01_BRAKE'},'a'*64)
    fixture=replace(c.fixture,pair=p,G=None,responses=(response,),
                    domain=replace(c.fixture.domain,topology={'category':'F','mechanism':'F01'}))
    frames=[]
    for i,f in enumerate(c.frames[:6]):
        e,n=f.actors
        control=ControlPacket(0.,0.,.5,False,False,False,1)
        command=CommandRecord(n.id,f.frame-1,f.frame,'CONTROL',F(0),F(0),control,None,'F01_BRAKE',response.hash)
        n=replace(n,pose=replace(n.pose,x=8.),arc=F(8),velocity=(4.-i*.25,0.,0.),commands=(command,),readback=control)
        e=replace(e,pose=replace(e.pose,x=4.),arc=F(4),velocity=(5.-i*.5,0.,0.))
        frames.append(replace(f,actors=(e,n),integrity={**f.integrity,'metric_context':{
            **f.integrity['metric_context'],'pair_hash':p.hash,'uncertainty':{'a_peak_025':F(1,100),'g_front_min_m':F(1,100)}}}))
    return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)


def test_f01_requires_actual_decel(require,f01_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=f01_trace
    events={e.name:e for e in detect(c.frames,c.fixture)}
    assert events['TRIGGER'].frame==105  # actual5m/s² over complete .25s, never brake-command timestamp
    steady=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],velocity=(4.,0.,0.)))) for f in c.frames)
    assert 'TRIGGER' not in {e.name for e in detect(rebind_trace(steady,c.fixture),c.fixture)}
    unplanned=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],commands=()))) for f in c.frames)
    assert 'TRIGGER' not in {e.name for e in detect(rebind_trace(unplanned,c.fixture),c.fixture)}
    assert 'TRIGGER' not in {e.name for e in detect(c.frames[:-1],c.fixture)}


def test_f01_peak_decel_uses_complete_quarter_second_windows(require,f01_trace):
    measure=require('m56.metrics','measure');c=f01_trace
    from m56.model import EventRecord
    events=tuple(EventRecord(name,f.frame,f.simtime,f.integrity['frame_refs'])
                 for name,f in (('TRIGGER',c.frames[0]),('F01_N_CLEAR',c.frames[-1])))
    out=measure(c.frames,c.fixture.pair,events)
    assert tuple(v.value for v in out)==(F(10),F(3))
    assert all(v.status=='VALID' for v in out)
    short=replace(events[1],frame=c.frames[-2].frame,time=c.frames[-2].simtime,witness_refs=c.frames[-2].integrity['frame_refs'])
    assert measure(c.frames[:-1],c.fixture.pair,(events[0],short))[0].status=='UNKNOWN'


@pytest.fixture
def f06_trace(crossing_trace,f_policies,rebind_trace,require):
    from m56.model import ControlPacket,CapabilityProof,ReviewRecord
    from m56.catalog import _digest
    from types import SimpleNamespace
    c=crossing_trace
    pair=require('m56.metrics','f_pair')('F06-ALT1',f_policies.approve('F06-ALT1',c.fixture.pair.reference))
    fixture=replace(c.fixture,pair=pair,G=None,domain=replace(c.fixture.domain,topology={
                    'category':'F','mechanism':'F06-ALT1'}))
    forward=ControlPacket(0.,0.,.3,False,False,False,1)
    reverse=ControlPacket(0.,0.,.3,False,True,True,-1)
    frames=[]
    # Cue111; fixed release issue171 is received172, then real STOP252..262.
    for number in range(100,263):
        f=c.frames[0];raw=replace(f.integrity['frame_refs'][0],frame=number,time=F(number-100,20))
        e,n=f.actors
        ex=F(4)-min(F(1),max(F(0),F(number-111,40)))
        nx=F(8)-min(F(2),max(F(0),F(number-171,40)))
        e=replace(e,pose=replace(e.pose,x=float(ex)),arc=F(float(ex)),velocity=(-.5 if 112<=number<=151 else 0.,0.,0.),
                  readback=reverse if number>=111 else forward)
        n=replace(n,pose=replace(n.pose,x=float(nx)),arc=F(float(nx)),velocity=(-.5 if 172<=number<=251 else 0.,0.,0.),
                  readback=reverse if number>=111 else forward)
        frames.append(replace(f,frame=number,simtime=F(number-100,20),actors=(e,n),events=(),integrity={
            'frame_refs':(raw,),'metric_context':{'reference':pair.reference,'pair_hash':pair.hash,
             'directed_route':fixture.routes['EGO'],'uncertainty':{'d_reserve_reverse_m':F(1,100),'g_front_min_m':F(1,100)}}}))
    frames=list(rebind_trace(tuple(frames),fixture))
    cue=frames[11];previous=frames[10];refs=cue.integrity['frame_refs']
    packet={'kind':'REVERSE_PREPARATION','method':'frame-correlated-cue-v1','raw_refs':refs,
        'uncertainty':F(1,1000),'limits':{'fixture_hash':_digest(fixture),'frame':cue.frame,
         'previous_frame':previous.frame,'actors_hash':_digest(cue.actors),'previous_actors_hash':_digest(previous.actors)},
        'status':'CORROBORATED'}
    review=ReviewRecord(_digest(packet),'CAPABILITY:REVERSE_PREPARATION',refs,'SYNTHETIC_TEST','2026-10-08',
                        'APPROVED',('synthetic externally observed preparation cue',),refs[0])
    frames[11]=replace(cue,integrity={**cue.integrity,'preparation_cue':CapabilityProof(**packet,review=review)})
    return SimpleNamespace(frames=tuple(frames),fixture=fixture)


@pytest.fixture
def f06_action_trace(f06_trace,rebind_trace,frame_capability):
    from m56.model import FrozenResponse,CommandRecord
    from m56.catalog import _digest
    from types import SimpleNamespace
    c=f06_trace
    def build(kind='normal'):
        action='A' if kind=='hold_moved' else 'B'
        response=FrozenResponse('EGO',action,c.fixture.routes['EGO'],{}, {},{},'a'*64)
        fixture=replace(c.fixture,responses=(response,))
        frames=[]
        for f in c.frames:
            e,n=f.actors
            if kind=='overshoot' and f.frame>111:
                x=F(4)-min(F(3,2),F(f.frame-111,40))
                e=replace(e,pose=replace(e.pose,x=float(x)),arc=F(float(x)),velocity=(-.5 if f.frame<=171 else 0.,0.,0.))
            if kind=='rescue' and f.frame>=200:
                e=replace(e,pose=replace(e.pose,x=3.25),arc=F(13,4),velocity=(5. if f.frame==200 else 0.,0.,0.))
            if kind=='no_reservation_stop':
                x=F(4)-max(F(0),F(f.frame-221,40))
                e=replace(e,pose=replace(e.pose,x=float(x)),arc=F(float(x)),velocity=(-.5 if f.frame>221 else 0.,0.,0.))
            command=CommandRecord(e.id,f.frame-1,f.frame,'CONTROL',F(9,5),F(0),e.readback,None,'SYNTHETIC',response.hash)
            frames.append(replace(f,actors=(replace(e,commands=(command,)),n)))
        frames=list(rebind_trace(tuple(frames),fixture));cue=frames[11];previous=frames[10]
        frames[11]=frame_capability(cue,fixture,'preparation_cue','REVERSE_PREPARATION','frame-correlated-cue-v1',
            {'previous_frame':previous.frame,'previous_actors_hash':_digest(previous.actors)})
        return SimpleNamespace(frames=tuple(frames),fixture=fixture)
    return build


def test_f06_metric_endpoint_does_not_finish_forward_destination(require,f06_action_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f06_action_trace();events=detect(c.frames,c.fixture)
    assert 'NPC_REVERSE_TARGET_STOP_CONFIRMED' in {e.name for e in events}
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='INCOMPLETE'
    assert 'DESTINATION_CONFIRMED_MISSING' in reasons


@pytest.mark.parametrize('kind,reason',[('overshoot','REVERSE_RESERVATION_EXCEEDED'),('rescue','FORWARD_RESCUE_BEFORE_RELEASE'),
                                       ('hold_moved','HOLD_ACTION_MOVED')])
def test_f06_action_limits_are_independent_of_metric_pair(require,f06_action_trace,kind,reason):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f06_action_trace(kind);state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='FAILED'
    assert reason in reasons


@pytest.fixture
def destination_trace(crossing_trace,rebind_trace):
    from types import SimpleNamespace
    c=crossing_trace
    def build(category='I',short=False,outside=False,wrong_marker=False):
        route=replace(c.fixture.routes['EGO'],destination=F(18))
        section=replace(c.fixture.domain.e_exit,route_station=F(19) if wrong_marker else F(18),
                        vertices=tuple((18.,y,z) for _,y,z in c.fixture.domain.e_exit.vertices))
        topology={'category':category,'mechanism':'F02'}
        if category=='F':
            from m56.metrics import _F_CONTRACTS
            names,units,estimators,windows=_F_CONTRACTS['F02']
            pair=replace(c.fixture.pair,names=names,units=units,estimators=estimators,window=windows)
        else:
            pair=replace(c.fixture.pair,names=('v_mean_E','e_lat_peak'),units=('m/s','m'),
                         estimators=('mean_speed','map_lateral_peak'),window=(('TRIGGER','X_END'),)*2)
        fixture=replace(c.fixture,routes={**c.fixture.routes,'EGO':route},pair=pair,
                        sections={'DESTINATION':section,'X':c.fixture.domain.e_exit,
                                  'I_SOURCE_BOUNDARY':c.fixture.domain.n_entry},
                        domain=replace(c.fixture.domain,topology=topology))
        frames=[]
        for i in range(6 if short else 7):
            f=c.frames[i];e,n=f.actors;x=17. if i==0 else 18.6
            e=replace(e,pose=replace(e.pose,x=x,y=2. if outside else 0.),arc=F(x))
            frames.append(replace(f,actors=(e,n)))
        return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)
    return build


@pytest.mark.parametrize('category',['I','F'])
def test_destination_common_to_io_and_f_confirms_actual_wholebody_hold(require,destination_trace,category):
    detect=require('m56.metrics','detect_events');c=destination_trace(category)
    events={e.name:e for e in detect(c.frames,c.fixture)}
    assert events['DESTINATION_CONFIRMED'].frame==106
    assert events['DESTINATION_CONFIRMED'].time==F(3,10)


@pytest.mark.parametrize('fault',['short','outside','wrong_marker'])
def test_destination_not_inferred_from_front_queue_or_wrong_marker(require,destination_trace,fault):
    detect=require('m56.metrics','detect_events');c=destination_trace(**{fault:True})
    assert 'DESTINATION_CONFIRMED' not in {e.name for e in detect(c.frames,c.fixture)}


def test_f06_reverse_reservation_requires_actual_stop_before_release(require,f06_action_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f06_action_trace('no_reservation_stop');events=detect(c.frames,c.fixture)
    assert 'NPC_REVERSE_TARGET_STOP_CONFIRMED' in {e.name for e in events}
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='FAILED'
    assert 'RESERVATION_STOP_NOT_CONFIRMED' in reasons


@pytest.mark.parametrize('reverse',[True,False])
def test_f06_observations_after_metric_end_still_constrain_forward_completion(require,f06_action_trace,rebind_trace,reverse):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f06_action_trace();last=c.frames[-1];e,n=last.actors
    x=2.875 if reverse else 3.125;speed=-2.5 if reverse else 2.5
    e=replace(e,pose=replace(e.pose,x=x),arc=F(x),velocity=(speed,0.,0.))
    if not reverse:
        e=replace(e,readback=replace(e.readback,reverse=False,manual_gear_shift=False,gear=1))
    e=replace(e,commands=tuple(replace(cmd,frame=262,next_frame=263,control=e.readback) for cmd in e.commands))
    raw=replace(last.integrity['frame_refs'][0],frame=263,time=F(163,20))
    extra=replace(last,frame=263,simtime=F(163,20),actors=(e,n),integrity={'frame_refs':(raw,)})
    frames=rebind_trace((*c.frames,extra),c.fixture);events=detect(frames,c.fixture)
    assert next(e.frame for e in events if e.name=='NPC_REVERSE_TARGET_STOP_CONFIRMED')==262
    state,reasons=audit(frames,c.fixture,events)
    assert state==('FAILED' if reverse else 'INCOMPLETE')
    assert ('POST_END_UNPLANNED_REVERSE' in reasons)==reverse


def test_f06_corroborated_cue_reverse_target_stop_and_measure(require,f06_trace):
    detect=require('m56.metrics','detect_events');measure=require('m56.metrics','measure');c=f06_trace
    events=detect(c.frames,c.fixture);by_name={e.name:e for e in events}
    assert by_name['TRIGGER'].frame==111
    assert by_name['NPC_REVERSE_TARGET_STOP_CONFIRMED'].frame==262
    values=measure(c.frames,c.fixture.pair,events)
    assert tuple(v.value for v in values)==(F(1),F(2))
    assert all(v.status=='VALID' for v in values)


def test_f06_command_only_cue_unknown(require,f06_trace):
    detect=require('m56.metrics','detect_events');c=f06_trace
    frames=tuple(replace(f,integrity={k:v for k,v in f.integrity.items() if k!='preparation_cue'}) for f in c.frames)
    events=detect(frames,c.fixture)
    assert 'TRIGGER' not in {e.name for e in events}
    assert 'WITNESS_UNKNOWN' in {e.name for e in events}


def test_f06_stopped_readback_never_invents_later_reverse_or_target(require,f06_trace):
    detect=require('m56.metrics','detect_events');c=f06_trace
    events=detect(c.frames[:71],c.fixture)  # ends before observed NPC reverse
    assert 'NPC_REVERSE_TARGET_STOP_CONFIRMED' not in {e.name for e in events}
    assert 'TRIGGER' in {e.name for e in events}
    assert 'NPC_REVERSE_TARGET_STOP_CONFIRMED' not in {e.name for e in detect(c.frames[:-1],c.fixture)}


def test_f02_closing_not_overtake(require,crossing_trace,f_policies,rebind_trace):
    detect=require('m56.metrics','detect_events');pairfn=require('m56.metrics','f_pair');c=crossing_trace
    from m56.catalog import _digest
    route=c.fixture.routes['EGO']
    route=replace(route,transforms=(route.transforms[0],replace(route.transforms[-1],x=120.)),arc=(F(0),F(120)),destination=F(115))
    pair=pairfn('F02',f_policies.approve('F02','route:'+_digest(route)))
    end=replace(c.fixture.domain.e_exit,route_station=F(181,2),
                vertices=tuple((90.5,y,z) for _,y,z in c.fixture.domain.e_exit.vertices))
    fixture=replace(c.fixture,pair=pair,G=None,routes={'EGO':route,'NPC':route},sections={'F02_END':end},
                    domain=replace(c.fixture.domain,topology={'category':'F','mechanism':'F02','nominal_front_t0_m':F(61,2)}))
    frames=[]
    for i,f in enumerate(c.frames[:3]):
        e,n=f.actors
        ex=(30.,30.25,92.)[i];nx=(8.,9.25,71.)[i]
        e=replace(e,pose=replace(e.pose,x=ex),arc=F(ex),velocity=(4.,0.,0.))
        n=replace(n,pose=replace(n.pose,x=nx),arc=F(nx),velocity=(5.,0.,0.))
        frames.append(replace(f,actors=(e,n)))
    frames=rebind_trace(tuple(frames),fixture)
    events={e.name:e for e in detect(frames,fixture)}
    assert events['TRIGGER'].frame==101  # gR21 ->20, NPC behind and closing
    assert events['F02_END'].frame==102
    not_closing=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],velocity=(3.,0.,0.)))) for f in frames)
    assert 'TRIGGER' not in {e.name for e in detect(rebind_trace(not_closing,fixture),fixture)}
    overtaken=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],pose=replace(f.actors[1].pose,x=40.),arc=F(40)))) for f in frames)
    assert 'TRIGGER' not in {e.name for e in detect(rebind_trace(overtaken,fixture),fixture)}


@pytest.fixture
def frame_capability():
    """Synthetic reviewed observation recipe, not a CARLA getter or authority."""
    from m56.model import CapabilityProof,ReviewRecord
    from m56.catalog import _digest
    def attach(frame,fixture,key,kind,method,limits):
        refs=frame.integrity['frame_refs']
        packet={'kind':kind,'method':method,'raw_refs':refs,'uncertainty':F(1,1000),
                'limits':{'fixture_hash':_digest(fixture),'frame':frame.frame,'actors_hash':_digest(frame.actors),**limits},
                'status':'CORROBORATED'}
        review=ReviewRecord(_digest(packet),'CAPABILITY:'+kind,refs,'SYNTHETIC_TEST','2026-10-08','APPROVED',
                            ('synthetic observed packet',),refs[0])
        return replace(frame,integrity={**frame.integrity,key:CapabilityProof(**packet,review=review)})
    return attach


@pytest.fixture
def f03_trace(crossing_trace,f_policies,rebind_trace,frame_capability,require):
    from m56.model import ControlPacket,FrozenResponse,CommandRecord
    from m56.catalog import _digest
    from types import SimpleNamespace
    c=crossing_trace;route=c.fixture.routes['NPC']
    route=replace(route,transforms=(route.transforms[0],replace(route.transforms[-1],x=24.,z=18.)))
    pair=require('m56.metrics','f_pair')('F03',f_policies.approve('F03','route:'+_digest(route)))
    response=FrozenResponse('NPC','NPC_COMMON',route,{}, {},{'brake':'F03_BRAKE'},'a'*64)
    fixture=replace(c.fixture,pair=pair,G=None,routes={'EGO':route,'NPC':route},responses=(response,),
                    domain=replace(c.fixture.domain,topology={'category':'F','mechanism':'F03'}))
    frames=[]
    # Trigger105, issue145 (+2s), receiving146; actual STOP samples147..157.
    for number in range(100,158):
        f=c.frames[0];e,n=f.actors;raw=replace(f.integrity['frame_refs'][0],frame=number,time=F(number-100,20))
        s=F(10)-F(min(number-100,46),40)
        control=ControlPacket(0.,0.,.5 if number>=146 else 0.,False,False,False,1)
        commands=(CommandRecord(n.id,number-1,number,'CONTROL',F(0),F(0),control,None,'F03_BRAKE',response.hash),) if number>=146 else ()
        n=replace(n,pose=replace(n.pose,x=float(s*F(4,5)),z=float(s*F(3,5))),arc=None,
                  velocity=(-.4,0.,-.3) if number<=146 else (0.,0.,0.),readback=control,commands=commands)
        e=replace(e,pose=replace(e.pose,x=3.2,z=2.4),arc=None,velocity=(0.,0.,0.))
        f=replace(f,frame=number,simtime=F(number-100,20),actors=(e,n),integrity={'frame_refs':(raw,)})
        frames.append(frame_capability(f,fixture,'rollback','ROLLBACK','unpowered-grade-motion-v1',{'gravity_along_reverse_mps2':F(1)}))
    return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)


def test_f03_powered_reverse_not_rollback(require,f03_trace,rebind_trace,frame_capability):
    detect=require('m56.metrics','detect_events');c=f03_trace
    events={e.name:e for e in detect(c.frames,c.fixture)}
    assert events['TRIGGER'].frame==105
    assert events['NPC_STOP_CONFIRMED'].frame==157
    powered=[]
    for f in c.frames:
        n=replace(f.actors[1],readback=replace(f.actors[1].readback,throttle=.1,reverse=True,gear=-1))
        f=replace(f,actors=(f.actors[0],n))
        powered.append(frame_capability(f,c.fixture,'rollback','ROLLBACK','unpowered-grade-motion-v1',{'gravity_along_reverse_mps2':F(1)}))
    assert 'TRIGGER' not in {e.name for e in detect(rebind_trace(tuple(powered),c.fixture),c.fixture)}
    no_grade=tuple(replace(f,integrity={k:v for k,v in f.integrity.items() if k!='rollback'}) for f in c.frames)
    assert 'TRIGGER' not in {e.name for e in detect(no_grade,c.fixture)}
    assert 'NPC_STOP_CONFIRMED' not in {e.name for e in detect(c.frames[:-1],c.fixture)}


@pytest.fixture
def f04_trace(io_trace,f_policies,rebind_trace,frame_capability,require):
    from itertools import product
    from types import SimpleNamespace
    c=io_trace
    pair=require('m56.metrics','f_pair')('F04',f_policies.approve('F04','map:'+'b'*64))
    corridor=tuple(product((0.,30.),(-1.,1.),(-1.,1.)))
    fixture=replace(c.fixture,pair=pair,sections={'F04_END':c.fixture.sections['X']},
              domain=replace(c.fixture.domain,topology={'category':'F','mechanism':'F04','door_corridor':corridor}))
    frames=[]
    for i,f in enumerate(c.frames):
        envelope=tuple(product((5.,6.),(2.,3.) if i==0 else (.5,1.5),(-.5,.5)))
        frames.append(frame_capability(f,fixture,'door_geometry','DOOR_GEOMETRY','calibrated-door-envelope-v1',
                      {'door_state':'CLOSED' if i==0 else 'OPEN','collider_envelope':envelope}))
    return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)


def test_f04_rpc_success_not_door_intrusion(require,f04_trace):
    detect=require('m56.metrics','detect_events');c=f04_trace
    events={e.name:e for e in detect(c.frames,c.fixture)}
    assert events['TRIGGER'].frame==101
    assert events['F04_END'].frame==103
    rpc=tuple(replace(f,integrity={k:v for k,v in f.integrity.items() if k!='door_geometry'}) for f in c.frames)
    rpc=tuple(replace(f,integrity={**f.integrity,'door_rpc_success':True}) for f in rpc)
    events=detect(rpc,c.fixture)
    assert 'TRIGGER' not in {e.name for e in events}
    assert 'WITNESS_UNKNOWN' in {e.name for e in events}


def test_f04_open_door_outside_corridor_never_triggers(require,f04_trace,frame_capability):
    detect=require('m56.metrics','detect_events');c=f04_trace
    from itertools import product
    frames=tuple(frame_capability(f,c.fixture,'door_geometry','DOOR_GEOMETRY','calibrated-door-envelope-v1',
        {'door_state':'CLOSED' if i==0 else 'OPEN','collider_envelope':tuple(product((5.,6.),(2.,3.),(-.5,.5)))})
        for i,f in enumerate(c.frames))
    assert 'TRIGGER' not in {e.name for e in detect(frames,c.fixture)}


@pytest.fixture
def f05_trace(crossing_trace,f_policies,rebind_trace,require):
    from m56.model import ControlPacket
    from types import SimpleNamespace
    c=crossing_trace
    pair=require('m56.metrics','f_pair')('F05',f_policies.approve('F05',c.fixture.pair.reference))
    end=replace(c.fixture.domain.e_exit,route_station=F(29,2),
                vertices=tuple((14.5,y,z) for _,y,z in c.fixture.domain.e_exit.vertices))
    fixture=replace(c.fixture,pair=pair,G=None,sections={'F05_END':end},domain=replace(c.fixture.domain,
        topology={'category':'F','mechanism':'F05','queue_gap_m':F(3),'nominal_front_t0_m':F(9,2)}))
    frames=[]
    for number in range(100,312):
        f=c.frames[0];e,n=f.actors;raw=replace(f.integrity['frame_refs'][0],frame=number,time=F(number-100,20))
        ex=4.+max(0,number-200)/10;nx=8.+max(0,number-180)/10
        e=replace(e,pose=replace(e.pose,x=ex),arc=F(ex),velocity=(2. if number>200 else 0.,0.,0.))
        n=replace(n,pose=replace(n.pose,x=nx),arc=F(nx),velocity=(2. if number>180 else 0.,0.,0.),
                  readback=ControlPacket(.25 if number>=180 else 0.,0.,0.,False,False,False,1))
        frames.append(replace(f,frame=number,simtime=F(number-100,20),actors=(e,n),integrity={
            'frame_refs':(raw,),'metric_context':{'reference':pair.reference,'pair_hash':pair.hash,
            'directed_route':fixture.routes['EGO'],'uncertainty':{'d_pre_move_m':F(1,100),'t_queue_exit_s':F(0)}}}))
    return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)


@pytest.fixture
def f05_action_trace(f05_trace,rebind_trace):
    from m56.model import FrozenResponse,CommandRecord,ControlPacket
    from types import SimpleNamespace
    c=f05_trace
    def build(kind='normal'):
        action='B' if kind in ('creep_overshoot','creep_never_stopped') else 'A'
        response=FrozenResponse('EGO',action,c.fixture.routes['EGO'],{}, {},{},'a'*64)
        fixture=replace(c.fixture,responses=(response,))
        frames=[]
        for f in c.frames:
            e,n=f.actors
            if kind=='early_a' and 121<=f.frame<200:
                x=4.+min(1.,(f.frame-120)/10)
                e=replace(e,pose=replace(e.pose,x=x),arc=F(x),velocity=(2. if f.frame<=130 else 0.,0.,0.))
            if kind=='creep_overshoot' and f.frame>120:
                x=4.+min(1.5,(f.frame-120)/40)
                e=replace(e,pose=replace(e.pose,x=x),arc=F(x),velocity=(.5 if f.frame<=180 else 0.,0.,0.))
            if kind=='creep_never_stopped' and f.frame>120:
                x=4.+min(1.,(f.frame-120)/40) if f.frame<181 else 5.+(f.frame-180)/10
                e=replace(e,pose=replace(e.pose,x=x),arc=F(x),velocity=(.5 if f.frame<=180 else 2.,0.,0.))
            control=ControlPacket(.2,0.,0.,False,False,False,1)
            command=CommandRecord(e.id,f.frame-1,f.frame,'CONTROL',F(36,5),F(0),control,None,'SYNTHETIC',response.hash)
            frames.append(replace(f,actors=(replace(e,commands=(command,),readback=control),n)))
        return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)
    return build


def test_f05_observed_queue_exit_still_needs_separate_destination(require,f05_action_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f05_action_trace();events=detect(c.frames,c.fixture)
    assert {'TRIGGER','N_MOVE','F05_END'}.issubset({e.name for e in events})
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='INCOMPLETE'
    assert 'DESTINATION_CONFIRMED_MISSING' in reasons


@pytest.mark.parametrize('kind,reason',[('early_a','QUEUE_RELEASE_BEFORE_NPC_ADVANCE'),
                                       ('creep_overshoot','CREEP_RESERVATION_EXCEEDED'),
                                       ('creep_never_stopped','CREEP_STOP_NOT_CONFIRMED')])
def test_f05_action_not_rescued_by_numeric_progress_metric(require,f05_action_trace,kind,reason):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f05_action_trace(kind);state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='FAILED'
    assert reason in reasons


def test_f05_move_is_not_release_command(require,f05_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');measure=require('m56.metrics','measure');c=f05_trace
    events=detect(c.frames,c.fixture);by_name={e.name:e for e in events}
    assert by_name['TRIGGER'].frame==120
    assert by_name['N_MOVE'].frame==186
    assert by_name['F05_END'].frame==311
    assert tuple(m.value for m in measure(c.frames,c.fixture.pair,events))==(F(0),F(25,4))
    # Positive throttle/readback alone cannot create first-move.
    stopped=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],pose=replace(f.actors[1].pose,x=8.),arc=F(8),velocity=(0.,0.,0.))))
                  for f in c.frames[:87])
    assert 'N_MOVE' not in {e.name for e in detect(rebind_trace(stopped,c.fixture),c.fixture)}
    assert 'TRIGGER' not in {e.name for e in detect(c.frames[:20],c.fixture)}
    assert 'N_MOVE' not in {e.name for e in detect(c.frames[:86],c.fixture)}


@pytest.fixture
def f01_complete_trace(f01_trace,rebind_trace):
    from types import SimpleNamespace
    c=f01_trace
    end=replace(c.fixture.domain.n_exit,route_station=F(19,2),
                vertices=tuple((9.5,y,z) for _,y,z in c.fixture.domain.n_exit.vertices))
    fixture=replace(c.fixture,sections={'F01_END':end})
    frames=list(c.frames)
    for number in range(106,161):
        f=c.frames[-1];e,n=f.actors;raw=replace(f.integrity['frame_refs'][0],frame=number,time=F(number-100,20))
        x=8.+max(0,number-146)*.15
        n=replace(n,pose=replace(n.pose,x=x),arc=F(x),velocity=(3. if number>=147 else 0.,0.,0.),commands=())
        frames.append(replace(f,frame=number,simtime=F(number-100,20),actors=(e,n),integrity={'frame_refs':(raw,)}))
    return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)


@pytest.fixture
def f01_action_trace(f01_complete_trace,rebind_trace):
    from m56.model import FrozenResponse,CommandRecord,ControlPacket
    from types import SimpleNamespace
    c=f01_complete_trace
    def build(kind='b_continuous'):
        action='B' if kind=='b_continuous' else 'A'
        response=FrozenResponse('EGO',action,c.fixture.routes['EGO'],{}, {},{},'b'*64)
        fixture=replace(c.fixture,responses=(*c.fixture.responses,response));frames=[]
        for f in c.frames:
            e,n=f.actors
            if kind=='early_resume':
                v=0. if 106<=f.frame<=120 else 2.
                x=4.+max(0,f.frame-120)/10
                e=replace(e,pose=replace(e.pose,x=x),arc=F(x),velocity=(v,0.,0.))
            control=ControlPacket(.2,0.,0.,False,False,False,1)
            command=CommandRecord(e.id,f.frame-1,f.frame,'CONTROL',F(36,5),F(0),control,None,'SYNTHETIC',response.hash)
            frames.append(replace(f,actors=(replace(e,commands=(command,),readback=control),n)))
        return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)
    return build


def test_f01_b_metric_end_alone_is_not_forward_completion(require,f01_action_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f01_action_trace();events=detect(c.frames,c.fixture)
    assert 'F01_N_CLEAR' in {e.name for e in events}
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='INCOMPLETE'
    assert 'DESTINATION_CONFIRMED_MISSING' in reasons


@pytest.mark.parametrize('kind,reason',[('a_no_stop','STOP_REQUIRED_BEFORE_RELEASE'),('early_resume','RESUMED_BEFORE_NPC_MOVE')])
def test_f01_wait_action_requires_actual_stop_and_restart_not_target(require,f01_action_trace,kind,reason):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f01_action_trace(kind);state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='FAILED'
    assert reason in reasons


def test_f04_a_cannot_complete_past_open_door_without_actual_stop(require,f04_trace,rebind_trace,frame_capability):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    from m56.model import FrozenResponse,CommandRecord,ControlPacket
    c=f04_trace;response=FrozenResponse('EGO','A',c.fixture.routes['EGO'],{}, {},{},'a'*64)
    fixture=replace(c.fixture,responses=(response,));frames=[]
    for f in c.frames:
        e,n=f.actors;control=ControlPacket(.2,0.,0.,False,False,False,1)
        command=CommandRecord(e.id,f.frame-1,f.frame,'CONTROL',F(36,5),F(0),control,None,'SYNTHETIC',response.hash)
        f=replace(f,actors=(replace(e,commands=(command,),readback=control),n))
        old=f.integrity['door_geometry'].limits
        frames.append(frame_capability(f,fixture,'door_geometry','DOOR_GEOMETRY','calibrated-door-envelope-v1',
            {'door_state':old['door_state'],'collider_envelope':old['collider_envelope']}))
    frames=rebind_trace(tuple(frames),fixture);events=detect(frames,fixture)
    assert 'F04_END' in {e.name for e in events}
    state,reasons=audit(frames,fixture,events)
    assert state=='FAILED'
    assert 'PASSED_BEFORE_DOOR_REMOVAL' in reasons
    assert 'STOP_REQUIRED_BEFORE_RELEASE' in reasons


@pytest.fixture
def f02_action_trace(crossing_trace,f_policies,rebind_trace,require):
    from m56.model import FrozenResponse,CommandRecord,ControlPacket
    from types import SimpleNamespace
    c=crossing_trace
    def build(stopped=False):
        route=replace(c.fixture.routes['EGO'],transforms=(c.fixture.routes['EGO'].transforms[0],
                        replace(c.fixture.routes['EGO'].transforms[-1],x=130.)),arc=(F(0),F(130)),destination=F(90))
        from m56.catalog import _digest
        pair=require('m56.metrics','f_pair')('F02',f_policies.approve('F02','route:'+_digest(route)))
        response=FrozenResponse('EGO','A',route,{}, {},{},'a'*64)
        section=replace(c.fixture.domain.e_exit,route_station=F(167,2),
                        vertices=tuple((83.5,y,z) for _,y,z in c.fixture.domain.e_exit.vertices))
        fixture=replace(c.fixture,pair=pair,routes={'EGO':route,'NPC':route},responses=(response,),
                        sections={'F02_END':section},domain=replace(c.fixture.domain,topology={
                        'category':'F','mechanism':'F02','nominal_front_t0_m':F(47,2)}))
        frames=[]
        for i in range(15):
            f=c.frames[0];e,n=f.actors;frame=100+i;time=F(i,20)
            x=23.+5*min(i,3) if stopped else 23.+5*i
            e=replace(e,pose=replace(e.pose,x=x),arc=F(x),velocity=(0. if stopped and i>=4 else 4.,0.,0.))
            n=replace(n,pose=replace(n.pose,x=1.+6*i),arc=F(1+6*i),velocity=(5.,0.,0.))
            control=ControlPacket(.2,0.,0.,False,False,False,1)
            command=CommandRecord(e.id,frame-1,frame,'CONTROL',F(72,5),F(0),control,None,'SYNTHETIC',response.hash)
            raw=replace(f.integrity['frame_refs'][0],frame=frame,time=time)
            frames.append(replace(f,frame=frame,simtime=time,actors=(replace(e,commands=(command,),readback=control),n),
                                  integrity={'frame_refs':(raw,)}))
        return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)
    return build


def test_f02_metric_section_is_not_forward_destination(require,f02_action_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f02_action_trace();events=detect(c.frames,c.fixture)
    assert 'F02_END' in {e.name for e in events}
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='INCOMPLETE'
    assert 'DESTINATION_CONFIRMED_MISSING' in reasons


def test_f02_full_forward_destination_can_complete_observed_action_component(require,f02_action_trace,rebind_trace):
    c=f02_action_trace();frames=list(c.frames)
    section=replace(c.fixture.sections['F02_END'],route_station=F(90),
                    vertices=tuple((90.,y,z) for _,y,z in c.fixture.sections['F02_END'].vertices))
    fixture=replace(c.fixture,sections={**c.fixture.sections,'DESTINATION':section})
    for _ in range(7):
        last=frames[-1];number=last.frame+1;time=last.simtime+F(1,20)
        actors=tuple(replace(a,pose=replace(a.pose,x=a.pose.x+.125),arc=F(a.pose.x+.125),
                             commands=tuple(replace(cmd,frame=number-1,next_frame=number) for cmd in a.commands)) for a in last.actors)
        ref=replace(last.integrity['frame_refs'][0],frame=number,time=time)
        frames.append(replace(last,frame=number,simtime=time,actors=actors,integrity={'frame_refs':(ref,)}))
    frames=rebind_trace(tuple(frames),fixture);events=require('m56.metrics','detect_events')(frames,fixture)
    assert {'TRIGGER','F02_END','DESTINATION_CONFIRMED'}.issubset({e.name for e in events})
    state,reasons=require('m56.metrics','_f_action')(frames,fixture,events)
    assert state=='UNKNOWN' and reasons==('F_FULL_ACTION_REVIEW_PENDING',)
    finish=require('m56.metrics','_finish_action')
    assert finish(frames,fixture,events,state,reasons)==('COMPLETE',())


def test_action_finisher_never_uses_metric_end_as_destination(require,f02_action_trace):
    c=f02_action_trace();events=require('m56.metrics','detect_events')(c.frames,c.fixture)
    state,reasons=require('m56.metrics','_f_action')(c.frames,c.fixture,events)
    out=require('m56.metrics','_finish_action')(c.frames,c.fixture,events,state,reasons)
    assert out[0]=='INCOMPLETE'
    assert 'DESTINATION_CONFIRMED_MISSING' in out[1]



def _f02_destination_trace(require,f02_action_trace,rebind_trace):
    c=f02_action_trace();frames=list(c.frames)
    section=replace(c.fixture.sections['F02_END'],route_station=F(90),
                    vertices=tuple((90.,y,z) for _,y,z in c.fixture.sections['F02_END'].vertices))
    fixture=replace(c.fixture,sections={**c.fixture.sections,'DESTINATION':section})
    for _ in range(7):
        last=frames[-1];number=last.frame+1;time=last.simtime+F(1,20)
        actors=tuple(replace(a,pose=replace(a.pose,x=a.pose.x+.125),arc=F(a.pose.x+.125),
                             commands=tuple(replace(cmd,frame=number-1,next_frame=number) for cmd in a.commands)) for a in last.actors)
        ref=replace(last.integrity['frame_refs'][0],frame=number,time=time)
        frames.append(replace(last,frame=number,simtime=time,actors=actors,integrity={'frame_refs':(ref,)}))
    frames=rebind_trace(tuple(frames),fixture)
    return frames,fixture,require('m56.metrics','detect_events')(frames,fixture)


@pytest.mark.parametrize('mechanism,end',[('F03','NPC_STOP_CONFIRMED'),('F06-ALT1','NPC_REVERSE_TARGET_STOP_CONFIRMED')])
def test_reverse_f_review_pending_finishes_only_with_forward_destination(require,f02_action_trace,rebind_trace,mechanism,end):
    """F03/F06 reverse audit already passed (pending reason only); the finisher must apply the same
    post-metric forward destination/progress/control gate as F01/F02/F04/F05, not stay pending forever."""
    frames,fixture,events=_f02_destination_trace(require,f02_action_trace,rebind_trace)
    fixture=replace(fixture,domain=replace(fixture.domain,topology={**fixture.domain.topology,'mechanism':mechanism}))
    events=tuple(replace(e,name=end) if e.name=='F02_END' else e for e in events)
    finish=require('m56.metrics','_finish_action');pending=('F_FULL_ACTION_REVIEW_PENDING',)
    assert finish(frames,fixture,events,'UNKNOWN',pending)==('COMPLETE',())
    # Other reverse unknowns are never upgraded by the finisher.
    assert finish(frames,fixture,events,'UNKNOWN',('REVERSE_CONTROL_UNKNOWN',))==('UNKNOWN',('REVERSE_CONTROL_UNKNOWN',))
    no_dest=tuple(e for e in events if e.name!='DESTINATION_CONFIRMED')
    assert finish(frames,fixture,no_dest,'UNKNOWN',pending)==('INCOMPLETE',('DESTINATION_CONFIRMED_MISSING',))
    dest=next(e.frame for e in events if e.name=='DESTINATION_CONFIRMED')
    reversing=tuple(replace(f,actors=tuple(replace(a,readback=replace(a.readback,reverse=True)) if a.role=='EGO' else a
                                           for a in f.actors)) if f.frame==dest else f for f in frames)
    assert finish(reversing,fixture,events,'UNKNOWN',pending)==('UNKNOWN',('FORWARD_CONTROL_UNPROVEN',))

def test_f02_cannot_stop_in_place_instead_of_forward_action(require,f02_action_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f02_action_trace(stopped=True);state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='FAILED'
    assert 'UNPLANNED_STOP' in reasons


@pytest.mark.parametrize('later_reverse',[False,True])
def test_f02_projection_gap_is_not_bridged_but_later_reverse_survives(require,f02_action_trace,rebind_trace,later_reverse):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f02_action_trace();frames=[]
    for f in c.frames:
        e,n=f.actors
        x={104:-1.,105:30.}.get(f.frame,e.pose.x)
        if later_reverse and f.frame==107:x=52.  # 106 observed at53,107 at52.
        e=replace(e,pose=replace(e.pose,x=x),arc=None if f.frame==104 else F(x))
        frames.append(replace(f,actors=(e,n)))
    frames=rebind_trace(tuple(frames),c.fixture);events=detect(frames,c.fixture)
    assert 'TRIGGER' in {e.name for e in events}
    state,reasons=audit(frames,c.fixture,events)
    assert 'ACTION_PROJECTION_UNKNOWN' in reasons
    assert state==('FAILED' if later_reverse else 'UNKNOWN')
    assert ('UNPLANNED_REVERSE' in reasons)==later_reverse


def test_f02_observed_stop_survives_independent_projection_gap(require,f02_action_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f02_action_trace(stopped=True);frames=[]
    for f in c.frames:
        e,n=f.actors
        if f.frame==102:e=replace(e,pose=replace(e.pose,x=-1.),arc=None)
        frames.append(replace(f,actors=(e,n)))
    frames=rebind_trace(tuple(frames),c.fixture);events=detect(frames,c.fixture)
    assert 'TRIGGER' in {e.name for e in events}
    state,reasons=audit(frames,c.fixture,events)
    assert state=='FAILED'
    assert {'ACTION_PROJECTION_UNKNOWN','UNPLANNED_STOP'}.issubset(reasons)


@pytest.mark.parametrize('fixture_name',['f01_action_trace','f02_action_trace','f05_action_trace'])
@pytest.mark.parametrize('role',['EGO','NPC'])
def test_f_forward_action_rejects_reverse_after_metric_window(require,request,rebind_trace,fixture_name,role):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=request.getfixturevalue(fixture_name)();last=c.frames[-1];number=last.frame+1;time=last.simtime+F(1,20)
    actors=[]
    for a in last.actors:
        if a.role==role:
            x=a.pose.x-.125
            a=replace(a,pose=replace(a.pose,x=x),arc=F(x),velocity=(-2.5,0.,0.))
        a=replace(a,commands=tuple(replace(cmd,frame=number-1,next_frame=number) for cmd in a.commands))
        actors.append(a)
    ref=replace(last.integrity['frame_refs'][0],frame=number,time=time)
    extra=replace(last,frame=number,simtime=time,actors=tuple(actors),integrity={'frame_refs':(ref,)})
    frames=rebind_trace((*c.frames,extra),c.fixture);events=detect(frames,c.fixture)
    assert c.fixture.pair.window[-1][1] in {e.name for e in events}
    state,reasons=audit(frames,c.fixture,events)
    assert state=='FAILED'


def test_f04_spatial_unknown_cannot_hide_observed_reverse_after_pass(require,f04_trace,rebind_trace,frame_capability):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    from m56.model import FrozenResponse,CommandRecord,ControlPacket
    c=f04_trace;response=FrozenResponse('EGO','B',c.fixture.routes['EGO'],{}, {},{},'a'*64)
    fixture=replace(c.fixture,responses=(response,));frames=[]
    control=ControlPacket(.2,0.,0.,False,False,False,1)
    for f in c.frames:
        e,n=f.actors;cmd=CommandRecord(e.id,f.frame-1,f.frame,'CONTROL',F(18,5),F(3,4),control,None,'SYNTHETIC',response.hash)
        f=replace(f,actors=(replace(e,commands=(cmd,),readback=control),n))
        old=f.integrity['door_geometry'].limits
        frames.append(frame_capability(f,fixture,'door_geometry','DOOR_GEOMETRY','calibrated-door-envelope-v1',
            {'door_state':old['door_state'],'collider_envelope':old['collider_envelope']}))
    f=frames[-1];e,n=f.actors;x=e.pose.x-.125;number=f.frame+1;time=f.simtime+F(1,20)
    e=replace(e,pose=replace(e.pose,x=x),arc=F(x),velocity=(-2.5,0.,0.),
              commands=tuple(replace(cmd,frame=number-1,next_frame=number) for cmd in e.commands))
    ref=replace(f.integrity['frame_refs'][0],frame=number,time=time)
    frames.append(replace(f,frame=number,simtime=time,actors=(e,n),integrity={'frame_refs':(ref,)}))
    frames=rebind_trace(tuple(frames),fixture);events=detect(frames,fixture)
    assert 'F04_END' in {e.name for e in events}
    state,reasons=audit(frames,fixture,events)
    assert state=='FAILED'
    assert {'SPATIAL_PASS_FIT_REVIEW_PENDING','POST_END_UNPLANNED_REVERSE'}.issubset(reasons)


@pytest.fixture
def f04_spatial_trace(f04_trace,rebind_trace,frame_capability):
    from m56.model import FrozenResponse,CommandRecord,ControlPacket
    from types import SimpleNamespace
    from itertools import product
    c=f04_trace
    def build(mode='inside'):
        response=FrozenResponse('EGO','B',c.fixture.routes['EGO'],{}, {},{},'a'*64)
        topology=dict(c.fixture.domain.topology)
        if mode!='missing_region':
            topology['action_regions']={'EGO_INITIAL':tuple(product((0.,30.),(-1.,1.),(-1.,1.)))}
        end=replace(c.fixture.sections['F04_END'],vertices=tuple(product((3.,),(-3.,3.),(-1.,1.))))
        fixture=replace(c.fixture,responses=(response,),domain=replace(c.fixture.domain,topology=topology),
                        sections={**c.fixture.sections,'F04_END':end})
        frames=[];control=ControlPacket(.2,0.,0.,False,False,False,1)
        for i,f in enumerate(c.frames):
            e,n=f.actors;y=0. if i==0 else 1.25 if mode in ('outside','projection_gap') else .75 if mode=='boundary' else .5
            if mode=='projection_gap' and i==2:
                e=replace(e,pose=replace(e.pose,x=-1.),arc=None)
            command=CommandRecord(e.id,f.frame-1,f.frame,'CONTROL',F(18,5),F(3,4),control,None,'SYNTHETIC',response.hash)
            e=replace(e,pose=replace(e.pose,y=y),commands=(command,),readback=control)
            f=replace(f,actors=(e,n));old=f.integrity['door_geometry'].limits
            frames.append(frame_capability(f,fixture,'door_geometry','DOOR_GEOMETRY','calibrated-door-envelope-v1',
                {'door_state':old['door_state'],'collider_envelope':old['collider_envelope']}))
        return SimpleNamespace(frames=rebind_trace(tuple(frames),fixture),fixture=fixture)
    return build


def test_f04_spatial_pass_cannot_leave_frozen_initial_lane(require,f04_spatial_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f04_spatial_trace('outside');events=detect(c.frames,c.fixture)
    assert 'F04_END' in {e.name for e in events}
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='FAILED'
    assert 'SPATIAL_PASS_LEFT_INITIAL_LANE' in reasons


@pytest.mark.parametrize('mode,reason',[('missing_region','SPATIAL_PASS_REGION_UNPROVEN'),
                                       ('boundary','SPATIAL_PASS_LANE_UNCERTAIN')])
def test_f04_missing_or_ambiguous_lane_not_inferred_from_passage(require,f04_spatial_trace,mode,reason):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f04_spatial_trace(mode);state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='UNKNOWN'
    assert reason in reasons


def test_f04_lane_escape_after_metric_end_still_violates_forward_action(require,f04_spatial_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f04_spatial_trace();last=c.frames[-1];ego,npc=last.actors;number=last.frame+1;time=last.simtime+F(1,20)
    ego=replace(ego,pose=replace(ego.pose,x=ego.pose.x+.125,y=1.5),arc=F(ego.pose.x+.125),
                commands=tuple(replace(cmd,frame=number-1,next_frame=number) for cmd in ego.commands))
    ref=replace(last.integrity['frame_refs'][0],frame=number,time=time)
    extra=replace(last,frame=number,simtime=time,actors=(ego,npc),integrity={'frame_refs':(ref,)})
    frames=rebind_trace((*c.frames,extra),c.fixture);events=detect(frames,c.fixture)
    assert next(e.frame for e in events if e.name=='F04_END')==103
    state,reasons=audit(frames,c.fixture,events)
    assert state=='FAILED'
    assert 'SPATIAL_PASS_LEFT_INITIAL_LANE' in reasons


def test_f04_missing_route_projection_cannot_hide_independent_lane_escape(require,f04_spatial_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f04_spatial_trace('projection_gap');events=detect(c.frames,c.fixture)
    assert {'TRIGGER','F04_END'}.issubset({e.name for e in events})
    assert c.frames[1].actors[0].pose.y==1.25  # Known lateral escape before projection gap.
    assert c.frames[2].actors[0].pose.x==-1.  # Outside finite directed route, not clamped.
    state,reasons=audit(c.frames,c.fixture,events)
    assert state=='FAILED'
    assert {'ACTION_PROJECTION_UNKNOWN','SPATIAL_PASS_LEFT_INITIAL_LANE'}.issubset(reasons)


def test_f04_sampled_inside_lane_does_not_prove_continuous_spatial_fit(require,f04_spatial_trace):
    detect=require('m56.metrics','detect_events');audit=require('m56.metrics','_f_action')
    c=f04_spatial_trace();state,reasons=audit(c.frames,c.fixture,detect(c.frames,c.fixture))
    assert state=='UNKNOWN'
    assert 'SPATIAL_PASS_FIT_REVIEW_PENDING' in reasons
    assert 'SPATIAL_PASS_LEFT_INITIAL_LANE' not in reasons


def test_f01_end_requires_stop_restart_and_whole_npc(require,f01_complete_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=f01_complete_trace
    events={e.name:e for e in detect(c.frames,c.fixture)}
    assert events['TRIGGER'].frame==105
    assert events['N_MOVE'].frame==152
    assert events['F01_N_CLEAR'].frame==160
    assert 'F01_N_CLEAR' not in {e.name for e in detect(c.frames[:-1],c.fixture)}
    no_restart=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],velocity=(0.,0.,0.)))) if f.frame>=147 else f for f in c.frames)
    assert 'F01_N_CLEAR' not in {e.name for e in detect(rebind_trace(no_restart,c.fixture),c.fixture)}
    no_hold=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],velocity=(1.,0.,0.)))) if 106<=f.frame<=146 else f for f in c.frames)
    assert 'F01_N_CLEAR' not in {e.name for e in detect(rebind_trace(no_hold,c.fixture),c.fixture)}


@pytest.mark.parametrize('fault',['early_reverse','overshoot','missing_reverse_readback','forged_cue','missing_stop_history'])
def test_f06_contradictory_or_missing_evidence_never_completes(require,f06_trace,rebind_trace,fault):
    detect=require('m56.metrics','detect_events');c=f06_trace;frames=list(c.frames)
    if fault=='forged_cue':
        cue=frames[11];proof=cue.integrity['preparation_cue']
        frames[11]=replace(cue,integrity={**cue.integrity,'preparation_cue':replace(proof,
            limits={**proof.limits,'previous_frame':999})})
    elif fault=='missing_stop_history':
        frames=frames[1:]
    else:
        for i,f in enumerate(frames):
            n=f.actors[1]
            if fault=='early_reverse' and 140<=f.frame<171:
                n=replace(n,pose=replace(n.pose,x=7.9),arc=F(7.9),velocity=(-.5,0.,0.))
            elif fault=='overshoot' and f.frame>=250:
                n=replace(n,pose=replace(n.pose,x=5.9),arc=F(5.9))
            elif fault=='missing_reverse_readback' and f.frame>=171:
                n=replace(n,readback=None)
            frames[i]=replace(f,actors=(f.actors[0],n))
        frames=rebind_trace(tuple(frames),c.fixture)
    events=detect(tuple(frames),c.fixture)
    assert 'NPC_REVERSE_TARGET_STOP_CONFIRMED' not in {e.name for e in events}
    assert 'WITNESS_UNKNOWN' in {e.name for e in events}


def test_f03_brake_schedule_is_not_optional(require,f03_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=f03_trace
    frames=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],commands=()))) if f.frame>=145 else f for f in c.frames)
    events=detect(rebind_trace(frames,c.fixture),c.fixture)
    assert 'TRIGGER' in {e.name for e in events}
    assert 'NPC_STOP_CONFIRMED' not in {e.name for e in events}
    assert 'WITNESS_UNKNOWN' in {e.name for e in events}


def test_f_pair_cannot_reuse_review_after_reference_or_policy_change(require,f_policies):
    pairfn=require('m56.metrics','f_pair')
    from m56.model import BlockedFixture
    policies=f_policies.approve('F03')
    changed=replace(policies,descriptor_specs={'F03':{**policies.descriptor_specs['F03'],'reference':'post-outcome-route'}})
    assert isinstance(pairfn('F03',changed),BlockedFixture)
    assert isinstance(pairfn('F03',replace(policies,hash='0'*64)),BlockedFixture)


def test_f03_full_event_window_measures_actual_reverse_and_gap(require,f03_trace):
    detect=require('m56.metrics','detect_events');measure=require('m56.metrics','measure');c=f03_trace
    # Geometry/status tested above; supply the explicit pre-frozen metric context.
    frames=tuple(replace(f,integrity={**f.integrity,'metric_context':{
        'reference':c.fixture.pair.reference,'pair_hash':c.fixture.pair.hash,
        'directed_route':c.fixture.routes['EGO'],'uncertainty':{'d_reverse_m':F(1,100),'g_front_min_m':F(1,100)}}}) for f in c.frames)
    values=measure(frames,c.fixture.pair,detect(frames,c.fixture))
    assert values[0].value==0 and values[0].status=='VALID'
    assert values[1].value is not None and values[1].value>0 and values[1].status=='VALID'
    assert values[0].frames[0]==105 and values[0].frames[-1]==157
    # Zero A distance is an observation; it still requires separate D09/AB review.


def test_f04_pair_consumes_same_map_reference_and_detected_window(require,f04_trace,f_policies,rebind_trace,frame_capability):
    detect=require('m56.metrics','detect_events');measure=require('m56.metrics','measure');pairfn=require('m56.metrics','f_pair')
    from m56.catalog import _digest
    c=f04_trace
    reference={'method':'segment-map-normal-v1','route':c.fixture.routes['EGO'],
               'normals':((0.,1.,0.),),'refs':c.fixture.routes['EGO'].continuity}
    pair=pairfn('F04',f_policies.approve('F04','map:'+_digest(reference)))
    fixture=replace(c.fixture,pair=pair);frames=[]
    for f in c.frames:
        old=f.integrity['door_geometry'].limits
        f=frame_capability(f,fixture,'door_geometry','DOOR_GEOMETRY','calibrated-door-envelope-v1',
                          {'door_state':old['door_state'],'collider_envelope':old['collider_envelope']})
        frames.append(replace(f,integrity={**f.integrity,'metric_context':{
            'reference':pair.reference,'pair_hash':pair.hash,'map_reference':reference,
            'uncertainty':{'passage_time_s':F(0),'e_lat_peak_m':F(1,100)}}}))
    frames=rebind_trace(tuple(frames),fixture)
    values=measure(frames,pair,detect(frames,fixture))
    assert tuple(m.value for m in values)==(F(1,10),F(0))
    assert all(m.status=='VALID' and m.frames==(101,102,103) for m in values)


def test_f01_missing_frozen_end_is_unknown_not_physical_never_clear(require,f01_trace):
    detect=require('m56.metrics','detect_events');c=f01_trace
    assert 'WITNESS_UNKNOWN' in {e.name for e in detect(c.frames,c.fixture)}


def test_f05_unprojectable_gap_is_unknown_not_absent_queue(require,f05_trace,rebind_trace):
    detect=require('m56.metrics','detect_events');c=f05_trace
    frames=tuple(replace(f,actors=(replace(f.actors[0],pose=replace(f.actors[0].pose,x=40.),arc=F(30)),f.actors[1])) for f in c.frames[:21])
    assert 'WITNESS_UNKNOWN' in {e.name for e in detect(rebind_trace(frames,c.fixture),c.fixture)}


def test_naked_or_stale_predicate_is_not_observation(require,clear_frames):
    confirm=require('m56.metrics','confirm_hold')
    for packet in (True,{'value':True},clear_frames[0].integrity['predicates']['NPC_WHOLE_BODY_CLEAR']):
        frames=tuple(replace(f,integrity={'predicates':{'NPC_WHOLE_BODY_CLEAR':packet}}) for f in clear_frames)
        assert confirm(frames,'NPC_WHOLE_BODY_CLEAR',F(1,4)) is None
