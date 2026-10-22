"""Joint F06 SOFTWARE producers; synthetic receipts are not native calibration.

Freeze both EGO actions, the common NPC, exact small body, readiness and separate
forward destination before observing either action. Each issuing observation has
independent EGO/NPC corridor authority. Literal receiving controls/poses below
are independent of reverse_intent; real producers must reproduce their intents.
"""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

from m56.catalog import _digest
from m56.model import (ActorRecipe,ActorFrame,FrameRecord,CommandRecord,ControlPacket,
                       ScriptState,Section)
from tests.m56.source_cases import Sources


def f06_fixture(s,shared=None):
    if shared is not None:
        s.refs.extend(shared.refs)
        return shared
    from tests.m56.reverse_cases import reverse_case
    from m56.response import _reverse_recipe_hash,_reverse_body_hash
    ego=reverse_case(s.root/'ego-template');npc=reverse_case(s.root/'npc-template',role='NPC')
    s.refs.extend((*ego.s.refs,*npc.s.refs))
    body=ego.frames[0].actors[0].body
    routes={'EGO':replace(ego.response.route,destination=F(10)),'NPC':ego.response.route}
    a=replace(ego.response,action_id='A',route=routes['EGO'],targets={'HOLD':F(0),'FORWARD':F(2)},
        phases={'category':'F','program':{'method':'ordered-event-program-v1','initial':'HOLD','transitions':(
            {'cause':'FORWARD','after_event':'NPC_REVERSE_TARGET_STOP_CONFIRMED','delay_s':F(0),'requires':()},)}})
    b=replace(ego.response,route=routes['EGO']);n=replace(npc.response,route=routes['NPC'],
        phases={**npc.response.phases,'preparation':{'method':'owned-reverse-preparation-v1',
            'request_kind':'REVERSE_PREPARATION_REQUEST'}})
    responses=tuple(replace(r,hash=_digest({k:getattr(r,k) for k in
        ('actor_role','action_id','route','targets','profile','phases')})) for r in (a,b,n))
    actors=tuple(ActorRecipe(role,'vehicle.audi.a2',F(0),pose,{'kind':'synthetic'},
        {'kind':'synthetic'},routes[role].destination) for role,pose in ego.fixture.poses.items())
    section=Section(tuple(product((10.,),(-2.,2.),(-1.,1.))),(1.,0.,0.),F(10),{})
    region=tuple(product((0.,60.),(-2.,2.),(-1.,1.)))
    fixture=replace(ego.fixture,actors=actors,routes=routes,responses=responses,proofs=(),
        sections={'DESTINATION':section},
        pair=replace(ego.fixture.pair,reference='route:'+_digest(routes['EGO'])),
        environment={'readiness':{'targets_mps':{'EGO':F(0),'NPC':F(0)},'markers_m':{'EGO':F(4),'NPC':F(8)}}},
        domain=replace(ego.fixture.domain,topology={'category':'F','mechanism':'F06-ALT1',
            'reverse_regions':{'EGO':region,'NPC':region},'driving_regions':{'EGO':(region,),'NPC':(region,)}}))
    proofs=[]
    for response,template in ((responses[1],ego.stop_proof),(responses[2],npc.stop_proof)):
        limits={**template.limits,'response_hash':response.hash,'route_hash':_digest(response.route),
            'body_hash':_reverse_body_hash(body),'fixture_recipe_hash':_reverse_recipe_hash(fixture)}
        ref=s.source('frozen-stop-'+response.actor_role,limits)
        proofs.append(s.capability('REVERSE_STOP_BOUND','bounded-reverse-stop-v1',limits,(ref,),F(0)))
    fixture=replace(fixture,proofs=tuple(proofs))
    return SimpleNamespace(fixture=fixture,body=body,refs=tuple(s.refs))


