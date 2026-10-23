"""T12 lazy runtime admission. Importing this module never imports carla/stock.

Every scope/identity/hash check runs before `_native_factory` binds a client.
The native backend implemented here is READ-ONLY (identity/map/settings/actors/
blueprints); spawn/tick/apply/destroy/restore belong to T13 and are not provided.
"""
from __future__ import annotations

from dataclasses import fields, replace
from datetime import datetime, timezone
from fractions import Fraction
import collections
import hashlib
import json
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

from m56.evidence import append_record
from m56.model import (AdmissionVerdict, BlockedPreparation, CleanupReceipt, EpisodeVerdict, EventRecord, FrameRecord,
                       IntegrityReport, OperationResponse, OwnedRegistry, PhysicalState, QueryBundle,
                       RuntimeIdentity, SourceRef, SpawnResponse, SpawnState, WitnessState)

READ_OPS = ('IDENTITY', 'READ_MAP', 'READ_SETTINGS', 'READ_ACTORS', 'READ_BLUEPRINTS')
EXPECTED = {'client': '0.9.16', 'server': '0.9.16', 'python': '3.12.10'}
LOOPBACK = ('127.0.0.1', 'localhost')
REQUIRED_BLUEPRINT = 'vehicle.audi.a2'
# Stock 0.9.16 offers no getter for these; they need separately reviewed recipes.
# Plan §pinned readonly input manifest (stock root E:/Carla/PythonAPI/carla/agents/navigation/).
STOCK_ROOT = 'E:/Carla/PythonAPI/carla/agents/navigation'
PINNED_STOCK = {'basic_agent': '298d7d7b8d89925b51300179932c18e6a066ab5c3e95708453f7fa020b136ea1',
                'local_planner': '9250a88536a04ee30ee19b01c3b3764388295cf3f438123e2b2c88b647096b4f',
                'controller': '35dbabac3b7bf69fd7f1272fcd8af97aa7797a537af2e58a31d9d6b67c1f3a0e'}
UNSUPPORTED_GETTERS = ('WHEEL_CONTACT', 'DOOR_COLLIDER', 'MECHANICAL_GEAR', 'COLLISION_COMPLETENESS')


_OWNERSHIP = ('NON_LOOPBACK_HOST', 'RPC_PORT_MISSING', 'FOREIGN_TICK_OWNER', 'FOREIGN_WRITER', 'STALE_BOOT',
              'IDENTITY_MISMATCH:boot', 'IDENTITY_MISMATCH:world', 'IDENTITY_MISMATCH:map')
_SOURCE = ('VERSION_MISMATCH', 'SOURCE_HASH_MISMATCH', 'STOCK_PIN_MISMATCH', 'IDENTITY_MISMATCH')


def _blocked(reasons, refs=()):
    """Plan status precedence: authority before ownership before source."""
    if any(not r.startswith(_OWNERSHIP + _SOURCE) for r in reasons):
        status = 'BLOCKED_AUTHORITY'
    elif any(r.startswith(_OWNERSHIP) for r in reasons):
        status = 'BLOCKED_OWNERSHIP'
    else:
        status = 'BLOCKED_SOURCE'
    return BlockedPreparation(status, tuple(reasons), tuple(refs))


def _authority_reasons(ops, approvals, ownership, charter_ref):
    r = []
    if ownership.host not in LOOPBACK:
        r.append('NON_LOOPBACK_HOST')
    if not isinstance(ownership.ports.get('rpc'), int):
        r.append('RPC_PORT_MISSING')
    if ownership.tick_owner != ownership.writer:
        r.append('FOREIGN_TICK_OWNER')
    if not approvals.receipt_refs:
        r.append('APPROVAL_RECEIPT_MISSING')
    if any(x.kind.upper().startswith('SYNTHETIC') for x in approvals.receipt_refs):
        r.append('SYNTHETIC_RECEIPT')
    if not ops:
        r.append('NO_QUERY_OPS')
    for op in ops:
        if op not in approvals.allowed_scopes:
            r.append(f'SCOPE_NOT_APPROVED:{op}')
        if op not in ownership.allowed_ops:
            r.append(f'OP_NOT_OWNED:{op}')
    if any(op not in READ_OPS for op in ops) and charter_ref is None:
        r.append('PROBE_CHARTER_MISSING')
    return r


def _scope_reasons(ops, approvals, environment, ownership, store, charter_ref):
    r = _authority_reasons(ops, approvals, ownership, charter_ref)
    if store is None:
        r.append('OWNED_STORE_MISSING')
    elif store.writer != ownership.writer:
        r.append('FOREIGN_WRITER')
    if (ownership.boot, ownership.world) != (environment.boot, environment.world):
        r.append('STALE_BOOT')
    for k, v in EXPECTED.items():
        if getattr(environment, k) != v:
            r.append(f'VERSION_MISMATCH:{k}')
    for name, module in environment.modules.items():
        if environment.source_hashes.get(name) != module.sha256:
            r.append(f'SOURCE_HASH_MISMATCH:{name}')
    for name, pinned in PINNED_STOCK.items():
        if environment.source_hashes.get(name) != pinned:
            r.append(f'STOCK_PIN_MISMATCH:{name}')
    return r


def _native_factory(ownership, timeout_s):
    """Transport seam: the only place that imports carla."""
    import carla
    client = carla.Client(ownership.host, ownership.ports['rpc'])
    client.set_timeout(timeout_s)
    return ReadOnlyCarlaBackend(client, ownership)


def identify(ownership, approvals, timeout_s):
    """Read the live server identity (world/map/versions) before a receipt names the world."""
    reasons = _authority_reasons(('IDENTITY',), approvals, ownership, None)
    if reasons:
        return _blocked(reasons)
    return _native_factory(ownership, float(timeout_s)).identity()


def prepare(request, approvals, environment, ownership):
    reasons = _scope_reasons(request.query_ops, approvals, environment, ownership,
                             request.store, request.charter_ref)
    if reasons:
        return _blocked(reasons)
    backend = _native_factory(ownership, float(request.bounds.get('timeout_s', 10)))
    live = backend.identity()
    mismatch = tuple(f'IDENTITY_MISMATCH:{f.name}' for f in fields(RuntimeIdentity)
                     if getattr(live, f.name) != getattr(environment, f.name))
    if mismatch:  # live server differs from the receipt: stale boot/world -> ownership, else source
        return _blocked(mismatch)
    out = backend.query(request)
    if 'READ_BLUEPRINTS' in request.query_ops and REQUIRED_BLUEPRINT not in out.map.get('blueprints', ()):
        # No substitute vehicle: a missing frozen blueprint blocks the fixture.
        return BlockedPreparation('BLOCKED_CAPABILITY', (f'BLUEPRINT_MISSING:{REQUIRED_BLUEPRINT}',), out.refs)
    return out


def _charter(approvals):
    """The probe charter receipt carried by the approval bundle, only while its bytes still match the receipt."""
    ref = next((r for r in approvals.receipt_refs if r.kind == 'PROBE_CHARTER'), None)
    if ref is None or not Path(ref.uri).is_file() or hashlib.sha256(Path(ref.uri).read_bytes()).hexdigest() != ref.sha256:
        return None
    return ref


