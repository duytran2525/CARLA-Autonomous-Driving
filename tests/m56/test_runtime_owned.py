"""T13 owned spawn/tick/cleanup kernels over a fake Backend; no native import."""
from fractions import Fraction as F
import json
import time
from types import SimpleNamespace

import pytest

from m56.model import (ActorRecipe, AdmissionVerdict, CommandRecord, EpisodeVerdict, FrameRecord,
                       OperationResponse, OwnedRegistry, SourceRef, SpawnResponse)

REF = SourceRef('file:///raw.json', 'b'*64, 1, '1', 'native', 'NATIVE_RAW')


class Backend:
    """Native-boundary recorder: every call is appended to self.calls."""
    def __init__(self, world='w7', spawn_ids=(101, 102), fail=(), destroy_delay=0.):
        self.world, self.spawn_ids, self.fail, self.destroy_delay = world, spawn_ids, fail, destroy_delay
        self.calls, self.destroyed_ids, self.destroy_batches, self.server_management_calls = [], [], [], []
        self.frame, self.actor_ids, self.writers = 10, None, ('m56',)

    def identity(self):
        self.calls.append('identity')
        return SimpleNamespace(boot='b1', world=self.world)

    def spawn(self, actors, due_tick_cue):
        self.calls.append(('spawn', due_tick_cue))
        return tuple(SpawnResponse(i, 'ERR' if i is None else None, REF) for i in self.spawn_ids)

    def listen(self, sensor_id, callback):
        self.calls.append(('listen', sensor_id))
        return OperationResponse(sensor_id, None, None, REF)

    def apply(self, commands):
        self.calls.append(('apply', tuple(c.actor for c in commands)))
        return tuple(OperationResponse(c.actor, None, self.frame, REF) for c in commands)

    def tick(self, timeout_s):
        self.calls.append(('tick', timeout_s))
        self.frame += 1
        return FrameRecord('b1', self.world, self.frame, F(self.frame, 20), F(1, 20), (), (),
                           {'actor_ids': self.actor_ids or (101, 102), 'writers': self.writers})

    def stop_listeners(self, ids):
        self.calls.append(('stop', ids))
        return tuple(OperationResponse(i, None, None, REF) for i in ids)

    def destroy(self, ids, timeout_s):
        self.calls.append(('destroy', ids, timeout_s)); self.destroy_batches.append(ids)
        time.sleep(self.destroy_delay)
        self.destroyed_ids += [i for i in ids if i not in self.fail]
        return tuple(OperationResponse(i, 'ERR' if i in self.fail else None, None, REF) for i in ids)

    def restore(self, ownership, timeout_s):
        self.calls.append('restore')
        return OperationResponse(None, None, None, REF)


def actor(role, bp):
    return ActorRecipe(role, bp, F(0), None, {}, {}, None)


@pytest.fixture
def rt(tmp_path):
    import m56.runtime as runtime
    from m56.evidence import open_run
    backend = Backend()
    ctx = SimpleNamespace(backend=backend, identity=SimpleNamespace(boot='b1', world='w7'),
                          ownership=SimpleNamespace(allowed_ops=('SPAWN', 'TICK', 'APPLY', 'DESTROY')),
                          admission=AdmissionVerdict('ADMITTED', ()), store=open_run(tmp_path/'run', 'r1', 'm56'),
                          deadlines={'tick_s': 2, 'cleanup_s': 15}, scope_mode='SINGLE_EPISODE', scope_phase='RUNNING')
    fixture = SimpleNamespace(actors=(actor('EGO', 'vehicle.audi.a2'), actor('NPC', 'vehicle.audi.a2')))
    return SimpleNamespace(m=runtime, b=backend, ctx=ctx, fixture=fixture)


def ns(base, **kw):
    return SimpleNamespace(**{**vars(base), **kw})


def registry(vehicles=(101, 102), sensors=(), world='w7'):
    return OwnedRegistry('b1', world, vehicles, sensors, ())


def cmd(actor_id, frame=10):
    return CommandRecord(actor_id, frame, frame + 1, 'FORWARD', F(0), F(0), None, None, 'test', 'h')


def journal_registry(store):
    rows = [json.loads(l) for l in (store.root/'owned/registry.jsonl').read_text(encoding='utf-8').splitlines()]
    return rows[-1]


