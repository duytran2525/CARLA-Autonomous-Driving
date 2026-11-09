"""Pure frozen-response arithmetic; no stock/native imports or runtime authority."""
from collections.abc import Mapping

from .model import (FrozenResponse, Number, FrameRecord, ScriptState, ResponseState,
                    CommandRecord, ControlPacket, EventRecord, SourceRef)
from math import sqrt, isfinite
from dataclasses import replace
from .model import StockDriver, PolicyBundle, DirectedRoute


class _StockSession:
    """One adapter/writer; failed attempts consume their issuing frame."""
    def __init__(self, backend):
        self.backend=backend
        self.last_frame=None
        self.reference_phase=None


def _stock_factory(actor: object, config: dict[str,object]) -> object:
    # T12 supplies an admitted materialization boundary. No accidental native
    # import, world query, waypoint fabrication, or hidden global factory here.
    raise RuntimeError('BLOCKED_NATIVE_ADMISSION: stock factory not attached')


def create_stock_driver(actor: object, response: FrozenResponse, policies: PolicyBundle) -> StockDriver:
    """Verify and configure the admitted constructor boundary; never apply controls."""
    from .catalog import _digest,_review_binds
    from .evidence import _source_bytes
    from .model import ReviewRecord
    binding=policies.event_specs.get('stock_binding')
    keys={'response_hash','response_record_hash','route_hash','actor_id','source_refs','plan','client_version','server_version','review'}
    if not isinstance(binding,Mapping) or not keys.issubset(binding) or set(binding)-keys-{'phase_plans','fixture_ref','npc_longitudinal','ego_longitudinal'}:
        raise ValueError('STOCK_BINDING_MISSING')
    packet={k:v for k,v in binding.items() if k!='review'};review=binding['review']
    if (response.route is None or binding['response_hash']!=response.hash or binding['response_record_hash']!=_digest(response)
            or binding['route_hash']!=_digest(response.route)
            or type(binding['actor_id']) is not int or binding['actor_id']!=getattr(actor,'id',None)
            or binding['client_version']!='0.9.16' or binding['server_version']!='0.9.16'
            or not isinstance(binding['plan'],tuple) or not binding['plan'] or not binding['source_refs']
            or not isinstance(review,ReviewRecord) or not _review_binds(review,_digest(packet),('STOCK_FORWARD_BINDING',))
            or any(r not in policies.receipt_refs or r not in review.refs or _source_bytes(r) is None for r in binding['source_refs'])
            or any(_source_bytes(r) is None for r in (*review.refs,review.authority_ref))):
        raise ValueError('STOCK_BINDING_INVALID')
    desired_offset(Number(0),response);program=_program(response)
    _reference_response(response,program['initial'])  # Validate every future switch before constructor effects.
    switches=response.phases.get('reference_switches',());phase_plans=binding.get('phase_plans',{})
    moving=any(s['start_offset_m']!=s['end_offset_m'] for s in response.profile['segments'])
    if moving or switches:
        from .evidence import _decode_source_record
        from .model import CompiledFixture
        ref=binding.get('fixture_ref')
        if ref is None:
            raise ValueError('STOCK_LATERAL_FIXTURE_MISSING')
        fixture=_decode_source_record('CompiledFixture',ref) if isinstance(ref,SourceRef) else None
        if (not isinstance(fixture,CompiledFixture) or ref not in policies.receipt_refs or ref not in review.refs
                or not any(_digest(r)==_digest(response) for r in fixture.responses)):
            raise ValueError('STOCK_LATERAL_FIXTURE_INVALID')
        _lateral_contract(response,fixture)
    if (not isinstance(phase_plans,Mapping) or set(phase_plans)!={s['cause'] for s in switches}
            or any(not isinstance(p,tuple) or not p for p in phase_plans.values())):
        raise ValueError('STOCK_SWITCH_PLAN_MISSING')
    ego=response.actor_role=='EGO'
    if not ego and response.actor_role!='NPC':
        raise ValueError('STOCK_ROLE_INVALID')
    opt={'dt':.05,'lateral_control_dict':{'K_P':1.95,'K_I':.05,'K_D':.2,'dt':.05},
         'longitudinal_control_dict':_longitudinal(binding,ego),
         'max_throttle':.75,'max_brake':.3,'max_steering':.8,'follow_speed_limits':False}
    if ego:
        opt.update(ignore_traffic_lights=True,ignore_stop_signs=True,ignore_vehicles=True)
    config={'backend':'BasicAgent' if ego else 'LocalPlanner','opt_dict':opt,'actor_id':binding['actor_id'],
            'response_hash':response.hash,'route_hash':binding['route_hash'],'policy_hash':policies.hash,
            'source_refs':binding['source_refs'],'plan':binding['plan'],'phase_plans':phase_plans,'response':response}
    digest=_digest(config);backend=_stock_factory(actor,config)
    backend.set_global_plan(binding['plan'],stop_waypoint_creation=True,clean_queue=True)
    backend.follow_speed_limits(False)
    return StockDriver(_StockSession(backend),config,digest)


def _longitudinal(binding,ego):
    """v5 P-NPC (prereg eda7680): an NPC may carry reviewed longitudinal gains 'npc_longitudinal' (calibration grid).
    v5 erratum 2 (2d27616): an EGO may carry 'ego_longitudinal' only where the stock PID is not steady. OLD RULE (spec
    6.1): the EGO always keeps the pinned stock PID. Absent key = stock gains; a key of the other role is invalid."""
    own,other=('ego_longitudinal','npc_longitudinal') if ego else ('npc_longitudinal','ego_longitudinal')
    gains=binding.get(own)
    if other in binding:
        raise ValueError('STOCK_BINDING_INVALID')
    if gains is None:
        return {'K_P':1.,'K_I':.05,'K_D':0.,'dt':.05}
    if (not isinstance(gains,Mapping) or set(gains)!={'K_P','K_I','K_D','dt'}
            or any(isinstance(v,bool) or not isinstance(v,Number) for v in gains.values())
            or gains['dt']!=Number(1,20) or not gains['K_P']>0 or gains['K_I']<0 or gains['K_D']<0):
        raise ValueError('STOCK_BINDING_INVALID')
    return {k:float(v) for k,v in gains.items()}


def _f32(limit):
    """CARLA VehicleControl fields are float32: a control at exactly a configured limit reads back as the limit's
    float32 image (native 2026-10-22: steer clamp 0.8 -> 0.800000011920929). Bounds compare against that image."""
    import struct
    return struct.unpack('<f',struct.pack('<f',limit))[0]


_DRIVER_HASH_OK = {}


def _driver_hash_ok(driver):
    """_digest(driver.config) == driver.hash. A StockDriver is a frozen model record whose config is deep-frozen at
    construction (model._freeze: a fresh MappingProxyType nobody else holds), so the answer cannot change for the same
    driver object: memoized by identity with a strong reference (perf 2026-10-25: re-encoding the config with its
    response route every tick was ~60% of the native tick loop). ponytail: bounded clear-all cache."""
    from .catalog import _digest
    hit=_DRIVER_HASH_OK.get(id(driver))
    if hit is not None and hit[0] is driver:
        return hit[1]
    if len(_DRIVER_HASH_OK)>256:
        _DRIVER_HASH_OK.clear()
    ok=_digest(driver.config)==driver.hash
    _DRIVER_HASH_OK[id(driver)]=(driver,ok)
    return ok


def apply_intent(driver: StockDriver, intent: CommandRecord) -> CommandRecord:
    """Compute a stock forward control; application/tick/readback belong to runtime.

    No clipping, brake-one rescue, negative target, reverse, or same-frame retry.
    """
    if not isinstance(driver.handle,_StockSession) or not _driver_hash_ok(driver):
        raise ValueError('STOCK_DRIVER_INVALID')
    session=driver.handle;config=driver.config
    if (intent.kind!='CONTROL' or type(intent.frame) is not int or intent.next_frame!=intent.frame+1
            or intent.actor!=config['actor_id'] or intent.response_hash!=config['response_hash']
            or not isinstance(intent.target_kmh,Number) or intent.target_kmh<0 or not isinstance(intent.offset,Number)):
        raise ValueError('STOCK_INTENT_INVALID')
    if session.last_frame is not None and intent.frame!=session.last_frame+1:
        raise ValueError('COMMAND_ORDER')
    response=config['response']
    if intent.cause!='NPC_TRAFFIC_HOLD' and (intent.cause not in response.targets or intent.target_kmh!=response.targets[intent.cause]*Number(18,5)):
        raise ValueError('STOCK_TARGET_MISMATCH')
    if intent.cause=='NPC_TRAFFIC_HOLD' and (response.actor_role!='NPC' or intent.target_kmh!=0):
        raise ValueError('STOCK_TARGET_MISMATCH')
    session.last_frame=intent.frame
    phases=(_program(response)['initial'],*(t['cause'] for t in _program(response)['transitions']))
    if intent.cause in phases:
        active=[s for s in response.phases.get('reference_switches',()) if phases.index(s['cause'])<=phases.index(intent.cause)]
        active_cause=active[-1]['cause'] if active else None
        if session.reference_phase is not None and (active_cause is None or phases.index(active_cause)<phases.index(session.reference_phase)):
            raise ValueError('REFERENCE_SWITCH_REVERSED')
        if active_cause!=session.reference_phase:
            if intent.cause==active_cause and intent.offset!=0:
                raise ValueError('REFERENCE_SWITCH_OFFSET_NOT_RESET')
            session.backend.set_global_plan(config['phase_plans'][active_cause],stop_waypoint_creation=True,clean_queue=True)
            session.reference_phase=active_cause
    setter=session.backend.set_target_speed if config['backend']=='BasicAgent' else session.backend.set_speed
    setter(float(intent.target_kmh));session.backend.set_offset(float(intent.offset))
    raw=intent.control if intent.control is not None else session.backend.run_step()
    try:
        fields=('throttle','steer','brake','hand_brake','reverse','manual_gear_shift','gear')
        control=ControlPacket(*(getattr(raw,k) for k in fields))
        if (any(type(v) not in (int,float) or not isfinite(v) for v in (control.throttle,control.steer,control.brake))
                or not 0<=control.throttle<=_f32(.75) or not 0<=control.brake<=_f32(.3) or not -_f32(.8)<=control.steer<=_f32(.8)
                or any(type(v) is not bool for v in (control.hand_brake,control.reverse,control.manual_gear_shift))
                or control.hand_brake or control.reverse or control.manual_gear_shift
                or type(control.gear) is not int or control.gear<0):
            raise ValueError('fields')
    except (AttributeError,TypeError,ValueError):
        raise ValueError('STOCK_CONTROL_INVALID') from None
    if intent.control is None and intent.target_kmh>0 and control.brake>0:
        # v6 e (prereg PREREG_M56_V6_20261026, probe native-yield-probe.py): below 1.4 m/s any CARLA brake collapses the
        # speed to ~0 within one tick; with a moving target the stock brake is replaced by coasting there.
        vehicle=getattr(session.backend,'_vehicle',None)
        speed=vehicle.get_velocity().length() if vehicle is not None else None
        if speed is not None and speed<LOW_SPEED_BRAKE_CUTOFF_MPS:
            control=replace(control,brake=0.)
    return replace(intent,control=control)


LOW_SPEED_BRAKE_CUTOFF_MPS=1.4


def _program(response):
    program=response.phases.get('program')
    if (not isinstance(program,Mapping) or set(program)!={'method','initial','transitions'}
            or program['method']!='ordered-event-program-v1' or not isinstance(program['initial'],str)
            or program['initial'] not in response.targets or not isinstance(program['transitions'],tuple)):
        raise ValueError('PHASE_PROGRAM_INVALID')
    names={program['initial']}
    for row in program['transitions']:
        if (not isinstance(row,Mapping) or set(row)!={'cause','after_event','delay_s','requires'}
                or not isinstance(row['cause'],str) or row['cause'] in names or row['cause'] not in response.targets
                or not isinstance(row['after_event'],str) or not row['after_event']
                or not isinstance(row['delay_s'],Number) or row['delay_s']<0
                or not isinstance(row['requires'],tuple) or any(not isinstance(s,str) or not s for s in row['requires'])):
            raise ValueError('PHASE_PROGRAM_INVALID')
        names.add(row['cause'])
    return program


def _advance_program(frame, state, response, observations):
    """One deterministic phase transition using only available issuing-frame events.

    Path clearance is an ephemeral observation, not a latched episode event. A
    whole-trace verifier and the online producer use exactly this same function.
    """
    program=_program(response);names=(program['initial'],*(r['cause'] for r in program['transitions']))
    if state.phase not in names or state.start>frame.simtime:
        raise ValueError('PHASE_STATE_INVALID')
    ephemeral={'LANE_CHANGE_PATH_CLEAR','RETURN_PATH_CLEAR','DOOR_CLOSED_CLEAR_CURRENT','QUEUE_CLEAR_CONFIRMED'};known={}
    for event in observations:
        if event.frame>frame.frame or event.time>frame.simtime:
            continue
        if event.name in ephemeral and (event.frame,event.time)!=(frame.frame,frame.simtime):
            continue
        old=known.get(event.name)
        if old is None or (event.frame,event.time)<(old.frame,old.time):
            known[event.name]=event
    phase=state.phase;start=state.start;index=names.index(phase)
    if index<len(program['transitions']):
        row=program['transitions'][index];anchor=known.get(row['after_event'])
        if anchor is not None and frame.simtime-anchor.time>=row['delay_s'] and all(g in known for g in row['requires']):
            phase=row['cause'];start=frame.simtime
    return ScriptState(phase,start,tuple(known.values()))


_REFERENCE_CACHE={}


def _reference_response(response, cause):
    """_reference_response_uncached memoized by (response identity, cause): a frozen response gives the same reference
    or the same ValueError. Perf 2026-10-27 (M56 O03): validating the two CARLA-route switches (_switch_real_v5, O(n*m)
    projection) took ~1.4 s per call and step_response calls it every tick. ponytail: bounded clear-all cache."""
    key=(id(response),cause);hit=_REFERENCE_CACHE.get(key)
    if hit is None or hit[0] is not response:
        try:
            hit=(response,_reference_response_uncached(response,cause),None)
        except ValueError as exc:
            hit=(response,None,str(exc))
        if len(_REFERENCE_CACHE)>256:
            _REFERENCE_CACHE.clear()
        _REFERENCE_CACHE[key]=hit
    if hit[2] is not None:
        raise ValueError(hit[2])
    return hit[1]


