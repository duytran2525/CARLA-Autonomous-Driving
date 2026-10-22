"""Real detector -> common F01 script, synthetic observations only."""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

import pytest


def f01_observations(root,defect=None):
    from tests.m56.source_cases import Sources
    from tests.m56.o_cases import o_fixture
    from tests.m56.test_f01_normative_response import f01_response
    from m56.catalog import _digest
    from m56.model import (ActorFrame,FrameRecord,CommandRecord,ControlPacket,Section,FrozenMetricPair)
    s=Sources(root);c=o_fixture(s)
    response,_=f01_response('NPC_COMMON','NPC');response=replace(response,route=c.fixture.routes['NPC'])
    response=replace(response,hash=_digest({k:getattr(response,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    def section(x):return Section(tuple(product((float(x),),(-1.75,1.75),(-1.,1.))),(1.,0.,0.),F(x)+10,{})
    pair=FrozenMetricPair(('a_peak_025','g_front_min_m'),('m/s^2','m'),('peak_decel_025','min_front_gap'),
        (('TRIGGER','F01_N_CLEAR'),)*2,'route:'+_digest(c.fixture.routes['EGO']),'e'*64,'APPROVED_PROPOSAL_NOT_READY')
    fixture=replace(c.fixture,responses=(response,),pair=pair,domain=replace(c.fixture.domain,
        topology={**c.fixture.domain.topology,'category':'F','mechanism':'F01'}),
        sections={'F01_BRAKE_START':section(F(81,5)),'F01_END':section(F(17))})
    frames=[];position=F(10);previous_speed=F(3)
    for i in range(122):
        number=100+i;time=F(i,20)
        speed=F(3) if i<=30 or i>=82 else max(F(0),F(3)-F(3,10)*(i-30))
        if i:
            position+=((previous_speed+speed)/2)*F(1,20) if i<=40 else speed*F(1,20)
        if defect=='velocity_lie' and 41<=i<=81:position+=F(1,100)
        if defect=='short_hold' and i>=80:
            speed=F(3)
            if i<82:position+=speed*F(1,20)
        phase='NOMINAL' if i<=30 else 'F01_BRAKE' if i<82 else 'NPC_RESTART'
        control=ControlPacket(0.,0.,.3,False,False,False,1) if phase=='F01_BRAKE' else ControlPacket(.2,0.,0.,False,False,False,1)
        command=CommandRecord(2,number-1,number,'CONTROL',F(0) if phase=='F01_BRAKE' else F(54,5),F(0),control,None,phase,response.hash)
        ego=ActorFrame('EGO',1,replace(c.fixture.poses['EGO'],x=0.),(0.,0.,0.),c.body,F(10),{},(),
            ControlPacket(0.,0.,.3,False,False,False,1),None,1,True,None)
        npc=replace(ego,role='NPC',id=2,pose=replace(ego.pose,x=float(position)),velocity=(float(speed),0.,0.),
            arc=F(float(position))+10,commands=(command,),readback=control,
            route_valid=not(defect=='unknown_route' and i==61))
        f=FrameRecord('boot','world',number,time,F(1,20),(ego,npc),(),{})
        ref=s.source('frame'+str(number),{'boot':f.boot,'world':f.world,'frame':number,'simtime':time,'actors':f.actors},number,time)
        fields={'frame_refs':(ref,)}
        if frames:
            limits={'fixture_hash':_digest(fixture),'previous_actors':_digest(frames[-1].actors),
                    'actors':_digest(f.actors),'previous_frame':number-1,'frame':number}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),F(0))
        frames.append(replace(f,integrity=fields));previous_speed=speed
    return SimpleNamespace(frames=tuple(frames),fixture=fixture,response=response)


def test_actual_marker_and_two_second_stationary_history_drive_common_npc_release(tmp_path):
    from m56.metrics import detect_events
    from m56.response import step_response
    from m56.model import ScriptState
    c=f01_observations(tmp_path/'sources');events=detect_events(c.frames,c.fixture)
    stable={e.name:e for e in events}
    assert stable['F01_BRAKE_MARKER'].frame==130
    assert stable['TRIGGER'].frame==135
    assert stable['NPC_F01_STOP_HOLD_CONFIRMED'].frame==181
    assert {r.frame for r in stable['NPC_F01_STOP_HOLD_CONFIRMED'].witness_refs}==set(range(141,182))
    state=ScriptState('NOMINAL',F(0),());commands=[]
    for f in c.frames:
        ref=f.integrity['frame_refs'][0]
        current=replace(f,events=tuple(e for e in events if e.frame==f.frame),integrity={**f.integrity,
            'npc_controls':{'boot':f.boot,'world':f.world,'frame':f.frame,'actor_id':2,'status':'CLEAR','witness_refs':(ref,)}})
        out=step_response(current,state,c.response);state=out.state;commands.append(out.command)
    assert next(x.frame for x in commands if x.cause=='F01_BRAKE')==130
    assert next(x.frame for x in commands if x.cause=='NPC_RESTART')==181
    assert all(x.target_kmh==0 for x in commands if 130<=x.frame<181)
    assert next(x.target_kmh for x in commands if x.cause=='NPC_RESTART')==F(54,5)


@pytest.mark.parametrize('defect',['velocity_lie','short_hold','unknown_route'])
def test_f01_stop_hold_cannot_use_velocity_only_short_or_unknown_route_history(tmp_path,defect):
    from m56.metrics import detect_events
    c=f01_observations(tmp_path/'sources',defect)
    names={e.name for e in detect_events(c.frames,c.fixture)}
    assert 'NPC_F01_STOP_HOLD_CONFIRMED' not in names
    assert 'N_MOVE' not in names