def test_lost_world_never_destroys(rt):
    rt.b.world = 'w8'
    out = rt.m.cleanup_owned(rt.ctx, registry())
    assert out.status == 'BLOCKED_CLEANUP' and rt.b.destroyed_ids == [] and out.survivors == (101, 102)


def test_unadmitted_context_never_spawns(rt):
    out = rt.m.spawn_owned(ns(rt.ctx, admission=AdmissionVerdict('BLOCKED_AUTHORITY', ('X',))), rt.fixture)
    assert out.status == 'BLOCKED_AUTHORITY' and rt.b.calls == []


def test_spawn_uses_batch_without_tick_cue(rt):
    out = rt.m.spawn_owned(rt.ctx, rt.fixture)
    assert isinstance(out, OwnedRegistry) and out.owned_vehicle_ids == (101, 102)
    assert ('spawn', False) in rt.b.calls and not any(isinstance(c, tuple) and c[0] == 'tick' for c in rt.b.calls)
    assert journal_registry(rt.ctx.store)['owned_vehicle_ids'] == [101, 102]


def test_partial_spawn_keeps_success_ids(rt):
    rt.b.spawn_ids = (101, None)
    out = rt.m.spawn_owned(rt.ctx, rt.fixture)
    assert isinstance(out, EpisodeVerdict) and out.spawn == 'FAILED'
    assert journal_registry(rt.ctx.store)['owned_vehicle_ids'] == [101]
    movement_count = sum(1 for c in rt.b.calls if isinstance(c, tuple) and c[0] in ('apply', 'tick'))
    assert movement_count == 0 and rt.b.calls.count(('spawn', False)) == 1


def test_unknown_spawn_id_escalates(rt):
    rt.b.spawn_ids = (101,)
    out = rt.m.spawn_owned(rt.ctx, rt.fixture)
    assert out.spawn == 'FAILED' and 'SPAWN_ID_UNKNOWN' in out.reasons
    assert rt.b.calls.count(('spawn', False)) == 1  # fallback_count == 0


def test_sensor_before_warmup(rt):
    fixture = SimpleNamespace(actors=rt.fixture.actors + (actor('EGO_COLLISION', 'sensor.other.collision'),))
    rt.b.spawn_ids = (101, 102, 201)
    reg = rt.m.spawn_owned(rt.ctx, fixture)
    assert reg.owned_sensor_ids == (201,) and reg.owned_vehicle_ids == (101, 102)
    rt.m.tick_owned(rt.ctx, reg, (), previous=10)
    listen = rt.b.calls.index(('listen', 201)); warmup = rt.b.calls.index(('tick', 2.0))
    assert listen < warmup


def test_tick_applies_only_owned_and_correlates_frame(rt):
    frame = rt.m.tick_owned(rt.ctx, registry(), (cmd(101),), previous=10)
    assert isinstance(frame, FrameRecord) and frame.frame == 11
    assert rt.b.calls[0] == ('apply', (101,))


def test_foreign_command_never_applied(rt):
    out = rt.m.tick_owned(rt.ctx, registry(), (cmd(999),), previous=10)
    assert out.witness == 'INVALID' and 'FOREIGN_COMMAND:999' in out.reasons and rt.b.calls == []


def test_extra_writer_invalidates(rt):
    rt.b.writers = ('m56', 'm55')
    out = rt.m.tick_owned(rt.ctx, registry(), (), previous=10)
    assert out.physical == 'FAILED' and out.witness == 'INVALID'


def test_foreign_actor_invalidates(rt):
    rt.b.actor_ids = (101, 102, 999)
    out = rt.m.tick_owned(rt.ctx, registry(), (), previous=10)
    assert out.witness == 'INVALID' and 'FOREIGN_ACTOR:999' in out.reasons


def test_tick_gap_invalidates(rt):
    rt.b.frame = 12
    out = rt.m.tick_owned(rt.ctx, registry(), (), previous=10)
    assert out.witness == 'INVALID' and 'TICK_GAP:10->13' in out.reasons