def admit(fixture, approvals, environment, ownership):
    # admit() has no RunStore argument; the store writer is checked again at runner bind.
    reasons = _scope_reasons(('VALIDATE_AB',), approvals, environment, ownership,
                             SimpleNamespace(writer=ownership.writer), _charter(approvals))
    if reasons:
        b = _blocked(reasons)
        return AdmissionVerdict(b.status, b.reasons)
    if fixture.freeze_ref is None:
        return AdmissionVerdict('BLOCKED_FIXTURE', ('FIXTURE_FREEZE_MISSING',))
    bad = [p.kind for p in fixture.proofs if p.review is None or p.review.verdict != 'APPROVED' or not p.raw_refs]
    if bad:
        return AdmissionVerdict('BLOCKED_CAPABILITY', tuple(f'CAPABILITY_UNREVIEWED:{k}' for k in bad))
    return AdmissionVerdict('ADMITTED', (), (fixture.freeze_ref,))


def bind_backend(context):
    if context.admission.status != 'ADMITTED':
        return BlockedPreparation(context.admission.status, context.admission.reasons)
    return _native_factory(context.ownership, float(context.deadlines['rpc_s']))


def verify_capability(proof, queries):
    r = []
    if not proof.raw_refs:
        r.append('CAPABILITY_RAW_MISSING')
    if proof.review is None or proof.review.verdict != 'APPROVED':
        r.append('CAPABILITY_REVIEW_MISSING')
    if proof.kind in UNSUPPORTED_GETTERS:
        r.append(f'UNSUPPORTED_NATIVE_GETTER:{proof.kind}')
    known = {(x.uri, x.sha256, x.bytes) for x in queries.refs}
    if any(x.kind.upper().startswith('SYNTHETIC') for x in proof.raw_refs):
        r.append('CAPABILITY_SYNTHETIC_RAW')
    if any((x.uri, x.sha256, x.bytes) not in known for x in proof.raw_refs):
        r.append('CAPABILITY_RAW_NOT_IN_QUERY')
    status = ('BLOCKED_CAPABILITY' if any(x.startswith('UNSUPPORTED_NATIVE_GETTER') for x in r)
              else 'WITNESS_UNCERTAIN' if r else 'VALID')
    return IntegrityReport(status, tuple(r), proof.raw_refs)


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def module_refs():
    """Hash libcarla and the pinned stock files; call only after an authorized bind."""
    import carla
    from pathlib import Path
    files = {'carla': next(Path(carla.__file__).parent.glob('libcarla*.pyd')),
             **{k: Path(STOCK_ROOT) / f'{k}.py' for k in PINNED_STOCK}}
    return {k: SourceRef(str(f), _sha_file(f), f.stat().st_size, '0.9.16', 'sha256', 'MODULE')
            for k, f in files.items()}


class ReadOnlyCarlaBackend:
    """Native identity/query only. No settings, tick, spawn, apply or destroy calls."""

    def __init__(self, client, ownership):
        self.client, self.ownership = client, ownership

    def identity(self):
        world = self.client.get_world()
        mods = module_refs()
        v = sys.version_info
        # Routes carry the map as the sha256 of its OpenDRIVE, and W01 compares route.map_hash with identity.map:
        # report the server's own OpenDRIVE hash, never the map name (native 2026-10-22).
        xodr = hashlib.sha256(world.get_map().to_opendrive().encode('utf-8')).hexdigest()
        return RuntimeIdentity(self.ownership.boot, str(world.id), self.client.get_client_version(),
                               self.client.get_server_version(), f'{v.major}.{v.minor}.{v.micro}',
                               mods, xodr, {k: m.sha256 for k, m in mods.items()})

    def query(self, request):
        world = self.client.get_world()
        raw = {'utc': datetime.now(timezone.utc).isoformat(), 'world': str(world.id),
               'ops': list(request.query_ops)}
        if 'READ_MAP' in request.query_ops:
            m = world.get_map()
            raw['map'] = {'name': m.name, 'spawn_points': len(m.get_spawn_points())}
        if 'READ_SETTINGS' in request.query_ops:
            s = world.get_settings()
            raw['settings'] = {'synchronous_mode': s.synchronous_mode,
                               'fixed_delta_seconds': s.fixed_delta_seconds,
                               'no_rendering_mode': s.no_rendering_mode}
        if 'READ_ACTORS' in request.query_ops:
            counts = {}
            for a in world.get_actors():
                k = a.type_id.split('.')[0]
                counts[k] = counts.get(k, 0) + 1
            raw['actors_by_kind'] = counts
        if 'READ_BLUEPRINTS' in request.query_ops:
            raw['blueprints'] = sorted(b.id for b in world.get_blueprint_library().filter('vehicle.*'))
        data = (json.dumps(raw, indent=1, sort_keys=True) + '\n').encode()
        path = request.store.root / f'query-{len(list(request.store.root.glob("query-*.json")))}.json'
        with open(path, 'xb') as f:  # exclusive: never overwrite raw evidence
            f.write(data)
        ref = SourceRef(str(path), hashlib.sha256(data).hexdigest(), len(data), '1', 'native-query', 'NATIVE_RAW')
        mp = {'name': raw.get('map', {}).get('name'), 'blueprints': tuple(raw.get('blueprints', ())),
              'settings': raw.get('settings'), 'actors_by_kind': raw.get('actors_by_kind')}
        return QueryBundle(self.ownership.boot, str(world.id), mp, {}, {}, {}, {}, {}, (), (), (ref,))


# --- T13 owned spawn / tick / cleanup kernels (backend-agnostic) ---

def _verdict(spawn, physical, witness, reasons):
    return EpisodeVerdict(SpawnState(spawn), PhysicalState(physical), WitnessState(witness), tuple(reasons), (), {})


def _record_registry(context, registry):
    # Partial successes stay owned: cleanup reads them back from the sealed-to-be journal.
    append_record(context.store, 'owned/registry.jsonl', {
        'boot': registry.boot, 'world': registry.world, 'owned_vehicle_ids': list(registry.owned_vehicle_ids),
        'owned_sensor_ids': list(registry.owned_sensor_ids),
        'responses': [{'actor_id': r.actor_id, 'error': r.error} for r in registry.spawn_responses]})


def spawn_owned(context, fixture):
    """Batch spawn without a tick cue, register every success, attach sensor listeners before any tick."""
    if context.admission.status != 'ADMITTED' or context.backend is None:
        return BlockedPreparation(context.admission.status if context.backend else 'BLOCKED_BACKEND',
                                  context.admission.reasons)
    live = context.backend.identity()
    if (live.boot, live.world) != (context.identity.boot, context.identity.world):
        return BlockedPreparation('BLOCKED_OWNERSHIP', ('WORLD_CHANGED_BEFORE_SPAWN',))
    responses = context.backend.spawn(tuple(fixture.actors), False)
    vehicles, sensors, reasons = [], [], []
    if len(responses) != len(fixture.actors):
        reasons.append('SPAWN_ID_UNKNOWN')
    for recipe, resp in zip(fixture.actors, responses):
        if resp.error or resp.actor_id is None:
            reasons.append(f'SPAWN_ERROR:{recipe.role}')
        else:
            (sensors if recipe.blueprint.startswith('sensor.') else vehicles).append(resp.actor_id)
    instrument = getattr(context.backend, 'instrument', None)
    if instrument is not None and not reasons:
        # Runner-owned collision instrumentation (v2 erratum E1): one sensor per scene vehicle, never a scene actor.
        sensors.extend(instrument({r.role: x.actor_id for r, x in zip(fixture.actors, responses)
                                   if not r.blueprint.startswith('sensor.')}))
    registry = OwnedRegistry(live.boot, live.world, tuple(vehicles), tuple(sensors), tuple(responses))
    _record_registry(context, registry)
    if reasons:  # no movement, no respawn, no fallback actor
        return _verdict('FAILED', 'NOT_RUN', 'UNKNOWN', reasons)
    for sensor_id in sensors:
        context.backend.listen(sensor_id, lambda packet, i=sensor_id: append_record(
            context.store, f'sensors/{i}.jsonl', packet))
    return registry


