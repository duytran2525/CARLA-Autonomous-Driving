"""Synthetic F05 stock-creep stopping/corridor contracts, NOT measured calibration."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace


def creep_case(root,defect=None,last=190):
    from tests.m56.test_f05_phase_events import f05_observations
    from tests.m56.test_f05_creep_normative_response import f05_ego_b
    from tests.m56.source_cases import Sources
    from tests.m56.reverse_cases import ground_actor
    from m56.model import CommandRecord,ControlPacket
    from m56.catalog import _digest
    from m56.response import _reverse_recipe_hash,_reverse_body_hash
    root.mkdir();c=f05_observations(root/'physical',last=last);s=Sources(root/'creep');s.refs.extend(c.s.refs)
    response=replace(f05_ego_b()[0],route=c.fixture.routes['EGO'])
    response=replace(response,hash=_digest({k:getattr(response,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    fixture=replace(c.fixture,responses=(response,c.npc))
    # Literal independent stock settings (not a measured stop result).
    stock={'lateral':{'K_P':F(39,20),'K_I':F(1,20),'K_D':F(1,5)},
           'longitudinal':{'K_P':F(1),'K_I':F(1,20),'K_D':F(0)},'dt_s':F(1,20),
           'max_throttle':F(3,4),'max_brake':F(3,10),'max_steering':F(4,5)}
    recipe=_reverse_recipe_hash(fixture);body=c.frames[0].actors[0].body
    limits={'actor_role':'EGO','response_hash':response.hash,'route_hash':_digest(response.route),
        'body_hash':_reverse_body_hash(body),'fixture_recipe_hash':recipe,'stock_config_hash':_digest(stock),
        'target_mps':F(1,2),'terminal_brake':F(3,10),'hard_limit_m':F(1),
        'stopping_boundary_m':F(4,5),'stopping_distance_bound_m':F(1,5),'maximum_forward_speed_mps':F(1,2)}
    if defect=='unsafe_bound':limits['stopping_distance_bound_m']=F(1,4)
    if defect=='wrong_body':limits['body_hash']='f'*64
    if defect=='wrong_response':limits['response_hash']='f'*64
    bound_ref=s.source('stop-bound',limits)
    proof=s.capability('CREEP_STOP_BOUND','bounded-forward-creep-stop-v1',limits,(bound_ref,),F(0))
    fixture=replace(fixture,proofs=() if defect=='missing_bound' else (proof,))
    fixture_ref=s.source('creep-fixture',fixture)
    ground_recipe=s.source('ground-recipe',{'method':'recorded-ground-contact-v1','version':'1',
        'limitations':'synthetic software receipt only, no native contact calibration'})
    frames=[]
    for raw in c.frames:
        e,n=raw.actors;number=raw.frame
        progress=F(min(max(number-120,0),40),40)
        if defect=='overshoot' and number>=161:progress+=F(1,40)
        stopped=number<=120 or number>=161
        control=ControlPacket(0.,0.,.3,False,False,False,1) if number<=120 or number>=152 else ControlPacket(.2,0.,0.,False,False,False,1)
        cause='HOLD' if number<=120 else 'CREEP' if number<=151 else 'CREEP_STOP'
        command=CommandRecord(e.id,number-1,number,'CONTROL',F(9,5) if cause=='CREEP' else F(0),F(0),control,None,cause,response.hash)
        e=replace(e,pose=replace(e.pose,x=float(-F(13,2)+progress)),arc=F(float(-F(13,2)+progress))+10,
            velocity=(0.,0.,0.) if stopped else (.5,0.,0.),commands=(command,),readback=control)
        if defect=='rolling_stop' and number>=161:
            e=replace(e,pose=replace(e.pose,x=float(-F(11,2)+F(number-160,64))),arc=F(9,2)+F(number-160,64))
        e=ground_actor(s,fixture,e,number,raw.simtime,ground_recipe)
        frame=replace(raw,actors=(e,n),integrity={})
        ref=s.source('observed-'+str(number),{'boot':frame.boot,'world':frame.world,'frame':number,'simtime':frame.simtime,'actors':frame.actors},number,frame.simtime)
        current={'fixture_recipe_hash':recipe,'boot':frame.boot,'world':frame.world,'frame':number,'actor_id':e.id,
                 'actors_hash':_digest(frame.actors),'response_hash':response.hash,'route_hash':_digest(response.route),
                 'minimum_forward_clearance_m':F(1)}
        path_ref=s.source('queue-path-'+str(number),current,number,frame.simtime)
        path=s.capability('QUEUE_PATH','bounded-queue-exit-corridor-v1',current,(path_ref,),F(0))
        if defect=='path_hash_alias' and number==last:path=replace(path,raw_refs=(replace(path_ref,sha256='f'*64),))
        fields={'frame_refs':(ref,),'queue_path':path,'creep_fixture_ref':fixture_ref}
        if defect=='missing_path' and number==last:fields.pop('queue_path')
        if frames:
            continuous={'fixture_hash':_digest(fixture),'previous_actors':_digest(frames[-1].actors),'actors':_digest(frame.actors),
                        'previous_frame':number-1,'frame':number}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',continuous,(ref,),F(0))
        frames.append(replace(frame,integrity=fields))
    history=s.source('history',tuple(frames));frame=frames[-1]
    frame=replace(frame,integrity={**frame.integrity,'creep_history_ref':history})
    if defect=='missing_fixture':frame=replace(frame,integrity={k:v for k,v in frame.integrity.items() if k!='creep_fixture_ref'})
    trigger=frames[20]
    return SimpleNamespace(s=s,frames=tuple(frames),frame=frame,fixture=fixture,response=response,proof=proof,
        trigger=trigger,fixture_ref=fixture_ref,history_ref=history,ground_recipe=ground_recipe)
