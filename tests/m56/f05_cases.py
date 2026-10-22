"""Full F05 SOFTWARE queue compositions, not native stopping/contact qualification.

The source-reviewed .8m braking boundary/.2m remaining stop proposal is an exact
synthetic certificate, NOT a measurement of stock PID stopping performance. All
routes/body/initial poses/sections, validation readiness131 and common3s release
are frozen before the trace. No selected catalog entry or scientific retry.
"""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

from m56.catalog import _digest
from m56.model import (ActorRecipe,ActorFrame,FrameRecord,CommandRecord,ControlPacket,
                       Section,FrozenMetricPair,ScriptState)
from tests.m56.source_cases import Sources


def f05_fixture(s,shared=None):
    if shared is not None:
        s.refs.extend(shared.refs)
        return shared
    from tests.m56.o_cases import o_fixture
    from tests.m56.test_f05_normative_response import f05_ego_a,f05_response
    from tests.m56.test_f05_creep_normative_response import f05_ego_b
    from m56.response import _reverse_recipe_hash,_reverse_body_hash
    c=o_fixture(s);routes={k:replace(r,destination=F(19)) for k,r in c.fixture.routes.items()}
    a=replace(f05_ego_a()[0],route=routes['EGO']);b=replace(f05_ego_b()[0],route=routes['EGO'])
    npc=replace(f05_response()[0],route=routes['NPC'])
    responses=tuple(replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')})) for r in (a,b,npc))
    region=tuple(product((-10.,185.),(-1.75,1.75),(-1.,1.)))
    def section(x):return Section(tuple(product((float(x),),(-1.75,1.75),(-1.,1.))),(1.,0.,0.),F(x)+10,{})
    poses={'EGO':replace(c.fixture.poses['EGO'],x=-6.5),'NPC':replace(c.fixture.poses['NPC'],x=0.,y=0.)}
    actors=tuple(ActorRecipe(role,'vehicle.audi.a2',F(0),pose,{'kind':'synthetic'},{'kind':'synthetic'},F(19)) for role,pose in poses.items())
    pair=FrozenMetricPair(('d_pre_move_m','t_queue_exit_s'),('m','s'),('forward_distance','elapsed'),
        (('TRIGGER','N_MOVE'),('N_MOVE','F05_END')),'route:'+_digest(routes['EGO']),'e'*64,'APPROVED_PROPOSAL_NOT_READY')
    fixture=replace(c.fixture,actors=actors,poses=poses,routes=routes,G=None,responses=responses,pair=pair,proofs=(),
        environment={'readiness':{'targets_mps':{'EGO':F(0),'NPC':F(0)},'markers_m':{'EGO':F(7,2),'NPC':F(10)}},
                     'validation_start':'recorded-readiness-start-v1'},
        sections={'F05_END':section(F(21,4)),'DESTINATION':section(F(9))},
        domain=replace(c.fixture.domain,topology={'category':'F','mechanism':'F05','queue_gap_m':F(3),
            'nominal_front_t0_m':F(21,4),'driving_regions':{'EGO':(region,),'NPC':(region,)}}))
    stock={'lateral':{'K_P':F(39,20),'K_I':F(1,20),'K_D':F(1,5)},
           'longitudinal':{'K_P':F(1),'K_I':F(1,20),'K_D':F(0)},'dt_s':F(1,20),
           'max_throttle':F(3,4),'max_brake':F(3,10),'max_steering':F(4,5)}
    limits={'actor_role':'EGO','response_hash':responses[1].hash,'route_hash':_digest(routes['EGO']),
        'body_hash':_reverse_body_hash(c.body),'fixture_recipe_hash':_reverse_recipe_hash(fixture),'stock_config_hash':_digest(stock),
        'target_mps':F(1,2),'terminal_brake':F(3,10),'hard_limit_m':F(1),'stopping_boundary_m':F(4,5),
        'stopping_distance_bound_m':F(1,5),'maximum_forward_speed_mps':F(1,2)}
    ref=s.source('stop-bound',limits);proof=s.capability('CREEP_STOP_BOUND','bounded-forward-creep-stop-v1',limits,(ref,),F(0))
    fixture=replace(fixture,proofs=(proof,))
    return SimpleNamespace(fixture=fixture,body=c.body,refs=tuple(s.refs))


def complete_f05(root,action,shared=None):
    from m56.metrics import detect_events
    from m56.response import step_response
    from tests.m56.reverse_cases import ground_actor
    s=Sources(root);c=f05_fixture(s,shared);fixture=c.fixture
    ego=next(r for r in fixture.responses if r.actor_role=='EGO' and r.action_id==action)
    npc=next(r for r in fixture.responses if r.actor_role=='NPC');responses=(ego,npc)
    ref=s.source('creep-fixture',fixture)
    ground_recipe=s.source('producer-ground-recipe',{'method':'recorded-ground-contact-v1','version':'1',
        'limitations':'synthetic only; no native stock stopping, body or contact calibration'})
    hold=ControlPacket(0.,0.,.3,False,False,False,1);forward=ControlPacket(.2,0.,0.,False,False,False,1)
    raw=[]
    for number in range(100,400 if action=='A' else 376):
        time=F(number-100,20);npc_distance=F(max(0,number-191),10)
        if action=='A':progress=F(max(0,number-211),10);speed=F(2) if number>=212 else F(0)
        elif number<=131:progress=F(0);speed=F(0)
        elif number<=197:
            progress=F(min(number-131,40),40);speed=F(1,2) if number<=171 else F(0)
        else:progress=F(1)+F(number-197,10);speed=F(2)
        ego_cause='HOLD' if number<=131 else 'CREEP' if action=='B' and number<=162 else 'CREEP_STOP' if action=='B' and number<=197 else 'FORWARD'
        if action=='A':ego_cause='HOLD' if number<=211 else 'FORWARD'
        ego_control=hold if speed==0 or (action=='B' and 163<=number<=197) else forward
        npc_control=hold if number<=191 else forward
        actors=[]
        for identity,(role,response,position,velocity,control,cause) in enumerate((
            ('EGO',ego,-F(13,2)+progress,speed,ego_control,ego_cause),
            ('NPC',npc,npc_distance,F(2) if number>=192 else F(0),npc_control,'NPC_QUEUE_HOLD' if number<=191 else 'NPC_QUEUE_FORWARD')),1):
            command=CommandRecord(identity,number-1,number,'CONTROL',F(18,5)*response.targets[cause],F(0),control,None,cause,response.hash)
            actor=ActorFrame(role,identity,replace(fixture.poses[role],x=float(position)),(float(velocity),0.,0.),c.body,
                F(float(position))+10,{},(command,),control,None,1,True,None)
            actors.append(ground_actor(s,fixture,actor,number,time,ground_recipe))
        frame=FrameRecord('boot','world',number,time,F(1,20),tuple(actors),(),{})
        observed=s.source('producer-observed-'+str(number),{'boot':frame.boot,'world':frame.world,'frame':number,'simtime':time,'actors':frame.actors},number,time)
        fields={'frame_refs':(observed,),'metric_context':{'reference':fixture.pair.reference,'pair_hash':fixture.pair.hash,
            'directed_route':fixture.routes['EGO'],'uncertainty':{name:F(0) for name in fixture.pair.names}},
            'npc_controls':{'boot':frame.boot,'world':frame.world,'frame':number,'actor_id':2,'status':'CLEAR','witness_refs':(observed,)}}
        if number==131:fields['validation_start']=s.capability('VALIDATION_START','recorded-readiness-start-v1',
            {'fixture_hash':_digest(fixture),'frame':number,'actors_hash':_digest(frame.actors)},(observed,),F(0))
        if action=='B':
            limits={'fixture_recipe_hash':_reverse_recipe_hash_for(fixture),'boot':frame.boot,'world':frame.world,'frame':number,'actor_id':1,
                'actors_hash':_digest(frame.actors),'response_hash':ego.hash,'route_hash':_digest(ego.route),'minimum_forward_clearance_m':F(1)}
            path=s.source('producer-queue-path-'+str(number),limits,number,time)
            fields.update(queue_path=s.capability('QUEUE_PATH','bounded-queue-exit-corridor-v1',limits,(path,),F(0)),
                          creep_fixture_ref=ref,creep_history_ref=ref)  # Replaced by a real prefix below.
        raw.append(replace(frame,integrity=fields))
    frames=s.bind_frames(tuple(raw),fixture)
    events=detect_events(frames,fixture)
    required={'TRIGGER','N_MOVE','NPC_ADVANCE_2M_CONFIRMED','F05_END','DESTINATION_CONFIRMED'}
    if action=='B':required|={'EGO_CREEP_STOPPING_BOUND','EGO_CREEP_STOP_CONFIRMED','QUEUE_CLEAR_CONFIRMED'}
    assert required<={e.name for e in events},sorted(required-{e.name for e in events})
    states={r.actor_role:ScriptState('HOLD' if r.actor_role=='EGO' else 'NPC_QUEUE_HOLD',-F(1,20),()) for r in responses}
    produced=[frames[0]]
    for i,frame in enumerate(frames):
        observed=replace(frame,events=tuple(e for e in events if e.frame==frame.frame))
        commands={}
        for response in responses:
            out=step_response(observed,states[response.actor_role],response);states[response.actor_role]=out.state
            commands[response.actor_role]=out.command
        if i+1<len(frames):
            receiving=frames[i+1]
            actors=tuple(replace(a,commands=(replace(commands[a.role],control=a.readback),)) for a in receiving.actors)
            # Literal receiving recipes independently pin times/causes. A broken
            # producer fails HERE, before sources/public verdict can mask it.
            assert _digest(actors)==_digest(receiving.actors),(frame.frame,commands)
            produced.append(replace(receiving,actors=actors))
    boundary=replace(frames[0],frame=99,simtime=-F(1,20),integrity={},actors=tuple(replace(a,commands=()) for a in frames[0].actors))
    packet={'boot':boundary.boot,'world':boundary.world,'frame':99,'actor_id':2,'status':'CLEAR'}
    traffic=s.source('producer-boundary-priority',packet,99,boundary.simtime)
    boundary=replace(boundary,integrity={'npc_controls':{**packet,'witness_refs':(traffic,)}})
    final=Sources(s.root/'public');final.refs.extend(s.refs)
    episode=final.complete(tuple(produced),fixture,boundary,120,131)
    return SimpleNamespace(episode=episode,fixture=fixture,sources=final,frozen=c)


def _reverse_recipe_hash_for(fixture):
    from m56.response import _reverse_recipe_hash
    return _reverse_recipe_hash(fixture)
