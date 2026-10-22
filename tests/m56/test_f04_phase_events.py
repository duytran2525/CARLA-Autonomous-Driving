"""Actual door-envelope closure drives waiting policy, never RPC/timer credit."""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

import pytest


def f04_observations(root,defect=None):
    from tests.m56.test_f05_phase_events import f05_observations
    from tests.m56.test_f04_wait_normative_response import f04_ego_a
    from tests.m56.source_cases import Sources
    from m56.catalog import _digest
    from m56.model import FrozenMetricPair,CommandRecord,ControlPacket
    root.mkdir();physical=f05_observations(root/'physical',last=180)
    s=Sources(root/'door');s.refs.extend(physical.s.refs)
    ego,_=f04_ego_a();ego=replace(ego,route=physical.ego.route)
    ego=replace(ego,hash=_digest({k:getattr(ego,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    # NPC remains parked. Articulation is a separately sourced geometry channel,
    # not inferred from these longitudinal commands or the temporary NPC recipe.
    fixture=replace(physical.fixture,responses=(ego,physical.npc),
        pair=FrozenMetricPair(('passage_time_s','e_lat_peak_m'),('s','m'),('elapsed','map_lateral_peak'),
            (('TRIGGER','F04_END'),)*2,'map:'+'b'*64,'e'*64,'APPROVED_PROPOSAL_NOT_READY'),
        sections={'F04_END':physical.fixture.sections['F05_END']},
        domain=replace(physical.fixture.domain,topology={'category':'F','mechanism':'F04',
            'door_corridor':tuple(product((-10.,10.),(-1.,1.),(-1.,1.)))}))
    frames=[]
    for f in physical.frames:
        number=f.frame;e,n=f.actors
        opened=101<=number<162
        state='OPEN' if opened else 'CLOSED';intruding=opened
        if number>=162:
            if defect=='open_outside':state='OPEN'
            elif defect=='closed_intruding':intruding=True
            elif defect=='reopened' and number>=170:state='OPEN';intruding=True
        envelope=tuple(product((0.,1.),(.5,1.5) if intruding else (2.,3.),(-.5,.5)))
        hold=ControlPacket(0.,0.,.3,False,False,False,1)
        moving=number<=101
        command=CommandRecord(1,number-1,number,'CONTROL',F(36,5) if moving else F(0),F(0),
            None if moving else hold,None,'NOMINAL' if moving else 'WAIT',ego.hash)
        e=replace(e,pose=replace(e.pose,x=-6.5 if number==100 else -6.375),
            velocity=(2.,0.,0.) if moving else (0.,0.,0.),commands=(command,),readback=hold)
        f=replace(f,actors=(e,n),integrity={})
        ref=s.source('door-observed-'+str(number),{'boot':f.boot,'world':f.world,'frame':number,
            'simtime':f.simtime,'actors':f.actors},number,f.simtime)
        limits={'fixture_hash':_digest(fixture),'frame':number,'actors_hash':_digest(f.actors),
            'door_state':state,'collider_envelope':envelope}
        proof=s.capability('DOOR_GEOMETRY','calibrated-door-envelope-v1',limits,(ref,),F(0))
        fields={'door_geometry':proof}
        if defect=='rpc_only' and number>=162:fields={'door_rpc_success':True}
        frames.append(replace(f,integrity=fields))
    frames=s.bind_frames(tuple(frames),fixture)
    return SimpleNamespace(s=s,frames=frames,fixture=fixture,ego=ego)


def test_f04_actual_closed_clear_and_postcue_stop_drive_a_release(tmp_path):
    from m56.metrics import detect_events
    from m56.response import step_response
    from m56.model import ScriptState
    c=f04_observations(tmp_path/'sources');events=detect_events(c.frames,c.fixture)
    by_name={e.name:e for e in events}
    assert by_name['TRIGGER'].frame==101
    assert by_name['STOP_AFTER_TRIGGER'].frame==112
    assert by_name['DOOR_CLOSED_CLEAR_CONFIRMED'].frame==162
    assert {r.frame for r in by_name['DOOR_CLOSED_CLEAR_CONFIRMED'].witness_refs}=={161,162}
    state=ScriptState('NOMINAL',F(0),());commands=[]
    for frame in c.frames:
        out=step_response(replace(frame,events=tuple(e for e in events if e.frame==frame.frame)),state,c.ego)
        state=out.state;commands.append(out.command)
    assert all(x.target_kmh==0 for x in commands if 101<=x.frame<162)
    assert all(x.target_kmh==F(36,5) for x in commands if x.frame>=162)
    assert not any(e.name=='F04_END' for e in events)


def test_f04_reopened_door_revokes_current_producer_resume_not_only_whole_trace_eligibility(tmp_path):
    from m56.metrics import detect_events
    from m56.response import step_response
    from m56.model import ScriptState
    c=f04_observations(tmp_path/'sources','reopened');events=detect_events(c.frames,c.fixture)
    state=ScriptState('NOMINAL',F(0),())
    for frame in c.frames:
        observed=replace(frame,events=tuple(e for e in events if e.frame==frame.frame))
        if frame.frame==170:
            with pytest.raises(ValueError):step_response(observed,state,c.ego)
            break
        out=step_response(observed,state,c.ego);state=out.state
        if 162<=frame.frame<170:assert out.command.target_kmh==F(36,5)
    assert next(e.frame for e in events if e.name=='DOOR_CLOSED_CLEAR_CONFIRMED')==162


@pytest.mark.parametrize('permission',['current','missing','stale'])
def test_f04_wait_resumed_phase_cannot_use_latched_closed_clear_as_current_door_permission(permission):
    from tests.m56.response_cases import response_case
    from tests.m56.test_f04_wait_normative_response import f04_ego_a
    from m56.model import ScriptState
    from m56.response import step_response
    names=('TRIGGER','STOP_AFTER_TRIGGER','DOOR_CLOSED_CLEAR_CONFIRMED')
    c=response_case('F','A',events=(*names,'DOOR_CLOSED_CLEAR_CURRENT') if permission!='missing' else names,speed=0.)
    frame=c.frame
    if permission=='stale':
        ref=replace(c.ref,frame=99,time=F(19,20))
        event=replace(frame.events[-1],frame=99,time=F(19,20),witness_refs=(ref,))
        frame=replace(frame,events=(*frame.events[:-1],event))
    state=ScriptState('FORWARD',F(0),())
    if permission=='current':
        assert step_response(frame,state,f04_ego_a()[0]).command.target_kmh==F(36,5)
    else:
        with pytest.raises(ValueError):step_response(frame,state,f04_ego_a()[0])


def test_f04_reopened_door_revokes_closed_clear_trace_eligibility(tmp_path):
    from m56.metrics import detect_events
    c=f04_observations(tmp_path/'sources','reopened')
    events=detect_events(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='DOOR_CLOSED_CLEAR_CONFIRMED')==162
    assert any(e.name=='WITNESS_UNKNOWN' and e.frame==170 for e in events)
    assert not any(e.name=='F04_END' for e in events)


@pytest.mark.parametrize('defect',['rpc_only','open_outside','closed_intruding'])
def test_f04_rpc_or_one_half_of_closed_clear_cannot_release_wait(tmp_path,defect):
    from m56.metrics import detect_events
    c=f04_observations(tmp_path/'sources',defect)
    events=detect_events(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='TRIGGER')==101
    assert not any(e.name=='DOOR_CLOSED_CLEAR_CONFIRMED' for e in events)