def _reference_response_uncached(response, cause):
    """Resolve frozen phase references; only analytically continuous parallel plans.

    Curved/banked switches require a separately qualified recipe and are blocked,
    not approximated by a discontinuous waypoint jump. Original metric reference
    remains response.route. Both source/profile and switched route are immutable.
    """
    switches=response.phases.get('reference_switches',())
    if not isinstance(switches,tuple):
        raise ValueError('REFERENCE_SWITCH_INVALID')
    program=_program(response);phases=(program['initial'],*(r['cause'] for r in program['transitions']))
    if cause not in phases:
        raise ValueError('PHASE_STATE_INVALID')
    effective=response;selected=response;last_index=-1
    for row in switches:
        new=row.get('route') if isinstance(row,Mapping) else None
        if isinstance(new,Mapping):
            # Nested Any-mappings survive source-record decoding. Reify only the
            # declared strict schema; no waypoint fabrication or geometry waiver.
            from .model import decode_record,encode_record
            new=decode_record('DirectedRoute',encode_record(new))
        if (not isinstance(row,Mapping) or set(row)!={'cause','event','marker_arc_m','route','profile'}
                or row['cause'] not in phases or phases.index(row['cause'])<=last_index
                or row['event'] not in ('TARGET_LANE_CONFIRMED','RETURN_LANE_CONFIRMED','NPC_TARGET_LANE_CONFIRMED')
                or not isinstance(row['marker_arc_m'],Number) or not isinstance(new,DirectedRoute)):
            raise ValueError('REFERENCE_SWITCH_INVALID')
        index=phases.index(row['cause']);last_index=index
        if index==0 or row['event'] not in (program['transitions'][index-1]['after_event'],*program['transitions'][index-1]['requires']):
            raise ValueError('REFERENCE_SWITCH_GUARD_MISSING')
        old=effective.route
        if old is None:
            raise ValueError('REFERENCE_SWITCH_UNSUPPORTED')
        axis=len(old.transforms)==2 and len(new.transforms)==2
        if axis:
            if old.arc!=new.arc or old.map_hash!=new.map_hash or not _axis_route(old) or not _axis_route(new):
                raise ValueError('REFERENCE_SWITCH_UNSUPPORTED')
            if any((a.x,a.z)!=(b.x,b.z) for a,b in zip(old.transforms,new.transforms)):
                raise ValueError('REFERENCE_SWITCH_DISCONTINUOUS')
        marker=row['marker_arc_m'];segments=effective.profile.get('segments',())
        if (not segments or marker<segments[-1]['start_arc_m']+segments[-1]['length_m']
                or not old.arc[0]<=marker<=old.arc[-1]):
            raise ValueError('REFERENCE_SWITCH_BEFORE_PROFILE_END')
        old_offset=desired_offset(marker,effective)
        if not axis:
            _switch_real_v5(old,new,marker,old_offset)
        effective=replace(response,route=new,profile=row['profile'])
        new_offset=desired_offset(marker,effective)
        if (new_offset!=0 or effective.profile['segments'][0]['start_offset_m']!=0
                or (axis and Number(old.transforms[0].y)+old_offset!=Number(new.transforms[0].y))):
            raise ValueError('REFERENCE_SWITCH_DISCONTINUOUS')
        if index<=phases.index(cause):
            selected=effective
    return selected


def _f_script_contract(response):
    """Fixed common NPC scripts; never runtime actor/frame/Ego-action conditional."""
    from .catalog import _digest
    script=response.phases.get('f_script')
    if isinstance(script,Mapping) and script.get('mechanism') in ('F01','F02','F03','F04','F05'):
        if (set(script)!={'mechanism','policy_hash'} or response.actor_role!='NPC'
                or response.action_id!='NPC_COMMON' or response.phases.get('category')!='F'
                or not isinstance(script['policy_hash'],str) or len(script['policy_hash'])!=64
                or any(c not in '0123456789abcdef' for c in script['policy_hash'])):
            raise ValueError('F_SCRIPT_POLICY_INVALID')
        packet={k:getattr(response,k) for k in ('actor_role','action_id','route','targets','profile','phases')}
        if _digest(packet)!=response.hash:
            raise ValueError('F_SCRIPT_HASH_INVALID')
        program=_program(response);rows=program['transitions'];initial=response.targets[program['initial']]
        if script['mechanism']=='F04':
            door=response.phases.get('door')
            if (set(response.phases)-{'category','f_script','program','door','stock_binding'}
                    or not isinstance(door,Mapping) or set(door)!={'method','selector'}
                    or door['method']!='owned-door-request-v1' or not isinstance(door['selector'],str)
                    or not door['selector'] or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-' for c in door['selector'])
                    or program['initial']!='NPC_DOOR_CLOSED_HOLD'
                    or dict(response.targets)!={'NPC_DOOR_CLOSED_HOLD':Number(0),'NPC_DOOR_OPEN':Number(0),'NPC_DOOR_CLOSED':Number(0)}
                    or len(rows)!=2
                    or rows!=({'cause':'NPC_DOOR_OPEN','after_event':'CAPTURE_START','delay_s':rows[0]['delay_s'],'requires':()},
                             {'cause':'NPC_DOOR_CLOSED','after_event':'TRIGGER','delay_s':Number(3),'requires':()})):
                raise ValueError('F_SCRIPT_POLICY_INVALID')
        elif script['mechanism']=='F03':
            brake_row={'cause':'F03_BRAKE','after_event':'TRIGGER','delay_s':Number(2),'requires':()}
            # Pre-release hold (2026-10-20, F04-staging style, operator-delegated design): brake-held until
            # CAPTURE_START + a frozen positive delay, then the unchanged coast/brake rule.
            held=(program['initial']=='NPC_HOLD' and len(rows)==2
                  and rows[0]=={'cause':'UNPOWERED','after_event':'CAPTURE_START','delay_s':rows[0]['delay_s'],'requires':()}
                  and isinstance(rows[0]['delay_s'],Number) and rows[0]['delay_s']>0 and rows[1]==brake_row
                  and dict(response.targets)=={'NPC_HOLD':Number(0),'UNPOWERED':Number(0),'F03_BRAKE':Number(0)})
            legacy=(program['initial']=='UNPOWERED' and rows==(brake_row,)
                    and dict(response.targets)=={'UNPOWERED':Number(0),'F03_BRAKE':Number(0)})
            if response.phases.get('brake')!='F03_BRAKE' or not (held or legacy):
                raise ValueError('F_SCRIPT_POLICY_INVALID')
        elif script['mechanism']=='F05':
            if (program['initial']!='NPC_QUEUE_HOLD'
                    or dict(response.targets)!={'NPC_QUEUE_HOLD':Number(0),'NPC_QUEUE_FORWARD':Number(2)}
                    or rows!=({'cause':'NPC_QUEUE_FORWARD','after_event':'TRIGGER','delay_s':Number(3),'requires':()},)):
                raise ValueError('F_SCRIPT_POLICY_INVALID')
        else:
            # m56-v13 (A-SEL2 F prereg part 1, 3fb9865): the F01 NPC nominal is one of the two approved inputs, 3 m/s
            # (spec 8.1) or 17/5 m/s (A-SEL2 ladder); F02 keeps 5. The same value must hold for NOMINAL and NPC_RESTART.
            allowed=(Number(3),Number(17,5)) if script['mechanism']=='F01' else (Number(5),)
            nominal=(response.targets[rows[0]['cause']] if initial==0 and rows and rows[0]['after_event']=='CAPTURE_START'
                     else initial)
            if nominal not in allowed:
                raise ValueError('F_SCRIPT_POLICY_INVALID')
            if initial==0 and rows and rows[0]['after_event']=='CAPTURE_START':
                if response.targets[rows[0]['cause']]!=nominal or rows[0]['requires']:
                    raise ValueError('F_SCRIPT_POLICY_INVALID')
                rows=rows[1:]
            elif initial!=nominal:
                raise ValueError('F_SCRIPT_POLICY_INVALID')
            if script['mechanism']=='F01':
                if (response.phases.get('brake')!='F01_BRAKE' or len(rows)!=2
                        or rows[0]!={'cause':'F01_BRAKE','after_event':'F01_BRAKE_MARKER','delay_s':Number(0),'requires':()}
                        or response.targets['F01_BRAKE']!=0
                        or rows[1]['after_event']!='NPC_F01_STOP_HOLD_CONFIRMED' or rows[1]['delay_s']!=0
                        or rows[1]['requires'] or response.targets[rows[1]['cause']]!=nominal):
                    raise ValueError('F_SCRIPT_POLICY_INVALID')
            elif rows:
                raise ValueError('F_SCRIPT_POLICY_INVALID')
        desired_offset(Number(0),response)
        if (response.phases.get('reference_switches')
                or any(s['start_offset_m']!=0 or s['end_offset_m']!=0 for s in response.profile['segments'])):
            raise ValueError('F_SCRIPT_POLICY_INVALID')
        return
    keys={'mechanism','policy_hash','release_mode','release_s','reverse_distance_m','target_mps'}
    if (not isinstance(script,Mapping) or set(script)!=keys or response.actor_role!='NPC'
            or response.action_id!='NPC_COMMON' or script['mechanism']!='F06-ALT1'
            or script['release_mode']!='FIXED_OBSERVED_CUE' or script['release_s']!=Number(3)
            or script['reverse_distance_m']!=Number(2) or script['target_mps']!=Number(1,2)
            or not isinstance(script['policy_hash'],str) or len(script['policy_hash'])!=64
            or any(c not in '0123456789abcdef' for c in script['policy_hash'])):
        raise ValueError('F_SCRIPT_POLICY_INVALID')
    if ('preparation' in response.phases and response.phases['preparation']!={
            'method':'owned-reverse-preparation-v1','request_kind':'REVERSE_PREPARATION_REQUEST'}):
        raise ValueError('F_SCRIPT_POLICY_INVALID')
    packet={'actor_role':response.actor_role,'action_id':response.action_id,'route':response.route,
            'targets':response.targets,'profile':response.profile,'phases':response.phases}
    if _digest(packet)!=response.hash:
        raise ValueError('F_SCRIPT_HASH_INVALID')
    program=_program(response);rows=program['transitions']
    if (program['initial']!='NPC_PREPARATION' or len(rows)!=4
            or rows[0]!={'cause':'NPC_REVERSE_TARGET','after_event':'TRIGGER','delay_s':Number(3),'requires':()}
            or rows[1]!={'cause':'NPC_STOPPING','after_event':'NPC_REVERSE_STOPPING_BOUND','delay_s':Number(0),'requires':()}
            or rows[2]!={'cause':'NPC_FORWARD_GEAR','after_event':'NPC_REVERSE_STOP_CONFIRMED','delay_s':Number(0),'requires':()}
            or rows[3]!={'cause':'NPC_FORWARD','after_event':'NPC_FORWARD_GEAR_CONFIRMED','delay_s':Number(0),'requires':()}
            or dict(response.targets)!={'NPC_PREPARATION':Number(0),'NPC_REVERSE_TARGET':Number(1,2),
                                       'NPC_STOPPING':Number(0),'NPC_FORWARD_GEAR':Number(0),'NPC_FORWARD':Number(2)}):
        raise ValueError('F_SCRIPT_POLICY_INVALID')


def _blocked_response(frame,state,response,phase,reason):
    actor=next((a for a in frame.actors if a.role==response.actor_role),None)
    observed=actor.readback if actor is not None else None
    control=(replace(observed,throttle=0.,steer=0.,brake=.3,hand_brake=False) if observed is not None else None)
    command=CommandRecord(actor.id if actor is not None else 0,frame.frame,frame.frame+1,'BLOCKED',Number(0),Number(0),
                          control,None,reason,response.hash)
    return ResponseState(command,ScriptState(phase,frame.simtime,state.events))


