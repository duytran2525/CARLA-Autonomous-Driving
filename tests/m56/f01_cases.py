"""Full F01 SOFTWARE compositions (lead-vehicle brake/stop/restart), not native dynamics qualification.

Frozen before any trace: o_fixture straight geometry (body 3.5 m), settle variants of the approved F01 programs
(EGO 4 m/s, NPC 3 m/s), brake-start section x=24.7, F01_END x=27, destination x=40 (station 50).
Literal kinematics (dt 1/20): both actors stationary to frame 120, nominal speeds from 121, ready 131.
NPC passes the brake marker at 140, brakes 6 m/s^2 from 141 (stops at 150), holds, restarts at 192.
EGO A brakes 8 m/s^2 after the trigger and stops; EGO B slows 4->2 m/s at 2 m/s^2; both resume after N_MOVE.
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


def f01_fixture(s, shared=None):
    if shared is not None:
        s.refs.extend(shared.refs)
        return shared
    from tests.m56.o_cases import o_fixture
    from tests.m56.test_f01_normative_response import f01_response
    from m56.model import FrozenMetricPair
    c = o_fixture(s)
    routes = {k: replace(r, destination=F(50)) for k, r in c.fixture.routes.items()}
    rs = [replace(f01_response(a, role, settle=True)[0], route=routes[role])
          for a, role in (('A', 'EGO'), ('B', 'EGO'), ('NPC_COMMON', 'NPC'))]
    responses = tuple(replace(r, hash=_digest({k: getattr(r, k) for k in
                      ('actor_role', 'action_id', 'route', 'targets', 'profile', 'phases')})) for r in rs)
    poses = {'EGO': replace(c.fixture.poses['EGO'], x=0.), 'NPC': replace(c.fixture.poses['NPC'], x=20.)}
    actors = tuple(ActorRecipe(role, 'vehicle.audi.a2', F(0), pose, {'kind': 'synthetic'}, {'kind': 'synthetic'}, F(50))
                   for role, pose in poses.items())
    pair = FrozenMetricPair(('a_peak_025', 'g_front_min_m'), ('m/s^2', 'm'), ('peak_decel_025', 'min_front_gap'),
                            (('TRIGGER', 'F01_N_CLEAR'),) * 2, 'route:' + _digest(routes['EGO']), 'e' * 64,
                            'APPROVED_PROPOSAL_NOT_READY')
    region = tuple(product((-10., 185.), (-1.75, 1.75), (-1., 1.)))
    fixture = replace(c.fixture, actors=actors, poses=poses, routes=routes, G=None, responses=responses, pair=pair,
                      proofs=(), environment={'readiness': {'targets_mps': {'EGO': F(4), 'NPC': F(3)},
                                                            'markers_m': {'EGO': F(61, 5), 'NPC': F(633, 20)}}},
                      sections={'F01_BRAKE_START': section(F(247, 10)), 'F01_END': section(F(27)),
                                'DESTINATION': section(F(40))},
                      domain=replace(c.fixture.domain, topology={'category': 'F', 'mechanism': 'F01',
                                     'driving_regions': {'EGO': (region,), 'NPC': (region,)}}))
    return SimpleNamespace(fixture=fixture, body=c.body, geometry=c.geometry, refs=tuple(s.refs))


def kinematics(action, last):
    """Literal (position, speed) per frame for both roles; independent of the producer."""
    rows = {}
    ego_x, npc_x, ego_v, npc_v = F(0), F(20), F(0), F(0)
    for n in range(100, last + 1):
        # NPC: nominal 3 from 121, brake 6 m/s^2 from 141 to 0 at 150, restart 3 m/s from 192.
        nv = F(0) if n <= 120 else F(3) if n <= 140 else max(F(0), F(3) - F(3, 10) * (n - 140)) if n <= 191 else F(3)
        # EGO: nominal 4 from 121; after the trigger (issue 145, effect 146) A brakes 8, B slows to 2; resume at 198.
        if n <= 120:
            ev = F(0)
        elif n <= 145:
            ev = F(4)
        elif n <= 197:
            ev = max(F(0), F(4) - F(2, 5) * (n - 145)) if action == 'A' else max(F(2), F(4) - F(1, 10) * (n - 145))
        else:
            ev = F(4)
        if n > 100:
            # Decelerating samples integrate the mean speed; constant/jump samples move at the new speed.
            npc_x += (npc_v + nv) / 2 * DT if 141 <= n <= 150 else nv * DT
            ego_x += (ego_v + ev) / 2 * DT if 146 <= n <= 197 and ev < ego_v else ev * DT
        ego_v, npc_v = ev, nv
        rows[n] = {'EGO': (ego_x, ego_v), 'NPC': (npc_x, npc_v)}
    return rows


def literal(role, action, issue):
    """Hand-written program schedule (cause, target m/s) by issuing frame; checked against the real producer."""
    if issue < 120:
        return 'SETTLE', F(0)
    if role == 'NPC':
        return (('NOMINAL', F(3)) if issue < 140 else ('F01_BRAKE', F(0)) if issue < 191 else ('NPC_RESTART', F(3)))
    if issue < 145:
        return 'NOMINAL', F(4)
    if issue < 197:
        return 'YIELD', F(0) if action == 'A' else F(2)
    return 'RESUME', F(4)


def complete_f01(root, action, shared=None, public=True):
    from m56.metrics import detect_events
    from m56.response import step_response
    s = Sources(root); c = f01_fixture(s, shared); fixture = c.fixture
    ego = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == action)
    npc = next(r for r in fixture.responses if r.actor_role == 'NPC'); responses = (ego, npc)
    hold = ControlPacket(0., 0., .3, False, False, False, 1); forward = ControlPacket(.2, 0., 0., False, False, False, 1)
    last = 385 if action == 'A' else 370  # whole Ego body past x=40 plus the .25 s destination hold
    rows = kinematics(action, last)
    frames = []
    for n in range(100, last + 1):
        actors = []
        for identity, (role, r) in enumerate(zip(('EGO', 'NPC'), responses), 1):
            x, v = rows[n][role]
            braking = (role == 'NPC' and 141 <= n <= 191) or (role == 'EGO' and action == 'A' and 146 <= n <= 197) or v == 0
            control = hold if braking else forward
            cause, target = literal(role, action, n - 1)
            command = CommandRecord(identity, n - 1, n, 'CONTROL', F(18, 5) * target, F(0), control, None, cause, r.hash)
            pose = replace(fixture.poses[role], x=float(x))
            actors.append(ActorFrame(role, identity, pose, (float(v), 0., 0.), c.body, x + 10, {}, (command,), control,
                                     None, 1, True, None))
        f = FrameRecord('boot', 'world', n, F(n - 100, 20), DT, tuple(actors), (), {})
        ref = s.source('f01-' + str(n), {'boot': f.boot, 'world': f.world, 'frame': n, 'simtime': f.simtime,
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
    required = {'F01_BRAKE_MARKER', 'TRIGGER', 'NPC_F01_STOP_HOLD_CONFIRMED', 'N_MOVE', 'F01_N_CLEAR',
                'DESTINATION_CONFIRMED'}
    assert required <= set(names), (sorted(required - set(names)), sorted(names.items(), key=lambda x: x[1]))
    boundary = replace(frames[0], frame=99, simtime=-DT, actors=tuple(replace(a, commands=()) for a in frames[0].actors))
    capture = EventRecord('CAPTURE_START', 99, -DT, (replace(c.geometry, frame=99, time=-DT),))
    states = {r.actor_role: ScriptState('SETTLE', -DT, (capture,)) for r in responses}
    commands = {a.role: CommandRecord(a.id, 99, 100, 'CONTROL', F(0), F(0), hold, None, 'SETTLE', r.hash)
                for a, r in zip(boundary.actors, responses)}
    produced = []
    for f in frames:
        actors = tuple(replace(a, commands=(replace(commands[a.role], control=a.readback),)) for a in f.actors)
        # A broken producer fails HERE: its program must reproduce the literal schedule the detector saw.
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
