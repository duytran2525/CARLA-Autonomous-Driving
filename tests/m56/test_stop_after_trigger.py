"""Observed postcue STOP semantics; no command credit or native dynamics claim."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


@pytest.mark.parametrize('case',['valid','precue_only','short','rolling','foreign','offroute'])
def test_postcue_stop_requires_own_stationary_history_not_initialization(case,tmp_path):
    from tests.m56.reverse_cases import reverse_case
    from m56.catalog import _digest
    from m56.metrics import _post_trigger_stop
    c=reverse_case(tmp_path/'sources')
    trigger=c.state.events[0];frames=list(c.frames)
    count=10 if case=='short' else 11
    for i in range(1,count+1):
        number=150+i;time=F(1,2)+F(i,20);actors=[]
        for a in c.frame.actors:
            if a.role=='EGO':
                if case=='precue_only':a=replace(a,velocity=(1.,0.,0.))
                if case=='rolling':a=replace(a,pose=replace(a.pose,x=4.+i/10),arc=F(4)+F(i,10))
                if case=='foreign' and i==6:a=replace(a,id=99)
                if case=='offroute' and i==6:a=replace(a,route_valid=False)
            actors.append(a)
        frame=replace(c.frame,frame=number,simtime=time,actors=tuple(actors),events=(),integrity={})
        ref=c.s.source('stop-observed-'+str(number),{'boot':frame.boot,'world':frame.world,
            'frame':number,'simtime':time,'actors':frame.actors},number,time)
        limits={'fixture_hash':_digest(c.fixture),'previous_actors':_digest(frames[-1].actors),
            'actors':_digest(frame.actors),'previous_frame':number-1,'frame':number}
        proof=c.s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),F(0))
        frame=replace(frame,integrity={'frame_refs':(ref,),'continuous_geometry':proof})
        frames.append(frame)
    event=_post_trigger_stop(tuple(frames),c.fixture,trigger)
    if case=='valid':
        assert (event.name,event.frame,event.time)==('STOP_AFTER_TRIGGER',161,F(21,20))
        assert {r.frame for r in event.witness_refs}==set(range(151,162))
    else:
        assert event is None
