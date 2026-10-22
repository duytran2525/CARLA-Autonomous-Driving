"""Exact synthetic reverse receipts; not calibration, native or dynamics evidence."""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

from m56.catalog import _digest
from m56.model import (ActorRecipe,CompiledFixture,Domain,Section,FrozenMetricPair,
    ControlPacket,EventRecord,ScriptState)
from tests.m56.response_cases import response_case
from tests.m56.source_cases import Sources


def reverse_case(root,mechanism='F06-ALT1',progress=F(0),speed=0.,reverse=False,phase='HOLD',stop_bound=True,rear_clearance=F(1),role='EGO',waiting_s=F(0),ground=True,reverse_region=None):
    s=Sources(root);c=response_case('F','B',events=(),speed=0.);geometry=s.source('geometry',{'scope':'synthetic flat straight corridor'})
    route=replace(c.response.route,continuity=(geometry,));body=replace(c.frame.actors[0].body,source=geometry)
    rows=tuple({'cause':cause,'after_event':event,'delay_s':F(0),'requires':()} for cause,event in (
        ('REVERSE','TRIGGER'),('STOPPING','REVERSE_STOPPING_BOUND'),('FORWARD_GEAR','REVERSE_STOP_CONFIRMED'),('FORWARD','FORWARD_GEAR_CONFIRMED')))
    response=replace(c.response,route=route,targets={'HOLD':F(0),'REVERSE':F(1,2),'STOPPING':F(0),'FORWARD_GEAR':F(0),'FORWARD':F(2)},
        phases={'category':'F','reverse':{'mechanism':mechanism,'policy_hash':'d'*64},
                'program':{'method':'ordered-event-program-v1','initial':'HOLD','transitions':rows}})
    if role=='NPC':
        rows=({'cause':'NPC_REVERSE_TARGET','after_event':'TRIGGER','delay_s':F(3),'requires':()},
              {'cause':'NPC_STOPPING','after_event':'NPC_REVERSE_STOPPING_BOUND','delay_s':F(0),'requires':()},
              {'cause':'NPC_FORWARD_GEAR','after_event':'NPC_REVERSE_STOP_CONFIRMED','delay_s':F(0),'requires':()},
              {'cause':'NPC_FORWARD','after_event':'NPC_FORWARD_GEAR_CONFIRMED','delay_s':F(0),'requires':()})
        script={'mechanism':'F06-ALT1','policy_hash':'d'*64,'release_mode':'FIXED_OBSERVED_CUE','release_s':F(3),'reverse_distance_m':F(2),'target_mps':F(1,2)}
        response=replace(response,actor_role='NPC',action_id='NPC_COMMON',
            targets={'NPC_PREPARATION':F(0),'NPC_REVERSE_TARGET':F(1,2),'NPC_STOPPING':F(0),'NPC_FORWARD_GEAR':F(0),'NPC_FORWARD':F(2)},
            phases={'category':'F','f_script':script,'program':{'method':'ordered-event-program-v1','initial':'NPC_PREPARATION','transitions':rows}})
    response=replace(response,hash=_digest({'actor_role':response.actor_role,'action_id':response.action_id,'route':route,
        'targets':response.targets,'profile':response.profile,'phases':response.phases}))
    region=tuple(product((0.,60.),(-2.,2.),(-1.,1.)))
    section=Section(tuple(product((10.,),(-2.,2.),(-1.,1.))),(1.,0.,0.),F(10),{})
    domain=Domain(section,section,section,section,(),{'category':'F','mechanism':mechanism,
        'reverse_regions':{role:reverse_region or region},'driving_regions':{'EGO':(region,),'NPC':(region,)}},(geometry,),'e'*64)
    pose=c.frame.actors[0].pose;poses={'EGO':pose,'NPC':replace(pose,x=8.)}
    actors=tuple(ActorRecipe(role,'vehicle.audi.a2',F(0),p,{}, {},F(40)) for role,p in poses.items())
    fixture=CompiledFixture('a'*64,'d'*64,actors,{},poses,{'EGO':route,'NPC':route},domain,None,{},(response,),
        FrozenMetricPair(('d_reserve_reverse_m','g_front_min_m'),('m','m'),('reverse_distance','min_front_gap'),
                         (('TRIGGER','NPC_REVERSE_TARGET_STOP_CONFIRMED'),)*2,'route:'+_digest(route),'f'*64,'APPROVED_PROPOSAL_NOT_READY'),(),geometry)
    recipe_hash=_digest({k:getattr(fixture,k) for k in ('candidate_hash','policy_hash','actors','environment','routes','domain','sections')})
    body_hash=_digest({k:getattr(body,k) for k in ('bbox_offset','rotation','extents','blueprint','attrs','physics')})
    hard=F(2 if mechanism=='F03' or role=='NPC' else 1)
    limits={'actor_role':role,'response_hash':response.hash,'route_hash':_digest(route),'body_hash':body_hash,
        'fixture_recipe_hash':recipe_hash,'target_mps':F(1,2),'gain':F(1,2),'throttle_cap':F(1,4),'brake_cap':F(3,10),
        'terminal_brake':F(3,10),'hard_limit_m':hard,'stopping_boundary_m':hard-F(1,5),
        'stopping_distance_bound_m':F(1,5),'maximum_reverse_speed_mps':F(1)}
    proof_ref=s.source('stop-bound',limits)
    proof=s.capability('REVERSE_STOP_BOUND','bounded-reverse-stop-v1',limits,(proof_ref,),F(0))
    fixture=replace(fixture,proofs=(proof,) if stop_bound else ())
    ground_recipe=s.source('ground-recipe',{'method':'recorded-ground-contact-v1','version':'synthetic-v1','limitations':'software receipt only; not contact calibration'})
    frames=[];steps=int(progress/F(1,40));remainder=progress-steps*F(1,40)
    distances=[F(0)]*(11+int(waiting_s*20))+[F(i,40) for i in range(1,steps+1)]
    if remainder:distances.append(progress)
    forward=ControlPacket(0.,0.,.3,False,False,False,1);back=ControlPacket(0.,0.,.3,False,True,True,-1)
    for i,distance in enumerate(distances):
        number=140+i;time=F(i,20);control=back if (i>10 or reverse or (role=='NPC' and i==10)) else forward
        station=F(4 if role=='EGO' else 8)-distance
        own=replace(c.frame.actors[0],role=role,id=1 if role=='EGO' else 2,body=body,pose=replace(poses[role],x=float(station)),arc=station,
                    velocity=(-.5 if distance>0 else 0.,0.,0.),readback=control)
        if i==len(distances)-1:own=replace(own,velocity=(-speed,0.,0.))
        peer_role='NPC' if role=='EGO' else 'EGO'
        peer=replace(own,role=peer_role,id=2 if role=='EGO' else 1,pose=poses[peer_role],arc=F(8 if role=='EGO' else 4),velocity=(0.,0.,0.),readback=forward)
        ego,npc=(own,peer) if role=='EGO' else (peer,own)
        if ground:
            ego,npc=tuple(ground_actor(s,fixture,a,number,time,ground_recipe) for a in (ego,npc))
        ref=s.source('observed-'+str(number),{'boot':'boot','world':'world','frame':number,'simtime':time,'actors':(ego,npc)},number,time)
        frames.append(replace(c.frame,frame=number,simtime=time,actors=(ego,npc),events=(),integrity={'frame_refs':(ref,)}))
    history=s.source('history',tuple(frames));frame=frames[-1]
    corridor={'fixture_recipe_hash':recipe_hash,'boot':'boot','world':'world','frame':frame.frame,'actor_id':1 if role=='EGO' else 2,
        'actors_hash':_digest(frame.actors),'response_hash':response.hash,'region_hash':_digest(reverse_region or region),'minimum_rear_clearance_m':rear_clearance}
    ref=s.source('rear-corridor',corridor,frame.frame,frame.simtime)
    clearance=s.capability('REVERSE_CORRIDOR','bounded-reverse-corridor-v1',corridor,(ref,),F(0))
    traffic={'boot':'boot','world':'world','frame':frame.frame,'actor_id':2,'status':'CLEAR'}
    traffic_ref=s.source('traffic',traffic,frame.frame,frame.simtime)
    frame=replace(frame,integrity={**frame.integrity,'reverse_history_ref':history,'reverse_corridor':clearance,
                                 'npc_controls':{**traffic,'witness_refs':(traffic_ref,)}})
    trigger_frame=frames[10];trigger=EventRecord('TRIGGER',trigger_frame.frame,trigger_frame.simtime,trigger_frame.integrity['frame_refs'])
    state=ScriptState(phase,trigger_frame.simtime,(trigger,))
    return SimpleNamespace(s=s,fixture=fixture,response=response,frame=frame,state=state,frames=tuple(frames),stop_proof=proof,
                           recipe_hash=recipe_hash,body_hash=body_hash,ground_recipe=ground_recipe)