def step_response(frame: FrameRecord, state: ScriptState, response: FrozenResponse) -> ResponseState:
    """Pure forward intent from authenticated events; no tick, stock or actor side effect.

    Event provenance is checked by the evidence/runtime boundary; this producer
    also rejects future/unbound/conflicting observations and unsupported scripts.
    Reverse actions remain a separate bounded controller (T11), never negative km/h.
    """
    if frame.dt!=Number(1,20) or state.start>frame.simtime:
        raise ValueError('RESPONSE_CLOCK_INVALID')
    if 'f_script' in response.phases:
        try:
            _f_script_contract(response)
        except ValueError as exc:
            return _blocked_response(frame,state,response,'BLOCKED_POLICY',str(exc))
    program=_program(response);names=(program['initial'],*(r['cause'] for r in program['transitions']))
    if state.phase not in names:
        raise ValueError('PHASE_STATE_INVALID')
    actors=tuple(a for a in frame.actors if a.role==response.actor_role)
    if len(actors)!=1 or actors[0].route_valid is not True:
        raise ValueError('RESPONSE_ACTOR_UNKNOWN')
    actor=actors[0];events={}
    for event in (*state.events,*frame.events):
        if (not isinstance(event,EventRecord) or event.frame>frame.frame or event.time>frame.simtime
                or not event.witness_refs or any(not isinstance(r,SourceRef) for r in event.witness_refs)
                or not any((r.frame,r.time)==(event.frame,event.time) for r in event.witness_refs)
                or (event.name in events and events[event.name]!=event and not (
                    event.name in ('LANE_CHANGE_PATH_CLEAR','RETURN_PATH_CLEAR','DOOR_CLOSED_CLEAR_CURRENT','QUEUE_CLEAR_CONFIRMED')
                    and events[event.name].frame<event.frame and events[event.name].time<event.time))):
            raise ValueError('RESPONSE_EVENT_INVALID')
        events[event.name]=event
    advanced=_advance_program(frame,state,response,tuple(events.values()))
    phase=advanced.phase;start=advanced.start
    target=response.targets.get(phase)
    if not isinstance(target,Number) or target<0:
        raise ValueError('TARGET_PROGRAM_INVALID')
    category=response.phases.get('category');control=None;cause=phase
    speed=sqrt(sum(v*v for v in actor.velocity))
    if not isfinite(speed):
        raise ValueError('ACTION_SPEED_UNKNOWN')
    if (response.actor_role=='EGO' and category=='F' and response.action_id=='B' and 'TRIGGER' in events
            and any(row['after_event']=='EGO_CREEP_STOPPING_BOUND' for row in program['transitions'])):
        _creep_guard(frame,ScriptState(phase,start,tuple(events.values())),response,target)
    if response.actor_role=='EGO' and category in ('C','L','M'):
        if response.action_id=='A' and phase=='RESUME' and not {'STOP_AFTER_TRIGGER','CLEAR_N_CONFIRMED'}.issubset(events):
            raise ValueError('STOP_AND_CLEAR_REQUIRED')
        if response.action_id=='B' and 'TRIGGER' in events and 'CLEAR_N_CONFIRMED' not in events and speed<.5:
            raise ValueError('CONTINUOUS_YIELD_SPEED_FLOOR')
    if (response.actor_role=='EGO' and category=='F' and response.action_id=='A' and target>0
            and 'TRIGGER' in events and any(row['after_event']=='DOOR_CLOSED_CLEAR_CONFIRMED' for row in program['transitions'])):
        current=events.get('DOOR_CLOSED_CLEAR_CURRENT')
        if current is None or (current.frame,current.time)!=(frame.frame,frame.simtime):
            raise ValueError('DOOR_CLEARANCE_STALE')
    if response.actor_role=='NPC':
        traffic=frame.integrity.get('npc_controls')
        if (not isinstance(traffic,Mapping) or set(traffic)!={'boot','world','frame','actor_id','status','witness_refs'}
                or (traffic['boot'],traffic['world'],traffic['frame'],traffic['actor_id'])!=(frame.boot,frame.world,frame.frame,actor.id)
                or not traffic['witness_refs'] or any(not isinstance(r,SourceRef) or (r.frame,r.time)!=(frame.frame,frame.simtime)
                                                   for r in traffic['witness_refs'])):
            raise ValueError('NPC_CONTROL_WITNESS_MISSING')
        if traffic['status']!='CLEAR':
            target=Number(0);cause='NPC_TRAFFIC_HOLD'
            control=ControlPacket(0.,0.,.3,False,False,False,1)
    from .metrics import _metric_station
    reference=_reference_response(response,phase)
    if reference.route is None:
        raise ValueError('RESPONSE_ROUTE_MISSING')
    arc=_metric_station((actor.pose.x,actor.pose.y,actor.pose.z),reference.route)
    if arc is None:
        raise ValueError('RESPONSE_PROJECTION_UNKNOWN')
    names=(program['initial'],*(r['cause'] for r in program['transitions']))
    for switch in response.phases.get('reference_switches',()):
        if names.index(switch['cause'])<=names.index(phase):
            if switch['event'] not in events:
                raise ValueError('REFERENCE_SWITCH_GUARD_MISSING')
            if arc<switch['marker_arc_m']:
                raise ValueError('REFERENCE_SWITCH_BEFORE_MARKER')
    offset=desired_offset(arc,reference)
    if response.actor_role=='EGO' and offset!=0:
        if (category,response.action_id)==('I','B'):
            if not {'TRIGGER','SOURCE_CLEAR_CONFIRMED','LANE_CHANGE_PATH_CLEAR'}.issubset(events):
                raise ValueError('LANE_CHANGE_GUARD_MISSING')
            onset=events.get('LANE_CHANGE_ONSET')
            if (onset.time if onset else frame.simtime)-events['TRIGGER'].time>4:
                raise ValueError('SOURCE_CLEAR_WAIT_EXCEEDED')
            if events['LANE_CHANGE_PATH_CLEAR'].frame!=frame.frame:
                raise ValueError('LANE_CHANGE_PATH_STALE')
        elif (category,response.action_id)==('O','A'):
            segments=response.profile['segments']
            # A target-plan switch can put the return in a single future segment.
            # Moving toward the initial centre still needs independent return
            # permission; a valid outbound path cannot authorize that motion.
            separation=_lateral_separation(reference.route,response.route)
            returning=(len(segments)>1 and arc>segments[1]['start_arc_m']) or offset*separation<0
            if returning:
                if not {'TRIGGER','RETURN_MARKER','RETURN_CLEAR_CONFIRMED','RETURN_PATH_CLEAR'}.issubset(events):
                    raise ValueError('RETURN_GUARD_MISSING')
                if events['RETURN_PATH_CLEAR'].frame!=frame.frame:
                    raise ValueError('RETURN_PATH_STALE')
            else:
                if not {'TRIGGER','LANE_CHANGE_PATH_CLEAR'}.issubset(events):
                    raise ValueError('LANE_CHANGE_GUARD_MISSING')
                if events['LANE_CHANGE_PATH_CLEAR'].frame!=frame.frame:
                    raise ValueError('LANE_CHANGE_PATH_STALE')
        elif category=='F':
            segments=response.profile['segments']
            if response.action_id!='B' or len(segments)!=2:
                raise ValueError('UNPLANNED_LANE_CHANGE')
            returning=arc>=segments[1]['start_arc_m']
            if returning:
                if not {'TRIGGER','F04_END','F04_OFFSET_CONFIRMED','F04_RETURN_MARKER','RETURN_PATH_CLEAR'}.issubset(events):
                    raise ValueError('WITHIN_LANE_RETURN_GUARD_MISSING')
                if events['RETURN_PATH_CLEAR'].frame!=frame.frame:
                    raise ValueError('RETURN_PATH_STALE')
            else:
                if not {'TRIGGER','LANE_CHANGE_PATH_CLEAR'}.issubset(events):
                    raise ValueError('WITHIN_LANE_PASS_GUARD_MISSING')
                if events['LANE_CHANGE_PATH_CLEAR'].frame!=frame.frame:
                    raise ValueError('LANE_CHANGE_PATH_STALE')
        elif category in ('I','O'):
            raise ValueError('UNPLANNED_LANE_CHANGE')
    kind='CONTROL'
    if response.actor_role=='NPC' and response.phases.get('f_script',{}).get('mechanism')=='F04':
        observed=actor.readback
        if (observed is None or observed.reverse is not False or observed.manual_gear_shift is not False
                or type(observed.gear) is not int or observed.gear<0 or observed.steer!=0
                or observed.hand_brake is not False):
            raise ValueError('PARKED_DOOR_READBACK_UNPROVEN')
        if speed>Number(1,10):
            raise ValueError('PARKED_DOOR_ACTOR_NOT_STOPPED')
        # Opaque, frozen owned-panel selector remains in the response hash.
        # Emit a request ONCE at entry, never an actor API call, stock PID door
        # substitute, observed articulation or native capability assertion.
        control=replace(observed,throttle=0.,steer=0.,brake=.3,hand_brake=False)
        # Priority still holds the motor at zero; it cannot consume or retime
        # the separately frozen stationary door operation (especially closure).
        cause=phase
        if phase!=state.phase:
            if phase=='NPC_DOOR_OPEN':kind='DOOR_OPEN_REQUEST'
            elif phase=='NPC_DOOR_CLOSED':kind='DOOR_CLOSE_REQUEST'
    if response.actor_role=='NPC' and response.phases.get('f_script',{}).get('mechanism')=='F03':
        observed=actor.readback
        if (observed is None or observed.reverse or type(observed.gear) is not int or observed.gear<0):
            raise ValueError('UNPOWERED_ROLLBACK_GEAR_REQUIRED')
        if control is None:
            # A zero stock target would brake immediately and erase rollback.
            # The admitted recipe coasts without motor torque; no velocity,
            # gravity, reverse-drive or physical-motion override is invented.
            control=replace(observed,throttle=0.,steer=0.,brake=0. if phase=='UNPOWERED' else .3,hand_brake=False)
    if response.actor_role=='NPC' and response.phases.get('f_script',{}).get('mechanism')=='F06-ALT1':
        if phase=='NPC_PREPARATION' and 'TRIGGER' not in events:
            observed=actor.readback
            if (observed is None or observed.reverse is not False or observed.manual_gear_shift is not False
                    or type(observed.gear) is not int or observed.gear<0 or observed.steer!=0 or observed.hand_brake is not False):
                raise ValueError('OBSERVED_PREPARATION_GEAR_REQUIRED')
            # Waiting for a separately owned gear request is not the observed
            # preparation cue and cannot start the fixed three-second clock.
            control=replace(observed,throttle=0.,steer=0.,brake=.3,hand_brake=False)
        elif phase in ('NPC_PREPARATION','NPC_STOPPING'):
            if actor.readback is None or not actor.readback.reverse or not actor.readback.manual_gear_shift or actor.readback.gear!=-1:
                raise ValueError('OBSERVED_PREPARATION_GEAR_REQUIRED')
            kind='REVERSE_HOLD';control=ControlPacket(0.,0.,.3,False,True,True,-1)
        elif phase=='NPC_REVERSE_TARGET':
            # T11 bounded controller must materialize this request using its
            # frozen stopping/rear-zone/capability proofs. Never stock PID.
            kind='REVERSE_REQUEST';control=None
    if target==0 and control is None:
        control=ControlPacket(0.,0.,.3,False,False,False,1)
    command=CommandRecord(actor.id,frame.frame,frame.frame+1,kind,target*Number(18,5),offset,control,None,cause,response.hash)
    return ResponseState(command,ScriptState(phase,start,tuple(events.values())))


def _reverse_recipe_hash(fixture):
    from .catalog import _digest
    return _digest({k:getattr(fixture,k) for k in ('candidate_hash','policy_hash','actors','environment','routes','domain','sections')})


def _reverse_body_hash(body):
    from .catalog import _digest
    return _digest({k:getattr(body,k) for k in ('bbox_offset','rotation','extents','blueprint','attrs','physics')})


# Frozen reverse stop-bound laws. v1 is the approved law, unchanged. v2 (D3, 2026-10-22) was set after the native
# capability probes A2/A3/A4 (vehicle.audi.a2 stalls at the v1 cap 1/4 in reverse), and before any A/B; it is chosen
# only by the fixture's proof method, never inferred.
REVERSE_LAWS={'bounded-reverse-stop-v1':{'target_mps':Number(1,2),'gain':Number(1,2),'throttle_cap':Number(1,4),
                                          'brake_cap':Number(3,10),'terminal_brake':Number(3,10)},
              'bounded-reverse-stop-v2':{'target_mps':Number(1,2),'hold_throttle':Number(29,100),'gain':Number(1,5),
                                          'throttle_cap':Number(2,5),'brake_cap':Number(3,10),'terminal_brake':Number(3,10)}}


def _v13_exact_x_alignment(route,pose):
    """OLD RULE (v13, reported in parallel): 2-point +x route, constant y/z, zero rotation of route and pose."""
    return not (route is None or len(route.transforms)!=2 or route.transforms[0].x>=route.transforms[1].x
                or route.transforms[0].y!=route.transforms[1].y or route.transforms[0].z!=route.transforms[1].z
                or any((t.pitch,t.yaw,t.roll)!=(0.,0.,0.) for t in route.transforms)
                or (pose.pitch,pose.yaw,pose.roll)!=(0.,0.,0.))


V14_YAW_DEG,V14_TILT_DEG,V14_LATERAL_M=1.,.5,Number(3,20)


def _v14_axis_route(route):
    """v14 (docs/m56/PLAN_M56_F_REVERSE_CREEP_V14_20261109.md 2.1): a straight world-axis route: >= 2 points, every
    yaw within 1 deg of the same axis direction (_axis_right), strictly monotone along that axis."""
    if route is None or len(route.transforms)<2:
        return None
    axes={_axis_right(t.yaw) for t in route.transforms}
    if len(axes)!=1 or None in axes:
        return None
    lat,_=next(iter(axes));trv=1-lat
    steps=[(b.x,b.y)[trv]-(a.x,a.y)[trv] for a,b in zip(route.transforms,route.transforms[1:])]
    if not (all(s>0 for s in steps) or all(s<0 for s in steps)):
        return None
    return lat,trv


def _v14_aligned(route,pose,spawn):
    """v14 2.1-2.3: pose yaw on the route's axis direction (1 deg), pitch/roll within 0.5 deg of the frozen spawn pose,
    lateral distance to the route polyline <= 0.15 m. v13 exact-zero poses satisfy it on a v13 route."""
    from math import hypot
    from .metrics import _metric_station
    axis=_v14_axis_route(route)
    if axis is None or spawn is None or _axis_right(pose.yaw)!=_axis_right(route.transforms[0].yaw):
        return False
    wrap=lambda a,b:abs(((a-b+180.)%360.)-180.)
    if wrap(pose.pitch,spawn.pitch)>V14_TILT_DEG or wrap(pose.roll,spawn.roll)>V14_TILT_DEG:
        return False
    station=_metric_station((pose.x,pose.y,pose.z),route)
    if station is None:
        return False
    for i,(a,b) in enumerate(zip(route.arc,route.arc[1:])):
        if a<=station<=b:
            s,e=route.transforms[i],route.transforms[i+1];u=float((station-a)/(b-a)) if b>a else 0.
            return hypot(pose.x-(s.x+u*(e.x-s.x)),pose.y-(s.y+u*(e.y-s.y)))<=float(V14_LATERAL_M)
    return False


def _reverse_capability(proof,kind,method):
    from .model import CapabilityProof
    from .catalog import _digest,_review_binds
    from .evidence import _source_bytes,_payload
    if (not isinstance(proof,CapabilityProof) or proof.kind!=kind or proof.method!=method
            or proof.status!='CORROBORATED' or not isinstance(proof.uncertainty,Number)
            or not 0<=proof.uncertainty<=Number(1,20) or not proof.raw_refs or proof.review is None):
        return False
    packet={k:getattr(proof,k) for k in ('kind','method','raw_refs','uncertainty','limits','status')}
    refs=(*proof.raw_refs,*proof.review.refs,proof.review.authority_ref)
    return (_review_binds(proof.review,_digest(packet),('CAPABILITY:'+kind,))
            and all(isinstance(r,SourceRef) and _source_bytes(r) is not None for r in refs)
            and all(r in proof.review.refs for r in proof.raw_refs)
            and any(_source_bytes(r)==_payload(proof.limits) for r in proof.raw_refs))