def test_sensor_destroy_before_vehicle(rt):
    out = rt.m.cleanup_owned(rt.ctx, registry(sensors=(201, 202)))
    assert rt.b.destroy_batches == [(201, 202), (101, 102)]
    assert rt.b.calls.index(('stop', (201, 202))) < rt.b.calls.index(('destroy', (201, 202), pytest.approx(15, abs=1)))
    assert out.status == 'CLEANED' and out.destroyed == (201, 202, 101, 102)


def test_cleanup_survivor_escalates_without_retry(rt):
    rt.b.fail = (102,)
    out = rt.m.cleanup_owned(rt.ctx, registry())
    assert out.status == 'ESCALATED' and out.survivors == (102,) and len(rt.b.destroy_batches) == 1


def test_cleanup_deadline_no_unbounded_loop(rt):
    rt.b.destroy_delay = .3
    ctx = ns(rt.ctx, deadlines={**rt.ctx.deadlines, 'cleanup_s': .2})
    start = time.monotonic()
    out = rt.m.cleanup_owned(ctx, registry(sensors=(201,)))
    assert out.status == 'BLOCKED_CLEANUP' and out.survivors == (101, 102)
    assert rt.b.destroy_batches == [(201,)] and time.monotonic() - start <= 15


def test_server_left_alive(rt):
    rt.m.cleanup_owned(rt.ctx, registry())
    assert 'restore' not in rt.b.calls and rt.b.server_management_calls == []
    ending = ns(rt.ctx, scope_phase='ENDING', ownership=SimpleNamespace(allowed_ops=('DESTROY', 'RESTORE')))
    rt.m.cleanup_owned(ending, registry())
    assert rt.b.calls.count('restore') == 1


def test_owned_adapter_sends_every_control_field(monkeypatch):
    # Reverse needs manual_gear_shift + gear=-1 on the server; a dropped field silently drives forward.
    import sys
    from m56.model import ControlPacket
    from m56.runtime import OwnedCarlaBackend
    sent = []
    carla = SimpleNamespace(VehicleControl=lambda **kw: SimpleNamespace(**kw),
                            command=SimpleNamespace(ApplyVehicleControl=lambda actor, control: (actor, control)))
    monkeypatch.setitem(sys.modules, 'carla', carla)
    backend = OwnedCarlaBackend.__new__(OwnedCarlaBackend)  # no server: only the batch translation is exercised
    backend.client = SimpleNamespace(apply_batch_sync=lambda batch, cue: sent.extend(batch) or [SimpleNamespace(error='')] * len(batch))
    backend._raw = lambda stream, record: REF
    control = ControlPacket(.25, 0., .3, False, True, True, -1)
    backend.apply((CommandRecord(7, 1, 2, 'REVERSE', F(0), F(0), control, None, 'REVERSE', 'h'),))
    (actor, applied), = sent
    assert actor == 7 and vars(applied) == {'throttle': .25, 'steer': 0., 'brake': .3, 'hand_brake': False,
                                            'reverse': True, 'manual_gear_shift': True, 'gear': -1}


def test_owned_adapter_attaches_sensors_to_real_parent_ids(monkeypatch):
    import sys
    from m56.model import Transform6
    from m56.runtime import OwnedCarlaBackend
    batches = []
    blueprint = SimpleNamespace(has_attribute=lambda k: False)
    carla = SimpleNamespace(Transform=lambda loc, rot: (loc, rot), Location=lambda *a: a, Rotation=lambda **kw: kw,
                            command=SimpleNamespace(SpawnActor=lambda bp, tf, parent=None: ('SPAWN', parent)))
    monkeypatch.setitem(sys.modules, 'carla', carla)
    ids = iter((41, 42, 90))
    backend = OwnedCarlaBackend.__new__(OwnedCarlaBackend)
    backend.world = SimpleNamespace(get_blueprint_library=lambda: SimpleNamespace(find=lambda name: blueprint))
    backend.client = SimpleNamespace(apply_batch_sync=lambda batch, cue: batches.append(batch) or
                                     [SimpleNamespace(error='', actor_id=next(ids)) for _ in batch])
    backend._raw, backend.owned = (lambda stream, record: REF), set()
    pose = Transform6(0., 0., 0., 0., 0., 0.)
    actors = (ActorRecipe('EGO', 'vehicle.audi.a2', F(0), pose, {}, {}, None),
              ActorRecipe('NPC', 'vehicle.audi.a2', F(0), pose, {}, {}, None),
              ActorRecipe('EGO_COLLISION', 'sensor.other.collision', F(0), pose, {'attach_to_role': 'EGO'}, {}, None),
              ActorRecipe('LOOSE', 'sensor.other.collision', F(0), pose, {}, {}, None))
    out = backend.spawn(actors, False)
    assert batches == [[('SPAWN', None), ('SPAWN', None)], [('SPAWN', 41)]]  # parent = EGO's actor id, not an index
    assert [(r.actor_id, r.error) for r in out] == [(41, None), (42, None), (90, None), (None, 'SENSOR_PARENT_UNDECLARED')]
    assert backend.owned == {41, 42, 90}


