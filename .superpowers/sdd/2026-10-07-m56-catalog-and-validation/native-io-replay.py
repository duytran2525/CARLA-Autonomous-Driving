"""Offline kinematic replay of a compiled O fixture through the consumer's own detect_events and step_response (template:
tests/m56/o_cases.complete_o). Ideal tracking at the probe-2 plateaus from t0 - 3 s; EGO A follows its frozen references
(initial profile, TARGET switch at its marker, HOME at its marker); EGO B drops to its FOLLOW target at TRIGGER. Corridor
proofs carry the kit's own io_paths clearances; synthetic sources (tests/m56/source_cases). It shows whether TRIGGER ->
TARGET_LANE_CONFIRMED -> RETURN_* -> X_END -> DESTINATION fire in order and whether step_response accepts every command.
NOT evidence and NOT an episode: kinematics are idealised.
  python -I native-io-replay.py SCENE_DIR (fixture-frozen.json)   [M56_CODE = the consumer under test]
"""
import json, math, sys, tempfile
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import body_record  # noqa: E402  (puts M56_CODE first on sys.path)
from native_v2_kit import Kit  # noqa: E402
from m56.catalog import _digest  # noqa: E402
from m56.metrics import detect_events, _metric_station  # noqa: E402
from m56.model import (ActorFrame, CommandRecord, ControlPacket, EventRecord, FrameRecord, ScriptState, Transform6,  # noqa: E402
                       decode_record, load_json)
from m56.response import desired_offset, step_response  # noqa: E402
from tests.m56.source_cases import Sources  # noqa: E402

sd = Path(sys.argv[1])
fx = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
prep = json.loads(Path(fx.environment['runtime_recipe_v2']['prepare_json']).read_text(encoding='utf-8'))
fl = lambda x: float.fromhex(x['binary64']) if 'binary64' in x else x['numerator'] / x['denominator']  # noqa: E731
vE, vN, gap = fl(prep['probe2']['EGO']), fl(prep['probe2']['NPC']), fl(prep['gap_at_t0_probe2'])
bbox = {k: [fl(v) if isinstance(v, dict) else v for v in vals] for k, vals in prep['bbox'].items()}


def at(route, arc):
    arcs = [float(a) for a in route.arc]
    i = max(0, min(len(arcs) - 2, max((n for n, a in enumerate(arcs) if a <= arc), default=0)))
    a, b = route.transforms[i], route.transforms[i + 1]; u = (arc - arcs[i]) / (arcs[i + 1] - arcs[i])
    return a.x + u * (b.x - a.x), a.y + u * (b.y - a.y), a.z + u * (b.z - a.z), a.yaw