def ground_actor(s,fixture,actor,number,time,recipe):
    limits={'fixture_hash':_digest(fixture),'boot':'boot','world':'world','frame':number,'actor_id':actor.id,
            'body_pose_hash':_digest({'body':actor.body,'pose':actor.pose}),'maximum_ground_error_m':F(0),
            'contact_method':'recorded-ground-contact-v1','recipe_ref':recipe}
    ref=s.source('ground-'+actor.role+'-'+str(number),limits,number,time)
    proof=s.capability('GROUND:'+actor.role,'recorded-ground-contact-v1',limits,(ref,),F(0),(recipe,))
    return replace(actor,ground=proof)


def terminal_observation(c,samples=11,forward=False,released=False):
    """Append genuine timestamped stationary packets, then optionally applied forward gear."""
    frames=list(c.frames);last=frames[-1]
    # STOP must already be observed at issue time; applied forward gear is
    # one further receiving frame, not the last sample that first proves STOP.
    terminal_samples=samples+int(forward)
    for i in range(1,terminal_samples+1):
        number=last.frame+i;time=last.simtime+F(i,20)
        gear_applied=forward and i==terminal_samples
        control=ControlPacket(0.,0.,.3,False,not gear_applied,not gear_applied,1 if gear_applied else -1)
        actors=tuple(replace(a,velocity=(0.,0.,0.),readback=control) if a.role==c.response.actor_role else a for a in last.actors)
        actors=tuple(ground_actor(c.s,c.fixture,a,number,time,c.ground_recipe) for a in actors)
        ref=c.s.source('terminal-'+str(i),{'boot':last.boot,'world':last.world,'frame':number,'simtime':time,'actors':actors},number,time)
        frames.append(replace(last,frame=number,simtime=time,actors=actors,events=(),integrity={'frame_refs':(ref,)}))
    history=c.s.source('terminal-history',tuple(frames));frame=frames[-1]
    old=c.frame.integrity['reverse_corridor'];limits={**old.limits,'frame':frame.frame,'actors_hash':_digest(frame.actors)}
    ref=c.s.source('terminal-corridor',limits,frame.frame,frame.simtime)
    corridor=c.s.capability(old.kind,old.method,limits,(ref,),old.uncertainty)
    events=()
    if released:
        name='NPC_STOP_CONFIRMED' if c.fixture.domain.topology['mechanism']=='F03' else 'NPC_REVERSE_TARGET_STOP_CONFIRMED'
        events=(EventRecord(name,frame.frame,frame.simtime,frame.integrity['frame_refs']),)
    traffic={'boot':frame.boot,'world':frame.world,'frame':frame.frame,'actor_id':2,'status':'CLEAR'}
    traffic_ref=c.s.source('terminal-traffic',traffic,frame.frame,frame.simtime)
    return replace(frame,events=events,integrity={**frame.integrity,'reverse_history_ref':history,'reverse_corridor':corridor,
        'npc_controls':{**traffic,'witness_refs':(traffic_ref,)}})


