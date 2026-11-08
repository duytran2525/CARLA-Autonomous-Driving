"""2026-11-08 capability smoke test only (no scene, no A/B): do ground and physics stay active on a CARLA large map for two
vehicles ~150-200 m apart, > 1 km from the origin, while the spectator stays where load_world put it?
Per town: pick the first spawn point (sorted by x, y) with |xy| > 1000 m that has another spawn point 150-200 m away;
spawn vehicle.audi.a2 at both, apply throttle 0.4 for 300 synchronous ticks (0.05 s). Report per vehicle: start / end z,
max |dz| per tick, distance travelled, ground_projection label under it at the end, and the large-map settings.
A failure is capability evidence (no harness change here).
usage: python -I native-largemap-smoke.py Town12,Town13"""
import json, math, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, NO_RENDER

log = lambda **k: print(json.dumps(k, default=str), flush=True)
with own_server(log) as (client, proc, start):
    client.set_timeout(900.)
    import carla
    for town in sys.argv[1].split(','):
        world = client.load_world(town)
        for _ in range(3):
            world.wait_for_tick(120)
        s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds, s.no_rendering_mode = True, .05, NO_RENDER
        world.apply_settings(s)
        s = world.get_settings()
        sp = sorted(world.get_map().get_spawn_points(), key=lambda t: (t.location.x, t.location.y))
        pair = next(((a, b) for a in sp if math.hypot(a.location.x, a.location.y) > 1000
                     for b in sp if 150 <= a.location.distance(b.location) <= 200), None)
        if pair is None:
            log(event='SMOKE_NO_PAIR', town=town); continue
        bp = world.get_blueprint_library().find('vehicle.audi.a2')
        vs = [world.try_spawn_actor(bp, t) for t in pair]
        if None in vs:
            log(event='SMOKE_SPAWN_FAIL', town=town, spawned=[v is not None for v in vs])
            for v in vs:
                if v: v.destroy()
            continue
        if os.environ.get('M56_SMOKE_SPECTATOR') == '1':  # variant: spectator above the pair midpoint before ticking
            mid = carla.Location((pair[0].location.x + pair[1].location.x) / 2, (pair[0].location.y + pair[1].location.y) / 2,
                                 max(pair[0].location.z, pair[1].location.z) + 50.)
            world.get_spectator().set_transform(carla.Transform(mid, carla.Rotation(pitch=-90.)))
            for _ in range(20):
                world.tick(120.)
        world.tick()
        z0 = [v.get_location().z for v in vs]; p0 = [v.get_location() for v in vs]; zprev = list(z0); dzmax = [0., 0.]
        for _ in range(300):
            for v in vs:
                v.apply_control(carla.VehicleControl(throttle=.4))
            world.tick(120.)
            for i, v in enumerate(vs):
                z = v.get_location().z; dzmax[i] = max(dzmax[i], abs(z - zprev[i])); zprev[i] = z
        out = []
        for i, v in enumerate(vs):
            loc = v.get_location()
            g = world.ground_projection(carla.Location(loc.x, loc.y, loc.z + 2.), 10.)
            out.append({'start': [round(p0[i].x, 1), round(p0[i].y, 1)], 'z0': round(z0[i], 3), 'z1': round(loc.z, 3),
                        'max_dz_per_tick': round(dzmax[i], 4), 'travelled_m': round(loc.distance(p0[i]), 1),
                        'ground': None if g is None else str(g.label)})
            v.destroy()
        log(event='SMOKE', town=town, spectator=os.environ.get('M56_SMOKE_SPECTATOR') == '1', tile_stream_distance=getattr(s, 'tile_stream_distance', None),
            actor_active_distance=getattr(s, 'actor_active_distance', None), vehicles=out)
        s.synchronous_mode, s.fixed_delta_seconds = False, None; world.apply_settings(s)
print('SMOKE_END')