def replay(action):
    s = Sources(Path(tempfile.mkdtemp()) / f'replay-{action}')
    body = body_record(bbox, s.source('bbox', bbox))
    half = bbox['extent'][0]
    ego_r = next(r for r in fx.responses if r.actor_role == 'EGO' and r.action_id == action)
    npc_r = next(r for r in fx.responses if r.actor_role == 'NPC')
    sw = ego_r.phases.get('reference_switches', ())
    dec = float(fx.sections['O_DECISION'].route_station)
    ego, npc = fx.routes['EGO'], fx.routes['NPC']
    # t0 (frame 60): EGO front at O_DECISION, NPC rear `gap` ahead (NPC route arc of road-s: same straight road, so
    # the NPC rear station = its spawn-frame station + the along-road distance)
    e0 = dec - half - 3 * vE - .2  # off-grid phase: a sample inside the +-0.001 m band of a section loses that crossing (consumer rule)
    n_spawn = float(_metric_station((fx.poses['NPC'].x, fx.poses['NPC'].y, fx.poses['NPC'].z), npc))
    ex = at(ego, dec)[0]; nx = at(npc, n_spawn)[0]
    n0 = n_spawn + (ex + gap + half - nx) - 3 * vN   # NPC centre station at frame 0 (x-axis road)
    kit = Kit.__new__(Kit); kit.fixture, kit.fixture_hash, kit.recipes, kit.authority = fx, _digest(fx), {}, s.authority
    frames, e_arc, follow = [], e0, False
    hold = ControlPacket(0., 0., .3, False, False, False, 1); fwd = ControlPacket(.2, 0., 0., False, False, False, 1)
    for i in range(int((float(ego.destination) + 10 - e0) / 2.5 * 20)):
        number, time = 1000 + i, F(i, 20)
        if i:
            e_arc += (2.5 if follow else vE) / 20
        if e_arc + half > float(ego.arc[-1]) - .5:
            break
        x, y, z, yaw = at(ego, e_arc)
        off = 0.
        if action == 'A':
            ref = ego_r
            for w in sw:
                if e_arc >= float(w['marker_arc_m']):
                    ref = replace(ego_r, route=w['route'], profile=w['profile'])
            off = float(desired_offset(F(e_arc), ref)) + (float(fx.domain.topology['lane_geometry']['EGO']['separation_m'])
                                                         if ref.route is not ego_r.route and ref.route != ego_r.route else 0.)
        r = math.radians(yaw)
        epose = Transform6(x - math.sin(r) * off, y + math.cos(r) * off, z + .01, 0., yaw, 0.)
        nxp, nyp, nzp, nyaw = at(npc, n0 + vN * i / 20)
        npose = Transform6(nxp, nyp, nzp + .01, 0., nyaw, 0.)
        speed = 2.5 if follow else vE
        actors = []
        for ident, (role, resp, pose, v) in enumerate((('EGO', ego_r, epose, speed), ('NPC', npc_r, npose, vN)), 1):
            st = _metric_station((pose.x, pose.y, pose.z), fx.routes[role])
            cmd = CommandRecord(ident, number - 1, number, 'CONTROL', F(0), F(0), fwd, None, 'SETTLE', resp.hash)
            actors.append(ActorFrame(role, ident, pose, (v * math.cos(math.radians(pose.yaw)), v * math.sin(math.radians(pose.yaw)), 0.),
                                     body, st, {}, (cmd,), fwd, None, 1, st is not None, None))
        f = FrameRecord('boot', 'world', number, time, F(1, 20), tuple(actors), (), {})
        ref = s.source(f'f{number}', {'frame': number, 'simtime': time, 'actors': f.actors}, number, time)
        fields = {'frame_refs': (ref,),
                  'metric_context': {'reference': fx.pair.reference, 'pair_hash': fx.pair.hash,
                                     'map_reference': fx.domain.topology['map_reference'],
                                     'uncertainty': {n: F(1, 1000) for n in fx.pair.names}},
                  'npc_controls': {'boot': 'boot', 'world': 'world', 'frame': number, 'actor_id': 2, 'status': 'CLEAR',
                                   'witness_refs': (ref,)}}
        if frames:
            fields['continuous_geometry'] = s.capability('CONTINUOUS_GEOMETRY', 'bounded-interframe-body-v1',
                {'fixture_hash': _digest(fx), 'previous_actors': _digest(frames[-1].actors), 'actors': _digest(f.actors),
                 'previous_frame': number - 1, 'frame': number}, (ref,), F(1, 1000))
        paths = kit.io_paths(SimpleNamespace(_raw=lambda *a, **k: ref), number, time, f.actors)
        for key in ('lane_change_path', 'return_path'):
            p = paths[key]
            fields[key] = s.capability(p.kind, p.method, p.limits, (ref,), F(1, 1000))
        frames.append(replace(f, integrity=fields))
        if action == 'B' and not follow:
            follow = any(e.name == 'TRIGGER' for e in detect_events(tuple(frames[-2:]), fx)) if len(frames) > 1 else False
    events = detect_events(tuple(frames), fx)
    order = [(e.name, e.frame - 1000) for e in events if e.name not in ('LANE_CHANGE_PATH_CLEAR', 'RETURN_PATH_CLEAR')]
    # step_response over the trace (as complete_o): every command the consumer would issue must be accepted
    boundary = replace(frames[0], frame=999, simtime=-F(1, 20), actors=tuple(replace(a, commands=()) for a in frames[0].actors))
    capture = EventRecord('CAPTURE_START', 999, -F(1, 20), (s.source('capture', {'frame': 999}, 999, -F(1, 20)),))
    states = {r.actor_role: ScriptState('SETTLE', -F(1, 20), (capture,)) for r in (ego_r, npc_r)}
    cmds = {a.role: CommandRecord(a.id, 999, 1000, 'CONTROL', F(0), F(0), hold, None, 'SETTLE', r.hash)
            for a, r in zip(boundary.actors, (ego_r, npc_r))}
    error = None
    for f in frames:
        f = replace(f, actors=tuple(replace(a, commands=(replace(cmds[a.role], control=a.readback),)) for a in f.actors),
                    events=tuple(e for e in events if e.frame == f.frame))
        try:
            for r in (ego_r, npc_r):
                out = step_response(f, states[r.actor_role], r); states[r.actor_role] = out.state; cmds[r.actor_role] = out.command
        except ValueError as e:
            error = (f.frame - 1000, str(e)); break
    return order, error, states['EGO'].phase


if __name__ == '__main__':
    for action in sys.argv[2:] or ('A', 'B'):
        order, error, phase = replay(action)
        print(action, 'events', order)
        print(action, 'step_response', 'OK' if error is None else f'ERROR at frame {error[0]}: {error[1]}', '| final EGO phase', phase)
