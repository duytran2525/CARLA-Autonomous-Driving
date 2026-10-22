"""Composed synthetic evidence; NOT CARLA dynamics, native qualification or selection."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
import hashlib

import pytest


@pytest.fixture(scope='module')
def complete_pair(tmp_path_factory):
    from m56.model import (SourceRef,BodyRecord,Transform6,DirectedRoute,Section,Domain,
        FrozenMetricPair,CompiledFixture,ActorFrame,FrameRecord,EpisodeEvidence,
        FrozenResponse,CommandRecord,ControlPacket,CapabilityProof,ReviewRecord,
        RuntimeIdentity,OwnershipReceipt,ActorRecipe)
    from m56.evidence import open_run,append_record,snapshot_sources,seal,_payload
    from m56.catalog import _digest
    from m56.metrics import _source_metrics,_authenticated_events,_ab_review_subject
    root=tmp_path_factory.mktemp('t09-composed');refs=[]
    def ref(path,frame=None,time=None):
        data=path.read_bytes()
        return SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST',frame,time)
    def source(name,payload,frame=None,time=None):
        path=root/(name+'.json');path.write_bytes(_payload(payload));r=ref(path,frame,time);refs.append(r);return r
    authority=source('authority',{'scope':'SYNTHETIC_TEST_ONLY','limitation':'no native permission or reviewer independence'})
    def review(payload,scope,sources):
        return ReviewRecord(_digest(payload),scope,tuple(sources),'SYNTHETIC_AUTHOR','2026-10-10','APPROVED',
                            ('literal source-bound software contract, not native qualification',),authority)
    def capability(kind,method,limits,raw,extra=(),uncertainty=F(1,1000)):
        packet=dict(kind=kind,method=method,raw_refs=tuple(raw),uncertainty=uncertainty,limits=limits,status='CORROBORATED')
        return CapabilityProof(**packet,review=review(packet,'CAPABILITY:'+kind,(*raw,*extra)))
    geometry=source('geometry',{'scope':'synthetic only','reference':'two finite directed test corridors'})
    body=BodyRecord((0.,0.,0.),(0.,0.,0.),(.5,.25,.25),(),'vehicle.audi.a2',{}, {},geometry)
    poses={role:Transform6(0.,y,0.,0.,0.,0.) for role,y in (('EGO',0.),('NPC',4.))}
    routes={role:DirectedRoute((),(p,replace(p,x=60.)),(F(0),F(60)),'b'*64,(geometry,),F(17)) for role,p in poses.items()}
    def section(x):
        return Section(tuple((float(x),y,z) for y in (-1.,5.) for z in (-1.,1.)),(1.,0.,0.),F(x),{})
    from itertools import product
    driving={role:(tuple(product((-1.,61.),(-1.+p.y,1.+p.y),(-1.,1.))),) for role,p in poses.items()}
    domain=Domain(section(10),section(12),section(10),section(12),(),{'category':'C','driving_regions':driving},(geometry,),'c'*64)
    pair=FrozenMetricPair(('d_yield_m','t_entry_s'),('m','s'),('forward_distance','elapsed'),
        (('TRIGGER','CLEAR_N_CONFIRMED'),('TRIGGER','E_ENTRY')),'route:'+_digest(routes['EGO']),'d'*64,'APPROVED_PROPOSAL_NOT_READY')
    zero_profile={'method':'quintic-arc-v1','segments':({'start_arc_m':F(0),'length_m':F(1),'start_offset_m':F(0),'end_offset_m':F(0)},)}
    def transition(cause,event,delay=F(0),guards=()):
        return {'cause':cause,'after_event':event,'delay_s':delay,'requires':guards}
    responses=[]
    for role,action,h in (('EGO','A','a'),('EGO','B','e'),('NPC','NPC_COMMON','f')):
        targets={'SETTLE':F(0),'NOMINAL':F(4 if role=='EGO' else 6)}
        transitions=[transition('NOMINAL','CAPTURE_START',F(21,20))]
        if role=='EGO':
            cause='STOP' if action=='A' else 'YIELD'
            targets.update({cause:F(0 if action=='A' else 2),'RESUME':F(4)})
            transitions.extend((transition(cause,'TRIGGER'),transition('RESUME','CLEAR_N_CONFIRMED',guards=('STOP_AFTER_TRIGGER',) if action=='A' else ())))
        responses.append(FrozenResponse(role,action,routes[role],targets,zero_profile,
            {'program':{'method':'ordered-event-program-v1','initial':'SETTLE','transitions':tuple(transitions)}},h*64))
    actors=tuple(ActorRecipe(role,'vehicle.audi.a2',F(0),pose,{'kind':'SYNTHETIC_TEST'},
                            {'kind':'SYNTHETIC_TEST'},F(17)) for role,pose in poses.items())
    readiness={'targets_mps':{'EGO':F(4),'NPC':F(6)},'markers_m':{'EGO':F(11,5),'NPC':F(33,10)}}
    fixture=CompiledFixture('1'*64,'2'*64,actors,{'readiness':readiness},poses,routes,domain,F(3),
                            {'DESTINATION':section(17)},tuple(responses),pair,(),geometry)
    fixture_hash=_digest(fixture)
    ground_recipe=source('ground-recipe',{'method':'recorded-ground-contact-v1','version':'1','limitations':'synthetic only'})
    init_recipe=source('initialization-recipe',{'method':'recorded-initialization-v1','version':'1','limitations':'synthetic only'})
    plans={role:source('plan-'+role,route) for role,route in routes.items()}
    modules={name:source('module-'+name,{'module':name,'scope':'not native source bytes'}) for name in ('carla','basic_agent','local_planner','controller')}
    def episode(action):
        ego_response=responses[0 if action=='A' else 1];npc_response=responses[2]
        frames=[];x=0.
        for i in range(-1,131):
            frame=100+i;time=F(i,20);actors=[]
            if i<=20:ex=nx=0.;ev=nv=0.
            else:
                nx=float(F(3,10)*(i-20));nv=6.
                if i<=53:ex=float(F(1,5)*(i-20));ev=4.
                elif i<=69:
                    ex=6.6 if action=='A' else float(F(33,5)+F(i-53,10));ev=0. if action=='A' else 2.
                else:
                    ex=float((F(33,5) if action=='A' else F(41,5))+F(i-69,5));ev=4.
            for role,identity,position,v,response in (('EGO',1,ex,ev,ego_response),('NPC',2,nx,nv,npc_response)):
                cause='SETTLE' if i<=20 else 'NOMINAL'
                if role=='EGO' and 54<=i<=69:cause='STOP' if action=='A' else 'YIELD'
                if role=='EGO' and i>=70:cause='RESUME'
                control=ControlPacket(.0 if v==0 else .2,0.,.3 if v==0 else 0.,False,False,False,1)
                command=CommandRecord(identity,frame-1,frame,'CONTROL',response.targets[cause]*F(18,5),F(0),control,None,cause,response.hash)
                pose=replace(poses[role],x=position)
                limits={'fixture_hash':fixture_hash,'boot':'boot','world':'world','frame':frame,'actor_id':identity,
                    'body_pose_hash':_digest({'body':body,'pose':pose}),'maximum_ground_error_m':F(0),
                    'contact_method':'recorded-ground-contact-v1','recipe_ref':ground_recipe}
                observed=source(f'{action}-ground-{frame}-{role}',limits,frame,time)
                ground=capability('GROUND:'+role,'recorded-ground-contact-v1',limits,(observed,),(ground_recipe,))
                actors.append(ActorFrame(role,identity,pose,(v,0.,0.),body,F(position),{},(command,) if i>=0 else (),control,None,1,True,ground))
            record=FrameRecord('boot','world',frame,time,F(1,20),tuple(actors),(),{})
            observed=source(f'{action}-frame-{frame}',{'boot':'boot','world':'world','frame':frame,'simtime':time,'actors':record.actors},frame,time)
            fields={'frame_refs':(observed,),'plan_refs':plans,'metric_context':{'pair_hash':pair.hash,'reference':pair.reference,
                    'directed_route':routes['EGO'],'uncertainty':{name:F(0) for name in pair.names}}}
            if frames:
                limits={'fixture_hash':fixture_hash,'previous_actors':_digest(frames[-1].actors),'actors':_digest(record.actors),
                        'previous_frame':frame-1,'frame':frame}
                fields['continuous_geometry']=capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(observed,))
            frames.append(replace(record,integrity=fields))
        boundary=frames[0];frames=tuple(frames[1:]);first,last=frames[0],frames[-1]
        trajectory_hash=_digest(frames)
        streams={'pre_observation_ref':boundary,'sensor_registry_ref':{'boot':'boot','world':'world','sensors':{'10':1,'11':2}},'collision_ref':[]}
        identity=RuntimeIdentity('boot','world','0.9.16','0.9.16','3.12.10',modules,'b'*64,{k:r.sha256 for k,r in modules.items()})
        owner=OwnershipReceipt('boot','world','synthetic-local',123,'synthetic-start',{'rpc':2000},(F(0),F(10)),
                               'synthetic-ticker','writer',('tick','observe'))
        ownership={'identity':identity,'ownership':owner,'actors':{'EGO':1,'NPC':2},'fixture_hash':fixture_hash,
                   'wall_interval':(F(0),F(9)),'observed_tick_owner':'synthetic-ticker'}
        ownership_ref=source(action+'-ownership',ownership)
        streams['w01_ref']=ownership;streams['w01_review_ref']=review(ownership,'W01_OWNERSHIP',(ownership_ref,*modules.values()))
        init={'method':'recorded-initialization-v1','fixture_hash':fixture_hash,'boundary_hash':_digest(boundary),
              'settled_frame':120,'ready_frame':131,'targets_mps':{'EGO':F(4),'NPC':F(6)},
              'ready_markers_m':{'EGO':F(11,5),'NPC':F(33,10)},'recipe_ref':init_recipe,
              'settings':{'synchronous_mode':True,'fixed_delta_seconds':F(1,20),'max_substep_delta_time':F(1,100),'max_substeps':10}}
        initial_ref=source(action+'-initialization',init)
        streams['initialization_ref']=init;streams['initialization_review_ref']=review(init,'INITIALIZATION',(initial_ref,init_recipe))
        qualification=source(action+'-delivery-qualification',{'limitation':'synthetic data contract only'})
        delivery_recipe={'schema':1,'method':'recorded-ack-fence-v1','version':'1','limits':'observed-owned-interval-only','qualification_refs':(qualification,)}
        recipe_ref=source(action+'-delivery-recipe',delivery_recipe)
        lifecycle={'boot':'boot','world':'world','channels':[{'sensor_id':s,'actor_id':a,'listen_frame':99,'stop_frame':last.frame+1,'errors':[]} for s,a in ((10,1),(11,2))]}
        fence={'boot':'boot','world':'world','recipe_hash':recipe_ref.sha256,'channels':[{'sensor_id':s,'request_id':str(s),
            'acknowledged_request_id':str(s),'first_frame':100,'last_frame':last.frame,'remaining':0} for s in (10,11)]}
        lr=source(action+'-lifecycle',lifecycle);fr=source(action+'-fence',fence)
        streams['delivery_ref']=capability('COLLISION_DELIVERY','recorded-ack-fence-v1',
            {'fixture_hash':fixture_hash,'trajectory_hash':trajectory_hash,'recipe_ref':recipe_ref,
             'recipe_review':review(delivery_recipe,'COLLISION_DELIVERY_RECIPE',(recipe_ref,qualification)),
             'lifecycle_ref':lr,'fence_ref':fr},(lr,fr),(recipe_ref,),F(0))
        rows=[{'boot':'boot','world':'world','first_frame':a.frame,'last_frame':b.frame,'first_actors_hash':_digest(a.actors),
               'last_actors_hash':_digest(b.actors),'minimum_body_separation_m':F(3),'minimum_road_edge_m':F(1),
               'maximum_ground_error_m':F(0),'error_m':F(1,1000)} for a,b in zip(frames,frames[1:])]
        rr=source(action+'-contact-intervals',rows)
        recipe={'method':'bounded-contact-interval-v1','version':'1','quantities':('body_separation','road_edge','ground_contact'),'source_refs':(rr,)}
        cr=source(action+'-contact-recipe',recipe)
        streams['contact_ref']=capability('CONTINUOUS_CONTACT','bounded-contact-interval-v1',
            {'fixture_hash':fixture_hash,'trajectory_hash':trajectory_hash,'recipe_ref':cr,
             'recipe_review':review(recipe,'CONTACT_RECIPE',(cr,rr)),'intervals_ref':rr},(rr,),(cr,))
        motion=[]
        for a,b in zip(frames,frames[1:]):
            envelopes={}
            for aa,bb in zip(a.actors,b.actors):
                envelopes[aa.role]={'actor_id':aa.id,'response_hash':bb.commands[0].response_hash,
                    'envelope':tuple(product((min(aa.pose.x,bb.pose.x)-.6,max(aa.pose.x,bb.pose.x)+.6),
                                             (aa.pose.y-.35,aa.pose.y+.35),(-.35,.35))),
                    'reference_lateral_acceleration_bound_mps2':F(0)}
            motion.append({'boot':a.boot,'world':a.world,'first_frame':a.frame,'last_frame':b.frame,
                           'first_actors_hash':_digest(a.actors),'last_actors_hash':_digest(b.actors),'actors':envelopes})
        mr=source(action+'-motion-intervals',motion)
        recipe={'method':'bounded-motion-envelope-v1','version':'1',
                'quantities':('continuous_body_enclosure','reference_lateral_acceleration'),'source_refs':(mr,)}
        mrecipe=source(action+'-motion-recipe',recipe)
        streams['motion_ref']=capability('CONTINUOUS_MOTION','bounded-motion-envelope-v1',
            {'fixture_hash':fixture_hash,'trajectory_hash':trajectory_hash,'recipe_ref':mrecipe,
             'recipe_review':review(recipe,'MOTION_RECIPE',(mrecipe,mr)),'intervals_ref':mr},(mr,),(mrecipe,))
        store=open_run(root/action,'synthetic-'+action,'writer')
        append_record(store,'fixture.json',fixture);append_record(store,'trajectory.json',frames)
        pointers={'trajectory_ref':ref(store.root/'trajectory.json')}
        for name,payload in streams.items():
            append_record(store,name+'.json',payload);pointers[name]=ref(store.root/(name+'.json'))
        assert snapshot_sources(store,tuple(refs)).status=='INTEGRITY_VALID'
        seal(store)
        e=EpisodeEvidence(frames,(ref(store.journal),),ref(store.root/'fixture.json'),(*pointers.values(),*refs),
                          ref(store.root/'manifest.json'),pointers,None,last.simtime)
        values=_source_metrics(e,fixture);events=_authenticated_events(e,fixture)
        assert values is not None and events is not None
        original=(e.fixture,e.manifest,*e.journal,*e.source)
        subject={'schema':1,'scope':'EPISODE_WITNESS_W05','fixture':e.fixture,'manifest':e.manifest,'journal':e.journal,
                 'sources':e.source,'trajectory_hash':trajectory_hash,'end_simtime':e.end_simtime,'events':events,'metrics':values}
        areas=('fulltrace','near_zero','nearstanding','identity','mechanism','comparability')
        w05=replace(review(subject,'EPISODE_WITNESS_W05',original),reasons=tuple(k+': synthetic software evidence only, no scientific acceptance' for k in areas))
        bundle=open_run(root/(action+'-w05'),'synthetic-'+action+'-review','writer')
        append_record(bundle,'review.json',w05);assert snapshot_sources(bundle,(*original,authority)).status=='INTEGRITY_VALID';seal(bundle)
        return replace(e,integrity={**e.integrity,'episode_review_ref':ref(bundle.root/'review.json'),'episode_review_manifest':ref(bundle.root/'manifest.json')})
    a=episode('A');b=episode('B');left=_source_metrics(a,fixture);right=_source_metrics(b,fixture)
    ab=review(_ab_review_subject(a,b,pair,left,right),'REALIZED_AB_COMPARABILITY_D09',
              tuple(dict.fromkeys((a.fixture,a.manifest,*a.journal,*a.source,b.fixture,b.manifest,*b.journal,*b.source))))
    ab=replace(ab,reasons=tuple(k+': synthetic contract verification, no realized scientific qualification' for k in ('fulltrace','near_zero','nearstanding','identity','mechanism','comparability')))
    return SimpleNamespace(a=a,b=b,fixture=fixture,review=ab)


@pytest.mark.parametrize('regions,want',[
    (((0.,2.),(2.,4.)),True),
    (((0.,1.9),(2.1,4.)),False),
    (((0.,1.),(3.,4.)),False),
])
def test_continuous_fit_checks_union_interior_not_only_envelope_corners(regions,want,require):
    from itertools import product
    covers=require('m56.evidence','_box_union_covers')
    union=tuple(tuple(product(x,(-1.,1.),(-1.,1.))) for x in regions)
    envelope=tuple(product((.5,3.5),(-.25,.25),(-.25,.25)))
    assert covers(envelope,union,F(3,20),F(1,1000)) is want


def test_t09_initialization_and_motion_components_are_source_backed(complete_pair,require):
    initialization=require('m56.evidence','_initialization_integrity')
    motion=require('m56.evidence','_motion_integrity')
    c=complete_pair
    assert initialization(c.a,c.fixture)==((),())
    assert motion(c.a,c.fixture)==((),())


@pytest.mark.parametrize('key,reason',[('initialization_ref','INITIALIZATION_MISSING'),('motion_ref','MOTION_PROOF_MISSING'),
                                       ('delivery_ref','DELIVERY_PROOF_MISSING'),('pre_observation_ref','PHASE_BOUNDARY_MISSING')])
def test_t09_missing_channel_never_keeps_positive_eligibility(complete_pair,key,reason):
    from m56.evidence import check_integrity
    from m56.metrics import compare_ab
    c=complete_pair;e=replace(c.a,integrity={k:v for k,v in c.a.integrity.items() if k!=key})
    out=check_integrity(e,c.fixture)
    assert out.status!='WITNESS_VALID'
    assert reason in out.reasons
    assert compare_ab(e,c.b,c.fixture.pair,c.review).status!='PASS'


def test_t09_same_action_pair_cannot_pass_even_with_good_episode_proofs(complete_pair):
    from m56.metrics import compare_ab
    c=complete_pair
    assert compare_ab(c.a,c.a,c.fixture.pair,c.review).status=='INVALID'


def test_t09_complete_actions_without_ab_review_remain_review_required(complete_pair):
    from m56.metrics import compare_ab
    c=complete_pair
    assert compare_ab(c.a,c.b,c.fixture.pair,None).status=='REVIEW_REQUIRED'


def test_t09_source_backed_positive_crossing_episode_and_ab(complete_pair):
    from m56.evidence import check_integrity
    from m56.metrics import evaluate_episode,compare_ab
    c=complete_pair
    for e in (c.a,c.b):
        integrity=check_integrity(e,c.fixture)
        assert integrity.status=='WITNESS_VALID',integrity.reasons
        out=evaluate_episode(e,c.fixture)
        assert (out.spawn,out.physical,out.witness)==('CONFIRMED','COMPLETE','VALID'),out.reasons
        assert all(m.status=='VALID' and m.value is not None for m in out.metrics.values())
    verdict=compare_ab(c.a,c.b,c.fixture.pair,c.review)
    assert verdict.status=='PASS'
    assert all(d>=F(1,5) for d in verdict.comparisons)