def tick_owned(context, registry, commands, previous=None):
    """Apply owned commands, tick once, and correlate the returned frame. No retries."""
    owned = set(registry.owned_vehicle_ids)
    foreign = [c.actor for c in commands if c.actor not in owned]
    if foreign:
        return _verdict('CONFIRMED', 'UNKNOWN', 'INVALID', (f'FOREIGN_COMMAND:{i}' for i in foreign))
    if commands:
        context.backend.apply(tuple(commands))
    frame = context.backend.tick(float(context.deadlines['tick_s']))
    writers = tuple(frame.integrity.get('writers', ()))
    if len(writers) != 1:  # another writer on our actors: the physical trace is not ours
        return _verdict('CONFIRMED', 'FAILED', 'INVALID', (f'WRITERS:{",".join(writers) or "UNKNOWN"}',))
    r = []
    if (frame.boot, frame.world) != (registry.boot, registry.world):
        r.append('WORLD_CHANGED')
    allowed = owned | set(registry.owned_sensor_ids)
    r += [f'FOREIGN_ACTOR:{i}' for i in frame.integrity.get('actor_ids', ()) if i not in allowed]
    if previous is not None and frame.frame != previous + 1:
        r.append(f'TICK_GAP:{previous}->{frame.frame}')
    return _verdict('CONFIRMED', 'UNKNOWN', 'INVALID', r) if r else frame


def cleanup_owned(context, registry):
    """Sensors before vehicles, one bounded pass, survivors escalate. Never restarts the server."""
    import time
    owned = registry.owned_sensor_ids + registry.owned_vehicle_ids
    live = context.backend.identity()
    if (live.boot, live.world) != (registry.boot, registry.world):
        return CleanupReceipt('BLOCKED_CLEANUP', (), owned, ())
    deadline = time.monotonic() + float(context.deadlines.get('cleanup_s', 15))
    left = lambda: max(0.0, deadline - time.monotonic())
    destroyed, survivors, refs, expired = [], [], [], False
    if registry.owned_sensor_ids:
        context.backend.stop_listeners(registry.owned_sensor_ids)
    for ids in (registry.owned_sensor_ids, registry.owned_vehicle_ids):
        if not ids:
            continue
        if left() <= 0:  # deadline spent: leave the rest owned and escalate, no retry loop
            expired = True; survivors += ids; continue
        for resp in context.backend.destroy(ids, left()):
            (survivors if resp.error else destroyed).append(resp.id)
            refs.append(resp.source)
    if not expired and context.scope_phase == 'ENDING' and 'RESTORE' in context.ownership.allowed_ops:
        refs.append(context.backend.restore(context.ownership, left()).source)
    status = 'BLOCKED_CLEANUP' if expired else 'ESCALATED' if survivors else 'CLEANED'
    return CleanupReceipt(status, tuple(destroyed), tuple(survivors), tuple(refs))


class _NativeStock:
    """Admitted native materialization for response.create_stock_driver: the PINNED stock BasicAgent (EGO) or
    LocalPlanner (NPC) with the reviewed config. The reviewed plan is a tuple of {'x','y','z'} points on the frozen
    route; each becomes the map waypoint at that point with LANEFOLLOW (no other waypoint is created)."""

    def __init__(self, actor, config, world):
        sys.path.insert(0, str(Path(STOCK_ROOT).parents[1]))  # E:/Carla/PythonAPI/carla (pinned hashes checked at admit)
        from agents.navigation.basic_agent import BasicAgent
        from agents.navigation.local_planner import LocalPlanner
        self.map = world.get_map()
        opt = dict(config['opt_dict'])
        if config['backend'] == 'BasicAgent':
            self.agent = BasicAgent(actor, target_speed=0., opt_dict=opt, map_inst=self.map)
            self.planner = self.agent.get_local_planner()
        else:
            self.agent = self.planner = LocalPlanner(actor, opt_dict=opt, map_inst=self.map)

    def set_global_plan(self, plan, stop_waypoint_creation, clean_queue):
        import carla
        from agents.navigation.local_planner import RoadOption
        # A point that names its lane (road/lane/s) becomes exactly that lane's waypoint: inside a junction the nearest
        # waypoint to a location can belong to an overlapping connector of another movement (M56 v2, 2026-10-23).
        route = [(self.map.get_waypoint_xodr(int(p['road']), int(p['lane']), float(p['s'])) if 'road' in p else
                  self.map.get_waypoint(carla.Location(float(p['x']), float(p['y']), float(p['z']))), RoadOption.LANEFOLLOW)
                 for p in plan]
        self.planner.set_global_plan(route, stop_waypoint_creation=stop_waypoint_creation, clean_queue=clean_queue)

    def follow_speed_limits(self, value):
        self.agent.follow_speed_limits(value)

    def set_target_speed(self, value):
        self.agent.set_target_speed(value)

    def set_speed(self, value):
        self.planner.set_speed(value)

    def set_offset(self, value):
        self.agent.set_offset(value)

    def run_step(self):
        return self.agent.run_step()

    def queue(self):
        return len(self.planner._waypoints_queue)


