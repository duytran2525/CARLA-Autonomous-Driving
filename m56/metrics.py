"""Pure offline event/metric kernels; derived predicates are not native authority."""
from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from dataclasses import replace
from math import sqrt, isfinite

from .model import (FrameRecord, EventRecord, Number, SourceRef, CapabilityProof,
                    CompiledFixture, BlockedFixture, FrozenMetricPair, MetricValue, DirectedRoute,
                    PolicyBundle, ReviewRecord, EpisodeEvidence, EpisodeVerdict, ABVerdict,
                    SpawnState, PhysicalState, WitnessState,
                    decode_record, encode_record)
from .geometry import world_vertices, project_route
from .catalog import _digest, _review_binds


_F_CONTRACTS={
    'F01':(('a_peak_025','g_front_min_m'),('m/s^2','m'),('peak_decel_025','min_front_gap'),(('TRIGGER','F01_N_CLEAR'),)*2),
    'F02':(('v_mean_E','g_rear_min_m'),('m/s','m'),('mean_speed','min_rear_gap'),(('TRIGGER','F02_END'),)*2),
    'F03':(('d_reverse_m','g_front_min_m'),('m','m'),('reverse_distance','min_front_gap'),(('TRIGGER','NPC_STOP_CONFIRMED'),)*2),
    'F04':(('passage_time_s','e_lat_peak_m'),('s','m'),('elapsed','map_lateral_peak'),(('TRIGGER','F04_END'),)*2),
    'F05':(('d_pre_move_m','t_queue_exit_s'),('m','s'),('forward_distance','elapsed'),(('TRIGGER','N_MOVE'),('N_MOVE','F05_END'))),
    'F06-ALT1':(('d_reserve_reverse_m','g_front_min_m'),('m','m'),('reverse_distance','min_front_gap'),(('TRIGGER','NPC_REVERSE_TARGET_STOP_CONFIRMED'),)*2),
}


def f_pair(mechanism_id: str, policies: PolicyBundle) -> FrozenMetricPair | BlockedFixture:
    """Return only the reviewed fixed proposal; never certify mechanism or readiness."""
    contract=_F_CONTRACTS.get(mechanism_id)
    packet=policies.descriptor_specs.get(mechanism_id)
    if contract is None or not isinstance(packet,Mapping) or set(packet)!={'reference','review'}:
        return BlockedFixture(('F_PAIR_NOT_APPROVED',))
    reference=packet['reference']
    if not isinstance(reference,str) or not reference or not policies.receipt_refs:
        return BlockedFixture(('F_PAIR_REFERENCE_OR_APPROVAL_MISSING',))
    names,units,estimators,window=contract
    binding={'mechanism':mechanism_id,'names':names,'units':units,'estimators':estimators,'window':window,
             'reference':reference,'policy_hash':policies.hash,'receipt_refs':policies.receipt_refs}
    digest=_digest(binding)
    review=decode_record('ReviewRecord',encode_record(packet['review']))
    if not isinstance(review,ReviewRecord) or not _review_binds(review,digest,('F_PAIR:'+mechanism_id,)):
        return BlockedFixture(('F_PAIR_REVIEW_MISMATCH',))
    return FrozenMetricPair(names,units,estimators,window,reference,digest,'APPROVED_PROPOSAL_NOT_READY')


def evaluate_episode(records: EpisodeEvidence, fixture: CompiledFixture) -> EpisodeVerdict:
    """Recompute orthogonal verdicts from bound sources; cached verdicts are not authority."""
    from .evidence import check_integrity, _collision_evidence, _bound_source, _read_trajectory, _decode_source_record
    integrity=check_integrity(records,fixture)
    collision,_=_collision_evidence(records)
    reasons=list(integrity.reasons)
    if collision:
        reasons.append('COLLISION_OBSERVED')
    negative_gap=False
    trajectory=_bound_source(records,'trajectory_ref')
    source_fixture=_decode_source_record('CompiledFixture',records.fixture)
    # Positive physical observations require authentic source objects even when delivery is uncertain.
    source_bound=(trajectory is not None and isinstance(source_fixture,CompiledFixture)
                  and _digest(source_fixture)==_digest(fixture)
                  and _digest(_read_trajectory(trajectory))==_digest(records.raw))
    if source_bound:
        route=fixture.routes.get('EGO')
        order=fixture.domain.topology.get('gap_order')
        if route is not None and order in ('front','rear'):
            estimator='min_rear_gap' if order=='rear' else 'min_front_gap'
            for frame in records.raw:
                gap=_route_observation(frame,{'directed_route':route},'route:'+_digest(route),estimator)
                if gap is not None and gap<0:
                    negative_gap=True;reasons.append('NEGATIVE_DIRECTED_GAP');break
    metrics={name:MetricValue(name,None,unit,window,fixture.pair.reference,estimator,(),None,'UNKNOWN')
             for name,unit,window,estimator in zip(fixture.pair.names,fixture.pair.units,fixture.pair.window,fixture.pair.estimators)}
    witness={'WITNESS_VALID':WitnessState.VALID,'WITNESS_INVALID':WitnessState.INVALID,
             'WITNESS_UNCERTAIN':WitnessState.UNCERTAIN}.get(integrity.status,WitnessState.UNKNOWN)
    state=PhysicalState.UNKNOWN;events=()
    if source_bound:
        observed=_authenticated_events(records,fixture)
        if observed is not None:
            events=observed
            category=fixture.domain.topology.get('category')
            audit=_f_action if category=='F' else _io_action if category in ('I','O') else _crossing_action
            state,action_reasons=audit(records.raw,fixture,events)
            state,action_reasons=_finish_action(records.raw,fixture,events,state,action_reasons)
            reasons.extend(action_reasons)
    if collision or negative_gap:
        state=PhysicalState.FAILED
    from .evidence import _initialization_integrity
    init_invalid,init_unknown=_initialization_integrity(records,fixture)
    spawn=SpawnState.CONFIRMED if source_bound and not init_invalid and not init_unknown else SpawnState.UNKNOWN
    if state==PhysicalState.COMPLETE and witness!=WitnessState.VALID:
        state=PhysicalState.UNKNOWN
    if state==PhysicalState.COMPLETE and spawn==SpawnState.CONFIRMED and witness==WitnessState.VALID:
        values=_source_metrics(records,fixture)
        if values is not None:
            metrics={m.name:m for m in values}
    return EpisodeVerdict(spawn,state,witness,tuple(dict.fromkeys(reasons)),events,metrics)


def _source_metrics(records: EpisodeEvidence,fixture: CompiledFixture) -> tuple[MetricValue,...] | None:
    """Derive source-correlated numeric inputs for W05, not episode eligibility.

    Action, ownership, collision/contact, ground, spawn and review gates remain
    independent. Public episode values stay None until those gates are resolved.
    """
    from .evidence import _bound_source,_read_trajectory,_decode_source_record,_metric_context_integrity
    source=_decode_source_record('CompiledFixture',records.fixture)
    trajectory=_bound_source(records,'trajectory_ref')
    if (not isinstance(source,CompiledFixture) or _digest(source)!=_digest(fixture) or trajectory is None
            or _digest(_read_trajectory(trajectory))!=_digest(records.raw)):
        return None
    invalid,uncertain=_metric_context_integrity(records,fixture)
    if invalid or uncertain:
        return None
    events=_authenticated_events(records,fixture)
    return measure(records.raw,fixture.pair,events) if events is not None else None


