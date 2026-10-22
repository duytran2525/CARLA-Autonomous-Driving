"""Real filesystem evidence tests, synthetic payloads only."""
import pytest
from dataclasses import replace
from fractions import Fraction as F


@pytest.fixture
def silent_episode(tmp_path):
    from types import SimpleNamespace
    from m56.model import (SourceRef,BodyRecord,Transform6,DirectedRoute,Section,Domain,
        FrozenMetricPair,CompiledFixture,ActorFrame,FrameRecord,EpisodeEvidence)
    from m56.evidence import open_run,append_record,seal
    import hashlib
    source=SourceRef('synthetic://metadata','a'*64,1,'test','literal','SYNTHETIC_TEST')
    body=BodyRecord((0.,0.,0.),(0.,0.,0.),(.5,.25,.25),(),'vehicle.audi.a2',{}, {},source)
    route=DirectedRoute((),(Transform6(0.,0.,0.,0.,0.,0.),Transform6(30.,0.,0.,0.,0.,0.)),
                        (F(0),F(30)),'b'*64,(source,),F(20))
    def section(x):
        return Section(tuple((float(x),y,z) for y in (-1.,1.) for z in (-1.,1.)),(1.,0.,0.),F(x),{})
    domain=Domain(section(10),section(12),section(10),section(12),(),{},(source,),'c'*64)
    pair=FrozenMetricPair(('d_yield_m','t_entry_s'),('m','s'),('forward_distance','elapsed'),
                         (('TRIGGER','CLEAR_N_CONFIRMED'),('TRIGGER','E_ENTRY')),'test-reference','d'*64,'APPROVED_PROPOSAL_NOT_READY')
    fixture=CompiledFixture('e'*64,'f'*64,(),{},
        {'EGO':Transform6(4.,0.,0.,0.,0.,0.),'NPC':Transform6(8.,0.,0.,0.,0.,0.)},
        {'EGO':route,'NPC':route},domain,F(3),{},(),pair,(),source)
    store=open_run(tmp_path/'episode','synthetic','writer')
    def ref(path):
        data=path.read_bytes()
        return SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'test','literal','SYNTHETIC_TEST')
    append_record(store,'raw/fixture.json',fixture)
    fixture_ref=ref(store.root/'raw/fixture.json')
    frames=[]
    for i in range(6):
        actors=tuple(ActorFrame(role,j,Transform6(x,0.,0.,0.,0.,0.),(0.,0.,0.),body,F(x),{},(),None,None,1,True,None)
                     for j,(role,x) in enumerate((('EGO',4.),('NPC',8.)),1))
        frames.append(FrameRecord('test-boot','test-world',100+i,F(i,20),F(1,20),actors,(),{}))
    append_record(store,'raw/frames.jsonl',tuple(frames))
    append_record(store,'raw/collision.jsonl',{'events':[],'actors':(1,2),'listeners_started':True,'drain_completed':True})
    sources=(ref(store.root/'raw/frames.jsonl'),ref(store.root/'raw/collision.jsonl'))
    seal(store)
    evidence=EpisodeEvidence(tuple(frames),(ref(store.journal),),fixture_ref,sources,
                             ref(store.root/'manifest.json'),{'collision_lifecycle':sources[1],'trajectory_ref':sources[0]},None,F(1,4))
    return SimpleNamespace(a=evidence,fixture=fixture,store=store)


def test_silence_is_not_health(require,silent_episode):
    check=require('m56.evidence','check_integrity');c=silent_episode
    out=check(c.a,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN',out.reasons
    assert 'DELIVERY_PROOF_MISSING' in out.reasons


def test_episode_source_corruption_is_invalid_even_when_events_empty(require,silent_episode):
    check=require('m56.evidence','check_integrity');c=silent_episode
    from pathlib import Path
    Path(c.a.source[1].uri).write_bytes(b'changed')
    out=check(c.a,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'SOURCE_HASH_MISMATCH' in out.reasons


def test_episode_frame_gap_and_world_change_do_not_become_never_event(require,silent_episode):
    check=require('m56.evidence','check_integrity');c=silent_episode
    for frames in (c.a.raw[:2]+c.a.raw[3:],(replace(c.a.raw[0],world='other'),)+c.a.raw[1:]):
        out=check(replace(c.a,raw=frames),c.fixture)
        assert out.status=='WITNESS_INVALID'
        assert 'FRAME_IDENTITY_OR_CONTINUITY' in out.reasons


def test_episode_fixture_object_must_match_sealed_source(require,silent_episode):
    check=require('m56.evidence','check_integrity');c=silent_episode
    out=check(c.a,replace(c.fixture,G=F(99)))
    assert out.status=='WITNESS_INVALID'
    assert 'FIXTURE_OBJECT_MISMATCH' in out.reasons


def test_episode_trajectory_object_must_match_sealed_source(require,silent_episode):
    check=require('m56.evidence','check_integrity');c=silent_episode
    first=c.a.raw[0];actor=first.actors[0]
    first=replace(first,actors=(replace(actor,pose=replace(actor.pose,x=5.)),first.actors[1]))
    out=check(replace(c.a,raw=(first,)+c.a.raw[1:]),c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'TRAJECTORY_OBJECT_MISMATCH' in out.reasons


def test_trajectory_reference_cannot_point_to_unsealed_replacement(require,silent_episode,tmp_path):
    check=require('m56.evidence','check_integrity');c=silent_episode
    from m56.evidence import _payload
    from m56.model import SourceRef
    import hashlib
    first=replace(c.a.raw[0],boot='replacement')
    data=_payload((first,)+c.a.raw[1:]);path=tmp_path/'replacement.jsonl';path.write_bytes(data)
    ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'test','literal','SYNTHETIC_TEST')
    episode=replace(c.a,source=c.a.source+(ref,),integrity={**c.a.integrity,'trajectory_ref':ref})
    out=check(episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'SOURCE_NOT_SEALED' in out.reasons


def test_late_collision_revokes_eligibility(require,silent_episode):
    check=require('m56.evidence','check_integrity');correct=require('m56.evidence','append_correction');c=silent_episode
    from m56.model import ArtifactRef
    source=c.a.source[1]
    raw=(c.store.root/'raw/collision.jsonl').read_bytes();seal=(c.store.root/'manifest.json').read_bytes()
    correct(c.store,ArtifactRef('raw/collision.jsonl',source.sha256,source.bytes,'STREAM'),
            {'frame':105,'actor_id':1,'other_actor_id':2,'normal_impulse':(1.,0.,0.)})
    out=check(c.a,c.fixture)
    assert out.status!='WITNESS_VALID'
    assert 'LATE_CORRECTIONS_REVIEW_REQUIRED' in out.reasons
    assert (c.store.root/'raw/collision.jsonl').read_bytes()==raw
    assert (c.store.root/'manifest.json').read_bytes()==seal


@pytest.fixture
def repackage_episode(tmp_path,silent_episode):
    """New namespace for every synthetic version; never rewrite a completed seal."""
    from m56.evidence import open_run,append_record,seal,snapshot_sources
    from m56.model import SourceRef
    import hashlib
    counter=0
    def build(frames=None,fixture=None,streams=None,integrity=None,external_refs=(),jsonl=()):
        nonlocal counter
        counter+=1;c=silent_episode
        frames=c.a.raw if frames is None else frames;fixture=fixture or c.fixture
        store=open_run(tmp_path/f'version-{counter}',f'synthetic-{counter}','writer')
        def ref(path):
            data=path.read_bytes()
            return SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'test','literal','SYNTHETIC_TEST')
        append_record(store,'raw/fixture.json',fixture)
        for row in frames if 'trajectory_ref' in jsonl else (frames,):
            append_record(store,'raw/frames.jsonl',row)
        refs={'trajectory_ref':ref(store.root/'raw/frames.jsonl')}
        for name,payload in (streams or {}).items():
            for row in payload if name in jsonl else (payload,):
                append_record(store,f'raw/{name}.jsonl',row)
            refs[name]=ref(store.root/f'raw/{name}.jsonl')
        if external_refs:
            assert snapshot_sources(store,external_refs).status=='INTEGRITY_VALID'
        seal(store)
        episode=replace(c.a,raw=frames,fixture=ref(store.root/'raw/fixture.json'),source=tuple(refs.values())+external_refs,
             journal=(ref(store.journal),),manifest=ref(store.root/'manifest.json'),
             integrity={**refs,**(integrity or {})},end_simtime=frames[-1].simtime)
        return episode
    return build


def test_collision_remains_failed_with_sensor_gap(require,silent_episode,repackage_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    registry={'boot':'test-boot','world':'test-world','sensors':{'10':1,'11':2}}
    collision={'boot':'test-boot','world':'test-world','sensor_id':10,'frame':102,'time':F(1,10),
               'actor_id':1,'other_actor_id':2,'normal_impulse':(1.,0.,0.)}
    episode=repackage_episode(streams={'sensor_registry_ref':registry,'collision_ref':[collision]})
    out=evaluate(episode,c.fixture)
    assert out.physical=='FAILED'
    assert out.witness=='UNCERTAIN'
    assert 'COLLISION_OBSERVED' in out.reasons
    assert all(v.value is None for v in out.metrics.values())


def test_unbound_collision_claim_cannot_become_observed_failure(require,silent_episode,repackage_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    episode=repackage_episode(integrity={'collision':True,'physical':'FAILED','spawn_confirmed':True})
    out=evaluate(episode,c.fixture)
    assert out.physical=='UNKNOWN'
    assert out.spawn=='UNKNOWN'
    assert 'COLLISION_OBSERVED' not in out.reasons


def test_foreign_collision_actor_is_not_owned_collision(require,silent_episode,repackage_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    registry={'boot':'test-boot','world':'test-world','sensors':{'10':1,'11':2}}
    collision={'boot':'test-boot','world':'test-world','sensor_id':10,'frame':102,'time':F(1,10),
               'actor_id':99,'other_actor_id':2,'normal_impulse':(1.,0.,0.)}
    episode=repackage_episode(streams={'sensor_registry_ref':registry,'collision_ref':[collision]})
    out=evaluate(episode,c.fixture)
    assert out.physical!='FAILED'
    assert out.witness=='INVALID'
    assert 'COLLISION_IDENTITY_MISMATCH' in out.reasons


@pytest.mark.parametrize('fault',['duplicate_actor','changed_actor','wrong_command_frame','duplicate_command','forged_event_time'])
def test_sealed_invalid_frame_correlations_are_rejected(require,silent_episode,repackage_episode,fault):
    check=require('m56.evidence','check_integrity');c=silent_episode
    from m56.model import ControlPacket,CommandRecord,EventRecord
    frames=list(c.a.raw);frame=frames[2];ego,npc=frame.actors
    if fault=='duplicate_actor':
        frame=replace(frame,actors=(ego,ego,npc))
    elif fault=='changed_actor':
        frame=replace(frame,actors=(replace(ego,id=99),npc))
    elif fault in ('wrong_command_frame','duplicate_command'):
        control=ControlPacket(0.,0.,1.,False,False,False,1)
        command=CommandRecord(ego.id,101,999 if fault=='wrong_command_frame' else 102,'CONTROL',F(0),F(0),control,None,'HOLD','a'*64)
        frame=replace(frame,actors=(replace(ego,commands=(command,command) if fault=='duplicate_command' else (command,)),npc))
    else:
        frame=replace(frame,events=(EventRecord('TRIGGER',102,F(99),(c.a.source[0],)),))
    frames[2]=frame
    out=check(repackage_episode(frames=tuple(frames)),c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'FRAME_CORRELATION_INVALID' in out.reasons


def test_missing_readback_plan_and_frame_sources_are_not_valid_witness(require,silent_episode):
    check=require('m56.evidence','check_integrity');c=silent_episode
    out=check(c.a,c.fixture)
    assert 'ACTOR_CONTROL_OR_PLAN_WITNESS_MISSING' in out.reasons
    assert 'FRAME_SOURCE_WITNESS_MISSING' in out.reasons


def test_negative_gap_is_violation(require,silent_episode,repackage_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    frames=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],pose=replace(f.actors[1].pose,x=4.5),arc=F(9,2)))) for f in c.a.raw)
    fixture=replace(c.fixture,domain=replace(c.fixture.domain,topology={'gap_order':'front'}))
    out=evaluate(repackage_episode(frames=frames,fixture=fixture),fixture)
    assert out.physical=='FAILED'
    assert 'NEGATIVE_DIRECTED_GAP' in out.reasons
    assert out.witness=='UNCERTAIN'


def test_trajectory_object_forgery_cannot_manufacture_negative_gap(require,silent_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    frames=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],pose=replace(f.actors[1].pose,x=4.5),arc=F(9,2)))) for f in c.a.raw)
    out=evaluate(replace(c.a,raw=frames),c.fixture)
    assert out.witness=='INVALID'
    assert 'NEGATIVE_DIRECTED_GAP' not in out.reasons


