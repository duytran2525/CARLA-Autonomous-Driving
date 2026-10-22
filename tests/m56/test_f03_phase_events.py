"""Observed downhill -> two-second issuing schedule -> real velocity/station STOP."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


def f03_observations(root,defect=None):
    from tests.m56.source_cases import Sources
    from tests.m56.reverse_cases import reverse_case
    from tests.m56.test_f03_normative_response import f03_response,reseal
    from m56.catalog import _digest
    from m56.model import FrozenMetricPair,ControlPacket,CommandRecord
    # Exact 3-4-5 synthetic grade; it is NOT a native allowed-map qualification.
    c=reverse_case(root/'base',mechanism='F03');s=Sources(root/'observations')
    s.refs.extend(c.s.refs)
    route=replace(c.response.route,transforms=(c.response.route.transforms[0],
        replace(c.response.route.transforms[-1],x=48.,z=36.)))
    response,_=f03_response();response=reseal(replace(response,route=route))
    pair=FrozenMetricPair(('d_reverse_m','g_front_min_m'),('m','m'),('reverse_distance','min_front_gap'),
        (('TRIGGER','NPC_STOP_CONFIRMED'),)*2,'route:'+_digest(c.response.route),'f'*64,'APPROVED_PROPOSAL_NOT_READY')
    fixture=replace(c.fixture,policy_hash='2'*64,routes={**c.fixture.routes,'NPC':route},responses=(response,),
        poses={**c.fixture.poses,'NPC':replace(c.fixture.poses['NPC'],x=8.,z=6.)},pair=pair,proofs=())
    frames=[]
    for number in range(100,159):
        time=F(number-100,20)
        station=F(10)-F(min(number-100,46),40)
        if defect=='rolling' and number>=147:station-=F(number-146,100)
        brake_frame=145 if defect=='early_brake' else 146
        control=ControlPacket(0.,0.,.3 if number>=brake_frame else 0.,False,False,False,1)
        command=CommandRecord(2,number-1,number,'CONTROL',F(0),F(0),control,None,
            'F03_BRAKE' if number>=brake_frame else 'UNPOWERED',response.hash)
        ego,npc=c.frames[0].actors
        npc=replace(npc,pose=replace(npc.pose,x=float(station*F(4,5)),z=float(station*F(3,5))),arc=None,
            velocity=(-.4,0.,-.3) if number<=146 else (0.,0.,0.),readback=control,commands=(command,),
            route_valid=not(defect=='unknown_route' and number==151))
        frame=replace(c.frames[0],frame=number,simtime=time,actors=(ego,npc),events=(),integrity={})
        ref=s.source('frame-'+str(number),{'boot':frame.boot,'world':frame.world,'frame':number,
                    'simtime':time,'actors':frame.actors},number,time)
        limits={'fixture_hash':_digest(fixture),'frame':number,'actors_hash':_digest(frame.actors),
                'gravity_along_reverse_mps2':F(1)}
        fields={'frame_refs':(ref,),'rollback':s.capability('ROLLBACK','unpowered-grade-motion-v1',limits,(ref,),F(0))}
        if frames:
            limits={'fixture_hash':_digest(fixture),'previous_actors':_digest(frames[-1].actors),
                    'actors':_digest(frame.actors),'previous_frame':number-1,'frame':number}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),F(0))
        frames.append(replace(frame,integrity=fields))
    return SimpleNamespace(s=s,frames=tuple(frames),fixture=fixture,response=response)


def test_f03_detector_and_producer_agree_on_issuing_two_seconds_then_applied_brake(tmp_path):
    from m56.metrics import detect_events
    from m56.response import step_response
    from m56.model import ScriptState
    root=tmp_path/'sources';root.mkdir();c=f03_observations(root)
    events=detect_events(c.frames,c.fixture);by_name={e.name:e for e in events}
    assert by_name['TRIGGER'].frame==105
    assert 'WITNESS_UNKNOWN' not in by_name,events
    assert by_name['NPC_STOP_CONFIRMED'].frame==157
    assert {r.frame for r in by_name['NPC_STOP_CONFIRMED'].witness_refs}==set(range(147,158))
    state=ScriptState('UNPOWERED',F(0),());commands=[]
    for frame in c.frames:
        packet={'boot':frame.boot,'world':frame.world,'frame':frame.frame,'actor_id':2,'status':'CLEAR'}
        ref=c.s.source('priority-'+str(frame.frame),packet,frame.frame,frame.simtime)
        frame=replace(frame,events=tuple(e for e in events if e.frame==frame.frame),integrity={**frame.integrity,
            'npc_controls':{**packet,'witness_refs':(ref,)}})
        out=step_response(frame,state,c.response);state=out.state;commands.append(out.command)
    assert next(c.frame for c in commands if c.cause=='F03_BRAKE')==145
    assert all(c.control.brake==0 and c.control.throttle==0 for c in commands if c.frame<145)
    assert all(c.control.brake==.3 and c.control.throttle==0 for c in commands if c.frame>=145)
    assert all(not c.control.reverse and c.control.gear==1 for c in commands)


@pytest.mark.parametrize('defect',['rolling','unknown_route'])
def test_f03_stop_event_needs_stationary_route_history_not_velocity_reporting(tmp_path,defect):
    from m56.metrics import detect_events
    root=tmp_path/'sources';root.mkdir();c=f03_observations(root,defect)
    events=detect_events(c.frames,c.fixture)
    assert 'TRIGGER' in {e.name for e in events}
    assert 'NPC_STOP_CONFIRMED' not in {e.name for e in events}


def test_f03_brake_applied_on_issuing_deadline_is_one_tick_early_not_valid_endpoint(tmp_path):
    from m56.metrics import detect_events
    root=tmp_path/'sources';root.mkdir();c=f03_observations(root,'early_brake')
    events=detect_events(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='TRIGGER')==105
    assert next(e.frame for e in events if e.name=='WITNESS_UNKNOWN')==145
    assert 'NPC_STOP_CONFIRMED' not in {e.name for e in events}
