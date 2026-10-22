"""Source-backed F06 preparation and receiving-frame fixed release, not native proof."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


def f06_observations(root,defect=None,last=301):
    from tests.m56.reverse_cases import reverse_case
    from tests.m56.source_cases import Sources
    from m56.catalog import _digest
    from m56.model import CommandRecord,ControlPacket
    root.mkdir()
    c=reverse_case(root/'base',role='NPC');s=Sources(root/'observations');s.refs.extend(c.s.refs)
    frames=[]
    first=210 if defect=='early_release' else 211
    for number in range(139,last+1):
        time=F(number-140,20);distance=min(F(2),max(F(0),F(number-first+1,40)))
        forward=ControlPacket(0.,0.,.3,False,False,False,1)
        reverse=ControlPacket(.25 if first<=number<first+80 else 0.,0.,0. if first<=number<first+80 else .3,
            False,True,True,-1)
        actors=[]
        for a in c.frames[0].actors:
            offset=F(number-139,64) if defect=='rolling_preparation' and number<=150 else F(0)
            if a.role=='EGO':
                a=replace(a,pose=replace(a.pose,x=float(F(4)+offset)),arc=F(4)+offset,velocity=(0.,0.,0.),readback=forward)
            else:
                control=forward if number<150 else reverse
                command=CommandRecord(a.id,number-1,number,'REVERSE' if first<=number<first+80 else 'REVERSE_HOLD',
                    F(9,5) if first<=number<first+80 else F(0),F(0),control,None,
                    'NPC_REVERSE_TARGET' if first<=number<first+80 else 'NPC_PREPARATION',c.response.hash)
                a=replace(a,pose=replace(a.pose,x=float(F(8)-distance+offset)),arc=F(8)-distance+offset,
                    velocity=(-.5,0.,0.) if first<=number<first+80 else (0.,0.,0.),readback=control,commands=(command,))
            actors.append(a)
        f=replace(c.frames[0],frame=number,simtime=time,actors=tuple(actors),events=(),integrity={})
        ref=s.source('frame-'+str(number),{'boot':f.boot,'world':f.world,'frame':number,'simtime':time,'actors':f.actors},number,time)
        fields={'frame_refs':(ref,)}
        if frames:
            limits={'fixture_hash':_digest(c.fixture),'previous_actors':_digest(frames[-1].actors),
                    'actors':_digest(f.actors),'previous_frame':number-1,'frame':number}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),F(0))
        if number==150:
            limits={'fixture_hash':_digest(c.fixture),'frame':number,'previous_frame':number-1,
                    'actors_hash':_digest(f.actors),'previous_actors_hash':_digest(frames[-1].actors)}
            fields['preparation_cue']=s.capability('REVERSE_PREPARATION','frame-correlated-cue-v1',limits,(ref,),F(0))
        frames.append(replace(f,integrity=fields))
    return SimpleNamespace(s=s,frames=tuple(frames),fixture=c.fixture,response=c.response)


def test_f06_observed_preparation_and_fixed_issuing_release_reach_actual_two_metre_stop(tmp_path):
    from m56.metrics import detect_events
    c=f06_observations(tmp_path/'sources');events=detect_events(c.frames,c.fixture);by_name={e.name:e for e in events}
    assert by_name['TRIGGER'].frame==150
    assert by_name['NPC_REVERSE_TARGET_STOP_CONFIRMED'].frame==301
    assert {r.frame for r in by_name['NPC_REVERSE_TARGET_STOP_CONFIRMED'].witness_refs}==set(range(291,302))
    assert 'WITNESS_UNKNOWN' not in by_name


@pytest.mark.parametrize('defect',['early_release','rolling_preparation'])
def test_f06_metric_peer_endpoint_never_uses_early_applied_release_or_rolling_zero_velocity(tmp_path,defect):
    from m56.metrics import detect_events
    c=f06_observations(tmp_path/'sources',defect)
    names={e.name for e in detect_events(c.frames,c.fixture)}
    assert 'NPC_REVERSE_TARGET_STOP_CONFIRMED' not in names
    assert 'WITNESS_UNKNOWN' in names
    if defect=='rolling_preparation':assert 'TRIGGER' not in names
