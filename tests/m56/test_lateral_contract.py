"""Frozen geometry/profile admission, not realized PID or native qualification."""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

import pytest


@pytest.fixture
def lateral_case():
    from m56.model import DirectedRoute,Transform6,FrozenResponse,SourceRef
    ref=SourceRef('synthetic://parallel','f'*64,1,'1','literal','SYNTHETIC_TEST')
    route=DirectedRoute((),(Transform6(0.,0.,0.,0.,0.,0.),Transform6(100.,0.,0.,0.,0.,0.)),(F(0),F(100)),'b'*64,(ref,),F(80))
    target=replace(route,transforms=tuple(replace(t,y=3.) for t in route.transforms))
    def profile(start,length,a,b):
        return {'method':'quintic-arc-v1','segments':({'start_arc_m':F(start),'length_m':F(length),'start_offset_m':F(a),'end_offset_m':F(b)},)}
    program={'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':(
        {'cause':'CHANGE','after_event':'SOURCE_CLEAR_CONFIRMED','delay_s':F(0),'requires':('LANE_CHANGE_PATH_CLEAR',)},
        {'cause':'TARGET','after_event':'TARGET_LANE_CONFIRMED','delay_s':F(0),'requires':('REFERENCE_MARKER:TARGET',)},)}
    response=FrozenResponse('EGO','B',route,{'NOMINAL':F(6),'CHANGE':F(6),'TARGET':F(6)},profile(10,18,0,3),
        {'program':program,'reference_switches':({'cause':'TARGET','event':'TARGET_LANE_CONFIRMED','marker_arc_m':F(28),
                                                'route':target,'profile':profile(28,1,0,0)},)},'a'*64)
    regions={'EGO_INITIAL':tuple(product((-1.,101.),(-1.75,1.75),(-1.,1.))),
             'EGO_TARGET':tuple(product((-1.,101.),(1.75,4.25),(-1.,1.)))}
    fixture=SimpleNamespace(domain=SimpleNamespace(topology={'category':'I','action_regions':regions}),
                            environment={'readiness':{'targets_mps':{'EGO':F(6),'NPC':F(5)}}})
    return SimpleNamespace(response=response,fixture=fixture,profile=profile,regions=regions)


def test_parallel_quintic_has_supported_continuity_width_and_curvature(require,lateral_case):
    validate=require('m56.response','_lateral_contract');c=lateral_case
    assert validate(c.response,c.fixture) is None


def test_source_roundtrip_preserves_lateral_reference_switch_admission(require,lateral_case):
    from m56.model import encode_record,decode_record,DirectedRoute
    from m56.catalog import _digest
    c=lateral_case;r=decode_record('FrozenResponse',encode_record(c.response))
    assert _digest(r)==_digest(c.response)
    reference=require('m56.response','_reference_response')(r,'TARGET')
    assert isinstance(reference.route,DirectedRoute)
    assert tuple(t.y for t in reference.route.transforms)==(3.,3.)
    assert require('m56.response','_lateral_contract')(r,c.fixture) is None


def test_source_mapping_route_cannot_smuggle_unknown_fields_into_a_switch(require,lateral_case):
    from m56.model import encode_record,decode_record
    raw=encode_record(lateral_case.response)
    raw['phases']['reference_switches'][0]['route']['unapproved_graphics_admission']=True
    r=decode_record('FrozenResponse',raw)
    with pytest.raises(ValueError,match='REFERENCE_SWITCH_INVALID'):
        require('m56.response','_reference_response')(r,'TARGET')


def test_lane_hold_before_profile_end_does_not_authorize_reference_reset(require,lateral_case):
    c=lateral_case;program=dict(c.response.phases['program']);rows=list(program['transitions'])
    rows[1]={**rows[1],'requires':()};program['transitions']=tuple(rows)
    r=replace(c.response,phases={**c.response.phases,'program':program})
    with pytest.raises(ValueError,match='LATERAL_MARKER_GUARD_MISSING'):
        require('m56.response','_lateral_contract')(r,c.fixture)