class OwnedCarlaBackend(ReadOnlyCarlaBackend):
    """T13/T14 native methods behind the same seam. With bind(fixture, policy_for) the frames carry fixture-bound
    ActorFrames (observed pose/velocity/bounding box, route station by the consumer's own projection, the attributed
    command, server control readback, stock plan queue), and stock intents run through response.create_stock_driver /
    apply_intent on the pinned stock agents. Without bind, frames carry actors=() (capability probes)."""

    def __init__(self, client, ownership, store):
        super().__init__(client, ownership)
        self.store, self.world = store, client.get_world()
        self.original = self.world.get_settings()  # restored only at ENDING
        self.owned = set()
        # Consumer initialization contract: synchronous, dt 1/20, substeps 1/100 x 10 (SETTINGS scope required).
        settings = self.world.get_settings()
        settings.synchronous_mode, settings.fixed_delta_seconds = True, 0.05
        settings.substepping, settings.max_substep_delta_time, settings.max_substeps = True, 0.01, 10
        self.world.apply_settings(settings)
        self.settings = {'synchronous_mode': True, 'fixed_delta_seconds': Fraction(1, 20),
                         'max_substep_delta_time': Fraction(1, 100), 'max_substeps': 10}

    def bind(self, fixture, policy_for, geometry_review=None, kit=None):
        """policy_for(response, actor) -> the reviewed PolicyBundle whose stock binding names that response and actor.
        geometry_review(packet) -> ReviewRecord for a per-frame CONTINUOUS_GEOMETRY proof, or None: no proof is emitted
        (the consumer then stays UNKNOWN). The adapter never reviews anything itself.
        kit (G4, optional): external producer/reviewer. kit.frame(backend, frame_id, simtime, actors) -> (actors,
        integrity additions) before the observation is written; kit.initialization_recipe/finish at seal. With a kit
        the backend also owns one collision sensor per vehicle and an ack fence (v2 erratum E1)."""
        from m56 import response as response_module
        self.fixture, self.policy_for, self.drivers, self.applied, self.roles, self.bodies = fixture, policy_for, {}, {}, {}, {}
        self.geometry_review, self.previous_actors = geometry_review, None
        if kit is not None:
            self.seal_kit, self.instrument, self.fence = kit, self._instrument, self._fence
            self.sensor_parents, self.collisions, self.lifecycle, self.fences = {}, [], {}, {}
        response_module._stock_factory = lambda actor, config: _NativeStock(actor, config, self.world)
        self.plan_refs = {role: self._raw(f'native/plan-{role}.json', route) for role, route in fixture.routes.items()}
        return self

    def _raw(self, stream, record, frame=None, time=None):
        self.count = getattr(self, 'count', 0) + 1  # one immutable file per record: refs never go stale
        a = append_record(self.store, f'{stream.rsplit(".", 1)[0]}/{self.count:07d}.json', record)
        return SourceRef(str(self.store.root / a.relativepath), a.hash, a.size, '1', 'native', 'NATIVE_RAW', frame, time)

    def spawn(self, actors, due_tick_cue):
        # Two batches: vehicles first, then sensors attached to the parent's REAL actor id (SpawnActor's parent
        # argument is an actor id, never a position inside the batch).
        import carla
        lib, ids, result = self.world.get_blueprint_library(), {}, [None] * len(actors)
        for sensors in (False, True):
            batch, slots = [], []
            for i, a in enumerate(actors):
                if a.blueprint.startswith('sensor.') != sensors:
                    continue
                bp = lib.find(a.blueprint)  # raises on a missing blueprint: never substitute
                bp.set_attribute('role_name', a.role) if bp.has_attribute('role_name') else None
                p = a.pose
                tf = carla.Transform(carla.Location(float(p.x), float(p.y), float(p.z)),
                                     carla.Rotation(pitch=float(p.pitch), yaw=float(p.yaw), roll=float(p.roll)))
                parent = a.pose_recipe.get('attach_to_role') if sensors else None
                if sensors and parent not in ids:  # undeclared or unspawned parent: an error, nothing guessed
                    result[i] = (None, 'SENSOR_PARENT_UNDECLARED' if parent is None else 'SENSOR_PARENT_NOT_SPAWNED')
                    continue
                batch.append(carla.command.SpawnActor(bp, tf, ids[parent]) if sensors else carla.command.SpawnActor(bp, tf))
                slots.append(i)
            for i, r in zip(slots, self.client.apply_batch_sync(batch, due_tick_cue) if batch else ()):
                actor_id = (r.actor_id or None) if not r.error else None
                result[i] = (actor_id, r.error or None)
                if actor_id:
                    self.owned.add(actor_id); ids[actors[i].role] = actor_id
                    if hasattr(self, 'roles') and not sensors:
                        self.roles[actor_id] = actors[i].role
        out = tuple(SpawnResponse(actor_id, error, self._raw('native/spawn.jsonl',
                    {'role': a.role, 'blueprint': a.blueprint, 'actor_id': actor_id, 'error': error}))
                    for a, (actor_id, error) in zip(actors, result))
        self.spawn_refs = {a.role: r.source for a, r in zip(actors, out)}
        return out

    def listen(self, sensor_id, callback):
        # Keep the Python sensor object alive: when it goes out of scope CARLA drops the stream and no packet is
        # ever delivered (native probe 2026-10-21: "sensor object went out of the scope", 0 collision packets).
        # CARLA calls back on its own thread; the RunStore writer lock is exclusive, so packets are only queued
        # here and handed to `callback` on the runner's thread by _drain() (every tick and at stop).
        sensor = self.world.get_actor(sensor_id)
        self.listening = {**getattr(self, 'listening', {}), sensor_id: sensor}
        self.callbacks = {**getattr(self, 'callbacks', {}), sensor_id: callback}
        if getattr(self, 'pending', None) is None:
            self.pending = collections.deque()  # append/popleft are thread-safe
        def queue(event):  # CARLA thread: copy plain values only
            packet = {'sensor_id': sensor_id, 'frame': event.frame, 'time': event.timestamp, 'repr': repr(event)}
            other = getattr(event, 'other_actor', None)
            if other is not None:  # collision event: the consumer's row schema, completed on the runner thread
                i = event.normal_impulse
                packet['collision'] = {'actor_id': event.actor.id, 'other_actor_id': other.id,
                                       'normal_impulse': (i.x, i.y, i.z)}
            self.pending.append((sensor_id, packet))
        sensor.listen(queue)
        if hasattr(self, 'lifecycle'):
            self.lifecycle[sensor_id] = {'sensor_id': sensor_id, 'actor_id': self.sensor_parents.get(sensor_id),
                                         'listen_frame': self.world.get_snapshot().frame, 'stop_frame': None, 'errors': []}
        return OperationResponse(sensor_id, None, None, self._raw('native/listen.jsonl', {'sensor_id': sensor_id}))

    def _instrument(self, vehicles):
        """One sensor.other.collision per scene vehicle (runner instrumentation, not a scene actor)."""
        import carla
        bp = self.world.get_blueprint_library().find('sensor.other.collision')
        roles = tuple(vehicles)
        results = self.client.apply_batch_sync([carla.command.SpawnActor(bp, carla.Transform(), vehicles[r]) for r in roles], False)
        out = []
        for role, r in zip(roles, results):
            if r.error or not r.actor_id:
                raise RuntimeError(f'COLLISION_SENSOR_SPAWN_FAILED:{role}:{r.error}')
            self.owned.add(r.actor_id); self.sensor_parents[r.actor_id] = vehicles[role]; out.append(r.actor_id)
            self._raw('native/spawn.jsonl', {'role': role + '_COLLISION', 'blueprint': 'sensor.other.collision',
                                             'actor_id': r.actor_id, 'parent': vehicles[role], 'error': None})
        return tuple(out)

    def _fence(self, last_frame):
        """recorded-ack-fence-v1: request = one owned tick after the last frame; acknowledged when world.tick returns
        exactly that frame and the callback queue is drained; remaining = packets still pending afterwards."""
        request = self.world.tick(10.)
        self._drain()
        remaining = len(getattr(self, 'pending', ()) or ())
        for sensor_id, life in self.lifecycle.items():
            life['stop_frame'] = request
            self.fences[sensor_id] = {'sensor_id': sensor_id, 'request_id': str(last_frame + 1),
                                      'acknowledged_request_id': str(request), 'first_frame': life['listen_frame'],
                                      'last_frame': request, 'remaining': remaining}

    def _materialize(self, c):
        """Stock intent (control None) -> the reviewed stock driver's control; explicit controls pass unchanged."""
        from m56.response import apply_intent, create_stock_driver
        if c.control is not None or not hasattr(self, 'fixture'):
            return c
        if c.actor not in self.drivers:
            response = next(r for r in self.fixture.responses if r.hash == c.response_hash)
            actor = self.world.get_actor(c.actor)
            self.drivers[c.actor] = create_stock_driver(actor, response, self.policy_for(response, actor))
        return apply_intent(self.drivers[c.actor], c)

    def apply(self, commands):
        import carla
        batch = []
        commands = tuple(self._materialize(c) for c in commands)
        if hasattr(self, 'fixture'):
            self.applied = {c.actor: c for c in commands}
        for c in commands:
            k = c.control
            # Every ControlPacket field reaches the server: reverse gear needs manual_gear_shift and gear=-1.
            batch.append(carla.command.ApplyVehicleControl(c.actor, carla.VehicleControl(
                throttle=float(k.throttle), steer=float(k.steer), brake=float(k.brake),
                hand_brake=bool(k.hand_brake), reverse=bool(k.reverse),
                manual_gear_shift=bool(k.manual_gear_shift), gear=int(k.gear))))
        results = self.client.apply_batch_sync(batch, False)
        return tuple(OperationResponse(c.actor, r.error or None, c.frame,
                     self._raw('native/apply.jsonl', {'actor': c.actor, 'frame': c.frame, 'error': r.error or None}))
                     for c, r in zip(commands, results))

    def _clock(self, frame_id, snap):
        """CARLA carries the configured fixed step as float32(0.05) (native probe 2026-10-21: 0.05000000074505806).
        Exactly that value IS the configured 1/20 step, so sim time is the owned frame count x 1/20 from the first
        owned tick. Any other step is kept raw, so the consumer's exact 1/20 contract rejects it (fail safe)."""
        raw_dt, raw_t = snap.timestamp.delta_seconds, snap.timestamp.elapsed_seconds
        if raw_dt != struct.unpack('<f', struct.pack('<f', 0.05))[0]:
            return Fraction(str(raw_dt)), Fraction(str(raw_t))
        if getattr(self, 'clock_origin', None) is None:
            self.clock_origin = (frame_id, Fraction(str(raw_t)))
        start_frame, start_time = self.clock_origin
        return Fraction(1, 20), start_time + (frame_id - start_frame) * Fraction(1, 20)

    def _drain(self):
        pending = getattr(self, 'pending', None)
        while pending:
            sensor_id, packet = pending.popleft()
            hit = packet.pop('collision', None)
            if hit is not None and hasattr(self, 'collisions') and getattr(self, 'clock_origin', None) is not None:
                start_frame, start_time = self.clock_origin  # same owned clock as the frames (x 1/20 from origin)
                self.collisions.append({'boot': self.ownership.boot, 'world': str(self.world.id), 'sensor_id': sensor_id,
                                        'frame': packet['frame'],
                                        'time': start_time + (packet['frame'] - start_frame) * Fraction(1, 20),
                                        **hit})
            self.callbacks[sensor_id](packet)

    def tick(self, timeout_s):
        frame_id = self.world.tick(timeout_s)
        snap = self.world.get_snapshot()
        self._clock(frame_id, snap)  # fixes the owned clock origin before any packet of this tick is timed
        self._drain()
        actors = self.world.get_actors()
        if hasattr(self, 'fixture'):
            return self._bound_frame(frame_id, snap, actors)
        state = {}
        for a in actors:
            if a.id in self.owned:
                t, v = a.get_transform(), a.get_velocity()
                state[a.id] = {'type': a.type_id, 'x': t.location.x, 'y': t.location.y, 'z': t.location.z,
                               'pitch': t.rotation.pitch, 'yaw': t.rotation.yaw, 'roll': t.rotation.roll,
                               'vx': v.x, 'vy': v.y, 'vz': v.z}
                if a.type_id.startswith('vehicle.'):  # applied-control readback (server view), never the command
                    k = a.get_control()
                    state[a.id]['readback'] = {'throttle': k.throttle, 'steer': k.steer, 'brake': k.brake,
                                               'hand_brake': k.hand_brake, 'reverse': k.reverse,
                                               'manual_gear_shift': k.manual_gear_shift, 'gear': k.gear}
        ref = self._raw('native/frames.jsonl', {'frame': frame_id, 'time': snap.timestamp.elapsed_seconds,
                                                'delta_seconds': snap.timestamp.delta_seconds, 'owned': state})
        movable = tuple(a.id for a in actors if a.type_id.startswith(('vehicle.', 'walker.', 'sensor.')))
        dt, simtime = self._clock(frame_id, snap)
        integrity = {'actor_ids': movable, 'writers': (self.ownership.writer,), 'raw_ref': ref, 'settings': self.settings}
        return FrameRecord(self.ownership.boot, str(self.world.id), frame_id, simtime, dt, (), (), integrity)

    def _bound_frame(self, frame_id, snap, actors):
        """Bound mode: the observation record IS the raw per-tick record (it carries the server's pose, velocity and
        control readback values unchanged), so no duplicate server-state file is written (~13 ms each)."""
        movable = tuple(a.id for a in actors if a.type_id.startswith(('vehicle.', 'walker.', 'sensor.')))
        dt, simtime = self._clock(frame_id, snap)
        integrity = {'actor_ids': movable, 'writers': (self.ownership.writer,), 'settings': self.settings,
                     'delta_seconds_raw': snap.timestamp.delta_seconds, 'plan_refs': self.plan_refs}
        npc = next((a for a in actors if self.roles.get(a.id) == 'NPC'), None)
        if npc is not None:
            # Stock NPC = pinned LocalPlanner (no obstacle logic): its only observable priority input is the light.
            red = npc.is_at_traffic_light() and str(npc.get_traffic_light_state()) == 'Red'
            packet = {'boot': self.ownership.boot, 'world': str(self.world.id), 'frame': frame_id, 'actor_id': npc.id,
                      'status': 'RED_LIGHT' if red else 'CLEAR'}
            integrity['npc_controls'] = {**packet, 'witness_refs': (self._raw('native/npc_controls.json', packet,
                                                                                frame_id, simtime),)}
        frames = self._actor_frames(actors)
        kit = getattr(self, 'seal_kit', None)
        if kit is not None:  # per-frame ground proofs / metric context, attached before the observation is written
            frames, added = kit.frame(self, frame_id, simtime, frames)
            integrity.update(added)
        # The consumer requires each frame ref to hold exactly the observation it evaluates (native 2026-10-22).
        observation = self._raw('native/observation.json', {'boot': self.ownership.boot, 'world': str(self.world.id),
                                'frame': frame_id, 'simtime': simtime, 'actors': frames}, frame_id, simtime)
        integrity['frame_refs'], integrity['raw_ref'] = (observation,), observation
        if self.geometry_review is not None and self.previous_actors is not None:
            from m56.catalog import _digest
            from m56.model import CapabilityProof
            limits = {'fixture_hash': _digest(self.fixture), 'previous_frame': frame_id - 1, 'frame': frame_id,
                      'previous_actors': _digest(self.previous_actors), 'actors': _digest(frames)}
            packet = {'kind': 'CONTINUOUS_GEOMETRY', 'method': 'bounded-interframe-body-v1', 'raw_refs': (observation,),
                      'uncertainty': Fraction(1, 1000), 'limits': limits, 'status': 'CORROBORATED'}
            integrity['continuous_geometry'] = CapabilityProof(**packet, review=self.geometry_review(packet))
        self.previous_actors = frames
        return FrameRecord(self.ownership.boot, str(self.world.id), frame_id, simtime, dt, frames, (), integrity)

    def _actor_frames(self, actors):
        from m56.metrics import _metric_station
        from m56.model import ActorFrame, BodyRecord, ControlPacket, Transform6
        out = []
        for a in actors:
            role = self.roles.get(a.id)
            if role is None:
                continue
            t, v, k = a.get_transform(), a.get_velocity(), a.get_control()
            if role not in self.bodies:  # observed bounding box of the spawned actor, never the recipe's guess
                b = a.bounding_box
                self.bodies[role] = BodyRecord((b.location.x, b.location.y, b.location.z),
                                               (b.rotation.pitch, b.rotation.yaw, b.rotation.roll),
                                               (b.extent.x, b.extent.y, b.extent.z), (), a.type_id, {}, {},
                                               self.spawn_refs[role])
            pose = Transform6(t.location.x, t.location.y, t.location.z, t.rotation.pitch, t.rotation.yaw, t.rotation.roll)
            station = _metric_station((pose.x, pose.y, pose.z), self.fixture.routes[role])
            sent = self.applied.get(a.id)
            driver = self.drivers.get(a.id)
            out.append(ActorFrame(role, a.id, pose, (v.x, v.y, v.z), self.bodies[role], station, {},
                                  (sent,) if sent is not None else (),
                                  ControlPacket(k.throttle, k.steer, k.brake, k.hand_brake, k.reverse,
                                                k.manual_gear_shift, k.gear),
                                  None, driver.handle.backend.queue() if driver is not None else 1,
                                  station is not None, None))
        self.applied = {}
        return tuple(sorted(out, key=lambda x: x.role))

    def stop_listeners(self, ids):
        out = []
        for i in ids:
            a = getattr(self, 'listening', {}).pop(i, None) or self.world.get_actor(i)
            if a is not None:
                a.stop()
            self._drain()
            out.append(OperationResponse(i, None if a is not None else 'NOT_FOUND', None,
                                         self._raw('native/cleanup.jsonl', {'stop': i})))
        return tuple(out)

    def destroy(self, ids, timeout_s):
        import carla
        self.client.set_timeout(max(timeout_s, 0.1))
        results = self.client.apply_batch_sync([carla.command.DestroyActor(i) for i in ids], False)
        return tuple(OperationResponse(i, r.error or None, None,
                     self._raw('native/cleanup.jsonl', {'destroy': i, 'error': r.error or None}))
                     for i, r in zip(ids, results))

    def restore(self, ownership, timeout_s):
        self.client.set_timeout(max(timeout_s, 0.1))
        self.world.apply_settings(self.original)
        return OperationResponse(None, None, None, self._raw('native/cleanup.jsonl', {'restore': 'original_settings'}))


