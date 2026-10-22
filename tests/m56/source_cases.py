"""Test-only immutable source composition. No native provider or permission."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import hashlib

from m56.catalog import _digest
from m56.evidence import _payload, open_run, append_record, snapshot_sources, seal
from m56.model import SourceRef, ReviewRecord, EpisodeEvidence, CapabilityProof


class Sources:
    def __init__(self, root):
        self.root=Path(root);self.root.mkdir();self.refs=[]
        self.authority=self.source('authority',{'scope':'SYNTHETIC_TEST_ONLY','limitations':'no native qualification or authority'})

    def ref(self, path, frame=None, time=None):
        data=path.read_bytes()
        return SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST',frame,time)

    def source(self, name, value, frame=None, time=None):
        path=self.root/(name+'.json');path.write_bytes(_payload(value))
        ref=self.ref(path,frame,time);self.refs.append(ref);return ref

    def review(self, value, scope, refs):
        return ReviewRecord(_digest(value),scope,tuple(refs),'SYNTHETIC_AUTHOR','2026-10-11','APPROVED',
                            ('synthetic source contract only; not native qualification',),self.authority)

    def capability(self, kind, method, limits, refs, uncertainty=F(1,1000), extra=()):
        packet=dict(kind=kind,method=method,raw_refs=tuple(refs),uncertainty=uncertainty,limits=limits,status='CORROBORATED')
        return CapabilityProof(**packet,review=self.review(packet,'CAPABILITY:'+kind,(*refs,*extra)))

    def bind_frames(self, frames, fixture):
        from m56.response import _reference_response
        plans={}
        for response in fixture.responses:
            program=response.phases.get('program',{})
            for cause in (program.get('initial','SYNTHETIC'),*(r['cause'] for r in program.get('transitions',()))):
                reference=_reference_response(response,cause).route if program else response.route
                key=(response.actor_role,cause)
                plans[key]=self.source('plan-'+response.actor_role+'-'+cause,reference)
        result=[]
        for f in frames:
            ref=self.source('frame-'+str(f.frame),{'boot':f.boot,'world':f.world,'frame':f.frame,'simtime':f.simtime,'actors':f.actors},f.frame,f.simtime)
            fields={**f.integrity,'frame_refs':(ref,),'plan_refs':{a.role:plans[(a.role,a.commands[0].cause)] for a in f.actors}}
            if 'npc_controls' in fields:
                traffic=fields['npc_controls'];raw={k:v for k,v in traffic.items() if k!='witness_refs'}
                witness=self.source('npc-controls-'+str(f.frame),raw,f.frame,f.simtime)
                fields['npc_controls']={**raw,'witness_refs':(witness,)}
            for key in ('lane_change_path','return_path','rollback','door_geometry','preparation_cue','validation_start'):
                proof=f.integrity.get(key)
                if proof is not None:
                    limits={**proof.limits,'fixture_hash':_digest(fixture),'frame':f.frame,'actors_hash':_digest(f.actors)}
                    if key=='preparation_cue' and result:limits['previous_actors_hash']=_digest(result[-1].actors)
                    fields[key]=self.capability(proof.kind,proof.method,limits,(ref,),proof.uncertainty)
            request=f.integrity.get('preparation_request')
            if request is not None:
                limits={**request.limits,'fixture_hash':_digest(fixture),'frame':f.frame,'actors_hash':_digest(f.actors)}
                raw=self.source('bound-preparation-request-'+str(f.frame),limits,f.frame,f.simtime)
                fields['preparation_request']=self.capability(request.kind,request.method,limits,(raw,),request.uncertainty)
            queue_path=f.integrity.get('queue_path')
            if queue_path is not None:
                limits={**queue_path.limits,'frame':f.frame,'actors_hash':_digest(f.actors)}
                raw=self.source('bound-queue-path-'+str(f.frame),limits,f.frame,f.simtime)
                fields['queue_path']=self.capability(queue_path.kind,queue_path.method,limits,(raw,),queue_path.uncertainty)
            fields.pop('continuous_geometry',None)
            if result:
                limits={'fixture_hash':_digest(fixture),'previous_actors':_digest(result[-1].actors),
                        'actors':_digest(f.actors),'previous_frame':f.frame-1,'frame':f.frame}
                fields['continuous_geometry']=self.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),F(0))
            elif f.integrity.get('continuous_geometry') is not None:
                original=f.integrity['continuous_geometry']
                if original.limits.get('actors')==_digest(f.actors):fields['continuous_geometry']=original
            result.append(replace(f,integrity=fields))
            if 'creep_history_ref' in f.integrity:
                # Grounding/receiving-command binding changes actor packets.
                # Seal a NEW complete prefix; never edit an old history or use
                # a cached verdict. Keep only detector-required source fields
                # so prior prefixes are not recursively embedded.
                selected=tuple(replace(p,events=(),integrity={k:v for k,v in p.integrity.items()
                    if k in ('frame_refs','continuous_geometry','validation_start','queue_path')}) for p in result)
                history=self.source('bound-creep-history-'+str(len(self.refs))+'-'+str(f.frame),selected)
                result[-1]=replace(result[-1],integrity={**result[-1].integrity,'creep_history_ref':history})
            if 'reverse_history_ref' in f.integrity:
                from m56.evidence import _read_trajectory
                original=_read_trajectory(f.integrity['reverse_history_ref'])
                preceding=tuple(p for p in original if p.frame<result[0].frame)
                # Semantic peer events must refer to THESE admitted observations,
                # not different original locators with otherwise matching actors.
                # Keep the original pre-capture prefix and omit recursive contexts.
                selected=tuple(replace(p,events=(),integrity={k:v for k,v in p.integrity.items()
                    if k in ('frame_refs','continuous_geometry','preparation_cue','rollback')})
                    for p in (*preceding,*result))
                history=self.source('bound-reverse-history-'+str(len(self.refs))+'-'+str(f.frame),selected)
                result[-1]=replace(result[-1],integrity={**result[-1].integrity,'reverse_history_ref':history})
        return tuple(result)

    def complete(self, frames, fixture, boundary, settled_frame, ready_frame, *, preserve_ground=False):
        """Seal independent W01/W03/motion/init/W05 channels around a literal trace.

        Reverse producer histories already bind their source ground packets. When
        explicitly preserved, the public consumer still verifies those original
        packets; replacing them would change actors without a new history recipe.
        """
        from itertools import product
        from m56.model import RuntimeIdentity,OwnershipReceipt
        from m56.metrics import _source_metrics,_authenticated_events
        recipe=self.source('ground-recipe',{'method':'recorded-ground-contact-v1','version':'1','limitations':'synthetic contract only'})
        grounded=[]
        for f in (boundary,*frames):
            actors=[]
            for a in f.actors:
                if preserve_ground:
                    assert a.ground is not None
                    actors.append(a);continue
                limits={'fixture_hash':_digest(fixture),'boot':f.boot,'world':f.world,'frame':f.frame,'actor_id':a.id,
                        'body_pose_hash':_digest({'body':a.body,'pose':a.pose}),'maximum_ground_error_m':F(0),
                        'contact_method':'recorded-ground-contact-v1','recipe_ref':recipe}
                ref=self.source('ground-'+str(f.frame)+'-'+a.role,limits,f.frame,f.simtime)
                actors.append(replace(a,ground=self.capability('GROUND:'+a.role,'recorded-ground-contact-v1',limits,(ref,),extra=(recipe,))))
            grounded.append(replace(f,actors=tuple(actors)))
        boundary=grounded[0];frames=self.bind_frames(tuple(grounded[1:]),fixture)
        # Preparation cue also binds the preceding observed actors, never old hashes.
        corrected=[]
        for i,f in enumerate(frames):
            if 'preparation_cue' in f.integrity and i:
                proof=f.integrity['preparation_cue'];limits={**proof.limits,'previous_actors_hash':_digest(frames[i-1].actors)}
                proof=self.capability(proof.kind,proof.method,limits,proof.raw_refs,proof.uncertainty)
                f=replace(f,integrity={**f.integrity,'preparation_cue':proof})
            corrected.append(f)
        frames=tuple(corrected);first,last=frames[0],frames[-1];streams={}
        modules={k:self.source('module-'+k,{'scope':'synthetic, not native source'}) for k in ('carla','basic_agent','local_planner','controller')}
        identity=RuntimeIdentity(first.boot,first.world,'0.9.16','0.9.16','3.12.10',modules,fixture.routes['EGO'].map_hash,{k:r.sha256 for k,r in modules.items()})
        owner=OwnershipReceipt(first.boot,first.world,'synthetic-local',123,'synthetic-start',{'rpc':2000},(F(0),F(300)),
                               'ticker','writer',('tick','observe'))
        ownership={'identity':identity,'ownership':owner,'actors':{a.role:a.id for a in first.actors},'fixture_hash':_digest(fixture),
                   'wall_interval':(F(0),F(299)),'observed_tick_owner':'ticker'}
        ref=self.source('ownership',ownership);streams.update(w01_ref=ownership,w01_review_ref=self.review(ownership,'W01_OWNERSHIP',(ref,*modules.values())))
        initrecipe=self.source('init-recipe',{'method':'recorded-initialization-v1','version':'1','limitations':'synthetic only'})
        metadata=fixture.environment['readiness']
        initialization={'method':'recorded-initialization-v1','fixture_hash':_digest(fixture),'boundary_hash':_digest(boundary),
            'settled_frame':settled_frame,'ready_frame':ready_frame,'targets_mps':metadata['targets_mps'],'ready_markers_m':metadata['markers_m'],
            'recipe_ref':initrecipe,'settings':{'synchronous_mode':True,'fixed_delta_seconds':F(1,20),'max_substep_delta_time':F(1,100),'max_substeps':10}}
        ref=self.source('initialization',initialization)
        streams.update(initialization_ref=initialization,initialization_review_ref=self.review(initialization,'INITIALIZATION',(ref,initrecipe)))
        streams.update(sensor_registry_ref={'boot':first.boot,'world':first.world,'sensors':{'10':1,'11':2}},collision_ref=[])
        qualification=self.source('delivery-qualification',{'limits':'synthetic only'})
        deliveryrecipe={'schema':1,'method':'recorded-ack-fence-v1','version':'1','limits':'observed-owned-interval-only','qualification_refs':(qualification,)}
        dr=self.source('delivery-recipe',deliveryrecipe)
        lifecycle={'boot':first.boot,'world':first.world,'channels':[{'sensor_id':s,'actor_id':a,'listen_frame':boundary.frame,'stop_frame':last.frame+1,'errors':[]} for s,a in ((10,1),(11,2))]}
        fence={'boot':first.boot,'world':first.world,'recipe_hash':dr.sha256,'channels':[{'sensor_id':s,'request_id':str(s),
            'acknowledged_request_id':str(s),'first_frame':first.frame,'last_frame':last.frame,'remaining':0} for s in (10,11)]}
        lr=self.source('lifecycle',lifecycle);fr=self.source('fence',fence)
        common={'fixture_hash':_digest(fixture),'trajectory_hash':_digest(frames)}
        streams['delivery_ref']=self.capability('COLLISION_DELIVERY','recorded-ack-fence-v1',{**common,'recipe_ref':dr,
            'recipe_review':self.review(deliveryrecipe,'COLLISION_DELIVERY_RECIPE',(dr,qualification)),'lifecycle_ref':lr,'fence_ref':fr},(lr,fr),F(0),extra=(dr,))
        contact=[];motion=[]
        for a,b in zip(frames,frames[1:]):
            row={'boot':a.boot,'world':a.world,'first_frame':a.frame,'last_frame':b.frame,
                 'first_actors_hash':_digest(a.actors),'last_actors_hash':_digest(b.actors)}
            contact.append({**row,'minimum_body_separation_m':F(1),'minimum_road_edge_m':F(1,2),'maximum_ground_error_m':F(0),'error_m':F(1,1000)})
            actors={}
            for aa,bb in zip(a.actors,b.actors):
                from m56.geometry import world_vertices
                vertices=(*world_vertices(aa.body,aa.pose),*world_vertices(bb.body,bb.pose))
                actors[aa.role]={'actor_id':aa.id,'response_hash':bb.commands[0].response_hash,
                    # Synthetic straight/monotone interval enclosure of the
                    # actual complete bodies, not one fixed tiny-test extent.
                    'envelope':tuple(product(*((min(v[k] for v in vertices)-.1,
                                                max(v[k] for v in vertices)+.1) for k in range(3)))),
                    'reference_lateral_acceleration_bound_mps2':F(12,5)}
            motion.append({**row,'actors':actors})
        for key,kind,method,rows,quantities,scope in (
            ('contact_ref','CONTINUOUS_CONTACT','bounded-contact-interval-v1',contact,('body_separation','road_edge','ground_contact'),'CONTACT_RECIPE'),
            ('motion_ref','CONTINUOUS_MOTION','bounded-motion-envelope-v1',motion,('continuous_body_enclosure','reference_lateral_acceleration'),'MOTION_RECIPE')):
            rr=self.source(key+'-intervals',rows);rp={'method':method,'version':'1','quantities':quantities,'source_refs':(rr,)};rref=self.source(key+'-recipe',rp)
            streams[key]=self.capability(kind,method,{**common,'recipe_ref':rref,'recipe_review':self.review(rp,scope,(rref,rr)),
                                                      'intervals_ref':rr},(rr,),extra=(rref,))
        e=self.episode(frames,fixture,boundary,streams)
        metrics=_source_metrics(e,fixture);events=_authenticated_events(e,fixture)
        assert metrics is not None and events is not None
        original=(e.fixture,e.manifest,*e.journal,*e.source)
        subject={'schema':1,'scope':'EPISODE_WITNESS_W05','fixture':e.fixture,'manifest':e.manifest,'journal':e.journal,
                 'sources':e.source,'trajectory_hash':_digest(e.raw),'end_simtime':e.end_simtime,'events':events,'metrics':metrics}
        review=replace(self.review(subject,'EPISODE_WITNESS_W05',original),reasons=tuple(k+': synthetic contract only' for k in ('fulltrace','near_zero','nearstanding','identity','mechanism','comparability')))
        store=open_run(self.root/'review','synthetic-review','writer');append_record(store,'review.json',review)
        assert snapshot_sources(store,(*original,self.authority)).status=='INTEGRITY_VALID';seal(store)
        return replace(e,integrity={**e.integrity,'episode_review_ref':self.ref(store.root/'review.json'),
                                    'episode_review_manifest':self.ref(store.root/'manifest.json')})

    def episode(self, frames, fixture, boundary, streams=None):
        store=open_run(self.root/'episode','synthetic','writer')
        append_record(store,'fixture.json',fixture);append_record(store,'trajectory.json',frames)
        pointers={'trajectory_ref':self.ref(store.root/'trajectory.json')}
        for key,value in {'pre_observation_ref':boundary,**(streams or {})}.items():
            append_record(store,key+'.json',value);pointers[key]=self.ref(store.root/(key+'.json'))
        assert snapshot_sources(store,tuple(self.refs)).status=='INTEGRITY_VALID'
        seal(store)
        return EpisodeEvidence(frames,(self.ref(store.journal),),self.ref(store.root/'fixture.json'),
                               (*pointers.values(),*self.refs),self.ref(store.root/'manifest.json'),pointers,None,frames[-1].simtime)
