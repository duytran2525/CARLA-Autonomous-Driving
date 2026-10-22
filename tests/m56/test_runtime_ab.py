"""T14 physical initialization / one A-B runner / audit-only resume over a scripted fake Backend.

The fake replays literal synthetic positions tick by tick; the runner (not the fake) enforces every
horizon, and all physical verdicts come from the real evaluate_episode. No native import.
"""
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import json
from types import SimpleNamespace

import pytest

from m56.model import (ActorFrame, ActorRecipe, AdmissionVerdict, BodyRecord, CapabilityProof, CompiledFixture,
                       ControlPacket, Domain, DirectedRoute, ReviewRecord,
                       FrameRecord, FrozenMetricPair, OperationResponse, OwnershipReceipt, RuntimeIdentity,
                       Section, SourceRef, SpawnResponse, Transform6)

DT = F(1, 20)
META = SourceRef('synthetic://metadata', 'a'*64, 1, 'test', 'literal', 'SYNTHETIC_TEST')
BODY = BodyRecord((0., 0., 0.), (0., 0., 0.), (.5, .25, .25), (), 'vehicle.audi.a2', {}, {}, META)


def section(x):
    return Section(tuple((float(x), y, z) for y in (-1., 1.) for z in (-1., 1.)), (1., 0., 0.), F(x), {})


def fixture(**environment):
    route = DirectedRoute((), (Transform6(0., 0., 0., 0., 0., 0.), Transform6(30., 0., 0., 0., 0., 0.)),
                          (F(0), F(30)), 'b'*64, (META,), F(20))
    domain = Domain(section(10), section(12), section(10), section(12), (), {'category': 'C'}, (META,), 'c'*64)
    pair = FrozenMetricPair(('d_yield_m', 't_entry_s'), ('m', 's'), ('forward_distance', 'elapsed'),
                            (('TRIGGER', 'CLEAR_N_CONFIRMED'), ('TRIGGER', 'E_ENTRY')), 'test-reference', 'd'*64,
                            'APPROVED_PROPOSAL_NOT_READY')
    env = {'readiness': {'targets_mps': {'EGO': F(0), 'NPC': F(0)}, 'markers_m': {'EGO': F(6), 'NPC': F(20)}},
           **environment}
    actors = tuple(ActorRecipe(r, 'vehicle.audi.a2', F(0), Transform6(x, 0., 0., 0., 0., 0.), {}, {}, None)
                   for r, x in (('EGO', 6.), ('NPC', 20.)))
    from tests.m56.response_cases import response_case
    responses = tuple(replace(response_case('C', a, role=r).response, route=route, hash=h)
                      for r, a, h in (('EGO', 'A', 'a'*64), ('EGO', 'B', 'e'*64), ('NPC', 'A', 'b'*64)))
    fx = CompiledFixture('e'*64, 'f'*64, actors, env, {'EGO': Transform6(6., 0., 0., 0., 0., 0.),
                         'NPC': Transform6(20., 0., 0., 0., 0., 0.)}, {'EGO': route, 'NPC': route}, domain, F(3), {},
                         responses, pair, (), META)
    return fx