# --- T14 physical initialization, one A/B runner, audit-only resume ---
# Clock contract is the consumer's (_initialization_integrity, T09): boundary = first post-spawn observation,
# settle >= 1 s without motion, ready <= settled + 15 s after an 11-frame .50 s hold, end - ready <= 60,
# end - boundary <= 76.5. The runner never writes reviews; unreviewed packets stay invalid/uncertain.

SETTLE_S, READY_LIMIT_S, PHASE_LIMIT_S, VALIDATION_S, TOTAL_S = 1, 15, 60, 60, Fraction(153, 2)
HOLD_S = Fraction(1, 2)


def _speed(actor):
    return Fraction(str(sum(v * v for v in actor.velocity) ** .5))


def _station(actor, fixture):
    from m56.metrics import _metric_station
    return _metric_station((actor.pose.x, actor.pose.y, actor.pose.z), fixture.routes[actor.role])


def _ready(frames, settled, fixture):
    """Same predicate the consumer re-checks: .50 s hold at target speed tracking the frozen terminal marker."""
    meta, last = fixture.environment['readiness'], frames[-1]
    hold = [f for f in frames if last.simtime - HOLD_S <= f.simtime <= last.simtime]
    if last.frame <= settled.frame or len(hold) != 11 or hold[0].simtime != last.simtime - HOLD_S:
        return False
    for f in hold:
        for a in f.actors:
            target, marker = meta['targets_mps'].get(a.role), meta['markers_m'].get(a.role)
            station = _station(a, fixture)
            if (target is None or marker is None or station is None or abs(_speed(a) - target) > Fraction(1, 10)
                    or abs(station - (marker - target * (last.simtime - f.simtime))) > Fraction(1, 10)):
                return False
    return True