def test_owned_adapter_clock_is_exact_only_for_the_float32_fixed_step():
    from m56.runtime import OwnedCarlaBackend
    backend = OwnedCarlaBackend.__new__(OwnedCarlaBackend)
    snap = lambda dt, t: SimpleNamespace(timestamp=SimpleNamespace(delta_seconds=dt, elapsed_seconds=t))
    f32 = 0.05000000074505806  # CARLA's float32(0.05), observed natively on 2026-10-21
    assert backend._clock(42, snap(f32, 7.5)) == (F(1, 20), F(15, 2))
    assert backend._clock(45, snap(f32, 7.650000002)) == (F(1, 20), F(15, 2) + F(3, 20))  # frame count, not drift
    assert backend._clock(46, snap(0.06, 7.71)) == (F('0.06'), F('7.71'))  # unknown step stays raw: consumer rejects


def test_owned_adapter_keeps_listened_sensors_alive_until_stopped():
    from m56.runtime import OwnedCarlaBackend
    calls = []
    sensor = SimpleNamespace(listen=lambda cb: calls.append('listen'), stop=lambda: calls.append('stop'))
    backend = OwnedCarlaBackend.__new__(OwnedCarlaBackend)
    backend.world = SimpleNamespace(get_actor=lambda i: sensor)
    backend._raw = lambda stream, record: REF
    backend.listen(9, lambda packet: None)
    assert backend.listening == {9: sensor}  # a dropped object makes CARLA unsubscribe the stream
    backend.stop_listeners((9,))
    assert calls == ['listen', 'stop'] and backend.listening == {}


def test_owned_adapter_hands_sensor_packets_to_the_runner_thread_only():
    import threading
    from m56.runtime import OwnedCarlaBackend
    hooks, got = [], []
    sensor = SimpleNamespace(listen=hooks.append, stop=lambda: None)
    backend = OwnedCarlaBackend.__new__(OwnedCarlaBackend)
    backend.world = SimpleNamespace(get_actor=lambda i: sensor)
    backend._raw = lambda stream, record: REF
    backend.listen(9, lambda packet: got.append((threading.get_ident(), packet['frame'])))
    worker = threading.Thread(target=hooks[0], args=(SimpleNamespace(frame=77, timestamp=3.85),))
    worker.start(); worker.join()
    assert got == []  # nothing written from CARLA's thread (exclusive RunStore writer lock)
    backend._drain()
    assert got == [(threading.get_ident(), 77)]


def test_readback_is_the_command_or_its_float32_image_only():
    from dataclasses import replace
    from m56.evidence import _f32_control
    from m56.model import ControlPacket
    sent = ControlPacket(0., 0., .3, False, True, True, -1)
    assert _f32_control(sent).brake == 0.30000001192092896  # what CARLA reads back for brake .3 (native 22/10)
    assert sent in (sent, _f32_control(sent)) and _f32_control(sent) in (sent, _f32_control(sent))
    assert replace(sent, brake=.31) not in (sent, _f32_control(sent))


def test_automatic_transmission_readback_gear_is_not_the_command():
    from dataclasses import replace
    from m56.evidence import _readback_matches
    from m56.model import ControlPacket
    hold = ControlPacket(0., 0., .3, False, False, False, 1)
    assert _readback_matches(hold, replace(hold, brake=0.30000001192092896, gear=0))  # native 22/10
    manual = ControlPacket(.25, 0., 0., False, True, True, -1)
    assert not _readback_matches(manual, replace(manual, gear=1))  # manual gear must match exactly
    assert not _readback_matches(hold, replace(hold, brake=.31, gear=0))
