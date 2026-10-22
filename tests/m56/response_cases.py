"""Literal response test packets, no native authority."""
from fractions import Fraction as F
from types import SimpleNamespace
from m56.model import (Transform6,DirectedRoute,BodyRecord,ActorFrame,FrameRecord,
    FrozenResponse,ScriptState,SourceRef,EventRecord)


def response_case(category='C',action='A',events=('TRIGGER',),speed=0.,role='EGO'):
    ref=SourceRef('synthetic://response','a'*64,1,'1','literal','SYNTHETIC_TEST',100,F(1))
    pose=Transform6(4.,0.,0.,0.,0.,0.)
    route=DirectedRoute((),(Transform6(0.,0.,0.,0.,0.,0.),Transform6(60.,0.,0.,0.,0.,0.)),
                        (F(0),F(60)),'b'*64,(ref,),F(40))
    body=BodyRecord((0.,0.,0.),(0.,0.,0.),(.5,.25,.25),(),'vehicle.audi.a2',{}, {},ref)
    actor=ActorFrame(role,1,pose,(speed,0.,0.),body,F(4),{},(),None,None,10,True,None)
    recorded=tuple(EventRecord(name,100,F(1),(ref,)) for name in events)
    frame=FrameRecord('boot','world',100,F(1),F(1,20),(actor,),recorded,{})
    nominal=F(2 if category=='L' else 4);yield_speed=F(1 if category=='L' else 2)
    targets={'NOMINAL':nominal,'WAIT_STOP_AND_CLEAR':F(0),'YIELD':yield_speed,'RESUME':nominal,'CHANGE':nominal}
    wait='WAIT_STOP_AND_CLEAR' if action=='A' else 'YIELD'
    transitions=({'cause':wait,'after_event':'TRIGGER','delay_s':F(0),'requires':()},
                 {'cause':'RESUME','after_event':'CLEAR_N_CONFIRMED','delay_s':F(0),
                  'requires':('STOP_AFTER_TRIGGER',) if action=='A' else ()})
    profile={'method':'quintic-arc-v1','segments':({'start_arc_m':F(0),'length_m':F(1),
                                                'start_offset_m':F(0),'end_offset_m':F(0)},)}
    response=FrozenResponse(role,action,route,targets,profile,{'category':category,
        'program':{'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':transitions}},'c'*64)
    return SimpleNamespace(frame=frame,state=ScriptState('NOMINAL',F(0),()),response=response,ref=ref)
