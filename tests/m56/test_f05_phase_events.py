"""F05 actual body advance vs scheduled release; synthetic source packets only."""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

import pytest


def f05_observations(root,defect=None,last=202):
    from tests.m56.source_cases import Sources
    from tests.m56.o_cases import o_fixture
    from tests.m56.test_f05_normative_response import f05_response,f05_ego_a
    from m56.catalog import _digest
    from m56.model import ActorFrame,FrameRecord,CommandRecord,ControlPacket,Section,FrozenMetricPair
    s=Sources(root);c=o_fixture(s);npc,_=f05_response();ego,_=f05_ego_a()
    def bind(r,role):
        r=replace(r,route=c.fixture.routes[role])
        return replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    ego,npc=bind(ego,'EGO'),bind(npc,'NPC')
    end=Section(tuple(product((5.25,),(-1.75,1.75),(-1.,1.))),(1.,0.,0.),F(61,4),{})
    pair=FrozenMetricPair(('d_pre_move_m','t_queue_exit_s'),('m','s'),('forward_distance','elapsed'),
        (('TRIGGER','N_MOVE'),('N_MOVE','F05_END')),'route:'+_digest(c.fixture.routes['EGO']),'e'*64,'APPROVED_PROPOSAL_NOT_READY')
    fixture=replace(c.fixture,responses=(ego,npc),pair=pair,G=None,policy_hash='2'*64,
        domain=replace(c.fixture.domain,topology={'category':'F','mechanism':'F05','queue_gap_m':F(3),
            'nominal_front_t0_m':F(21,4)}),sections={'F05_END':end})
    frames=[]
    for number in range(100,last+1):
        release=179 if defect=='early_receiving_release' else 180
        time=F(number-100,20);distance=F(max(0,number-release),10)
        if defect=='never_moved':distance=F(0)
        position=float(distance)
        hold=ControlPacket(0.,0.,.3,False,False,False,1)
        move=ControlPacket(.2,0.,0.,False,False,False,1)
        moving=number>release
        ego_command=CommandRecord(1,number-1,number,'CONTROL',F(0),F(0),hold,None,'HOLD',ego.hash)
        npc_command=CommandRecord(2,number-1,number,'CONTROL',F(36,5) if moving else F(0),F(0),
            move if moving else hold,None,'NPC_QUEUE_FORWARD' if moving else 'NPC_QUEUE_HOLD',npc.hash)
        if defect=='rolling_queue':position+=float(F(number-100,64))
        ego_position=-6.5+float(F(number-100,64)) if defect=='rolling_queue' else -6.5
        e=ActorFrame('EGO',1,replace(c.fixture.poses['EGO'],x=ego_position),(0.,0.,0.),c.body,F(ego_position)+10,{},
            (ego_command,),hold,None,1,True,None)
        n=replace(e,role='NPC',id=2,pose=replace(e.pose,x=position),arc=F(position)+10,
            velocity=(2.,0.,0.) if moving and defect!='never_moved' else (0.,0.,0.),
            commands=(npc_command,),readback=move if moving else hold,
            route_valid=not(defect=='unknown_route' and number==199))
        f=FrameRecord('boot','world',number,time,F(1,20),(e,n),(),{})
        ref=s.source('frame'+str(number),{'boot':f.boot,'world':f.world,'frame':number,'simtime':time,'actors':f.actors},number,time)
        fields={'frame_refs':(ref,)}
        if frames:
            limits={'fixture_hash':_digest(fixture),'previous_actors':_digest(frames[-1].actors),
                    'actors':_digest(f.actors),'previous_frame':number-1,'frame':number}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),
                F(1,100) if defect=='uncertain_endpoint' else F(0))
        frames.append(replace(f,integrity=fields))
    return SimpleNamespace(s=s,frames=tuple(frames),fixture=fixture,ego=ego,npc=npc)


def test_f05_actual_whole_body_advance_drives_a_not_release_or_first_move(tmp_path):
    from m56.metrics import detect_events
    from m56.response import step_response
    from m56.model import ScriptState
    c=f05_observations(tmp_path/'sources');events=detect_events(c.frames,c.fixture);by_name={e.name:e for e in events}
    assert by_name['TRIGGER'].frame==120
    assert by_name['N_MOVE'].frame==186
    assert by_name['NPC_ADVANCE_2M_CONFIRMED'].frame==200
    assert {r.frame for r in by_name['NPC_ADVANCE_2M_CONFIRMED'].witness_refs}==set(range(120,201))
    commands=[];state=ScriptState('HOLD',F(0),())
    for f in c.frames:
        out=step_response(replace(f,events=tuple(e for e in events if e.frame==f.frame)),state,c.ego)
        commands.append(out.command);state=out.state
    assert all(x.target_kmh==0 for x in commands if x.frame<200)
    assert next(x.frame for x in commands if x.target_kmh>0)==200
    assert all(x.target_kmh==F(36,5) for x in commands if x.frame>=200)


@pytest.mark.parametrize('defect,last',[(None,199),('never_moved',202),('unknown_route',202),('uncertain_endpoint',200)])
def test_f05_two_metre_permission_needs_complete_projectable_body_history(tmp_path,defect,last):
    from m56.metrics import detect_events
    c=f05_observations(tmp_path/'sources',defect,last)
    events=detect_events(c.frames,c.fixture)
    assert 'TRIGGER' in {e.name for e in events}
    assert 'NPC_ADVANCE_2M_CONFIRMED' not in {e.name for e in events}


def test_f05_npc_motion_cannot_be_received_on_fixed_issuing_release_frame(tmp_path):
    from m56.metrics import detect_events
    c=f05_observations(tmp_path/'sources','early_receiving_release')
    events=detect_events(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='TRIGGER')==120
    assert not any(e.name in ('N_MOVE','NPC_ADVANCE_2M_CONFIRMED') for e in events)
    assert any(e.name=='WITNESS_UNKNOWN' for e in events)


def test_f05_initial_queue_stop_is_not_zero_velocity_over_rolling_bodies(tmp_path):
    from m56.metrics import detect_events
    c=f05_observations(tmp_path/'sources','rolling_queue',last=180)
    events=detect_events(c.frames,c.fixture)
    assert 'TRIGGER' not in {e.name for e in events}
    assert 'N_MOVE' not in {e.name for e in events}
    assert 'NPC_ADVANCE_2M_CONFIRMED' not in {e.name for e in events}
