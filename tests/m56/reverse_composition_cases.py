"""Synthetic actual cue -> fixed hold -> bounded release, with source receipts."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

from m56.catalog import _digest
from m56.model import CommandRecord,ControlPacket,ScriptState,EventRecord
from tests.m56.reverse_cases import reverse_case,ground_actor


def npc_release_case(root,tamper=False,terminal=False):
    from m56.response import reverse_intent
    c=reverse_case(root,role='NPC',waiting_s=F(3))
    from tests.m56.source_cases import Sources
    s=Sources(c.s.root/'composition');s.refs.extend(c.s.refs)
    ego=replace(c.response,actor_role='EGO',action_id='A',targets={'HOLD':F(0)},
        phases={'category':'F','program':{'method':'ordered-event-program-v1','initial':'HOLD','transitions':()}},hash='e'*64)
    fixture=replace(c.fixture,responses=(ego,c.response))
    original=(replace(c.frames[0],frame=139,simtime=-F(1,20)),*c.frames)
    end=304 if terminal else 211
    original=(*original,*(replace(original[-1],frame=n,simtime=F(n-140,20)) for n in range(211,end+1)))
    history=[];incoming=None;state=ScriptState('NPC_PREPARATION',F(1,2),());trigger=None
    for frame in original:
        actors=[]
        for a in frame.actors:
            r=ego if a.role=='EGO' else c.response
            if a.role=='NPC' and incoming is not None:
                command=incoming
                if tamper and frame.frame==211:
                    command=replace(command,control=replace(command.control,throttle=.1))
                readback=command.control or ControlPacket(.2,0.,0.,False,False,False,1)
                a=replace(a,readback=readback,commands=(command,))
            else:
                command=CommandRecord(a.id,frame.frame-1,frame.frame,'CONTROL',F(0),F(0),a.readback,None,
                    'HOLD' if a.role=='EGO' else 'NPC_PREPARATION',r.hash)
                a=replace(a,commands=(command,))
            if a.role=='NPC' and frame.frame>=211:
                if frame.frame<=290:
                    station=F(8)-F(frame.frame-210,40);velocity=(-.5,0.,0.)
                elif frame.frame<=302:
                    station=F(6);velocity=(0.,0.,0.)
                else:
                    station=F(6)+F(frame.frame-302,10);velocity=(2.,0.,0.)
                a=replace(a,pose=replace(a.pose,x=float(station)),arc=station,velocity=velocity)
            actors.append(ground_actor(s,fixture,a,frame.frame,frame.simtime,c.ground_recipe))
        frame=replace(frame,actors=tuple(actors),events=(),integrity={})
        ref=s.source('release-observed-'+str(frame.frame),{'boot':frame.boot,'world':frame.world,
            'frame':frame.frame,'simtime':frame.simtime,'actors':frame.actors},frame.frame,frame.simtime)
        frame=replace(frame,integrity={'frame_refs':(ref,)})
        if frame.frame==150:
            trigger=EventRecord('TRIGGER',frame.frame,frame.simtime,(history[-1].integrity['frame_refs'][0],ref))
            limits={'fixture_hash':_digest(fixture),'frame':150,'previous_frame':149,
                    'actors_hash':_digest(frame.actors),'previous_actors_hash':_digest(history[-1].actors)}
            cue=s.capability('REVERSE_PREPARATION','frame-correlated-cue-v1',limits,(ref,),F(0))
            frame=replace(frame,integrity={**frame.integrity,'preparation_cue':cue})
            state=replace(state,events=(trigger,))
        history.append(frame)
        if trigger is not None and frame.frame<end:
            h=s.source('release-history-'+str(frame.frame),tuple(history))
            limits={**c.frame.integrity['reverse_corridor'].limits,'frame':frame.frame,'actors_hash':_digest(frame.actors)}
            corridor_ref=s.source('release-corridor-'+str(frame.frame),limits,frame.frame,frame.simtime)
            corridor=s.capability('REVERSE_CORRIDOR','bounded-reverse-corridor-v1',limits,(corridor_ref,),F(0))
            traffic={'boot':frame.boot,'world':frame.world,'frame':frame.frame,'actor_id':2,'status':'CLEAR'}
            traffic_ref=s.source('release-traffic-'+str(frame.frame),traffic,frame.frame,frame.simtime)
            frame=replace(frame,integrity={**frame.integrity,'reverse_history_ref':h,'reverse_corridor':corridor,
                'npc_controls':{**traffic,'witness_refs':(traffic_ref,)}})
            history[-1]=frame
            out=reverse_intent(frame,state,c.response,fixture)
            assert out.command.kind in ('REVERSE_HOLD','REVERSE','GEAR_TRANSITION','CONTROL'),out.state
            state=out.state;incoming=out.command
    frames=s.bind_frames(tuple(history),fixture)
    boundary=replace(frames[0],frame=138,simtime=-F(1,10),actors=tuple(replace(a,commands=()) for a in frames[0].actors))
    episode=s.episode(frames,fixture,boundary)
    return SimpleNamespace(episode=episode,fixture=fixture,trigger=trigger)