def _observed_refs(value):
    """Every SourceRef the backend attached to an observation (frames, plans, priority, capability raws/reviews)."""
    from collections.abc import Mapping
    from dataclasses import fields as dc_fields, is_dataclass
    if isinstance(value, SourceRef):
        yield value
    elif isinstance(value, Mapping):
        for v in value.values():
            yield from _observed_refs(v)
    elif isinstance(value, (tuple, list)):
        for v in value:
            yield from _observed_refs(v)
    elif is_dataclass(value):
        for f in dc_fields(value):
            yield from _observed_refs(getattr(value, f.name))


def _ref(store, relative):
    path = store.root / relative
    data = path.read_bytes()
    return SourceRef(str(path), hashlib.sha256(data).hexdigest(), len(data), '1', 'runner', 'RUNNER_RECORD')


def _bounded(response):
    """Same dispatch rule the consumer replays (_phase_integrity): bounded reverse producers."""
    meta = response.phases.get('reverse', response.phases.get('f_script', {}))
    return isinstance(meta, dict) and (
        (response.actor_role == 'EGO' and response.action_id == 'B' and meta.get('mechanism') in ('F03', 'F06-ALT1'))
        or (response.actor_role == 'NPC' and response.action_id == 'NPC_COMMON' and meta.get('mechanism') == 'F06-ALT1'))


def _known_events(frames, fixture):
    """Online event view the consumer will authenticate: detected events plus STOP_AFTER_TRIGGER.

    ponytail: full re-detection every tick is O(n^2) (~1.5 s/tick at ~200 frames offline), which would exceed the
    300 s outer wall deadline of a native episode. A streaming/incremental detector in metrics.py is required
    before any native A/B; until then native runs would stop with OUTER_TIMEOUT (raw kept)."""
    from m56.metrics import detect_events
    events = tuple(detect_events(tuple(frames), fixture))
    trigger = next((e for e in events if e.name == 'TRIGGER'), None)
    if trigger is not None:
        post = tuple(f for f in frames if f.frame >= trigger.frame)
        stop = next((e for e in detect_events(post, fixture) if e.name == 'STOP_CONFIRMED'), None)
        if stop is not None:
            events = (*events, replace(stop, name='STOP_AFTER_TRIGGER'))
    return events


def _commands(frames, boundary, states, responses, registry_ids, fixture, known=()):
    """Issue each response's command from the latest observation and the events admitted at that frame."""
    from m56.response import reverse_intent, step_response
    frame = frames[-1] if frames else boundary
    admitted = tuple(e for e in known if e.frame <= frame.frame and e.time <= frame.simtime)
    out = []
    for r in responses:
        actor = registry_ids.get(r.actor_role)
        if actor is None:
            continue
        state = replace(states[r.actor_role], events=admitted)
        if _bounded(r) and any(e.name == 'TRIGGER' for e in admitted):
            # As the consumer replays: CAPTURE_START is a program timer anchor, never passed to the bounded kernel.
            state = replace(state, events=tuple(e for e in admitted if e.name != 'CAPTURE_START'))
            rs = reverse_intent(frame, state, r, fixture)
        else:
            rs = step_response(frame, state, r)
        states[r.actor_role] = rs.state
        out.append(replace(rs.command, actor=actor))
    return tuple(out)