def _authenticated_events(records,fixture):
    """Source-correlated observations and interval receipts, not cached event claims."""
    from .evidence import _frame_integrity,_admitted_source,_verified_review
    invalid,uncertain=_frame_integrity(records,fixture)
    if invalid or uncertain or not records.raw or records.end_simtime!=records.raw[-1].simtime:
        return None
    for previous,frame in zip(records.raw,records.raw[1:]):
        proof=_continuous_proof(previous,frame,_digest(fixture))
        if proof is None:
            return None
        packet={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
        if (any(not _admitted_source(records,r) for r in proof.raw_refs)
                or not _verified_review(records,proof.review,_digest(packet),'CAPABILITY:CONTINUOUS_GEOMETRY')):
            return None
    events=detect_events(records.raw,fixture)
    return None if any(e.name=='WITNESS_UNKNOWN' for e in events) else events


def _action_response(frames,fixture):
    hashes={c.response_hash for f in frames for a in f.actors if a.role=='EGO' for c in a.commands}
    responses=tuple(r for r in fixture.responses if r.actor_role=='EGO' and r.hash in hashes)
    if len(responses)!=1 or hashes!={responses[0].hash} or responses[0].action_id not in ('A','B'):
        return None
    return responses[0]


def _in_action_region(actor,region,error):
    """Three-valued full-body membership in a frozen, separately qualified box."""
    vertices=world_vertices(actor.body,actor.pose)
    lower=tuple(min(p[i] for p in region) for i in range(3))
    upper=tuple(max(p[i] for p in region) for i in range(3))
    if all(Fraction(lower[i])+error<=Fraction(p[i])<=Fraction(upper[i])-error for p in vertices for i in range(3)):
        return True
    if any(Fraction(p[i])<Fraction(lower[i])-error or Fraction(p[i])>Fraction(upper[i])+error for p in vertices for i in range(3)):
        return False
    return None


def _observed_stop(frames):
    start=None
    for frame in frames:
        actor=next(a for a in frame.actors if a.role=='EGO');speed=_speed(actor.velocity)
        if speed is None or speed>Fraction(1,10):
            start=None;continue
        if start is None:
            start=frame.simtime
        if frame.simtime-start>=Fraction(1,2):
            return frame
    return None


def _io_action(frames,fixture,events):
    """Partial I/O action audit: X_END alone never supplies maneuver success.

    Region data must be frozen/qualified by fixture admission. Unsupported geometry
    or ambiguous body membership is UNKNOWN, not an invented lane-change failure.
    """
    from .geometry import _is_box
    category=fixture.domain.topology.get('category');response=_action_response(frames,fixture)
    if category not in ('I','O') or response is None:
        return PhysicalState.UNKNOWN,('ACTION_BINDING_MISSING',)
    regions=fixture.domain.topology.get('action_regions')
    if (not isinstance(regions,Mapping) or set(regions)!={'EGO_INITIAL','EGO_TARGET'}
            or any(not _is_box(region) for region in regions.values())):
        return PhysicalState.UNKNOWN,('ACTION_REGIONS_UNPROVEN',)
    by_name={e.name:e for e in events};trigger=by_name.get('TRIGGER');end=by_name.get('X_END')
    if trigger is None:
        return PhysicalState.INCOMPLETE,('TRIGGER_MISSING',)
    selected=[];states=[]
    for previous,frame in zip(frames,frames[1:]):
        if frame.frame<trigger.frame or (end is not None and frame.frame>end.frame):
            continue
        proof=_continuous_proof(previous,frame,_digest(fixture))
        if proof is None:
            return PhysicalState.UNKNOWN,('ACTION_REGION_WITNESS_UNKNOWN',)
        ego=next(a for a in frame.actors if a.role=='EGO')
        state={name:_in_action_region(ego,region,proof.uncertainty) for name,region in regions.items()}
        if any(v is None for v in state.values()):
            return PhysicalState.UNKNOWN,('ACTION_REGION_WITNESS_UNKNOWN',)
        selected.append(frame);states.append(state)
    if not selected:
        return PhysicalState.UNKNOWN,('ACTION_REGION_WITNESS_UNKNOWN',)
    action=response.action_id;failed=[]
    if (category,action) in (('I','A'),('O','B')) and any(not s['EGO_INITIAL'] for s in states):
        failed.append('UNPLANNED_LANE_CHANGE')
    if category=='I' and action=='A':
        stopped=_observed_stop(selected);clear=by_name.get('SOURCE_CLEAR_CONFIRMED')
        if end is not None and stopped is None:
            failed.append('STOP_REQUIRED_BEFORE_X')
        if stopped is not None:
            route=fixture.routes['EGO'];by_frame={f.frame:f for f in frames}
            for frame in selected:
                if frame.frame<=stopped.frame or _actor_stopped(frame,'EGO'):
                    continue
                previous=by_frame[frame.frame-1]
                npc=next(a for a in previous.actors if a.role=='NPC')
                proof=_continuous_proof(previous,frame,_digest(fixture))
                inside=_in_action_region(npc,regions['EGO_INITIAL'],proof.uncertainty)
                gap=_route_observation(previous,{'directed_route':route},'route:'+_digest(route),'min_front_gap')
                if clear is None or clear.frame>=frame.frame or inside is False or (gap is not None and gap+proof.uncertainty<Fraction(1,5)):
                    failed.append('RESUMED_BEFORE_NPC_MERGED_AHEAD');break
                if inside is None or gap is None or gap-proof.uncertainty<Fraction(1,5):
                    return (PhysicalState.FAILED if failed else PhysicalState.UNKNOWN),tuple(failed+['MERGE_AHEAD_WITNESS_UNKNOWN'])
    if category=='I' and action=='B':
        clear=by_name.get('SOURCE_CLEAR_CONFIRMED')
        left=next((f for f,s in zip(selected,states) if not s['EGO_INITIAL']),None)
        departure,departure_unknown=_lateral_departure(frames,fixture,selected)
        # Actual departure can precede leaving the initial lane's body envelope.
        onset=departure if departure is not None else left
        if onset is not None and (clear is None or onset.frame<=clear.frame):
            failed.append('CHANGED_BEFORE_SOURCE_CLEAR')
        wait_end=onset.simtime if onset is not None else selected[-1].simtime
        if wait_end-trigger.time>4 or (clear is not None and clear.time-trigger.time>4):
            failed.append('SOURCE_CLEAR_WAIT_EXCEEDED')
        if end is not None and not states[-1]['EGO_TARGET']:
            failed.append('MANEUVER_NOT_COMPLETE_BY_X')
        if onset is not None:
            if departure_unknown:
                return (PhysicalState.FAILED if failed else PhysicalState.UNKNOWN),tuple(failed+[departure_unknown])
            completed=next((f for f,s in zip(selected,states) if f.frame>=onset.frame and s['EGO_TARGET']),None)
            segment=tuple(f for f in frames if f.frame>=onset.frame-1
                          and f.frame<=(completed.frame if completed is not None else selected[-1].frame))
            if any(not _lane_change_path(f,fixture) for f in segment):
                return (PhysicalState.FAILED if failed else PhysicalState.UNKNOWN),tuple(failed+['LANE_CHANGE_PATH_UNPROVEN'])
    if category=='O' and action=='B':
        route=fixture.routes['EGO']
        for frame in selected:
            gap=_route_observation(frame,{'directed_route':route},'route:'+_digest(route),'min_front_gap')
            previous=next(f for f in frames if f.frame==frame.frame-1)
            error=_continuous_proof(previous,frame,_digest(fixture)).uncertainty
            if gap is None:
                return (PhysicalState.FAILED if failed else PhysicalState.UNKNOWN),tuple(failed+['FOLLOW_GAP_UNKNOWN'])
            if gap+error<Fraction(1,5):
                failed.append('FOLLOW_GAP_VIOLATION');break
            if gap-error<Fraction(1,5):
                return (PhysicalState.FAILED if failed else PhysicalState.UNKNOWN),tuple(failed+['FOLLOW_GAP_UNKNOWN'])
    if category=='O' and action=='A':
        if end is not None and (not any(s['EGO_TARGET'] for s in states) or not states[-1]['EGO_INITIAL']):
            failed.append('MANEUVER_NOT_COMPLETE_BY_X')
        unresolved=[]
        for check in (_o_outbound_action,_o_return_action):
            stage,details=check(frames,fixture,events,selected,states)
            if stage==PhysicalState.FAILED:
                failed.extend(details)
            elif stage is not None:
                unresolved.append((stage,details))
        if unresolved:
            stage=PhysicalState.FAILED if failed else (PhysicalState.UNKNOWN if any(s==PhysicalState.UNKNOWN for s,_ in unresolved)
                                                     else PhysicalState.INCOMPLETE)
            return stage,tuple(dict.fromkeys([*failed,*(r for _,reasons in unresolved for r in reasons)]))
    if failed:
        return PhysicalState.FAILED,tuple(failed)
    if end is None:
        return PhysicalState.INCOMPLETE,('X_END_MISSING',)
    return PhysicalState.UNKNOWN,('IO_FULL_ACTION_REVIEW_PENDING',)


def _lateral_departure(frames,fixture,selected):
    """First witnessed lateral motion relative to the frozen initial-map lane."""
    by_frame={f.frame:f for f in frames};binding=_digest(fixture)
    for frame in selected:
        previous=by_frame.get(frame.frame-1)
        if previous is None:
            return None,'LANE_CHANGE_ONSET_UNPROVEN'
        offsets=[]
        for sample in (previous,frame):
            context=sample.integrity.get('metric_context')
            actors=tuple(a for a in sample.actors if a.role=='EGO')
            offset=(_map_offset(actors[0].pose,context.get('map_reference'),fixture.pair.reference)
                    if isinstance(context,Mapping) and len(actors)==1 else None)
            if offset is None:
                return None,'LANE_CHANGE_ONSET_UNPROVEN'
            offsets.append(offset)
        proof=_continuous_proof(previous,frame,binding)
        if proof is None:
            return None,'LANE_CHANGE_ONSET_UNPROVEN'
        difference=abs(offsets[1]-offsets[0])
        if difference>2*proof.uncertainty:
            return frame,None
        if difference:
            return None,'LANE_CHANGE_ONSET_UNCERTAIN'
    return None,None


def _lane_change_path(frame,fixture):
    """Reviewed bounded-corridor observation; not a native path-clear getter.

    Source/authority bytes are admitted independently by the evidence consumer.
    Lateral profile/continuous fit and actual departure timing remain separate.
    """
    proof=_frame_capability(frame,fixture,'lane_change_path','LANE_CHANGE_PATH','bounded-lane-change-corridor-v1')
    if proof is None:
        return False
    limits=proof.limits;regions=fixture.domain.topology.get('action_regions')
    if (not isinstance(regions,Mapping) or set(regions)!={'EGO_INITIAL','EGO_TARGET'}
            or set(limits)!={'fixture_hash','frame','actors_hash','from_region_hash','to_region_hash','route_hash','minimum_clearance_m'}):
        return False
    clearance=limits['minimum_clearance_m']
    return (limits['from_region_hash']==_digest(regions['EGO_INITIAL'])
            and limits['to_region_hash']==_digest(regions['EGO_TARGET'])
            and limits['route_hash']==_digest(fixture.routes['EGO'])
            and not isinstance(clearance,bool) and isinstance(clearance,(int,Fraction))
            and clearance-proof.uncertainty>=Fraction(1,5))


def _o_outbound_action(frames,fixture,events,selected,states):
    """Independent outbound onset/path gates; safe return does not prove departure."""
    trigger=next(e for e in events if e.name=='TRIGGER')
    onset,unknown=_lateral_departure(frames,fixture,selected)
    if unknown:
        return PhysicalState.UNKNOWN,('OUTBOUND_ONSET_UNPROVEN',)
    if onset is None:
        return PhysicalState.INCOMPLETE,('OUTBOUND_ONSET_MISSING',)
    failed=[]
    if onset.frame<=trigger.frame:
        failed.append('OUTBOUND_BEFORE_DECISION')
    target=next((f for f,s in zip(selected,states) if f.frame>=onset.frame and s['EGO_TARGET']),None)
    segment=tuple(f for f in frames if onset.frame-1<=f.frame<=(target.frame if target is not None else selected[-1].frame))
    if any(not _lane_change_path(f,fixture) for f in segment):
        return (PhysicalState.FAILED if failed else PhysicalState.UNKNOWN),tuple(failed+['OUTBOUND_PATH_UNPROVEN'])
    if failed:
        return PhysicalState.FAILED,tuple(failed)
    return None,()


def _o_return_action(frames,fixture,events,selected,states):
    """Frozen return marker plus actual lateral start, gap hold and independent path."""
    section=fixture.sections.get('O_RETURN_START')
    if section is None:
        return PhysicalState.UNKNOWN,('RETURN_MARKER_UNPROVEN',)
    marker=next((e for e in events if e.name=='RETURN_MARKER'),None)
    by_frame={f.frame:f for f in frames};binding=_digest(fixture);failed=[];unknown=[]
    reached_target=False;previous_offset=None
    for frame,state in zip(selected,states):
        context=frame.integrity.get('metric_context')
        ego=next(a for a in frame.actors if a.role=='EGO')
        offset=_map_offset(ego.pose,context.get('map_reference') if isinstance(context,Mapping) else None,fixture.pair.reference)
        if offset is None:
            unknown.append('RETURN_LATERAL_REFERENCE_UNPROVEN');continue
        proof=_continuous_proof(by_frame[frame.frame-1],frame,binding)
        if reached_target and previous_offset is not None and offset<previous_offset:
            if previous_offset-offset<=2*proof.uncertainty:
                unknown.append('RETURN_LATERAL_START_UNCERTAIN')
            else:
                front=_section_margin(world_vertices(ego.body,ego.pose),section)
                if (marker is not None and frame.frame<=marker.frame) or (front is not None and max(front)+proof.uncertainty<0):
                    failed.append('RETURN_STARTED_BEFORE_FIXED_MARKER')
                break
        reached_target=reached_target or state['EGO_TARGET']
        previous_offset=offset
    if marker is None:
        return (PhysicalState.FAILED if failed else PhysicalState.INCOMPLETE),tuple(dict.fromkeys(failed+unknown+['RETURN_MARKER_MISSING']))
    completed=next((f for f,s in zip(selected,states) if f.frame>marker.frame and s['EGO_INITIAL']),None)
    returning=tuple(f for f in frames if marker.frame<=f.frame<=
                    (completed.frame if completed is not None else selected[-1].frame))
    if any(not _return_path(f,binding) for f in returning):
        unknown.append('RETURN_PATH_UNPROVEN')
    hold=tuple(f for f in frames if marker.time-Fraction(1,4)<=f.simtime<=marker.time)
    if len(hold)!=6 or hold[0].simtime!=marker.time-Fraction(1,4) or hold[-1].frame!=marker.frame:
        unknown.append('RETURN_CLEARANCE_HISTORY_MISSING')
    else:
        route=fixture.routes['EGO']
        for frame in hold:
            previous=by_frame.get(frame.frame-1)
            proof=_continuous_proof(previous,frame,binding) if previous is not None else None
            gap=_route_observation(frame,{'directed_route':route},'route:'+_digest(route),'min_rear_gap')
            if proof is None or gap is None:
                unknown.append('RETURN_CLEARANCE_WITNESS_UNKNOWN');continue
            if gap+proof.uncertainty<Fraction(1,2):
                failed.append('RETURN_MARKER_CLEARANCE_NOT_MET')
            elif gap-proof.uncertainty<Fraction(1,2):
                unknown.append('RETURN_CLEARANCE_WITNESS_UNKNOWN')
            if not _return_path(frame,binding):
                unknown.append('RETURN_PATH_UNPROVEN')
    if failed:
        return PhysicalState.FAILED,tuple(dict.fromkeys(failed+unknown))
    if unknown:
        return PhysicalState.UNKNOWN,tuple(dict.fromkeys(unknown))
    return None,()


def _f_queue_action(frames,fixture,events,response):
    by_name={e.name:e for e in events};trigger=by_name.get('TRIGGER');move=by_name.get('N_MOVE')
    if trigger is None:
        return PhysicalState.INCOMPLETE,('TRIGGER_MISSING',)
    selected=tuple(f for f in frames if f.frame>=trigger.frame)
    route=fixture.routes['EGO'];records=[]
    for f in selected:
        actors={a.role:a for a in f.actors};stations={}
        for role in ('EGO','NPC'):
            body=world_vertices(actors[role].body,actors[role].pose)
            projected=tuple(_metric_station(p,route) for p in body)
            if any(p is None for p in projected):
                return PhysicalState.UNKNOWN,('QUEUE_PROJECTION_UNKNOWN',)
            stations[role]=projected
        records.append((f,actors,stations))
    initial_e=max(records[0][2]['EGO']);initial_n=records[0][2]['NPC']
    failed=[];unknown=[];reach=None;release=None
    if response.action_id=='A':
        release=next((f for f,_,s in records if move is not None and f.frame>=move.frame
                      and all(b-a>=2 for a,b in zip(initial_n,s['NPC']))),None)
    elif move is not None:
        # The independent continuous contact/gap channel remains required as well.
        release=move
    for i,(f,actors,stations) in enumerate(records):
        if not i:
            continue
        before=records[i-1][2];duration=f.simtime-records[i-1][0].simtime
        if duration!=Fraction(1,20):
            return PhysicalState.UNKNOWN,('ACTION_WINDOW_UNKNOWN',)
        step=max(stations['EGO'])-max(before['EGO'])
        if step<0:
            failed.append('UNPLANNED_REVERSE')
        if any(b<a for a,b in zip(before['NPC'],stations['NPC'])):
            failed.append('NPC_UNPLANNED_REVERSE')
        # Commands applied before this observed release cannot resume in the same frame.
        held=release is None or f.frame<=release.frame
        if response.action_id=='A' and held and (abs(step)/duration>Fraction(1,10) or not _actor_stopped(f,'EGO')):
            failed.append('QUEUE_RELEASE_BEFORE_NPC_ADVANCE')
        if response.action_id=='B' and held:
            progress=max(stations['EGO'])-initial_e
            if progress>1:
                failed.append('CREEP_RESERVATION_EXCEEDED')
            if progress==1 and reach is None:
                reach=f
    if response.action_id=='B' and release is not None:
        hold=tuple(f for f,_,s in records if reach is not None and reach.frame<=f.frame<=release.frame)
        if reach is None or _observed_stop(hold) is None:
            failed.append('CREEP_STOP_NOT_CONFIRMED')
    missing=[name+'_MISSING' for name in ('N_MOVE','F05_END','DESTINATION_CONFIRMED') if name not in by_name]
    if release is None:
        missing.append('QUEUE_RELEASE_NOT_OBSERVED')
    reasons=tuple(dict.fromkeys(failed+unknown+missing))
    if failed:
        return PhysicalState.FAILED,reasons
    if missing:
        return PhysicalState.INCOMPLETE,reasons
    return PhysicalState.UNKNOWN,('F_FULL_ACTION_REVIEW_PENDING',)


def _f_wait_action(frames,fixture,events,response):
    mechanism=fixture.domain.topology['mechanism'];by_name={e.name:e for e in events}
    trigger=by_name.get('TRIGGER');end_name={'F01':'F01_N_CLEAR','F02':'F02_END','F04':'F04_END'}[mechanism];end=by_name.get(end_name)
    if trigger is None:
        return PhysicalState.INCOMPLETE,('TRIGGER_MISSING',)
    selected=tuple(f for f in frames if trigger.frame<=f.frame and (end is None or f.frame<=end.frame))
    failed=[];unknown=[];route=fixture.routes['EGO']
    stations=tuple(_metric_station((a.pose.x,a.pose.y,a.pose.z),route)
                   for f in selected for a in f.actors if a.role=='EGO')
    if any(s is None for s in stations):
        unknown.append('ACTION_PROJECTION_UNKNOWN')
    # Missing route projection cannot erase independent stop/door/lane findings.
    # Compare adjacent observed projections only; never bridge an unknown sample.
    if any(a is not None and b is not None and b<a for a,b in zip(stations,stations[1:])):
        failed.append('UNPLANNED_REVERSE')
    release=None
    if mechanism=='F01':
        release=by_name.get('N_MOVE')
    elif mechanism=='F04':
        for f in selected:
            state=_door_state(f,fixture)
            if state is None:
                unknown.append('DOOR_REMOVAL_WITNESS_UNKNOWN');continue
            if state==('CLOSED','OUTSIDE'):
                release=f;break
    if mechanism=='F02':
        if _observed_stop(selected) is not None:
            failed.append('UNPLANNED_STOP')
    elif response.action_id=='A':
        hold=tuple(f for f in selected if release is None or f.frame<=release.frame)
        stopped=_observed_stop(hold)
        if stopped is None:
            if release is not None or end is not None:
                failed.append('STOP_REQUIRED_BEFORE_RELEASE')
        else:
            for f in hold:
                if f.frame<=stopped.frame:
                    continue
                if not _actor_stopped(f,'EGO'):
                    failed.append('RESUMED_BEFORE_NPC_MOVE' if mechanism=='F01' else 'RESUMED_BEFORE_DOOR_REMOVAL')
        if mechanism=='F04' and end is not None and (release is None or end.frame<=release.frame):
            failed.append('PASSED_BEFORE_DOOR_REMOVAL')
    elif mechanism=='F04':
        lane_failed,lane_unknown=_spatial_lane_observations(frames,fixture,tuple(f for f in frames if f.frame>=trigger.frame))
        failed.extend(lane_failed);unknown.extend(lane_unknown)
        segments=response.profile.get('segments',())
        if len(segments)==2 and segments[0].get('end_offset_m')!=0 and 'F04_OFFSET_CONFIRMED' not in by_name:
            # A certified plateau still on the original centre is observed
            # wrong action, not a requested offset credited as physical motion.
            # Uncertain or partial observations cannot establish this failure.
            plateau=[];unproven=False;out_end=segments[0]['start_arc_m']+segments[0]['length_m']
            for i,frame in enumerate(selected):
                actor=next((a for a in frame.actors if a.role=='EGO'),None)
                station=_metric_station((actor.pose.x,actor.pose.y,actor.pose.z),response.route) if actor else None
                if station is None:
                    unproven=True;continue
                if not out_end<=station<segments[1]['start_arc_m']:
                    continue
                proof=_continuous_proof(selected[i-1],frame,_digest(fixture)) if i else None
                if proof is None or proof.uncertainty!=0 or actor.route_valid is not True:
                    unproven=True;continue
                plateau.append((frame,actor.pose.y==response.route.transforms[0].y))
            if (not unproven and plateau and all(on_centre for _,on_centre in plateau)
                    and plateau[-1][0].simtime-plateau[0][0].simtime>=Fraction(1,4)):
                failed.append('SPATIAL_PASS_NOT_REALIZED')
            else:
                unknown.append('SPATIAL_OFFSET_UNPROVEN')
        if len(segments)==2 and 'F04_HOME_CONFIRMED' not in by_name:
            unknown.append('SPATIAL_RETURN_UNPROVEN')
        # Exact observed horizontal synthetic tracking can establish this
        # component. Continuous body enclosure/contact and actual command/path
        # replay are independently mandatory at public witness admission.
        if not _f04_profile_observations(frames,fixture,response,trigger):
            unknown.append('SPATIAL_PASS_FIT_REVIEW_PENDING')
    missing=[name+'_MISSING' for name in (end_name,'DESTINATION_CONFIRMED') if name not in by_name]
    if mechanism!='F02' and response.action_id=='A' and release is None:
        missing.append('ACTUAL_RELEASE_MISSING')
    reasons=tuple(dict.fromkeys(failed+unknown+missing))
    if failed:
        return PhysicalState.FAILED,reasons
    if unknown:
        return PhysicalState.UNKNOWN,reasons
    if missing:
        return PhysicalState.INCOMPLETE,reasons
    return PhysicalState.UNKNOWN,('F_FULL_ACTION_REVIEW_PENDING',)


def _f04_profile_observations(frames,fixture,response,trigger):
    """Conservative supported observation of the frozen within-lane profile.

    Only flat, stable-body, zero-uncertainty exact observed coordinates are
    supported here. No new tracking tolerance, native calibration, source-trust
    flag or requested-offset-as-motion credit is introduced. General noisy or
    banked observations stay unproven until a separately qualified recipe.
    """
    from .response import _lateral_contract,desired_offset
    try:
        _lateral_contract(response,fixture)
        if len(response.profile['segments'])!=2:
            return False
        region=fixture.domain.topology['action_regions']['EGO_INITIAL']
        binding=_digest(fixture);identity=None;found=False
        for i,frame in enumerate(frames):
            if frame.frame<trigger.frame:
                continue
            actors=tuple(a for a in frame.actors if a.role=='EGO')
            proof=_continuous_proof(frames[i-1],frame,binding) if i else None
            if len(actors)!=1 or proof is None or proof.uncertainty!=0:
                return False
            actor=actors[0];key=(actor.id,_digest(actor.body));found=True
            if identity is not None and identity!=key:
                return False
            identity=key
            station=_metric_station((actor.pose.x,actor.pose.y,actor.pose.z),response.route)
            if (actor.route_valid is not True or station is None
                    or (actor.pose.pitch,actor.pose.yaw,actor.pose.roll)!=(0.,0.,0.)
                    or actor.pose.y!=float(Fraction(response.route.transforms[0].y)+desired_offset(station,response))
                    or _in_action_region(actor,region,Fraction(3,20)) is not True):
                return False
        return found
    except (ValueError,TypeError,KeyError,AttributeError):
        return False


def _spatial_lane_observations(frames,fixture,selected):
    """Independent observed wholebody membership, never inferred from door corridor.

    A frozen initial-lane region is required; a passing metric or set_offset call
    cannot supply it. Continuous fit and edge buffers remain separate gates.
    """
    from .geometry import _is_box
    regions=fixture.domain.topology.get('action_regions')
    region=regions.get('EGO_INITIAL') if isinstance(regions,Mapping) else None
    if not _is_box(region):
        return (),('SPATIAL_PASS_REGION_UNPROVEN',)
    by_frame={f.frame:f for f in frames};binding=_digest(fixture);failed=[];unknown=[]
    for frame in selected:
        previous=by_frame.get(frame.frame-1)
        proof=_continuous_proof(previous,frame,binding) if previous is not None else None
        actors=tuple(a for a in frame.actors if a.role=='EGO')
        if proof is None or len(actors)!=1 or actors[0].route_valid is not True:
            unknown.append('SPATIAL_PASS_LANE_UNCERTAIN');continue
        membership=_in_action_region(actors[0],region,proof.uncertainty)
        if membership is False:
            failed.append('SPATIAL_PASS_LEFT_INITIAL_LANE')
        elif membership is None:
            unknown.append('SPATIAL_PASS_LANE_UNCERTAIN')
    return tuple(dict.fromkeys(failed)),tuple(dict.fromkeys(unknown))


def _f_action(frames,fixture,events):
    """Combine maneuver-window checks with full post-metric forward observation."""
    state,reasons=_f_action_window(frames,fixture,events)
    mechanism=fixture.domain.topology.get('mechanism');contract=_F_CONTRACTS.get(mechanism)
    if contract is None or fixture.pair.names!=contract[0] or _action_response(frames,fixture) is None:
        return state,reasons
    end=next((e for e in events if e.name==contract[3][-1][1]),None)
    if end is None:
        return state,reasons
    failures,unknown=_forward_tail(frames,fixture,end)
    if failures:
        state=PhysicalState.FAILED
    elif unknown and state!=PhysicalState.FAILED:
        state=PhysicalState.UNKNOWN
    return state,tuple(dict.fromkeys((*reasons,*failures,*unknown)))


def _forward_tail(frames,fixture,end):
    tail=tuple(f for f in frames if f.frame>=end.frame);failed=[];unknown=[]
    if not tail or tail[0].frame!=end.frame:
        return (),('POST_END_PROJECTION_UNKNOWN',)
    for role in ('EGO','NPC'):
        route=fixture.routes.get(role);previous=None
        for frame in tail:
            actors=tuple(a for a in frame.actors if a.role==role)
            station=(_metric_station((actors[0].pose.x,actors[0].pose.y,actors[0].pose.z),route)
                     if route is not None and len(actors)==1 and actors[0].route_valid is True else None)
            if station is None:
                unknown.append('POST_END_PROJECTION_UNKNOWN')
            elif previous is not None and station<previous:
                failed.append('POST_END_UNPLANNED_REVERSE')
            previous=station  # Never compare across a missing observation.
    return tuple(dict.fromkeys(failed)),tuple(dict.fromkeys(unknown))


def _reverse_throttle_cap(fixture):
    """Consumer throttle limit while reversing: the frozen law's cap (v1 1/4 unless the EGO stop proof is a known law)."""
    from .response import REVERSE_LAWS
    proof=next((p for p in fixture.proofs if p.kind=='REVERSE_STOP_BOUND' and p.limits.get('actor_role')=='EGO'),None)
    law=REVERSE_LAWS.get(proof.method) if proof is not None else None
    return law['throttle_cap'] if law is not None else Fraction(1,4)


def _f_action_window(frames,fixture,events):
    """Observed reverse/hold limits; a frozen metric end is not forward completion."""
    mechanism=fixture.domain.topology.get('mechanism');response=_action_response(frames,fixture)
    if mechanism not in _F_CONTRACTS:
        return PhysicalState.UNKNOWN,('F_ACTION_RECIPE_PENDING',)
    if response is None or fixture.pair.names!=_F_CONTRACTS[mechanism][0]:
        return PhysicalState.UNKNOWN,('ACTION_BINDING_MISSING',)
    if mechanism=='F05':
        return _f_queue_action(frames,fixture,events,response)
    if mechanism in ('F01','F02','F04'):
        return _f_wait_action(frames,fixture,events,response)
    by_name={e.name:e for e in events};trigger=by_name.get('TRIGGER')
    end_name='NPC_STOP_CONFIRMED' if mechanism=='F03' else 'NPC_REVERSE_TARGET_STOP_CONFIRMED'
    end=by_name.get(end_name)
    if trigger is None:
        return PhysicalState.INCOMPLETE,('TRIGGER_MISSING',)
    selected=tuple(f for f in frames if trigger.frame<=f.frame and (end is None or f.frame<=end.frame))
    if not selected:
        return PhysicalState.UNKNOWN,('ACTION_WINDOW_UNKNOWN',)
    route=fixture.routes['EGO'];actors=tuple(next(a for a in f.actors if a.role=='EGO') for f in selected)
    stations=tuple(_metric_station((a.pose.x,a.pose.y,a.pose.z),route) for a in actors)
    if any(s is None for s in stations):
        return PhysicalState.UNKNOWN,('ACTION_PROJECTION_UNKNOWN',)
    speeds=tuple(_speed(a.velocity) for a in actors)
    if any(v is None for v in speeds):
        return PhysicalState.UNKNOWN,('ACTION_SPEED_UNKNOWN',)
    failed=[];unknown=[];reverse=Fraction(0);cap=Fraction(2 if mechanism=='F03' else 1)
    from .response import _f32
    throttle_cap=_f32(float(_reverse_throttle_cap(fixture)))  # readback is float32 (native 2026-10-22)
    if response.action_id=='B' and mechanism=='F06-ALT1':
        from .response import _reverse_reservation_ready
        try:
            if not _reverse_reservation_ready(frames,fixture,trigger):
                failed.append('RESERVATION_STOP_NOT_CONFIRMED')
        except (ValueError,TypeError,KeyError,AttributeError,StopIteration):
            unknown.append('RESERVATION_HISTORY_UNPROVEN')
    if response.action_id=='A' and any(v>Fraction(1,10) for v in speeds):
        failed.append('HOLD_ACTION_MOVED')
    for i,(a,b) in enumerate(zip(stations,stations[1:]),1):
        duration=selected[i].simtime-selected[i-1].simtime
        if duration!=Fraction(1,20):
            return PhysicalState.UNKNOWN,('ACTION_WINDOW_UNKNOWN',)
        step=b-a;reverse+=max(Fraction(0),-step)
        if response.action_id=='A' and abs(step)/duration>Fraction(1,10):
            failed.append('HOLD_ACTION_MOVED')
        if response.action_id=='B':
            if step/duration>Fraction(1,10):
                failed.append('FORWARD_RESCUE_BEFORE_RELEASE')
            if step<0:
                control=actors[i].readback
                if control is None:
                    unknown.append('REVERSE_CONTROL_UNKNOWN')
                elif (not control.reverse or not control.manual_gear_shift or control.gear!=-1 or control.steer!=0
                      or control.throttle>throttle_cap or control.brake>_f32(.30)):
                    failed.append('REVERSE_CONTROL_MISMATCH')
    if response.action_id=='B':
        if reverse>cap:
            failed.append('REVERSE_RESERVATION_EXCEEDED')
        if end is not None and ((mechanism=='F06-ALT1' and reverse<cap) or reverse==0):
            failed.append('REVERSE_RESERVATION_NOT_REACHED')
        if end is not None:
            # A preparation stop does not satisfy the stop after actual retreat.
            last_retreat=max((i for i,(a,b) in enumerate(zip(stations,stations[1:]),1) if b<a),default=None)
            if last_retreat is None or _observed_stop(selected[last_retreat:]) is None:
                failed.append('RESERVATION_STOP_NOT_CONFIRMED')
    missing=[]
    if end is None:
        missing.append(end_name+'_MISSING')
    if 'DESTINATION_CONFIRMED' not in by_name:
        missing.append('DESTINATION_CONFIRMED_MISSING')
    reasons=tuple(dict.fromkeys(failed+unknown+missing))
    if failed:
        return PhysicalState.FAILED,reasons
    if unknown:
        return PhysicalState.UNKNOWN,reasons
    if missing:
        return PhysicalState.INCOMPLETE,reasons
    return PhysicalState.UNKNOWN,('F_FULL_ACTION_REVIEW_PENDING',)


def _finish_action(frames,fixture,events,state,reasons):
    """Complete the forward F observation component, never witness admission.

    Public completion additionally requires independent initialization, continuous
    motion/contact/ground, command replay and all source/review gates. Unsupported
    lateral/reverse recipes keep their explicit unknown reasons.
    """
    category=fixture.domain.topology.get('category');mechanism=fixture.domain.topology.get('mechanism')
    if state!=PhysicalState.UNKNOWN:
        return state,reasons
    by_name={e.name:e for e in events};destination=by_name.get('DESTINATION_CONFIRMED')
    response=_action_response(frames,fixture)
    if category in ('I','O') and reasons==('IO_FULL_ACTION_REVIEW_PENDING',) and response is not None:
        end=by_name.get('X_END')
        required=('TARGET_LANE_CONFIRMED',) if (category,response.action_id)==('I','B') else (
            ('TARGET_LANE_CONFIRMED','RETURN_LANE_CONFIRMED') if (category,response.action_id)==('O','A') else ())
        if end is None or any(name not in by_name for name in required):
            return PhysicalState.INCOMPLETE,('MANEUVER_HOLD_MISSING',)
        if any(by_name[name].frame>=end.frame for name in required):
            return PhysicalState.FAILED,('MANEUVER_NOT_COMPLETE_BY_X',)
        # After X the declared action still owns its lane. Inside-sample success
        # remains subject to the separate continuous envelope/edge/profile gates.
        regions=fixture.domain.topology['action_regions']
        region=regions['EGO_TARGET' if (category,response.action_id)==('I','B') else 'EGO_INITIAL']
        previous=None
        for f in frames:
            if f.frame>end.frame:
                proof=_continuous_proof(previous,f,_digest(fixture)) if previous is not None else None
                actor=next(a for a in f.actors if a.role=='EGO')
                membership=_in_action_region(actor,region,proof.uncertainty) if proof is not None else None
                if membership is False:
                    return PhysicalState.FAILED,('POST_END_UNPLANNED_LANE_CHANGE',)
                if membership is None:
                    return PhysicalState.UNKNOWN,('POST_END_LANE_UNPROVEN',)
            previous=f
        failures,unknown=_forward_tail(frames,fixture,end)
        if failures or unknown:
            return (PhysicalState.FAILED if failures else PhysicalState.UNKNOWN),(*failures,*unknown)
    elif mechanism in ('F01','F02','F03','F04','F05','F06-ALT1') and reasons==('F_FULL_ACTION_REVIEW_PENDING',):
        # F03/F06 reach here only after the reverse audit passed reserve/STOP/gear/control checks.
        end=by_name.get(_F_CONTRACTS[mechanism][3][-1][1])
        if mechanism=='F04' and response is not None and response.action_id=='B':
            names=('F04_OFFSET_CONFIRMED','F04_END','F04_RETURN_MARKER','F04_RETURN_REFERENCE_MARKER','F04_HOME_CONFIRMED')
            if any(name not in by_name for name in names):
                return PhysicalState.INCOMPLETE,('SPATIAL_MANEUVER_MISSING',)
            if any(by_name[a].frame>=by_name[b].frame for a,b in zip(names,names[1:])):
                return PhysicalState.FAILED,('SPATIAL_MANEUVERS_OUT_OF_ORDER',)
            if destination is not None and destination.frame<=by_name['F04_HOME_CONFIRMED'].frame:
                return PhysicalState.INCOMPLETE,('SPATIAL_RETURN_BEFORE_DESTINATION_UNPROVEN',)
    else:
        return state,reasons
    if destination is None or end is None:
        return PhysicalState.INCOMPLETE,('DESTINATION_CONFIRMED_MISSING',)
    if destination.frame<=end.frame:
        return PhysicalState.UNKNOWN,('FORWARD_DESTINATION_ORDER_UNPROVEN',)
    selected=tuple(f for f in frames if end.frame<=f.frame<=destination.frame)
    stations=[]
    for f in selected:
        actors=tuple(a for a in f.actors if a.role=='EGO')
        if len(actors)!=1 or actors[0].route_valid is not True:
            return PhysicalState.UNKNOWN,('FORWARD_COMPLETION_UNPROVEN',)
        a=actors[0];station=_metric_station((a.pose.x,a.pose.y,a.pose.z),fixture.routes['EGO'])
        if station is None:
            return PhysicalState.UNKNOWN,('FORWARD_COMPLETION_UNPROVEN',)
        stations.append(station)
    if len(stations)<2 or stations[-1]<=stations[0]:
        return PhysicalState.INCOMPLETE,('FORWARD_PROGRESS_MISSING',)
    last=next(a for a in selected[-1].actors if a.role=='EGO')
    if (last.readback is None or last.readback.reverse or last.readback.manual_gear_shift or last.readback.gear<0
            or len(last.commands)!=1 or last.commands[0].target_kmh<=0):
        return PhysicalState.UNKNOWN,('FORWARD_CONTROL_UNPROVEN',)
    return PhysicalState.COMPLETE,()


def _crossing_action(frames,fixture,events):
    """C/L/M observed action gate; successful completeness remains downstream-blocked."""
    if fixture.domain.topology.get('category') not in ('C','L','M'):
        return PhysicalState.UNKNOWN,('ACTION_RECIPE_NOT_IMPLEMENTED',)
    response=_action_response(frames,fixture)
    if response is None:
        return PhysicalState.UNKNOWN,('ACTION_BINDING_MISSING',)
    action=response.action_id;by_name={e.name:e for e in events};reasons=[];failed=[]
    required=('TRIGGER','NPC_ENTRY','CLEAR_N_CONFIRMED','E_ENTRY','DESTINATION_CONFIRMED')
    for name in required:
        if name not in by_name:
            reasons.append(name+'_MISSING')
    trigger=by_name.get('TRIGGER');entry=by_name.get('E_ENTRY');clear=by_name.get('CLEAR_N_CONFIRMED')
    if trigger is None:
        return PhysicalState.INCOMPLETE,tuple(reasons)
    window=tuple(f for f in frames if trigger.frame<=f.frame and (clear is None or f.frame<=clear.frame))
    for role in ('EGO','NPC'):
        route=fixture.routes[role]
        actors=tuple(next(a for a in f.actors if a.role==role) for f in frames)
        stations=tuple(_metric_station((a.pose.x,a.pose.y,a.pose.z),route) for a in actors)
        if any(s is None for s in stations):
            return PhysicalState.UNKNOWN,('ACTION_PROJECTION_UNKNOWN',)
        if any(b<a for a,b in zip(stations,stations[1:])):
            failed.append('UNPLANNED_REVERSE' if role=='EGO' else 'NPC_UNPLANNED_REVERSE')
    if entry is not None and (clear is None or entry.frame<=clear.frame):
        failed.append('EARLY_ENTRY_BEFORE_NPC_CLEAR')
    if action=='B':
        speeds=tuple(_speed(next(a for a in f.actors if a.role=='EGO').velocity) for f in window)
        if any(v is None for v in speeds):
            return PhysicalState.UNKNOWN,('ACTION_SPEED_UNKNOWN',)
        if any(v<Fraction(1,2) for v in speeds):
            failed.append('CONTINUOUS_YIELD_SPEED_FLOOR')
    else:
        # Settle/warm-up stops before the actual trigger cannot satisfy response A.
        post_trigger=tuple(f for f in frames if f.frame>=trigger.frame)
        stopped=next((e for e in detect_events(post_trigger,fixture) if e.name=='STOP_CONFIRMED'),None)
        if stopped is None:
            reasons.append('STOP_CONFIRMED_MISSING')
        if entry is not None and (stopped is None or stopped.frame>=entry.frame):
            failed.append('STOP_REQUIRED_BEFORE_ENTRY')
        if stopped is not None:
            hold=tuple(f for f in window if f.frame>stopped.frame)
            speeds=tuple(_speed(next(a for a in f.actors if a.role=='EGO').velocity) for f in hold)
            if any(v is None for v in speeds):
                return PhysicalState.UNKNOWN,('ACTION_SPEED_UNKNOWN',)
            if any(v>Fraction(1,10) for v in speeds):
                failed.append('RESUMED_BEFORE_NPC_CLEAR')
    if failed:
        return PhysicalState.FAILED,tuple(failed+reasons)
    if reasons:
        return PhysicalState.INCOMPLETE,tuple(reasons)
    return PhysicalState.COMPLETE,()


def _ab_review_subject(a,b,pair,left,right):
    def side(e,values):
        return {'fixture':e.fixture,'manifest':e.manifest,'journal':e.journal,'sources':e.source,
                'trajectory_hash':_digest(e.raw),'end_simtime':e.end_simtime,'metrics':values}
    return {'schema':1,'scope':'REALIZED_AB_COMPARABILITY_D09','pair':pair,
            'a':side(a,left),'b':side(b,right)}


def _review_artifact_bound(episode,ref):
    from .evidence import _admitted_source,_source_bytes,_sealed_source,verify_manifest
    from pathlib import Path
    import json
    if _admitted_source(episode,ref):
        return True
    if episode.manifest is None or _source_bytes(episode.manifest) is None or _source_bytes(ref) is None:
        return False
    root=Path(episode.manifest.uri).parent
    if ref==episode.manifest:
        return verify_manifest(root).status=='INTEGRITY_VALID'
    if ref not in (*episode.journal,episode.fixture):
        return False
    try:
        entries={r['relativepath']:r for r in json.loads(_source_bytes(episode.manifest))['files']}
        return _sealed_source(ref,root,entries)
    except (KeyError,TypeError,ValueError):
        return False


def _ab_fulltrace_review(a,b,pair,left,right,review):
    """Verify the review's inputs/scope, not the truth of a person's judgment.

    Runtime authority and reviewer independence must be established separately;
    these offline contracts do not turn synthetic authority into native approval.
    """
    from .evidence import _bound_source
    review=decode_record('ReviewRecord',encode_record(review))
    if not isinstance(review,ReviewRecord):
        return False
    subject=_ab_review_subject(a,b,pair,left,right)
    if not _review_binds(review,_digest(subject),('REALIZED_AB_COMPARABILITY_D09',)):
        return False
    areas={'fulltrace','near_zero','nearstanding','identity','mechanism','comparability'}
    covered=set()
    for reason in review.reasons:
        name,sep,text=reason.partition(':')
        if sep and text.strip():
            covered.add(name.strip())
    if not areas.issubset(covered):
        return False
    for e in (a,b):
        trajectory=_bound_source(e,'trajectory_ref')
        if trajectory is None or e.manifest is None:
            return False
        required=(e.fixture,e.manifest,*e.journal,trajectory)
        if any(r not in review.refs or not _review_artifact_bound(e,r) for r in required):
            return False
    return all(any(_review_artifact_bound(e,r) for e in (a,b)) for r in (*review.refs,review.authority_ref))


def _ab_metric_audit(a,b,pair,left,right,review):
    """Numeric component only: never certifies action, sources or episode eligibility.

    Callers must derive inputs from authenticated observations and independently
    establish action/physical/witness gates. No epsilon/rounding/sign tricks.
    """
    from .catalog import delta
    metrics=(*left,*right);empty=(None,None)
    if (len(pair.names)!=2 or len(set(pair.names))!=2 or len(left)!=2 or len(right)!=2
            or any(len(v)!=2 for v in (pair.units,pair.estimators,pair.window))):
        return ABVerdict((),metrics,empty,review,'INVALID')
    for episode,values in ((a,left),(b,right)):
        frames={f.frame for f in episode.raw}
        for i,m in enumerate(values):
            if (not isinstance(m,MetricValue) or (m.name,m.unit,m.window,m.reference,m.estimator)!=
                    (pair.names[i],pair.units[i],pair.window[i],pair.reference,pair.estimators[i])
                    or m.status!='VALID' or isinstance(m.value,bool) or not isinstance(m.value,(int,Fraction))
                    or m.value<0 or isinstance(m.uncertainty,bool) or not isinstance(m.uncertainty,(int,Fraction))
                    or m.uncertainty<0 or not m.frames or any(type(f) is not int or f not in frames for f in m.frames)
                    or tuple(sorted(set(m.frames)))!=m.frames):
                return ABVerdict((),metrics,empty,review,'INVALID')
    comparisons=tuple(delta(x.value,y.value) for x,y in zip(left,right))
    if any(d is None for d in comparisons):
        status='NOT_COMPARABLE'
    elif any(d<Fraction(1,5) for d in comparisons):
        status='NUMERIC_FAILED'
    else:
        status='NUMERIC_REVIEW_ACCEPTED' if _ab_fulltrace_review(a,b,pair,left,right,review) else 'REVIEW_REQUIRED'
    return ABVerdict((),metrics,comparisons,review,status)


def compare_ab(a: EpisodeEvidence, b: EpisodeEvidence, pair: FrozenMetricPair,
               review: ReviewRecord | None) -> ABVerdict:
    """Source-bound episode gates precede exact numerical and fulltrace D09 review."""
    from .evidence import _decode_source_record
    fa=_decode_source_record('CompiledFixture',a.fixture)
    fb=_decode_source_record('CompiledFixture',b.fixture)
    if not isinstance(fa,CompiledFixture) or not isinstance(fb,CompiledFixture):
        return ABVerdict((),(),(None,None),review,'INVALID')
    actions=tuple(_action_response(e.raw,f) for e,f in ((a,fa),(b,fb)))
    proofs=(evaluate_episode(a,fa),evaluate_episode(b,fb))
    metrics=tuple(m for proof in proofs for m in proof.metrics.values())
    if _digest(fa)!=_digest(fb) or fa.pair!=pair or fb.pair!=pair:
        status='INVALID'
    elif any(proof.physical==PhysicalState.FAILED for proof in proofs):
        status='FAILED'
    elif all(r is not None for r in actions) and tuple(r.action_id for r in actions)!=('A','B'):
        status='INVALID'
    elif any(proof.witness!=WitnessState.VALID for proof in proofs):
        status='BLOCKED_WITNESS'
    elif any(r is None for r in actions):
        status='INVALID'
    elif any(proof.spawn!=SpawnState.CONFIRMED or proof.physical!=PhysicalState.COMPLETE for proof in proofs):
        status='BLOCKED_ACTION'
    else:
        values=tuple(tuple(proof.metrics[name] for name in pair.names) for proof in proofs)
        numeric=_ab_metric_audit(a,b,pair,*values,review)
        return replace(numeric,action_proofs=proofs,status='PASS' if numeric.status=='NUMERIC_REVIEW_ACCEPTED' else numeric.status)
    return ABVerdict(proofs,metrics,(None,None),review,status)


def _contiguous(frames: tuple[FrameRecord,...]) -> bool:
    if not frames:
        return False
    if any(f.dt!=Fraction(1,20) for f in frames):
        return False
    return all(b.frame==a.frame+1 and b.simtime-a.simtime==b.dt
               and (a.boot,a.world)==(b.boot,b.world)
               for a,b in zip(frames,frames[1:]))


def _predicate(frame: FrameRecord, name: str):
    predicates=frame.integrity.get('predicates')
    if not isinstance(predicates,Mapping):
        return None
    packet=predicates.get(name)
    if not isinstance(packet,Mapping) or set(packet)!={'value','frame','time','fixture_hash','witness_refs'}:
        return None
    digest=packet['fixture_hash']
    if (packet['frame']!=frame.frame or packet['time']!=frame.simtime
            or not isinstance(digest,str) or len(digest)!=64
            or any(ch not in '0123456789abcdef' for ch in digest)
            or packet['value'] is not True):
        return None
    refs=packet['witness_refs']
    if not isinstance(refs,tuple) or not refs:
        return None
    decoded=tuple(decode_record('SourceRef',encode_record(ref)) for ref in refs)
    if any(not isinstance(ref,SourceRef) or ref.frame!=frame.frame or ref.time!=frame.simtime for ref in decoded):
        return None
    return digest,decoded


def confirm_hold(frames: tuple[FrameRecord,...], predicate: str,
                 duration: Number) -> EventRecord | None:
    """Confirm at the final actual sample, never backdate or bridge missing frames.

    The predicate producer must derive body/corridor/entry facts from the frozen
    fixture and retain their witnesses. This accumulator checks continuity and
    correlation only; its output is not independent verification of those facts.
    """
    policies={'NPC_WHOLE_BODY_CLEAR':('CLEAR_N_CONFIRMED',Fraction(1,4),'NPC_ENTRY'),
              'EGO_STOP':('STOP_CONFIRMED',Fraction(1,2),None),
              'EGO_DESTINATION':('DESTINATION_CONFIRMED',Fraction(1,4),None),
              'NPC_SOURCE_CLEAR':('SOURCE_CLEAR_CONFIRMED',Fraction(1,4),'TRIGGER'),
              'EGO_RETURN_CLEAR':('RETURN_CLEAR_CONFIRMED',Fraction(1,4),'TRIGGER')}
    if predicate not in policies:
        raise ValueError('UNSUPPORTED_HOLD_PREDICATE')
    event_name,minimum,entry_name=policies[predicate]
    if isinstance(duration,bool) or not isinstance(duration,(int,Fraction)) or duration<0:
        raise ValueError('INVALID_HOLD_DURATION')
    if duration!=minimum:
        raise ValueError('HOLD_DURATION_POLICY')
    if not _contiguous(frames):
        return None
    start=None;entered=entry_name is None;binding=None;witness=[]
    for frame in frames:
        if any(e.name==entry_name and e.frame<=frame.frame and e.time<=frame.simtime and e.witness_refs
               for e in frame.events):
            entered=True
        observed=_predicate(frame,predicate)
        if observed is None or not entered:
            start=None;binding=None;witness=[]
            continue
        digest,refs=observed
        if binding is not None and binding!=digest:
            return None
        if start is None:
            start=frame.simtime;binding=digest
        witness.extend(refs)
        if frame.simtime-start>=duration:
            return EventRecord(event_name,frame.frame,frame.simtime,tuple(witness))
    return None


_REFS_CACHE = {}
_CORRIDOR_CACHE = {}


def _frame_refs(frame):
    # Pure in the immutable frame: memoized by identity (strong ref kept). ponytail: bounded clear-all cache.
    hit = _REFS_CACHE.get(id(frame))
    if hit is not None and hit[0] is frame:
        return hit[1]
    if len(_REFS_CACHE) > 8192:
        _REFS_CACHE.clear()
    result = _frame_refs_uncached(frame)
    _REFS_CACHE[id(frame)] = (frame, result)
    return result


def _frame_refs_uncached(frame):
    refs=frame.integrity.get('frame_refs',())
    if not isinstance(refs,tuple):
        return ()
    decoded=tuple(decode_record('SourceRef',encode_record(r)) for r in refs)
    if any(not isinstance(r,SourceRef) or r.frame!=frame.frame or r.time!=frame.simtime for r in decoded):
        return ()
    return decoded


_PROOF_CACHE = {}


def _continuous_proof(previous, frame, fixture_hash):
    # Pure function of two immutable frames: memoized by identity (strong refs prevent id reuse) so online
    # per-tick detection re-checks only new frame pairs. ponytail: bounded clear-all cache, LRU if memory matters.
    key = (id(previous), id(frame), fixture_hash)
    hit = _PROOF_CACHE.get(key)
    if hit is not None and hit[0] is previous and hit[1] is frame:
        return hit[2]
    if len(_PROOF_CACHE) > 4096:
        _PROOF_CACHE.clear()
    result = _continuous_proof_uncached(previous, frame, fixture_hash)
    _PROOF_CACHE[key] = (previous, frame, result)
    return result


def _continuous_proof_uncached(previous, frame, fixture_hash):
    packet=frame.integrity.get('continuous_geometry')
    if packet is None:
        return None
    proof=decode_record('CapabilityProof',encode_record(packet))
    if (not isinstance(proof,CapabilityProof) or proof.kind!='CONTINUOUS_GEOMETRY'
            or proof.method!='bounded-interframe-body-v1' or proof.status!='CORROBORATED'
            or proof.uncertainty is None or not 0<=proof.uncertainty<=Fraction(1,20)
            or not proof.raw_refs or any(r.frame!=frame.frame or r.time!=frame.simtime for r in proof.raw_refs)):
        return None
    expected={'fixture_hash':fixture_hash,'previous_actors':_digest(previous.actors),
              'actors':_digest(frame.actors),'previous_frame':previous.frame,'frame':frame.frame}
    binding={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
    if proof.limits!=expected or not _review_binds(proof.review,_digest(binding),('CAPABILITY:CONTINUOUS_GEOMETRY',)):
        return None
    return proof


def _section_margin(vertices, section):
    normal=section.normal;length=sqrt(sum(v*v for v in normal))
    if length==0:
        return None
    return tuple(Fraction(sum((v-o)*n for v,o,n in zip(p,section.vertices[0],normal))/length) for p in vertices)


def _section_corridor(vertices, section):
    # Pure in (vertex values, immutable section): memoized by value + section identity. ponytail: bounded cache.
    try:
        key = (tuple(vertices), id(section))
    except TypeError:
        return _section_corridor_uncached(vertices, section)
    hit = _CORRIDOR_CACHE.get(key)
    if hit is not None and hit[0] is section:
        return hit[1]
    if len(_CORRIDOR_CACHE) > 65536:
        _CORRIDOR_CACHE.clear()
    result = _section_corridor_uncached(vertices, section)
    _CORRIDOR_CACHE[key] = (section, result)
    return result


def _section_corridor_uncached(vertices, section):
    # Orthogonal projection must precede dropping an axis for an oblique section.
    from shapely.geometry import MultiPoint, Point
    normal=tuple(Fraction(v) for v in section.normal);square=sum(v*v for v in normal)
    if not square or not section.vertices:
        return False
    origin=section.vertices[0]
    projected=[]
    for p in vertices:
        distance=sum((Fraction(v)-Fraction(o))*n for v,o,n in zip(p,origin,normal))/square
        projected.append(tuple(float(Fraction(v)-distance*n) for v,n in zip(p,normal)))
    axis=max(range(3),key=lambda k:abs(normal[k]))
    others=[k for k in range(3) if k!=axis]
    plane=MultiPoint([(p[others[0]],p[others[1]]) for p in section.vertices]).convex_hull
    return plane.geom_type=='Polygon' and all(plane.covers(Point(p[others[0]],p[others[1]])) for p in projected)


def detect_events(frames: tuple[FrameRecord,...], fixture: CompiledFixture) -> tuple[EventRecord,...]:
    """Frozen C/L/M and I/O event kernels; events do not certify action completion."""
    if not frames:
        return ()
    if not _contiguous(frames):
        last=frames[-1]
        return (EventRecord('WITNESS_UNKNOWN',last.frame,last.simtime,_frame_refs(last)),)
    if any(not _frame_refs(f) or len({a.role for a in f.actors})!=len(f.actors)
           or not {'EGO','NPC'}.issubset({a.role for a in f.actors}) for f in frames):
        return (EventRecord('WITNESS_UNKNOWN',frames[-1].frame,frames[-1].simtime,_frame_refs(frames[-1])),)
    identities={a.role:a.id for a in frames[0].actors}
    binding=_digest(fixture)
    if (any({a.role:a.id for a in f.actors}!=identities for f in frames)
            or any(_continuous_proof(a,b,binding) is None for a,b in zip(frames,frames[1:]))):
        return (EventRecord('WITNESS_UNKNOWN',frames[-1].frame,frames[-1].simtime,_frame_refs(frames[-1])),)
    if fixture.domain.topology.get('category')=='F':
        return _with_destination(_detect_f(frames,fixture),frames,fixture)
    if fixture.pair.names==('v_mean_E','e_lat_peak'):
        return _with_destination(_detect_io(frames,fixture),frames,fixture)
    if fixture.pair.names!=('d_yield_m','t_entry_s') or fixture.G is None:
        return ()
    events=[];seen=set();derived=[];previous_positions=None;fixture_hash=_digest(fixture)
    for i,frame in enumerate(frames):
        refs=_frame_refs(frame)
        actors={a.role:a for a in frame.actors}
        positions={};vertices={}
        for role in ('EGO','NPC'):
            actor=actors.get(role)
            if actor is None or actor.route_valid is not True or role not in fixture.routes:
                continue
            body=world_vertices(actor.body,actor.pose)
            stations=tuple(project_route(p,fixture.routes[role]) for p in body)
            if any(isinstance(s,BlockedFixture) for s in stations):
                continue
            vertices[role]=body;positions[role]=max(stations)
        newly=[]
        def emit(name):
            if name not in seen and refs:
                event=EventRecord(name,frame.frame,frame.simtime,refs)
                events.append(event);newly.append(event);seen.add(name)
        if previous_positions is not None:
            for role,name,section in (('EGO','E_ENTRY',fixture.domain.e_entry),('NPC','NPC_ENTRY',fixture.domain.n_entry)):
                if (role in positions and role in previous_positions
                        and previous_positions[role]<section.route_station<=positions[role]
                        and _section_corridor(vertices[role],section)):
                    emit(name)
            if 'EGO' in previous_positions and 'EGO' in positions:
                before=fixture.domain.e_entry.route_station-previous_positions['EGO']
                now=fixture.domain.e_entry.route_station-positions['EGO']
                if before>fixture.G>=now:
                    emit('TRIGGER')
        proof=_continuous_proof(frames[i-1],frame,fixture_hash) if i else None
        clear=False
        if 'NPC_ENTRY' in seen and 'NPC' in positions and proof is not None and refs:
            margins=_section_margin(vertices['NPC'],fixture.domain.n_exit)
            clear=(margins is not None and min(margins)-proof.uncertainty>=Fraction(1,2)
                   and _section_corridor(vertices['NPC'],fixture.domain.n_exit))
        def packet(value):
            return {'value':value,'frame':frame.frame,'time':frame.simtime,
                    'fixture_hash':fixture_hash,'witness_refs':refs}
        stopped=False;arrived=False
        if 'EGO' in positions and refs and (i==0 or proof is not None):
            error=proof.uncertainty if proof is not None else Fraction(0)
            speed=_speed(actors['EGO'].velocity)
            stopped=(speed is not None and speed<=Fraction(1,10)
                     and fixture.domain.e_entry.route_station-positions['EGO']-error>=Fraction(1,2)
                     and _section_corridor(vertices['EGO'],fixture.domain.e_entry))
            destination=fixture.sections.get('DESTINATION')
            if destination is not None and destination.route_station==fixture.routes['EGO'].destination:
                margins=_section_margin(vertices['EGO'],destination)
                arrived=(margins is not None and min(margins)-error>0
                         and _section_corridor(vertices['EGO'],destination))
        derived.append(replace(frame,events=tuple(newly),integrity={**frame.integrity,
                      'predicates':{'NPC_WHOLE_BODY_CLEAR':packet(clear),
                                    'EGO_STOP':packet(stopped),'EGO_DESTINATION':packet(arrived)}}))
        previous_positions=positions
    for predicate,duration in (('NPC_WHOLE_BODY_CLEAR',Fraction(1,4)),('EGO_STOP',Fraction(1,2)),
                               ('EGO_DESTINATION',Fraction(1,4))):
        confirmed=confirm_hold(tuple(derived),predicate,duration)
        if confirmed is not None:
            events.append(confirmed)
    return tuple(sorted(events,key=lambda e:(e.frame,e.name)))


def _reference_marker_events(frames,fixture):
    """First actual fixed-reference station observations; no moved marker/timer."""
    result=[]
    for response in fixture.responses:
        for switch in response.phases.get('reference_switches',()):
            for frame in frames:
                actors=tuple(a for a in frame.actors if a.role==response.actor_role)
                if len(actors)!=1 or actors[0].route_valid is not True:
                    continue
                a=actors[0];station=_metric_station((a.pose.x,a.pose.y,a.pose.z),response.route)
                refs=_frame_refs(frame)
                if station is not None and station>=switch['marker_arc_m'] and refs:
                    result.append(EventRecord('REFERENCE_MARKER:'+('NPC:' if response.actor_role=='NPC' else '')+switch['cause'],frame.frame,frame.simtime,refs));break
    return tuple(result)


def _with_destination(events,frames,fixture):
    events=(*events,*_reference_marker_events(frames,fixture),*_f01_brake_marker(frames,fixture),
            *_f04_spatial_events(frames,fixture,events),*_f05_creep_events(frames,fixture,events))
    if fixture.domain.topology.get('mechanism') in ('F01','F04'):
        trigger=next((e for e in events if e.name=='TRIGGER'),None);response=_action_response(frames,fixture)
        if trigger is not None and response is not None and response.action_id=='A':
            stop=_post_trigger_stop(frames,fixture,trigger)
            if stop is not None:
                events=(*events,stop)
    section=fixture.sections.get('DESTINATION');route=fixture.routes.get('EGO')
    if section is None or route is None or section.route_station!=route.destination:
        return events
    derived=[];binding=_digest(fixture)
    for i,frame in enumerate(frames):
        actors=tuple(a for a in frame.actors if a.role=='EGO')
        proof=_continuous_proof(frames[i-1],frame,binding) if i else None
        refs=_frame_refs(frame);arrived=False
        if len(actors)==1 and actors[0].route_valid is True and refs and (i==0 or proof is not None):
            body=world_vertices(actors[0].body,actors[0].pose)
            margins=_section_margin(body,section);error=proof.uncertainty if proof is not None else Fraction(0)
            arrived=(margins is not None and min(margins)-error>0 and _section_corridor(body,section))
        packet={'value':arrived,'frame':frame.frame,'time':frame.simtime,'fixture_hash':binding,'witness_refs':refs}
        derived.append(replace(frame,events=(),integrity={**frame.integrity,'predicates':{'EGO_DESTINATION':packet}}))
    event=confirm_hold(tuple(derived),'EGO_DESTINATION',Fraction(1,4))
    return tuple(sorted((*events,event),key=lambda e:(e.frame,e.name))) if event is not None else events


def _decel_windows(frames,role):
    speeds=[]
    for frame in frames:
        actors=tuple(a for a in frame.actors if a.role==role)
        speed=_speed(actors[0].velocity) if len(actors)==1 and actors[0].route_valid is True else None
        if speed is None:
            return None
        speeds.append(speed)
    return tuple((i,(speeds[i-5]-speeds[i])/Fraction(1,4))
                 for i in range(5,len(frames)) if frames[i].simtime-frames[i-5].simtime==Fraction(1,4))


def _planned_brake(frame,fixture):
    responses=tuple(r for r in fixture.responses if r.actor_role=='NPC' and r.action_id=='NPC_COMMON')
    npc=tuple(a for a in frame.actors if a.role=='NPC')
    if len(responses)!=1 or len(npc)!=1 or responses[0].phases.get('brake')!='F01_BRAKE':
        return False
    actor=npc[0]
    return any(c.actor==actor.id and c.next_frame==frame.frame and c.frame==frame.frame-1
               and c.response_hash==responses[0].hash and c.cause=='F01_BRAKE'
               and c.control is not None and c.control.brake>0 for c in actor.commands)


def _detect_f(frames,fixture):
    mechanism=fixture.domain.topology.get('mechanism')
    contract=_F_CONTRACTS.get(mechanism)
    if contract is None or (fixture.pair.names,fixture.pair.units,fixture.pair.estimators,fixture.pair.window)!=contract:
        return (EventRecord('WITNESS_UNKNOWN',frames[-1].frame,frames[-1].simtime,_frame_refs(frames[-1])),)
    if mechanism=='F05':
        return _detect_f05(frames,fixture)
    if mechanism=='F04':
        return _detect_f04(frames,fixture)
    if mechanism=='F03':
        return _detect_f03(frames,fixture)
    if mechanism=='F02':
        return _detect_f02(frames,fixture)
    if mechanism=='F06-ALT1':
        return _detect_f06(frames,fixture)
    if mechanism=='F01':
        windows=_decel_windows(frames,'NPC')
        if windows is None:
            return (EventRecord('WITNESS_UNKNOWN',frames[-1].frame,frames[-1].simtime,_frame_refs(frames[-1])),)
        for i,decel in windows:
            if decel>=Fraction(3,2) and all(_planned_brake(f,fixture) for f in frames[i-4:i+1]):
                refs=tuple(r for f in frames[i-5:i+1] for r in _frame_refs(f))
                trigger=EventRecord('TRIGGER',frames[i].frame,frames[i].simtime,refs)
                return _f01_after_trigger(frames,fixture,i,trigger)
        return ()
    return (EventRecord('WITNESS_UNKNOWN',frames[-1].frame,frames[-1].simtime,_frame_refs(frames[-1])),)


def _f01_brake_marker(frames,fixture):
    """Actual NPC front at its frozen compiled brake-start section, not a timer."""
    if fixture.domain.topology.get('category')!='F' or fixture.domain.topology.get('mechanism')!='F01':
        return ()
    section=fixture.sections.get('F01_BRAKE_START');binding=_digest(fixture)
    if section is None:
        return ()
    for previous,current in zip(frames,frames[1:]):
        a=tuple(x for x in previous.actors if x.role=='NPC');b=tuple(x for x in current.actors if x.role=='NPC')
        proof=_continuous_proof(previous,current,binding);refs=(*_frame_refs(previous),*_frame_refs(current))
        if (len(a)!=1 or len(b)!=1 or a[0].id!=b[0].id or a[0].route_valid is not True
                or b[0].route_valid is not True or proof is None or not _frame_refs(previous) or not _frame_refs(current)):
            continue
        before=world_vertices(a[0].body,a[0].pose);after=world_vertices(b[0].body,b[0].pose)
        old=_section_margin(before,section);new=_section_margin(after,section)
        if (old is not None and new is not None and max(old)+proof.uncertainty<=0<max(new)-proof.uncertainty
                and _section_corridor(before,section) and _section_corridor(after,section)):
            return (EventRecord('F01_BRAKE_MARKER',current.frame,current.simtime,
                                tuple(dict.fromkeys((*refs,*proof.raw_refs)))),)
    return ()


def _stationary_interval(previous,current,fixture,role):
    """Observed stable-role velocity and directed-station rate, never brake credit."""
    a=tuple(x for x in previous.actors if x.role==role);b=tuple(x for x in current.actors if x.role==role)
    route=fixture.routes.get(role)
    if (len(a)!=1 or len(b)!=1 or route is None or a[0].id!=b[0].id or _digest(a[0].body)!=_digest(b[0].body)
            or a[0].route_valid is not True or b[0].route_valid is not True or not _actor_stopped(current,role)
            or not _frame_refs(previous) or not _frame_refs(current)
            or current.simtime-previous.simtime!=Fraction(1,20)
            or _continuous_proof(previous,current,_digest(fixture)) is None):
        return False
    before=_metric_station((a[0].pose.x,a[0].pose.y,a[0].pose.z),route)
    now=_metric_station((b[0].pose.x,b[0].pose.y,b[0].pose.z),route)
    return before is not None and now is not None and abs(now-before)/(current.simtime-previous.simtime)<=Fraction(1,10)


def _f01_after_trigger(frames,fixture,index,trigger):
    result=[trigger];stop_start=None;held=False;move_start=None;moved=False
    end=fixture.sections.get('F01_END')
    if end is None:
        return (trigger,_unknown(frames[index]))
    for i in range(index+1,len(frames)):
        frame=frames[i]
        if not held:
            if _stationary_interval(frames[i-1],frame,fixture,'NPC'):
                if stop_start is None:
                    stop_start=i
                held=frame.simtime-frames[stop_start].simtime>=2
                if held:
                    result.append(EventRecord('NPC_F01_STOP_HOLD_CONFIRMED',frame.frame,frame.simtime,
                        tuple(dict.fromkeys(r for sample in frames[stop_start:i+1] for r in _frame_refs(sample)))))
            else:
                stop_start=None
            continue
        if not moved:
            if _forward_move_sample(frames[i-1],frame,fixture.routes['NPC'],'NPC'):
                if move_start is None:
                    move_start=i
                if frame.simtime-frames[move_start].simtime>=Fraction(1,4):
                    moved=True
                    result.append(EventRecord('N_MOVE',frame.frame,frame.simtime,
                                  tuple(r for f in frames[move_start:i+1] for r in _frame_refs(f))))
            else:
                move_start=None
        if moved and end is not None and _body_crossed(frames[i-1],frame,'NPC',end):
            result.append(EventRecord('F01_N_CLEAR',frame.frame,frame.simtime,_frame_refs(frames[i-1])+_frame_refs(frame)))
            break
    return tuple(result)


def _frame_capability(frame,fixture,key,kind,method):
    packet=frame.integrity.get(key)
    if packet is None:
        return None
    proof=decode_record('CapabilityProof',encode_record(packet))
    if (not isinstance(proof,CapabilityProof) or proof.kind!=kind or proof.method!=method
            or proof.status!='CORROBORATED' or proof.uncertainty is None
            or not 0<=proof.uncertainty<=Fraction(1,20) or not proof.raw_refs
            or any(r.frame!=frame.frame or r.time!=frame.simtime for r in proof.raw_refs)):
        return None
    limits=proof.limits
    if (limits.get('fixture_hash')!=_digest(fixture) or limits.get('frame')!=frame.frame
            or limits.get('actors_hash')!=_digest(frame.actors)):
        return None
    binding={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
    return proof if _review_binds(proof.review,_digest(binding),('CAPABILITY:'+kind,)) else None


def _unknown(frame):
    return EventRecord('WITNESS_UNKNOWN',frame.frame,frame.simtime,_frame_refs(frame))


def _phase_command(frame,fixture,cause):
    responses=tuple(r for r in fixture.responses if r.actor_role=='NPC' and r.action_id=='NPC_COMMON')
    actors=tuple(a for a in frame.actors if a.role=='NPC')
    if len(responses)!=1 or len(actors)!=1 or responses[0].phases.get('brake')!=cause:
        return False
    actor=actors[0]
    return any(c.actor==actor.id and c.frame==frame.frame-1 and c.next_frame==frame.frame
               and c.cause==cause and c.response_hash==responses[0].hash
               and c.control is not None and c.control.brake>0 for c in actor.commands)


def _detect_f03(frames,fixture):
    route=fixture.routes['NPC'];start=None;trigger=None;result=[]
    npcs=[next(a for a in f.actors if a.role=='NPC') for f in frames]
    for i,(frame,npc) in enumerate(zip(frames,npcs)):
        if trigger is not None:
            break
        proof=_frame_capability(frame,fixture,'rollback','ROLLBACK','unpowered-grade-motion-v1')
        if proof is None:
            return (_unknown(frame),)
        gravity=proof.limits.get('gravity_along_reverse_mps2')
        if isinstance(gravity,bool) or not isinstance(gravity,(int,Fraction)) or gravity<=0:
            return (_unknown(frame),)
        speed=_directed_speed(npc,route);control=npc.readback
        if speed is None or control is None:
            return (_unknown(frame),)
        unpowered=(control.throttle==0 and control.reverse is False and control.gear!=-1)
        # Grade packet alone never substitutes for observed downward displacement.
        falling=(i==0 or (npc.pose.z<npcs[i-1].pose.z and
                 _metric_station((npc.pose.x,npc.pose.y,npc.pose.z),route)<
                 _metric_station((npcs[i-1].pose.x,npcs[i-1].pose.y,npcs[i-1].pose.z),route)))
        if speed<=-Fraction(1,5) and unpowered and falling:
            if start is None:
                start=i
            if frame.simtime-frames[start].simtime>=Fraction(1,4):
                trigger=i
                refs=tuple(r for f in frames[start:i+1] for r in _frame_refs(f))
                result.append(EventRecord('TRIGGER',frame.frame,frame.simtime,refs))
        else:
            start=None
    if trigger is None:
        return ()
    # The program issues at cue+2s. Readback/CommandRecord at frame n
    # belongs to issue n-1, so an applied brake one tick earlier is premature.
    due=frames[trigger].simtime+2+frames[trigger].dt;stop_start=None
    for i in range(trigger+1,len(frames)):
        frame=frames[i];npc=npcs[i];control=npc.readback
        if frame.simtime<due:
            if _phase_command(frame,fixture,'F03_BRAKE'):
                return tuple(result)+(_unknown(frame),)
            continue
        if (not _phase_command(frame,fixture,'F03_BRAKE') or control is None or control.brake<=0):
            return tuple(result)+(_unknown(frame),)
        if _stationary_interval(frames[i-1],frame,fixture,'NPC'):
            if stop_start is None:
                stop_start=i
            if frame.simtime-frames[stop_start].simtime>=Fraction(1,2):
                result.append(EventRecord('NPC_STOP_CONFIRMED',frame.frame,frame.simtime,
                              tuple(r for f in frames[stop_start:i+1] for r in _frame_refs(f))))
                break
        else:
            stop_start=None
    return tuple(result)


def _body_crossed(previous,current,role,section):
    old=next(a for a in previous.actors if a.role==role)
    new=next(a for a in current.actors if a.role==role)
    if old.route_valid is not True or new.route_valid is not True:
        return False
    before=world_vertices(old.body,old.pose);after=world_vertices(new.body,new.pose)
    a=_section_margin(before,section);b=_section_margin(after,section)
    return (a is not None and b is not None and min(a)<=0<min(b)
            and _section_corridor(before,section) and _section_corridor(after,section))


def _door_state(frame,fixture):
    from .geometry import _is_box
    proof=_frame_capability(frame,fixture,'door_geometry','DOOR_GEOMETRY','calibrated-door-envelope-v1')
    if proof is None:
        return None
    corridor=fixture.domain.topology.get('door_corridor')
    envelope=proof.limits.get('collider_envelope');state=proof.limits.get('door_state')
    if not _is_box(corridor) or not _is_box(envelope) or state not in ('CLOSED','OPEN'):
        return None
    overlap=tuple(min(max(Fraction(v[k]) for v in corridor),max(Fraction(v[k]) for v in envelope))-
                  max(min(Fraction(v[k]) for v in corridor),min(Fraction(v[k]) for v in envelope)) for k in range(3))
    if any(d < -proof.uncertainty for d in overlap):
        return (state,'OUTSIDE')
    if all(d>2*proof.uncertainty for d in overlap):
        return (state,'INTRUDING')
    return None  # uncertain/touching envelope is not a manufactured intrusion


def _f04_path(frame,fixture,returning=False):
    """A separately reviewed path stays in the ONE frozen initial lane.

    No target-lane alias is permitted. Current body fit and future path-clear
    receipt are not substitutes for full continuous motion/contact admission.
    """
    from .geometry import _is_box
    key,kind,method=(('return_path','RETURN_PATH','bounded-return-corridor-v1') if returning else
                     ('lane_change_path','LANE_CHANGE_PATH','bounded-lane-change-corridor-v1'))
    proof=_frame_capability(frame,fixture,key,kind,method)
    regions=fixture.domain.topology.get('action_regions')
    if (proof is None or not isinstance(regions,Mapping) or set(regions)!={'EGO_INITIAL'}
            or not _is_box(regions['EGO_INITIAL'])):
        return False
    region=regions['EGO_INITIAL'];limits=proof.limits
    if set(limits)!={'fixture_hash','frame','actors_hash','from_region_hash','to_region_hash','route_hash','minimum_clearance_m'}:
        return False
    clearance=limits['minimum_clearance_m'];actors=tuple(a for a in frame.actors if a.role=='EGO')
    return (len(actors)==1 and actors[0].route_valid is True
            and limits['from_region_hash']==limits['to_region_hash']==_digest(region)
            and limits['route_hash']==_digest(fixture.routes['EGO'])
            and not isinstance(clearance,bool) and isinstance(clearance,(int,Fraction))
            and clearance-proof.uncertainty>=Fraction(1,5)
            and _in_action_region(actors[0],region,Fraction(3,20)+proof.uncertainty) is True)


def _f04_spatial_events(frames,fixture,events):
    """Observed F04 B path/marker/home witnesses, not a requested offset readback.

    Exact horizontal centre return is the supported offline observation here;
    no new tracking tolerance, banked approximation or native calibration claim.
    """
    if fixture.domain.topology.get('mechanism')!='F04':
        return ()
    response=_action_response(frames,fixture);trigger=next((e for e in events if e.name=='TRIGGER'),None)
    if response is None or response.action_id!='B' or trigger is None:
        return ()
    from .response import _lateral_contract
    try:
        _lateral_contract(response,fixture)
        segments=response.profile['segments']
        if len(segments)!=2 or response.route is None:
            return ()
        start=segments[1]['start_arc_m'];finish=start+segments[1]['length_m']
    except (ValueError,TypeError,KeyError,AttributeError):
        return ()
    end=next((e for e in events if e.name=='F04_END'),None);result=[];marker=False;completed=False;home=False;hold=[]
    out_end=segments[0]['start_arc_m']+segments[0]['length_m'];separation=segments[0]['end_offset_m']
    offset_confirmed=False;offset_hold=[]
    region=fixture.domain.topology['action_regions']['EGO_INITIAL'];binding=_digest(fixture)
    for i,frame in enumerate(frames):
        if frame.frame<trigger.frame:
            continue
        for returning,name,key in ((False,'LANE_CHANGE_PATH_CLEAR','lane_change_path'),(True,'RETURN_PATH_CLEAR','return_path')):
            if _f04_path(frame,fixture,returning):
                proof=decode_record('CapabilityProof',encode_record(frame.integrity[key]))
                result.append(EventRecord(name,frame.frame,frame.simtime,_frame_refs(frame)+proof.raw_refs))
        actors=tuple(a for a in frame.actors if a.role=='EGO')
        if len(actors)!=1 or actors[0].route_valid is not True:
            hold=[];continue
        actor=actors[0];station=_metric_station((actor.pose.x,actor.pose.y,actor.pose.z),response.route)
        if station is None:
            hold=[];continue
        proof=_continuous_proof(frames[i-1],frame,binding) if i else None
        previous=next((a for a in frames[i-1].actors if a.role=='EGO'),None) if i else None
        stable=(proof is not None and previous is not None and previous.id==actor.id and previous.body==actor.body)
        at_offset=(not offset_confirmed and stable and out_end<=station<start and proof.uncertainty==0
                   and Fraction(actor.pose.y)-Fraction(response.route.transforms[0].y)==separation
                   and _in_action_region(actor,region,Fraction(3,20)) is True)
        if not at_offset:
            offset_hold=[]
        else:
            if offset_hold and (frame.frame!=offset_hold[-1].frame+1 or frame.simtime-offset_hold[-1].simtime!=Fraction(1,20)):
                offset_hold=[]
            offset_hold.append(frame)
            if frame.simtime-offset_hold[0].simtime>=Fraction(1,4):
                result.append(EventRecord('F04_OFFSET_CONFIRMED',frame.frame,frame.simtime,
                    tuple(dict.fromkeys(r for f in offset_hold for r in _frame_refs(f)))));offset_confirmed=True
        if not marker and station>=start:
            if end is None or end.frame>=frame.frame:
                return tuple(result)+(_unknown(frame),)
            result.append(EventRecord('F04_RETURN_MARKER',frame.frame,frame.simtime,_frame_refs(frame)));marker=True
        if marker and not completed and station>=finish:
            result.append(EventRecord('F04_RETURN_REFERENCE_MARKER',frame.frame,frame.simtime,_frame_refs(frame)));completed=True
        inside=(completed and offset_confirmed and not home and stable and actor.pose.y==response.route.transforms[0].y
                and _in_action_region(actor,region,Fraction(3,20)+proof.uncertainty) is True)
        if not inside:
            hold=[];continue
        if hold and (frame.frame!=hold[-1].frame+1 or frame.simtime-hold[-1].simtime!=Fraction(1,20)):
            hold=[]
        hold.append(frame)
        if frame.simtime-hold[0].simtime>=Fraction(1,4):
            result.append(EventRecord('F04_HOME_CONFIRMED',frame.frame,frame.simtime,
                tuple(dict.fromkeys(r for f in hold for r in _frame_refs(f)))));home=True
    return tuple(result)


def _detect_f04(frames,fixture):
    end=fixture.sections.get('F04_END')
    if end is None:
        return (_unknown(frames[-1]),)
    result=[];previous_state=_door_state(frames[0],fixture);triggered=False;closed=False;ended=False
    if previous_state is None:
        return (_unknown(frames[0]),)
    for previous,current in zip(frames,frames[1:]):
        state=_door_state(current,fixture)
        if state is None:
            return tuple(result)+(_unknown(current),)
        if not triggered and previous_state==('CLOSED','OUTSIDE') and state==('OPEN','INTRUDING'):
            result.append(EventRecord('TRIGGER',current.frame,current.simtime,_frame_refs(previous)+_frame_refs(current)))
            triggered=True
        if closed and state!=('CLOSED','OUTSIDE'):
            return tuple(result)+(_unknown(current),)
        if triggered and not closed and state==('CLOSED','OUTSIDE'):
            result.append(EventRecord('DOOR_CLOSED_CLEAR_CONFIRMED',current.frame,current.simtime,
                                     _frame_refs(previous)+_frame_refs(current)))
            closed=True
        if triggered and closed and state==('CLOSED','OUTSIDE'):
            result.append(EventRecord('DOOR_CLOSED_CLEAR_CURRENT',current.frame,current.simtime,_frame_refs(current)))
        if triggered and not ended and _body_crossed(previous,current,'EGO',end):
            result.append(EventRecord('F04_END',current.frame,current.simtime,_frame_refs(previous)+_frame_refs(current)))
            ended=True
        previous_state=state
    return tuple(result)


def _forward_move_sample(previous,current,route,role):
    a=next(a for a in previous.actors if a.role==role)
    b=next(a for a in current.actors if a.role==role)
    speed=_directed_speed(b,route)
    before=_metric_station((a.pose.x,a.pose.y,a.pose.z),route)
    after=_metric_station((b.pose.x,b.pose.y,b.pose.z),route)
    return (a.route_valid is True and b.route_valid is True and speed is not None
            and speed>=Fraction(1,5) and before is not None and after is not None and after>before)


def _validation_start_frame(frames,fixture):
    """Admitted validation clock, never a physical cue or a restarted queue hold.

    A declared start stays closed on every incomplete live prefix. The full
    public witness additionally binds this exact clock to initialization_ref;
    this observation predicate alone cannot grant native runtime admission.
    """
    declared=fixture.environment.get('validation_start')
    if declared!='recorded-readiness-start-v1':raise ValueError('VALIDATION_START_UNSUPPORTED')
    candidates=tuple(f for f in frames if 'validation_start' in f.integrity)
    if not candidates:return None
    if len(candidates)!=1:raise ValueError('VALIDATION_START_UNPROVEN')
    ready=candidates[0]
    proof=_frame_capability(ready,fixture,'validation_start','VALIDATION_START',declared)
    if proof is None or set(proof.limits)!={'fixture_hash','frame','actors_hash'}:
        raise ValueError('VALIDATION_START_UNPROVEN')
    metadata=fixture.environment.get('readiness')
    if not isinstance(metadata,Mapping) or set(metadata)!= {'targets_mps','markers_m'}:
        raise ValueError('VALIDATION_READINESS_UNPROVEN')
    hold=tuple(f for f in frames if ready.simtime-Fraction(1,2)<=f.simtime<=ready.simtime)
    identity={a.role:(a.id,_digest(a.body)) for a in ready.actors}
    if (len(hold)!=11 or hold[0].simtime!=ready.simtime-Fraction(1,2) or set(identity)!={'EGO','NPC'}
            or set(metadata['targets_mps'])!={'EGO','NPC'} or set(metadata['markers_m'])!={'EGO','NPC'}):
        raise ValueError('VALIDATION_READINESS_UNPROVEN')
    for f in hold:
        if not _frame_refs(f) or {a.role:(a.id,_digest(a.body)) for a in f.actors}!=identity:
            raise ValueError('VALIDATION_READINESS_UNPROVEN')
        for a in f.actors:
            speed=_speed(a.velocity);target=metadata['targets_mps'][a.role];marker=metadata['markers_m'][a.role]
            route=fixture.routes.get(a.role);station=_metric_station((a.pose.x,a.pose.y,a.pose.z),route) if route is not None else None
            if (not isinstance(target,Fraction) or target<0 or not isinstance(marker,Fraction)
                    or a.route_valid is not True or station is None or speed is None
                    or abs(speed-target)>Fraction(1,10)
                    or abs(station-(marker-target*(ready.simtime-f.simtime)))>Fraction(1,10)):
                raise ValueError('VALIDATION_READINESS_UNPROVEN')
    return ready.frame


def _detect_f05(frames,fixture):
    topology=fixture.domain.topology;end=fixture.sections.get('F05_END')
    gap=topology.get('queue_gap_m');front=topology.get('nominal_front_t0_m')
    if (end is None or isinstance(front,bool) or not isinstance(front,(int,Fraction))
            or isinstance(gap,bool) or not isinstance(gap,(int,Fraction)) or gap<0
            or end.route_station-front!=10):
        return (_unknown(frames[-1]),)
    start=None
    if 'validation_start' in fixture.environment:
        try:start=_validation_start_frame(frames,fixture)
        except (ValueError,TypeError,KeyError,AttributeError):return (_unknown(frames[-1]),)
        if start is None:return ()
    result=[];queue_start=None;ego_start=None;trigger=None;move_start=None;moved=False;advanced=False
    route=fixture.routes['EGO'];reference='route:'+_digest(route)
    for i,frame in enumerate(frames):
        if trigger is None:
            actual=_route_observation(frame,{'directed_route':route},reference,'min_front_gap')
            if actual is None:
                return tuple(result)+(_unknown(frame),)
            npc_stop=(_actor_stopped(frame,'NPC') if i==0 else _stationary_interval(frames[i-1],frame,fixture,'NPC'))
            ego_stop=(_actor_stopped(frame,'EGO') if i==0 else _stationary_interval(frames[i-1],frame,fixture,'EGO'))
            if npc_stop and actual==gap:
                if queue_start is None:
                    queue_start=i
            else:
                queue_start=None
            if ego_stop:
                if ego_start is None:
                    ego_start=i
            else:
                ego_start=None
            if (queue_start is not None and ego_start is not None and (start is None or frame.frame>=start)
                    and frame.simtime-frames[queue_start].simtime>=1
                    and frame.simtime-frames[ego_start].simtime>=Fraction(1,2)):
                trigger=i
                result.append(EventRecord('TRIGGER',frame.frame,frame.simtime,
                              tuple(r for f in frames[min(queue_start,ego_start):i+1] for r in _frame_refs(f))))
            continue
        if not moved:
            moving=_forward_move_sample(frames[i-1],frame,fixture.routes['NPC'],'NPC')
            if moving:
                if frame.simtime-frames[trigger].simtime<3+frames[trigger].dt:
                    return tuple(result)+(_unknown(frame),)
                if move_start is None:
                    move_start=i
                if frame.simtime-frames[move_start].simtime>=Fraction(1,4):
                    moved=True
                    result.append(EventRecord('N_MOVE',frame.frame,frame.simtime,
                                  tuple(r for f in frames[move_start:i+1] for r in _frame_refs(f))))
            else:
                move_start=None
        if moved and not advanced:
            event=_f05_body_advance(frames,fixture,trigger,i)
            if event is not None:
                result.append(event);advanced=True
        if moved and _body_crossed(frames[i-1],frame,'EGO',end):
            result.append(EventRecord('F05_END',frame.frame,frame.simtime,_frame_refs(frames[i-1])+_frame_refs(frame)))
            break
    return tuple(result)


def _f05_creep_events(frames,fixture,events):
    """Observed stock-creep stopping bound/actual terminal STOP/current queue path.

    These extra permissions do not change the frozen TRIGGER/N_MOVE/F05_END
    metric windows. The stop proposal must have independent source/review binding
    before it is used; native stopping/contact qualification remains separate.
    """
    if fixture.domain.topology.get('mechanism')!='F05':
        return ()
    response=_action_response(frames,fixture);trigger=next((e for e in events if e.name=='TRIGGER'),None)
    if (response is None or response.action_id!='B' or trigger is None
            or not any(row.get('after_event')=='EGO_CREEP_STOPPING_BOUND'
                       for row in response.phases.get('program',{}).get('transitions',()))):
        return ()
    from .response import _creep_stop_proof,_queue_path
    origin=next((f for f in frames if f.frame==trigger.frame),None)
    ego=next((a for a in origin.actors if a.role=='EGO'),None) if origin else None
    if ego is None:return ()
    try:proof=_creep_stop_proof(fixture,response,ego)
    except (ValueError,TypeError,KeyError,AttributeError):return ()
    initial=_metric_station((ego.pose.x,ego.pose.y,ego.pose.z),response.route)
    if initial is None:return ()
    move=next((e for e in events if e.name=='N_MOVE'),None);result=[];stopping=False;stopped=False;hold=[];progress=Fraction(0);previous_station=initial
    for i,frame in enumerate(frames):
        if frame.frame<=trigger.frame:continue
        actors=tuple(a for a in frame.actors if a.role=='EGO')
        continuous=_continuous_proof(frames[i-1],frame,_digest(fixture)) if i else None
        if (len(actors)!=1 or continuous is None or actors[0].id!=ego.id or _digest(actors[0].body)!=_digest(ego.body)
                or actors[0].route_valid is not True):return tuple(result)
        actor=actors[0];station=_metric_station((actor.pose.x,actor.pose.y,actor.pose.z),response.route)
        if station is None or station<previous_station:return tuple(result)
        # Once actually released, later forward progress is not additional creep.
        before_release=move is None or frame.frame<=move.frame
        if before_release:
            progress+=station-previous_station
            if progress+continuous.uncertainty>1:return tuple(result)
            if (not stopping and progress+continuous.uncertainty+proof.uncertainty
                    +proof.limits['maximum_forward_speed_mps']*frame.dt>=proof.limits['stopping_boundary_m']):
                result.append(EventRecord('EGO_CREEP_STOPPING_BOUND',frame.frame,frame.simtime,
                    _frame_refs(frame)));stopping=True
            if (stopping and not stopped and progress==1 and continuous.uncertainty==0
                    and _stationary_interval(frames[i-1],frame,fixture,'EGO')):
                hold.append(frame)
                if frame.simtime-hold[0].simtime>=Fraction(1,2):
                    result.append(EventRecord('EGO_CREEP_STOP_CONFIRMED',frame.frame,frame.simtime,
                        tuple(dict.fromkeys(r for f in hold for r in _frame_refs(f)))));stopped=True
            else:hold=[]
        if stopped and move is not None and frame.frame>=move.frame:
            path=_queue_path(frame,fixture,response)
            if path is not None:
                result.append(EventRecord('QUEUE_CLEAR_CONFIRMED',frame.frame,frame.simtime,_frame_refs(frame)+path.raw_refs))
        previous_station=station
    return tuple(result)


def _f05_body_advance(frames,fixture,start,end):
    """Both body extrema have advanced 2m from the observed queue origin."""
    route=fixture.routes.get('NPC');binding=_digest(fixture);extrema=[];errors=[];identity=None
    if route is None:
        return None
    for i in range(start,end+1):
        frame=frames[i];actors=tuple(a for a in frame.actors if a.role=='NPC')
        if len(actors)!=1 or actors[0].route_valid is not True or not _frame_refs(frame):
            return None
        actor=actors[0];key=(actor.id,_digest(actor.body))
        if identity is not None and key!=identity:
            return None
        identity=key
        proof=_continuous_proof(frames[i-1],frame,binding) if i else None
        if proof is None:
            return None
        stations=tuple(_metric_station(v,route) for v in world_vertices(actor.body,actor.pose))
        if not stations or any(s is None for s in stations):
            return None
        extrema.append((min(stations),max(stations)));errors.append(proof.uncertainty)
    if any(b-a-errors[0]-errors[-1]<2 for a,b in zip(extrema[0],extrema[-1])):
        return None
    frame=frames[end]
    return EventRecord('NPC_ADVANCE_2M_CONFIRMED',frame.frame,frame.simtime,
        tuple(dict.fromkeys(r for sample in frames[start:end+1] for r in _frame_refs(sample))))


def _directed_speed(actor,route):
    station=_metric_station((actor.pose.x,actor.pose.y,actor.pose.z),route)
    if station is None or _speed(actor.velocity) is None:
        return None
    values=[]
    for i,(a,b) in enumerate(zip(route.arc,route.arc[1:])):
        if a<=station<=b:
            first,last=route.transforms[i:i+2]
            direction=tuple(Fraction(v)-Fraction(u) for u,v in zip((first.x,first.y,first.z),(last.x,last.y,last.z)))
            length=_speed(direction)
            if not length:
                return None
            values.append(sum(Fraction(v)*d for v,d in zip(actor.velocity,direction))/length)
    return values[0] if values and len(set(values))==1 else None


def _detect_f02(frames,fixture):
    route=fixture.routes['EGO'];section=fixture.sections.get('F02_END')
    front=fixture.domain.topology.get('nominal_front_t0_m')
    if (section is None or isinstance(front,bool) or not isinstance(front,(int,Fraction))
            or section.route_station-front!=60):
        return (EventRecord('WITNESS_UNKNOWN',frames[-1].frame,frames[-1].simtime,_frame_refs(frames[-1])),)
    reference='route:'+_digest(route);context={'directed_route':route};result=[];triggered=False
    for previous,current in zip(frames,frames[1:]):
        old=_route_observation(previous,context,reference,'min_rear_gap')
        gap=_route_observation(current,context,reference,'min_rear_gap')
        actors={a.role:a for a in current.actors}
        ve=_directed_speed(actors['EGO'],route);vn=_directed_speed(actors['NPC'],route)
        if not triggered and old is not None and gap is not None and old>20>=gap>=0 and ve is not None and vn is not None and vn>ve:
            result.append(EventRecord('TRIGGER',current.frame,current.simtime,_frame_refs(previous)+_frame_refs(current)))
            triggered=True
        if triggered:
            ego=actors['EGO'];prior=next(a for a in previous.actors if a.role=='EGO')
            before=_section_margin(world_vertices(prior.body,prior.pose),section)
            body=world_vertices(ego.body,ego.pose);after=_section_margin(body,section)
            if before is not None and after is not None and min(before)<=0<min(after) and _section_corridor(body,section):
                result.append(EventRecord('F02_END',current.frame,current.simtime,_frame_refs(previous)+_frame_refs(current)))
                break
    return tuple(result)


def _actor_stopped(frame,role):
    actors=tuple(a for a in frame.actors if a.role==role)
    if len(actors)!=1 or actors[0].route_valid is not True:
        return False
    speed=_speed(actors[0].velocity)
    return speed is not None and speed<=Fraction(1,10)


def _preparation_cue(previous,current,fixture):
    packet=current.integrity.get('preparation_cue')
    if packet is None:
        return False
    proof=decode_record('CapabilityProof',encode_record(packet))
    if (not isinstance(proof,CapabilityProof) or proof.kind!='REVERSE_PREPARATION'
            or proof.method!='frame-correlated-cue-v1' or proof.status!='CORROBORATED'
            or proof.uncertainty is None or not 0<=proof.uncertainty<=Fraction(1,20)
            or not proof.raw_refs or any(r.frame!=current.frame or r.time!=current.simtime for r in proof.raw_refs)):
        return False
    limits={'fixture_hash':_digest(fixture),'frame':current.frame,'previous_frame':previous.frame,
            'actors_hash':_digest(current.actors),'previous_actors_hash':_digest(previous.actors)}
    binding={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
    return proof.limits==limits and _review_binds(proof.review,_digest(binding),('CAPABILITY:REVERSE_PREPARATION',))


def _detect_f06(frames,fixture):
    def unknown(frame):
        return (EventRecord('WITNESS_UNKNOWN',frame.frame,frame.simtime,_frame_refs(frame)),)
    npcs=[next(a for a in f.actors if a.role=='NPC') for f in frames]
    trigger=None
    for i in range(1,len(frames)):
        before=npcs[i-1].readback;after=npcs[i].readback
        transition=(before is not None and after is not None and before.reverse is False and before.gear!=-1
                    and after.reverse is True and after.manual_gear_shift is True and after.gear==-1)
        if not transition:
            continue
        if (i<11 or any(not _actor_stopped(f,role) for f in frames[i-11:i+1] for role in ('EGO','NPC'))
                or any(not _stationary_interval(frames[j-1],frames[j],fixture,role)
                       for j in range(i-10,i+1) for role in ('EGO','NPC'))
                or not _preparation_cue(frames[i-1],frames[i],fixture)):
            return unknown(frames[i])
        trigger=i;break
    if trigger is None:
        return ()
    cue=frames[trigger]
    result=[EventRecord('TRIGGER',cue.frame,cue.simtime,_frame_refs(frames[trigger-1])+_frame_refs(cue))]
    route=fixture.routes['NPC']
    stations=[_metric_station((a.pose.x,a.pose.y,a.pose.z),route) for a in npcs]
    if any(s is None for s in stations):
        return unknown(cue)
    origin=stations[trigger];reverse_seen=False;stop_start=None
    for i in range(trigger+1,len(frames)):
        f=frames[i];actor=npcs[i];travel=origin-stations[i]
        if stations[i]<stations[i-1]:
            control=actor.readback
            if (control is None or control.reverse is not True or control.manual_gear_shift is not True or control.gear!=-1
                    or f.simtime-cue.simtime<Fraction(3)+cue.dt):
                return tuple(result)+unknown(f)
            reverse_seen=True
        if travel>2 or (reverse_seen and stations[i]>stations[i-1]):
            return tuple(result)+unknown(f)  # never invent a target stop after overshoot or forward rescue
        if reverse_seen and travel==2 and _actor_stopped(f,'NPC'):
            if stop_start is None:
                stop_start=i
            if f.simtime-frames[stop_start].simtime>=Fraction(1,2):
                refs=tuple(r for sample in frames[stop_start:i+1] for r in _frame_refs(sample))
                result.append(EventRecord('NPC_REVERSE_TARGET_STOP_CONFIRMED',f.frame,f.simtime,refs))
                break
        else:
            stop_start=None
    return tuple(result)


def _detect_io(frames, fixture):
    category=fixture.domain.topology.get('category')
    key={'I':'I_SOURCE_BOUNDARY','O':'O_DECISION'}.get(category)
    if key is None or key not in fixture.sections or 'X' not in fixture.sections:
        return (EventRecord('WITNESS_UNKNOWN',frames[-1].frame,frames[-1].simtime,_frame_refs(frames[-1])),)
    boundary=fixture.sections[key];end=fixture.sections['X'];binding=_digest(fixture)
    result=[];seen=set();derived=[]
    for previous,current in zip(frames,frames[1:]):
        prior_refs=_frame_refs(previous);refs=_frame_refs(current)
        proof=_continuous_proof(previous,current,binding)
        if not prior_refs or not refs or proof is None:
            continue
        old={a.role:a for a in previous.actors};new={a.role:a for a in current.actors}
        if len(old)!=len(previous.actors) or len(new)!=len(current.actors):
            continue
        def crossing(role,section,whole):
            if role not in old or role not in new or old[role].id!=new[role].id:
                return False
            if old[role].route_valid is not True or new[role].route_valid is not True:
                return False
            before=world_vertices(old[role].body,old[role].pose)
            after=world_vertices(new[role].body,new[role].pose)
            if not _section_corridor(before,section) or not _section_corridor(after,section):
                return False
            a=_section_margin(before,section);b=_section_margin(after,section)
            if a is None or b is None:
                return False
            # Whole-source -> actual intrusion uses front/max, X uses rear/min.
            extreme=min if whole else max
            # Certified touching is still not beyond the fence. Requiring a
            # strictly negative predecessor loses a real crossing after an exact
            # on-plane sample; the new lower bound must remain strictly beyond.
            return extreme(a)+proof.uncertainty<=0 and extreme(b)-proof.uncertainty>0
        if 'TRIGGER' not in seen and crossing('NPC' if category=='I' else 'EGO',boundary,False):
            seen.add('TRIGGER')
            result.append(EventRecord('TRIGGER',current.frame,current.simtime,prior_refs+refs+proof.raw_refs))
        if 'TRIGGER' in seen:
            if _lane_change_path(current,fixture):
                path=decode_record('CapabilityProof',encode_record(current.integrity['lane_change_path']))
                result.append(EventRecord('LANE_CHANGE_PATH_CLEAR',current.frame,current.simtime,
                                          refs+path.raw_refs))
            if category=='O' and _return_path(current,binding):
                path=decode_record('CapabilityProof',encode_record(current.integrity['return_path']))
                result.append(EventRecord('RETURN_PATH_CLEAR',current.frame,current.simtime,
                                          refs+path.raw_refs))
        return_start=fixture.sections.get('O_RETURN_START') if category=='O' else None
        if ('TRIGGER' in seen and 'RETURN_MARKER' not in seen and return_start is not None
                and crossing('EGO',return_start,False)):
            seen.add('RETURN_MARKER')
            result.append(EventRecord('RETURN_MARKER',current.frame,current.simtime,prior_refs+refs+proof.raw_refs))
        if 'TRIGGER' in seen and 'X_END' not in seen and crossing('EGO',end,True):
            seen.add('X_END')
            result.append(EventRecord('X_END',current.frame,current.simtime,prior_refs+refs+proof.raw_refs))
        clear=False
        if 'TRIGGER' in seen:
            if category=='I' and 'NPC' in new and new['NPC'].route_valid is True:
                source=fixture.domain.topology.get('source_region')
                from .geometry import _is_box
                if _is_box(source):
                    source_margins=_section_margin(source,boundary)
                    body=world_vertices(new['NPC'].body,new['NPC'].pose)
                    margins=_section_margin(body,boundary)
                    clear=(source_margins is not None and max(source_margins)<=0
                           and margins is not None and min(margins)-proof.uncertainty>=Fraction(1,2)
                           and _section_corridor(body,boundary))
            elif category=='O':
                context={'directed_route':fixture.routes['EGO']}
                gap=_route_observation(current,context,'route:'+_digest(fixture.routes['EGO']),'min_rear_gap')
                clear=(gap is not None and gap-proof.uncertainty>=Fraction(1,2)
                       and _return_path(current,binding))
        predicate='NPC_SOURCE_CLEAR' if category=='I' else 'EGO_RETURN_CLEAR'
        derived.append(replace(current,events=tuple(e for e in result if e.frame==current.frame),
                       integrity={**current.integrity,'predicates':{predicate:{'value':clear,
                       'frame':current.frame,'time':current.simtime,'fixture_hash':binding,
                       'witness_refs':refs}}}))
    predicate='NPC_SOURCE_CLEAR' if category=='I' else 'EGO_RETURN_CLEAR'
    confirmed=confirm_hold(tuple(derived),predicate,Fraction(1,4))
    if confirmed is not None:
        result.append(confirmed)
    result.extend(_lane_confirmation_events(frames,fixture,tuple(result)))
    trigger=next((e for e in result if e.name=='TRIGGER'),None)
    response=_action_response(frames,fixture)
    if trigger is not None and category=='I' and response is not None and response.action_id=='A':
        stop=_post_trigger_stop(frames,fixture,trigger)
        if stop is not None:
            result.append(stop)
    if trigger is not None:
        onset,unknown=_lateral_departure(frames,fixture,tuple(f for f in frames if f.frame>=trigger.frame))
        if onset is not None and unknown is None:
            result.append(EventRecord('LANE_CHANGE_ONSET',onset.frame,onset.simtime,_frame_refs(onset)))
    npc_regions=fixture.domain.topology.get('npc_regions')
    if category=='I' and isinstance(npc_regions,Mapping):
        target=npc_regions.get('NPC_TARGET');hold=[]
        from .geometry import _is_box
        if _is_box(target):
            for previous,current in zip(frames,frames[1:]):
                proof=_continuous_proof(previous,current,binding);npc=next((a for a in current.actors if a.role=='NPC'),None)
                inside=False
                if proof is not None and npc is not None and npc.route_valid is True:
                    low=tuple(Fraction(min(v[k] for v in target)) for k in range(3))
                    high=tuple(Fraction(max(v[k] for v in target)) for k in range(3))
                    inside=all(low[k]+proof.uncertainty+(Fraction(3,20) if k<2 else 0)<=Fraction(v[k])<=
                               high[k]-proof.uncertainty-(Fraction(3,20) if k<2 else 0)
                               for v in world_vertices(npc.body,npc.pose) for k in range(3))
                if not inside:
                    hold=[];continue
                hold.append(current)
                if current.simtime-hold[0].simtime>=Fraction(1,4):
                    result.append(EventRecord('NPC_TARGET_LANE_CONFIRMED',current.frame,current.simtime,
                        tuple(dict.fromkeys(r for f in hold for r in _frame_refs(f)))))
                    break
    return tuple(sorted(result,key=lambda e:(e.frame,e.name)))


def _post_trigger_stop(frames,fixture,trigger):
    """Actual role-bound .50s STOP after cue, not initialization or brake credit."""
    route=fixture.routes.get('EGO');hold=[];binding=_digest(fixture)
    if route is None:
        return None
    for previous,current in zip(frames,frames[1:]):
        if current.frame<=trigger.frame or current.simtime<=trigger.time:
            continue
        a=tuple(a for a in previous.actors if a.role=='EGO')
        b=tuple(a for a in current.actors if a.role=='EGO')
        if (len(a)!=1 or len(b)!=1 or a[0].id!=b[0].id
                or a[0].route_valid is not True or b[0].route_valid is not True
                or _continuous_proof(previous,current,binding) is None):
            hold=[];continue
        before=_metric_station((a[0].pose.x,a[0].pose.y,a[0].pose.z),route)
        now=_metric_station((b[0].pose.x,b[0].pose.y,b[0].pose.z),route)
        speed=_speed(b[0].velocity);refs=_frame_refs(current)
        if (before is None or now is None or speed is None or speed>Fraction(1,10)
                or not refs or abs(now-before)/(current.simtime-previous.simtime)>Fraction(1,10)):
            hold=[];continue
        hold.append(current)
        if current.simtime-hold[0].simtime>=Fraction(1,2):
            return EventRecord('STOP_AFTER_TRIGGER',current.frame,current.simtime,
                tuple(dict.fromkeys(r for f in hold for r in _frame_refs(f))))
    return None


def _lane_confirmation_events(frames,fixture,events):
    """Actual wholebody, conservative margin and contiguous .25s lane holds.

    Events authorize no controller/reference switch by themselves: independent
    path, continuous-fit and source/review gates still apply.
    """
    from .geometry import _is_box
    regions=fixture.domain.topology.get('action_regions');trigger=next((e for e in events if e.name=='TRIGGER'),None)
    if not isinstance(regions,Mapping) or trigger is None:
        return ()
    region=regions.get('EGO_TARGET')
    if not _is_box(region):
        return ()
    result=[];hold=[];target=None;binding=_digest(fixture)
    for previous,current in zip(frames,frames[1:]):
        if current.frame<trigger.frame:
            continue
        if target is not None:
            if fixture.domain.topology.get('category')!='O':
                break
            region=regions.get('EGO_INITIAL')
            if not _is_box(region):
                break
        proof=_continuous_proof(previous,current,binding);ego=next((a for a in current.actors if a.role=='EGO'),None)
        inside=False
        if proof is not None and ego is not None and ego.route_valid is True:
            # Footprint buffer is horizontal; vertical uncertainty stays separate.
            low=tuple(Fraction(min(p[k] for p in region)) for k in range(3))
            high=tuple(Fraction(max(p[k] for p in region)) for k in range(3))
            inside=all(low[k]+proof.uncertainty+(Fraction(3,20) if k<2 else 0)<=Fraction(v[k])<=
                       high[k]-proof.uncertainty-(Fraction(3,20) if k<2 else 0)
                       for v in world_vertices(ego.body,ego.pose) for k in range(3))
        if not inside:
            hold=[];continue
        if hold and (current.frame!=hold[-1].frame+1 or current.simtime-hold[-1].simtime!=Fraction(1,20)):
            hold=[]
        hold.append(current)
        if current.simtime-hold[0].simtime>=Fraction(1,4):
            name='TARGET_LANE_CONFIRMED' if target is None else 'RETURN_LANE_CONFIRMED'
            event=EventRecord(name,current.frame,current.simtime,tuple(dict.fromkeys(r for f in hold for r in _frame_refs(f))))
            result.append(event);hold=[]
            if target is not None:
                break
            target=event
    return tuple(result)


def _return_path(frame, fixture_hash):
    packet=frame.integrity.get('return_path')
    if packet is None:
        return False
    proof=decode_record('CapabilityProof',encode_record(packet))
    if (not isinstance(proof,CapabilityProof) or proof.kind!='RETURN_PATH'
            or proof.method!='bounded-return-corridor-v1' or proof.status!='CORROBORATED'
            or proof.uncertainty is None or not 0<=proof.uncertainty<=Fraction(1,20)
            or not proof.raw_refs or any(r.frame!=frame.frame or r.time!=frame.simtime for r in proof.raw_refs)):
        return False
    limits=proof.limits
    if set(limits)!={'fixture_hash','actors_hash','frame','minimum_clearance_m'}:
        return False
    clearance=limits['minimum_clearance_m']
    if (isinstance(clearance,bool) or not isinstance(clearance,(int,Fraction))
            or clearance-proof.uncertainty<Fraction(1,5)
            or limits['fixture_hash']!=fixture_hash or limits['actors_hash']!=_digest(frame.actors)
            or limits['frame']!=frame.frame):
        return False
    binding={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
    return _review_binds(proof.review,_digest(binding),('CAPABILITY:RETURN_PATH',))


def _speed(velocity):
    if len(velocity)!=3 or any(isinstance(v,bool) or not isinstance(v,(float,int,Fraction)) or not isfinite(v) for v in velocity):
        return None
    square=sum(Fraction(v)**2 for v in velocity)
    root=sqrt(square)
    return Fraction(root) if isfinite(root) else None


def _map_offset(pose, packet, reference):
    if (not isinstance(packet,Mapping) or set(packet)!={'method','route','normals','refs'}
            or packet['method']!='segment-map-normal-v1' or not packet['refs']
            or reference!='map:'+_digest(packet)):
        return None
    route=decode_record('DirectedRoute',encode_record(packet['route']))
    if not isinstance(route,DirectedRoute):
        return None
    point=(pose.x,pose.y,pose.z);station=_metric_station(point,route)
    if station is None:
        return None
    normals=packet['normals']
    if not isinstance(normals,tuple) or len(normals)!=len(route.arc)-1:
        return None
    values=[];directions=[]
    for i,(a,b) in enumerate(zip(route.arc,route.arc[1:])):
        if not a<=station<=b:
            continue
        normal=normals[i];length=_speed(normal)
        if length is None or not length:
            return None
        first,last=route.transforms[i:i+2]
        start=tuple(Fraction(v) for v in (first.x,first.y,first.z))
        delta=tuple(Fraction(v)-p for v,p in zip((last.x,last.y,last.z),start))
        n=tuple(Fraction(v)/length for v in normal)
        if sum(v*d for v,d in zip(n,delta))!=0:
            return None  # unsupported inconsistent map normal, not a tuned epsilon
        u=(station-a)/(b-a)
        projected=tuple(v+u*d for v,d in zip(start,delta))
        values.append(abs(sum((Fraction(v)-q)*d for v,q,d in zip(point,projected,n))))
        directions.append(n)
    # At a corner there must be one well-defined pinned normal, not a nearest-edge tie break.
    if not values or len(set(directions))!=1 or len(set(values))!=1:
        return None
    return values[0]


def _metric_station(point,route):
    station=project_route(point,route)
    if isinstance(station,BlockedFixture):
        return None
    if station in (route.arc[0],route.arc[-1]):
        start=station==route.arc[0]
        first,last=route.transforms[:2] if start else route.transforms[-2:]
        endpoint=first if start else last
        delta=tuple(Fraction(b)-Fraction(a) for a,b in zip((first.x,first.y,first.z),(last.x,last.y,last.z)))
        dot=sum((Fraction(p)-Fraction(o))*d for p,o,d in zip(point,(endpoint.x,endpoint.y,endpoint.z),delta))
        if (start and dot<0) or (not start and dot>0):
            return None
    return station


def _route_observation(frame,context,reference,estimator):
    packet=context.get('directed_route')
    if packet is None:
        return None
    route=decode_record('DirectedRoute',encode_record(packet))
    if not isinstance(route,DirectedRoute) or reference!='route:'+_digest(route):
        return None
    actors={a.role:a for a in frame.actors}
    if len(actors)!=len(frame.actors):
        return None
    roles=('EGO','NPC') if estimator.endswith('_gap') else ('EGO',)
    for role in roles:
        if role not in actors or actors[role].route_valid is not True:
            return None
    if len(roles)==1:
        actor=actors['EGO']
        station=_metric_station((actor.pose.x,actor.pose.y,actor.pose.z),route)
        if station is None:
            return None
        if actor.arc is not None and (isinstance(actor.arc,bool) or actor.arc!=station):
            return None
        return station
    extrema={}
    for role in roles:
        actor=actors[role]
        stations=tuple(_metric_station(v,route) for v in world_vertices(actor.body,actor.pose))
        if any(s is None for s in stations):
            return None
        extrema[role]=(min(stations),max(stations))
    if estimator=='min_front_gap':
        return extrema['NPC'][0]-extrema['EGO'][1]
    return extrema['EGO'][0]-extrema['NPC'][1]


def measure(frames: tuple[FrameRecord,...], pair: FrozenMetricPair,
            events: tuple[EventRecord,...]) -> tuple[MetricValue,...]:
    """Measure declared windows, distinguishing missing events from lost witnesses."""
    results=[];valid_frames=_contiguous(frames) and all(_frame_refs(f) for f in frames)
    by_frame={f.frame:f for f in frames}
    ephemeral={'LANE_CHANGE_PATH_CLEAR','RETURN_PATH_CLEAR','DOOR_CLOSED_CLEAR_CURRENT','QUEUE_CLEAR_CONFIRMED'}
    endpoints=tuple(e for e in events if e.name not in ephemeral)
    by_name={e.name:e for e in endpoints}
    valid_events=(len(by_name)==len(endpoints) and 'WITNESS_UNKNOWN' not in by_name
                  and len({(e.name,e.frame,e.time) for e in events})==len(events)
                  and not any(name in ephemeral for window in pair.window for name in window))
    for event in events:
        f=by_frame.get(event.frame)
        if (f is None or event.time!=f.simtime or not event.witness_refs
                or not any(r.frame==event.frame and r.time==event.time for r in event.witness_refs)
                or any(r.frame is None or r.time is None or r.frame>event.frame or r.time>event.time for r in event.witness_refs)):
            valid_events=False
    for name,unit,estimator,window in zip(pair.names,pair.units,pair.estimators,pair.window):
        value=None;uncertainty=None;used=();status='UNKNOWN'
        if valid_frames and valid_events:
            start,end=(by_name.get(k) for k in window)
            if start is None or end is None:
                status='INCOMPLETE'
            elif start.frame<=end.frame and start.time<=end.time:
                selected=tuple(f for f in frames if start.frame<=f.frame<=end.frame)
                contexts=[f.integrity.get('metric_context') for f in selected]
                context_ok=all(isinstance(c,Mapping) and c.get('reference')==pair.reference
                               and c.get('pair_hash')==pair.hash and isinstance(c.get('uncertainty'),Mapping)
                               for c in contexts)
                errors=[c['uncertainty'].get(name) for c in contexts] if context_ok else []
                if (errors and all(not isinstance(e,bool) and isinstance(e,(int,Fraction)) and e>=0 for e in errors)
                        and all(_frame_refs(f) for f in selected)):
                    if estimator=='elapsed' and unit=='s':
                        value=end.time-start.time
                    elif estimator in ('forward_distance','reverse_distance','min_front_gap','min_rear_gap') and unit=='m':
                        observations=[_route_observation(f,c,pair.reference,estimator) for f,c in zip(selected,contexts)]
                        if all(v is not None for v in observations):
                            if estimator.endswith('_gap'):
                                value=min(observations)
                            else:
                                sign=1 if estimator=='forward_distance' else -1
                                value=sum((max(Fraction(0),sign*(b-a)) for a,b in zip(observations,observations[1:])),Fraction(0))
                    elif estimator=='peak_decel_025' and unit=='m/s^2':
                        windows=_decel_windows(selected,'EGO')
                        if windows:
                            value=max(Fraction(0),max(v for _,v in windows))
                    elif estimator in ('mean_speed','map_lateral_peak'):
                        ego=[tuple(a for a in f.actors if a.role=='EGO') for f in selected]
                        if all(len(a)==1 and a[0].route_valid is True for a in ego):
                            if estimator=='mean_speed' and unit=='m/s' and end.time>start.time:
                                speeds=[_speed(a[0].velocity) for a in ego]
                                if all(v is not None for v in speeds):
                                    value=sum(( (a+b)*(g.simtime-f.simtime)/2
                                              for a,b,f,g in zip(speeds,speeds[1:],selected,selected[1:])),Fraction(0))/(end.time-start.time)
                            elif estimator=='map_lateral_peak' and unit=='m':
                                offsets=[_map_offset(a[0].pose,c.get('map_reference'),pair.reference)
                                         for a,c in zip(ego,contexts)]
                                if all(v is not None for v in offsets):
                                    value=max(offsets)
                    if value is not None:
                        status='FAILED' if estimator in ('min_front_gap','min_rear_gap') and value<0 else 'VALID'
                        used=tuple(f.frame for f in selected);uncertainty=max(errors)
        results.append(MetricValue(name,value,unit,window,pair.reference,estimator,used,uncertainty,status))
    return tuple(results)