class ScriptBackend:
    """Fake native boundary. script(t) -> {role: (x, speed)}; phase(t) -> observed phase packet."""
    def __init__(self, root, script, phase=lambda t: None, start=F(-11, 10), fail_at=None, queue=lambda role, t: 1):
        # boundary -1.05, settled -0.05 (>= 1 s), ready 0.00 after the 11-frame .50 s hold
        self.root, self.script, self.phase, self.t, self.fail_at, self.queue = root, script, phase, start, fail_at, queue
        self.frame, self.calls, self.ids, self.applied, self.previous = 1000, [], {}, {}, None
        self.server_management_calls = []
        root.mkdir(parents=True, exist_ok=True)

    def identity(self):
        self.calls.append('identity')
        return SimpleNamespace(boot='b1', world='w7')

    def bind(self, fixture):
        from m56.catalog import _digest
        self.fixture_hash = _digest(fixture)
        self.plans = {role: self.source('plan-' + role, route) for role, route in fixture.routes.items()}
        return self

    def spawn(self, actors, due_tick_cue):
        self.calls.append(('spawn', due_tick_cue))
        self.ids = {a.role: 101 + i for i, a in enumerate(actors)}
        return tuple(SpawnResponse(self.ids[a.role], None, META) for a in actors)

    def listen(self, sensor_id, callback):
        self.calls.append(('listen', sensor_id))
        return OperationResponse(sensor_id, None, None, META)

    def apply(self, commands):
        self.calls.append(('apply', tuple(c.actor for c in commands)))
        self.applied = {c.actor: c for c in commands}
        return tuple(OperationResponse(c.actor, None, c.frame, META) for c in commands)

    def tick(self, timeout_s):
        self.calls.append('tick')
        if self.fail_at is not None and self.t >= self.fail_at:
            raise TimeoutError('tick timeout (scripted)')
        self.frame += 1; self.t += DT
        state = self.script(self.t)
        hold = ControlPacket(0., 0., 1., False, False, False, 1)
        actors = []
        for role, (x, v) in state.items():
            sent = self.applied.get(self.ids.get(role))
            # Observed attribution: the command actually applied before this tick and the control readback.
            cmds = (replace(sent, frame=self.frame - 1, next_frame=self.frame),) if sent is not None else ()
            # CARLA reports the applied control; a stock intent (control None) gets a placeholder PID readback.
            readback = (sent.control if sent.control is not None else hold) if cmds else None
            actors.append(ActorFrame(role, self.ids.get(role, 0), Transform6(float(x), 0., 0., 0., 0., 0.),
                                     (float(v), 0., 0.), BODY, F(x), {}, cmds, readback, None,
                                     self.queue(role, self.t), True, None))
        actors = tuple(actors) if self.ids else ()
        self.applied = {}
        from m56.evidence import _payload
        payload = _payload({'boot': 'b1', 'world': 'w7', 'frame': self.frame, 'simtime': self.t, 'actors': actors})
        path = self.root / f'frame-{self.frame}.json'; path.write_bytes(payload)
        raw = SourceRef(str(path), hashlib.sha256(payload).hexdigest(), len(payload), '1', 'literal-observation',
                        'SYNTHETIC_TEST', self.frame, self.t)
        integrity = {'frame_refs': (raw,), 'actor_ids': tuple(self.ids.values()), 'writers': ('m56',),
                     'plan_refs': self.plans}
        if 'NPC' in self.ids:  # observed stock traffic priority for the NPC (synthetic CLEAR)
            integrity['npc_controls'] = {'boot': 'b1', 'world': 'w7', 'frame': self.frame, 'actor_id': self.ids['NPC'],
                                         'status': 'CLEAR', 'witness_refs': (raw,)}
        if self.previous is not None and actors:
            integrity['continuous_geometry'] = self.geometry(raw, actors)
        self.previous = actors or None
        if self.phase(self.t) is not None:
            integrity['phase'] = self.phase(self.t)
        return FrameRecord('b1', 'w7', self.frame, self.t, DT, actors, (), integrity)

    def source(self, name, value):
        from m56.evidence import _payload
        data = _payload(value); path = self.root / f'{name}.json'; path.write_bytes(data)
        return SourceRef(str(path), hashlib.sha256(data).hexdigest(), len(data), '1', 'literal-observation', 'SYNTHETIC_TEST')

    def geometry(self, raw, actors):
        # SYNTHETIC stand-in for a reviewed continuous-geometry recipe (native: no such recipe yet -> uncertain).
        from m56.catalog import _digest
        packet = {'kind': 'CONTINUOUS_GEOMETRY', 'method': 'bounded-interframe-body-v1', 'raw_refs': (raw,),
                  'uncertainty': F(1, 1000), 'limits': {'fixture_hash': self.fixture_hash,
                  'previous_actors': _digest(self.previous), 'actors': _digest(actors),
                  'previous_frame': self.frame - 1, 'frame': self.frame}, 'status': 'CORROBORATED'}
        review = ReviewRecord(_digest(packet), 'CAPABILITY:CONTINUOUS_GEOMETRY', (raw,), 'SYNTHETIC_TEST', '2026-10-20',
                              'APPROVED', ('literal interval, not native proof',), raw)
        return CapabilityProof(**packet, review=review)

    def stop_listeners(self, ids):
        return tuple(OperationResponse(i, None, None, META) for i in ids)

    def destroy(self, ids, timeout_s):
        self.calls.append(('destroy', ids))
        return tuple(OperationResponse(i, None, None, META) for i in ids)

    def restore(self, ownership, timeout_s):
        self.calls.append('restore')
        return OperationResponse(None, None, None, META)


