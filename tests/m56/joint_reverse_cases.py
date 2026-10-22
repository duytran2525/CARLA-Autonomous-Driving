"""Joint source histories for semantic peer release; no native calibration/admission."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

from m56.catalog import _digest
from m56.model import CommandRecord,ControlPacket,ScriptState
from tests.m56.reverse_cases import reverse_case,ground_actor


def joint_reverse_case(root,mechanism='F06-ALT1',mode='gear',ego_delay_frames=0,gear_early=False,reserve_erosion=False):
    from tests.m56.test_f03_phase_events import f03_observations
    from tests.m56.test_f06_phase_events import f06_observations
    from m56.metrics import detect_events
    root.mkdir()
    if mechanism=='F03':
        (root/'physical').mkdir();physical=f03_observations(root/'physical')
        cue_number=105;peer_end=157
    else:
        physical=f06_observations(root/'physical');cue_number=150;peer_end=301
    c=reverse_case(root/'calibration',mechanism=mechanism)
    s=physical.s;s.refs.extend(c.s.refs)
    npc=physical.response
    key='f_script';npc=replace(npc,phases={**npc.phases,key:{**npc.phases[key],'policy_hash':c.fixture.policy_hash}})
    npc=replace(npc,hash=_digest({k:getattr(npc,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    poses={**c.fixture.poses,'NPC':next(a.pose for a in physical.frames[0].actors if a.role=='NPC')}
    actors=tuple(replace(a,pose=poses[a.role]) for a in c.fixture.actors)
    fixture=replace(c.fixture,poses=poses,actors=actors,routes={**c.fixture.routes,'NPC':npc.route},
        responses=(c.response,npc),pair=replace(physical.fixture.pair,reference='route:'+_digest(c.response.route)),proofs=())
    recipe_hash=_digest({k:getattr(fixture,k) for k in ('candidate_hash','policy_hash','actors','environment','routes','domain','sections')})
    limits={**c.stop_proof.limits,'fixture_recipe_hash':recipe_hash}
    ref=s.source('joint-stop-bound',limits)
    proof=s.capability('REVERSE_STOP_BOUND','bounded-reverse-stop-v1',limits,(ref,),F(0))
    fixture=replace(fixture,proofs=(proof,))
    source_by_frame={f.frame:f for f in physical.frames}
    last=peer_end if mode=='gear' else peer_end+3
    history=[]
    for number in range(physical.frames[0].frame,last+1):
        original=source_by_frame.get(number,physical.frames[-1]);time=F(number-physical.frames[0].frame,20)+physical.frames[0].simtime
        ego_origin=cue_number+ego_delay_frames
        distance=min(F(1),max(F(0),F(number-ego_origin,40)))
        forward=mode=='forward' and number>=peer_end+(0 if gear_early else 1)
        moving_forward=forward and number>peer_end+1
        erosion=min(F(1,4),max(F(0),F(number-220,40))) if reserve_erosion else F(0)
        station=F(4)-distance+erosion+(F(number-peer_end-1,10) if moving_forward else F(0))
        reverse=number>cue_number and not forward
        control=ControlPacket(.2 if moving_forward else 0.,0.,0. if moving_forward else .3,False,reverse,reverse,-1 if reverse else 1)
        speed=2. if moving_forward else .5 if reserve_erosion and 220<number<=230 else -.5 if ego_origin<number<=ego_origin+40 else 0.
        cause='FORWARD' if moving_forward else 'FORWARD_GEAR' if forward else 'REVERSE' if speed<0 else 'STOPPING' if reverse else 'HOLD'
        command=CommandRecord(1,number-1,number,'CONTROL' if forward or not reverse else 'REVERSE',
            F(36,5) if moving_forward else F(9,5) if speed<0 else F(0),F(0),control,None,cause,c.response.hash)
        ego=replace(c.frames[0].actors[0],pose=replace(c.fixture.poses['EGO'],x=float(station)),arc=station,
            velocity=(speed,0.,0.),commands=(command,),readback=control)
        peer=next(a for a in original.actors if a.role=='NPC')
        peer=replace(peer,commands=tuple(replace(x,response_hash=npc.hash,frame=number-1,next_frame=number) for x in peer.commands))
        own,peer=tuple(ground_actor(s,fixture,a,number,time,c.ground_recipe) for a in (ego,peer))
        frame=replace(original,frame=number,simtime=time,actors=(own,peer),events=(),integrity={})
        ref=s.source('joint-observed-'+str(number),{'boot':frame.boot,'world':frame.world,'frame':number,
            'simtime':time,'actors':frame.actors},number,time)
        fields={'frame_refs':(ref,)}
        if history:
            limits={'fixture_hash':_digest(fixture),'previous_actors':_digest(history[-1].actors),
                'actors':_digest(frame.actors),'previous_frame':number-1,'frame':number}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),F(0))
        if mechanism=='F03':
            limits={'fixture_hash':_digest(fixture),'frame':number,'actors_hash':_digest(frame.actors),'gravity_along_reverse_mps2':F(1)}
            fields['rollback']=s.capability('ROLLBACK','unpowered-grade-motion-v1',limits,(ref,),F(0))
        elif number==cue_number:
            limits={'fixture_hash':_digest(fixture),'frame':number,'previous_frame':number-1,
                'actors_hash':_digest(frame.actors),'previous_actors_hash':_digest(history[-1].actors)}
            fields['preparation_cue']=s.capability('REVERSE_PREPARATION','frame-correlated-cue-v1',limits,(ref,),F(0))
        history.append(replace(frame,integrity=fields))
    events=detect_events(tuple(history),fixture)
    name='NPC_STOP_CONFIRMED' if mechanism=='F03' else 'NPC_REVERSE_TARGET_STOP_CONFIRMED'
    trigger=next(e for e in events if e.name=='TRIGGER');endpoint=next(e for e in events if e.name==name)
    assert (trigger.frame,endpoint.frame)==(cue_number,peer_end),events
    frame=history[-1];history_ref=s.source('joint-history',tuple(history))
    limits={**c.frame.integrity['reverse_corridor'].limits,'fixture_recipe_hash':recipe_hash,
        'frame':frame.frame,'actors_hash':_digest(frame.actors)}
    ref=s.source('joint-corridor',limits,frame.frame,frame.simtime)
    corridor=s.capability('REVERSE_CORRIDOR','bounded-reverse-corridor-v1',limits,(ref,),F(0))
    frame=replace(frame,events=(endpoint,),integrity={**frame.integrity,'reverse_history_ref':history_ref,'reverse_corridor':corridor})
    state=ScriptState('FORWARD' if mode=='forward' else 'STOPPING',trigger.time,(trigger,))
    return SimpleNamespace(s=s,frame=frame,fixture=fixture,response=c.response,state=state,
        frames=tuple(history),trigger=trigger,endpoint=endpoint,stop_proof=proof,ground_recipe=c.ground_recipe,
        recipe_hash=recipe_hash)
