"""Exclusive append-only evidence. Hashes prove bytes, never scientific validity."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from contextlib import contextmanager
from dataclasses import replace
from functools import lru_cache
from types import MappingProxyType
import hashlib
import json
import os
import re
import uuid

from .model import (RunStore, ReleaseBlocked, ArtifactRef, IntegrityReport, SourceRef,
                    EpisodeEvidence, CompiledFixture, FrameRecord, SensorPacket, RuntimeIdentity,
                    OwnershipReceipt, DirectedRoute, ReviewRecord, CapabilityProof, decode_record, encode_record)
from .catalog import _digest, _review_binds
from fractions import Fraction
from collections.abc import Mapping


@lru_cache(maxsize=8)
def _manifest_entries(data: bytes):
    # Parsing cache keyed by FULL freshly read bytes, never path/mtime or verdict.
    # Source bytes, hashes and seals are still revalidated on each use.
    return MappingProxyType({row['relativepath']:MappingProxyType(row) for row in json.loads(data)['files']})


def _source_bytes(ref: SourceRef) -> bytes | None:
    """Verify an explicitly supplied local source; no URI fetch or fallback lookup."""
    if not isinstance(ref,SourceRef) or '://' in ref.uri:
        return None
    path=Path(ref.uri)
    if (not path.is_absolute() or type(ref.bytes) is not int or ref.bytes<0
            or not re.fullmatch(r'[0-9a-f]{64}',ref.sha256)):
        return None
    try:
        if path.stat().st_size!=ref.bytes:
            return None
        data=path.read_bytes()
        return data if hashlib.sha256(data).hexdigest()==ref.sha256 else None
    except OSError:
        return None


def check_integrity(evidence: EpisodeEvidence, fixture: CompiledFixture) -> IntegrityReport:
    """Initial T09 byte/continuity gates. A valid delivery recipe is still mandatory.

    No WITNESS_VALID path until W01-W05 and source-correlated fence validation is
    implemented; listeners, silence and completed drain alone never suffice.
    """
    invalid=[];uncertain=[];verified=[]
    refs=(*evidence.journal,evidence.fixture,*evidence.source)
    if evidence.manifest is not None:
        refs=(*refs,evidence.manifest)
    else:
        uncertain.append('MANIFEST_MISSING')
    for ref in refs:
        if _source_bytes(ref) is None:
            invalid.append('SOURCE_HASH_MISMATCH')
        else:
            verified.append(ref)
    manifest_root=None;entries={}
    if evidence.manifest is not None and evidence.manifest in verified:
        manifest_path=Path(evidence.manifest.uri);manifest_root=manifest_path.parent
        sealed=verify_manifest(manifest_root)
        if sealed.status!='INTEGRITY_VALID' or manifest_path.name!='manifest.json':
            invalid.append('SEALED_MANIFEST_INVALID')
        else:
            entries=_manifest_entries(manifest_path.read_bytes())
            for ref in refs:
                if ref!=evidence.manifest and not _sealed_source(ref,manifest_root,entries):
                    invalid.append('SOURCE_NOT_SEALED')
            addenda=manifest_root/'addenda'
            if addenda.exists() and any(addenda.iterdir()):
                uncertain.append('LATE_CORRECTIONS_REVIEW_REQUIRED')
    source_fixture=_decode_source_record('CompiledFixture',evidence.fixture)
    if not isinstance(source_fixture,CompiledFixture) or _digest(source_fixture)!=_digest(fixture):
        invalid.append('FIXTURE_OBJECT_MISMATCH')
    trajectory=decode_record('SourceRef',encode_record(evidence.integrity.get('trajectory_ref')))
    if not isinstance(trajectory,SourceRef):
        uncertain.append('TRAJECTORY_REFERENCE_MISSING')
    else:
        if trajectory not in refs or (manifest_root is not None and not _sealed_source(trajectory,manifest_root,entries)):
            invalid.append('SOURCE_NOT_SEALED')
        recorded=_read_trajectory(trajectory)
        if recorded is None or _digest(recorded)!=_digest(evidence.raw):
            invalid.append('TRAJECTORY_OBJECT_MISMATCH')
    frames=evidence.raw
    if not frames:
        uncertain.append('TRAJECTORY_MISSING')
    elif (any(f.dt!=Fraction(1,20) for f in frames)
          or any((a.boot,a.world)!=(b.boot,b.world) or b.frame!=a.frame+1
                 or b.simtime-a.simtime!=b.dt for a,b in zip(frames,frames[1:]))):
        invalid.append('FRAME_IDENTITY_OR_CONTINUITY')
    if frames and evidence.end_simtime!=frames[-1].simtime:
        invalid.append('END_SIMTIME_MISMATCH')
    target_invalid,target_uncertain=_target_integrity(evidence,fixture)
    invalid.extend(target_invalid);uncertain.extend(target_uncertain)
    init_invalid,init_uncertain=_initialization_integrity(evidence,fixture)
    invalid.extend(init_invalid);uncertain.extend(init_uncertain)
    motion_invalid,motion_uncertain=_motion_integrity(evidence,fixture)
    invalid.extend(motion_invalid);uncertain.extend(motion_uncertain)
    phase_invalid,phase_uncertain=_phase_integrity(evidence,fixture)
    invalid.extend(phase_invalid);uncertain.extend(phase_uncertain)
    offset_invalid,offset_uncertain=_offset_integrity(evidence,fixture)
    invalid.extend(offset_invalid);uncertain.extend(offset_uncertain)
    lateral_invalid,lateral_uncertain=_lateral_integrity(evidence,fixture)
    invalid.extend(lateral_invalid);uncertain.extend(lateral_uncertain)
    policy_invalid,policy_uncertain=_normative_integrity(evidence,fixture)
    invalid.extend(policy_invalid);uncertain.extend(policy_uncertain)
    metric_invalid,metric_uncertain=_metric_context_integrity(evidence,fixture)
    invalid.extend(metric_invalid);uncertain.extend(metric_uncertain)
    owner_invalid,owner_uncertain=_ownership_integrity(evidence,fixture)
    invalid.extend(owner_invalid);uncertain.extend(owner_uncertain)
    frame_invalid,frame_uncertain=_frame_integrity(evidence,fixture)
    invalid.extend(frame_invalid);uncertain.extend(frame_uncertain)
    ground_invalid,ground_uncertain=_ground_integrity(evidence,fixture)
    invalid.extend(ground_invalid);uncertain.extend(ground_uncertain)
    _,collision_errors=_collision_evidence(evidence)
    invalid.extend(collision_errors)
    delivery_invalid,delivery_uncertain=_delivery_integrity(evidence,fixture)
    invalid.extend(delivery_invalid);uncertain.extend(delivery_uncertain)
    contact_invalid,contact_uncertain=_contact_integrity(evidence,fixture)
    invalid.extend(contact_invalid);uncertain.extend(contact_uncertain)
    review_invalid,review_uncertain=_episode_review_integrity(evidence,fixture)
    invalid.extend(review_invalid);uncertain.extend(review_uncertain)
    # Positive witness admission requires the independent actual-action consumer.
    # Unsupported mechanisms remain explicitly blocked; no completeness flag input.
    from .metrics import _authenticated_events,_crossing_action,_io_action,_f_action,_finish_action
    from .model import PhysicalState
    if not invalid and not uncertain:
        events=_authenticated_events(evidence,fixture)
        category=fixture.domain.topology.get('category')
        audit=_f_action if category=='F' else _io_action if category in ('I','O') else _crossing_action
        state,details=audit(evidence.raw,fixture,events) if events is not None else (None,('ACTION_WITNESS_UNKNOWN',))
        if events is not None:
            state,details=_finish_action(evidence.raw,fixture,events,state,details)
        if state!=PhysicalState.COMPLETE:
            uncertain.extend(details or ('ACTION_COMPLETION_UNPROVEN',))
    if invalid or uncertain:
        uncertain.append('W01_W05_VALIDATION_PENDING')
    reasons=tuple(dict.fromkeys(invalid+uncertain))
    status='WITNESS_INVALID' if invalid else 'WITNESS_UNCERTAIN' if uncertain else 'WITNESS_VALID'
    return IntegrityReport(status,reasons,tuple(verified))


def _episode_review_integrity(evidence,fixture):
    """Review the sealed episode in a separate sealed bundle, without circular hashes.

    The bundle snapshots original refs; it never upgrades or rewrites raw data.
    This verifies review provenance/content binding, not human judgment or native
    authority. All other witness/action/late-correction gates remain independent.
    """
    if 'episode_review_ref' not in evidence.integrity and 'episode_review_manifest' not in evidence.integrity:
        return (),('W05_REVIEW_MISSING',)
    review_ref=decode_record('SourceRef',encode_record(evidence.integrity.get('episode_review_ref')))
    manifest=decode_record('SourceRef',encode_record(evidence.integrity.get('episode_review_manifest')))
    if not isinstance(review_ref,SourceRef) or not isinstance(manifest,SourceRef):
        return ('W05_REVIEW_INVALID',),()
    try:
        manifest_data=_source_bytes(manifest);review_data=_source_bytes(review_ref)
        root=Path(manifest.uri).parent
        if (manifest_data is None or review_data is None or Path(manifest.uri).name!='manifest.json'
                or verify_manifest(root).status!='INTEGRITY_VALID'):
            return ('W05_REVIEW_INVALID',),()
        entries=_manifest_entries(manifest_data)
        if not _sealed_source(review_ref,root,entries):
            return ('W05_REVIEW_INVALID',),()
        review=decode_record('ReviewRecord',json.loads(review_data))
        if not isinstance(review,ReviewRecord) or evidence.manifest is None:
            return ('W05_REVIEW_INVALID',),()
        from .metrics import _source_metrics,_authenticated_events
        values=_source_metrics(evidence,fixture);events=_authenticated_events(evidence,fixture)
        if values is None or events is None:
            return ('W05_REVIEW_INVALID',),()
        subject={'schema':1,'scope':'EPISODE_WITNESS_W05','fixture':evidence.fixture,'manifest':evidence.manifest,
                 'journal':evidence.journal,'sources':evidence.source,'trajectory_hash':_digest(evidence.raw),
                 'end_simtime':evidence.end_simtime,'events':events,'metrics':values}
        if not _review_binds(review,_digest(subject),('EPISODE_WITNESS_W05',)):
            return ('W05_REVIEW_INVALID',),()
        required=(evidence.fixture,evidence.manifest,*evidence.journal,*evidence.source)
        if any(ref not in review.refs for ref in required):
            return ('W05_REVIEW_INVALID',),()
        for ref in (*review.refs,review.authority_ref):
            if _source_bytes(ref) is None or not _sealed_source(ref,root,entries):
                return ('W05_REVIEW_INVALID',),()
        areas={'fulltrace','near_zero','nearstanding','identity','mechanism','comparability'}
        covered={reason.partition(':')[0].strip() for reason in review.reasons
                 if ':' in reason and reason.partition(':')[2].strip()}
        if not areas.issubset(covered):
            return ('W05_REVIEW_INVALID',),()
        # A later review correction invalidates this review version's eligibility.
        # Do not fold it into, overwrite, or silently upgrade the original review.
        addenda=root/'addenda'
        if addenda.exists() and any(addenda.iterdir()):
            return (),('W05_REVIEW_CORRECTIONS_PENDING',)
    except (OSError,ValueError,TypeError,KeyError,UnicodeError):
        return ('W05_REVIEW_INVALID',),()
    return (),()


def _source_json(evidence,packet):
    ref=decode_record('SourceRef',encode_record(packet))
    if not isinstance(ref,SourceRef) or not _admitted_source(evidence,ref):
        return None
    try:
        return json.loads(_source_bytes(ref)),ref
    except (ValueError,TypeError,UnicodeError):
        return None


def _delivery_integrity(evidence,fixture):
    """Validate recorded qualified-recipe data, NOT implement a CARLA heartbeat/fence.

    An actual runtime must separately qualify and authorize the recipe. Even a
    matching recording supports only its observed interval, never lossless delivery.
    """
    source=_bound_json(evidence,'delivery_ref')
    if source is None:
        reason='DELIVERY_RECIPE_NOT_VALIDATED' if evidence.integrity.get('delivery_proof') is not None else 'DELIVERY_PROOF_MISSING'
        return (),(reason,)
    proof=decode_record('CapabilityProof',source[0])
    if not isinstance(proof,CapabilityProof):
        return ('DELIVERY_PROOF_INVALID',),()
    packet={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
    limits=proof.limits
    required={'fixture_hash','trajectory_hash','recipe_ref','recipe_review','lifecycle_ref','fence_ref'}
    if (proof.kind!='COLLISION_DELIVERY' or proof.method!='recorded-ack-fence-v1' or proof.status!='CORROBORATED'
            or proof.uncertainty!=0 or set(limits)!=required
            or limits['fixture_hash']!=_digest(fixture) or limits['trajectory_hash']!=_digest(evidence.raw)
            or not _verified_review(evidence,proof.review,_digest(packet),'CAPABILITY:COLLISION_DELIVERY')):
        return ('DELIVERY_PROOF_INVALID',),()
    recipe=_source_json(evidence,limits['recipe_ref'])
    lifecycle=_source_json(evidence,limits['lifecycle_ref']);fence=_source_json(evidence,limits['fence_ref'])
    registry=_bound_json(evidence,'sensor_registry_ref')
    if any(p is None for p in (recipe,lifecycle,fence,registry)) or not evidence.raw:
        return ('DELIVERY_PROOF_INVALID',),()
    try:
        recipe_data,recipe_ref=recipe
        recipe_review=decode_record('ReviewRecord',encode_record(limits['recipe_review']))
        qualifications=recipe_data['qualification_refs']
        if (set(recipe_data)!={'schema','method','version','limits','qualification_refs'}
                or recipe_data['schema']!=1 or recipe_data['method']!=proof.method or not recipe_data['version']
                or recipe_data['limits']!='observed-owned-interval-only' or not qualifications
                or not _verified_review(evidence,recipe_review,_digest(recipe_data),'COLLISION_DELIVERY_RECIPE')
                or recipe_ref not in recipe_review.refs or any(_source_json(evidence,r) is None for r in qualifications)
                or any(p[1] not in proof.raw_refs or p[1] not in proof.review.refs for p in (lifecycle,fence))):
            return ('DELIVERY_PROOF_INVALID',),()
        first,last=evidence.raw[0],evidence.raw[-1]
        bootworld=(first.boot,first.world)
        reg=registry[0];life=lifecycle[0];acks=fence[0]
        if any((p['boot'],p['world'])!=bootworld for p in (reg,life,acks)) or acks['recipe_hash']!=recipe_ref.sha256:
            return ('DELIVERY_PROOF_INVALID',),()
        expected=reg['sensors']
        if len(expected)!=2 or set(expected.values())!={a.id for a in first.actors}:
            return ('DELIVERY_PROOF_INVALID',),()
        channels=life['channels'];fences=acks['channels']
        if len(channels)!=2 or len(fences)!=2 or {str(p['sensor_id']) for p in channels}!=set(expected) or {str(p['sensor_id']) for p in fences}!=set(expected):
            return ('DELIVERY_PROOF_INVALID',),()
        for p in channels:
            if (set(p)!={'sensor_id','actor_id','listen_frame','stop_frame','errors'}
                    or any(type(p[k]) is not int for k in ('sensor_id','actor_id','listen_frame','stop_frame'))
                    or expected[str(p['sensor_id'])]!=p['actor_id'] or p['errors']!=[]
                    or p['listen_frame']>first.frame or p['stop_frame']<last.frame):
                return ('DELIVERY_PROOF_INVALID',),()
        for p in fences:
            if (set(p)!={'sensor_id','request_id','acknowledged_request_id','first_frame','last_frame','remaining'}
                    or not isinstance(p['request_id'],str) or not p['request_id']
                    or p['request_id']!=p['acknowledged_request_id']
                    or any(type(p[k]) is not int for k in ('sensor_id','first_frame','last_frame','remaining'))
                    or p['first_frame']>first.frame or p['last_frame']<last.frame or p['remaining']!=0):
                return ('DELIVERY_PROOF_INVALID',),()
    except (KeyError,TypeError,ValueError):
        return ('DELIVERY_PROOF_INVALID',),()
    return (),()


def _exact_bound(value):
    if type(value) is int:
        return Fraction(value)
    if (isinstance(value,dict) and set(value)=={'numerator','denominator'}
            and type(value['numerator']) is int and type(value['denominator']) is int):
        return Fraction(value['numerator'],value['denominator'])
    raise ValueError('EXACT_BOUND_REQUIRED')


def _contact_integrity(evidence,fixture):
    """Audit full-trace conservative contact receipts; no inference from sampled silence."""
    source=_bound_json(evidence,'contact_ref')
    if source is None:
        return (),('CONTACT_PROOF_MISSING',)
    proof=decode_record('CapabilityProof',source[0])
    if not isinstance(proof,CapabilityProof):
        return ('CONTACT_PROOF_INVALID',),()
    packet={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
    limits=proof.limits
    if (proof.kind!='CONTINUOUS_CONTACT' or proof.method!='bounded-contact-interval-v1' or proof.status!='CORROBORATED'
            or proof.uncertainty is None or not 0<=proof.uncertainty<=Fraction(1,20)
            or set(limits)!={'fixture_hash','trajectory_hash','recipe_ref','recipe_review','intervals_ref'}
            or limits['fixture_hash']!=_digest(fixture) or limits['trajectory_hash']!=_digest(evidence.raw)
            or not _verified_review(evidence,proof.review,_digest(packet),'CAPABILITY:CONTINUOUS_CONTACT')):
        return ('CONTACT_PROOF_INVALID',),()
    recipe=_source_json(evidence,limits['recipe_ref']);intervals=_source_json(evidence,limits['intervals_ref'])
    if recipe is None or intervals is None or len(evidence.raw)<2:
        return ('CONTACT_PROOF_INVALID',),()
    try:
        recipe_data,recipe_ref=recipe;rows,rows_ref=intervals
        review=decode_record('ReviewRecord',encode_record(limits['recipe_review']))
        if (set(recipe_data)!={'method','version','quantities','source_refs'}
                or recipe_data['method']!=proof.method or not recipe_data['version']
                or recipe_data['quantities']!=['body_separation','road_edge','ground_contact']
                or not _verified_review(evidence,review,_digest(recipe_data),'CONTACT_RECIPE')
                or not recipe_data['source_refs'] or any(_source_json(evidence,r) is None for r in recipe_data['source_refs'])
                or recipe_ref not in review.refs or rows_ref not in proof.raw_refs or rows_ref not in proof.review.refs
                or not isinstance(rows,list) or len(rows)!=len(evidence.raw)-1):
            return ('CONTACT_PROOF_INVALID',),()
        expected={'boot','world','first_frame','last_frame','first_actors_hash','last_actors_hash',
                  'minimum_body_separation_m','minimum_road_edge_m','maximum_ground_error_m','error_m'}
        for row,a,b in zip(rows,evidence.raw,evidence.raw[1:]):
            if (not isinstance(row,dict) or set(row)!=expected or (row['boot'],row['world'])!=(a.boot,a.world)
                    or type(row['first_frame']) is not int or type(row['last_frame']) is not int
                    or (row['first_frame'],row['last_frame'])!=(a.frame,b.frame)
                    or b.frame!=a.frame+1 or b.simtime-a.simtime!=Fraction(1,20)
                    or row['first_actors_hash']!=_digest(a.actors) or row['last_actors_hash']!=_digest(b.actors)):
                return ('CONTACT_PROOF_INVALID',),()
            body,edge,ground,error=(_exact_bound(row[k]) for k in (
                'minimum_body_separation_m','minimum_road_edge_m','maximum_ground_error_m','error_m'))
            if (not 0<=error<=proof.uncertainty or body-proof.uncertainty<Fraction(1,5)
                    or edge-proof.uncertainty<Fraction(3,20) or ground<0 or ground+proof.uncertainty>Fraction(1,20)):
                return ('CONTACT_PROOF_INVALID',),()
    except (KeyError,TypeError,ValueError,ZeroDivisionError):
        return ('CONTACT_PROOF_INVALID',),()
    return (),()


def _ownership_integrity(evidence,fixture):
    source=_bound_json(evidence,'w01_ref')
    if source is None:
        return (),('W01_RECEIPT_MISSING',)
    packet,_=source
    expected={'identity','ownership','actors','fixture_hash','wall_interval','observed_tick_owner'}
    if not isinstance(packet,dict) or set(packet)!=expected:
        return ('W01_SCHEMA_INVALID',),()
    identity=decode_record('RuntimeIdentity',packet['identity'])
    owner=decode_record('OwnershipReceipt',packet['ownership'])
    if not isinstance(identity,RuntimeIdentity) or not isinstance(owner,OwnershipReceipt):
        return ('W01_SCHEMA_INVALID',),()
    try:
        # This is an observed wall-clock interval, never compare it with CARLA simtime.
        interval=packet['wall_interval']
        def exact(value):
            if type(value) is int:
                return Fraction(value)
            if (isinstance(value,dict) and set(value)=={'numerator','denominator'}
                    and type(value['numerator']) is int and type(value['denominator']) is int):
                return Fraction(value['numerator'],value['denominator'])
            raise ValueError('WALL_INTERVAL_INVALID')
        if not isinstance(interval,list) or len(interval)!=2:
            raise ValueError('WALL_INTERVAL_INVALID')
        start,end=map(exact,interval)
        writer=json.loads((Path(evidence.manifest.uri).parent/'writer.json').read_bytes())
        frames=evidence.raw
        mismatch=(not frames or any((f.boot,f.world)!=(identity.boot,identity.world) for f in frames)
                  or (owner.boot,owner.world)!=(identity.boot,identity.world)
                  or identity.client!='0.9.16' or identity.server!='0.9.16' or identity.python!='3.12.10'
                  or any(r.map_hash!=identity.map for r in fixture.routes.values())
                  or owner.writer!=writer['writer'] or not owner.tick_owner or owner.tick_owner!=packet['observed_tick_owner']
                  or not owner.host or owner.pid<=0 or not owner.start
                  or not owner.exclusive_window[0]<=start<=end<=owner.exclusive_window[1]
                  or not {'tick','observe'}.issubset(owner.allowed_ops)
                  or packet['fixture_hash']!=_digest(fixture)
                  or any(packet['actors']!={a.role:a.id for a in f.actors} for f in frames))
    except (OSError,ValueError,TypeError,KeyError,ZeroDivisionError):
        return ('W01_SCHEMA_INVALID',),()
    invalid=['W01_IDENTITY_OR_OWNERSHIP_MISMATCH'] if mismatch else []
    review_source=_bound_json(evidence,'w01_review_ref')
    if review_source is None:
        return tuple(invalid),('W01_AUTHORITY_REVIEW_MISSING',)
    review=decode_record('ReviewRecord',review_source[0])
    if (not _verified_review(evidence,review,_digest(packet),'W01_OWNERSHIP')
            or not any(ref.sha256==source[1].sha256 and ref.bytes==source[1].bytes for ref in review.refs)):
        invalid.append('W01_AUTHORITY_REVIEW_INVALID')
    required={'carla','basic_agent','local_planner','controller'}
    if (not required.issubset(identity.modules) or set(identity.source_hashes)!=set(identity.modules)
            or any(identity.source_hashes[name]!=ref.sha256 or not _admitted_source(evidence,ref)
                   or not isinstance(review,ReviewRecord) or ref not in review.refs for name,ref in identity.modules.items())):
        invalid.append('W01_MODULE_SOURCE_INVALID')
    return tuple(dict.fromkeys(invalid)),()


_VERIFIED_SOURCES = {}
_ADMISSION_INDEX = {}


def _source_ok(ref):
    """_source_bytes(ref) is not None, memoized by (ref, mtime_ns, size): a rewritten file is verified again.
    perf 2026-10-25: the uncached read+sha256 per frame pair dominated offline evaluation. ponytail: clear-all cache."""
    try:
        st=Path(ref.uri).stat()
    except (OSError,TypeError,ValueError):
        return _source_bytes(ref) is not None
    key=(ref,st.st_mtime_ns,st.st_size)
    hit=_VERIFIED_SOURCES.get(key)
    if hit is None:
        if len(_VERIFIED_SOURCES)>65536:
            _VERIFIED_SOURCES.clear()
        hit=_VERIFIED_SOURCES[key]=_source_bytes(ref) is not None
    return hit


def _admission_index(evidence):
    """(source set, manifest root, manifest entries) of one evidence bundle, or None when the manifest does not
    verify or parse; memoized by identity of (source tuple, manifest ref) with strong references."""
    key=(id(evidence.source),id(evidence.manifest))
    hit=_ADMISSION_INDEX.get(key)
    if hit is not None and hit[0] is evidence.source and hit[1] is evidence.manifest:
        return hit[2]
    try:
        data=_source_bytes(evidence.manifest)
        index=None if data is None else (frozenset(evidence.source),Path(evidence.manifest.uri).parent,
                                         _manifest_entries(data))
    except (ValueError,TypeError,KeyError):
        index=None
    if len(_ADMISSION_INDEX)>64:
        _ADMISSION_INDEX.clear()
    _ADMISSION_INDEX[key]=(evidence.source,evidence.manifest,index)
    return index


def _admitted_source(evidence,ref):
    if not isinstance(ref,SourceRef) or evidence.manifest is None:
        return False
    index=_admission_index(evidence)
    if index is None:
        return False
    sources,root,entries=index
    if ref not in sources or not _source_ok(ref):
        return False
    try:
        return _sealed_source(ref,root,entries)
    except (ValueError,TypeError,KeyError):
        return False


def _verified_review(evidence,review,digest,scope):
    return (isinstance(review,ReviewRecord) and _review_binds(review,digest,(scope,))
            and all(_admitted_source(evidence,r) for r in (*review.refs,review.authority_ref)))


def _f32_control(control):
    """CARLA stores VehicleControl floats as float32 (native 2026-10-22: brake .3 reads back 0.30000001192092896).
    The readback of an exact command is the command or its float32 image, nothing else."""
    from dataclasses import replace
    from .response import _f32
    return replace(control,throttle=_f32(control.throttle),steer=_f32(control.steer),brake=_f32(control.brake))


def _readback_matches(control,readback):
    """Server readback of an exact command: the command or its float32 image. In automatic transmission
    (manual_gear_shift False on both) CARLA ignores the commanded gear and reads back the transmission's actual gear
    (native 2026-10-22: HOLD gear=1 reads back gear=0 at standstill), so gear is not compared there."""
    from dataclasses import replace
    if not control.manual_gear_shift and not readback.manual_gear_shift:
        control=replace(control,gear=readback.gear)
    return readback in (control,_f32_control(control))


def _frame_integrity(evidence,fixture):
    invalid=[];uncertain=[];identity=None
    response_hashes={r.hash for r in fixture.responses}
    capability_types={
        'continuous_geometry':('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1'),
        'rollback':('ROLLBACK','unpowered-grade-motion-v1'),
        'door_geometry':('DOOR_GEOMETRY','calibrated-door-envelope-v1'),
        'preparation_cue':('REVERSE_PREPARATION','frame-correlated-cue-v1'),
        'preparation_request':('REVERSE_PREPARATION_REQUEST','owned-reverse-preparation-v1'),
        'return_path':('RETURN_PATH','bounded-return-corridor-v1'),
        'lane_change_path':('LANE_CHANGE_PATH','bounded-lane-change-corridor-v1'),
        'queue_path':('QUEUE_PATH','bounded-queue-exit-corridor-v1'),
        'validation_start':('VALIDATION_START','recorded-readiness-start-v1'),
    }
    for f in evidence.raw:
        for key,(kind,method) in capability_types.items():
            if key not in f.integrity:
                continue
            proof=decode_record('CapabilityProof',encode_record(f.integrity[key]))
            if not isinstance(proof,CapabilityProof):
                invalid.append('FRAME_CAPABILITY_SOURCE_INVALID');continue
            packet={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
            if (proof.kind!=kind or proof.method!=method or not proof.raw_refs
                    or any(not _admitted_source(evidence,r) for r in proof.raw_refs)
                    or not _verified_review(evidence,proof.review,_digest(packet),'CAPABILITY:'+kind)):
                invalid.append('FRAME_CAPABILITY_SOURCE_INVALID')
        actors={a.role:a for a in f.actors}
        ids={role:a.id for role,a in actors.items()}
        if (set(actors)!={'EGO','NPC'} or len(actors)!=len(f.actors) or len(set(ids.values()))!=len(ids)
                or (identity is not None and ids!=identity)):
            invalid.append('FRAME_CORRELATION_INVALID')
        if identity is None:
            identity=ids
        for actor in f.actors:
            if actor.readback is None or not actor.commands or not isinstance(f.integrity.get('plan_refs'),Mapping):
                uncertain.append('ACTOR_CONTROL_OR_PLAN_WITNESS_MISSING')
            if type(actor.plan_queue) is not int or actor.plan_queue<0 or len(actor.commands)>1:
                invalid.append('FRAME_CORRELATION_INVALID')
            for command in actor.commands:
                if (command.control is not None and actor.readback is not None
                        and not _readback_matches(command.control,actor.readback)):
                    invalid.append('CONTROL_READBACK_MISMATCH')
                if (command.actor!=actor.id or command.frame!=f.frame-1 or command.next_frame!=f.frame
                        or command.response_hash not in response_hashes):
                    invalid.append('FRAME_CORRELATION_INVALID')
        plans=f.integrity.get('plan_refs')
        if isinstance(plans,Mapping):
            if set(plans)!=set(actors):
                invalid.append('PLAN_SOURCE_WITNESS_INVALID')
            for role,packet in plans.items():
                ref=decode_record('SourceRef',encode_record(packet))
                route=_decode_source_record('DirectedRoute',ref) if isinstance(ref,SourceRef) else None
                actor=actors.get(role)
                responses=tuple(r for r in fixture.responses if r.actor_role==role and actor is not None
                                and any(c.response_hash==r.hash for c in actor.commands))
                reference=responses[0] if len(responses)==1 else None
                if reference is not None and reference.phases.get('reference_switches'):
                    from .response import _reference_response
                    try:
                        reference=_reference_response(reference,actor.commands[0].cause)
                    except ValueError:
                        reference=None
                if (not isinstance(ref,SourceRef) or ref not in evidence.source or not isinstance(route,DirectedRoute)
                        or reference is None or reference.route is None or _digest(route)!=_digest(reference.route)):
                    invalid.append('PLAN_SOURCE_WITNESS_INVALID')
        for event in f.events:
            if not event.witness_refs or any(not _admitted_source(evidence,r) for r in event.witness_refs):
                invalid.append('EVENT_SOURCE_WITNESS_INVALID')
            if (event.frame!=f.frame or event.time!=f.simtime or not event.witness_refs
                    or not any(r.frame==f.frame and r.time==f.simtime for r in event.witness_refs)):
                invalid.append('FRAME_CORRELATION_INVALID')
        refs=f.integrity.get('frame_refs')
        if not isinstance(refs,tuple) or not refs:
            uncertain.append('FRAME_SOURCE_WITNESS_MISSING')
            continue
        for packet in refs:
            ref=decode_record('SourceRef',encode_record(packet))
            if (not isinstance(ref,SourceRef) or ref.frame!=f.frame or ref.time!=f.simtime
                    or ref not in evidence.source or _source_bytes(ref) is None):
                invalid.append('FRAME_SOURCE_WITNESS_INVALID')
                continue
            try:
                observed=json.loads(_source_bytes(ref))
                expected=encode_record({'boot':f.boot,'world':f.world,'frame':f.frame,
                                        'simtime':f.simtime,'actors':f.actors})
                if observed!=expected:
                    invalid.append('FRAME_OBSERVATION_CONTENT_MISMATCH')
            except (ValueError,TypeError,UnicodeError):
                invalid.append('FRAME_OBSERVATION_CONTENT_MISMATCH')
    return tuple(dict.fromkeys(invalid)),tuple(dict.fromkeys(uncertain))


def _metric_context_integrity(evidence,fixture):
    """Freeze observation references/uncertainty before any numerical admission."""
    invalid=[];uncertain=[];pair=fixture.pair
    route_estimators={'forward_distance','reverse_distance','min_front_gap','min_rear_gap'}
    for frame in evidence.raw:
        context=frame.integrity.get('metric_context')
        if context is None:
            uncertain.append('METRIC_CONTEXT_MISSING');continue
        if not isinstance(context,Mapping):
            invalid.append('METRIC_CONTEXT_INVALID');continue
        errors=context.get('uncertainty')
        if (context.get('reference')!=pair.reference or context.get('pair_hash')!=pair.hash
                or not isinstance(errors,Mapping) or set(errors)!=set(pair.names)
                or any(isinstance(v,bool) or not isinstance(v,(int,Fraction)) or v<0 for v in errors.values())):
            invalid.append('METRIC_CONTEXT_INVALID');continue
        if route_estimators.intersection(pair.estimators):
            route=decode_record('DirectedRoute',encode_record(context.get('directed_route')))
            expected=fixture.routes.get('EGO')
            if (not isinstance(route,DirectedRoute) or expected is None or _digest(route)!=_digest(expected)
                    or pair.reference!='route:'+_digest(route) or not route.continuity
                    or any(not _admitted_source(evidence,r) for r in route.continuity)):
                invalid.append('METRIC_CONTEXT_INVALID')
        elif 'map_lateral_peak' in pair.estimators:
            from .metrics import _map_offset
            packet=context.get('map_reference')
            if not isinstance(packet,Mapping) or set(packet)!={'method','route','normals','refs'}:
                invalid.append('METRIC_CONTEXT_INVALID');continue
            route=decode_record('DirectedRoute',encode_record(packet['route']))
            sources=packet['refs'];ego=tuple(a for a in frame.actors if a.role=='EGO')
            if not isinstance(sources,tuple):
                invalid.append('METRIC_CONTEXT_INVALID');continue
            sources=tuple(decode_record('SourceRef',encode_record(r)) for r in sources)
            if (not isinstance(route,DirectedRoute) or not sources or not route.continuity
                    or fixture.routes.get('EGO') is None or route.map_hash!=fixture.routes['EGO'].map_hash
                    or any(not _admitted_source(evidence,r) for r in (*sources,*route.continuity))
                    or len(ego)!=1 or _map_offset(ego[0].pose,packet,pair.reference) is None):
                invalid.append('METRIC_CONTEXT_INVALID')
    return tuple(dict.fromkeys(invalid)),tuple(dict.fromkeys(uncertain))


def _target_integrity(evidence,fixture):
    """Bind recorded target units to frozen phase targets, never to realized speed.

    targets maps phase/cause names to m/s; phase ordering/guards additionally need
    observed action checks and the T10/T11 state-machine producer contract.
    """
    invalid=[];uncertain=[]
    for frame in evidence.raw:
        for actor in frame.actors:
            if not actor.commands:
                uncertain.append('TARGET_PROGRAM_MISSING')
            for command in actor.commands:
                responses=tuple(r for r in fixture.responses if r.actor_role==actor.role and r.hash==command.response_hash)
                if len(responses)!=1:
                    invalid.append('TARGET_PROGRAM_MISMATCH');continue
                targets=responses[0].targets
                if not targets:
                    uncertain.append('TARGET_PROGRAM_MISSING');continue
                target=targets.get(command.cause)
                if (isinstance(target,bool) or not isinstance(target,(int,Fraction)) or target<0
                        or isinstance(command.target_kmh,bool) or not isinstance(command.target_kmh,(int,Fraction))
                        or command.target_kmh!=Fraction(18,5)*target):
                    invalid.append('TARGET_PROGRAM_MISMATCH')
    return tuple(dict.fromkeys(invalid)),tuple(dict.fromkeys(uncertain))


def _initial_state_matches(actor,pose):
    """First observation vs the frozen spawn pose (M56 v2 errata E3/E5, objective-error exception, 2026-10-23).

    OLD RULE (kept verbatim in initial_state_old_rule): actor.velocity==(0,0,0) and actor.pose==pose exactly. A spawned
    CARLA vehicle is only observable after one physics step, by which time it has settled 1-2 mm with a few mm/s
    (native g4 probe 2026-10-23), so the old rule can never hold natively. NEW RULE: x/y/yaw equal the float32
    image of the frozen pose within 1e-4; 0 <= z_frozen - z_observed <= 0.02 m (measured spawn clearance);
    |pitch|,|roll| <= 0.1 deg; speed <= 0.10 m/s (the spec's settle/stop threshold)."""
    from .response import _f32
    from .metrics import _speed
    a=actor.pose;yaw=(a.yaw-_f32(pose.yaw)+180)%360-180;speed=_speed(actor.velocity)
    return (abs(a.x-_f32(pose.x))<=1e-4 and abs(a.y-_f32(pose.y))<=1e-4 and abs(yaw)<=1e-4
            and 0<=pose.z-a.z<=.02 and abs(a.pitch)<=.1 and abs(a.roll)<=.1
            and speed is not None and speed<=Fraction(1,10))


def _runin_route_ok(actor,fixture):
    """v5 C1 (prereg eda7680): run-in room at ready = route distance from the EGO body's most forward route station to
    e_entry, > G. OLD RULE (runin_old_rule, report-only): plane distance -max(section margin) > G, which measures a
    lateral distance when the EGO enters the conflict box through a side face (L01, native 2026-10-24)."""
    from .geometry import world_vertices,project_route
    from .model import BlockedFixture
    stations=[project_route(v,fixture.routes['EGO']) for v in world_vertices(actor.body,actor.pose)]
    if not stations or any(isinstance(s,BlockedFixture) for s in stations):
        return False
    return fixture.domain.e_entry.route_station-max(stations)>fixture.G


def runin_old_rule(actor,fixture):
    """Report-only: the old plane-distance run-in rule."""
    from .metrics import _section_margin
    from .geometry import world_vertices
    margins=_section_margin(world_vertices(actor.body,actor.pose),fixture.domain.e_entry)
    return margins is not None and -max(margins)>fixture.G


def initial_state_old_rule(evidence,fixture):
    """Report-only: roles whose first observation fails the OLD exact rule (both rules are reported)."""
    boundary=_pre_observation(evidence)
    if boundary is None:
        return None
    return tuple(a.role for a in boundary.actors
                 if a.velocity!=(0.,0.,0.) or a.pose!=fixture.poses.get(a.role))


def _initialization_integrity(evidence,fixture):
    """Recorded spawn/settle/readiness contracts, not a native spawn implementation."""
    source=_bound_json(evidence,'initialization_ref')
    if source is None:
        return (),('INITIALIZATION_MISSING',)
    boundary=_pre_observation(evidence)
    if boundary is None:
        return (),('INITIALIZATION_BOUNDARY_MISSING',)
    from .metrics import _speed,_metric_station,_section_margin
    from .geometry import world_vertices
    packet,ref=source;review_source=_bound_json(evidence,'initialization_review_ref')
    required={'method','fixture_hash','boundary_hash','settled_frame','ready_frame','targets_mps','ready_markers_m','recipe_ref','settings'}
    try:
        if not isinstance(packet,dict) or set(packet)!=required or packet['method']!='recorded-initialization-v1':
            raise ValueError('schema')
        review=decode_record('ReviewRecord',review_source[0]) if review_source else None
        recipe=_source_json(evidence,packet['recipe_ref'])
        if (packet['fixture_hash']!=_digest(fixture) or packet['boundary_hash']!=_digest(boundary)
                or not _verified_review(evidence,review,_digest(packet),'INITIALIZATION')
                or not any((r.sha256,r.bytes)==(ref.sha256,ref.bytes) for r in review.refs)
                or recipe is None or recipe[1] not in review.refs
                or recipe[0].get('method')!=packet['method'] or not recipe[0].get('version') or not recipe[0].get('limitations')):
            raise ValueError('binding')
        settings=packet['settings']
        if (set(settings)!={'synchronous_mode','fixed_delta_seconds','max_substep_delta_time','max_substeps'}
                or settings['synchronous_mode'] is not True or _exact_bound(settings['fixed_delta_seconds'])!=Fraction(1,20)
                or _exact_bound(settings['max_substep_delta_time'])!=Fraction(1,100) or type(settings['max_substeps']) is not int
                or settings['max_substeps']!=10):
            raise ValueError('settings')
        metadata=fixture.environment.get('readiness')
        if not isinstance(metadata,Mapping) or set(metadata)!={'targets_mps','markers_m'}:
            return (),('INITIALIZATION_METADATA_MISSING',)
        if (packet['targets_mps']!=encode_record(metadata['targets_mps'])
                or packet['ready_markers_m']!=encode_record(metadata['markers_m'])
                or set(packet['targets_mps'])!={'EGO','NPC'}):
            raise ValueError('frozen readiness')
        initial={a.role:a for a in boundary.actors};declared={a.role:a for a in fixture.actors}
        if set(initial)!=set(declared) or set(initial)!={'EGO','NPC'}:
            raise ValueError('spawn registry')
        for role,a in initial.items():
            if (declared[role].initial_speed_mps!=0 or not _initial_state_matches(a,fixture.poses[role])
                    or declared[role].pose!=fixture.poses[role]
                    or a.body.blueprint!=declared[role].blueprint or a.route_valid is not True):
                raise ValueError('actual initial state')
        gi,gu=_ground_integrity(replace(evidence,raw=(boundary,)),fixture)
        if gi or gu:
            raise ValueError('initial ground')
        frames={f.frame:f for f in evidence.raw}
        if type(packet['settled_frame']) is not int or type(packet['ready_frame']) is not int:
            raise ValueError('frame types')
        settled=frames[packet['settled_frame']];ready=frames[packet['ready_frame']]
        if 'validation_start' in fixture.environment:
            from .metrics import _validation_start_frame
            if _validation_start_frame(evidence.raw,fixture)!=ready.frame:
                raise ValueError('validation clock differs from initialization readiness')
            start=decode_record('CapabilityProof',encode_record(ready.integrity.get('validation_start')))
            binding={k:getattr(start,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
            if (not _verified_review(evidence,start.review,_digest(binding),'CAPABILITY:VALIDATION_START')
                    or any(not _admitted_source(evidence,r) for r in start.raw_refs)):
                raise ValueError('validation clock source unadmitted')
        if (settled.simtime-boundary.simtime<1 or not settled.simtime<ready.simtime<=settled.simtime+15
                or evidence.end_simtime-ready.simtime>Fraction(121,2)
                or evidence.end_simtime-boundary.simtime>Fraction(153,2)):
            raise ValueError('clock bounds')
        for f in evidence.raw:
            if f.frame<=settled.frame and any(_speed(a.velocity) is None or _speed(a.velocity)>Fraction(1,10) for a in f.actors):
                raise ValueError('settle movement')
        hold=tuple(f for f in evidence.raw if ready.simtime-Fraction(1,2)<=f.simtime<=ready.simtime)
        if len(hold)!=11 or hold[0].simtime!=ready.simtime-Fraction(1,2):
            raise ValueError('ready hold')
        for f in hold:
            for a in f.actors:
                target=metadata['targets_mps'][a.role];speed=_speed(a.velocity)
                if not isinstance(target,Fraction) or target<0 or speed is None or abs(speed-target)>Fraction(1,10):
                    raise ValueError('ready speed')
                # A moving actor cannot hold a fixed station for .50s. Freeze the
                # terminal ready marker and corroborate the nominal run-in track
                # backwards over the hold, rather than bless a terminal teleport.
                marker=metadata['markers_m'][a.role]
                station=_metric_station((a.pose.x,a.pose.y,a.pose.z),fixture.routes[a.role])
                expected=marker-target*(ready.simtime-f.simtime) if isinstance(marker,Fraction) else None
                if expected is None or station is None or abs(station-expected)>Fraction(1,10):
                    raise ValueError('ready marker hold')
        for a in ready.actors:
            station=_metric_station((a.pose.x,a.pose.y,a.pose.z),fixture.routes[a.role])
            marker=metadata['markers_m'][a.role]
            if not isinstance(marker,Fraction) or station is None or abs(station-marker)>Fraction(1,10):
                raise ValueError('ready marker')
            if a.role=='EGO' and fixture.G is not None and not _runin_route_ok(a,fixture):
                raise ValueError('run-in room')
    except (KeyError,TypeError,ValueError,AttributeError,ZeroDivisionError):
        return ('INITIALIZATION_INVALID',),()
    return (),()


def _box_union_covers(envelope,regions,margin,uncertainty):
    """Exact partition containment; inflation applies to the union, not each seam."""
    from itertools import product
    from .geometry import _is_box
    if not _is_box(envelope) or not regions or any(not _is_box(r) for r in regions):
        return False
    low=tuple(Fraction(min(v[k] for v in envelope))-uncertainty-(margin if k<2 else 0) for k in range(3))
    high=tuple(Fraction(max(v[k] for v in envelope))+uncertainty+(margin if k<2 else 0) for k in range(3))
    boxes=[tuple((Fraction(min(v[k] for v in r)),Fraction(max(v[k] for v in r))) for k in range(3)) for r in regions]
    axes=[sorted({low[k],high[k],*(bound for box in boxes for bound in box[k] if low[k]<bound<high[k])}) for k in range(3)]
    if (len(axes[0])-1)*(len(axes[1])-1)*(len(axes[2])-1)>4096:
        return False  # Unsupported complexity is never a geometric success.
    return all(any(all(box[k][0]<=point[k]<=box[k][1] for k in range(3)) for box in boxes)
               for point in product(*(tuple((a+b)/2 for a,b in zip(axis,axis[1:])) for axis in axes)))


def _motion_integrity(evidence,fixture):
    """Admitted continuous enclosures and reference-acceleration bounds for all intervals.

    The receipt is not an implementation/qualification of a native enclosure
    producer. Enclosure containment is conservative: a protruding bound is unknown
    safety, NOT proof that the actual body crossed an edge.
    """
    source=_bound_json(evidence,'motion_ref')
    if source is None:
        return (),('MOTION_PROOF_MISSING',)
    from .model import _decode,VertexSet
    from .geometry import _is_box,world_vertices
    proof=decode_record('CapabilityProof',source[0])
    if not isinstance(proof,CapabilityProof):
        return ('MOTION_PROOF_INVALID',),()
    packet={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
    limits=proof.limits
    if (proof.kind!='CONTINUOUS_MOTION' or proof.method!='bounded-motion-envelope-v1' or proof.status!='CORROBORATED'
            or proof.uncertainty is None or not 0<=proof.uncertainty<=Fraction(1,20)
            or set(limits)!={'fixture_hash','trajectory_hash','recipe_ref','recipe_review','intervals_ref'}
            or limits['fixture_hash']!=_digest(fixture) or limits['trajectory_hash']!=_digest(evidence.raw)
            or not _verified_review(evidence,proof.review,_digest(packet),'CAPABILITY:CONTINUOUS_MOTION')):
        return ('MOTION_PROOF_INVALID',),()
    regions=fixture.domain.topology.get('driving_regions')
    if not isinstance(regions,Mapping) or set(regions)!={'EGO','NPC'}:
        return (),('MOTION_REGIONS_MISSING',)
    recipe=_source_json(evidence,limits['recipe_ref']);intervals=_source_json(evidence,limits['intervals_ref'])
    uncertain=[]
    try:
        if recipe is None or intervals is None:
            raise ValueError('missing source')
        data,recipe_ref=recipe;rows,rows_ref=intervals
        review=decode_record('ReviewRecord',encode_record(limits['recipe_review']))
        if (set(data)!={'method','version','quantities','source_refs'} or data['method']!=proof.method or not data['version']
                or data['quantities']!=['continuous_body_enclosure','reference_lateral_acceleration']
                or not _verified_review(evidence,review,_digest(data),'MOTION_RECIPE') or recipe_ref not in review.refs
                or not data['source_refs'] or any(_source_json(evidence,r) is None for r in data['source_refs'])
                or rows_ref not in proof.raw_refs or rows_ref not in proof.review.refs
                or not isinstance(rows,list) or len(rows)!=len(evidence.raw)-1 or not rows):
            raise ValueError('recipe')
        end=None;intended=None
        if fixture.domain.topology.get('category') in ('I','O'):
            from .metrics import detect_events,_action_response
            # Only an additional enclosure constraint. Source/command/event
            # authentication remains independently mandatory for eligibility.
            response=_action_response(evidence.raw,fixture)
            end=next((e for e in detect_events(evidence.raw,fixture) if e.name=='X_END'),None)
            action_regions=fixture.domain.topology.get('action_regions')
            if response is not None and response.action_id in ('A','B') and isinstance(action_regions,Mapping):
                key='EGO_TARGET' if (fixture.domain.topology['category'],response.action_id)==('I','B') else 'EGO_INITIAL'
                intended=action_regions.get(key)
        for row,a,b in zip(rows,evidence.raw,evidence.raw[1:]):
            if (set(row)!={'boot','world','first_frame','last_frame','first_actors_hash','last_actors_hash','actors'}
                    or (row['boot'],row['world'])!=(a.boot,a.world) or (b.boot,b.world)!=(a.boot,a.world)
                    or type(row['first_frame']) is not int or type(row['last_frame']) is not int
                    or (row['first_frame'],row['last_frame'])!=(a.frame,b.frame) or b.frame!=a.frame+1
                    or b.simtime-a.simtime!=Fraction(1,20) or row['first_actors_hash']!=_digest(a.actors)
                    or row['last_actors_hash']!=_digest(b.actors) or set(row['actors'])!={'EGO','NPC'}):
                raise ValueError('interval')
            for aa in a.actors:
                bb=next(x for x in b.actors if x.role==aa.role);p=row['actors'][aa.role]
                if (set(p)!={'actor_id','response_hash','envelope','reference_lateral_acceleration_bound_mps2'}
                        or type(p['actor_id']) is not int or p['actor_id']!=aa.id or aa.id!=bb.id
                        or len(bb.commands)!=1 or bb.commands[0].response_hash!=p['response_hash']):
                    raise ValueError('actor')
                bound=_exact_bound(p['reference_lateral_acceleration_bound_mps2'])
                if bound<0:
                    raise ValueError('bound')
                if bound>Fraction(5,2):
                    uncertain.append('REFERENCE_LATERAL_BUDGET_UNPROVEN')
                envelope=_decode(VertexSet,p['envelope'],'motion.envelope')
                if not _is_box(envelope):
                    raise ValueError('enclosure schema')
                low=tuple(min(v[k] for v in envelope) for k in range(3));high=tuple(max(v[k] for v in envelope) for k in range(3))
                if any(not all(low[k]<=v[k]<=high[k] for k in range(3)) for actor in (aa,bb) for v in world_vertices(actor.body,actor.pose)):
                    raise ValueError('enclosure contradicts observation')
                if not _box_union_covers(envelope,regions[aa.role],Fraction(3,20),proof.uncertainty):
                    uncertain.append('CONTINUOUS_FIT_UNPROVEN')
                if (aa.role=='EGO' and end is not None and b.frame>end.frame
                        and (intended is None or not _box_union_covers(envelope,(intended,),Fraction(3,20),proof.uncertainty))):
                    uncertain.append('CONTINUOUS_POST_END_LANE_UNPROVEN')
    except (KeyError,TypeError,ValueError,StopIteration,ZeroDivisionError):
        return ('MOTION_PROOF_INVALID',),()
    return (),tuple(dict.fromkeys(uncertain))


def _pre_observation(evidence):
    """Sealed issuing-boundary snapshot, not an inferred previous pose."""
    source=_bound_json(evidence,'pre_observation_ref')
    if source is None or not evidence.raw:
        return None
    frame=decode_record('FrameRecord',source[0]);first=evidence.raw[0]
    if (not isinstance(frame,FrameRecord) or (frame.boot,frame.world)!=(first.boot,first.world)
            or frame.frame+1!=first.frame or first.simtime-frame.simtime!=Fraction(1,20)
            or frame.dt!=Fraction(1,20)
            or {a.role:a.id for a in frame.actors}!={a.role:a.id for a in first.actors}
            or len(frame.actors)!=len(first.actors)):
        return None
    return frame


def _phase_integrity(evidence,fixture):
    """Replay frozen, ordered event guards at the issuing observation.

    This validates a recorded script, not approval of its chosen protocol. Actual
    action guards and source/authority admission remain independent requirements.
    """
    from .metrics import _authenticated_events,detect_events,_frame_refs
    from .response import _advance_program,reverse_intent,step_response,_reverse_priority
    from .model import ScriptState,EventRecord
    from dataclasses import replace
    invalid=[];uncertain=[];boundary=_pre_observation(evidence)
    events=None;loaded=False
    for response in fixture.responses:
        commands=[(f,a,c) for f in evidence.raw for a in f.actors for c in a.commands
                  if a.role==response.actor_role and c.response_hash==response.hash
                  and c.kind in ('CONTROL','REVERSE','REVERSE_HOLD','REVERSE_REQUEST','GEAR_TRANSITION',
                                 'DOOR_OPEN_REQUEST','DOOR_CLOSE_REQUEST')]
        if not commands:
            continue
        program=response.phases.get('program')
        if program is None:
            uncertain.append('PHASE_PROGRAM_MISSING');continue
        if (not isinstance(program,Mapping) or set(program)!={'method','initial','transitions'}
                or program['method']!='ordered-event-program-v1'
                or not isinstance(program['initial'],str) or program['initial'] not in response.targets
                or not isinstance(program['transitions'],tuple)):
            invalid.append('PHASE_PROGRAM_INVALID');continue
        names={program['initial']};valid=True
        for row in program['transitions']:
            if (not isinstance(row,Mapping) or set(row)!={'cause','after_event','delay_s','requires'}
                    or not isinstance(row['cause'],str) or row['cause'] not in response.targets or row['cause'] in names
                    or not isinstance(row['after_event'],str) or not row['after_event']
                    or not isinstance(row['delay_s'],Fraction) or row['delay_s']<0
                    or not isinstance(row['requires'],tuple)
                    or any(not isinstance(g,str) or not g for g in row['requires'])):
                valid=False;break
            names.add(row['cause'])
        if not valid:
            invalid.append('PHASE_PROGRAM_INVALID');continue
        if boundary is None:
            uncertain.append('PHASE_BOUNDARY_MISSING');continue
        if not loaded:
            events=_authenticated_events(evidence,fixture);loaded=True
            if events is not None:
                trigger=next((e for e in events if e.name=='TRIGGER'),None)
                if trigger is not None:
                    post=tuple(f for f in evidence.raw if f.frame>=trigger.frame)
                    stop=next((e for e in detect_events(post,fixture) if e.name=='STOP_CONFIRMED'),None)
                    if stop is not None:
                        from dataclasses import replace
                        events=(*events,replace(stop,name='STOP_AFTER_TRIGGER'))
        observations={f.frame:f for f in (boundary,*evidence.raw)}
        # The boundary is a sealed observation. Recurring path receipts are not
        # latched globally: the shared producer filters them at each issuing tick.
        known=(EventRecord('CAPTURE_START',boundary.frame,boundary.simtime,()),*(events or ()))
        needs_events=any(row['after_event']!='CAPTURE_START' or any(g!='CAPTURE_START' for g in row['requires'])
                         for row in program['transitions'])
        if needs_events and events is None:
            uncertain.append('PHASE_EVENT_WITNESS_UNKNOWN');continue
        state=ScriptState(program['initial'],boundary.simtime,())
        metadata=response.phases.get('reverse',response.phases.get('f_script',{}))
        bounded=(isinstance(metadata,Mapping) and (
            (response.actor_role=='EGO' and response.action_id=='B' and metadata.get('mechanism') in ('F03','F06-ALT1'))
            or (response.actor_role=='NPC' and response.action_id=='NPC_COMMON' and metadata.get('mechanism')=='F06-ALT1')))
        door=(response.actor_role=='NPC' and response.action_id=='NPC_COMMON'
              and isinstance(metadata,Mapping) and metadata.get('mechanism')=='F04')
        if not bounded and any(c.kind!='CONTROL' and not (door and c.kind in ('DOOR_OPEN_REQUEST','DOOR_CLOSE_REQUEST'))
                               for _,_,c in commands):
            uncertain.append('REVERSE_COMMAND_PROGRAM_UNPROVEN');continue
        for frame,actor,command in commands:
            observed=observations.get(command.frame)
            if (observed is None or command.frame!=frame.frame-1 or command.next_frame!=frame.frame
                    or command.actor!=actor.id):
                invalid.append('PHASE_PROGRAM_MISMATCH');continue
            admitted=tuple(e for e in known if e.frame<=observed.frame and e.time<=observed.simtime)
            if bounded and (command.kind!='CONTROL' or any(e.name=='TRIGGER' for e in admitted)):
                # The sealed boundary's CAPTURE_START token is a timer anchor,
                # not a physical event receipt. Passing it into stock-forward
                # continuation would violate step_response's source-event gate.
                state=replace(state,events=tuple(e for e in admitted if e!=known[0]))
                try:
                    history_ref=decode_record('SourceRef',encode_record(observed.integrity.get('reverse_history_ref')))
                    history=_read_trajectory(history_ref) if _admitted_source(evidence,history_ref) else None
                    if history is None or len(history)>1532 or any(not _frame_refs(f) or any(not _admitted_source(evidence,r)
                            for r in _frame_refs(f)) for f in history):
                        raise ValueError('REVERSE_HISTORY_UNADMITTED')
                    proofs=tuple(p for p in fixture.proofs if p.kind=='REVERSE_STOP_BOUND'
                                 and p.limits.get('actor_role')==response.actor_role)
                    if len(proofs)!=1:raise ValueError('REVERSE_STOP_BOUND_MISSING')
                    if state.phase not in ('FORWARD','NPC_FORWARD'):
                        corridors=observed.integrity.get('reverse_corridors')
                        corridor=(corridors.get(response.actor_role) if isinstance(corridors,Mapping)
                                  else observed.integrity.get('reverse_corridor'))
                        proof=decode_record('CapabilityProof',encode_record(corridor))
                        proofs=(*proofs,proof)
                    for proof in proofs:
                        if not isinstance(proof,CapabilityProof):raise ValueError('REVERSE_CAPABILITY_UNADMITTED')
                        packet={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
                        if (any(not _admitted_source(evidence,r) for r in proof.raw_refs)
                                or not _verified_review(evidence,proof.review,_digest(packet),'CAPABILITY:'+proof.kind)):
                            raise ValueError('REVERSE_CAPABILITY_UNADMITTED')
                    if response.actor_role=='NPC':
                        npc=next(a for a in observed.actors if a.role=='NPC')
                        traffic=_reverse_priority(observed,npc,require_clear=False)
                        if any(not _admitted_source(evidence,r) for r in traffic['witness_refs']):
                            raise ValueError('NPC_CONTROL_WITNESS_MISSING')
                    replay=reverse_intent(observed,state,response,fixture)
                except (ValueError,TypeError,KeyError,AttributeError,StopIteration):
                    uncertain.append('REVERSE_COMMAND_REPLAY_UNPROVEN');continue
                if replay.command.kind=='BLOCKED' or replay.state.phase in ('BLOCKED_CONTROLLER','FAILED'):
                    uncertain.append('REVERSE_COMMAND_REPLAY_UNPROVEN');continue
                # Positive stock continuation materializes its own PID control;
                # compare the complete produced intent, not an invented PID.
                # Mandatory reverse/hold/gear controls remain exact matches.
                actual=replace(command,control=None) if replay.command.control is None else command
                if _digest(actual)!=_digest(replay.command):
                    invalid.append('REVERSE_COMMAND_MISMATCH')
                state=replay.state
                continue
            prior=state
            state=_advance_program(observed,state,response,known)
            if command.cause!=state.phase:
                invalid.append('PHASE_PROGRAM_MISMATCH')
            if (response.actor_role=='EGO' and response.action_id in ('A','B')
                    and fixture.domain.topology.get('mechanism')=='F04'):
                # Re-run the producer from its PRIOR phase, not the newly
                # advanced phase (one transition per observed issuing frame).
                # Actual stock PID output is not reproduced by this guard replay;
                # targets/offsets/readback keep their independent source gates.
                replay_state=replace(prior,events=tuple(e for e in admitted if e!=known[0]))
                try:
                    if (response.targets[program['initial']]==0 and program['transitions']
                            and program['transitions'][0]['after_event']=='CAPTURE_START'):
                        refs=_frame_refs(boundary)
                        if not refs or any(not _admitted_source(evidence,r) for r in refs):
                            raise ValueError('PHASE_BOUNDARY_MISSING')
                        # A separately frozen initialization clock is not a
                        # physical door/path event. Retain its source attribution
                        # for staging only; all maneuver permissions stay actual.
                        replay_state=replace(replay_state,events=(replace(known[0],witness_refs=refs),*replay_state.events))
                    replay=step_response(observed,replay_state,response)
                except (ValueError,TypeError,KeyError,AttributeError):
                    uncertain.append('FORWARD_COMMAND_REPLAY_UNPROVEN');continue
                if replay.command.kind=='BLOCKED':
                    uncertain.append('FORWARD_COMMAND_REPLAY_UNPROVEN')
                elif replay.state.phase!=state.phase:
                    invalid.append('PHASE_PROGRAM_MISMATCH')
            if (response.actor_role=='EGO' and response.action_id=='B'
                    and fixture.domain.topology.get('mechanism')=='F05'
                    and any(row['after_event']=='EGO_CREEP_STOPPING_BOUND' for row in program['transitions'])
                    and any(e.name=='TRIGGER' for e in admitted)):
                # Preserve unchanged stock PID materialization; independently
                # replay the bounded intent/mandatory terminal brake/current
                # source admission at its actual issuing observation.
                try:
                    context=_source_json(evidence,observed.integrity.get('creep_fixture_ref'))
                    history=_source_json(evidence,observed.integrity.get('creep_history_ref'))
                    if context is None or history is None:
                        raise ValueError('CREEP_CONTEXT_UNADMITTED')
                    decoded=decode_record('CompiledFixture',context[0])
                    if _digest(decoded)!=_digest(fixture):raise ValueError('CREEP_FIXTURE_UNBOUND')
                    proofs=tuple(p for p in fixture.proofs if p.kind=='CREEP_STOP_BOUND')
                    if len(proofs)!=1 or proofs[0].review is None:
                        raise ValueError('CREEP_STOP_BOUND_MISSING')
                    refs=(*proofs[0].raw_refs,*proofs[0].review.refs,proofs[0].review.authority_ref)
                    if any(not _admitted_source(evidence,r) for r in refs):raise ValueError('CREEP_STOP_BOUND_UNADMITTED')
                    replay=step_response(observed,replace(prior,events=tuple(e for e in admitted if e!=known[0])),response)
                except (ValueError,TypeError,KeyError,AttributeError):
                    uncertain.append('FORWARD_COMMAND_REPLAY_UNPROVEN');continue
                if replay.command.kind=='BLOCKED':
                    uncertain.append('FORWARD_COMMAND_REPLAY_UNPROVEN')
                elif _digest(command if replay.command.control is not None else replace(command,control=None))!=_digest(replay.command):
                    invalid.append('FORWARD_COMMAND_MISMATCH')
            if (response.actor_role=='NPC' and response.action_id=='NPC_COMMON'
                    and isinstance(metadata,Mapping) and metadata.get('mechanism') in ('F03','F04','F05')):
                replay_state=replace(prior if door or metadata.get('mechanism')=='F05' else state,
                                     events=tuple(e for e in admitted if e!=known[0]))
                try:
                    npc=next(a for a in observed.actors if a.role=='NPC')
                    traffic=_reverse_priority(observed,npc,require_clear=False)
                    if any(not _admitted_source(evidence,r) for r in traffic['witness_refs']):
                        raise ValueError('NPC_CONTROL_WITNESS_MISSING')
                    source=replace(observed,integrity={**observed.integrity,'npc_controls':traffic})
                    if door:
                        refs=_frame_refs(boundary)
                        if not refs or any(not _admitted_source(evidence,r) for r in refs):
                            raise ValueError('PHASE_BOUNDARY_MISSING')
                        capture=replace(known[0],witness_refs=refs)
                        # Capture is a SOURCE-BOUND initialization clock, never a
                        # geometry/closed-clear observation. Retain it only for
                        # the frozen one-shot open request, not native admission.
                        replay_state=replace(replay_state,events=(capture,*replay_state.events))
                    replay=step_response(source,replay_state,response)
                except (ValueError,TypeError,KeyError,AttributeError,StopIteration):
                    uncertain.append('FORWARD_COMMAND_REPLAY_UNPROVEN');continue
                if replay.command.kind=='BLOCKED':
                    uncertain.append('FORWARD_COMMAND_REPLAY_UNPROVEN')
                elif _digest(command if replay.command.control is not None else replace(command,control=None))!=_digest(replay.command):
                    # Mandatory zero-target motor control is replayed exactly.
                    # A positive stock intent does not recreate its PID output;
                    # actual materialized control/readback/source/stock gates
                    # remain separate, with no inferred dynamics permission.
                    invalid.append('FORWARD_COMMAND_MISMATCH')
    return tuple(dict.fromkeys(invalid)),tuple(dict.fromkeys(uncertain))


def _offset_integrity(evidence,fixture):
    """Command reference arithmetic, not realized lateral tracking or fit proof.

    Evaluate from the observed issuing frame, never from receiving-frame pose or
    the actor's asserted arc. Original source/plan authentication is independent.
    Target-plan switches/rebases are unsupported until their producer is bound.
    """
    from .response import desired_offset,_reference_response,_program
    from .metrics import _metric_station
    invalid=[];uncertain=[]
    frames={(f.boot,f.world,f.frame):f for f in evidence.raw}
    boundary=_pre_observation(evidence)
    if boundary is not None:
        frames[(boundary.boot,boundary.world,boundary.frame)]=boundary
    for frame in evidence.raw:
        for actor in frame.actors:
            for command in actor.commands:
                if command.kind!='CONTROL':
                    continue
                responses=tuple(r for r in fixture.responses
                                if r.actor_role==actor.role and r.hash==command.response_hash)
                if len(responses)!=1:
                    invalid.append('OFFSET_PROGRAM_MISMATCH');continue
                response=responses[0]
                if not isinstance(response.profile,Mapping) or 'method' not in response.profile:
                    uncertain.append('OFFSET_PROFILE_MISSING');continue
                try:
                    desired_offset(Fraction(0),response)  # Validate the entire frozen recipe.
                except ValueError:
                    invalid.append('OFFSET_PROFILE_INVALID');continue
                if response.route!=fixture.routes.get(actor.role):
                    invalid.append('OFFSET_ROUTE_MISMATCH');continue
                reference=response
                if response.phases.get('reference_switches'):
                    try:
                        reference=_reference_response(response,command.cause)
                    except ValueError:
                        invalid.append('OFFSET_REFERENCE_SWITCH_INVALID');continue
                route=reference.route
                if not isinstance(route,DirectedRoute):
                    uncertain.append('OFFSET_PROJECTION_UNKNOWN');continue
                previous=frames.get((frame.boot,frame.world,command.frame))
                if previous is None:
                    uncertain.append('OFFSET_SOURCE_FRAME_MISSING');continue
                if command.frame!=frame.frame-1 or command.next_frame!=frame.frame:
                    invalid.append('OFFSET_PROGRAM_MISMATCH');continue
                sources=tuple(a for a in previous.actors if a.role==actor.role and a.id==actor.id==command.actor)
                if len(sources)!=1 or sources[0].route_valid is not True:
                    uncertain.append('OFFSET_PROJECTION_UNKNOWN');continue
                pose=sources[0].pose
                arc=_metric_station((pose.x,pose.y,pose.z),route)
                if arc is None:
                    uncertain.append('OFFSET_PROJECTION_UNKNOWN');continue
                if response.phases.get('reference_switches'):
                    program=_program(response);names=(program['initial'],*(t['cause'] for t in program['transitions']))
                    if any(names.index(s['cause'])<=names.index(command.cause) and arc<s['marker_arc_m']
                           for s in response.phases['reference_switches']):
                        invalid.append('OFFSET_REFERENCE_SWITCH_INVALID');continue
                if (not isinstance(command.offset,Fraction)
                        or command.offset!=desired_offset(arc,reference)):
                    invalid.append('OFFSET_PROGRAM_MISMATCH')
    return tuple(dict.fromkeys(invalid)),tuple(dict.fromkeys(uncertain))


def _normative_integrity(evidence,fixture):
    from .response import _forward_contract
    invalid=[];uncertain=[]
    active={c.response_hash for f in evidence.raw for a in f.actors for c in a.commands}
    for response in fixture.responses:
        if response.hash not in active:
            continue
        if fixture.domain.topology.get('category') in ('C','L','M') and response.actor_role=='EGO' and 'program' not in response.phases:
            uncertain.append('NORMATIVE_RESPONSE_UNPROVEN')
            continue
        try:
            _forward_contract(response,fixture)
        except ValueError as exc:
            if any(code in str(exc) for code in ('UNPROVEN','MISSING')):
                uncertain.append('NORMATIVE_RESPONSE_UNPROVEN')
            else:
                invalid.append('NORMATIVE_RESPONSE_INVALID')
    return tuple(dict.fromkeys(invalid)),tuple(dict.fromkeys(uncertain))


def _lateral_integrity(evidence,fixture):
    """Validate the desired profile independently of sampled/motion success."""
    from .response import _lateral_contract
    active={c.response_hash for f in evidence.raw for a in f.actors for c in a.commands}
    invalid=[];uncertain=[]
    for response in fixture.responses:
        if response.hash not in active:
            continue
        if not response.profile or 'method' not in response.profile:
            uncertain.append('LATERAL_PROFILE_MISSING');continue
        try:
            _lateral_contract(response,fixture)
        except ValueError as exc:
            # Unsupported/missing conservative geometry is a blocked capability,
            # not evidence that an authenticated commanded action was invalid.
            if any(code in str(exc) for code in ('UNSUPPORTED','UNPROVEN','MISSING')):
                uncertain.append('LATERAL_CONTRACT_UNPROVEN')
            else:
                invalid.append('LATERAL_CONTRACT_INVALID')
        except (TypeError,KeyError,AttributeError):
            invalid.append('LATERAL_CONTRACT_INVALID')
    return tuple(dict.fromkeys(invalid)),tuple(dict.fromkeys(uncertain))


def _ground_integrity(evidence,fixture):
    """Source-bound ground observations, never inferred from map z or route_valid.

    recorded-ground-contact-v1 is a receipt schema only. Native contact producers
    and their authority/qualification remain separate admission requirements.
    """
    invalid=[];uncertain=[]
    for frame in evidence.raw:
        for actor in frame.actors:
            proof=actor.ground
            if proof is None:
                uncertain.append('GROUND_WITNESS_MISSING');continue
            proof=decode_record('CapabilityProof',encode_record(proof))
            if not isinstance(proof,CapabilityProof):
                invalid.append('GROUND_PROOF_INVALID');continue
            packet={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
            limits=proof.limits;kind='GROUND:'+actor.role;error=limits.get('maximum_ground_error_m')
            expected={'fixture_hash','boot','world','frame','actor_id','body_pose_hash','maximum_ground_error_m','contact_method','recipe_ref'}
            if (proof.kind!=kind or proof.method!='recorded-ground-contact-v1' or proof.status!='CORROBORATED'
                    or set(limits)!=expected or limits['fixture_hash']!=_digest(fixture)
                    or (limits['boot'],limits['world'],limits['frame'],limits['actor_id'])!=(frame.boot,frame.world,frame.frame,actor.id)
                    or type(limits['frame']) is not int or type(limits['actor_id']) is not int
                    or limits['body_pose_hash']!=_digest({'body':actor.body,'pose':actor.pose})
                    or limits['contact_method']!=proof.method or not proof.raw_refs
                    or isinstance(error,bool) or not isinstance(error,(int,Fraction)) or error<0
                    or isinstance(proof.uncertainty,bool) or not isinstance(proof.uncertainty,(int,Fraction))
                    or proof.uncertainty<0 or error+proof.uncertainty>Fraction(1,20)
                    or not _verified_review(evidence,proof.review,_digest(packet),'CAPABILITY:'+kind)):
                invalid.append('GROUND_PROOF_INVALID');continue
            recipe=_source_json(evidence,limits['recipe_ref'])
            if (recipe is None or not isinstance(recipe[0],dict) or recipe[0].get('method')!=proof.method
                    or not recipe[0].get('version') or not recipe[0].get('limitations') or recipe[1] not in proof.review.refs):
                invalid.append('GROUND_PROOF_INVALID');continue
            for ref in proof.raw_refs:
                observed=_source_json(evidence,ref)
                if (observed is None or ref not in proof.review.refs or (ref.frame,ref.time)!=(frame.frame,frame.simtime)
                        or observed[0]!=encode_record(limits)):
                    invalid.append('GROUND_PROOF_INVALID')
    return tuple(dict.fromkeys(invalid)),tuple(dict.fromkeys(uncertain))


def _bound_source(evidence,key):
    """Resolve source membership independently of the stream's serialization."""
    ref=decode_record('SourceRef',encode_record(evidence.integrity.get(key)))
    return ref if _admitted_source(evidence,ref) else None


def _bound_json(evidence,key):
    """An integrity field points to a sealed source, never to an asserted result."""
    ref=_bound_source(evidence,key)
    if ref is None:
        return None
    try:
        return json.loads(_source_bytes(ref)),ref
    except (ValueError,TypeError,UnicodeError):
        return None


def _collision_evidence(evidence):
    raw_ref=_bound_source(evidence,'collision_ref')
    registry=_bound_json(evidence,'sensor_registry_ref')
    if raw_ref is None or registry is None:
        return False,()
    registration,_=registry;payload=[];parse_errors=[]
    for line in _source_bytes(raw_ref).splitlines():
        try:
            row=json.loads(line)
            payload.extend(row if isinstance(row,list) else [row])
        except (ValueError,TypeError,UnicodeError):
            parse_errors.append('COLLISION_SCHEMA_INVALID')
    if (not isinstance(registration,dict)
            or set(registration)!={'boot','world','sensors'} or not isinstance(registration['sensors'],dict)):
        return False,('COLLISION_SCHEMA_INVALID',)
    trajectory=_bound_source(evidence,'trajectory_ref')
    recorded=_read_trajectory(trajectory) if trajectory is not None else None
    if recorded is None:
        return False,('COLLISION_TRAJECTORY_BINDING_MISSING',)
    late,late_errors=_late_collision_rows(evidence,raw_ref)
    frames={f.frame:f for f in recorded};positive=False;errors=[*parse_errors,*late_errors]
    for row in [*payload,*late]:
        keys={'boot','world','sensor_id','frame','time','actor_id','other_actor_id','normal_impulse'}
        if not isinstance(row,dict) or set(row)!=keys or type(row['frame']) is not int:
            errors.append('COLLISION_SCHEMA_INVALID');continue
        frame=frames.get(row['frame'])
        if frame is None:
            errors.append('COLLISION_FRAME_MISSING');continue
        actors=tuple(a for a in frame.actors if a.id==row['actor_id'])
        if (len(actors)!=1 or (row['boot'],row['world'])!=(frame.boot,frame.world)
                or (registration['boot'],registration['world'])!=(frame.boot,frame.world)
                or registration['sensors'].get(str(row['sensor_id']))!=row['actor_id']):
            errors.append('COLLISION_IDENTITY_MISMATCH');continue
        packet={k:row[k] for k in ('sensor_id','frame','time','actor_id','other_actor_id','normal_impulse')}
        packet.update(transform=encode_record(actors[0].pose),raw_ref=encode_record(raw_ref),errors=[])
        event=decode_record('SensorPacket',packet)
        if (not isinstance(event,SensorPacket) or event.time!=frame.simtime or event.normal_impulse is None
                or event.other_actor_id is None or event.other_actor_id==event.actor_id):
            errors.append('COLLISION_SCHEMA_INVALID');continue
        positive=True  # even zero impulse is a reported contact, not silence
    return positive,tuple(dict.fromkeys(errors))


def _late_collision_rows(evidence,collision_ref):
    """Read append-only addenda bound to this exact seal and original collision stream."""
    if evidence.manifest is None or _source_bytes(evidence.manifest) is None:
        return (),()
    root=Path(evidence.manifest.uri).parent;directory=root/'addenda'
    if not directory.exists():
        return (),()
    rows=[];errors=[]
    try:
        for path in sorted(directory.iterdir()):
            _safe_path(root,path.relative_to(root).as_posix())
            if not path.is_file() or path.suffix!='.json':
                errors.append('CORRECTION_BINDING_INVALID');continue
            data=json.loads(path.read_bytes())
            if (not isinstance(data,dict) or set(data)!={'original','seal','record','eligibility'}
                    or data['eligibility']!='REVIEW_REQUIRED'):
                errors.append('CORRECTION_BINDING_INVALID');continue
            original=decode_record('ArtifactRef',data['original'])
            seal_ref=decode_record('ArtifactRef',data['seal'])
            if (not isinstance(original,ArtifactRef) or not isinstance(seal_ref,ArtifactRef)
                    or seal_ref.relativepath!='manifest.json' or seal_ref.hash!=evidence.manifest.sha256
                    or seal_ref.size!=evidence.manifest.bytes):
                errors.append('CORRECTION_BINDING_INVALID');continue
            original_path=_safe_path(root,original.relativepath)
            if not original_path.is_file() or _ref(root,original_path,original.kind)!=original:
                errors.append('CORRECTION_BINDING_INVALID');continue
            manifest=json.loads(_source_bytes(evidence.manifest))
            if not any(row['relativepath']==original.relativepath and row['hash']==original.hash and row['size']==original.size
                       for row in manifest['files']):
                errors.append('CORRECTION_BINDING_INVALID');continue
            record=data['record']
            if isinstance(record,dict) and record.get('kind')=='COLLISION':
                if (original_path!=Path(collision_ref.uri) or original.hash!=collision_ref.sha256
                        or original.size!=collision_ref.bytes or set(record)!={'kind','event'}):
                    errors.append('CORRECTION_BINDING_INVALID');continue
                rows.append(record['event'])
    except (OSError,ValueError,TypeError,KeyError,UnicodeError):
        errors.append('CORRECTION_BINDING_INVALID')
    return tuple(rows),tuple(dict.fromkeys(errors))


def _sealed_source(ref,root,entries):
    if not isinstance(ref,SourceRef):
        return False
    path=Path(ref.uri)
    try:
        relative=path.relative_to(root).as_posix()
    except ValueError:
        relative=f'sources/{ref.sha256}.bin'
    entry=entries.get(relative)
    return entry is not None and entry['hash']==ref.sha256 and entry['size']==ref.bytes


_SOURCE_RECORDS = {}


def _decode_source_record(kind,ref):
    # A verified source decodes to the same immutable record every time: memoized by (kind, SourceRef) for successful
    # decodes (perf 2026-10-25: per-frame plan-route decoding dominated offline evaluation). ponytail: assumes sealed
    # sources are not rewritten in place during one process; bounded clear-all cache.
    key=(kind,ref)
    try:
        hit=_SOURCE_RECORDS.get(key)
    except TypeError:
        return _decode_source_record_uncached(kind,ref)
    if hit is not None:
        return hit
    result=_decode_source_record_uncached(kind,ref)
    if result is not None and not hasattr(result,'errors'):
        if len(_SOURCE_RECORDS)>4096:
            _SOURCE_RECORDS.clear()
        _SOURCE_RECORDS[key]=result
    return result


def _decode_source_record_uncached(kind,ref):
    data=_source_bytes(ref)
    if data is None:
        return None
    try:
        return decode_record(kind,json.loads(data))
    except (ValueError,TypeError,UnicodeError):
        return None


_TRAJECTORIES = {}


def _read_trajectory(ref):
    """Memoized by SourceRef for successful reads (a verified trajectory decodes to the same immutable frames);
    perf 2026-10-25: it was decoded 4 times per evaluation (~47 s each). ponytail: bounded clear-all cache."""
    try:
        hit=_TRAJECTORIES.get(ref)
    except TypeError:
        return _read_trajectory_uncached(ref)
    if hit is not None and _source_ok(ref):
        return hit
    result=_read_trajectory_uncached(ref)
    if result is not None:
        if len(_TRAJECTORIES)>16:
            _TRAJECTORIES.clear()
        _TRAJECTORIES[ref]=result
    return result


def _read_trajectory_uncached(ref):
    data=_source_bytes(ref)
    if data is None:
        return None
    try:
        rows=[]
        for line in data.splitlines():
            payload=json.loads(line)
            # T02 streams may contain individual frames or a single frozen batch.
            rows.extend(payload if isinstance(payload,list) else [payload])
        frames=tuple(decode_record('FrameRecord',row) for row in rows)
        return frames if frames and all(isinstance(f,FrameRecord) for f in frames) else None
    except (ValueError,TypeError,UnicodeError):
        return None


def _write_new(path: Path, payload: bytes) -> None:
    with path.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def open_run(root: Path, run_id: str, writer_id: str) -> RunStore | ReleaseBlocked:
    root=Path(root)
    if not run_id or not writer_id:
        return ReleaseBlocked('OUTPUT_BLOCKED', ('WRITER_ID_REQUIRED',))
    try:
        root.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        return ReleaseBlocked('OUTPUT_EXISTS', ('NAMESPACE_ALREADY_EXISTS',))
    try:
        _write_new(root/'writer.json', json.dumps({'run_id':run_id,'writer':writer_id},
                   sort_keys=True).encode('utf-8'))
    except OSError:
        # Keep partial namespace; never erase/reuse it automatically.
        return ReleaseBlocked('OUTPUT_BLOCKED', ('WRITER_RECEIPT_FAILED',))
    return RunStore(root.resolve(),run_id,writer_id,root.resolve()/'journal.jsonl')


def _payload(record: object) -> bytes:
    return (json.dumps(encode_record(record), sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8')


def _safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative,str) or not relative or '\\' in relative:
        raise ValueError('PATH_REJECTED')
    parts=PurePosixPath(relative).parts
    reserved={'CON','PRN','AUX','NUL'}|{f'{prefix}{i}' for prefix in ('COM','LPT') for i in range(1,10)}
    if (PurePosixPath(relative).is_absolute() or not parts or '/'.join(parts)!=relative
            or any(part in ('.','..') or not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*',part)
                   or part.endswith('.') or part.split('.')[0].upper() in reserved for part in parts)):
        raise ValueError('PATH_REJECTED')
    path=root.joinpath(*parts)
    for parent in (path,*path.parents):
        if parent==root.parent:
            break
        if parent.is_symlink() or (hasattr(parent,'is_junction') and parent.is_junction()):
            raise ValueError('PATH_REJECTED_LINK')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('PATH_REJECTED')
    return path


@contextmanager
def _writer(store: RunStore, *, allow_sealed: bool=False):
    receipt=json.loads((store.root/'writer.json').read_text(encoding='utf-8'))
    if receipt!={'run_id':store.run_id,'writer':store.writer}:
        raise ValueError('WRITER_MISMATCH')
    lock=_safe_path(store.root,'writer.lock')
    # Exclusive lease held across journal + effect; no automatic stale-lock removal.
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        if (store.root/'manifest.json').exists() and not allow_sealed:
            raise ValueError('SEALED_IMMUTABLE')
        os.write(fd,store.writer.encode('utf-8'))
        os.fsync(fd)
        yield
    finally:
        os.close(fd)
        lock.unlink()


def _append_bytes(path: Path, payload: bytes) -> None:
    with path.open('ab') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _ref(root: Path, path: Path, kind: str) -> ArtifactRef:
    data=path.read_bytes()
    return ArtifactRef(path.relative_to(root).as_posix(),hashlib.sha256(data).hexdigest(),len(data),kind)


def append_record(store: RunStore, stream: str, record: object) -> ArtifactRef:
    path=_safe_path(store.root,stream)
    if path.name in ('writer.json','manifest.json','journal.jsonl','writer.lock') or path.parts[len(store.root.parts)]=='addenda':
        raise ValueError('PATH_REJECTED_RESERVED')
    payload=_payload(record)
    with _writer(store):
        _append_bytes(store.journal,_payload({'operation':'APPEND_INTENT','stream':stream,
                       'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}))
        path.parent.mkdir(parents=True,exist_ok=True)
        _append_bytes(path,payload)
        return _ref(store.root,path,'STREAM')


def seal(store: RunStore) -> ArtifactRef:
    with _writer(store):
        _append_bytes(store.journal,_payload({'operation':'SEAL_INTENT'}))
        entries=[]
        for path in sorted(store.root.rglob('*')):
            relative=path.relative_to(store.root).as_posix()
            _safe_path(store.root,relative)
            if path.is_file() and relative!='writer.lock':
                entries.append(encode_record(_ref(store.root,path,'SEALED')))
        _write_new(store.root/'manifest.json',_payload({'schema':1,'files':entries}))
        return _ref(store.root,store.root/'manifest.json','MANIFEST')


def verify_manifest(root: Path) -> IntegrityReport:
    root=Path(root)
    reasons=[]
    try:
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        if set(manifest)!={'schema','files'} or manifest['schema']!=1 or not isinstance(manifest['files'],list):
            raise ValueError('MANIFEST_SCHEMA')
        seen=set()
        for entry in manifest['files']:
            if set(entry)!={'relativepath','hash','size','kind'}:
                raise ValueError('MANIFEST_ENTRY_SCHEMA')
            relative=entry['relativepath']
            if relative in seen or relative in ('manifest.json','writer.lock') or relative.startswith('addenda/'):
                raise ValueError('MANIFEST_DUPLICATE_OR_RESERVED')
            seen.add(relative)
            path=_safe_path(root,relative)
            if not path.is_file():
                reasons.append('MISSING:'+relative)
                continue
            actual=_ref(root,path,'SEALED')
            if actual.hash!=entry['hash'] or actual.size!=entry['size']:
                reasons.append('CONTENT_MISMATCH:'+relative)
        actual_files=set()
        for path in root.rglob('*'):
            rel=path.relative_to(root).as_posix()
            _safe_path(root,rel)
            if path.is_file() and rel not in ('manifest.json','writer.lock') and not rel.startswith('addenda/'):
                actual_files.add(rel)
        if actual_files!=seen or not {'writer.json','journal.jsonl'}<=seen:
            reasons.append('MANIFEST_COVERAGE')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        reasons.append('MANIFEST_INVALID:'+str(exc))
    return IntegrityReport('INTEGRITY_INVALID' if reasons else 'INTEGRITY_VALID',tuple(reasons))


def append_correction(store: RunStore, original: ArtifactRef, record: object) -> ArtifactRef:
    with _writer(store,allow_sealed=True):
        if not (store.root/'manifest.json').is_file():
            raise ValueError('ORIGINAL_SEAL_REQUIRED')
        integrity=verify_manifest(store.root)
        if integrity.status!='INTEGRITY_VALID':
            raise ValueError('ORIGINAL_INTEGRITY_INVALID')
        source=_safe_path(store.root,original.relativepath)
        actual=_ref(store.root,source,original.kind)
        if actual!=original:
            raise ValueError('ORIGINAL_REFERENCE_MISMATCH')
        manifest=json.loads((store.root/'manifest.json').read_text(encoding='utf-8'))
        if not any(entry['relativepath']==original.relativepath and entry['hash']==original.hash
                   for entry in manifest['files']):
            raise ValueError('ORIGINAL_NOT_SEALED')
        directory=_safe_path(store.root,'addenda')
        directory.mkdir(exist_ok=True)
        target=directory/f'{uuid.uuid4().hex}.json'
        _write_new(target,_payload({'original':encode_record(original),
                    'seal':encode_record(_ref(store.root,store.root/'manifest.json','MANIFEST')),
                    'record':record,'eligibility':'REVIEW_REQUIRED'}))
        return _ref(store.root,target,'CORRECTION')


def snapshot_sources(store: RunStore, refs: tuple[SourceRef,...]) -> IntegrityReport:
    reasons=[]
    verified=[]
    with _writer(store):
        for ref in refs:
            try:
                path=Path(ref.uri)
                if '://' in ref.uri or not path.is_absolute():
                    raise ValueError('SOURCE_LOCAL_ABSOLUTE_REQUIRED')
                if not re.fullmatch(r'[0-9a-f]{64}',ref.sha256) or type(ref.bytes) is not int:
                    raise ValueError('SOURCE_REF_INVALID')
                data=path.read_bytes()
                if len(data)!=ref.bytes or hashlib.sha256(data).hexdigest()!=ref.sha256:
                    raise ValueError('SOURCE_MISMATCH')
                dest=_safe_path(store.root,f'sources/{ref.sha256}.bin')
                _append_bytes(store.journal,_payload({'operation':'SOURCE_SNAPSHOT_INTENT','source':ref}))
                dest.parent.mkdir(exist_ok=True)
                if dest.exists():
                    if dest.read_bytes()!=data:
                        raise ValueError('SOURCE_SNAPSHOT_CHANGED')
                else:
                    _write_new(dest,data)
                verified.append(ref)
                _append_bytes(store.journal,_payload({'operation':'SOURCE_SNAPSHOT_COMPLETE','source':ref,
                                                       'snapshot':_ref(store.root,dest,'SOURCE')}))
            except (OSError,ValueError) as exc:
                reason=f'{ref.uri}:{exc}'
                reasons.append(reason)
                _append_bytes(store.journal,_payload({'operation':'SOURCE_FAILURE','reason':reason}))
    return IntegrityReport('INTEGRITY_INVALID' if reasons else 'INTEGRITY_VALID',tuple(reasons),tuple(verified))
