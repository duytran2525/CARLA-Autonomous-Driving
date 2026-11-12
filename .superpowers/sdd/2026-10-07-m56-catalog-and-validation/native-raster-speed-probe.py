"""2026-11-12 capability probe only (no scene, no A/B, no fixture): why does the dv1 raster of the FIRST scene after
load_world take hours (Town12 C02-S1 3.8 h at ~70 ms per cast_ray; later scenes 34-49 s; Town13 C07-S1 > 10.7 h)?
Loads TOWN with the A/B settings (native_v2_common.load, no_rendering), streams to (X, Y, Z) like stream_to, then times
batches of cast_ray (same ray shape as drivable_union: z+3 -> z-3) at fixed pseudo-random points within 60 m:
  phase ASYNC: batches with a 60 s sleep between them, for MINUTES (does the latency fall as the server settles?), with a get_settings RPC as
               a plain round-trip reference;
  phase SYNC : synchronous_mode on (no tick during the batch), one batch; then async restored and one more batch.
usage: python -I native-raster-speed-probe.py TOWN X Y Z MINUTES"""
import json, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load

log = lambda **k: print(json.dumps({'t': time.strftime('%H:%M:%S'), **k}, default=str), flush=True)
town, X, Y, Z, minutes = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
rng = random.Random(56)
pts = [(X + rng.uniform(-60, 60), Y + rng.uniform(-60, 60)) for _ in range(100)]


def batch(world, carla, tag):
    t0 = time.perf_counter(); hits = 0
    for x, y in pts:
        h = world.cast_ray(carla.Location(x, y, Z + 3.), carla.Location(x, y, Z - 3.))
        hits += bool(h and str(h[0].label) in ('Roads', 'RoadLines'))
    ray = (time.perf_counter() - t0) / len(pts) * 1000
    t0 = time.perf_counter()
    for _ in range(20):
        world.get_settings()
    rpc = (time.perf_counter() - t0) / 20 * 1000
    s = world.get_settings()
    log(event='BATCH', tag=tag, ms_per_ray=round(ray, 2), ms_per_rpc=round(rpc, 2), road_hits=hits,
        sync=s.synchronous_mode, no_render=s.no_rendering_mode)


with own_server(log) as (client, proc, start):
    import carla
    world = load(client, town)
    log(event='LOADED', town=town)
    world.get_spectator().set_transform(carla.Transform(carla.Location(X, Y, Z + 50.), carla.Rotation(pitch=-90.)))
    for _ in range(20):
        world.wait_for_tick(120.)
    t_end = time.monotonic() + minutes * 60
    i = 0
    while time.monotonic() < t_end:
        batch(world, carla, f'async-{i}'); i += 1
        time.sleep(60)
    s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = True, .05; world.apply_settings(s)
    world.tick(120.)
    batch(world, carla, 'sync-no-tick')
    for _ in range(200):
        world.tick(120.)
    batch(world, carla, 'sync-after-200-ticks')
    s.synchronous_mode, s.fixed_delta_seconds = False, None; world.apply_settings(s)
    world.wait_for_tick(120.)
    batch(world, carla, 'async-after')
    log(event='PROBE_END')
