"""Whole-road enclosure alone does not certify the intended lane after X."""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product

import pytest


def lane_enclosure(root,wide):
    from tests.m56.source_cases import Sources
    from tests.m56.o_cases import o_fixture
    from m56.catalog import _digest
    from m56.model import ActorFrame,FrameRecord,CommandRecord,ControlPacket,Section
    from m56.geometry import world_vertices
    s=Sources(root);c=o_fixture(s);fixture=c.fixture
    end=Section(tuple(product((4.4,),(-1.75,5.25),(-1.,1.))),(1.,0.,0.),F(float(4.4))+10,{})
    fixture=replace(fixture,sections={**fixture.sections,'X':end})
    ego=next(r for r in fixture.responses if r.actor_role=='EGO' and r.action_id=='B')
    npc=next(r for r in fixture.responses if r.actor_role=='NPC')
    control=ControlPacket(.2,0.,0.,False,False,False,1);frames=[]
    for number,x in enumerate((5.7,6.,6.3,6.6),139):
        actors=[]
        for identity,(role,response,position) in enumerate((('EGO',ego,x),('NPC',npc,25.)),1):
            command=CommandRecord(identity,number-1,number,'CONTROL',F(108,5) if role=='EGO' else F(9),F(0),control,None,
                                  'NOMINAL',response.hash)
            actors.append(ActorFrame(role,identity,replace(fixture.poses[role],x=position),(6. if role=='EGO' else 0.,0.,0.),
                c.body,F(position)+10,{},(command,),control,None,1,True,None))
        f=FrameRecord('boot','world',number,F(number-100,20),F(1,20),tuple(actors),(),{})
        ref=s.source('frame'+str(number),{'boot':f.boot,'world':f.world,'frame':number,'simtime':f.simtime,'actors':f.actors},number,f.simtime)
        fields={'frame_refs':(ref,)}
        if frames:
            limits={'fixture_hash':_digest(fixture),'previous_actors':_digest(frames[-1].actors),
                    'actors':_digest(f.actors),'previous_frame':number-1,'frame':number}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),F(0))
        frames.append(replace(f,integrity=fields))
    rows=[]
    for a,b in zip(frames,frames[1:]):
        actors={}
        for aa,bb in zip(a.actors,b.actors):
            vertices=(*world_vertices(aa.body,aa.pose),*world_vertices(bb.body,bb.pose))
            bounds=[(min(v[k] for v in vertices)-.1,max(v[k] for v in vertices)+.1) for k in range(3)]
            if wide and aa.role=='EGO' and b.frame>141:bounds[1]=(bounds[1][0],4.5)
            actors[aa.role]={'actor_id':aa.id,'response_hash':bb.commands[0].response_hash,
                'envelope':tuple(product(*bounds)),'reference_lateral_acceleration_bound_mps2':F(0)}
        rows.append({'boot':a.boot,'world':a.world,'first_frame':a.frame,'last_frame':b.frame,
            'first_actors_hash':_digest(a.actors),'last_actors_hash':_digest(b.actors),'actors':actors})
    intervals=s.source('intervals',rows)
    recipe={'method':'bounded-motion-envelope-v1','version':'synthetic-v1',
            'quantities':('continuous_body_enclosure','reference_lateral_acceleration'),'source_refs':(intervals,)}
    rr=s.source('recipe',recipe)
    proof=s.capability('CONTINUOUS_MOTION','bounded-motion-envelope-v1',
        {'fixture_hash':_digest(fixture),'trajectory_hash':_digest(tuple(frames)),'recipe_ref':rr,
         'recipe_review':s.review(recipe,'MOTION_RECIPE',(rr,intervals)),'intervals_ref':intervals},
        (intervals,),F(0),extra=(rr,))
    boundary=replace(frames[0],frame=138,simtime=frames[0].simtime-F(1,20))
    return s.episode(tuple(frames),fixture,boundary,{'motion_ref':proof}),fixture


@pytest.mark.parametrize('wide',[False,True])
def test_bound_continuous_post_x_enclosure_must_fit_intended_lane_not_both_lanes(tmp_path,wide):
    from m56.evidence import _motion_integrity
    from m56.metrics import detect_events
    e,fixture=lane_enclosure(tmp_path/'sources',wide)
    assert next(event.frame for event in detect_events(e.raw,fixture) if event.name=='X_END')==141
    invalid,unknown=_motion_integrity(e,fixture)
    assert not invalid
    assert unknown==(('CONTINUOUS_POST_END_LANE_UNPROVEN',) if wide else ())