def forward_observations(c,terminal,samples=2):
    """Actual forward snapshots after terminal STOP/forward gear, without reverse-zone credit."""
    from m56.evidence import _read_trajectory
    frames=list(_read_trajectory(terminal.integrity['reverse_history_ref']))
    last=terminal
    for i in range(1,samples+1):
        number=terminal.frame+i;time=terminal.simtime+F(i,20)
        actors=tuple(replace(a,pose=replace(a.pose,x=float(F(a.pose.x)+F(1,10))),arc=a.arc+F(1,10),
                            velocity=(2.,0.,0.),readback=ControlPacket(.2,0.,0.,False,False,False,1))
                     if a.role==c.response.actor_role else a for a in last.actors)
        actors=tuple(ground_actor(c.s,c.fixture,a,number,time,c.ground_recipe) for a in actors)
        ref=c.s.source('forward-'+str(i),{'boot':last.boot,'world':last.world,'frame':number,'simtime':time,'actors':actors},number,time)
        last=replace(last,frame=number,simtime=time,actors=actors,events=(),integrity={'frame_refs':(ref,)})
        frames.append(last)
    history=c.s.source('forward-history',tuple(frames))
    traffic={'boot':last.boot,'world':last.world,'frame':last.frame,'actor_id':2,'status':'CLEAR'}
    ref=c.s.source('forward-traffic',traffic,last.frame,last.simtime)
    return replace(last,events=terminal.events,integrity={**last.integrity,'reverse_history_ref':history,
        'npc_controls':{**traffic,'witness_refs':(ref,)}})