def _reverse_ground(frame,actor,fixture):
    import json
    from .catalog import _digest
    from .evidence import _source_bytes
    from .model import decode_record,encode_record
    proof=actor.ground;method='recorded-ground-contact-v1'
    if not _reverse_capability(proof,'GROUND:'+actor.role,method):
        raise ValueError('REVERSE_GROUND_UNPROVEN')
    limits=proof.limits;recipe_ref=limits.get('recipe_ref')
    if isinstance(recipe_ref,Mapping):
        recipe_ref=decode_record('SourceRef',encode_record(recipe_ref))
    expected={'fixture_hash':_digest(fixture),'boot':frame.boot,'world':frame.world,'frame':frame.frame,
        'actor_id':actor.id,'body_pose_hash':_digest({'body':actor.body,'pose':actor.pose}),'contact_method':method}
    if (set(limits)!=set(expected)|{'maximum_ground_error_m','recipe_ref'} or any(limits[k]!=v for k,v in expected.items())
            or not isinstance(limits['maximum_ground_error_m'],Number) or limits['maximum_ground_error_m']<0
            or limits['maximum_ground_error_m']+proof.uncertainty>Number(1,20)
            or not isinstance(recipe_ref,SourceRef) or recipe_ref not in proof.review.refs
            or any((r.frame,r.time)!=(frame.frame,frame.simtime) for r in proof.raw_refs)):
        raise ValueError('REVERSE_GROUND_UNPROVEN')
    raw=_source_bytes(recipe_ref)
    try:recipe=json.loads(raw) if raw is not None else None
    except (ValueError,TypeError,UnicodeError):recipe=None
    if (not isinstance(recipe,dict) or recipe.get('method')!=method or not recipe.get('version') or not recipe.get('limitations')):
        raise ValueError('REVERSE_GROUND_RECIPE_UNPROVEN')


def _reverse_inputs(frame,response,fixture,forward=False):
    """Source-bound calibration, observed history and current reserved corridor."""
    from .catalog import _digest
    from .evidence import _read_trajectory,_source_bytes,_payload
    from .model import decode_record,encode_record
    from .geometry import _is_box,world_vertices
    from .metrics import _metric_station,_contiguous,_frame_refs
    mechanism=fixture.domain.topology.get('mechanism');role=response.actor_role
    ego=role=='EGO' and response.action_id=='B' and mechanism in ('F03','F06-ALT1')
    npc=role=='NPC' and response.action_id=='NPC_COMMON' and mechanism=='F06-ALT1'
    if not (ego or npc):
        raise ValueError('REVERSE_ACTION_UNSUPPORTED')
    if npc:_f_script_contract(response)
    else:_ego_reverse_contract(response,fixture)
    metadata=response.phases.get('f_script' if npc else 'reverse')
    if (not isinstance(metadata,Mapping) or (ego and set(metadata)!={'mechanism','policy_hash'})
            or metadata['mechanism']!=mechanism or metadata['policy_hash']!=fixture.policy_hash
            or not any(_digest(r)==_digest(response) for r in fixture.responses)):
        raise ValueError('REVERSE_POLICY_UNBOUND')
    actors=tuple(a for a in frame.actors if a.role==role)
    if len(actors)!=1 or actors[0].route_valid is not True:
        raise ValueError('REVERSE_ACTOR_UNKNOWN')
    actor=actors[0];route=response.route;recipe=_reverse_recipe_hash(fixture)
    spawn=fixture.poses.get(role) if isinstance(fixture.poses,Mapping) else None
    if not _v14_aligned(route,actor.pose,spawn):  # v14; OLD RULE _v13_exact_x_alignment
        raise ValueError('REVERSE_ALIGNMENT_UNSUPPORTED')
    proofs=tuple(p for p in fixture.proofs if p.kind=='REVERSE_STOP_BOUND' and p.limits.get('actor_role')==role)
    if (len(proofs)!=1 or proofs[0].method not in REVERSE_LAWS
            or not _reverse_capability(proofs[0],'REVERSE_STOP_BOUND',proofs[0].method)):
        raise ValueError('REVERSE_STOP_BOUND_MISSING')
    proof=proofs[0];limits=proof.limits;hard=Number(2 if mechanism=='F03' or npc else 1)
    expected={'actor_role':role,'response_hash':response.hash,'route_hash':_digest(route),'body_hash':_reverse_body_hash(actor.body),
              'fixture_recipe_hash':recipe,**REVERSE_LAWS[proof.method],'hard_limit_m':hard}
    extra={'stopping_boundary_m','stopping_distance_bound_m','maximum_reverse_speed_mps'}
    if (set(limits)!=set(expected)|extra or any(limits[k]!=v for k,v in expected.items())
            or any(not isinstance(limits[k],Number) for k in extra)
            or not 0<limits['stopping_boundary_m']<hard or limits['stopping_distance_bound_m']<=0
            or limits['stopping_boundary_m']+limits['stopping_distance_bound_m']+proof.uncertainty>hard
            or limits['maximum_reverse_speed_mps']<Number(1,2)):
        raise ValueError('REVERSE_STOP_BOUND_INVALID')
    _reverse_ground(frame,actor,fixture)
    history_ref=frame.integrity.get('reverse_history_ref')
    if isinstance(history_ref,Mapping):
        history_ref=decode_record('SourceRef',encode_record(history_ref))
    history=_read_trajectory(history_ref)
    if (history is None or len(history)>1532 or not _contiguous(history)
            or (history[-1].boot,history[-1].world,history[-1].frame,history[-1].simtime)!=(frame.boot,frame.world,frame.frame,frame.simtime)
            or _digest(history[-1].actors)!=_digest(frame.actors)):
        raise ValueError('REVERSE_HISTORY_UNBOUND')
    for observed in history:
        own=tuple(a for a in observed.actors if a.role==role)
        refs=_frame_refs(observed)
        payload=_payload({'boot':observed.boot,'world':observed.world,'frame':observed.frame,
                          'simtime':observed.simtime,'actors':observed.actors})
        if (len(own)!=1 or own[0].id!=actor.id or own[0].route_valid is not True
                or _reverse_body_hash(own[0].body)!=_reverse_body_hash(actor.body)
                or not _v14_aligned(route,own[0].pose,spawn)
                or not refs or not any(_source_bytes(r)==payload for r in refs)):
            raise ValueError('REVERSE_HISTORY_OBSERVATION_UNBOUND')
    if forward:
        return actor,history,proof
    corridors=frame.integrity.get('reverse_corridors')
    if 'reverse_corridors' in frame.integrity:
        if (not isinstance(corridors,Mapping) or set(corridors)-{'EGO','NPC'}
                or 'reverse_corridor' in frame.integrity):
            raise ValueError('REVERSE_REAR_ZONE_UNPROVEN')
        corridor=corridors.get(role)
    else:
        corridor=frame.integrity.get('reverse_corridor')
    regions=fixture.domain.topology.get('reverse_regions',{})
    if isinstance(corridor,Mapping):
        corridor=decode_record('CapabilityProof',encode_record(corridor))
    region=regions.get(role)
    if not _is_box(region) or not _reverse_capability(corridor,'REVERSE_CORRIDOR','bounded-reverse-corridor-v1'):
        raise ValueError('REVERSE_REAR_ZONE_UNPROVEN')
    expected={'fixture_recipe_hash':recipe,'boot':frame.boot,'world':frame.world,'frame':frame.frame,'actor_id':actor.id,
              'actors_hash':_digest(frame.actors),'response_hash':response.hash,'region_hash':_digest(region)}
    if (set(corridor.limits)!=set(expected)|{'minimum_rear_clearance_m'}
            or any(corridor.limits[k]!=v for k,v in expected.items())
            or not isinstance(corridor.limits['minimum_rear_clearance_m'],Number)
            or corridor.limits['minimum_rear_clearance_m']-corridor.uncertainty<Number(1,5)):
        raise ValueError('REVERSE_REAR_ZONE_UNPROVEN')
    if any(not all(Number(min(p[k] for p in region))+corridor.uncertainty+(Number(3,20) if k<2 else 0)<=Number(v[k])<=
                       Number(max(p[k] for p in region))-corridor.uncertainty-(Number(3,20) if k<2 else 0)
                       for k in range(3)) for v in world_vertices(actor.body,actor.pose)):
        raise ValueError('REVERSE_CORRIDOR_BODY_UNPROVEN')
    return actor,history,proof


def _creep_stop_proof(fixture,response,actor):
    """Reviewed body/stock/recipe-bound forward stopping proposal, not calibration.

    The standard stock forward PID is unchanged. A brake command, target zero or
    the 1m hard marker alone is never a stopping-distance certificate.
    """
    from .catalog import _digest
    from .model import decode_record,encode_record
    if (fixture.domain.topology.get('mechanism')!='F05' or response.actor_role!='EGO' or response.action_id!='B'
            or not any(_digest(r)==_digest(response) for r in fixture.responses)):
        raise ValueError('CREEP_POLICY_UNBOUND')
    _forward_contract(response,fixture)
    route=response.route
    spawn=fixture.poses.get('EGO') if isinstance(fixture.poses,Mapping) else None
    if not _v14_aligned(route,actor.pose,spawn) or actor.route_valid is not True:  # v14; OLD RULE _v13_exact_x_alignment
        raise ValueError('CREEP_ALIGNMENT_UNSUPPORTED')
    proofs=tuple(decode_record('CapabilityProof',encode_record(p)) for p in fixture.proofs
                 if p.kind=='CREEP_STOP_BOUND' and p.limits.get('actor_role')=='EGO')
    if len(proofs)!=1 or not _reverse_capability(proofs[0],'CREEP_STOP_BOUND','bounded-forward-creep-stop-v1'):
        raise ValueError('CREEP_STOP_BOUND_MISSING')
    proof=proofs[0];limits=proof.limits
    stock={'lateral':{'K_P':Number(39,20),'K_I':Number(1,20),'K_D':Number(1,5)},
           'longitudinal':{'K_P':Number(1),'K_I':Number(1,20),'K_D':Number(0)},'dt_s':Number(1,20),
           'max_throttle':Number(3,4),'max_brake':Number(3,10),'max_steering':Number(4,5)}
    expected={'actor_role':'EGO','response_hash':response.hash,'route_hash':_digest(route),
        'body_hash':_reverse_body_hash(actor.body),'fixture_recipe_hash':_reverse_recipe_hash(fixture),
        'stock_config_hash':_digest(stock),'target_mps':Number(1,2),'terminal_brake':Number(3,10),'hard_limit_m':Number(1)}
    extra={'stopping_boundary_m','stopping_distance_bound_m','maximum_forward_speed_mps'}
    if (set(limits)!=set(expected)|extra or any(limits[k]!=v for k,v in expected.items())
            or any(not isinstance(limits[k],Number) for k in extra)
            or not 0<limits['stopping_boundary_m']<1 or limits['stopping_distance_bound_m']<=0
            or limits['stopping_boundary_m']+limits['stopping_distance_bound_m']+proof.uncertainty>1
            or limits['maximum_forward_speed_mps']<Number(1,2)):
        raise ValueError('CREEP_STOP_BOUND_INVALID')
    return proof


def _queue_path(frame,fixture,response):
    """Exact current independently reviewed queue corridor; no latched permission."""
    from .catalog import _digest
    from .model import decode_record,encode_record
    proof=frame.integrity.get('queue_path')
    if isinstance(proof,Mapping):proof=decode_record('CapabilityProof',encode_record(proof))
    actors=tuple(a for a in frame.actors if a.role=='EGO')
    if len(actors)!=1 or actors[0].route_valid is not True or not _reverse_capability(proof,'QUEUE_PATH','bounded-queue-exit-corridor-v1'):
        return None
    expected={'fixture_recipe_hash':_reverse_recipe_hash(fixture),'boot':frame.boot,'world':frame.world,'frame':frame.frame,
        'actor_id':actors[0].id,'actors_hash':_digest(frame.actors),'response_hash':response.hash,'route_hash':_digest(response.route)}
    clearance=proof.limits.get('minimum_forward_clearance_m')
    if (set(proof.limits)!=set(expected)|{'minimum_forward_clearance_m'} or any(proof.limits[k]!=v for k,v in expected.items())
            or not isinstance(clearance,Number) or clearance-proof.uncertainty<Number(1,5)
            or any((r.frame,r.time)!=(frame.frame,frame.simtime) for r in proof.raw_refs)):
        return None
    return proof


