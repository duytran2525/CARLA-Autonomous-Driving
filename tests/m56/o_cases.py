"""Frozen synthetic O geometry/protocol; not native admission or selection."""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

from m56.catalog import _digest
from m56.model import (BodyRecord,Transform6,DirectedRoute,Section,Domain,FrozenMetricPair,
    FrozenResponse,CompiledFixture,ActorRecipe,ActorFrame,FrameRecord,CommandRecord,
    ControlPacket,EventRecord,ScriptState)
from tests.m56.source_cases import Sources


def o_fixture(s,shared_geometry=None,body_length=F(7,2)):
    geometry=shared_geometry or s.source('geometry',{'scope':'synthetic horizontal parallel lanes, no native qualification'})
    if shared_geometry is not None:s.refs.append(shared_geometry)
    body=BodyRecord((0.,0.,0.),(0.,0.,0.),(float(body_length/2),1.,.25),(),'vehicle.audi.a2',{}, {},geometry)
    destination=F(349,4)  # world77.25 + route origin10
    def route(y):
        return DirectedRoute((),(Transform6(-10.,y,0.,0.,0.,0.),Transform6(190.,y,0.,0.,0.,0.)),
            (F(0),F(200)),'b'*64,(geometry,),destination)
    routes={'EGO':route(0.),'NPC':route(0.)}
    def profile(start,length,a,b):
        return {'method':'quintic-arc-v1','segments':({'start_arc_m':F(start),'length_m':F(length),
            'start_offset_m':F(a),'end_offset_m':F(b)},)}
    def row(cause,event,guards=(),delay=F(0)):
        return {'cause':cause,'after_event':event,'requires':guards,'delay_s':delay}
    initial=tuple(product((-5.,185.),(-1.75,1.75),(-1.,1.)))
    target=tuple(product((-5.,185.),(1.75,5.25),(-1.,1.)))
    def section(x):
        return Section(tuple(product((float(x),),(-1.75,5.25),(-1.,1.))),(1.,0.,0.),F(x)+10,{})
    # Approved literal O scale: nominal6, estimated body lengths4.5 each, gap15,
    # Dlc18, returnstart42, Xdistance42+18+3.75=63.75. These are test
    # geometry, not a new real site/pose/fixture or outcome-selected marker.
    begin=F(163,10);out_end=begin+18;return_begin=begin+42;return_end=return_begin+18
    ego_a=FrozenResponse('EGO','A',routes['EGO'],
        {'SETTLE':F(0),'NOMINAL':F(6),'CHANGE':F(6),'TARGET':F(6),'RETURN':F(6),'HOME':F(6)},
        profile(begin,18,0,F(7,2)),{'category':'O','program':{'method':'ordered-event-program-v1','initial':'SETTLE',
            'transitions':(row('NOMINAL','CAPTURE_START',delay=F(21,20)),
                row('CHANGE','TRIGGER',('LANE_CHANGE_PATH_CLEAR',)),
                row('TARGET','TARGET_LANE_CONFIRMED',('REFERENCE_MARKER:TARGET',)),
                row('RETURN','RETURN_MARKER',('RETURN_CLEAR_CONFIRMED','RETURN_PATH_CLEAR')),
                row('HOME','RETURN_LANE_CONFIRMED',('REFERENCE_MARKER:HOME',)))},
            'reference_switches':(
                {'cause':'TARGET','event':'TARGET_LANE_CONFIRMED','marker_arc_m':out_end,'route':route(3.5),
                 'profile':profile(return_begin,18,0,-F(7,2))},
                {'cause':'HOME','event':'RETURN_LANE_CONFIRMED','marker_arc_m':return_end,'route':route(0.),
                 'profile':profile(return_end,1,0,0)})},'a'*64)
    ego_b=FrozenResponse('EGO','B',routes['EGO'],{'SETTLE':F(0),'NOMINAL':F(6),'FOLLOW':F(5,2)},profile(0,1,0,0),
        {'category':'O','program':{'method':'ordered-event-program-v1','initial':'SETTLE',
            'transitions':(row('NOMINAL','CAPTURE_START',delay=F(21,20)),row('FOLLOW','TRIGGER'))}},'f'*64)
    npc=FrozenResponse('NPC','NPC_COMMON',routes['NPC'],{'SETTLE':F(0),'NOMINAL':F(5,2)},profile(0,1,0,0),
        {'category':'O','program':{'method':'ordered-event-program-v1','initial':'SETTLE',
            'transitions':(row('NOMINAL','CAPTURE_START',delay=F(21,20)),)}},'c'*64)
    decision=F(63,10)+body_length/2-F(1,20)
    end_section=decision+F(255,4)
    return_section=F(483,10)+body_length/2-F(1,20)
    domain=Domain(section(decision),section(end_section),section(decision),section(end_section),(),
        {'category':'O','action_regions':{'EGO_INITIAL':initial,'EGO_TARGET':target},
         'driving_regions':{'EGO':(initial,target),'NPC':(initial,)}},(geometry,),'d'*64)
    reference={'method':'segment-map-normal-v1','route':routes['EGO'],'normals':((0.,1.,0.),),'refs':(geometry,)}
    pair=FrozenMetricPair(('v_mean_E','e_lat_peak'),('m/s','m'),('mean_speed','map_lateral_peak'),
        (('TRIGGER','X_END'),)*2,'map:'+_digest(reference),'e'*64,'APPROVED_PROPOSAL_NOT_READY')
    # A distinct positive software input has actual synthetic length3.5, below
    # the frozen4.5 estimate. The4.5 actual-body trace is retained as a blocked
    # marker-clearance case, never tuned into a scientific accepted fixture.
    npc_initial=F(927,40)+body_length-F(9,2)
    poses={'EGO':Transform6(0.,0.,0.,0.,0.,0.),'NPC':Transform6(float(npc_initial),0.,0.,0.,0.,0.)}
    actors=tuple(ActorRecipe(role,'vehicle.audi.a2',F(0),pose,{'kind':'synthetic'},{'kind':'synthetic'},destination)
                 for role,pose in poses.items())
    fixture=CompiledFixture('1'*64,'2'*64,actors,{'readiness':{'targets_mps':{'EGO':F(6),'NPC':F(5,2)},
        'markers_m':{'EGO':F(133,10),'NPC':npc_initial+10+F(11,8)}}},poses,routes,domain,None,
        {'O_DECISION':section(decision),'O_RETURN_START':section(return_section),
         'X':section(end_section),'DESTINATION':section(F(309,4))},(ego_a,ego_b,npc),pair,(),geometry)
    return SimpleNamespace(fixture=fixture,body=body,reference=reference,geometry=geometry,
        begin=begin,out_end=out_end,return_begin=return_begin,return_end=return_end,npc_initial=npc_initial)


