"""Full source-backed F04 SOFTWARE compositions. No native door/contact/dynamics claim.

All geometry/profiles/timings/destinations are frozen before each trace. The narrow
body and reviewed-envelope packets are distinct synthetic inputs, not blueprint
measurements, new selected catalog scenes, calibration or scientific acceptance.
"""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

from m56.catalog import _digest
from m56.model import (Transform6,ActorRecipe,Section,FrozenMetricPair,ActorFrame,FrameRecord,
                       CommandRecord,ControlPacket,EventRecord,ScriptState)
from tests.m56.source_cases import Sources


def f04_fixture(s,shared_geometry=None):
    from tests.m56.o_cases import o_fixture
    from tests.m56.test_f04_wait_normative_response import f04_ego_a
    from tests.m56.test_f04_spatial_normative_response import f04_ego_b
    from tests.m56.test_f04_npc_normative_response import f04_npc_response
    c=o_fixture(s,shared_geometry)
    routes={'EGO':replace(c.fixture.routes['EGO'],destination=F(40)),
            'NPC':replace(c.fixture.routes['NPC'],transforms=tuple(replace(t,y=-3.5) for t in c.fixture.routes['NPC'].transforms),destination=F(40))}
    a=replace(f04_ego_a()[0],route=routes['EGO']);b=replace(f04_ego_b()[0],route=routes['EGO'],profile={
        'method':'quintic-arc-v1','segments':(
            {'start_arc_m':F(56,5),'length_m':F(6),'start_offset_m':F(0),'end_offset_m':F(3,4)},
            {'start_arc_m':F(28),'length_m':F(6),'start_offset_m':F(3,4),'end_offset_m':F(0)},)})
    responses=[]
    for response in (a,b):
        program=response.phases['program'];row={'cause':'NOMINAL','after_event':'CAPTURE_START','delay_s':F(21,20),'requires':()}
        response=replace(response,targets={'SETTLE':F(0),**response.targets},phases={**response.phases,
            'program':{**program,'initial':'SETTLE','transitions':(row,*program['transitions'])}})
        responses.append(response)
    npc=replace(f04_npc_response()[0],route=routes['NPC']);rows=list(npc.phases['program']['transitions'])
    # Frozen initialization staging only; actual intrusion->close remains 3s.
    rows[0]={**rows[0],'delay_s':F(8,5)}
    npc=replace(npc,phases={**npc.phases,'program':{**npc.phases['program'],'transitions':tuple(rows)}})
    responses.append(npc)
    responses=tuple(replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')})) for r in responses)
    initial=tuple(product((-5.,185.),(-1.75,1.75),(-1.,1.)))
    parked=tuple(product((-5.,185.),(-5.25,-1.75),(-1.,1.)))
    def section(x):return Section(tuple(product((float(x),),(-1.75,1.75),(-1.,1.))),(1.,0.,0.),F(x)+10,{})
    poses={'EGO':Transform6(0.,0.,0.,0.,0.,0.),'NPC':Transform6(11.,-3.5,0.,0.,0.,0.)}
    actors=tuple(ActorRecipe(role,'vehicle.audi.a2',F(0),pose,{'kind':'synthetic'},{'kind':'synthetic'},F(40)) for role,pose in poses.items())
    reference={**c.reference,'route':routes['EGO']}
    pair=FrozenMetricPair(('passage_time_s','e_lat_peak_m'),('s','m'),('elapsed','map_lateral_peak'),
        (('TRIGGER','F04_END'),)*2,'map:'+_digest(reference),'e'*64,'APPROVED_PROPOSAL_NOT_READY')
    fixture=replace(c.fixture,actors=actors,poses=poses,routes=routes,G=None,responses=responses,pair=pair,
        sections={'F04_END':section(F(13)),'DESTINATION':section(F(30))},
        environment={'readiness':{'targets_mps':{'EGO':F(2),'NPC':F(0)},'markers_m':{'EGO':F(111,10),'NPC':F(21)}}},
        domain=replace(c.fixture.domain,topology={'category':'F','mechanism':'F04',
            'door_corridor':tuple(product((9.,12.),(-1.,1.),(-1.,1.))),
            'action_regions':{'EGO_INITIAL':initial},'driving_regions':{'EGO':(initial,),'NPC':(parked,)}}))
    return SimpleNamespace(fixture=fixture,body=replace(c.body,extents=(1.75,.5,.25)),reference=reference,geometry=c.geometry)


def complete_f04(root,action,shared_geometry=None):
    from m56.metrics import detect_events,_metric_station
    from m56.response import desired_offset,step_response
    s=Sources(root);c=f04_fixture(s,shared_geometry);fixture=c.fixture
    ego=next(r for r in fixture.responses if r.actor_role=='EGO' and r.action_id==action)
    npc=next(r for r in fixture.responses if r.actor_role=='NPC');responses=(ego,npc)
    hold=ControlPacket(0.,0.,.3,False,False,False,1);forward=ControlPacket(.2,0.,0.,False,False,False,1)
    frames=[]
    for number in range(100,511 if action=='A' else 681):
        time=F(number-100,20)
        if number<=120:x=F(0);speed=F(0)
        elif number<=132:x=F(number-120,10);speed=F(2)
        elif action=='A':
            x=F(6,5)+F(max(0,number-193),10);speed=F(0) if number<=193 else F(2)
        elif number<=593:x=F(6,5)+F(number-132,20);speed=F(1)
        else:x=F(97,4)+F(number-593,10);speed=F(2)
        arc=_metric_station((float(x),0.,0.),fixture.routes['EGO']);y=desired_offset(arc,ego)
        control=hold if speed==0 else forward;actors=[]
        for identity,(role,response) in enumerate(zip(('EGO','NPC'),responses),1):
            pose=replace(fixture.poses[role],x=float(x),y=float(y)) if role=='EGO' else fixture.poses[role]
            actual=control if role=='EGO' else hold
            cmd=CommandRecord(identity,number-1,number,'CONTROL',F(0),F(0),actual,None,
                'SETTLE' if role=='EGO' else 'NPC_DOOR_CLOSED_HOLD',response.hash)
            actors.append(ActorFrame(role,identity,pose,(float(speed),0.,0.) if role=='EGO' else (0.,0.,0.),c.body,
                arc if role=='EGO' else F(21),{},(cmd,),actual,None,1,True,None))
        f=FrameRecord('boot','world',number,time,F(1,20),tuple(actors),(),{})
        ref=s.source('prototype-'+str(number),{'boot':f.boot,'world':f.world,'frame':number,'simtime':time,'actors':f.actors},number,time)
        common={'fixture_hash':_digest(fixture),'frame':number,'actors_hash':_digest(f.actors)}
        opened=132<=number<=192
        fields={'frame_refs':(ref,),
            'metric_context':{'reference':fixture.pair.reference,'pair_hash':fixture.pair.hash,'map_reference':c.reference,
                'uncertainty':{name:F(0) for name in fixture.pair.names}},
            'npc_controls':{'boot':f.boot,'world':f.world,'frame':number,'actor_id':2,'status':'CLEAR','witness_refs':(ref,)},
            'door_geometry':s.capability('DOOR_GEOMETRY','calibrated-door-envelope-v1',{**common,
                'door_state':'OPEN' if opened else 'CLOSED',
                'collider_envelope':tuple(product((9.,12.),(-1.5,0.) if opened else (-4.,-3.),(-.5,.5)))},(ref,),F(0))}
        if frames:
            limits={**common,'previous_frame':number-1,'previous_actors':_digest(frames[-1].actors),'actors':_digest(f.actors)}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',
                {k:v for k,v in limits.items() if k!='actors_hash'},(ref,),F(0))
        region=fixture.domain.topology['action_regions']['EGO_INITIAL']
        path={**common,'from_region_hash':_digest(region),'to_region_hash':_digest(region),
              'route_hash':_digest(fixture.routes['EGO']),'minimum_clearance_m':F(1,4)}
        fields['lane_change_path']=s.capability('LANE_CHANGE_PATH','bounded-lane-change-corridor-v1',path,(ref,),F(0))
        fields['return_path']=s.capability('RETURN_PATH','bounded-return-corridor-v1',path,(ref,),F(0))
        frames.append(replace(f,integrity=fields))
    events=detect_events(tuple(frames),fixture)
    required={'TRIGGER','F04_END','DOOR_CLOSED_CLEAR_CONFIRMED','DESTINATION_CONFIRMED'}
    required|={'STOP_AFTER_TRIGGER'} if action=='A' else {'F04_OFFSET_CONFIRMED','F04_HOME_CONFIRMED','F04_RETURN_MARKER'}
    assert required<={e.name for e in events},sorted(required-{e.name for e in events})
    boundary=replace(frames[0],frame=99,simtime=-F(1,20),actors=tuple(replace(a,commands=()) for a in frames[0].actors),integrity={})
    capture_ref=s.source('capture-boundary',{'boot':boundary.boot,'world':boundary.world,'frame':99,'simtime':boundary.simtime,'actors':boundary.actors},99,boundary.simtime)
    packet={'boot':boundary.boot,'world':boundary.world,'frame':99,'actor_id':2,'status':'CLEAR'}
    traffic_ref=s.source('priority-boundary',packet,99,boundary.simtime)
    boundary=replace(boundary,integrity={'frame_refs':(capture_ref,),'npc_controls':{**packet,'witness_refs':(traffic_ref,)}})
    capture=EventRecord('CAPTURE_START',99,boundary.simtime,(capture_ref,))
    states={r.actor_role:ScriptState('SETTLE' if r.actor_role=='EGO' else 'NPC_DOOR_CLOSED_HOLD',boundary.simtime,(capture,)) for r in responses}
    commands={a.role:CommandRecord(a.id,99,100,'CONTROL',F(0),F(0),hold,None,states[a.role].phase,r.hash) for a,r in zip(boundary.actors,responses)}
    produced=[]
    for frame in frames:
        actors=tuple(replace(a,commands=(replace(commands[a.role],control=a.readback),)) for a in frame.actors)
        f=replace(frame,actors=actors,events=tuple(e for e in events if e.frame==frame.frame))
        produced.append(replace(f,events=()))
        for r in responses:
            out=step_response(f,states[r.actor_role],r);states[r.actor_role]=out.state;commands[r.actor_role]=out.command
    # Grounding adds a field to boundary actors. Preserve its exact observed
    # SourceRef bytes: Sources.complete sources the grounded boundary below.
    episode=s.complete(tuple(produced),fixture,boundary,120,131)
    return SimpleNamespace(episode=episode,fixture=fixture,sources=s)