def context(tmp_path, backend, name='run'):
    from m56.evidence import open_run
    identity = RuntimeIdentity('b1', 'w7', '0.9.16', '0.9.16', '3.12.10', {}, 'Town04', {})
    ownership = OwnershipReceipt('b1', 'w7', '127.0.0.1', 1, 'start', {'rpc': 2610}, (F(0), F(300)), 'm56', 'm56',
                                 ('SPAWN', 'TICK', 'APPLY', 'DESTROY'))
    return SimpleNamespace(backend=backend, identity=identity, ownership=ownership,
                           admission=AdmissionVerdict('ADMITTED', ()), store=open_run(tmp_path/name, 'r1', 'm56'),
                           # Fake episodes are not real-time; online event detection makes them slower than a native
                           # tick budget. Production keeps outer_s=300 (see runtime _known_events performance note).
                           deadlines={'tick_s': 5, 'cleanup_s': 15, 'outer_s': 7200}, scope_mode='SINGLE_EPISODE',
                           scope_phase='RUNNING')


def late_trigger(t):
    # EGO waits at x=6 (front gap 3.5 > G=3) until 55 s, then creeps to 7 (TRIGGER) and stops short of entry.
    ego = 6 if t < 55 else min(F(7), 6 + (t - 55) * 4)
    return {'EGO': (ego, 0 if t < 55 or ego == 7 else 4), 'NPC': (F(20), 0)}


def test_validation_horizon_not_reset_at_trigger(tmp_path, require):
    run = require('m56.runtime', 'run_episode')
    fx = fixture()
    backend = ScriptBackend(tmp_path/'native', late_trigger).bind(fx)
    out = run(context(tmp_path, backend), fx, 'A')
    assert 'TRIGGER' in {e.name for e in out.verdict.events}
    assert out.verdict.physical == 'INCOMPLETE'
    assert out.verdict.metrics['t_entry_s'].value is None
    assert out.end_simtime <= 60
    assert backend.t > 55  # the fake would keep going; the runner stopped at the ready-based horizon
    # Every sealed evidence ref verifies against its bytes; fixture metadata refs are never admitted as observations.
    from pathlib import Path
    for r in (out.fixture, out.manifest, *out.journal, *out.source):
        data = Path(r.uri).read_bytes()
        assert (len(data), hashlib.sha256(data).hexdigest()) == (r.bytes, r.sha256), r.uri
    assert 'SOURCE_SNAPSHOT_FAILED' not in out.verdict.reasons


def test_readiness_never_forces_velocity(tmp_path, require):
    run = require('m56.runtime', 'run_episode')
    fx = fixture()
    fx = replace(fx, environment={**fx.environment, 'readiness': {**fx.environment['readiness'],
                 'markers_m': {'EGO': F(8), 'NPC': F(20)}}})  # actual EGO station 6 never reaches marker 8
    backend = ScriptBackend(tmp_path/'native', lambda t: {'EGO': (F(6), 0), 'NPC': (F(20), 0)}).bind(fx)
    out = run(context(tmp_path, backend), fx, 'A')
    assert out.verdict.physical == 'INCOMPLETE' and 'READINESS_NOT_REACHED' in out.verdict.reasons
    assert not any(c in ('set_velocity', 'teleport') for c in backend.calls)
    assert backend.t <= F(-11, 10) + 1 + 15 + 3 * DT


def test_signal_timeout_blocks_no_hunt(tmp_path, require):
    run = require('m56.runtime', 'run_episode')
    fx = fixture(phase_predicate={'light': 7, 'state': 'Green'})
    backend = ScriptBackend(tmp_path/'native', late_trigger, phase=lambda t: {'light': 7, 'state': 'Red'}).bind(fx)
    out = run(context(tmp_path, backend), fx, 'A')
    assert 'BLOCKED_SIGNAL_ADMISSION' in out.verdict.reasons
    assert not any(isinstance(c, tuple) and c[0] == 'spawn' for c in backend.calls)
    assert 'reload' not in backend.calls and backend.t <= 60


