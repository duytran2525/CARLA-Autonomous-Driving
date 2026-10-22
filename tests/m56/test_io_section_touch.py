"""Certified on-plane observations are not already beyond the physical fence."""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product

import pytest


@pytest.mark.parametrize('endpoint',['TRIGGER','X_END'])
@pytest.mark.parametrize('defect',['none','uncertain_predecessor','touch_only'])
def test_certified_plane_touch_does_not_lose_next_actual_io_crossing(tmp_path,endpoint,defect):
    from tests.m56.o_cases import o_fixture
    from tests.m56.source_cases import Sources
    from m56.catalog import _digest
    from m56.model import ActorFrame,FrameRecord,ControlPacket,Section
    from m56.metrics import detect_events
    s=Sources(tmp_path/'sources');c=o_fixture(s);fixture=c.fixture
    if endpoint=='X_END':
        def plane(x):return Section(tuple(product((float(x),),(-1.75,5.25),(-1.,1.))),(1.,0.,0.),F(x)+10,{})
        fixture=replace(fixture,sections={**fixture.sections,'O_DECISION':plane(F(38,5)),'X':plane(F(9,2))})
    frames=[]
    uncertainty=F(1,100) if defect=='uncertain_predecessor' else F(0)
    for n,x in enumerate((5.75,6.,6.25,6.25 if defect=='touch_only' else 6.5),139):
        actors=tuple(ActorFrame(role,i,replace(fixture.poses[role],x=x if role=='EGO' else 24.),
             (5. if role=='EGO' and not (defect=='touch_only' and n==142) else 0.,0.,0.),
             c.body,F(x)+10 if role=='EGO' else F(34),{},(),
             ControlPacket(.2,0.,0.,False,False,False,1),None,1,True,None)
             for i,role in enumerate(('EGO','NPC'),1))
        f=FrameRecord('boot','world',n,F(n-100,20),F(1,20),actors,(),{})
        ref=s.source('frame'+str(n),{'boot':f.boot,'world':f.world,'frame':n,'simtime':f.simtime,'actors':actors},n,f.simtime)
        fields={'frame_refs':(ref,)}
        if frames:
            limits={'fixture_hash':_digest(fixture),'previous_actors':_digest(frames[-1].actors),
                    'actors':_digest(actors),'previous_frame':n-1,'frame':n}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),uncertainty)
        frames.append(replace(f,integrity=fields))
    events=detect_events(tuple(frames),fixture)
    event=next((e for e in events if e.name==endpoint),None)
    if defect!='none':
        assert event is None,tuple((e.name,e.frame) for e in events)
    else:
        assert event is not None and event.frame==142,tuple((e.name,e.frame) for e in events)
        assert {r.frame for r in event.witness_refs}=={141,142}
