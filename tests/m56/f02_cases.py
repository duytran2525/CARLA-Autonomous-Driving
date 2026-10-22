"""Full F02 SOFTWARE compositions (faster NPC closing from behind), not native dynamics qualification.

Frozen before any trace: o_fixture straight geometry (body 3.5 m), settle variants of the approved F02 programs
(EGO nominal 4, NPC constant 5 m/s), EGO initial x=30, NPC x=5, nominal front at t0 station 47.75,
F02_END x=97.75 (station 107.75 = front t0 + 60), destination x=105 (station 115).
Literal kinematics: stationary to frame 120, nominal speeds from 121, ready 131, rear gap reaches 20 m at 150
(TRIGGER); A keeps 4 m/s, B runs 5.5 m/s from 151 (issue 150).
"""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from types import SimpleNamespace

from m56.catalog import _digest
from m56.model import ActorFrame, ActorRecipe, CommandRecord, ControlPacket, EventRecord, FrameRecord, ScriptState, Section
from tests.m56.source_cases import Sources

DT = F(1, 20)


def section(x):
    return Section(tuple(product((float(x),), (-1.75, 1.75), (-1., 1.))), (1., 0., 0.), F(x) + 10, {})


def f02_fixture(s, shared=None):
    if shared is not None:
        s.refs.extend(shared.refs)
        return shared
    from tests.m56.o_cases import o_fixture
    from tests.m56.test_f02_normative_response import f02_response
    from m56.model import FrozenMetricPair
    c = o_fixture(s)
    routes = {k: replace(r, destination=F(115)) for k, r in c.fixture.routes.items()}
    rs = [replace(f02_response(a, role, settle=True)[0], route=routes[role])
          for a, role in (('A', 'EGO'), ('B', 'EGO'), ('NPC_COMMON', 'NPC'))]
    responses = tuple(replace(r, hash=_digest({k: getattr(r, k) for k in
                      ('actor_role', 'action_id', 'route', 'targets', 'profile', 'phases')})) for r in rs)
    poses = {'EGO': replace(c.fixture.poses['EGO'], x=30.), 'NPC': replace(c.fixture.poses['NPC'], x=5.)}
    actors = tuple(ActorRecipe(role, 'vehicle.audi.a2', F(0), pose, {'kind': 'synthetic'}, {'kind': 'synthetic'}, F(115))
                   for role, pose in poses.items())
    pair = FrozenMetricPair(('v_mean_E', 'g_rear_min_m'), ('m/s', 'm'), ('mean_speed', 'min_rear_gap'),
                            (('TRIGGER', 'F02_END'),) * 2, 'route:' + _digest(routes['EGO']), 'e' * 64,
                            'APPROVED_PROPOSAL_NOT_READY')
    region = tuple(product((-10., 185.), (-1.75, 1.75), (-1., 1.)))
    fixture = replace(c.fixture, actors=actors, poses=poses, routes=routes, G=None, responses=responses, pair=pair,
                      proofs=(), environment={'readiness': {'targets_mps': {'EGO': F(4), 'NPC': F(5)},
                                                            'markers_m': {'EGO': F(211, 5), 'NPC': F(71, 4)}}},
                      sections={'F02_END': section(F(391, 4)), 'DESTINATION': section(F(105))},
                      domain=replace(c.fixture.domain, topology={'category': 'F', 'mechanism': 'F02',
                                     'nominal_front_t0_m': F(191, 4),
                                     'driving_regions': {'EGO': (region,), 'NPC': (region,)}}))
    return SimpleNamespace(fixture=fixture, body=c.body, geometry=c.geometry, refs=tuple(s.refs))


def kinematics(action, last):
    rows = {}
    ego_x, npc_x = F(30), F(5)
    for n in range(100, last + 1):
        nv = F(0) if n <= 120 else F(5)
        ev = F(0) if n <= 120 else F(4) if n <= 150 or action == 'A' else F(11, 2)
        if n > 100:
            ego_x += ev * DT; npc_x += nv * DT
        rows[n] = {'EGO': (ego_x, ev), 'NPC': (npc_x, nv)}
    return rows


def literal(role, action, issue):
    """Hand-written program schedule (cause, target m/s) by issuing frame; checked against the real producer."""
    if issue < 120:
        return 'SETTLE', F(0)
    if role == 'NPC':
        return 'NOMINAL', F(5)
    if issue < 150:
        return 'NOMINAL', F(4)
    return 'ACTION', F(4) if action == 'A' else F(11, 2)