def _literal_command(role,action,number,response):
    """Hand-checked receiving recipe, not an expected value from the producer."""
    issue=number-1;hold=ControlPacket(0.,0.,.3,False,False,False,1)
    drive=ControlPacket(.2,0.,0.,False,False,False,1)
    if role=='EGO' and action=='A':
        cause='HOLD' if issue<301 else 'FORWARD'
        return CommandRecord(1,issue,number,'CONTROL',F(0) if issue<301 else F(36,5),F(0),
            hold if issue<301 else drive,None,cause,response.hash)
    first=150 if role=='EGO' else 210;bound=180 if role=='EGO' else 280
    initial='HOLD' if role=='EGO' else 'NPC_PREPARATION'
    reverse='REVERSE' if role=='EGO' else 'NPC_REVERSE_TARGET'
    stopping='STOPPING' if role=='EGO' else 'NPC_STOPPING'
    gear='FORWARD_GEAR' if role=='EGO' else 'NPC_FORWARD_GEAR'
    forward='FORWARD' if role=='EGO' else 'NPC_FORWARD'
    identity=1 if role=='EGO' else 2
    if role=='NPC' and issue==149:
        kind,target,control,cause='GEAR_TRANSITION',F(0),ControlPacket(0.,0.,.3,False,True,True,-1),initial
    elif issue<150:kind,target,control,cause='CONTROL',F(0),hold,initial
    elif issue<first:
        kind,target,control,cause='REVERSE_HOLD',F(0),ControlPacket(0.,0.,.3,False,True,True,-1),initial
    elif issue<bound:
        kind,target,cause='REVERSE',F(9,5),reverse
        control=ControlPacket(.25 if issue==first else 0.,0.,0.,False,True,True,-1)
    elif issue<301:
        kind,target,control,cause='REVERSE',F(0),ControlPacket(0.,0.,.3,False,True,True,-1),stopping
    elif issue==301:kind,target,control,cause='GEAR_TRANSITION',F(0),hold,gear
    else:kind,target,control,cause='CONTROL',F(36,5),drive,forward
    return CommandRecord(identity,issue,number,kind,target,F(0),control,None,cause,response.hash)


