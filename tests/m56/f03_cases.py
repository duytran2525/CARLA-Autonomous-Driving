"""Full F03 SOFTWARE compositions (NPC unpowered grade rollback toward a held / reversing Ego).

Frozen before any trace: reverse_case F03 templates (flat Ego route, body .5 m half-length, 2 m hard reverse limit,
stop bound 1.8 + .2), NPC on the synthetic 3-4-5 grade (route (0,0,0)->(48,0,36)), Ego at x=4, NPC at station 10,
destination x=10. NPC program = pre-release hold variant (NPC_HOLD until CAPTURE_START+2 s, then UNPOWERED, then
F03_BRAKE at TRIGGER+2 s). Literal kinematics (dt 1/20): all stationary to the release; NPC coasts -0.5 m/s along
the grade from 140, TRIGGER 145, brake received 186 then decelerates 20/152 m/s^2 (no instant stop); the consumer's stationary rule is a
station rate <= .1 m/s, first met at 247 (v = 15/152, never exactly on the threshold), so NPC_STOP_CONFIRMED 257
(+.5 s). Below .1 m/s the brake holds it (v = 0 from 247): the consumer forbids any NPC/Ego station decrease
after NPC_STOP_CONFIRMED (_forward_tail), so a creep after the confirmation would be an unplanned reverse. Ego A holds then drives 2 m/s after the peer stop; Ego B reverses 0.5 m/s from 146 up to the
frozen stop bound, stops (observed before the peer stop, as the consumer requires), shifts and drives forward.
No native grade, brake, gear or contact calibration is implied.
"""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

from m56.catalog import _digest
from m56.model import ActorFrame, ActorRecipe, CommandRecord, ControlPacket, FrameRecord, ScriptState, Section
from tests.m56.source_cases import Sources

DT = F(1, 20)
HOLD = ControlPacket(0., 0., .3, False, False, False, 1)
COAST = ControlPacket(0., 0., 0., False, False, False, 1)
DRIVE = ControlPacket(.2, 0., 0., False, False, False, 1)


def f03_fixture(s, shared=None):
    if shared is not None:
        s.refs.extend(shared.refs)
        return shared
    from tests.m56.reverse_cases import reverse_case
    from tests.m56.test_f03_normative_response import f03_response, f03_held_response
    from m56.model import FrozenMetricPair
    from m56.response import _reverse_recipe_hash, _reverse_body_hash
    ego = reverse_case(s.root/'ego-template', mechanism='F03')
    s.refs.extend(ego.s.refs)
    body = ego.frames[0].actors[0].body
    flat = replace(ego.response.route, destination=F(10))
    grade = replace(ego.response.route, transforms=(ego.response.route.transforms[0],
                    replace(ego.response.route.transforms[-1], x=48., z=36.)))
    routes = {'EGO': flat, 'NPC': grade}
    a = replace(f03_response('EGO', 'F03', forward=True)[0], route=flat)
    b = replace(ego.response, route=flat)
    n = f03_held_response()[0]  # one frozen policy hash for the Ego reverse policy and the NPC F03 script
    n = replace(n, route=grade, phases={**n.phases, 'f_script': {**n.phases['f_script'], 'policy_hash': ego.fixture.policy_hash}})
    responses = tuple(replace(r, hash=_digest({k: getattr(r, k) for k in
                      ('actor_role', 'action_id', 'route', 'targets', 'profile', 'phases')})) for r in (a, b, n))
    poses = {'EGO': ego.fixture.poses['EGO'], 'NPC': replace(ego.fixture.poses['EGO'], x=8., z=6.)}
    actors = tuple(ActorRecipe(role, 'vehicle.audi.a2', F(0), pose, {'kind': 'synthetic'}, {'kind': 'synthetic'},
                               F(10) if role == 'EGO' else None) for role, pose in poses.items())
    flat_region = tuple(product((0., 60.), (-2., 2.), (-1., 1.)))
    grade_region = tuple(product((0., 60.), (-2., 2.), (-1., 40.)))
    pair = FrozenMetricPair(('d_reverse_m', 'g_front_min_m'), ('m', 'm'), ('reverse_distance', 'min_front_gap'),
                            (('TRIGGER', 'NPC_STOP_CONFIRMED'),) * 2, 'route:' + _digest(flat), 'f' * 64,
                            'APPROVED_PROPOSAL_NOT_READY')
    section = Section(tuple(product((10.,), (-2., 2.), (-1., 1.))), (1., 0., 0.), F(10), {})
    fixture = replace(ego.fixture, actors=actors, poses=poses, routes=routes, responses=responses, proofs=(), pair=pair,
                      sections={'DESTINATION': section},
                      environment={'readiness': {'targets_mps': {'EGO': F(0), 'NPC': F(0)},
                                                 'markers_m': {'EGO': F(4), 'NPC': F(10)}}},
                      domain=replace(ego.fixture.domain, topology={'category': 'F', 'mechanism': 'F03',
                                     'reverse_regions': {'EGO': flat_region},
                                     'driving_regions': {'EGO': (flat_region,), 'NPC': (grade_region,)}}))
    limits = {**ego.stop_proof.limits, 'response_hash': responses[1].hash, 'route_hash': _digest(flat),
              'body_hash': _reverse_body_hash(body), 'fixture_recipe_hash': _reverse_recipe_hash(fixture)}
    ref = s.source('frozen-stop-EGO', limits)
    fixture = replace(fixture, proofs=(s.capability('REVERSE_STOP_BOUND', 'bounded-reverse-stop-v1', limits, (ref,), F(0)),))
    return SimpleNamespace(fixture=fixture, body=body, refs=tuple(s.refs))