def _creep_guard(frame,state,response,target):
    """No stock-creep torque without exact current frozen/source admission.

    Runtime materialization is not implemented here. A local reviewed context
    must already exist; native stopping/ground/corridor qualification and sole
    owner authorization cannot be obtained by this pure arithmetic producer.
    """
    from .catalog import _digest
    from .model import decode_record,encode_record
    from .evidence import _read_trajectory,_decode_source_record,_source_bytes,_payload
    from .metrics import _contiguous,_frame_refs,_metric_station,detect_events,_route_observation
    fixture_ref=frame.integrity.get('creep_fixture_ref');history_ref=frame.integrity.get('creep_history_ref')
    if isinstance(fixture_ref,Mapping):fixture_ref=decode_record('SourceRef',encode_record(fixture_ref))
    if isinstance(history_ref,Mapping):history_ref=decode_record('SourceRef',encode_record(history_ref))
    if not isinstance(fixture_ref,SourceRef):raise ValueError('CREEP_FIXTURE_UNBOUND')
    fixture=_decode_source_record('CompiledFixture',fixture_ref)
    if fixture is None:raise ValueError('CREEP_FIXTURE_UNBOUND')
    actor=next((a for a in frame.actors if a.role=='EGO'),None)
    if actor is None:raise ValueError('CREEP_ACTOR_UNBOUND')
    proof=_creep_stop_proof(fixture,response,actor);history=_read_trajectory(history_ref)
    if (history is None or len(history)>1532 or not _contiguous(history)
            or (history[-1].boot,history[-1].world,history[-1].frame,history[-1].simtime)!=(frame.boot,frame.world,frame.frame,frame.simtime)
            or _digest(history[-1].actors)!=_digest(frame.actors)):
        raise ValueError('CREEP_HISTORY_UNBOUND')
    identity={a.role:(a.id,_reverse_body_hash(a.body)) for a in frame.actors}
    if set(identity)!={'EGO','NPC'} or len(set(a.id for a in frame.actors))!=2:
        raise ValueError('CREEP_ACTOR_UNBOUND')
    for observed in history:
        refs=_frame_refs(observed)
        packet={'boot':observed.boot,'world':observed.world,'frame':observed.frame,'simtime':observed.simtime,'actors':observed.actors}
        if ({a.role:(a.id,_reverse_body_hash(a.body)) for a in observed.actors}!=identity
                or any(a.route_valid is not True for a in observed.actors)
                or not refs or not any(_source_bytes(r)==_payload(packet) for r in refs)):
            raise ValueError('CREEP_HISTORY_OBSERVATION_UNBOUND')
    _reverse_ground(frame,actor,fixture)
    if _queue_path(frame,fixture,response) is None:raise ValueError('CREEP_CURRENT_CORRIDOR_UNPROVEN')
    observed=actor.readback
    if (observed is None or observed.reverse is not False or observed.manual_gear_shift is not False
            or type(observed.gear) is not int or observed.gear<0 or observed.steer!=0 or observed.hand_brake is not False):
        raise ValueError('CREEP_CONTROL_UNPROVEN')
    actual=detect_events(history,fixture)
    known={e.name:e for e in state.events}
    origin=next((e for e in actual if e.name=='TRIGGER'),None)
    if origin is None or 'TRIGGER' not in known or _digest(origin)!=_digest(known['TRIGGER']):
        raise ValueError('CREEP_ORIGIN_UNBOUND')
    if any(e.name=='WITNESS_UNKNOWN' for e in actual):raise ValueError('CREEP_HISTORY_UNPROVEN')
    release=next((e for e in actual if e.name=='N_MOVE'),None)
    stop=next((e for e in actual if e.name=='EGO_CREEP_STOP_CONFIRMED'),None)
    # Own calibrated creep remains bounded through the actual issuing release;
    # later verified stock-forward speed is NOT reverse/creep calibration.
    selected=tuple(f for f in history if origin.frame<=f.frame and (release is None or f.frame<=release.frame))
    progress=Number(0);previous=None
    for f in selected:
        a=next(a for a in f.actors if a.role=='EGO');station=_metric_station((a.pose.x,a.pose.y,a.pose.z),response.route)
        if station is None or not _v14_aligned(response.route,a.pose,fixture.poses.get('EGO')):  # v14
            raise ValueError('CREEP_ALIGNMENT_UNSUPPORTED')
        speed=sqrt(sum(v*v for v in a.velocity))
        if not isfinite(speed) or speed>proof.limits['maximum_forward_speed_mps']:
            raise ValueError('CREEP_SPEED_OUTSIDE_CALIBRATION')
        if previous is not None:
            step=station-previous
            if step<0:raise ValueError('CREEP_DIRECTION_INVALID')
            progress+=step
        if progress+proof.uncertainty>1:raise ValueError('CREEP_RESERVATION_EXCEEDED')
        previous=station
    gap=_route_observation(frame,{'directed_route':response.route},'route:'+_digest(response.route),'min_front_gap')
    if gap is None or gap<Number(1,5):raise ValueError('CREEP_CURRENT_GAP_UNPROVEN')
    if state.phase=='FORWARD':
        current=known.get('QUEUE_CLEAR_CONFIRMED')
        admitted_clear=next((e for e in actual if e.name=='QUEUE_CLEAR_CONFIRMED' and e.frame==frame.frame),None)
        if (release is None or stop is None or current is None or admitted_clear is None
                or _digest(current)!=_digest(admitted_clear)
                or any(name not in known or _digest(known[name])!=_digest(event)
                       for name,event in (('N_MOVE',release),('EGO_CREEP_STOP_CONFIRMED',stop)))):
            raise ValueError('CREEP_RELEASE_UNPROVEN')
    elif target>0 and (progress+proof.uncertainty+proof.limits['maximum_forward_speed_mps']*frame.dt
                      >=proof.limits['stopping_boundary_m']):
        raise ValueError('CREEP_STOPPING_BOUND_REQUIRED')


def _reverse_stop_tail(history,role,route):
    from .metrics import _speed,_metric_station
    tail=[];previous=None
    for f in reversed(history):
        actors=tuple(a for a in f.actors if a.role==role)
        if len(actors)!=1 or actors[0].route_valid is not True:
            break
        actor=actors[0];speed=_speed(actor.velocity)
        station=_metric_station((actor.pose.x,actor.pose.y,actor.pose.z),route)
        if speed is None or speed>Number(1,10) or station is None:
            break
        if previous is not None and abs(previous[1]-station)/(previous[0].simtime-f.simtime)>Number(1,10):
            break
        tail.append(f);previous=(f,station)
    return bool(tail) and tail[0].simtime-tail[-1].simtime>=Number(1,2)


def _reverse_priority(frame,actor,require_clear=True):
    """Exact current stock-priority source, including after reverse is over."""
    from .evidence import _source_bytes,_payload
    from .model import decode_record,encode_record
    traffic=frame.integrity.get('npc_controls')
    status=traffic.get('status') if isinstance(traffic,Mapping) else None
    expected={'boot':frame.boot,'world':frame.world,'frame':frame.frame,'actor_id':actor.id,'status':status}
    refs=traffic.get('witness_refs',()) if isinstance(traffic,Mapping) else ()
    refs=tuple(decode_record('SourceRef',encode_record(r)) if isinstance(r,Mapping) else r for r in refs)
    if (not isinstance(traffic,Mapping) or set(traffic)!=set(expected)|{'witness_refs'}
            or not isinstance(status,str) or not status or (require_clear and status!='CLEAR')
            or any(traffic[k]!=v for k,v in expected.items()) or not refs
            or any(not isinstance(r,SourceRef) or (r.frame,r.time)!=(frame.frame,frame.simtime)
                   or _source_bytes(r)!=_payload(expected) for r in refs)):
        raise ValueError('REVERSE_NPC_PRIORITY_UNPROVEN')
    return {**traffic,'witness_refs':refs}


def _reverse_peer_event(frame,state,fixture,history,before=None):
    """Authenticate peer STOP and re-detect the actual frozen mechanism endpoint."""
    from .evidence import _source_bytes,_payload
    from .metrics import _frame_refs,detect_events
    from .catalog import _digest
    cutoff=before or frame
    name='NPC_STOP_CONFIRMED' if fixture.domain.topology['mechanism']=='F03' else 'NPC_REVERSE_TARGET_STOP_CONFIRMED'
    events=tuple(e for e in (*state.events,*frame.events)
                 if e.name==name and e.frame<=cutoff.frame and e.time<=cutoff.simtime
                 and (before is None or (e.frame<cutoff.frame and e.time<cutoff.simtime)))
    if not events:return False
    if len({_digest(e) for e in events})!=1:
        raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
    event=events[0];prefix=tuple(f for f in history if f.frame<=event.frame)
    if (not prefix or (prefix[-1].frame,prefix[-1].simtime)!=(event.frame,event.time)
            or not event.witness_refs or not any((r.frame,r.time)==(event.frame,event.time) for r in event.witness_refs)):
        raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
    observed={(f.frame,f.simtime):f for f in prefix}
    for ref in event.witness_refs:
        if not isinstance(ref,SourceRef) or (ref.frame,ref.time) not in observed:
            raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
        f=observed[(ref.frame,ref.time)]
        if (ref not in _frame_refs(f) or _source_bytes(ref)!=_payload({'boot':f.boot,'world':f.world,
                'frame':f.frame,'simtime':f.simtime,'actors':f.actors})):
            raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
    origin=tuple(a for a in prefix[0].actors if a.role=='NPC')
    if len(origin)!=1:
        raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
    for f in prefix:
        peers=tuple(a for a in f.actors if a.role=='NPC')
        if (len(peers)!=1 or peers[0].id!=origin[0].id or peers[0].route_valid is not True
                or _reverse_body_hash(peers[0].body)!=_reverse_body_hash(origin[0].body)):
            raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
    if not _reverse_stop_tail(prefix,'NPC',fixture.routes['NPC']):
        raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
    actual=detect_events(prefix,fixture)
    endpoints=tuple(e for e in actual if e.name==name)
    triggers=tuple(e for e in actual if e.name=='TRIGGER')
    claimed=tuple(e for e in (*state.events,*frame.events) if e.name=='TRIGGER')
    if (any(e.name=='WITNESS_UNKNOWN' for e in actual) or len(endpoints)!=1 or len(triggers)!=1
            or _digest(endpoints[0])!=_digest(event) or not claimed
            or any(_digest(e)!=_digest(triggers[0]) for e in claimed)):
        raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
    return True


def _reverse_reservation_ready(history,fixture,trigger):
    """F06's actual 1m EGO reserve/STOP must precede the first NPC retreat."""
    from .metrics import _metric_station,_continuous_proof
    from .catalog import _digest
    peers=[];identity=None
    for frame in history:
        actors=tuple(a for a in frame.actors if a.role=='NPC')
        if len(actors)!=1 or actors[0].route_valid is not True:
            raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
        actor=actors[0];key=(actor.id,_reverse_body_hash(actor.body))
        if identity is not None and identity!=key:
            raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
        identity=key
        station=_metric_station((actor.pose.x,actor.pose.y,actor.pose.z),fixture.routes['NPC'])
        if station is None:
            raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
        peers.append(station)
    first=next((i+1 for i,(a,b) in enumerate(zip(peers,peers[1:]))
                if b<a and history[i+1].frame>trigger.frame),None)
    if first is None:
        return True  # No NPC motion yet; this is not permission to release the reserve.
    if _continuous_proof(history[first-1],history[first],_digest(fixture)) is None:
        raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
    prefix=tuple(f for f in history[:first] if f.frame>=trigger.frame)
    if not prefix or not _reverse_stop_tail(prefix,'EGO',fixture.routes['EGO']):
        return False
    positions=tuple(_metric_station((a.pose.x,a.pose.y,a.pose.z),fixture.routes['EGO'])
        for f in prefix for a in f.actors if a.role=='EGO')
    if len(positions)!=len(prefix) or any(p is None for p in positions):
        raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
    return positions[0]-positions[-1]>=1


def _reverse_forward(frame,state,response,fixture,actor,selected,positions,proof,history):
    """Authenticate the past exception; forward motion is not reverse calibration."""
    role=response.actor_role
    reverse_indices=tuple(i+1 for i,(a,b) in enumerate(zip(positions,positions[1:])) if b<a)
    if not reverse_indices:
        raise ValueError('REVERSE_FORWARD_HISTORY_UNPROVEN')
    last_reverse=reverse_indices[-1]
    retreat=sum((max(Number(0),a-b) for a,b in zip(positions,positions[1:])),Number(0))
    if retreat>proof.limits['hard_limit_m']:
        raise ValueError('REVERSE_RESERVATION_EXCEEDED')
    if fixture.domain.topology['mechanism']=='F06-ALT1' and retreat<Number(2 if role=='NPC' else 1):
        raise ValueError('REVERSE_RESERVATION_NOT_REACHED')
    gear_index=None
    for i in range(last_reverse+1,len(selected)):
        own=next(a for a in selected[i].actors if a.role==role);control=own.readback
        if control is not None and not control.reverse and not control.manual_gear_shift and control.gear>0:
            gear_index=i;break
    if gear_index is None or not _reverse_stop_tail(selected[:gear_index],role,response.route):
        raise ValueError('REVERSE_TERMINAL_GEAR_UNPROVEN')
    if any(b>a for a,b in zip(positions[:gear_index],positions[1:gear_index+1])):
        raise ValueError('REVERSE_RESERVATION_NOT_MAINTAINED')
    for f in selected[last_reverse:gear_index]:
        control=next(a for a in f.actors if a.role==role).readback
        if control is None or not control.reverse or not control.manual_gear_shift or control.gear!=-1 or control.steer!=0:
            raise ValueError('REVERSE_TERMINAL_CONTROL_UNPROVEN')
    for f in selected[gear_index:]:
        control=next(a for a in f.actors if a.role==role).readback
        if control is None or control.reverse or control.manual_gear_shift:
            raise ValueError('REVERSE_FORWARD_READBACK_UNPROVEN')
    if any(b<a for a,b in zip(positions[gear_index:],positions[gear_index+1:])):
        raise ValueError('REVERSE_FORWARD_DIRECTION_INVALID')
    if role=='EGO' and not _reverse_peer_event(frame,state,fixture,history,before=selected[gear_index]):
        raise ValueError('REVERSE_HAZARD_RESOLUTION_UNPROVEN')
    target=response.targets.get(state.phase)
    if not isinstance(target,Number) or target<=0:
        raise ValueError('REVERSE_FORWARD_TARGET_UNBOUND')
    if role=='NPC':
        traffic=_reverse_priority(frame,actor,require_clear=False)
        frame=replace(frame,integrity={**frame.integrity,'npc_controls':traffic})
    return step_response(frame,state,response)


def _reverse_preparation(frame,state,response,fixture,actor,history):
    """Opt-in owned gear request; only receiving observations can become a cue."""
    from .catalog import _digest
    from .model import decode_record,encode_record
    method='owned-reverse-preparation-v1';kind='REVERSE_PREPARATION_REQUEST'
    if (response.actor_role!='NPC' or state.phase!='NPC_PREPARATION'
            or response.phases.get('preparation')!={'method':method,'request_kind':kind}):
        raise ValueError('REVERSE_PREPARATION_UNPROVEN')
    proof=decode_record('CapabilityProof',encode_record(frame.integrity.get('preparation_request')))
    expected={'fixture_hash':_digest(fixture),'response_hash':response.hash,'boot':frame.boot,'world':frame.world,
              'frame':frame.frame,'actor_id':actor.id,'actors_hash':_digest(frame.actors)}
    if (not _reverse_capability(proof,kind,method) or proof.uncertainty!=0 or dict(proof.limits)!=expected
            or any((r.frame,r.time)!=(frame.frame,frame.simtime) for r in proof.raw_refs)
            or any(not _reverse_stop_tail(history,role,fixture.routes[role]) for role in ('EGO','NPC'))
            or actor.readback.reverse or actor.readback.manual_gear_shift or actor.readback.gear<0):
        raise ValueError('REVERSE_PREPARATION_UNPROVEN')
    _reverse_priority(frame,actor)
    control=ControlPacket(0.,0.,.3,False,True,True,-1)
    command=CommandRecord(actor.id,frame.frame,frame.frame+1,'GEAR_TRANSITION',Number(0),Number(0),control,None,
                          'NPC_PREPARATION',response.hash)
    return ResponseState(command,ScriptState('NPC_PREPARATION_REQUESTED',frame.simtime,state.events))