def joint_f06_producer(root,action='B',shared=None,last=None):
    from tests.m56.reverse_cases import ground_actor
    from m56.response import _reverse_recipe_hash,reverse_intent,step_response
    from m56.metrics import detect_events
    s=Sources(root);frozen=f06_fixture(s,shared);fixture=frozen.fixture
    ego=next(r for r in fixture.responses if r.actor_role=='EGO' and r.action_id==action)
    npc=next(r for r in fixture.responses if r.actor_role=='NPC');responses=(ego,npc)
    last=last if last is not None else (385 if action=='A' else 397)
    recipe=s.source('producer-ground-recipe',{'method':'recorded-ground-contact-v1','version':'1',
        'limitations':'synthetic source composition only; no native ground/dynamics/stop calibration'})
    raw=[]
    for number in range(99,last+1):
        time=F(number-100,20)
        ego_retreat=F(0) if action=='A' else min(F(1),max(F(0),F(number-150,40)))
        ego_forward=max(0,number-(301 if action=='A' else 302))
        positions={'EGO':F(4)-ego_retreat+F(ego_forward,10),
            'NPC':F(8)-min(F(2),max(F(0),F(number-210,40)))+F(max(0,number-302),10)}
        speeds={'EGO':F(2) if ego_forward else -F(1,2) if action=='B' and 151<=number<=190 else F(0),
            'NPC':F(2) if number>=303 else -F(1,2) if 211<=number<=290 else F(0)}
        actors=[]
        for identity,(role,response) in enumerate(zip(('EGO','NPC'),responses),1):
            command=_literal_command(role,action,number,response)
            pose=replace(fixture.poses[role],x=float(positions[role]))
            actor=ActorFrame(role,identity,pose,(float(speeds[role]),0.,0.),frozen.body,F(pose.x),{},
                () if number==99 else (command,),command.control,None,1,True,None)
            actors.append(ground_actor(s,fixture,actor,number,time,recipe))
        frame=FrameRecord('boot','world',number,time,F(1,20),tuple(actors),(),{})
        ref=s.source('observed-'+str(number),{'boot':frame.boot,'world':frame.world,'frame':number,
            'simtime':time,'actors':frame.actors},number,time)
        traffic={'boot':frame.boot,'world':frame.world,'frame':number,'actor_id':2,'status':'CLEAR'}
        priority=s.source('priority-'+str(number),traffic,number,time)
        fields={'frame_refs':(ref,),'npc_controls':{**traffic,'witness_refs':(priority,)},
            'metric_context':{'reference':fixture.pair.reference,'pair_hash':fixture.pair.hash,
                'directed_route':fixture.routes['EGO'],'uncertainty':{name:F(0) for name in fixture.pair.names}}}
        if raw:
            limits={'fixture_hash':_digest(fixture),'previous_frame':number-1,'frame':number,
                'previous_actors':_digest(raw[-1].actors),'actors':_digest(frame.actors)}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),F(0))
        if number==149:
            limits={'fixture_hash':_digest(fixture),'response_hash':npc.hash,'boot':frame.boot,'world':frame.world,
                'frame':number,'actor_id':2,'actors_hash':_digest(frame.actors)}
            ref=s.source('owned-preparation-request',limits,number,time)
            fields['preparation_request']=s.capability('REVERSE_PREPARATION_REQUEST','owned-reverse-preparation-v1',limits,(ref,),F(0))
        if number==150:
            limits={'fixture_hash':_digest(fixture),'previous_frame':149,'frame':150,
                'previous_actors_hash':_digest(raw[-1].actors),'actors_hash':_digest(frame.actors)}
            fields['preparation_cue']=s.capability('REVERSE_PREPARATION','frame-correlated-cue-v1',limits,(ref,),F(0))
        raw.append(replace(frame,integrity=fields))
    events=detect_events(tuple(raw),fixture)
    assert next(e.frame for e in events if e.name=='TRIGGER')==150,events
    states={r.actor_role:ScriptState(r.phases['program']['initial'],-F(1,20),()) for r in responses}
    produced=[]
    for i,frame in enumerate(raw):
        fields=dict(frame.integrity)
        if frame.frame>=149:
            prefix=tuple(replace(p,integrity={k:v for k,v in p.integrity.items() if k in
                ('frame_refs','continuous_geometry','preparation_cue')}) for p in raw[:i+1])
            fields['reverse_history_ref']=s.source('history-'+str(frame.frame),prefix)
            corridors={}
            for response in responses:
                if response.actor_role=='EGO' and action=='A':continue
                role=response.actor_role;actor=next(a for a in frame.actors if a.role==role)
                limits={'fixture_recipe_hash':_reverse_recipe_hash(fixture),'boot':frame.boot,'world':frame.world,
                    'frame':frame.frame,'actor_id':actor.id,'actors_hash':_digest(frame.actors),'response_hash':response.hash,
                    'region_hash':_digest(fixture.domain.topology['reverse_regions'][role]),'minimum_rear_clearance_m':F(1)}
                ref=s.source('corridor-'+role+'-'+str(frame.frame),limits,frame.frame,frame.simtime)
                corridors[role]=s.capability('REVERSE_CORRIDOR','bounded-reverse-corridor-v1',limits,(ref,),F(0))
            fields['reverse_corridors']=corridors
        observed=replace(frame,integrity=fields,events=tuple(e for e in events if e.frame==frame.frame))
        produced.append(replace(observed,events=()))
        if i+1==len(raw):continue
        for response in responses:
            role=response.actor_role;state=replace(states[role],events=tuple(e for e in events if e.frame<=frame.frame))
            bounded=(role=='NPC' and frame.frame>=149) or (role=='EGO' and action=='B' and frame.frame>=150)
            out=reverse_intent(observed,state,response,fixture) if bounded else step_response(observed,state,response)
            assert out.command.kind!='BLOCKED',(frame.frame,role,out.state)
            receiving=next(a for a in raw[i+1].actors if a.role==role)
            materialized=replace(out.command,control=receiving.readback) if out.command.control is None else out.command
            assert _digest(materialized)==_digest(receiving.commands[0]),(frame.frame,role,out.command,receiving.commands[0])
            states[role]=out.state
    return SimpleNamespace(frames=tuple(produced[1:]),boundary=produced[0],fixture=fixture,
        sources=s,frozen=frozen,events=events,states=states)


def complete_f06(root,action='B',shared=None):
    c=joint_f06_producer(root,action,shared)
    public=Sources(c.sources.root/'public');public.refs.extend(c.sources.refs)
    episode=public.complete(c.frames,c.fixture,c.boundary,120,131,preserve_ground=True)
    return SimpleNamespace(episode=episode,fixture=c.fixture,sources=public,frozen=c.frozen)