@pytest.mark.parametrize('fault',['length','separation','switch','bank','curved','acceleration','malformed_future'])
def test_unproven_lateral_profile_blocks_instead_of_command_success(require,lateral_case,fault):
    validate=require('m56.response','_lateral_contract');c=lateral_case;r=c.response
    if fault=='length':r=replace(r,profile=c.profile(10,6,0,3))
    elif fault=='separation':r=replace(r,profile=c.profile(10,18,0,2))
    elif fault=='switch':r=replace(r,phases={'program':r.phases['program']})
    elif fault=='bank':r=replace(r,route=replace(r.route,transforms=tuple(replace(t,roll=2.) for t in r.route.transforms)))
    elif fault=='curved':r=replace(r,route=replace(r.route,transforms=(r.route.transforms[0],replace(r.route.transforms[-1],y=1.))))
    elif fault=='acceleration':
        r=replace(r,profile=c.profile(10,18,0,4))
        c.fixture.domain.topology['action_regions']={**c.regions,'EGO_TARGET':tuple(product((-1.,101.),(2.25,5.75),(-1.,1.)))}
    else:r=replace(r,profile={'method':'quintic-arc-v1','segments':(*r.profile['segments'],{'start_arc_m':F(30)})})
    with pytest.raises(ValueError,match='LATERAL|REFERENCE|profile|segment'):
        validate(r,c.fixture)


def test_public_witness_consumer_rejects_wrong_lateral_scale(require,lateral_case):
    from m56.model import CommandRecord
    c=lateral_case
    bad=replace(c.response,profile=c.profile(10,6,0,3))
    fixture=SimpleNamespace(**vars(c.fixture),responses=(bad,))
    command=CommandRecord(1,99,100,'CONTROL',F(108,5),F(0),None,None,'NOMINAL',bad.hash)
    evidence=SimpleNamespace(raw=(SimpleNamespace(actors=(SimpleNamespace(role='EGO',commands=(command,)),)),))
    assert require('m56.evidence','_lateral_integrity')(evidence,fixture)==(('LATERAL_CONTRACT_INVALID',),())


def test_npc_cut_in_uses_its_own_parallel_reference_and_three_second_scale(require,lateral_case):
    c=lateral_case;r=c.response
    initial=replace(r.route,transforms=tuple(replace(t,y=-3.) for t in r.route.transforms))
    target=replace(r.route,transforms=tuple(replace(t,y=0.) for t in r.route.transforms))
    program={'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':(
        {'cause':'NPC_TARGET','after_event':'NPC_TARGET_LANE_CONFIRMED','delay_s':F(0),'requires':('REFERENCE_MARKER:NPC:NPC_TARGET',)},)}
    response=replace(r,actor_role='NPC',action_id='NPC_COMMON',route=initial,targets={'NOMINAL':F(5),'NPC_TARGET':F(5)},
        profile=c.profile(10,15,0,3),phases={'program':program,'reference_switches':(
            {'cause':'NPC_TARGET','event':'NPC_TARGET_LANE_CONFIRMED','marker_arc_m':F(25),'route':target,'profile':c.profile(25,1,0,0)},)})
    c.fixture.domain.topology['npc_regions']={'NPC_INITIAL':tuple(product((-1.,101.),(-4.25,-1.75),(-1.,1.))),
                                            'NPC_TARGET':c.regions['EGO_INITIAL']}
    assert require('m56.response','_lateral_contract')(response,c.fixture) is None


def test_reference_marker_is_actual_arc_observation_not_lane_hold(require,lateral_case):
    from m56.model import ActorFrame,FrameRecord,BodyRecord,SourceRef
    c=lateral_case;r=c.response;fixture=SimpleNamespace(responses=(r,))
    ref=SourceRef('synthetic://marker','f'*64,1,'1','literal','SYNTHETIC_TEST')
    body=BodyRecord((0.,0.,0.),(0.,0.,0.),(.5,.25,.25),(),'vehicle.audi.a2',{}, {},ref)
    frames=[]
    for i,x in enumerate((27.,27.5,28.,28.5)):
        time=F(i,20);source=replace(ref,frame=100+i,time=time)
        actor=ActorFrame('EGO',1,replace(r.route.transforms[0],x=x,y=3.),(6.,0.,0.),body,F(x),{},(),None,None,1,True,None)
        frames.append(FrameRecord('boot','world',100+i,time,F(1,20),(actor,),(),{'frame_refs':(source,)}))
    events=require('m56.metrics','_reference_marker_events')(tuple(frames),fixture)
    assert [(e.name,e.frame,e.time) for e in events]==[('REFERENCE_MARKER:TARGET',102,F(1,10))]
