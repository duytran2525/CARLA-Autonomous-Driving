"""2026-11-09 capability probe (observe-only, no scene, no A/B): first-tick settle of vehicle.audi.a2 at the frozen spawn
poses of the batch-1 Town12 A/Bs, spawned (a) with pitch = roll = 0 (as batch 1) and (b) with the waypoint pitch/roll
(A-SEL2 addendum 6, M56_SPAWN_TILT). Synchronous 0.05 s, spectator streamed first. Reports, after 1 and 5 ticks, the
horizontal displacement from the spawn x/y, the pitch, and the speed — the quantities of _initial_state_matches.
usage: python -I native-settle-probe.py AB_SCENE_DIR [...]   (all on Town12)"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load, stream_to, spawn_tilt

log = lambda **k: print(json.dumps(k, default=str), flush=True)
g = lambda x: float.fromhex(x['binary64']) if isinstance(x, dict) and 'binary64' in x else float(x)
poses = []
for d in sys.argv[1:]:
    fx = json.loads((Path(d) / 'fixture-frozen.json').read_text(encoding='utf-8'))
    for role, p in fx['poses'].items():
        v = [g(x) for x in (p if isinstance(p, list) else [p[k] for k in ('x', 'y', 'z', 'pitch', 'yaw', 'roll')])]
        poses.append((Path(d).name, role, v))
with own_server(log) as (client, proc, start):
    import carla
    client.set_timeout(900.)
    world = load(client, 'Town12'); m = world.get_map()
    s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = True, .05; world.apply_settings(s)
    bp = world.get_blueprint_library().find('vehicle.audi.a2')
    for scene, role, (x, y, z, pi, ya, ro) in poses:
        stream_to(world, x, y, z)
        for mode in ('flat', 'tilt'):
            pt, rl = spawn_tilt(m, x, y, z) if mode == 'tilt' else (0., 0.)
            v = world.try_spawn_actor(bp, carla.Transform(carla.Location(x, y, z), carla.Rotation(pitch=pt, yaw=ya, roll=rl)))
            if v is None:
                log(event='SPAWN_FAIL', scene=scene, role=role, mode=mode); continue
            rows = []
            for i in range(5):
                world.tick(120.)
                t = v.get_transform(); vel = v.get_velocity()
                rows.append({'tick': i + 1, 'dxy_mm': round(1000 * math.hypot(t.location.x - x, t.location.y - y), 3),
                             'pitch': round(t.rotation.pitch, 3), 'dpitch': round(t.rotation.pitch - pt, 3),
                             'speed': round(math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2), 3)})
            log(event='SETTLE', scene=scene, role=role, mode=mode, spawn_pitch=round(pt, 3), ticks=[rows[0], rows[-1]])
            v.destroy(); world.tick(120.)
    s.synchronous_mode, s.fixed_delta_seconds = False, None; world.apply_settings(s)
print('SETTLE_END')