TRIGGER_FRAME, NPC_STOP_FRAME = 145, 257


def npc_speed(n):
    """Speed along the grade by frame: .5 m/s coasting 140..186, braked by 1/152 m/s per frame, held at rest once
    at or below .1 m/s (from 247; v(246) = 2/19)."""
    if n < 140:
        return F(0)
    v = F(1, 2) - F(max(0, n - 186), 152)
    return v if v > F(1, 10) else F(0)


def npc_state(n):
    """(station along the grade, speed): station(n) - station(n-1) = -speed(n) * dt."""
    return F(10) - sum((npc_speed(k) for k in range(140, n + 1)), F(0)) * DT, npc_speed(n)


def npc_literal(issue):
    if issue < 139:
        return 'NPC_HOLD', HOLD
    if issue < 185:
        return 'UNPOWERED', COAST
    return 'F03_BRAKE', HOLD


def joint_f03_producer(root, action='B', shared=None, last=None):
    """Closed loop: the command issued at frame n is applied/read back at n+1 (as on a real server); events are
    detected online on the observed prefix. NPC and Ego-A commands must equal the hand-written literal schedule;
    Ego-B (bounded reverse kernel) is checked by properties in the tests, not by a copied schedule."""
    from tests.m56.reverse_cases import ground_actor
    from m56.model import EventRecord
    from m56.runtime import _known_events
    from m56.response import _reverse_recipe_hash, reverse_intent, step_response
    s = Sources(root); frozen = f03_fixture(s, shared); fixture = frozen.fixture
    ego = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == action)
    npc = next(r for r in fixture.responses if r.actor_role == 'NPC'); responses = (ego, npc)
    last = last if last is not None else (333 if action == 'A' else 357)
    recipe = s.source('producer-ground-recipe', {'method': 'recorded-ground-contact-v1', 'version': '1',
                      'limitations': 'synthetic source composition only; no native ground/grade/brake calibration'})
    raw, produced, events, issued, commands, states, seen = [], [], (), {}, {}, {}, set()
    ego_x, ego_v, stopping_frames, capture = F(4), F(0), 0, None
    for n in range(99, last + 1):
        time = F(n - 100, 20)
        station, npc_v = npc_state(n)
        sent = commands.get('EGO')
        if sent is not None:  # physical response of the Ego to the command it received at n
            if sent.cause == 'REVERSE':
                ego_v = -F(1, 2)
            elif sent.cause == 'STOPPING':
                stopping_frames += 1
                ego_v = -F(1, 2) if stopping_frames <= 4 else F(0)
            elif sent.cause == 'FORWARD':
                ego_v = F(2)
            else:
                ego_v = F(0)
            if F(4) - (ego_x + ego_v * DT) > 2:  # physical stop at the hard reserve; never pass it
                ego_v = F(0)
            ego_x += ego_v * DT
        actors = []
        for identity, role in enumerate(('EGO', 'NPC'), 1):
            if n == 99:
                command, readback = None, HOLD
            else:
                command = commands[role]
                readback = command.control if command.control is not None else (DRIVE if command.target_kmh > 0 else HOLD)
                command = replace(command, control=readback)
            if role == 'NPC':
                pose = replace(fixture.poses['NPC'], x=float(station * F(4, 5)), z=float(station * F(3, 5)))
                velocity, arc = (float(-npc_v * F(4, 5)), 0., float(-npc_v * F(3, 5))), None
            else:
                pose = replace(fixture.poses['EGO'], x=float(ego_x)); velocity, arc = (float(ego_v), 0., 0.), F(pose.x)
            actor = ActorFrame(role, identity, pose, velocity, frozen.body, arc, {}, () if command is None else (command,),
                               readback, None, 1, True, None)
            actors.append(ground_actor(s, fixture, actor, n, time, recipe))
        frame = FrameRecord('boot', 'world', n, time, DT, tuple(actors), (), {})
        ref = s.source('observed-' + str(n), {'boot': frame.boot, 'world': frame.world, 'frame': n, 'simtime': time,
                                               'actors': frame.actors}, n, time)
        traffic = {'boot': frame.boot, 'world': frame.world, 'frame': n, 'actor_id': 2, 'status': 'CLEAR'}
        priority = s.source('priority-' + str(n), traffic, n, time)
        fields = {'frame_refs': (ref,), 'npc_controls': {**traffic, 'witness_refs': (priority,)},
                  'metric_context': {'reference': fixture.pair.reference, 'pair_hash': fixture.pair.hash,
                                     'directed_route': fixture.routes['EGO'],
                                     'uncertainty': {name: F(0) for name in fixture.pair.names}},
                  'rollback': s.capability('ROLLBACK', 'unpowered-grade-motion-v1',
                                           {'fixture_hash': _digest(fixture), 'frame': n, 'actors_hash': _digest(frame.actors),
                                            'gravity_along_reverse_mps2': F(1)}, (ref,), F(0))}
        if raw:
            limits = {'fixture_hash': _digest(fixture), 'previous_frame': n - 1, 'frame': n,
                      'previous_actors': _digest(raw[-1].actors), 'actors': _digest(frame.actors)}
            fields['continuous_geometry'] = s.capability('CONTINUOUS_GEOMETRY', 'bounded-interframe-body-v1', limits,
                                                         (ref,), F(0))
        raw.append(replace(frame, integrity=dict(fields)))
        if n == 99:
            capture = EventRecord('CAPTURE_START', 99, -DT, (ref,))
            states = {r.actor_role: ScriptState(r.phases['program']['initial'], -DT, (capture,)) for r in responses}
        else:
            events = _known_events(tuple(raw[1:]), fixture)  # online, the consumer's known-event view of the prefix
            seen.update(events)
        if n >= 145:
            prefix = tuple(replace(p, integrity={k: v for k, v in p.integrity.items() if k in
                           ('frame_refs', 'continuous_geometry', 'rollback')}) for p in raw)
            fields['reverse_history_ref'] = s.source('history-' + str(n), prefix)
            if action == 'B':
                own = next(a for a in frame.actors if a.role == 'EGO')
                limits = {'fixture_recipe_hash': _reverse_recipe_hash(fixture), 'boot': frame.boot, 'world': frame.world,
                          'frame': n, 'actor_id': own.id, 'actors_hash': _digest(frame.actors),
                          'response_hash': ego.hash, 'region_hash': _digest(fixture.domain.topology['reverse_regions']['EGO']),
                          'minimum_rear_clearance_m': F(1)}
                cref = s.source('corridor-EGO-' + str(n), limits, n, time)
                fields['reverse_corridors'] = {'EGO': s.capability('REVERSE_CORRIDOR', 'bounded-reverse-corridor-v1',
                                                                    limits, (cref,), F(0))}
        observed = replace(frame, integrity=fields, events=tuple(e for e in events if e.frame == n))
        produced.append(replace(observed, events=()))
        if n == last:
            break
        for response in responses:
            role = response.actor_role
            admitted = tuple(e for e in events if e.frame <= n)
            bounded = role == 'EGO' and action == 'B' and any(e.name == 'TRIGGER' for e in admitted)
            # As the consumer replays: CAPTURE_START is a timer anchor for programs, never passed to the bounded kernel.
            state = replace(states[role], events=admitted if bounded else (capture, *admitted))
            out = reverse_intent(observed, state, response, fixture) if bounded else step_response(observed, state, response)
            assert out.command.kind != 'BLOCKED', (n, role, out.command)
            states[role] = replace(out.state, events=tuple(e for e in out.state.events if e.name != 'CAPTURE_START'))
            commands[role] = out.command
            issued[(role, n)] = out.command
            if role == 'NPC':
                assert (out.command.cause, out.command.control) == npc_literal(n), (n, out.command)
            if role == 'EGO' and action == 'A':
                expect = ('HOLD', F(0)) if n < NPC_STOP_FRAME else ('FORWARD', F(36, 5))
                assert (out.command.cause, out.command.target_kmh) == expect, (n, out.command)
    final = _known_events(tuple(raw[1:]), fixture)
    assert seen <= set(final), sorted((e.name, e.frame) for e in seen - set(final))  # no online event revised later
    by = {e.name: e.frame for e in final}
    assert (by.get('TRIGGER'), by.get('NPC_STOP_CONFIRMED')) == (TRIGGER_FRAME, NPC_STOP_FRAME), sorted(by.items(), key=lambda x: x[1])
    return SimpleNamespace(frames=tuple(produced[1:]), boundary=produced[0], fixture=fixture, sources=s, frozen=frozen,
                           events=final, issued=issued)


def complete_f03(root, action='B', shared=None):
    c = joint_f03_producer(root, action, shared)
    public = Sources(c.sources.root/'public'); public.refs.extend(c.sources.refs)
    episode = public.complete(c.frames, c.fixture, c.boundary, 120, 131, preserve_ground=True)
    return SimpleNamespace(episode=episode, fixture=c.fixture, sources=public, frozen=c.frozen)