def test_outer_and_tick_timeout_keep_raw(tmp_path, require):
    run = require('m56.runtime', 'run_episode')
    fx = fixture()
    backend = ScriptBackend(tmp_path/'native', late_trigger, fail_at=F(3)).bind(fx)
    ctx = context(tmp_path, backend)
    out = run(ctx, fx, 'A')
    assert 'TICK_TIMEOUT' in out.verdict.reasons
    failure = ctx.store.root/'runner/failure.json'
    assert failure.exists() and 'tick timeout' in failure.read_text(encoding='utf-8')
    assert backend.calls.count(('spawn', False)) == 1  # rerun_count == 0
    assert ('destroy', (101, 102)) in backend.calls


def test_one_a_one_b_no_auto_repeat(tmp_path, require):
    run_ab = require('m56.runtime', 'run_ab')
    fx = fixture()
    backend = ScriptBackend(tmp_path/'native', late_trigger).bind(fx)
    ctx = context(tmp_path, backend)
    a, b = run_ab(ctx, fx, 'C99')
    assert (a.verdict is not None, b.verdict is not None) == (True, True)
    assert backend.calls.count(('spawn', False)) == 2
    report = json.loads((ctx.store.root/'episodes/C99/ab_report.json').read_text(encoding='utf-8'))
    assert report['attempted_actions'] == ['A', 'B']
    again = run_ab(ctx, fx, 'C99')
    assert again.blocked and backend.calls.count(('spawn', False)) == 2


def test_actual_phase_mismatch_not_claimed_identical(tmp_path, require):
    run_ab = require('m56.runtime', 'run_ab')
    fx = fixture(phase_predicate={'light': 7, 'state': 'Green'})
    seen = []
    def phase(t):
        seen.append(t)
        return {'light': 7, 'state': 'Green', 'elapsed_s': '1' if len(seen) < 400 else '2'}
    backend = ScriptBackend(tmp_path/'native', late_trigger, phase=phase).bind(fx)
    ctx = context(tmp_path, backend)
    run_ab(ctx, fx, 'C98')
    report = json.loads((ctx.store.root/'episodes/C98/ab_report.json').read_text(encoding='utf-8'))
    assert report['observed_phases']['A'] != report['observed_phases']['B']
    assert report['actual_phases_identical'] is False


def test_early_empty_plan_failed_not_destination(tmp_path, require):
    """Plan literal is physical FAILED; T09 author ruling (progress l.434) makes missing destination INCOMPLETE.
    The runner never sets verdicts: it stops on the empty plan and the evaluator decides. Disclosed deviation."""
    run = require('m56.runtime', 'run_episode')
    fx = fixture()
    # The stock plan queue empties at 2 s (observed, written into the raw frame like every other field).
    backend = ScriptBackend(tmp_path/'native', lambda t: {'EGO': (6 if t < 1 else min(F(7), 6 + (t - 1) * 4), 0),
                            'NPC': (F(20), 0)}, queue=lambda role, t: 0 if role == 'EGO' and t > 2 else 1).bind(fx)
    out = run(context(tmp_path, backend), fx, 'A')
    assert 'EARLY_EMPTY_PLAN' in out.verdict.reasons
    # Observed evaluator value is INCOMPLETE (missing destination); the plan literal says FAILED. Disclosed deviation.
    assert out.verdict.physical == 'INCOMPLETE'
    assert 'DESTINATION_CONFIRMED' not in {e.name for e in out.verdict.events}
    assert backend.t < 10


def test_resume_is_audit_only(tmp_path, require):
    run_ab, resume = require('m56.runtime', 'run_ab'), require('m56.runtime', 'resume_audit')
    fx = fixture()
    backend = ScriptBackend(tmp_path/'native', late_trigger).bind(fx)
    ctx = context(tmp_path, backend)
    run_ab(ctx, fx, 'C97')
    calls = len(backend.calls)
    summary = resume(ctx.store)
    assert set(summary.completed) == {'C97/A', 'C97/B'} and summary.attempted == summary.completed
    assert len(backend.calls) == calls  # native_bind_count == 0, rerun_count == 0