def complete_f02(root, action, shared=None, public=True):
    from m56.metrics import detect_events
    from m56.response import step_response
    s = Sources(root); c = f02_fixture(s, shared); fixture = c.fixture
    ego = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == action)
    npc = next(r for r in fixture.responses if r.actor_role == 'NPC'); responses = (ego, npc)
    hold = ControlPacket(0., 0., .3, False, False, False, 1); forward = ControlPacket(.2, 0., 0., False, False, False, 1)
    last = 512 if action == 'A' else 415  # whole Ego body past x=105 plus the .25 s destination hold
    rows = kinematics(action, last)
    frames = []
    for n in range(100, last + 1):
        actors = []
        for identity, (role, r) in enumerate(zip(('EGO', 'NPC'), responses), 1):
            x, v = rows[n][role]
            control = hold if v == 0 else forward
            cause, target = literal(role, action, n - 1)
            command = CommandRecord(identity, n - 1, n, 'CONTROL', F(18, 5) * target, F(0), control, None, cause, r.hash)
            pose = replace(fixture.poses[role], x=float(x))
            actors.append(ActorFrame(role, identity, pose, (float(v), 0., 0.), c.body, x + 10, {}, (command,), control,
                                     None, 1, True, None))
        f = FrameRecord('boot', 'world', n, F(n - 100, 20), DT, tuple(actors), (), {})
        ref = s.source('f02-' + str(n), {'boot': f.boot, 'world': f.world, 'frame': n, 'simtime': f.simtime,
                                         'actors': f.actors}, n, f.simtime)
        fields = {'frame_refs': (ref,),
                  'metric_context': {'reference': fixture.pair.reference, 'pair_hash': fixture.pair.hash,
                                     'directed_route': fixture.routes['EGO'],
                                     'uncertainty': {name: F(0) for name in fixture.pair.names}},
                  'npc_controls': {'boot': f.boot, 'world': f.world, 'frame': n, 'actor_id': 2, 'status': 'CLEAR',
                                   'witness_refs': (ref,)}}
        if frames:
            limits = {'fixture_hash': _digest(fixture), 'previous_actors': _digest(frames[-1].actors),
                      'actors': _digest(f.actors), 'previous_frame': n - 1, 'frame': n}
            fields['continuous_geometry'] = s.capability('CONTINUOUS_GEOMETRY', 'bounded-interframe-body-v1', limits,
                                                         (ref,), F(0))
        frames.append(replace(f, integrity=fields))
    events = detect_events(tuple(frames), fixture)
    names = {e.name: e.frame for e in events}
    required = {'TRIGGER', 'F02_END', 'DESTINATION_CONFIRMED'}
    assert required <= set(names), (sorted(required - set(names)), sorted(names.items(), key=lambda x: x[1]))
    boundary = replace(frames[0], frame=99, simtime=-DT, actors=tuple(replace(a, commands=()) for a in frames[0].actors))
    capture = EventRecord('CAPTURE_START', 99, -DT, (replace(c.geometry, frame=99, time=-DT),))
    states = {r.actor_role: ScriptState('SETTLE', -DT, (capture,)) for r in responses}
    commands = {a.role: CommandRecord(a.id, 99, 100, 'CONTROL', F(0), F(0), hold, None, 'SETTLE', r.hash)
                for a, r in zip(boundary.actors, responses)}
    produced = []
    for f in frames:
        actors = tuple(replace(a, commands=(replace(commands[a.role], control=a.readback),)) for a in f.actors)
        assert _digest(actors) == _digest(f.actors), (f.frame, [(x.role, x.commands[0].cause, x.commands[0].target_kmh)
                                                                for x in actors])
        f = replace(f, actors=actors, events=tuple(e for e in events if e.frame == f.frame))
        produced.append(replace(f, events=()))
        for r in responses:
            out = step_response(f, states[r.actor_role], r)
            states[r.actor_role] = out.state; commands[r.actor_role] = out.command
    if not public:
        return SimpleNamespace(frames=tuple(produced), events=events, fixture=fixture, rows=rows, sources=s, frozen=c)
    episode = s.complete(tuple(produced), fixture, boundary, 120, 131)
    return SimpleNamespace(episode=episode, fixture=fixture, sources=s, frozen=c, rows=rows)
