"""2026-11-09 capability probe (observe-only, no scene, no A/B): wall cost per tick on Town12 at the C02-S1 site with two
vehicles, split into (a) world.tick, (b) 16 ground_projection RPCs (the per-frame ground proofs of two bodies), (c) one
cast_ray, (d) one get_actors snapshot; for the large-map settings tile_stream_distance / actor_active_distance at the
default (2000 m) and at 400 m. 100 ticks per setting, medians in ms.
usage: python -I native-tick-cost-probe.py X Y Z"""
import json, statistics, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load, stream_to

log = lambda **k: print(json.dumps(k, default=str), flush=True)
x, y, z = (float(v) for v in sys.argv[1:4])
with own_server(log) as (client, proc, start):
    import carla
    client.set_timeout(900.)
    world = load(client, 'Town12')
    bp = world.get_blueprint_library().find('vehicle.audi.a2')
    for dist in (None, 400.):
        s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = True, .05
        if dist is not None:
            s.tile_stream_distance, s.actor_active_distance = dist, dist
        world.apply_settings(s)
        stream_to(world, x, y, z)
        m = world.get_map()
        wp = m.get_waypoint(carla.Location(x, y, z))
        vs = [world.try_spawn_actor(bp, t) for t in (wp.transform, (wp.next(30.)[0]).transform)]
        for v in vs:
            if v:
                v.apply_control(carla.VehicleControl(throttle=.3))
        cost = {'tick': [], 'ground16': [], 'ray': [], 'actors': []}
        for _ in range(100):
            t = time.perf_counter(); world.tick(120.); cost['tick'].append(time.perf_counter() - t)
            t = time.perf_counter()
            for v in vs:
                if v:
                    l = v.get_location()
                    for dx in (-2, -1, 1, 2):
                        for dy in (-1, 1):
                            world.ground_projection(carla.Location(l.x + dx, l.y + dy, l.z + 2.), 10.)
            cost['ground16'].append(time.perf_counter() - t)
            t = time.perf_counter(); world.cast_ray(carla.Location(x, y, z + 3.), carla.Location(x, y, z - 3.)); cost['ray'].append(time.perf_counter() - t)
            t = time.perf_counter(); world.get_actors(); cost['actors'].append(time.perf_counter() - t)
        s2 = world.get_settings()
        log(event='COST', setting=dist or 'default', tile_stream_distance=s2.tile_stream_distance, actor_active_distance=s2.actor_active_distance,
            ms={k: round(1000 * statistics.median(v), 1) for k, v in cost.items()}, spawned=[v is not None for v in vs])
        for v in vs:
            if v:
                v.destroy()
        world.tick(120.)
    s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = False, None; world.apply_settings(s)
print('COST_END')