def reverse_intent(frame:FrameRecord,state:ScriptState,response:FrozenResponse,fixture) -> ResponseState:
    """Source-bound bounded reverse; never stock PID, actor mutation or native I/O."""
    try:
        if frame.dt!=Number(1,20) or state.start>frame.simtime:
            raise ValueError('REVERSE_CLOCK_INVALID')
        forward=state.phase==('NPC_FORWARD' if response.actor_role=='NPC' else 'FORWARD')
        actor,history,proof=_reverse_inputs(frame,response,fixture,forward=forward)
        if actor.readback is None or actor.readback.steer!=0 or actor.readback.hand_brake:
            raise ValueError('REVERSE_APPLIED_CONTROL_UNPROVEN')
        from .metrics import _metric_station,_speed
        from .evidence import _source_bytes
        triggers=tuple(e for e in (*state.events,*frame.events) if e.name=='TRIGGER' and e.frame<=frame.frame and e.time<=frame.simtime)
        if not triggers:
            if response.actor_role=='NPC' and 'preparation' in response.phases:
                return _reverse_preparation(frame,state,response,fixture,actor,history)
            raise ValueError('REVERSE_TRIGGER_MISSING')
        trigger=min(triggers,key=lambda e:(e.frame,e.time));selected=tuple(f for f in history if f.frame>=trigger.frame)
        if (not trigger.witness_refs or any(not isinstance(r,SourceRef) or r.frame is None or r.time is None
                or r.frame>trigger.frame or r.time>trigger.time or _source_bytes(r) is None for r in trigger.witness_refs)
                or not any((r.frame,r.time)==(trigger.frame,trigger.time) for r in trigger.witness_refs)):
            raise ValueError('REVERSE_TRIGGER_UNBOUND')
        if not selected or selected[0].frame!=trigger.frame:
            raise ValueError('REVERSE_ORIGIN_UNBOUND')
        positions=tuple(_metric_station((a.pose.x,a.pose.y,a.pose.z),response.route)
                        for f in selected for a in f.actors if a.role==response.actor_role)
        if any(p is None for p in positions) or len(positions)!=len(selected):
            raise ValueError('REVERSE_PROJECTION_UNKNOWN')
        if (response.actor_role=='EGO' and fixture.domain.topology['mechanism']=='F06-ALT1'
                and not _reverse_reservation_ready(history,fixture,trigger)):
            return _blocked_response(frame,state,response,'FAILED','RESERVATION_STOP_NOT_CONFIRMED')
        if forward:
            return _reverse_forward(frame,state,response,fixture,actor,selected,positions,proof,history)
        if any(b>a for a,b in zip(positions,positions[1:])):
            return _blocked_response(frame,state,response,'FAILED','REVERSE_RESERVATION_NOT_MAINTAINED')
        speed=_speed(actor.velocity)
        if speed is None or speed>proof.limits['maximum_reverse_speed_mps']:
            raise ValueError('REVERSE_SPEED_OUTSIDE_CALIBRATION')
        stopped=_reverse_stop_tail(history,response.actor_role,response.route)
        if not actor.readback or not actor.readback.reverse or not actor.readback.manual_gear_shift or actor.readback.gear!=-1:
            if not stopped:
                raise ValueError('REVERSE_STOP_REQUIRED_BEFORE_GEAR')
        retreat=sum((max(Number(0),a-b) for a,b in zip(positions,positions[1:])),Number(0))
        if retreat>proof.limits['hard_limit_m']:
            return _blocked_response(frame,state,response,'FAILED','REVERSE_RESERVATION_EXCEEDED')
        npc=response.actor_role=='NPC'
        if npc:
            _reverse_priority(frame,actor)
        if npc and frame.simtime-trigger.time<Number(3):
            if retreat>0 or speed>Number(1,10):
                return _blocked_response(frame,state,response,'FAILED','F06_PREPARATION_MOTION')
            control=ControlPacket(0.,0.,.3,False,actor.readback.reverse,actor.readback.manual_gear_shift,actor.readback.gear)
            command=CommandRecord(actor.id,frame.frame,frame.frame+1,'REVERSE_HOLD',Number(0),Number(0),control,None,'NPC_PREPARATION',response.hash)
            return ResponseState(command,ScriptState('NPC_PREPARATION',state.start,state.events))
        stopping=(state.phase in ('STOPPING','WAIT_FORWARD_GEAR','NPC_STOPPING','NPC_FORWARD_GEAR') or retreat+proof.uncertainty+
                  proof.limits['maximum_reverse_speed_mps']*frame.dt>=proof.limits['stopping_boundary_m'])
        resolved=npc or _reverse_peer_event(frame,state,fixture,history)
        if stopping and stopped and retreat>0 and resolved:
            if fixture.domain.topology['mechanism']=='F06-ALT1' and retreat<Number(2 if npc else 1):
                return _blocked_response(frame,state,response,'FAILED','REVERSE_RESERVATION_NOT_REACHED')
            observed=actor.readback
            gear_phase='NPC_FORWARD_GEAR' if npc else 'WAIT_FORWARD_GEAR'
            forward_phase='NPC_FORWARD' if npc else 'FORWARD'
            if (state.phase in (gear_phase,forward_phase) and observed is not None and not observed.reverse
                    and not observed.manual_gear_shift and observed.gear>0):
                target=response.targets.get(forward_phase)
                if not isinstance(target,Number) or target<=0:
                    raise ValueError('REVERSE_FORWARD_TARGET_UNBOUND')
                command=CommandRecord(actor.id,frame.frame,frame.frame+1,'CONTROL',target*Number(18,5),Number(0),None,None,forward_phase,response.hash)
                return ResponseState(command,ScriptState(forward_phase,state.start if state.phase==forward_phase else frame.simtime,state.events))
            control=ControlPacket(0.,0.,.3,False,False,False,1)
            cause='NPC_FORWARD_GEAR' if npc else 'FORWARD_GEAR'
            command=CommandRecord(actor.id,frame.frame,frame.frame+1,'GEAR_TRANSITION',Number(0),Number(0),control,None,cause,response.hash)
            return ResponseState(command,ScriptState(gear_phase,state.start if state.phase==gear_phase else frame.simtime,state.events))
        if stopping:
            control=ControlPacket(0.,0.,.3,False,True,True,-1)
            phase='NPC_STOPPING' if npc else 'STOPPING'
            command=CommandRecord(actor.id,frame.frame,frame.frame+1,'REVERSE',Number(0),Number(0),control,None,phase,response.hash)
            return ResponseState(command,ScriptState(phase,state.start if state.phase==phase else frame.simtime,state.events))
        law=REVERSE_LAWS[proof.method]  # v1: hold 0, gain 1/2, cap 1/4, i.e. exactly the approved regulator
        throttle=min(law['throttle_cap'],max(Number(0),law.get('hold_throttle',Number(0))+law['gain']*(law['target_mps']-speed)))
        brake=min(Number(3,10),max(Number(0),Number(1,2)*(speed-Number(1,2))))
        control=ControlPacket(float(throttle),0.,float(brake),False,True,True,-1)
        command=CommandRecord(actor.id,frame.frame,frame.frame+1,'REVERSE',Number(9,5),Number(0),control,None,'REVERSE',response.hash)
        if npc:command=replace(command,cause='NPC_REVERSE_TARGET')
        phase='NPC_REVERSE_TARGET' if npc else 'REVERSE'
        return ResponseState(command,ScriptState(phase,state.start if state.phase==phase else frame.simtime,state.events))
    except (ValueError,TypeError,KeyError,AttributeError,StopIteration) as exc:
        return _blocked_response(frame,state,response,'BLOCKED_CONTROLLER',str(exc))


def _ego_reverse_contract(response,fixture):
    """Approved bounded EGO exception; proposed forward speed stays frozen, not invented."""
    from .catalog import _digest
    mechanism=fixture.domain.topology.get('mechanism');metadata=response.phases.get('reverse')
    if (response.actor_role!='EGO' or response.action_id!='B' or response.phases.get('category')!='F'
            or mechanism not in ('F03','F06-ALT1') or not isinstance(metadata,Mapping)
            or set(metadata)!={'mechanism','policy_hash'} or metadata['mechanism']!=mechanism
            or metadata['policy_hash']!=fixture.policy_hash):
        raise ValueError('NORMATIVE_REVERSE_POLICY_UNBOUND')
    packet={k:getattr(response,k) for k in ('actor_role','action_id','route','targets','profile','phases')}
    if _digest(packet)!=response.hash:
        raise ValueError('NORMATIVE_REVERSE_HASH_INVALID')
    program=_program(response);rows=program['transitions']
    expected=(('REVERSE','TRIGGER'),('STOPPING','REVERSE_STOPPING_BOUND'),
              ('FORWARD_GEAR','REVERSE_STOP_CONFIRMED'),('FORWARD','FORWARD_GEAR_CONFIRMED'))
    if (program['initial']!='HOLD' or response.targets['HOLD']!=0 or len(rows)!=4
            or any(row!={'cause':cause,'after_event':event,'delay_s':Number(0),'requires':()}
                   for row,(cause,event) in zip(rows,expected))
            or response.targets['REVERSE']!=Number(1,2) or response.targets['STOPPING']!=0
            or response.targets['FORWARD_GEAR']!=0 or not isinstance(response.targets['FORWARD'],Number)
            or response.targets['FORWARD']<=0):
        raise ValueError('NORMATIVE_REVERSE_PROGRAM_INVALID')
    desired_offset(Number(0),response)
    if (response.phases.get('reference_switches')
            or any(s['start_offset_m']!=0 or s['end_offset_m']!=0 for s in response.profile['segments'])):
        raise ValueError('NORMATIVE_REVERSE_LATERAL_INVALID')