def run_episode(context, fixture, action_id):
    """Signal admission (<=60 s, before spawn) -> spawn -> settle/readiness -> validation -> cleanup -> seal ->
    the real evaluate_episode. No velocity forcing, teleport, reload, retry or verdict shaping."""
    import time
    from m56.model import ScriptState
    store, backend = context.store, context.backend
    t0 = time.monotonic()
    wall = t0 + float(context.deadlines.get('outer_s', 300))
    reasons, frames, registry, previous = [], [], None, None

    def fail(kind, error):
        append_record(store, 'runner/failure.json', {'kind': kind, 'error': repr(error), 'frames_seen': len(frames)})
        reasons.append(kind)

    def tick(commands):
        if time.monotonic() > wall:
            fail('OUTER_TIMEOUT', 'outer wall deadline')
            return None
        try:
            if registry is None:
                return backend.tick(float(context.deadlines['tick_s']))
            return tick_owned(context, registry, commands, previous)
        except Exception as e:  # tick/RPC failure: keep raw, never rerun
            fail('TICK_TIMEOUT' if isinstance(e, TimeoutError) else 'TICK_ERROR', e)
            return None

    predicate, phase_packet = fixture.environment.get('phase_predicate'), None
    if predicate is not None:  # observe only: no reload, no phase hunting, no actor mutation
        start = None
        while phase_packet is None:
            f = tick(())
            if f is None:
                return _seal_stop(context, reasons, None)
            start = f.simtime if start is None else start
            seen = f.integrity.get('phase')
            if seen is not None and all(seen.get(k) == v for k, v in predicate.items()):
                phase_packet = {'frame': f.frame, 'time': str(f.simtime), 'observed': seen}
            elif f.simtime - start >= PHASE_LIMIT_S:
                reasons.append('BLOCKED_SIGNAL_ADMISSION')
                return _seal_stop(context, reasons, None)
    if set(fixture.environment.get('readiness') or ()) != {'targets_mps', 'markers_m'}:
        return _seal_stop(context, ['READINESS_METADATA_MISSING'], None)
    spawned = spawn_owned(context, fixture)
    if not isinstance(spawned, OwnedRegistry):
        return _seal_stop(context, spawned.reasons, spawned if isinstance(spawned, EpisodeVerdict) else None)
    registry = spawned
    ids = {r.role: x.actor_id for r, x in zip(fixture.actors, registry.spawn_responses)}
    responses = tuple(r for r in fixture.responses if r.actor_role != 'EGO' or r.action_id == action_id)
    states, boundary, settled, ready, known, capture = {}, None, None, None, (), ()
    while True:
        commands = ()
        if boundary is not None and responses:  # witness requires attributed commands on every recorded frame
            try:
                commands = _commands(frames, boundary, states, responses, ids, fixture, (*capture, *known))
            except Exception as e:  # unsupported/blocked script: stop, never fall back
                fail('RESPONSE_BLOCKED', e)
                break
        f = tick(commands)
        if f is None:
            break
        if isinstance(f, EpisodeVerdict):
            reasons += list(f.reasons)
            break
        previous = f.frame
        if boundary is None:
            boundary = f
            # The consumer replays programs with CAPTURE_START at the boundary observation; the runner must too, or a
            # program released at CAPTURE_START + delay never leaves its first phase (native 2026-10-22).
            capture = (EventRecord('CAPTURE_START', f.frame, f.simtime, tuple(f.integrity.get('frame_refs', ()))),)
            # Each response starts in its own frozen program phase; one without a program is blocked downstream.
            states = {r.actor_role: ScriptState((r.phases.get('program') or {}).get('initial', 'UNSET'), f.simtime, ())
                      for r in responses}
            continue
        frames.append(f)
        known = _known_events(frames, fixture) if responses else ()
        if settled is None:
            if any(_speed(a) > Fraction(1, 10) for a in f.actors):
                reasons.append('SETTLE_MOVEMENT')  # never damped or teleported into place
                break
            if f.simtime - boundary.simtime >= SETTLE_S:
                settled = f
            continue
        if ready is None:
            if _ready(frames, settled, fixture):
                ready = f
            elif f.simtime - settled.simtime >= READY_LIMIT_S:
                reasons.append('READINESS_NOT_REACHED')
                break
            continue
        if any(e.name == 'DESTINATION_CONFIRMED' for e in known):
            break  # endpoint observed; the evaluator still checks progress/forward control up to it
        ego = next((a for a in f.actors if a.role == 'EGO'), None)
        if ego is not None and ego.plan_queue == 0:
            reasons.append('EARLY_EMPTY_PLAN')  # whether that is FAILED is the evaluator's call
            break
        if f.simtime - ready.simtime >= VALIDATION_S or f.simtime - boundary.simtime >= TOTAL_S:
            break
    fence = getattr(context.backend, 'fence', None)
    if fence is not None and frames:  # delivery ack fence: one owned tick after the last frame, queue drained
        fence(frames[-1].frame)
    cleanup = cleanup_owned(context, registry)
    wall_interval = (Fraction(0), Fraction(round(time.monotonic() - t0)))
    if ready is None:
        # Observations existed but no validation started: readiness, not the action, is incomplete.
        return _seal_stop(context, reasons, _verdict('CONFIRMED', 'INCOMPLETE', 'UNKNOWN', reasons), frames, cleanup)
    return _seal(context, fixture, frames, boundary, settled, ready, registry, phase_packet, cleanup, reasons,
                 wall_interval)


def _seal_stop(context, reasons, verdict, frames=(), cleanup=None):
    from m56.evidence import seal
    from m56.model import EpisodeEvidence
    append_record(context.store, 'runner/stop.json', {'reasons': list(reasons),
                  'cleanup': None if cleanup is None else cleanup.status})
    manifest = seal(context.store)
    # Nothing evaluable was observed: unobserved axes are NOT_RUN, never a guessed state.
    v = verdict or _verdict('NOT_RUN', 'NOT_RUN', 'NOT_RUN', reasons)
    v = replace(v, reasons=tuple(dict.fromkeys((*v.reasons, *reasons))))
    return EpisodeEvidence(tuple(frames), (_ref(context.store, 'journal.jsonl'),), None, (),
                           _ref(context.store, manifest.relativepath), {}, v,
                           frames[-1].simtime if frames else Fraction(0))