def test_common_fixed_release_is_action_independent(tmp_path, require):
    """Runner-level counterpart of T11's fixed release: the common NPC program is issued from ONLINE events and
    releases at TRIGGER+3 s in both actions although the Ego moves differently (Ego has no program here)."""
    run_ab = require('m56.runtime', 'run_ab')
    from m56.metrics import detect_events
    fx = fixture()
    npc = next(r for r in fx.responses if r.actor_role == 'NPC')
    program = {'method': 'ordered-event-program-v1', 'initial': 'NOMINAL',
               'transitions': ({'cause': 'NPC_GO', 'after_event': 'TRIGGER', 'delay_s': F(3), 'requires': ()},)}
    npc = replace(npc, targets={'NOMINAL': F(0), 'NPC_GO': F(4)}, phases={'category': 'C', 'program': program})
    fx = replace(fx, responses=(npc,), sections={'DESTINATION': section(14)})
    episode = []

    def script(t):
        b = len(episode) > 1  # second spawn = action B
        stop = F(15, 2) if b else F(7)
        if t < 2:
            ego, v = F(6), 0
        elif t < 7:
            ego = min(stop, 6 + (t - 2) * 4); v = 4 if ego < stop else 0
        else:
            ego = min(F(16), stop + (t - 7) * 4); v = 4 if ego < 16 else 0
        return {'EGO': (ego, v), 'NPC': (F(20), 0)}

    class Backend(ScriptBackend):
        def spawn(self, actors, due_tick_cue):
            episode.append(len(episode))
            self.t, self.previous = F(-11, 10), None  # each episode has its own simulated clock
            return super().spawn(actors, due_tick_cue)

    backend = Backend(tmp_path/'native', script).bind(fx)
    results = run_ab(context(tmp_path, backend), fx, 'C96')
    offsets = []
    for ev in results:
        trigger = next(e for e in detect_events(ev.raw, fx) if e.name == 'TRIGGER')
        npc_cmds = [c for f in ev.raw for x in f.actors if x.role == 'NPC' for c in x.commands]
        release = next(c for c in npc_cmds if c.cause == 'NPC_GO')
        issue_time = next(f.simtime for f in ev.raw if f.frame == release.frame)
        assert issue_time - trigger.time == 3, (trigger, release)
        offsets.append(release.frame - trigger.frame)
    assert offsets[0] == offsets[1] == 60


def test_runner_anchors_capture_start_like_the_consumer(tmp_path, require):
    # Native 22/10: programs released by CAPTURE_START + delay (initial target 0, as settle requires) never left
    # their first phase because the runner did not admit the boundary anchor the consumer replays with.
    run = require('m56.runtime', 'run_episode')
    from tests.m56.response_cases import response_case
    base = fixture()
    ego = response_case('C', 'A', role='EGO').response
    program = ego.phases['program']
    held = replace(ego, route=base.routes['EGO'], hash='a' * 64, targets={**ego.targets, 'HOLD': F(0)},
                   phases={**ego.phases, 'program': {**program, 'initial': 'HOLD', 'transitions': (
                       {'cause': 'NOMINAL', 'after_event': 'CAPTURE_START', 'delay_s': F(3, 2), 'requires': ()},
                       *program['transitions'])}})
    fx = replace(base, responses=(held, *(r for r in base.responses if r.hash != 'a' * 64)))
    backend = ScriptBackend(tmp_path/'native', lambda t: {'EGO': (F(6), 0), 'NPC': (F(20), 0)},
                            queue=lambda role, t: 0 if t > 1 else 1).bind(fx)
    issued, apply = [], backend.apply
    backend.apply = lambda commands: issued.extend((c.frame, c.cause) for c in commands if c.actor == backend.ids['EGO']) or apply(commands)
    run(context(tmp_path, backend), fx, 'A')
    boundary = issued[0][0]  # the first command is issued from the boundary observation
    assert issued[0][1] == 'HOLD'
    assert next(frame for frame, cause in issued if cause == 'NOMINAL') - boundary == 30  # boundary + 1.5 s