def complete_o(root,action,shared_geometry=None,body_length=F(7,2)):
    from m56.metrics import detect_events
    from m56.response import desired_offset,step_response
    s=Sources(root);c=o_fixture(s,shared_geometry,body_length);fixture=c.fixture
    ego=next(r for r in fixture.responses if r.actor_role=='EGO' and r.action_id==action)
    npc=next(r for r in fixture.responses if r.actor_role=='NPC');responses=(ego,npc)
    hold=ControlPacket(0.,0.,.3,False,False,False,1);forward=ControlPacket(.2,0.,0.,False,False,False,1)
    frames=[]
    for i in range(331 if action=='A' else 641):
        number=100+i;time=F(i,20);actors=[]
        for identity,(role,r) in enumerate(zip(('EGO','NPC'),responses),1):
            if role=='EGO':
                x=F(3,10)*max(0,i-20)
                if action=='B' and i>41:x=F(63,10)+F(i-41,8)
                speed=0. if i<=20 else float(6 if action=='A' or i<=41 else F(5,2))
                station=x+10
                if action=='A' and station>c.out_end:
                    switched=replace(ego,route=fixture.responses[0].phases['reference_switches'][0]['route'],
                        profile=fixture.responses[0].phases['reference_switches'][0]['profile'])
                    y=F(7,2)+desired_offset(station,switched)
                else:y=desired_offset(station,ego)
            else:
                x=c.npc_initial+F(1,8)*max(0,i-20);y=F(0);station=x+10
                speed=0. if i<=20 else 2.5
            pose=replace(fixture.poses[role],x=float(x),y=float(y));control=hold if i<=20 else forward
            command=CommandRecord(identity,number-1,number,'CONTROL',F(0),F(0),control,None,'SETTLE',r.hash)
            actors.append(ActorFrame(role,identity,pose,(speed,0.,0.),c.body,station,{},(command,),control,None,1,True,None))
        f=FrameRecord('boot','world',number,time,F(1,20),tuple(actors),(),{})
        ref=s.source('prototype-'+str(number),{'boot':f.boot,'world':f.world,'frame':number,'simtime':time,'actors':f.actors},number,time)
        fields={'frame_refs':(ref,),
            'metric_context':{'reference':fixture.pair.reference,'pair_hash':fixture.pair.hash,'map_reference':c.reference,
                'uncertainty':{name:F(0) for name in fixture.pair.names}},
            'npc_controls':{'boot':f.boot,'world':f.world,'frame':number,'actor_id':2,'status':'CLEAR','witness_refs':(ref,)}}
        if frames:
            limits={'fixture_hash':_digest(fixture),'previous_actors':_digest(frames[-1].actors),
                'actors':_digest(f.actors),'previous_frame':number-1,'frame':number}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),F(0))
        common={'fixture_hash':_digest(fixture),'frame':number,'actors_hash':_digest(f.actors),'minimum_clearance_m':F(1)}
        regions=fixture.domain.topology['action_regions']
        fields['lane_change_path']=s.capability('LANE_CHANGE_PATH','bounded-lane-change-corridor-v1',
            {**common,'from_region_hash':_digest(regions['EGO_INITIAL']),'to_region_hash':_digest(regions['EGO_TARGET']),
             'route_hash':_digest(fixture.routes['EGO'])},(ref,),F(0))
        fields['return_path']=s.capability('RETURN_PATH','bounded-return-corridor-v1',common,(ref,),F(0))
        frames.append(replace(f,integrity=fields))
    events=detect_events(tuple(frames),fixture)
    required={'TRIGGER','X_END','DESTINATION_CONFIRMED'}
    if action=='A':required|={'TARGET_LANE_CONFIRMED','RETURN_MARKER','RETURN_CLEAR_CONFIRMED','RETURN_LANE_CONFIRMED',
                             'REFERENCE_MARKER:TARGET','REFERENCE_MARKER:HOME'}
    assert required<={e.name for e in events}, (sorted(required-{e.name for e in events}),
        tuple((e.name,e.frame,e.time) for e in events if e.name not in ('LANE_CHANGE_PATH_CLEAR','RETURN_PATH_CLEAR')))
    boundary=replace(frames[0],frame=99,simtime=-F(1,20),actors=tuple(replace(a,commands=()) for a in frames[0].actors))
    capture=EventRecord('CAPTURE_START',99,-F(1,20),(replace(c.geometry,frame=99,time=-F(1,20)),))
    states={r.actor_role:ScriptState('SETTLE',-F(1,20),(capture,)) for r in responses}
    commands={a.role:CommandRecord(a.id,99,100,'CONTROL',F(0),F(0),hold,None,'SETTLE',r.hash)
              for a,r in zip(boundary.actors,responses)}
    produced=[]
    for f in frames:
        actors=tuple(replace(a,commands=(replace(commands[a.role],control=a.readback),)) for a in f.actors)
        f=replace(f,actors=actors,events=tuple(e for e in events if e.frame==f.frame));produced.append(replace(f,events=()))
        for r in responses:
            out=step_response(f,states[r.actor_role],r);states[r.actor_role]=out.state;commands[r.actor_role]=out.command
    episode=s.complete(tuple(produced),fixture,boundary,120,131)
    return SimpleNamespace(episode=episode,fixture=fixture,sources=s)