def _forward_contract(response,fixture):
    """Approved forward policy, independent of self-consistent command replay."""
    category=fixture.domain.topology.get('category')
    mechanism=fixture.domain.topology.get('mechanism')
    if category=='F' and mechanism in ('F03','F06-ALT1') and response.actor_role=='EGO' and response.action_id=='B':
        _ego_reverse_contract(response,fixture)
        return
    if category=='F' and mechanism in ('F03','F06-ALT1') and response.actor_role=='EGO' and response.action_id=='A':
        program=_program(response);rows=program['transitions']
        end='NPC_STOP_CONFIRMED' if mechanism=='F03' else 'NPC_REVERSE_TARGET_STOP_CONFIRMED'
        if (response.phases.get('category')!='F' or response.targets[program['initial']]!=0
                or (rows and (len(rows)!=1 or rows[0]['after_event']!=end or rows[0]['delay_s']!=0
                              or rows[0]['requires'] or response.targets[rows[0]['cause']]<=0))):
            raise ValueError('NORMATIVE_REVERSE_HOLD_POLICY_INVALID')
        desired_offset(Number(0),response)
        if (response.phases.get('reference_switches')
                or any(s['start_offset_m']!=0 or s['end_offset_m']!=0 for s in response.profile['segments'])):
            raise ValueError('NORMATIVE_REVERSE_HOLD_LATERAL_INVALID')
        return
    if category=='F' and mechanism=='F04' and response.actor_role=='EGO' and response.action_id=='A':
        program=_program(response);rows=program['transitions'];initial=response.targets[program['initial']]
        if initial==0 and rows and rows[0]['after_event']=='CAPTURE_START':
            if response.targets[rows[0]['cause']]!=Number(2) or rows[0]['requires']:
                raise ValueError('NORMATIVE_NOMINAL_INVALID')
            rows=rows[1:]
        elif initial!=Number(2):
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        if (response.phases.get('category')!='F' or len(rows)!=2
                or rows[0]['after_event']!='TRIGGER' or rows[0]['delay_s']!=0 or rows[0]['requires']
                or response.targets[rows[0]['cause']]!=0
                or rows[1]['after_event']!='DOOR_CLOSED_CLEAR_CONFIRMED' or rows[1]['delay_s']!=0
                or rows[1]['requires']!=('STOP_AFTER_TRIGGER',) or response.targets[rows[1]['cause']]!=Number(2)):
            raise ValueError('NORMATIVE_F04_WAIT_POLICY_INVALID')
        desired_offset(Number(0),response)
        if (response.phases.get('reference_switches')
                or any(s['start_offset_m']!=0 or s['end_offset_m']!=0 for s in response.profile['segments'])):
            raise ValueError('NORMATIVE_F04_WAIT_LATERAL_INVALID')
        return
    if category=='F' and mechanism=='F04' and response.actor_role=='EGO' and response.action_id=='B':
        program=_program(response);rows=program['transitions'];initial=response.targets[program['initial']]
        if initial==0 and rows and rows[0]['after_event']=='CAPTURE_START':
            if response.targets[rows[0]['cause']]!=Number(2) or rows[0]['requires']:
                raise ValueError('NORMATIVE_NOMINAL_INVALID')
            rows=rows[1:]
        elif initial!=Number(2):
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        if (response.phases.get('category')!='F' or len(rows)!=3
                or rows[0]['after_event']!='TRIGGER' or rows[0]['delay_s']!=0
                or rows[0]['requires']!=('LANE_CHANGE_PATH_CLEAR',) or response.targets[rows[0]['cause']]!=Number(1)
                or rows[1]['after_event']!='F04_RETURN_MARKER' or rows[1]['delay_s']!=0
                or rows[1]['requires']!=('F04_END','F04_OFFSET_CONFIRMED','RETURN_PATH_CLEAR') or response.targets[rows[1]['cause']]!=Number(1)
                or rows[2]['after_event']!='F04_HOME_CONFIRMED' or rows[2]['delay_s']!=0
                or rows[2]['requires']!=('F04_RETURN_REFERENCE_MARKER',) or response.targets[rows[2]['cause']]!=Number(2)):
            raise ValueError('NORMATIVE_F04_PASS_POLICY_INVALID')
        desired_offset(Number(0),response);segments=response.profile['segments']
        if (response.phases.get('reference_switches') or len(segments)!=2
                or segments[0]['length_m']!=Number(6) or segments[0]['start_offset_m']!=0
                or abs(segments[0]['end_offset_m'])!=Number(3,4)
                or segments[1]['start_offset_m']!=segments[0]['end_offset_m'] or segments[1]['end_offset_m']!=0):
            raise ValueError('NORMATIVE_F04_PASS_PROFILE_INVALID')
        return
    if category=='F' and mechanism=='F05' and response.actor_role=='EGO' and response.action_id=='A':
        program=_program(response);rows=program['transitions']
        if (response.phases.get('category')!='F' or program['initial']!='HOLD'
                or dict(response.targets)!={'HOLD':Number(0),'FORWARD':Number(2)}
                or rows!=({'cause':'FORWARD','after_event':'NPC_ADVANCE_2M_CONFIRMED','delay_s':Number(0),'requires':('TRIGGER',)},)):
            raise ValueError('NORMATIVE_F05_WAIT_POLICY_INVALID')
        desired_offset(Number(0),response)
        if (response.phases.get('reference_switches') or response.profile.get('offset',Number(0))!=0
                or any(s['start_offset_m']!=0 or s['end_offset_m']!=0 for s in response.profile['segments'])):
            raise ValueError('NORMATIVE_F05_WAIT_LATERAL_INVALID')
        return
    if category=='F' and mechanism=='F05' and response.actor_role=='EGO' and response.action_id=='B':
        program=_program(response)
        expected=(
            {'cause':'CREEP','after_event':'TRIGGER','delay_s':Number(0),'requires':()},
            {'cause':'CREEP_STOP','after_event':'EGO_CREEP_STOPPING_BOUND','delay_s':Number(0),'requires':()},
            {'cause':'FORWARD','after_event':'N_MOVE','delay_s':Number(0),
             'requires':('TRIGGER','EGO_CREEP_STOP_CONFIRMED','QUEUE_CLEAR_CONFIRMED')})
        if (response.phases.get('category')!='F' or program['initial']!='HOLD'
                or dict(response.targets)!={'HOLD':Number(0),'CREEP':Number(1,2),'CREEP_STOP':Number(0),'FORWARD':Number(2)}
                or program['transitions']!=expected):
            raise ValueError('NORMATIVE_F05_CREEP_POLICY_INVALID')
        desired_offset(Number(0),response)
        if (response.phases.get('reference_switches')
                or any(s['start_offset_m']!=0 or s['end_offset_m']!=0 for s in response.profile['segments'])):
            raise ValueError('NORMATIVE_F05_CREEP_LATERAL_INVALID')
        return
    if category=='F' and mechanism in ('F04','F05') and response.actor_role=='NPC':
        if 'f_script' not in response.phases:
            raise ValueError('NORMATIVE_F_SCRIPT_UNPROVEN')
        _f_script_contract(response)
        if (response.phases['f_script']['mechanism']!=mechanism
                or response.phases['f_script']['policy_hash']!=fixture.policy_hash):
            raise ValueError('NORMATIVE_F_SCRIPT_POLICY_UNBOUND')
        return
    if category=='F' and mechanism in ('F01','F02','F03'):
        if response.actor_role=='NPC':
            if 'f_script' not in response.phases:
                raise ValueError('NORMATIVE_F_SCRIPT_UNPROVEN')
            _f_script_contract(response)
            if (response.phases['f_script']['mechanism']!=mechanism
                    or response.phases['f_script']['policy_hash']!=fixture.policy_hash):
                raise ValueError('NORMATIVE_F_SCRIPT_POLICY_UNBOUND')
            return
        if response.actor_role!='EGO' or response.action_id not in ('A','B') or response.phases.get('category')!='F':
            raise ValueError('NORMATIVE_F_POLICY_INVALID')
        program=_program(response);rows=program['transitions'];initial=response.targets[program['initial']]
        if initial==0 and rows and rows[0]['after_event']=='CAPTURE_START':
            if response.targets[rows[0]['cause']]!=Number(4) or rows[0]['requires']:
                raise ValueError('NORMATIVE_NOMINAL_INVALID')
            rows=rows[1:]
        elif initial!=Number(4):
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        if mechanism=='F01':
            if (len(rows)!=2 or rows[0]['after_event']!='TRIGGER' or rows[0]['delay_s']!=0 or rows[0]['requires']
                    or response.targets[rows[0]['cause']]!=(0 if response.action_id=='A' else Number(2))
                    or rows[1]['after_event']!='N_MOVE' or rows[1]['delay_s']!=0
                    or rows[1]['requires']!=(('STOP_AFTER_TRIGGER',) if response.action_id=='A' else ())
                    or response.targets[rows[1]['cause']]!=Number(4)):
                raise ValueError('NORMATIVE_F01_POLICY_INVALID')
        elif not (not rows and response.action_id=='A'):
            if (len(rows)!=1 or rows[0]['after_event']!='TRIGGER' or rows[0]['delay_s']!=0 or rows[0]['requires']
                    or response.targets[rows[0]['cause']]!=(Number(4) if response.action_id=='A' else Number(11,2))):
                raise ValueError('NORMATIVE_F02_POLICY_INVALID')
        desired_offset(Number(0),response)
        if (response.phases.get('reference_switches')
                or any(s['start_offset_m']!=0 or s['end_offset_m']!=0 for s in response.profile['segments'])):
            raise ValueError('NORMATIVE_F_LATERAL_INVALID')
        return
    if response.actor_role=='NPC' and category=='F' and mechanism=='F06-ALT1':
        _f_script_contract(response)
        if response.phases['f_script']['policy_hash']!=fixture.policy_hash:
            raise ValueError('NORMATIVE_F_SCRIPT_POLICY_UNBOUND')
        return
    if response.actor_role=='EGO' and category=='O' and response.action_id=='A':
        program=_program(response);rows=program['transitions']
        nominal=_nominal_v5(response)
        if nominal is None:
            raise ValueError('NORMATIVE_NOMINAL_UNPROVEN')
        if not _io_nominal_ok(nominal):  # v9; OLD RULE v8: nominal not in (6, 15/2, 75/8)
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        initial=response.targets[program['initial']]
        if initial==0 and rows and rows[0]['after_event']=='CAPTURE_START':
            if response.targets[rows[0]['cause']]!=nominal:
                raise ValueError('NORMATIVE_NOMINAL_INVALID')
            rows=rows[1:]
        elif initial!=nominal:
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        if (len(rows)!=4 or any(row['delay_s']!=0 or response.targets[row['cause']]!=nominal for row in rows)
                or rows[0]['after_event']!='TRIGGER' or 'LANE_CHANGE_PATH_CLEAR' not in rows[0]['requires']
                or rows[1]['after_event']!='TARGET_LANE_CONFIRMED'
                or 'REFERENCE_MARKER:'+rows[1]['cause'] not in rows[1]['requires']
                or rows[2]['after_event']!='RETURN_MARKER'
                or not {'RETURN_CLEAR_CONFIRMED','RETURN_PATH_CLEAR'}.issubset(rows[2]['requires'])
                or rows[3]['after_event']!='RETURN_LANE_CONFIRMED'
                or 'REFERENCE_MARKER:'+rows[3]['cause'] not in rows[3]['requires']):
            raise ValueError('NORMATIVE_O_PASS_POLICY_INVALID')
        return
    if response.actor_role=='EGO' and category=='O' and response.action_id=='B':
        program=_program(response);rows=program['transitions']
        nominal=_nominal_v5(response)
        if nominal is None:
            raise ValueError('NORMATIVE_NOMINAL_UNPROVEN')
        if not _io_nominal_ok(nominal):  # v9; OLD RULE v8: nominal not in (6, 15/2, 75/8)
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        initial=response.targets[program['initial']]
        if initial==0 and rows and rows[0]['after_event']=='CAPTURE_START':
            if response.targets[rows[0]['cause']]!=nominal:
                raise ValueError('NORMATIVE_NOMINAL_INVALID')
            rows=rows[1:]
        elif initial!=nominal:
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        if (len(rows)!=1 or rows[0]['after_event']!='TRIGGER' or rows[0]['delay_s']!=0
                or response.targets[rows[0]['cause']]!=Number(5,2)):
            raise ValueError('NORMATIVE_O_FOLLOW_POLICY_INVALID')
        desired_offset(Number(0),response)
        if (response.phases.get('reference_switches') or any(s['start_offset_m']!=0 or s['end_offset_m']!=0
                for s in response.profile['segments'])):
            raise ValueError('NORMATIVE_O_FOLLOW_LATERAL_INVALID')
        return
    if response.actor_role=='EGO' and category=='I' and response.action_id=='A':
        program=_program(response);rows=program['transitions']
        nominal=_nominal_v5(response)
        if nominal is None:
            raise ValueError('NORMATIVE_NOMINAL_UNPROVEN')
        if not _io_nominal_ok(nominal):  # v9; OLD RULE v8: nominal not in (6, 15/2, 75/8)
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        initial=response.targets[program['initial']]
        if initial==0 and rows and rows[0]['after_event']=='CAPTURE_START':
            if response.targets[rows[0]['cause']]!=nominal:
                raise ValueError('NORMATIVE_NOMINAL_INVALID')
            rows=rows[1:]
        elif initial!=nominal:
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        if (len(rows)!=2 or rows[0]['after_event']!='TRIGGER' or rows[0]['delay_s']!=0
                or response.targets[rows[0]['cause']]!=0
                or rows[1]['after_event']!='SOURCE_CLEAR_CONFIRMED' or rows[1]['delay_s']!=0
                or response.targets[rows[1]['cause']]!=nominal
                or not {'STOP_AFTER_TRIGGER','NPC_TARGET_LANE_CONFIRMED'}.issubset(rows[1]['requires'])):
            raise ValueError('NORMATIVE_I_STOP_POLICY_INVALID')
        desired_offset(Number(0),response)
        if (response.phases.get('reference_switches') or any(s['start_offset_m']!=0 or s['end_offset_m']!=0
                for s in response.profile['segments'])):
            raise ValueError('NORMATIVE_I_STOP_LATERAL_INVALID')
        return
    if response.actor_role=='EGO' and category=='I' and response.action_id=='B':
        program=_program(response);rows=program['transitions']
        nominal=_nominal_v5(response)
        if nominal is None:
            raise ValueError('NORMATIVE_NOMINAL_UNPROVEN')
        if not _io_nominal_ok(nominal):  # v9; OLD RULE v8: nominal not in (6, 15/2, 75/8)
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        initial=response.targets[program['initial']]
        if initial==0 and rows and rows[0]['after_event']=='CAPTURE_START':
            if response.targets[rows[0]['cause']]!=nominal:
                raise ValueError('NORMATIVE_NOMINAL_INVALID')
            rows=rows[1:]
        elif initial!=nominal:
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        if (len(rows)!=2 or rows[0]['after_event']!='SOURCE_CLEAR_CONFIRMED' or rows[0]['delay_s']!=0
                or not {'TRIGGER','LANE_CHANGE_PATH_CLEAR'}.issubset(rows[0]['requires'])
                or rows[1]['after_event']!='TARGET_LANE_CONFIRMED' or rows[1]['delay_s']!=0
                or 'REFERENCE_MARKER:'+rows[1]['cause'] not in rows[1]['requires']
                or any(response.targets[row['cause']]!=nominal for row in rows)):
            raise ValueError('NORMATIVE_I_CHANGE_POLICY_INVALID')
        return
    if response.actor_role!='EGO' or category not in ('C','L','M'):
        return
    program=_program(response);rows=program['transitions'];nominal=Number(2 if category=='L' else 4)
    reduced=Number(1 if category=='L' else 2)
    initial=response.targets[program['initial']]
    if initial==0 and rows and rows[0]['after_event']=='CAPTURE_START':
        if response.targets[rows[0]['cause']]!=nominal:
            raise ValueError('NORMATIVE_NOMINAL_INVALID')
        rows=rows[1:]
    elif initial!=nominal:
        raise ValueError('NORMATIVE_NOMINAL_INVALID')
    if len(rows)!=2:
        raise ValueError('NORMATIVE_PROGRAM_UNPROVEN')
    yielding,resuming=rows
    if (yielding['after_event']!='TRIGGER' or yielding['delay_s']!=0
            or response.targets[yielding['cause']]!=(Number(0) if response.action_id=='A' else reduced)
            or resuming['after_event']!='CLEAR_N_CONFIRMED' or resuming['delay_s']!=0
            or response.targets[resuming['cause']]!=nominal
            or (response.action_id=='A' and 'STOP_AFTER_TRIGGER' not in resuming['requires'])
            or response.action_id not in ('A','B')):
        raise ValueError('NORMATIVE_CROSSING_POLICY_INVALID')


def _nominal_v5(response):
    """v5 C2 (prereg eda7680): the normative nominal is the response's own NOMINAL target. OLD RULE (report-only,
    nominal_old_rule): readiness.targets_mps['EGO'], which E6 sets to the measured stock plateau, so it can never equal
    6 / 7.5 / 75/8 natively."""
    return response.targets.get('NOMINAL')


_IO_SERIES=frozenset(6*Number(5,4)**(k-1) for k in range(-4,9))


def _io_nominal_ok(nominal, npc=False):
    """v9 (prereg PREREG_M56_V9_IO_NOMINAL_SERIES_20261107): an I/O EGO nominal is 6*(5/4)^(k-1) for an integer k in
    [-4, 8], exact (FILL20 dd2954c series); the NPC of an I scene is vE - 1. OLD RULE v8 (report-only): EGO in
    {6, 15/2, 75/8}, NPC in {5, 13/2, 67/8} = k 1..3 only, so every k outside 1..3 was blocked at admission."""
    if type(nominal) not in (Number,int):
        return False
    return (nominal+1 if npc else nominal) in _IO_SERIES


def nominal_old_rule(fixture, role='EGO'):
    """Report-only: the old normative nominal (readiness target)."""
    return fixture.environment.get('readiness',{}).get('targets_mps',{}).get(role)