def _seal(context, fixture, frames, boundary, settled, ready, registry, phase_packet, cleanup, reasons, wall_interval):
    """Write the runner's own observations in the consumer schemas; reviews/recipes are never fabricated here."""
    from m56.catalog import _digest
    from m56.evidence import seal, snapshot_sources
    from m56.metrics import evaluate_episode
    from m56.model import EpisodeEvidence
    store, meta = context.store, fixture.environment['readiness']
    kit = getattr(context.backend, 'seal_kit', None)  # external reviewer/producer (G4), never the runner itself
    parents = getattr(context.backend, 'sensor_parents', None) or {}
    append_record(store, 'fixture.json', fixture)
    append_record(store, 'trajectory.json', tuple(frames))
    streams = {'pre_observation_ref': boundary,
               'w01_ref': {'identity': context.identity, 'ownership': context.ownership,
                           'actors': {a.role: a.id for a in boundary.actors}, 'fixture_hash': _digest(fixture),
                           'wall_interval': wall_interval, 'observed_tick_owner': context.ownership.tick_owner},
               # recipe_ref stays None until a frozen, reviewed readiness recipe exists (G4); settings are the
               # backend-observed ones. Without that review the consumer reports INITIALIZATION_INVALID.
               'initialization_ref': {'method': 'recorded-initialization-v1', 'fixture_hash': _digest(fixture),
                                      'boundary_hash': _digest(boundary), 'settled_frame': settled.frame,
                                      'ready_frame': ready.frame, 'targets_mps': meta['targets_mps'],
                                      'ready_markers_m': meta['markers_m'],
                                      'recipe_ref': kit.initialization_recipe(store) if kit is not None else None,
                                      'settings': boundary.integrity.get('settings')},
               'sensor_registry_ref': {'boot': registry.boot, 'world': registry.world,
                                       'sensors': {str(i): parents.get(i, i) for i in registry.owned_sensor_ids}},
               'collision_ref': list(getattr(context.backend, 'collisions', ()))}
    pointers = {'trajectory_ref': _ref(store, 'trajectory.json')}
    for key, value in streams.items():
        append_record(store, f'{key}.json', value)
        pointers[key] = _ref(store, f'{key}.json')
    extra = ()
    if kit is not None:  # reviews/proofs over the written streams; bound to their exact bytes before the seal
        added, extra = kit.finish(store, fixture, tuple(frames), boundary, pointers, context)
        for key, value in added.items():
            append_record(store, f'{key}.json', value)
            pointers[key] = _ref(store, f'{key}.json')
    append_record(store, 'runner/stop.json', {'reasons': list(reasons), 'cleanup': cleanup.status,
                                              'cleanup_survivors': list(cleanup.survivors), 'phase': phase_packet})
    # Observation packets only (integrity + per-actor ground proofs); body/route metadata belongs to the fixture.
    raw = tuple(dict.fromkeys((*(r for f in (boundary, *frames)
                                 for r in _observed_refs((f.integrity, tuple(a.ground for a in f.actors)))), *extra)))
    snapshot = snapshot_sources(store, raw)
    if snapshot.status != 'INTEGRITY_VALID':
        reasons = [*reasons, 'SOURCE_SNAPSHOT_FAILED', *snapshot.reasons]
    manifest = seal(store)
    evidence = EpisodeEvidence(tuple(frames), (_ref(store, 'journal.jsonl'),), _ref(store, 'fixture.json'),
                               (*pointers.values(), *raw), _ref(store, manifest.relativepath), pointers, None,
                               frames[-1].simtime)
    verdict = evaluate_episode(evidence, fixture)
    verdict = replace(verdict, reasons=tuple(dict.fromkeys((*verdict.reasons, *reasons))))
    return replace(evidence, verdict=verdict)


def _with(context, **changes):
    try:
        return replace(context, **changes)
    except TypeError:  # SimpleNamespace contexts in offline tests
        return SimpleNamespace(**{**vars(context), **changes})


def run_ab(context, fixture, scene):
    """Exactly one A then one B, each in its own create-exclusive namespace; never auto-repeated."""
    from m56.catalog import _digest
    from m56.evidence import open_run
    from m56.model import RunSummary
    root = context.store.root / 'episodes' / scene
    if root.exists():
        return RunSummary((), (), (f'{scene}:NAMESPACE_EXISTS',), (), ())
    results, phases = [], {}
    for action in ('A', 'B'):
        store = open_run(root / action, context.store.run_id, context.store.writer)
        ev = run_episode(_with(context, store=store), fixture, action)
        stops = [json.loads(l) for l in (store.root / 'runner/stop.json').read_text(encoding='utf-8').splitlines()]
        phases[action] = stops[-1].get('phase')
        results.append(ev)
    report = {'scene': scene, 'fixture_hash': _digest(fixture), 'attempted_actions': ['A', 'B'],
              'npc_program_hashes': sorted({r.hash for r in fixture.responses if r.actor_role == 'NPC'}),
              'observed_phases': phases,
              'actual_phases_identical': phases['A'] is not None and phases['A'] == phases['B']}
    (root / 'ab_report.json').write_text(json.dumps(report, indent=1, default=str), encoding='utf-8')
    return tuple(results)


def resume_audit(store):
    """Offline: verify sealed episode namespaces and summarize them. Never binds, never executes."""
    from m56.evidence import verify_manifest
    from m56.model import RunSummary
    attempted, completed, invalid = [], [], []
    for manifest in sorted((store.root / 'episodes').glob('*/*/manifest.json')):
        name = f'{manifest.parent.parent.name}/{manifest.parent.name}'
        attempted.append(name)
        (completed if verify_manifest(manifest.parent).status == 'INTEGRITY_VALID' else invalid).append(name)
    return RunSummary(tuple(attempted), tuple(completed), (), tuple(invalid), ())


# --- Offline reconstruction for resume/export (never executes, never binds) ---

_POINTERS = ('pre_observation_ref', 'w01_ref', 'initialization_ref', 'sensor_registry_ref', 'collision_ref')


def load_episode(root):
    """Rebuild a sealed runner episode from its namespace; None when unsealed, tampered or never started."""
    from m56.evidence import _read_trajectory, verify_manifest
    from m56.model import EpisodeEvidence, decode_record
    root = Path(root)
    if verify_manifest(root).status != 'INTEGRITY_VALID' or not (root / 'trajectory.json').exists():
        return None
    store = SimpleNamespace(root=root)
    pointers = {'trajectory_ref': _ref(store, 'trajectory.json'),
                **{k: _ref(store, f'{k}.json') for k in _POINTERS if (root / f'{k}.json').exists()}}
    raw = []
    for line in (root / 'journal.jsonl').read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        if row.get('operation') == 'SOURCE_SNAPSHOT_INTENT':
            raw.append(decode_record('SourceRef', row['source']))
    frames = _read_trajectory(pointers['trajectory_ref'])
    if frames is None:
        return None
    return EpisodeEvidence(frames, (_ref(store, 'journal.jsonl'),), _ref(store, 'fixture.json'),
                           (*pointers.values(), *raw), _ref(store, 'manifest.json'), pointers, None, frames[-1].simtime)


def eligibility_from_run(run_root):
    """Per scene: both sealed actions + a human D09 review supplied at reviews/<scene>.json -> real compare_ab.
    Missing reviews or episodes yield no record (the release gate reports the AB_PROOF deficit)."""
    from m56.evidence import _decode_source_record
    from m56.metrics import compare_ab
    from m56.model import CompiledFixture, EligibilityRecord, ReviewRecord, decode_record, load_json
    out = []
    for scene in sorted(p for p in (Path(run_root) / 'episodes').iterdir() if p.is_dir()):
        a, b = load_episode(scene / 'A'), load_episode(scene / 'B')
        review_path = Path(run_root) / 'reviews' / f'{scene.name}.json'
        if a is None or b is None or not review_path.exists():
            continue
        review = decode_record('ReviewRecord', load_json(review_path))
        fixture = _decode_source_record('CompiledFixture', a.fixture)
        if not isinstance(review, ReviewRecord) or not isinstance(fixture, CompiledFixture):
            continue
        verdict = compare_ab(a, b, fixture.pair, review)
        out.append(EligibilityRecord(scene.name, verdict, (a.fixture, b.fixture), (review,),
                                     (a.manifest, b.manifest)))
    return tuple(out)


def _owned_factory(context):
    """Transport seam for owned runs: binds carla only after admission (see bind_owned)."""
    import carla
    client = carla.Client(context.ownership.host, context.ownership.ports['rpc'])
    client.set_timeout(float(context.deadlines['rpc_s']))
    return OwnedCarlaBackend(client, context.ownership, context.store)


def bind_owned(context):
    if context.admission.status != 'ADMITTED':
        return BlockedPreparation(context.admission.status, context.admission.reasons)
    missing = [op for op in ('SETTINGS', 'SPAWN', 'TICK', 'APPLY', 'DESTROY') if op not in context.ownership.allowed_ops]
    if missing:
        return BlockedPreparation('BLOCKED_AUTHORITY', tuple(f'OP_NOT_OWNED:{op}' for op in missing))
    return _owned_factory(context)