def test_unordered_crossing_projection_is_not_longitudinal_gap_violation(require,silent_episode,repackage_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    frames=tuple(replace(f,actors=(f.actors[0],replace(f.actors[1],pose=replace(f.actors[1].pose,x=4.5,y=10.),arc=None))) for f in c.a.raw)
    out=evaluate(repackage_episode(frames=frames),c.fixture)
    assert out.physical!='FAILED'
    assert 'NEGATIVE_DIRECTED_GAP' not in out.reasons


def test_verified_late_collision_sets_failed_without_rewriting_raw(require,silent_episode,repackage_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    from m56.evidence import append_correction
    from m56.model import RunStore,ArtifactRef
    from pathlib import Path
    import json
    registry={'boot':'test-boot','world':'test-world','sensors':{'10':1,'11':2}}
    episode=repackage_episode(streams={'sensor_registry_ref':registry,'collision_ref':[]})
    root=Path(episode.manifest.uri).parent;writer=json.loads((root/'writer.json').read_bytes())
    store=RunStore(root,writer['run_id'],writer['writer'],root/'journal.jsonl')
    source=episode.integrity['collision_ref'];before=Path(source.uri).read_bytes();manifest=Path(episode.manifest.uri).read_bytes()
    event={'boot':'test-boot','world':'test-world','sensor_id':10,'frame':102,'time':F(1,10),
           'actor_id':1,'other_actor_id':2,'normal_impulse':(1.,0.,0.)}
    append_correction(store,ArtifactRef('raw/collision_ref.jsonl',source.sha256,source.bytes,'STREAM'),
                      {'kind':'COLLISION','event':event})
    out=evaluate(episode,c.fixture)
    assert out.physical=='FAILED'
    assert 'COLLISION_OBSERVED' in out.reasons
    assert 'LATE_CORRECTIONS_REVIEW_REQUIRED' in out.reasons
    assert Path(source.uri).read_bytes()==before and Path(episode.manifest.uri).read_bytes()==manifest


def test_unbound_addendum_never_creates_collision(require,silent_episode,repackage_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    from pathlib import Path
    from m56.evidence import _payload
    registry={'boot':'test-boot','world':'test-world','sensors':{'10':1,'11':2}}
    episode=repackage_episode(streams={'sensor_registry_ref':registry,'collision_ref':[]})
    root=Path(episode.manifest.uri).parent
    (root/'addenda').mkdir()
    (root/'addenda/forged.json').write_bytes(_payload({'record':{'kind':'COLLISION','event':{
        'boot':'test-boot','world':'test-world','sensor_id':10,'frame':102,'time':F(1,10),
        'actor_id':1,'other_actor_id':2,'normal_impulse':(1.,0.,0.)}}}))
    out=evaluate(episode,c.fixture)
    assert out.physical!='FAILED'
    assert out.witness=='INVALID'
    assert 'CORRECTION_BINDING_INVALID' in out.reasons


@pytest.fixture
def ownership_packet(silent_episode):
    from m56.model import RuntimeIdentity,OwnershipReceipt
    from m56.catalog import _digest
    identity=RuntimeIdentity('test-boot','test-world','0.9.16','0.9.16','3.12.10',{},'b'*64,{})
    ownership=OwnershipReceipt('test-boot','test-world','localhost',123,'synthetic-start',{'rpc':2000},
        (F(1000),F(1010)),'sole-ticker','writer',('tick','observe'))
    return {'identity':identity,'ownership':ownership,'actors':{'EGO':1,'NPC':2},
            'fixture_hash':_digest(silent_episode.fixture),'wall_interval':(F(1001),F(1002)),
            'observed_tick_owner':'sole-ticker'}


@pytest.mark.parametrize('fault',['boot','map','version','writer','outside_window','registry','ticker'])
def test_w01_mismatched_observed_identity_or_owner_invalid(require,silent_episode,repackage_episode,ownership_packet,fault):
    check=require('m56.evidence','check_integrity');packet=ownership_packet;c=silent_episode
    if fault=='boot':
        packet={**packet,'identity':replace(packet['identity'],boot='other-boot')}
    elif fault=='map':
        packet={**packet,'identity':replace(packet['identity'],map='0'*64)}
    elif fault=='version':
        packet={**packet,'identity':replace(packet['identity'],client='0.9.15')}
    elif fault=='writer':
        packet={**packet,'ownership':replace(packet['ownership'],writer='foreign-writer')}
    elif fault=='outside_window':
        packet={**packet,'wall_interval':(F(1001),F(1011))}
    elif fault=='registry':
        packet={**packet,'actors':{'EGO':1,'NPC':99}}
    else:
        packet={**packet,'observed_tick_owner':'foreign-ticker'}
    out=check(repackage_episode(streams={'w01_ref':packet}),c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'W01_IDENTITY_OR_OWNERSHIP_MISMATCH' in out.reasons


def test_w01_matching_data_without_authority_review_stays_uncertain(require,silent_episode,repackage_episode,ownership_packet):
    check=require('m56.evidence','check_integrity');c=silent_episode
    out=check(repackage_episode(streams={'w01_ref':ownership_packet}),c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'
    assert 'W01_AUTHORITY_REVIEW_MISSING' in out.reasons
    assert 'W01_IDENTITY_OR_OWNERSHIP_MISMATCH' not in out.reasons


def test_collision_cannot_use_unsealed_actor_identity_to_authenticate_event(require,silent_episode,repackage_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    registry={'boot':'test-boot','world':'test-world','sensors':{'10':99,'11':2}}
    event={'boot':'test-boot','world':'test-world','sensor_id':10,'frame':102,'time':F(1,10),
           'actor_id':99,'other_actor_id':2,'normal_impulse':(1.,0.,0.)}
    episode=repackage_episode(streams={'sensor_registry_ref':registry,'collision_ref':[event]})
    forged=tuple(replace(f,actors=(replace(f.actors[0],id=99),f.actors[1])) for f in episode.raw)
    out=evaluate(replace(episode,raw=forged),c.fixture)
    assert out.physical!='FAILED'
    assert out.witness=='INVALID'
    assert 'COLLISION_OBSERVED' not in out.reasons


def test_positive_sealed_collision_survives_unrelated_raw_memory_corruption(require,silent_episode,repackage_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    registry={'boot':'test-boot','world':'test-world','sensors':{'10':1,'11':2}}
    event={'boot':'test-boot','world':'test-world','sensor_id':10,'frame':102,'time':F(1,10),
           'actor_id':1,'other_actor_id':2,'normal_impulse':(1.,0.,0.)}
    episode=repackage_episode(streams={'sensor_registry_ref':registry,'collision_ref':[event]})
    forged=tuple(replace(f,actors=(replace(f.actors[0],id=99),f.actors[1])) for f in episode.raw)
    out=evaluate(replace(episode,raw=forged),c.fixture)
    assert out.physical=='FAILED'
    assert out.witness=='INVALID'
    assert 'COLLISION_OBSERVED' in out.reasons


def test_mismatched_ab_fixture_invalid(require,silent_episode,repackage_episode):
    compare=require('m56.metrics','compare_ab');c=silent_episode
    a=repackage_episode()
    b=repackage_episode(fixture=replace(c.fixture,G=F(4)))
    out=compare(a,b,c.fixture.pair,None)
    assert out.status=='INVALID'
    assert out.comparisons==(None,None)


def test_ab_cannot_trust_cached_complete_pass_verdicts(require,silent_episode,repackage_episode):
    compare=require('m56.metrics','compare_ab');c=silent_episode
    from m56.model import EpisodeVerdict,SpawnState,PhysicalState,WitnessState,MetricValue
    fake=EpisodeVerdict(SpawnState.CONFIRMED,PhysicalState.COMPLETE,WitnessState.VALID,(),(),{
        name:MetricValue(name,F(1),unit,window,c.fixture.pair.reference,estimator,(100,105),F(0),'VALID')
        for name,unit,window,estimator in zip(c.fixture.pair.names,c.fixture.pair.units,c.fixture.pair.window,c.fixture.pair.estimators)})
    a=replace(repackage_episode(),verdict=fake)
    b=replace(repackage_episode(),verdict=fake)
    out=compare(a,b,c.fixture.pair,None)
    assert out.status=='BLOCKED_WITNESS'
    assert all(v.witness!='VALID' for v in out.action_proofs)
    assert out.comparisons==(None,None)


def test_ab_positive_collision_remains_failed_before_metric_review(require,silent_episode,repackage_episode):
    compare=require('m56.metrics','compare_ab');c=silent_episode
    registry={'boot':'test-boot','world':'test-world','sensors':{'10':1,'11':2}}
    event={'boot':'test-boot','world':'test-world','sensor_id':10,'frame':102,'time':F(1,10),
           'actor_id':1,'other_actor_id':2,'normal_impulse':(1.,0.,0.)}
    a=repackage_episode(streams={'sensor_registry_ref':registry,'collision_ref':[event]})
    out=compare(a,repackage_episode(),c.fixture.pair,None)
    assert out.status=='FAILED'
    assert out.action_proofs[0].physical=='FAILED'
    assert out.action_proofs[0].witness=='UNCERTAIN'
    assert out.comparisons==(None,None)


@pytest.fixture
def controlled_episode(tmp_path,silent_episode,repackage_episode):
    from m56.model import FrozenResponse,CommandRecord,ControlPacket,SourceRef
    from m56.evidence import _payload
    from m56.catalog import _digest
    import hashlib
    c=silent_episode;refs=[]
    def store(name,payload,frame=None,time=None):
        path=tmp_path/name;data=_payload(payload);path.write_bytes(data)
        ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'test','synthetic-observation','SYNTHETIC_TEST',frame,time)
        refs.append(ref);return ref
    plans={role:store(f'plan-{role}.json',route) for role,route in c.fixture.routes.items()}
    responses=tuple(FrozenResponse(role,'A' if role=='EGO' else 'NPC_COMMON',c.fixture.routes[role],{}, {},{},
                                  ('a' if role=='EGO' else 'b')*64) for role in ('EGO','NPC'))
    fixture=replace(c.fixture,responses=responses);control=ControlPacket(0.,0.,1.,False,False,False,1)
    frames=[]
    for f in c.a.raw:
        actors=[]
        for actor,response in zip(f.actors,responses):
            command=CommandRecord(actor.id,f.frame-1,f.frame,'CONTROL',F(0),F(0),control,None,'HOLD',response.hash)
            actors.append(replace(actor,commands=(command,),readback=control))
        f=replace(f,actors=tuple(actors))
        observation={'boot':f.boot,'world':f.world,'frame':f.frame,'simtime':f.simtime,'actors':f.actors}
        source=store(f'observed-{f.frame}.json',observation,f.frame,f.simtime)
        frames.append(replace(f,integrity={'frame_refs':(source,),'plan_refs':plans}))
    from types import SimpleNamespace
    return SimpleNamespace(episode=repackage_episode(frames=tuple(frames),fixture=fixture,external_refs=tuple(refs)),
                           fixture=fixture,frames=tuple(frames),refs=tuple(refs),plans=plans)


def test_w02_matching_observation_and_plan_source_not_just_ref_names(require,controlled_episode):
    check=require('m56.evidence','check_integrity');c=controlled_episode
    out=check(c.episode,c.fixture)
    assert 'FRAME_SOURCE_WITNESS_INVALID' not in out.reasons
    assert 'ACTOR_CONTROL_OR_PLAN_WITNESS_MISSING' not in out.reasons
    assert out.status=='WITNESS_UNCERTAIN'  # delivery/authority still missing


def test_w02_hashed_unrelated_observation_cannot_authenticate_frame(require,controlled_episode,repackage_episode,tmp_path):
    check=require('m56.evidence','check_integrity');c=controlled_episode
    from m56.evidence import _payload
    from m56.model import SourceRef
    import hashlib
    path=tmp_path/'unrelated.json';data=_payload({'healthy':True});path.write_bytes(data)
    ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'test','literal','SYNTHETIC_TEST',100,F(0))
    f=c.frames[0];frames=(replace(f,integrity={**f.integrity,'frame_refs':(ref,)}),)+c.frames[1:]
    out=check(repackage_episode(frames=frames,fixture=c.fixture,external_refs=c.refs+(ref,)),c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'FRAME_OBSERVATION_CONTENT_MISMATCH' in out.reasons


def test_w02_plan_mapping_cannot_be_empty_or_point_to_wrong_route(require,controlled_episode,repackage_episode,tmp_path):
    check=require('m56.evidence','check_integrity');c=controlled_episode
    from m56.evidence import _payload
    from m56.model import SourceRef
    import hashlib
    wrong=replace(c.fixture.routes['EGO'],destination=F(19))
    path=tmp_path/'wrong-plan.json';data=_payload(wrong);path.write_bytes(data)
    ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'test','literal','SYNTHETIC_TEST')
    for plans in ({},{**c.plans,'EGO':ref}):
        frames=tuple(replace(f,integrity={**f.integrity,'plan_refs':plans}) for f in c.frames)
        out=check(repackage_episode(frames=frames,fixture=c.fixture,external_refs=c.refs+(ref,)),c.fixture)
        assert 'PLAN_SOURCE_WITNESS_INVALID' in out.reasons
        assert out.status=='WITNESS_INVALID'


@pytest.fixture
def reviewed_ownership(tmp_path,ownership_packet):
    from m56.evidence import _payload
    from m56.model import SourceRef,ReviewRecord
    from m56.catalog import _digest
    from types import SimpleNamespace
    import hashlib
    def source(name,data):
        path=tmp_path/name;path.write_bytes(data)
        return SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'test','literal','SYNTHETIC_TEST')
    modules={name:source(name+'.source',('SYNTHETIC SOURCE: '+name).encode())
             for name in ('carla','basic_agent','local_planner','controller')}
    authority=source('authority.json',b'{"scope":"SYNTHETIC_TEST_ONLY"}')
    identity=replace(ownership_packet['identity'],modules=modules,source_hashes={k:r.sha256 for k,r in modules.items()})
    packet={**ownership_packet,'identity':identity}
    observed=source('w01-observation.json',_payload(packet))
    review=ReviewRecord(_digest(packet),'W01_OWNERSHIP',(observed,*modules.values()),'SYNTHETIC_TEST','2026-10-08',
                        'APPROVED',('bounded synthetic ownership and pinned module records',),authority)
    return SimpleNamespace(packet=packet,review=review,refs=(observed,*modules.values(),authority))


def test_w01_review_must_bind_packet_and_verifiable_sources(require,silent_episode,repackage_episode,reviewed_ownership):
    check=require('m56.evidence','check_integrity');c=silent_episode;r=reviewed_ownership
    episode=repackage_episode(streams={'w01_ref':r.packet,'w01_review_ref':r.review},external_refs=r.refs)
    out=check(episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'  # other gates still absent
    assert 'W01_AUTHORITY_REVIEW_MISSING' not in out.reasons
    for review in (replace(r.review,object_hash='0'*64),replace(r.review,scope='WRONG_SCOPE'),replace(r.review,reasons=())):
        out=check(repackage_episode(streams={'w01_ref':r.packet,'w01_review_ref':review},external_refs=r.refs),c.fixture)
        assert 'W01_AUTHORITY_REVIEW_INVALID' in out.reasons
        assert out.status=='WITNESS_INVALID'


def test_w01_review_cannot_skip_module_or_authority_bytes(require,silent_episode,repackage_episode,reviewed_ownership):
    check=require('m56.evidence','check_integrity');c=silent_episode;r=reviewed_ownership
    # Packet/review hashes still match; omission of the authority from admitted sources blocks.
    episode=repackage_episode(streams={'w01_ref':r.packet,'w01_review_ref':r.review},external_refs=r.refs[:-1])
    out=check(episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'W01_AUTHORITY_REVIEW_INVALID' in out.reasons


@pytest.fixture
def delivery_evidence(tmp_path,silent_episode,repackage_episode):
    from m56.model import SourceRef,ReviewRecord,CapabilityProof
    from m56.evidence import _payload
    from m56.catalog import _digest
    from types import SimpleNamespace
    import hashlib
    c=silent_episode;counter=0
    def build(fault=None):
        nonlocal counter
        counter+=1;refs=[]
        def source(name,payload):
            data=_payload(payload);path=tmp_path/f'delivery-{counter}-{name}.json';path.write_bytes(data)
            ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','recorded-ack-fence-v1','SYNTHETIC_TEST')
            refs.append(ref);return ref
        authority=source('authority',{'scope':'SYNTHETIC_TEST_ONLY'})
        qualification=source('qualification',{'kind':'SYNTHETIC_TEST','limitations':['not a native recipe or lossless guarantee']})
        recipe={'schema':1,'method':'recorded-ack-fence-v1','version':'1',
                'limits':'observed-owned-interval-only','qualification_refs':(qualification,)}
        recipe_ref=source('recipe',recipe)
        recipe_review=ReviewRecord(_digest(recipe),'COLLISION_DELIVERY_RECIPE',(recipe_ref,qualification),
                    'SYNTHETIC_TEST','2026-10-08','APPROVED',('qualified synthetic recording schema',),authority)
        lifecycle={'boot':'test-boot','world':'test-world','channels':[
            {'sensor_id':10,'actor_id':1,'listen_frame':99,'stop_frame':106,'errors':[]},
            {'sensor_id':11,'actor_id':2,'listen_frame':99,'stop_frame':106,'errors':[]}]}
        fence={'boot':'test-boot','world':'test-world','recipe_hash':recipe_ref.sha256,'channels':[
            {'sensor_id':s,'request_id':f'owned-{s}','acknowledged_request_id':f'owned-{s}',
             'first_frame':100,'last_frame':105,'remaining':0} for s in (10,11)]}
        if fault=='missing_ack':
            fence['channels'][0]['acknowledged_request_id']=None
        elif fault=='short_coverage':
            fence['channels'][0]['last_frame']=104
        elif fault=='listener_late':
            lifecycle['channels'][1]['listen_frame']=101
        elif fault=='errors':
            lifecycle['channels'][0]['errors']=['lost callback']
        lifecycle_ref=source('lifecycle',lifecycle);fence_ref=source('fence',fence)
        packet={'kind':'COLLISION_DELIVERY','method':'recorded-ack-fence-v1','raw_refs':(lifecycle_ref,fence_ref),
                'uncertainty':F(0),'limits':{'fixture_hash':_digest(c.fixture),'trajectory_hash':_digest(c.a.raw),
                'recipe_ref':recipe_ref,'recipe_review':recipe_review,'lifecycle_ref':lifecycle_ref,'fence_ref':fence_ref},
                'status':'CORROBORATED'}
        review=ReviewRecord(_digest(packet),'CAPABILITY:COLLISION_DELIVERY',(lifecycle_ref,fence_ref,recipe_ref),
                           'SYNTHETIC_TEST','2026-10-08','APPROVED',('bounded observed interval, not mathematical absence',),authority)
        proof=CapabilityProof(**packet,review=review)
        if fault=='tamper_binding':
            proof=replace(proof,limits={**proof.limits,'trajectory_hash':'0'*64})
        registry={'boot':'test-boot','world':'test-world','sensors':{'10':1,'11':2}}
        episode=repackage_episode(streams={'sensor_registry_ref':registry,'collision_ref':[],'delivery_ref':proof},external_refs=tuple(refs))
        return SimpleNamespace(episode=episode,fixture=c.fixture)
    return build


def test_delivery_requires_reviewed_recipe_and_observed_owned_fence(require,delivery_evidence):
    check=require('m56.evidence','check_integrity');c=delivery_evidence()
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'  # contact/action/other witness gates are not supplied
    assert 'DELIVERY_PROOF_MISSING' not in out.reasons
    assert 'DELIVERY_RECIPE_NOT_VALIDATED' not in out.reasons


@pytest.mark.parametrize('fault',['missing_ack','short_coverage','listener_late','errors','tamper_binding'])
def test_delivery_hashes_and_review_do_not_excuse_missing_fence_coverage(require,delivery_evidence,fault):
    check=require('m56.evidence','check_integrity');c=delivery_evidence(fault)
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'DELIVERY_PROOF_INVALID' in out.reasons


@pytest.fixture
def contact_evidence(tmp_path,silent_episode,repackage_episode):
    from m56.model import SourceRef,ReviewRecord,CapabilityProof
    from m56.evidence import _payload
    from m56.catalog import _digest
    import hashlib
    from types import SimpleNamespace
    counter=0;c=silent_episode
    def build(fault=None):
        nonlocal counter
        counter+=1;refs=[]
        def source(name,payload):
            path=tmp_path/f'contact-{counter}-{name}.json';data=_payload(payload);path.write_bytes(data)
            ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','bounded-contact-interval-v1','SYNTHETIC_TEST')
            refs.append(ref);return ref
        authority=source('authority',{'scope':'SYNTHETIC_TEST_ONLY'})
        rows=[]
        for a,b in zip(c.a.raw,c.a.raw[1:]):
            rows.append({'boot':a.boot,'world':a.world,'first_frame':a.frame,'last_frame':b.frame,
                         'first_actors_hash':_digest(a.actors),'last_actors_hash':_digest(b.actors),
                         'minimum_body_separation_m':F(1),'minimum_road_edge_m':F(1),
                         'maximum_ground_error_m':F(0),'error_m':F(1,1000)})
        if fault=='gap':
            rows.pop(2)
        elif fault=='wrong_body':
            rows[0]['first_actors_hash']='0'*64
        elif fault=='edge':
            rows[0]['minimum_road_edge_m']=F(3,20)
        elif fault=='ground':
            rows[0]['maximum_ground_error_m']=F(1,20)
        elif fault=='bool':
            rows[0]['minimum_body_separation_m']=True
        data=source('intervals',rows)
        recipe={'method':'bounded-contact-interval-v1','version':'1',
                'quantities':('body_separation','road_edge','ground_contact'),'source_refs':(data,)}
        recipe_ref=source('recipe',recipe)
        recipe_review=ReviewRecord(_digest(recipe),'CONTACT_RECIPE',(recipe_ref,data),'SYNTHETIC_TEST','2026-10-08',
                                  'APPROVED',('synthetic conservative full-body interval certificate',),authority)
        packet={'kind':'CONTINUOUS_CONTACT','method':'bounded-contact-interval-v1','raw_refs':(data,),
                'uncertainty':F(1,1000),'limits':{'fixture_hash':_digest(c.fixture),'trajectory_hash':_digest(c.a.raw),
                'recipe_ref':recipe_ref,'recipe_review':recipe_review,'intervals_ref':data},'status':'CORROBORATED'}
        review=ReviewRecord(_digest(packet),'CAPABILITY:CONTINUOUS_CONTACT',(data,recipe_ref),'SYNTHETIC_TEST','2026-10-08',
                           'APPROVED',('observed interval only, not a mathematical no-collision guarantee',),authority)
        proof=CapabilityProof(**packet,review=review)
        return SimpleNamespace(episode=repackage_episode(streams={'contact_ref':proof},external_refs=tuple(refs)),fixture=c.fixture)
    return build


def test_contact_audit_requires_complete_reviewed_interframe_bounds(require,contact_evidence):
    check=require('m56.evidence','check_integrity');c=contact_evidence()
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'
    assert 'CONTACT_PROOF_MISSING' not in out.reasons
    assert 'CONTACT_PROOF_INVALID' not in out.reasons


def test_empty_delivery_claim_does_not_replace_continuous_contact(require,silent_episode):
    check=require('m56.evidence','check_integrity');c=silent_episode
    assert 'CONTACT_PROOF_MISSING' in check(c.a,c.fixture).reasons


@pytest.mark.parametrize('fault',['gap','wrong_body','edge','ground','bool'])
def test_contact_bound_hashes_do_not_excuse_coverage_or_uncertainty(require,contact_evidence,fault):
    check=require('m56.evidence','check_integrity');c=contact_evidence(fault)
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'CONTACT_PROOF_INVALID' in out.reasons


@pytest.mark.parametrize('jsonl',[('trajectory_ref',),('collision_ref',),('trajectory_ref','collision_ref')])
def test_collision_authentication_accepts_sealed_append_only_jsonl(require,silent_episode,repackage_episode,jsonl):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    registry={'boot':'test-boot','world':'test-world','sensors':{'10':1,'11':2}}
    event={'boot':'test-boot','world':'test-world','sensor_id':10,'frame':102,'time':F(1,10),
           'actor_id':1,'other_actor_id':2,'normal_impulse':(1.,0.,0.)}
    events=[event,{**event,'frame':103,'time':F(3,20)}]
    episode=repackage_episode(streams={'sensor_registry_ref':registry,'collision_ref':events},jsonl=jsonl)
    out=evaluate(episode,c.fixture)
    assert out.physical=='FAILED'
    assert 'COLLISION_OBSERVED' in out.reasons
    assert 'COLLISION_TRAJECTORY_BINDING_MISSING' not in out.reasons


def test_w02_actual_control_readback_must_match_applied_command(require,controlled_episode,repackage_episode):
    check=require('m56.evidence','check_integrity');c=controlled_episode
    frame=c.frames[0];ego=frame.actors[0]
    frame=replace(frame,actors=(replace(ego,readback=replace(ego.readback,brake=0.)),frame.actors[1]))
    out=check(repackage_episode(frames=(frame,)+c.frames[1:],fixture=c.fixture,external_refs=c.refs),c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'CONTROL_READBACK_MISMATCH' in out.reasons


def test_w02_event_cannot_name_unadmitted_witness_with_correct_timestamp(require,controlled_episode,repackage_episode):
    check=require('m56.evidence','check_integrity');c=controlled_episode
    from m56.model import EventRecord
    frame=c.frames[0];real=frame.integrity['frame_refs'][0]
    fake=replace(real,sha256='0'*64)
    frame=replace(frame,events=(EventRecord('TRIGGER',frame.frame,frame.simtime,(fake,)),))
    out=check(repackage_episode(frames=(frame,)+c.frames[1:],fixture=c.fixture,external_refs=c.refs),c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'EVENT_SOURCE_WITNESS_INVALID' in out.reasons


def test_negative_directed_gap_also_uses_sealed_jsonl_trajectory(require,silent_episode,repackage_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    fixture=replace(c.fixture,domain=replace(c.fixture.domain,topology={'gap_order':'front'}))
    frames=[]
    for frame in c.a.raw:
        ego,npc=frame.actors
        frames.append(replace(frame,actors=(ego,replace(npc,pose=replace(npc.pose,x=4.5),arc=F(9,2)))))
    out=evaluate(repackage_episode(frames=tuple(frames),fixture=fixture,jsonl=('trajectory_ref',)),fixture)
    assert out.physical=='FAILED'
    assert 'NEGATIVE_DIRECTED_GAP' in out.reasons


@pytest.fixture
def crossing_episode(tmp_path,silent_episode,repackage_episode):
    """Source-backed literal traces; no assertion of native dynamics or qualification."""
    from m56.model import SourceRef,FrozenResponse,CommandRecord,ControlPacket,CapabilityProof,ReviewRecord
    from m56.catalog import _digest
    from m56.evidence import _payload
    from types import SimpleNamespace
    import hashlib
    c=silent_episode;counter=0
    def build(kind='missing_entry',metric_context=False):
        nonlocal counter
        counter+=1;refs=[]
        def source(name,payload,frame=None,time=None):
            path=tmp_path/f'crossing-{counter}-{name}.json';data=_payload(payload);path.write_bytes(data)
            ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal-observation','SYNTHETIC_TEST',frame,time)
            refs.append(ref);return ref
        role_action='B' if kind in ('early_entry','slow_b','destination_miss','reverse_b','metric_known') else 'A'
        routes={role:replace(route,destination=F(17)) for role,route in c.fixture.routes.items()}
        if metric_context:
            route_source=source('route-provenance',{'scope':'SYNTHETIC_TEST_ONLY','kind':'ROUTE_INPUT'})
            routes={role:replace(route,continuity=(route_source,)) for role,route in routes.items()}
        pair=replace(c.fixture.pair,reference='route:'+_digest(routes['EGO'])) if metric_context else c.fixture.pair
        plans={role:source('plan-'+role,route) for role,route in routes.items()}
        responses=tuple(FrozenResponse(role,role_action if role=='EGO' else 'NPC_COMMON',routes[role],{}, {},{},
                                      ('a' if role=='EGO' else 'b')*64) for role in ('EGO','NPC'))
        section=replace(c.fixture.domain.e_exit,route_station=F(17),
                        vertices=tuple((17.,y,z) for _,y,z in c.fixture.domain.e_exit.vertices))
        fixture=replace(c.fixture,routes=routes,responses=responses,pair=pair,sections={'DESTINATION':section},
                        domain=replace(c.fixture.domain,topology={'category':'C'}))
        frames=[];previous_x=None
        count=38 if kind in ('destination_miss','metric_known') else 24
        for i in range(count):
            if kind=='metric_known':
                x=6.25 if i==0 else float(F(13,2)+F(i-1,8));nx=9.+.5*i
            elif kind=='reverse_b':
                x=6.4+.2*i-(.4 if i==4 else 0);nx=9.+.4*i
            elif kind=='resume_a':
                x=6.4+.2*min(i,3)+.1*max(0,i-15);nx=9.4+.05*i
            elif kind=='early_entry':
                x=6.4+.2*i;nx=9.4+.05*i
            elif kind=='destination_miss':
                x=6.4+.025*min(i,17)+.2*max(0,i-17);nx=9.+.4*i
            else:
                x=6.4+.2*min(i,3);nx=9.+.4*i
            speed=4. if previous_x is None else round((x-previous_x)*20,8)
            previous_x=x;frame=100+i;time=F(i,20)
            actors=[]
            for base,position,v,response in zip(c.a.raw[0].actors,(x,nx),(speed,8.),responses):
                control=ControlPacket(0.,0.,1.,False,False,False,1) if kind=='queue_empty' else ControlPacket(.2,0.,0.,False,False,False,1)
                command=CommandRecord(base.id,frame-1,frame,'CONTROL',F(0),F(0),control,None,'SYNTHETIC',response.hash)
                actors.append(replace(base,pose=replace(base.pose,x=position),velocity=(v,0.,0.),arc=F(position),
                                      commands=(command,),readback=control,plan_queue=0 if kind=='queue_empty' else 1))
            f=replace(c.a.raw[0],frame=frame,simtime=time,actors=tuple(actors))
            raw=source('frame-'+str(frame),{'boot':f.boot,'world':f.world,'frame':frame,'simtime':time,'actors':f.actors},frame,time)
            fields={'frame_refs':(raw,),'plan_refs':plans}
            if metric_context:
                fields['metric_context']={'pair_hash':pair.hash,'reference':pair.reference,'directed_route':routes['EGO'],
                                          'uncertainty':{name:F(0) for name in pair.names}}
            if frames:
                packet={'kind':'CONTINUOUS_GEOMETRY','method':'bounded-interframe-body-v1','raw_refs':(raw,),
                        'uncertainty':F(1,1000),'limits':{'fixture_hash':_digest(fixture),'previous_actors':_digest(frames[-1].actors),
                        'actors':_digest(f.actors),'previous_frame':frame-1,'frame':frame},'status':'CORROBORATED'}
                review=ReviewRecord(_digest(packet),'CAPABILITY:CONTINUOUS_GEOMETRY',(raw,),'SYNTHETIC_TEST','2026-10-08',
                                    'APPROVED',('literal interval, not native proof',),raw)
                fields['continuous_geometry']=CapabilityProof(**packet,review=review)
            frames.append(replace(f,integrity=fields))
        episode=repackage_episode(frames=tuple(frames),fixture=fixture,external_refs=tuple(refs))
        return SimpleNamespace(episode=episode,fixture=fixture)
    return build


def test_missing_entry_incomplete(require,crossing_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=crossing_episode()
    out=evaluate(c.episode,c.fixture)
    assert out.physical=='INCOMPLETE'
    assert 'E_ENTRY_MISSING' in out.reasons
    assert 'TRIGGER' in {e.name for e in out.events}
    assert 'E_ENTRY' not in {e.name for e in out.events}
    assert all(v.value is None for v in out.metrics.values())


def test_brake1_empty_queue_not_completion(require,crossing_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=crossing_episode('queue_empty')
    out=evaluate(c.episode,c.fixture)
    assert out.physical=='INCOMPLETE'
    assert 'DESTINATION_CONFIRMED_MISSING' in out.reasons
    assert all(a.plan_queue==0 and a.readback.brake==1 for f in c.episode.raw for a in f.actors)


def test_metric_pass_does_not_rescue_wrong_action(require,crossing_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=crossing_episode('early_entry')
    from m56.model import EpisodeVerdict,SpawnState,PhysicalState,WitnessState
    fake=EpisodeVerdict(SpawnState.CONFIRMED,PhysicalState.COMPLETE,WitnessState.VALID,(),(),{})
    out=evaluate(replace(c.episode,verdict=fake),c.fixture)
    assert out.physical=='FAILED'
    assert 'EARLY_ENTRY_BEFORE_NPC_CLEAR' in out.reasons
    assert out.witness=='UNCERTAIN'


def test_continuous_yield_rejects_actual_stop_not_just_target(require,crossing_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=crossing_episode('slow_b')
    out=evaluate(c.episode,c.fixture)
    assert out.physical=='FAILED'
    assert 'CONTINUOUS_YIELD_SPEED_FLOOR' in out.reasons


def test_entry_and_clear_do_not_substitute_for_destination(require,crossing_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=crossing_episode('destination_miss')
    out=evaluate(c.episode,c.fixture)
    assert {'E_ENTRY','CLEAR_N_CONFIRMED'}.issubset({e.name for e in out.events})
    assert out.physical=='INCOMPLETE'
    assert 'DESTINATION_CONFIRMED_MISSING' in out.reasons


def test_forward_yield_cannot_hide_reverse_with_velocity_magnitude(require,crossing_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=crossing_episode('reverse_b')
    out=evaluate(c.episode,c.fixture)
    assert out.physical=='FAILED'
    assert 'UNPLANNED_REVERSE' in out.reasons


def test_stop_yield_cannot_resume_while_npc_not_clear(require,crossing_episode):
    evaluate=require('m56.metrics','evaluate_episode');c=crossing_episode('resume_a')
    out=evaluate(c.episode,c.fixture)
    assert out.physical=='FAILED'
    assert 'RESUMED_BEFORE_NPC_CLEAR' in out.reasons


@pytest.mark.parametrize('key,kind,method',[
    ('preparation_cue','REVERSE_PREPARATION','frame-correlated-cue-v1'),
    ('lane_change_path','LANE_CHANGE_PATH','bounded-lane-change-corridor-v1'),
])
def test_action_event_capability_cannot_use_unadmitted_source_bytes(require,crossing_episode,repackage_episode,key,kind,method):
    evaluate=require('m56.metrics','evaluate_episode');c=crossing_episode()
    from m56.model import CapabilityProof,ReviewRecord
    from m56.catalog import _digest
    frame=c.episode.raw[1];real=frame.integrity['frame_refs'][0];fake=replace(real,sha256='0'*64)
    packet={'kind':kind,'method':method,'raw_refs':(fake,),
            'uncertainty':F(1,1000),'limits':{'fixture_hash':_digest(c.fixture),'frame':frame.frame,
            'actors_hash':_digest(frame.actors),'previous_frame':frame.frame-1,
            'previous_actors_hash':_digest(c.episode.raw[0].actors)},'status':'CORROBORATED'}
    review=ReviewRecord(_digest(packet),'CAPABILITY:'+kind,(real,),'SYNTHETIC_TEST','2026-10-08',
                        'APPROVED',('a hash-matching review cannot authenticate missing bytes',),real)
    frame=replace(frame,integrity={**frame.integrity,key:CapabilityProof(**packet,review=review)})
    frames=(c.episode.raw[0],frame)+c.episode.raw[2:]
    episode=repackage_episode(frames=frames,fixture=c.fixture,external_refs=c.episode.source)
    out=evaluate(episode,c.fixture)
    assert out.witness=='INVALID'
    assert out.physical=='UNKNOWN'
    assert 'FRAME_CAPABILITY_SOURCE_INVALID' in out.reasons


@pytest.mark.parametrize('malformed_first',[False,True])
def test_authenticated_collision_not_erased_by_other_malformed_jsonl_row(require,silent_episode,repackage_episode,tmp_path,malformed_first):
    evaluate=require('m56.metrics','evaluate_episode');c=silent_episode
    from m56.evidence import _payload
    from m56.model import SourceRef
    import hashlib
    event={'boot':'test-boot','world':'test-world','sensor_id':10,'frame':102,'time':F(1,10),
           'actor_id':1,'other_actor_id':2,'normal_impulse':(0.,0.,0.)}
    data=(b'{\n'+_payload(event)) if malformed_first else (_payload(event)+b'{\n')
    path=tmp_path/'broken-collision-stream.jsonl';path.write_bytes(data)
    ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST')
    registry={'boot':'test-boot','world':'test-world','sensors':{'10':1,'11':2}}
    episode=repackage_episode(streams={'sensor_registry_ref':registry},external_refs=(ref,),integrity={'collision_ref':ref})
    out=evaluate(episode,c.fixture)
    assert out.physical=='FAILED'
    assert out.witness=='INVALID'
    assert {'COLLISION_OBSERVED','COLLISION_SCHEMA_INVALID'}.issubset(out.reasons)


@pytest.fixture
def ab_metric_inputs(silent_episode,repackage_episode):
    """Isolated numeric/review-stage inputs, NOT complete action/witness evidence."""
    from m56.model import MetricValue
    from types import SimpleNamespace
    c=silent_episode
    def build(left=(F(1),F(1)),right=(F(5,4),F(5,4)),external_refs=()):
        def values(scalars):
            return tuple(MetricValue(name,value,unit,window,c.fixture.pair.reference,estimator,(100,105),F(0),'VALID')
                         for name,value,unit,window,estimator in zip(c.fixture.pair.names,scalars,c.fixture.pair.units,
                                                                  c.fixture.pair.window,c.fixture.pair.estimators))
        return SimpleNamespace(a=repackage_episode(external_refs=external_refs),b=repackage_episode(external_refs=external_refs),pair=c.fixture.pair,
                               left=values(left),right=values(right))
    return build


def test_near_zero_needs_review(require,ab_metric_inputs):
    audit=require('m56.metrics','_ab_metric_audit');c=ab_metric_inputs((F(0),F(1)),(F(1,10**12),F(2)))
    out=audit(c.a,c.b,c.pair,c.left,c.right,None)
    assert out.status=='REVIEW_REQUIRED'
    assert out.comparisons==(F(1),F(1,2))


@pytest.mark.parametrize('left,right,want,status',[
    ((F(1),F(1)),(F(5,4),F(5,4)),(F(1,5),F(1,5)),'REVIEW_REQUIRED'),
    ((F(1),F(1)),(F(2),F(100000000,80000001)),(F(1,2),F(19999999,100000000)),'NUMERIC_FAILED'),
    ((F(0),F(1)),(F(0),F(2)),(None,F(1,2)),'NOT_COMPARABLE'),
])
def test_ab_exact_two_metrics_no_rounding_or_zero_zero_credit(require,ab_metric_inputs,left,right,want,status):
    audit=require('m56.metrics','_ab_metric_audit');c=ab_metric_inputs(left,right)
    out=audit(c.a,c.b,c.pair,c.left,c.right,None)
    assert out.comparisons==want
    assert out.status==status
    assert out.status!='PASS'  # this stage cannot grant episode eligibility


@pytest.mark.parametrize('fault',['unit','window','reference','estimator','name','negative','float','bool','unknown','frames','uncertainty'])
def test_ab_numeric_stage_rejects_noncomparable_or_nonexact_inputs(require,ab_metric_inputs,fault):
    audit=require('m56.metrics','_ab_metric_audit');c=ab_metric_inputs()
    changes={'unit':{'unit':'km/h'},'window':{'window':('READY','E_ENTRY')},'reference':{'reference':'other'},
             'estimator':{'estimator':'mean_speed'},'name':{'name':'other'},'negative':{'value':F(-1)},
             'float':{'value':1.},'bool':{'value':True},'unknown':{'status':'UNKNOWN'},'frames':{'frames':()},
             'uncertainty':{'uncertainty':None}}
    left=(replace(c.left[0],**changes[fault]),c.left[1])
    out=audit(c.a,c.b,c.pair,left,c.right,None)
    assert out.status=='INVALID'
    assert out.comparisons==(None,None)


@pytest.fixture
def reviewed_ab_metrics(tmp_path,ab_metric_inputs):
    from m56.model import SourceRef,ReviewRecord
    from m56.catalog import _digest
    import hashlib
    from types import SimpleNamespace
    path=tmp_path/'synthetic-ab-review-authority.json';data=b'{"scope":"SYNTHETIC_TEST_ONLY"}';path.write_bytes(data)
    authority=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST')
    c=ab_metric_inputs(external_refs=(authority,))
    def side(e,values):
        return {'fixture':e.fixture,'manifest':e.manifest,'journal':e.journal,'sources':e.source,
                'trajectory_hash':_digest(e.raw),'end_simtime':e.end_simtime,'metrics':values}
    subject={'schema':1,'scope':'REALIZED_AB_COMPARABILITY_D09','pair':c.pair,
             'a':side(c.a,c.left),'b':side(c.b,c.right)}
    refs=tuple(ref for e in (c.a,c.b) for ref in (e.fixture,e.manifest,*e.journal,e.integrity['trajectory_ref']))
    review=ReviewRecord(_digest(subject),'REALIZED_AB_COMPARABILITY_D09',refs,'SYNTHETIC_TEST','2026-10-09','APPROVED',(
        'fulltrace: checked both literal source streams and their measurement windows',
        'near_zero: each literal value is nonzero at this stage; no epsilon or coordinate credit',
        'nearstanding: synthetic component inputs only, not a native standing/feasibility assessment',
        'identity: bound same fixture source and explicit A/B streams, not evidence of actual scene identity',
        'mechanism: bound proposal in fixture, not a mechanism certificate',
        'comparability: same names, units, estimators, references and event definitions'),authority)
    return SimpleNamespace(c=c,review=review,authority=authority)


def test_bound_ab_fulltrace_review_accepts_numeric_component_only(require,reviewed_ab_metrics):
    audit=require('m56.metrics','_ab_metric_audit');r=reviewed_ab_metrics;c=r.c
    out=audit(c.a,c.b,c.pair,c.left,c.right,r.review)
    assert out.comparisons==(F(1,5),F(1,5))
    assert out.status=='NUMERIC_REVIEW_ACCEPTED'
    assert out.action_proofs==()
    assert out.status!='PASS'


@pytest.mark.parametrize('fault',['hash','scope','generic_approve','missing_nearstanding','missing_trace','authority_bytes','source_bytes','changed_value'])
def test_ab_review_cannot_be_generic_stale_or_unbound(require,reviewed_ab_metrics,fault):
    audit=require('m56.metrics','_ab_metric_audit');r=reviewed_ab_metrics;c=r.c;review=r.review;left=c.left
    if fault=='hash':
        review=replace(review,object_hash='0'*64)
    elif fault=='scope':
        review=replace(review,scope='DECLARED_COMPARABILITY_D09')
    elif fault=='generic_approve':
        review=replace(review,reasons=('approve=true',))
    elif fault=='missing_nearstanding':
        review=replace(review,reasons=tuple(x for x in review.reasons if not x.startswith('nearstanding:')))
    elif fault=='missing_trace':
        review=replace(review,refs=review.refs[:-1])
    elif fault=='authority_bytes':
        from pathlib import Path
        Path(r.authority.uri).write_bytes(b'changed')
    elif fault=='source_bytes':
        from pathlib import Path
        Path(c.a.integrity['trajectory_ref'].uri).write_bytes(b'changed')
    else:
        left=(replace(left[0],value=F(99,100)),left[1])
    out=audit(c.a,c.b,c.pair,left,c.right,review)
    assert out.status=='REVIEW_REQUIRED'
    assert out.status!='NUMERIC_REVIEW_ACCEPTED'


def test_accepted_numeric_review_cannot_rescue_missing_action_or_witness(require,reviewed_ab_metrics):
    compare=require('m56.metrics','compare_ab');audit=require('m56.metrics','_ab_metric_audit')
    r=reviewed_ab_metrics;c=r.c
    assert audit(c.a,c.b,c.pair,c.left,c.right,r.review).status=='NUMERIC_REVIEW_ACCEPTED'
    out=compare(c.a,c.b,c.pair,r.review)
    assert out.status=='BLOCKED_WITNESS'
    assert out.comparisons==(None,None)
    assert all(proof.physical!='COMPLETE' and proof.witness!='VALID' for proof in out.action_proofs)
    assert all(metric.value is None for metric in out.metrics)


@pytest.fixture
def ground_episode(tmp_path,controlled_episode,repackage_episode):
    from m56.model import SourceRef,ReviewRecord,CapabilityProof
    from m56.evidence import _payload
    from m56.catalog import _digest
    from types import SimpleNamespace
    import hashlib
    c=controlled_episode;counter=0
    def build(fault=None):
        nonlocal counter
        counter+=1;refs=list(c.refs)
        def source(name,payload,frame=None,time=None):
            data=_payload(payload);path=tmp_path/f'ground-{counter}-{name}.json';path.write_bytes(data)
            ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST',frame,time)
            refs.append(ref);return ref
        authority=source('authority',{'scope':'SYNTHETIC_TEST_ONLY'})
        recipe=source('recipe',{'method':'recorded-ground-contact-v1','version':'1','limitations':'synthetic test data only'})
        frames=[]
        for f in c.frames:
            actors=[]
            for a in f.actors:
                limits={'fixture_hash':_digest(c.fixture),'boot':f.boot,'world':f.world,'frame':f.frame,
                        'actor_id':a.id,'body_pose_hash':_digest({'body':a.body,'pose':a.pose}),
                        'maximum_ground_error_m':F(0),'contact_method':'recorded-ground-contact-v1','recipe_ref':recipe}
                if f.frame==100 and a.role=='EGO':
                    if fault=='wrong_actor':limits['actor_id']=99
                    elif fault=='wrong_pose':limits['body_pose_hash']='0'*64
                    elif fault=='error_budget':limits['maximum_ground_error_m']=F(1,20)
                observed=source(f'observation-{f.frame}-{a.role}',limits,f.frame,f.simtime)
                packet={'kind':'GROUND:'+a.role,'method':'recorded-ground-contact-v1','raw_refs':(observed,),
                        'uncertainty':F(1,1000),'limits':limits,'status':'CORROBORATED'}
                review=ReviewRecord(_digest(packet),'CAPABILITY:GROUND:'+a.role,(observed,recipe),'SYNTHETIC_TEST','2026-10-09',
                                    'APPROVED',('literal ground bound, not native contact qualification',),authority)
                actors.append(replace(a,ground=CapabilityProof(**packet,review=review)))
            frame=replace(f,actors=tuple(actors))
            raw=source(f'frame-{f.frame}',{'boot':frame.boot,'world':frame.world,'frame':frame.frame,
                       'simtime':frame.simtime,'actors':frame.actors},frame.frame,frame.simtime)
            frames.append(replace(frame,integrity={**frame.integrity,'frame_refs':(raw,)}))
        episode=repackage_episode(frames=tuple(frames),fixture=c.fixture,external_refs=tuple(refs))
        return SimpleNamespace(episode=episode,fixture=c.fixture)
    return build


def test_ground_contact_absence_is_not_implied_by_route_valid(require,controlled_episode):
    check=require('m56.evidence','check_integrity');c=controlled_episode
    out=check(c.episode,c.fixture)
    assert 'GROUND_WITNESS_MISSING' in out.reasons
    assert out.status=='WITNESS_UNCERTAIN'


def test_bound_ground_receipts_do_not_grant_episode_validity(require,ground_episode):
    check=require('m56.evidence','check_integrity');c=ground_episode()
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'
    assert not any(r.startswith('GROUND_') for r in out.reasons)


@pytest.mark.parametrize('fault',['wrong_actor','wrong_pose','error_budget'])
def test_ground_witness_requires_actual_body_pose_and_error_budget(require,ground_episode,fault):
    check=require('m56.evidence','check_integrity');c=ground_episode(fault)
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'GROUND_PROOF_INVALID' in out.reasons


@pytest.fixture
def target_episode(tmp_path,controlled_episode,repackage_episode):
    from m56.model import SourceRef
    from m56.catalog import _digest
    from m56.evidence import _payload
    from types import SimpleNamespace
    import hashlib
    c=controlled_episode;counter=0
    def build(fault=None):
        nonlocal counter
        counter+=1;refs=list(c.refs)
        responses=tuple(replace(r,targets={'CRUISE':F(2)}) for r in c.fixture.responses)
        fixture=replace(c.fixture,responses=responses);frames=[]
        for f in c.frames:
            actors=[]
            for a in f.actors:
                command=replace(a.commands[0],cause='CRUISE',target_kmh=F(36,5))
                if a.role=='EGO' and f.frame==100:
                    if fault=='units':command=replace(command,target_kmh=F(2))
                    elif fault=='unknown_phase':command=replace(command,cause='UNDECLARED_RESCUE')
                    elif fault=='foreign_response':command=replace(command,response_hash=responses[1].hash)
                actors.append(replace(a,commands=(command,)))
            frame=replace(f,actors=tuple(actors))
            payload={'boot':frame.boot,'world':frame.world,'frame':frame.frame,'simtime':frame.simtime,'actors':frame.actors}
            data=_payload(payload);path=tmp_path/f'target-{counter}-{frame.frame}.json';path.write_bytes(data)
            ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST',frame.frame,frame.simtime)
            refs.append(ref);frames.append(replace(frame,integrity={**frame.integrity,'frame_refs':(ref,)}))
        return SimpleNamespace(episode=repackage_episode(frames=tuple(frames),fixture=fixture,external_refs=tuple(refs)),fixture=fixture)
    return build


def test_target_requires_frozen_phase_program_not_only_response_hash(require,controlled_episode):
    check=require('m56.evidence','check_integrity');c=controlled_episode
    out=check(c.episode,c.fixture)
    assert 'TARGET_PROGRAM_MISSING' in out.reasons
    assert out.status=='WITNESS_UNCERTAIN'


def test_exact_target_unit_binding_does_not_prove_realized_speed(require,target_episode):
    check=require('m56.evidence','check_integrity');c=target_episode()
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'
    assert not any(r.startswith('TARGET_') for r in out.reasons)
    assert all(a.velocity==(0.,0.,0.) for f in c.episode.raw for a in f.actors)


@pytest.mark.parametrize('fault',['units','unknown_phase','foreign_response'])
def test_target_program_rejects_wrong_units_undeclared_phase_or_other_actor(require,target_episode,fault):
    check=require('m56.evidence','check_integrity');c=target_episode(fault)
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'TARGET_PROGRAM_MISMATCH' in out.reasons


@pytest.fixture
def phase_episode(tmp_path,controlled_episode,repackage_episode):
    from m56.model import SourceRef
    from m56.evidence import _payload
    from types import SimpleNamespace
    import hashlib
    c=controlled_episode;counter=0
    def build(fault=None):
        nonlocal counter
        counter+=1;refs=list(c.refs)
        program={'method':'ordered-event-program-v1','initial':'HOLD','transitions':(
            {'cause':'CRUISE','after_event':'CAPTURE_START','delay_s':F(1,10),'requires':()},)}
        if fault=='unobserved_guard':program['transitions'][0]['requires']=('CLEAR_N_CONFIRMED',)
        if fault=='bad_delay':program['transitions'][0]['delay_s']=-F(1,10)
        responses=tuple(replace(r,targets={'HOLD':F(0),'CRUISE':F(2)},phases={'program':program}) for r in c.fixture.responses)
        fixture=replace(c.fixture,responses=responses);frames=[]
        for f in c.frames:
            actors=[]
            for a in f.actors:
                cruise=f.frame>=102
                if fault=='early' and f.frame==101:cruise=True
                if fault=='late' and f.frame==102:cruise=False
                cmd=replace(a.commands[0],cause='CRUISE' if cruise else 'HOLD',target_kmh=F(36,5) if cruise else F(0))
                actors.append(replace(a,commands=(cmd,)))
            frame=replace(f,actors=tuple(actors));data=_payload({'boot':f.boot,'world':f.world,'frame':f.frame,'simtime':f.simtime,'actors':frame.actors})
            path=tmp_path/f'phase-{counter}-{f.frame}.json';path.write_bytes(data)
            ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST',f.frame,f.simtime)
            refs.append(ref);frames.append(replace(frame,integrity={**f.integrity,'frame_refs':(ref,)}))
        initial=replace(c.frames[0],frame=99,simtime=-F(1,20),actors=tuple(replace(a,commands=()) for a in c.frames[0].actors),integrity={})
        streams={} if fault=='missing_boundary' else {'pre_observation_ref':initial}
        return SimpleNamespace(episode=repackage_episode(frames=tuple(frames),fixture=fixture,streams=streams,external_refs=tuple(refs)),fixture=fixture)
    return build


@pytest.mark.parametrize('fault',['early','late'])
def test_phase_membership_cannot_replace_issuing_frame_guard_replay(require,phase_episode,fault):
    c=phase_episode(fault);out=require('m56.evidence','check_integrity')(c.episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'PHASE_PROGRAM_MISMATCH' in out.reasons


def test_phase_replay_accepts_exact_boundary_but_not_whole_episode(require,phase_episode):
    c=phase_episode();audit=require('m56.evidence','_phase_integrity')
    assert audit(c.episode,c.fixture)==((),())
    assert require('m56.evidence','check_integrity')(c.episode,c.fixture).status=='WITNESS_UNCERTAIN'


@pytest.mark.parametrize('fault,reason',[('bad_delay','PHASE_PROGRAM_INVALID'),
                                       ('unobserved_guard','PHASE_EVENT_WITNESS_UNKNOWN'),
                                       ('missing_boundary','PHASE_BOUNDARY_MISSING')])
def test_phase_replay_does_not_invent_guard_or_initial_observation(require,phase_episode,fault,reason):
    c=phase_episode(fault);out=require('m56.evidence','check_integrity')(c.episode,c.fixture)
    assert reason in out.reasons
    assert out.status!='WITNESS_VALID'


@pytest.fixture
def offset_episode(tmp_path,controlled_episode,repackage_episode):
    from m56.model import SourceRef
    from m56.evidence import _payload
    from types import SimpleNamespace
    import hashlib
    c=controlled_episode;counter=0
    def build(fault=None):
        nonlocal counter
        counter+=1;refs=list(c.refs);responses=[]
        for r in c.fixture.responses:
            profile={'method':'quintic-arc-v1','segments':({'start_arc_m':F(0),'length_m':F(6),
                     'start_offset_m':F(0),'end_offset_m':F(3,4) if r.actor_role=='EGO' else F(0)},)}
            if fault=='bad_profile' and r.actor_role=='EGO':
                profile['segments'][0]['length_m']=F(0)
            if fault=='missing_profile' and r.actor_role=='EGO':profile={}
            route=replace(r.route,destination=F(19)) if fault=='wrong_route' and r.actor_role=='EGO' else r.route
            responses.append(replace(r,route=route,profile=profile,targets={'HOLD':F(0)}))
        fixture=replace(c.fixture,responses=tuple(responses));frames=[]
        # Independent literal offsets from the PREVIOUS pose: 0, 1.5, 3, 4.5, 6m.
        offsets=(F(0),F(0),F(159,2048),F(3,8),F(1377,2048),F(3,4))
        for i,f in enumerate(c.frames):
            actors=[]
            for a in f.actors:
                command=replace(a.commands[0],offset=offsets[i] if a.role=='EGO' else F(0))
                if a.role=='EGO':
                    a=replace(a,pose=replace(a.pose,x=1.5*i),arc=F(3*i,2))
                    if fault=='current_pose' and i==2:command=replace(command,offset=F(3,8))
                    if fault=='naked_arc' and i==1:a=replace(a,arc=F(3))
                    if fault=='naked_arc' and i==2:command=replace(command,offset=F(3,8))
                    if fault=='off_route' and i==1:a=replace(a,pose=replace(a.pose,x=-1.),arc=None)
                actors.append(replace(a,commands=(command,)))
            frame=replace(f,actors=tuple(actors))
            payload={'boot':frame.boot,'world':frame.world,'frame':frame.frame,'simtime':frame.simtime,'actors':frame.actors}
            data=_payload(payload);path=tmp_path/f'offset-{counter}-{frame.frame}.json';path.write_bytes(data)
            ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST',frame.frame,frame.simtime)
            refs.append(ref);frames.append(replace(frame,integrity={**frame.integrity,'frame_refs':(ref,)}))
        return SimpleNamespace(episode=repackage_episode(frames=tuple(frames),fixture=fixture,external_refs=tuple(refs)),fixture=fixture)
    return build


@pytest.mark.parametrize('fault',['current_pose','naked_arc'])
def test_command_offset_uses_observed_precommand_pose_not_future_or_asserted_arc(require,offset_episode,fault):
    check=require('m56.evidence','check_integrity');c=offset_episode(fault)
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'OFFSET_PROGRAM_MISMATCH' in out.reasons


def test_malformed_frozen_offset_profile_cannot_be_blessed_by_matching_readback(require,offset_episode):
    check=require('m56.evidence','check_integrity');c=offset_episode('bad_profile')
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'OFFSET_PROFILE_INVALID' in out.reasons


def test_bound_offsets_still_require_missing_initial_observation_and_physical_fit(require,offset_episode):
    check=require('m56.evidence','check_integrity');c=offset_episode()
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'
    assert 'OFFSET_SOURCE_FRAME_MISSING' in out.reasons
    assert 'OFFSET_PROGRAM_MISMATCH' not in out.reasons
    assert 'W01_W05_VALIDATION_PENDING' in out.reasons


def test_unprojectable_offset_origin_is_uncertain_not_clamped_to_profile_start(require,offset_episode):
    check=require('m56.evidence','check_integrity');c=offset_episode('off_route')
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'
    assert 'OFFSET_PROJECTION_UNKNOWN' in out.reasons
    assert 'OFFSET_PROGRAM_MISMATCH' not in out.reasons


@pytest.fixture
def reference_switch_episode(tmp_path,controlled_episode,repackage_episode):
    from m56.model import SourceRef
    from m56.catalog import _digest
    from m56.evidence import _payload
    from types import SimpleNamespace
    import hashlib
    counter=0;c=controlled_episode
    def build(fault=None):
        nonlocal counter
        counter+=1;refs=list(c.refs)
        def source(name,value,frame=None,time=None):
            data=_payload(value);path=tmp_path/f'reference-{counter}-{name}.json';path.write_bytes(data)
            ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST',frame,time)
            refs.append(ref);return ref
        original=c.fixture.responses[0];target=replace(original.route,transforms=tuple(replace(p,y=3.) for p in original.route.transforms))
        def profile(end):return {'method':'quintic-arc-v1','segments':({'start_arc_m':F(0),'length_m':F(3),
                                                                     'start_offset_m':F(0),'end_offset_m':F(end)},)}
        switch={'cause':'SWITCH','event':'TARGET_LANE_CONFIRMED','marker_arc_m':F(3),'route':target,'profile':profile(0)}
        program={'method':'ordered-event-program-v1','initial':'HOLD','transitions':(
            {'cause':'SWITCH','after_event':'TARGET_LANE_CONFIRMED','delay_s':F(0),'requires':()},)}
        response=replace(original,targets={'HOLD':F(0),'SWITCH':F(0)},profile=profile(3),
                         phases={'program':program,'reference_switches':(switch,)})
        fixture=replace(c.fixture,responses=(response,c.fixture.responses[1]));target_ref=source('target-route',target)
        frames=[]
        for i,f in enumerate(c.frames):
            ego,npc=f.actors
            # Boundary unknown is retained; every later command has a real prior pose.
            offset=F(3) if i<3 else F(0)
            cmd=replace(ego.commands[0],cause='HOLD' if i<3 else 'SWITCH',offset=offset)
            if fault=='old_offset' and i==3:cmd=replace(cmd,offset=F(3))
            pose=replace(ego.pose,x=4.,y=3.)
            if fault=='early_marker' and i==2:pose=replace(pose,x=2.)
            ego=replace(ego,pose=pose,commands=(cmd,))
            frame=replace(f,actors=(ego,npc));plans={**c.plans,'EGO':target_ref if i>=3 and fault!='old_plan' else c.plans['EGO']}
            observed=source(f'frame-{f.frame}',{'boot':f.boot,'world':f.world,'frame':f.frame,'simtime':f.simtime,'actors':frame.actors},f.frame,f.simtime)
            frames.append(replace(frame,integrity={**frame.integrity,'frame_refs':(observed,),'plan_refs':plans}))
        return SimpleNamespace(episode=repackage_episode(frames=tuple(frames),fixture=fixture,external_refs=tuple(refs)),fixture=fixture)
    return build


def test_w02_switched_plan_and_zero_offset_use_frozen_target_reference(require,reference_switch_episode):
    c=reference_switch_episode()
    invalid,unknown=require('m56.evidence','_offset_integrity')(c.episode,c.fixture)
    assert invalid==()
    assert 'OFFSET_SOURCE_FRAME_MISSING' in unknown
    assert require('m56.evidence','_frame_integrity')(c.episode,c.fixture)==((),())
    assert require('m56.evidence','check_integrity')(c.episode,c.fixture).status!='WITNESS_VALID'


@pytest.mark.parametrize('fault,reason',[('old_offset','OFFSET_PROGRAM_MISMATCH'),('early_marker','OFFSET_REFERENCE_SWITCH_INVALID')])
def test_w02_switch_rejects_old_offset_and_pre_marker_command(require,reference_switch_episode,fault,reason):
    c=reference_switch_episode(fault)
    invalid,_=require('m56.evidence','_offset_integrity')(c.episode,c.fixture)
    assert reason in invalid


def test_w02_offset_reset_does_not_excuse_keeping_old_plan(require,reference_switch_episode):
    c=reference_switch_episode('old_plan')
    invalid,_=require('m56.evidence','_frame_integrity')(c.episode,c.fixture)
    assert 'PLAN_SOURCE_WITNESS_INVALID' in invalid


def test_offset_reference_route_must_match_bound_fixture_role_route(require,offset_episode):
    check=require('m56.evidence','check_integrity');c=offset_episode('wrong_route')
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'OFFSET_ROUTE_MISMATCH' in out.reasons


def test_missing_offset_profile_never_defaults_to_zero(require,offset_episode):
    check=require('m56.evidence','check_integrity');c=offset_episode('missing_profile')
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'
    assert 'OFFSET_PROFILE_MISSING' in out.reasons


def test_offset_arithmetic_cannot_authenticate_modified_in_memory_pose(require,offset_episode):
    check=require('m56.evidence','check_integrity');c=offset_episode()
    frames=list(c.episode.raw);f=frames[1];e,n=f.actors
    frames[1]=replace(f,actors=(replace(e,pose=replace(e.pose,x=3.)),n))
    out=check(replace(c.episode,raw=tuple(frames)),c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert {'TRAJECTORY_OBJECT_MISMATCH','FRAME_OBSERVATION_CONTENT_MISMATCH'}.issubset(out.reasons)


@pytest.mark.parametrize('end',[F(1,5),F(3,10)])
def test_episode_end_metadata_must_equal_last_recorded_observation(require,silent_episode,end):
    check=require('m56.evidence','check_integrity');c=silent_episode
    out=check(replace(c.a,end_simtime=end),c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'END_SIMTIME_MISMATCH' in out.reasons


@pytest.fixture
def metric_context_episode(tmp_path,controlled_episode,repackage_episode):
    from m56.model import SourceRef
    from m56.catalog import _digest
    from m56.evidence import _payload
    from types import SimpleNamespace
    import hashlib
    c=controlled_episode;counter=0
    def build(fault=None,mapped=False):
        nonlocal counter
        counter+=1;refs=list(c.refs)
        def source(name,payload):
            path=tmp_path/f'metric-context-{counter}-{name}.json';data=_payload(payload);path.write_bytes(data)
            ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST')
            refs.append(ref);return ref
        query=source('route-provenance',{'scope':'SYNTHETIC_TEST_ONLY','kind':'ROUTE_INPUT'})
        route=replace(c.fixture.routes['EGO'],continuity=(query,))
        pair=replace(c.fixture.pair,reference='route:'+_digest(route))
        map_reference={'method':'segment-map-normal-v1','route':route,'normals':((0.,1.,0.),),'refs':(query,)}
        if mapped:
            if fault=='normals':map_reference['normals']=((1.,0.,0.),)
            elif fault=='world_map':map_reference['route']=replace(route,map_hash='0'*64)
            pair=replace(pair,names=('v_mean_E','e_lat_peak'),units=('m/s','m'),estimators=('mean_speed','map_lateral_peak'),
                         window=(('TRIGGER','X_END'),)*2,reference='map:'+_digest(map_reference))
        fixture=replace(c.fixture,routes={'EGO':route,'NPC':route},pair=pair,
                        responses=tuple(replace(r,route=route) for r in c.fixture.responses))
        plans={role:source('plan-'+role,route) for role in ('EGO','NPC')}
        context={'reference':pair.reference,'pair_hash':pair.hash,'directed_route':route,
                 'uncertainty':{name:F(0) for name in pair.names}}
        if mapped:
            context['map_reference']=map_reference
        if fault=='changed_route':
            context['directed_route']=replace(route,destination=F(19))
        elif fault=='missing_source':
            refs.remove(query)
        elif fault=='uncertainty':
            context['uncertainty'][pair.names[0]]=True
        elif fault=='reference':
            context['reference']='post-outcome-origin'
        frames=tuple(replace(f,integrity={**f.integrity,'plan_refs':plans,'metric_context':context}) for f in c.frames)
        return SimpleNamespace(episode=repackage_episode(frames=frames,fixture=fixture,external_refs=tuple(refs)),fixture=fixture)
    return build


def test_metric_context_missing_cannot_produce_valid_witness(require,controlled_episode):
    check=require('m56.evidence','check_integrity');c=controlled_episode
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'
    assert 'METRIC_CONTEXT_MISSING' in out.reasons


def test_bound_metric_context_does_not_replace_other_witnesses(require,metric_context_episode):
    check=require('m56.evidence','check_integrity');c=metric_context_episode()
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'
    assert not any(r.startswith('METRIC_') for r in out.reasons)


@pytest.mark.parametrize('fault',['changed_route','missing_source','uncertainty','reference'])
def test_metric_context_cannot_change_frozen_reference_or_skip_sources(require,metric_context_episode,fault):
    check=require('m56.evidence','check_integrity');c=metric_context_episode(fault)
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'METRIC_CONTEXT_INVALID' in out.reasons


def test_map_normal_context_requires_admitted_frozen_map_sources(require,metric_context_episode):
    check=require('m56.evidence','check_integrity');c=metric_context_episode(mapped=True)
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'
    assert not any(r.startswith('METRIC_') for r in out.reasons)


@pytest.mark.parametrize('fault',['missing_source','normals','world_map'])
def test_map_normal_context_rejects_unbound_or_geometrically_invalid_reference(require,metric_context_episode,fault):
    check=require('m56.evidence','check_integrity');c=metric_context_episode(fault,mapped=True)
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'METRIC_CONTEXT_INVALID' in out.reasons


def test_source_metrics_recompute_actual_windows_without_eligibility_claim(require,crossing_episode):
    derive=require('m56.metrics','_source_metrics');evaluate=require('m56.metrics','evaluate_episode')
    c=crossing_episode('metric_known',metric_context=True)
    values=derive(c.episode,c.fixture)
    assert values is not None
    assert tuple(v.value for v in values)==(F(13,8),F(6,5))
    assert tuple((v.frames[0],v.frames[-1]) for v in values)==((101,114),(101,125))
    # These observed numerical components are not eligible episode values.
    out=evaluate(c.episode,c.fixture)
    assert out.physical=='INCOMPLETE' and out.witness!='VALID'
    assert all(v.value is None for v in out.metrics.values())


def test_source_metrics_missing_entry_stays_none_not_horizon(require,crossing_episode):
    derive=require('m56.metrics','_source_metrics');c=crossing_episode(metric_context=True)
    values=derive(c.episode,c.fixture)
    assert values is not None
    assert values[1].value is None and values[1].status=='INCOMPLETE'


def test_source_metrics_cannot_use_mutated_unsealed_trajectory(require,crossing_episode):
    derive=require('m56.metrics','_source_metrics');c=crossing_episode('metric_known',metric_context=True)
    frame=c.episode.raw[2];ego=frame.actors[0]
    frame=replace(frame,actors=(replace(ego,pose=replace(ego.pose,x=20.)),frame.actors[1]))
    raw=c.episode.raw[:2]+(frame,)+c.episode.raw[3:]
    assert derive(replace(c.episode,raw=raw),c.fixture) is None


@pytest.fixture
def reviewed_episode(tmp_path,crossing_episode):
    from m56.evidence import open_run,append_record,snapshot_sources,seal,_payload
    from m56.metrics import _source_metrics,detect_events
    from m56.model import SourceRef,ReviewRecord
    from m56.catalog import _digest
    from types import SimpleNamespace
    import hashlib
    c=crossing_episode('metric_known',metric_context=True);e=c.episode
    def ref(path):
        data=path.read_bytes()
        return SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST')
    authority_path=tmp_path/'w05-authority.json';authority_path.write_bytes(_payload({'scope':'SYNTHETIC_TEST_ONLY'}))
    authority=ref(authority_path)
    original_refs=(e.fixture,e.manifest,*e.journal,*e.source)
    subject={'schema':1,'scope':'EPISODE_WITNESS_W05','fixture':e.fixture,'manifest':e.manifest,
             'journal':e.journal,'sources':e.source,'trajectory_hash':_digest(e.raw),'end_simtime':e.end_simtime,
             'events':detect_events(e.raw,c.fixture),'metrics':_source_metrics(e,c.fixture)}
    assert tuple(v.value for v in subject['metrics'])==(F(13,8),F(6,5))
    review=ReviewRecord(_digest(subject),'EPISODE_WITNESS_W05',original_refs,'SYNTHETIC_TEST','2026-10-09','APPROVED',(
        'fulltrace: the complete literal recording is bound, not only endpoint values',
        'near_zero: literal metrics are nonzero; no epsilon or rounded credit',
        'nearstanding: component-only synthetic trace, not a native assessment',
        'identity: frozen fixture and complete original manifest are bound',
        'mechanism: synthetic trace follows a proposal, not proof of realized scientific mechanism',
        'comparability: this is episode review only; interscene and AB reviews are still separate'),authority)
    store=open_run(tmp_path/'w05-bundle','synthetic-w05-review','writer')
    append_record(store,'review.json',review)
    assert snapshot_sources(store,(*original_refs,authority)).status=='INTEGRITY_VALID'
    seal(store)
    episode=replace(e,integrity={**e.integrity,'episode_review_ref':ref(store.root/'review.json'),
                                'episode_review_manifest':ref(store.root/'manifest.json')})
    counter=0
    def with_review(changed):
        nonlocal counter
        counter+=1
        bundle=open_run(tmp_path/f'w05-review-version-{counter}',f'synthetic-w05-review-{counter}','writer')
        append_record(bundle,'review.json',changed)
        assert snapshot_sources(bundle,(*original_refs,authority)).status=='INTEGRITY_VALID'
        seal(bundle)
        return replace(e,integrity={**e.integrity,'episode_review_ref':ref(bundle.root/'review.json'),
                                   'episode_review_manifest':ref(bundle.root/'manifest.json')})
    return SimpleNamespace(episode=episode,fixture=c.fixture,original=e,authority_path=authority_path,store=store,
                           review=review,with_review=with_review)


def test_episode_w05_missing_is_not_implicit_human_approval(require,controlled_episode):
    check=require('m56.evidence','check_integrity');c=controlled_episode
    assert 'W05_REVIEW_MISSING' in check(c.episode,c.fixture).reasons


def test_episode_review_can_be_separately_sealed_without_rewriting_raw(require,reviewed_episode):
    check=require('m56.evidence','check_integrity');c=reviewed_episode
    from pathlib import Path
    raw=Path(c.original.integrity['trajectory_ref'].uri).read_bytes();seal=Path(c.original.manifest.uri).read_bytes()
    out=check(c.episode,c.fixture)
    assert out.status=='WITNESS_UNCERTAIN'  # no ownership/ground/delivery/target qualification
    assert 'W05_REVIEW_MISSING' not in out.reasons and 'W05_REVIEW_INVALID' not in out.reasons
    assert Path(c.original.integrity['trajectory_ref'].uri).read_bytes()==raw
    assert Path(c.original.manifest.uri).read_bytes()==seal


@pytest.mark.parametrize('fault',['authority','bundle','raw_memory','missing_bundle'])
def test_episode_w05_cannot_reuse_unbound_review_or_changed_trace(require,reviewed_episode,fault):
    check=require('m56.evidence','check_integrity');c=reviewed_episode;e=c.episode
    if fault=='authority':
        c.authority_path.write_bytes(b'changed')
    elif fault=='bundle':
        (c.store.root/'review.json').write_bytes(b'{}')
    elif fault=='missing_bundle':
        e=replace(e,integrity={k:v for k,v in e.integrity.items() if k!='episode_review_manifest'})
    else:
        f=e.raw[0];ego=f.actors[0]
        e=replace(e,raw=(replace(f,actors=(replace(ego,velocity=(99.,0.,0.)),f.actors[1])),)+e.raw[1:])
    out=check(e,c.fixture)
    assert out.status=='WITNESS_INVALID'
    assert 'W05_REVIEW_INVALID' in out.reasons


def test_episode_review_positive_component_is_explicit_not_absent_validation(require,reviewed_episode):
    audit=require('m56.evidence','_episode_review_integrity');c=reviewed_episode
    assert audit(c.episode,c.fixture)==((),())


@pytest.mark.parametrize('fault',['hash','scope','generic_approval','missing_nearstanding','missing_original_ref'])
def test_new_sealed_w05_bundle_does_not_make_invalid_review_acceptable(require,reviewed_episode,fault):
    audit=require('m56.evidence','_episode_review_integrity');c=reviewed_episode;review=c.review
    if fault=='hash':
        review=replace(review,object_hash='0'*64)
    elif fault=='scope':
        review=replace(review,scope='REALIZED_AB_COMPARABILITY_D09')
    elif fault=='generic_approval':
        review=replace(review,reasons=('approved',))
    elif fault=='missing_nearstanding':
        review=replace(review,reasons=tuple(r for r in review.reasons if not r.startswith('nearstanding:')))
    else:
        review=replace(review,refs=review.refs[1:])
    episode=c.with_review(review)
    invalid,uncertain=audit(episode,c.fixture)
    assert invalid==('W05_REVIEW_INVALID',)
    assert uncertain==()


def test_late_review_bundle_correction_cannot_leave_w05_accepted(require,reviewed_episode):
    audit=require('m56.evidence','_episode_review_integrity');c=reviewed_episode
    from m56.evidence import append_correction
    from m56.model import ArtifactRef
    ref=c.episode.integrity['episode_review_ref']
    original=(c.store.root/'review.json').read_bytes();manifest=(c.store.root/'manifest.json').read_bytes()
    append_correction(c.store,ArtifactRef('review.json',ref.sha256,ref.bytes,'REVIEW'),
                      {'kind':'REVIEW_WITHDRAWN','reason':'synthetic review correction pending'})
    invalid,uncertain=audit(c.episode,c.fixture)
    assert invalid==()
    assert 'W05_REVIEW_CORRECTIONS_PENDING' in uncertain
    assert (c.store.root/'review.json').read_bytes()==original
    assert (c.store.root/'manifest.json').read_bytes()==manifest


def test_namespace_reuse_cannot_overwrite(require, tmp_path):
    open_run=require('m56.evidence','open_run')
    a=open_run(tmp_path/'run','unit-run','writer-a')
    original=(tmp_path/'run'/'writer.json').read_bytes()
    b=open_run(tmp_path/'run','unit-run','writer-b')
    assert b.status=='OUTPUT_EXISTS'
    assert (tmp_path/'run'/'writer.json').read_bytes()==original


def test_manifest_detects_single_byte_change(require,tmp_path):
    open_run=require('m56.evidence','open_run')
    append=require('m56.evidence','append_record')
    seal=require('m56.evidence','seal')
    verify=require('m56.evidence','verify_manifest')
    store=open_run(tmp_path/'run','unit-run','writer-a')
    artifact=append(store,'raw/frames.jsonl',{'kind':'SYNTHETIC_TEST','frame':10})
    seal(store)
    assert verify(store.root).status=='INTEGRITY_VALID'
    raw=store.root/artifact.relativepath
    data=raw.read_bytes()
    raw.write_bytes(data.replace(b'10',b'11'))
    out=verify(store.root)
    assert out.status=='INTEGRITY_INVALID'
    assert any('raw/frames.jsonl' in reason for reason in out.reasons)


def test_seal_retains_raw_failure(require,tmp_path):
    import pytest
    open_run=require('m56.evidence','open_run')
    append=require('m56.evidence','append_record')
    seal=require('m56.evidence','seal')
    store=open_run(tmp_path/'run','unit','writer')
    failure=append(store,'failures/native.jsonl',{'error':'SYNTHETIC_TIMEOUT','partial_ids':[101]})
    path=store.root/failure.relativepath
    original=path.read_bytes()
    seal(store)
    with pytest.raises(ValueError,match='SEALED_IMMUTABLE'):
        append(store,'failures/native.jsonl',{'error':'replacement'})
    assert path.read_bytes()==original


def test_path_escape_rejected(require,tmp_path):
    import pytest
    open_run=require('m56.evidence','open_run')
    append=require('m56.evidence','append_record')
    store=open_run(tmp_path/'run','unit','writer')
    foreign=tmp_path/'foreign.jsonl'
    with pytest.raises(ValueError,match='PATH_REJECTED'):
        append(store,'../foreign.jsonl',{'frame':1})
    assert not foreign.exists()


def test_late_event_addendum_leaves_seal_unchanged(require,tmp_path):
    import json
    open_run=require('m56.evidence','open_run')
    append=require('m56.evidence','append_record')
    seal=require('m56.evidence','seal')
    correction=require('m56.evidence','append_correction')
    verify=require('m56.evidence','verify_manifest')
    store=open_run(tmp_path/'run','unit','writer')
    artifact=append(store,'raw/sensor.jsonl',{'kind':'SYNTHETIC_TEST','events':[]})
    seal(store)
    before=(store.root/'manifest.json').read_bytes()
    raw=(store.root/artifact.relativepath).read_bytes()
    added=correction(store,artifact,{'collision':True,'frame':12})
    assert (store.root/'manifest.json').read_bytes()==before
    assert (store.root/artifact.relativepath).read_bytes()==raw
    assert (store.root/added.relativepath).is_file()
    data=json.loads((store.root/added.relativepath).read_text())
    assert data['original']['hash']==artifact.hash
    assert data['eligibility']=='REVIEW_REQUIRED'
    assert verify(store.root).status=='INTEGRITY_VALID'


def test_snapshot_sources_checks_bytes_before_admission(require,tmp_path):
    import hashlib
    open_run=require('m56.evidence','open_run')
    snapshot=require('m56.evidence','snapshot_sources')
    from m56.model import SourceRef
    source=tmp_path/'input.json'
    source.write_bytes(b'{"scope":"SYNTHETIC_TEST"}')
    raw=source.read_bytes()
    ref=SourceRef(str(source),hashlib.sha256(raw).hexdigest(),len(raw),'test','literal','SYNTHETIC_TEST')
    store=open_run(tmp_path/'run','unit','writer')
    out=snapshot(store,(ref,))
    assert out.status=='INTEGRITY_VALID'
    assert (store.root/'sources'/f'{ref.sha256}.bin').read_bytes()==raw
    source.write_bytes(b'changed')
    failed=snapshot(store,(ref,))
    assert failed.status=='INTEGRITY_INVALID'
    assert (store.root/'sources'/f'{ref.sha256}.bin').read_bytes()==raw
    assert b'SOURCE_MISMATCH' in (store.root/'journal.jsonl').read_bytes()


def test_windows_device_paths_are_rejected_before_io(require,tmp_path):
    import pytest
    safe=require('m56.evidence','_safe_path')
    # Pure path validation only: never open a Windows device in this test.
    for name in ('CON','raw/con.txt','raw/NUL.jsonl','AUX','COM1.log','LPT9.txt'):
        with pytest.raises(ValueError,match='PATH_REJECTED'):
            safe(tmp_path,name)


def test_seal_checked_after_exclusive_lease(require,tmp_path,monkeypatch):
    import pytest
    open_run=require('m56.evidence','open_run')
    append=require('m56.evidence','append_record')
    import m56.evidence as evidence
    store=open_run(tmp_path/'run','unit','writer')
    original_open=evidence.os.open
    def interleaving_open(path,flags,*args):
        fd=original_open(path,flags,*args)
        # Another writer finished a seal immediately before this lease was acquired.
        (store.root/'manifest.json').write_bytes(b'{"schema":1,"files":[]}')
        return fd
    monkeypatch.setattr(evidence.os,'open',interleaving_open)
    with pytest.raises(ValueError,match='SEALED_IMMUTABLE'):
        append(store,'raw/frames.jsonl',{'frame':1})
    assert not (store.root/'raw/frames.jsonl').exists()