def _lateral_contract(response, fixture):
    """Analytic offline admission of frozen horizontal parallel references.

    Full continuous body fit is a separate motion receipt, not inferred from this
    desired curve. General/banked/variable-width geometry remains explicitly
    unsupported. The exact squared curvature bound avoids rounded rescue.
    """
    from .geometry import _is_box
    desired_offset(Number(0),response)
    segments=response.profile['segments']
    moving=tuple(s for s in segments if s['start_offset_m']!=s['end_offset_m'])
    if not moving:
        return
    category=fixture.domain.topology.get('category');mechanism=fixture.domain.topology.get('mechanism')
    npc=response.actor_role=='NPC';role=response.actor_role
    if not ((not npc and role=='EGO' and (category,response.action_id) in (('I','B'),('O','A'),('F','B'))
            and (category!='F' or mechanism=='F04')) or (npc and category=='I' and response.action_id=='NPC_COMMON')):
        raise ValueError('LATERAL_ACTION_UNSUPPORTED')
    route=response.route
    if route is None or not route.continuity:
        raise ValueError('LATERAL_GEOMETRY_UNSUPPORTED')
    axis=(len(route.transforms)==2 and route.transforms[0].x<route.transforms[1].x
          and route.transforms[0].y==route.transforms[1].y and route.transforms[0].z==route.transforms[1].z
          and all((t.pitch,t.yaw,t.roll)==(0.,0.,0.) for t in route.transforms))
    regions=fixture.domain.topology.get('npc_regions' if npc else 'action_regions')
    required={role+'_INITIAL',role+'_TARGET'} if category in ('I','O') else {role+'_INITIAL'}
    if not isinstance(regions,Mapping) or not required.issubset(regions) or any(not _is_box(regions[k]) for k in required):
        raise ValueError('LATERAL_WIDTH_UNPROVEN')
    if axis:
        initial=regions[role+'_INITIAL'];center=(Number(min(p[1] for p in initial))+Number(max(p[1] for p in initial)))/2
        if Number(route.transforms[0].y)!=center:
            raise ValueError('LATERAL_REFERENCE_NOT_LANE_CENTER')
        if category in ('I','O'):
            target=regions[role+'_TARGET']
            separation=(Number(min(p[1] for p in target))+Number(max(p[1] for p in target)))/2-center
    else:
        separation=_lateral_route_v5(response,fixture)
    nominal=_nominal_v5(response)
    if not isinstance(nominal,Number) or nominal<=0:
        raise ValueError('LATERAL_NOMINAL_UNPROVEN')
    switches=response.phases.get('reference_switches',())
    _reference_response(response,_program(response)['initial'])
    if category in ('I','O'):
        if not _io_nominal_ok(nominal,npc=npc):  # v9; OLD RULE v8: NPC in (5, 13/2, 67/8), EGO in (6, 15/2, 75/8)
            raise ValueError('LATERAL_NOMINAL_INVALID')
        if not separation or moving[0]['start_offset_m']!=0 or moving[0]['end_offset_m']!=separation:
            raise ValueError('LATERAL_SEPARATION_INVALID')
        if not switches or switches[0]['event']!=('NPC_TARGET_LANE_CONFIRMED' if npc else 'TARGET_LANE_CONFIRMED'):
            raise ValueError('LATERAL_TARGET_SWITCH_MISSING')
        if category=='O' and (len(switches)!=2 or switches[1]['event']!='RETURN_LANE_CONFIRMED'):
            raise ValueError('LATERAL_RETURN_SWITCH_MISSING')
        for switch in switches:
            row=next(t for t in _program(response)['transitions'] if t['cause']==switch['cause'])
            marker='REFERENCE_MARKER:'+('NPC:' if npc else '')+switch['cause']
            if marker not in (row['after_event'],*row['requires']):
                raise ValueError('LATERAL_MARKER_GUARD_MISSING')
        profiles=(response.profile,*(s['profile'] for s in switches))
        moving=tuple(s for p in profiles for s in p['segments'] if s['start_offset_m']!=s['end_offset_m'])
        if len(moving)!=(1 if category=='I' else 2) or any(s['length_m']!=3*nominal for s in moving):
            raise ValueError('LATERAL_LENGTH_INVALID')
        for s in moving:
            if abs(s['end_offset_m']-s['start_offset_m'])!=abs(separation):
                raise ValueError('LATERAL_SEPARATION_INVALID')
    else:
        if nominal!=2 or moving[0]['length_m']!=6 or abs(moving[0]['end_offset_m']-moving[0]['start_offset_m'])!=Number(3,4):
            raise ValueError('LATERAL_F04_PROFILE_INVALID')
        if moving[0]['start_offset_m']!=0 or segments[-1]['end_offset_m']!=0 or len(moving)!=2:
            raise ValueError('LATERAL_F04_RETURN_MISSING')
    if not axis:
        _lateral_axis_v5(route,moving,regions,role,separation)
    for s in moving:
        if not route.arc[0]<=s['start_arc_m']<s['start_arc_m']+s['length_m']<=route.arc[-1]:
            raise ValueError('LATERAL_MARKER_OUTSIDE_ROUTE')
        # max |q''| = 10/sqrt(3); curvature <= |y''|. Normal
        # acceleration <= v^2 curvature, conservatively ignoring its denominator.
        delta=s['end_offset_m']-s['start_offset_m']
        if Number(100,3)*delta**2*nominal**4/s['length_m']**4>Number(25,4):
            raise ValueError('LATERAL_ACCELERATION_BUDGET_UNPROVEN')


def _lateral_route_v5(response, fixture):
    """v5 C3 (prereg eda7680): a real CARLA route reference (I/O only). It must be the fixture's own route for the role
    (CARLA lane-centre waypoints, every step <= 0.25 m); the lane separation is the reviewed CARLA lane-centre distance
    recorded in topology.lane_geometry[role] = {'separation_m': signed Number, 'lane_width_m': {'initial','target'}}.
    OLD RULE: only the 2-point +x route was accepted (any other route -> LATERAL_GEOMETRY_UNSUPPORTED)."""
    from math import dist
    from .catalog import _digest
    route=response.route;role=response.actor_role;routes=getattr(fixture,'routes',None)
    if (fixture.domain.topology.get('category') not in ('I','O') or not isinstance(routes,Mapping) or role not in routes
            or _digest(routes[role])!=_digest(route) or len(route.transforms)<2
            or any(dist((a.x,a.y,a.z),(b.x,b.y,b.z))>.25+1e-6 for a,b in zip(route.transforms,route.transforms[1:]))):
        raise ValueError('LATERAL_GEOMETRY_UNSUPPORTED')
    geo=fixture.domain.topology.get('lane_geometry',{})
    geo=geo.get(role) if isinstance(geo,Mapping) else None
    widths=geo.get('lane_width_m') if isinstance(geo,Mapping) else None
    if (not isinstance(geo,Mapping) or not isinstance(geo.get('separation_m'),Number)
            or not isinstance(widths,Mapping) or set(widths)!={'initial','target'}
            or any(not isinstance(w,Number) or w<=0 for w in widths.values())):
        raise ValueError('LATERAL_WIDTH_UNPROVEN')
    return geo['separation_m']


def _lateral_separation(reference, route):
    """v8 (docs/m56/PREREG_M56_V8_IO_ONSET_AXIS_20261027.md, Duy 2026-10-27): signed lateral separation of the reference
    route from the response route along the CARLA right vector (_axis_right, as _lateral_axis_v5). OLD RULE (v7): the y
    difference only, right only for +x roads (yaw 0): reversed at yaw 180, zero at yaw +-90. Identical on +x routes."""
    a,b=reference.transforms[0],route.transforms[0]
    axis=_axis_right(b.yaw)
    if axis is None:
        return Number(a.y)-Number(b.y)
    k,sign=axis
    return (Number((a.x,a.y)[k])-Number((b.x,b.y)[k]))*sign


def _axis_right(yaw):
    """v5 erratum 1 E1-a: (lateral world index, sign of the CARLA right vector on it) when yaw is within 1 degree of a
    world axis, else None. CARLA right vector = (-sin yaw, cos yaw)."""
    a=yaw%360.
    for k,axis in ((0.,(1,1)),(90.,(0,-1)),(180.,(1,-1)),(270.,(0,1)),(360.,(1,1))):
        if abs(a-k)<=1.:
            return axis
    return None


def _lateral_axis_v5(route, moving, regions, role, separation):
    """v5 C3 + erratum 1 (22c5cd4): the stretch holding every lane-change segment is straight (total heading variation
    <= 1 degree) and world-axis aligned (each yaw within 1 degree of one axis), because the frozen metric lane boxes are
    world-axis aligned (metrics._in_action_region). INITIAL/TARGET boxes are disjoint on the lateral axis, the route
    stretch lies inside the INITIAL lateral range, and the reviewed separation matches the box centres within 0.05 m."""
    lo=min(s['start_arc_m'] for s in moving);hi=max(s['start_arc_m']+s['length_m'] for s in moving)
    first=max((i for i,a in enumerate(route.arc) if a<=lo),default=0)
    last=min((i for i,a in enumerate(route.arc) if a>=hi),default=len(route.arc)-1)
    stretch=route.transforms[first:last+1];yaws=[t.yaw for t in stretch]
    axes={_axis_right(y) for y in yaws}
    if (len(axes)!=1 or None in axes
            or sum(abs((b-a+180.)%360.-180.) for a,b in zip(yaws,yaws[1:]))>1.):
        raise ValueError('LATERAL_GEOMETRY_UNSUPPORTED')
    (k,sign),=axes
    def span(box):
        return min(p[k] for p in box),max(p[k] for p in box)
    (li,hi_),(lt,ht)=span(regions[role+'_INITIAL']),span(regions[role+'_TARGET'])
    if not (hi_<=lt or ht<=li) or any(not li<=(t.x,t.y)[k]<=hi_ for t in stretch):
        raise ValueError('LATERAL_WIDTH_UNPROVEN')
    if abs(float(separation)-((lt+ht)/2-(li+hi_)/2)*sign)>.05:
        raise ValueError('LATERAL_SEPARATION_INVALID')


def _axis_route(route):
    a,b=route.transforms
    return (route.continuity and b.x>a.x and a.y==b.y and a.z==b.z
            and all((t.pitch,t.yaw,t.roll)==(0.,0.,0.) for t in route.transforms))


def _at_arc(route, arc):
    """Float linear interpolation (x, y, yaw) of a waypoint route at an arc."""
    arc=float(arc);arcs=[float(a) for a in route.arc]
    i=max(0,min(len(arcs)-2,max((n for n,a in enumerate(arcs) if a<=arc),default=0)))
    a,b=route.transforms[i],route.transforms[i+1];f=(arc-arcs[i])/(arcs[i+1]-arcs[i])
    return a.x+f*(b.x-a.x),a.y+f*(b.y-a.y),a.yaw


def _station(x, y, route):
    """Float horizontal projection station of (x, y) on a waypoint route."""
    best=None
    for a,b,sa,sb in zip(route.transforms,route.transforms[1:],route.arc,route.arc[1:]):
        dx,dy=b.x-a.x,b.y-a.y;n=dx*dx+dy*dy
        f=0. if n==0 else max(0.,min(1.,((x-a.x)*dx+(y-a.y)*dy)/n))
        d=(a.x+f*dx-x)**2+(a.y+f*dy-y)**2
        if best is None or d<best[0]:
            best=(d,float(sa)+f*(float(sb)-float(sa)))
    return best[1]


def _switch_real_v5(old, new, marker, old_offset):
    """v5 erratum 1 E1-c (22c5cd4): a CARLA waypoint switch route (<= 0.25 m steps, same map, continuity) whose arc frame
    is aligned with the old route (|arc - projected old station| <= 0.05 m for every point), continuous at the marker
    (old point + old_offset along the CARLA right vector within 0.05 m of the new point). OLD RULE: 2-point +x routes
    with identical arc tuples and exact y + offset == new y."""
    from math import dist,sin,cos,radians
    if (not new.continuity or new.map_hash!=old.map_hash or len(new.transforms)<2 or len(new.arc)!=len(new.transforms)
            or any(b<=a for a,b in zip(new.arc,new.arc[1:]))
            or any(dist((a.x,a.y,a.z),(b.x,b.y,b.z))>.25+1e-6 for a,b in zip(new.transforms,new.transforms[1:]))
            or not (old.arc[0]<=marker<=old.arc[-1] and new.arc[0]<=marker<=new.arc[-1])):
        raise ValueError('REFERENCE_SWITCH_UNSUPPORTED')
    # ponytail: O(n_new * n_old) float projection; window it if switch routes grow past a few thousand points.
    if any(abs(float(a)-_station(t.x,t.y,old))>.05 for t,a in zip(new.transforms,new.arc)):
        raise ValueError('REFERENCE_SWITCH_DISCONTINUOUS')
    x,y,yaw=_at_arc(old,marker);nx,ny,_=_at_arc(new,marker);o=float(old_offset);r=radians(yaw)
    if dist((x-sin(r)*o,y+cos(r)*o),(nx,ny))>.05:
        raise ValueError('REFERENCE_SWITCH_DISCONTINUOUS')


def desired_offset(arc: Number, response: FrozenResponse) -> Number:
    """Evaluate the frozen, continuous piecewise quintic arc reference exactly.

    Segments hold absolute signed offsets in one unchanged plan/reference frame.
    Gaps hold the preceding endpoint; queries outside the profile clamp to its
    endpoint offsets. Validate ALL segments before evaluating even the first one.
    No marker selection, target-plan switch, fit/curvature certification, or
    evidence of realized motion is provided by this arithmetic function.
    """
    if not isinstance(arc, Number) or not isinstance(response, FrozenResponse):
        raise ValueError('Exact arc and frozen response required')
    profile = response.profile
    if (not isinstance(profile, Mapping) or set(profile) != {'method', 'segments'}
            or profile['method'] != 'quintic-arc-v1'):
        raise ValueError('Unsupported lateral profile')
    segments = profile['segments']
    if not isinstance(segments, tuple) or not segments:
        raise ValueError('Nonempty frozen segments required')
    keys = {'start_arc_m', 'length_m', 'start_offset_m', 'end_offset_m'}
    previous_end = previous_offset = None
    for segment in segments:
        if (not isinstance(segment, Mapping) or set(segment) != keys
                or any(not isinstance(segment[key], Number) for key in keys)):
            raise ValueError('Exact segment fields required')
        start, length = segment['start_arc_m'], segment['length_m']
        if length <= 0:
            raise ValueError('Positive profile length required')
        if previous_end is not None and (start < previous_end
                or segment['start_offset_m'] != previous_offset):
            raise ValueError('Overlapping, unordered or discontinuous profile')
        previous_end = start + length
        previous_offset = segment['end_offset_m']

    offset = segments[0]['start_offset_m']
    for segment in segments:
        start, length = segment['start_arc_m'], segment['length_m']
        if arc <= start:
            return offset
        if arc < start + length:
            u = (arc - start) / length
            q = 10*u**3 - 15*u**4 + 6*u**5
            return segment['start_offset_m'] + q*(segment['end_offset_m'] - segment['start_offset_m'])
        offset = segment['end_offset_m']
    return offset
