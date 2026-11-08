"""2026-11-08 capability test only (no scene, no A/B): can Claude's own server (2610) load each candidate town of the
selection-expansion addendum on this laptop, and tick in synchronous mode with one spawned vehicle?
Per town: load_world seconds, junction count of the map topology, 200 synchronous ticks (0.05 s) with one vehicle at
the first spawn point, mean wall ms per tick. A failure is recorded as that town's BLOCKED_CAPABILITY evidence.
usage: python -I native-town-load-test.py Town01,Town02,...  (M56_NO_RENDER=1 as every M56 run)"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, NO_RENDER

log = lambda **k: print(json.dumps(k, default=str), flush=True)
with own_server(log) as (client, proc, start):
    client.set_timeout(900.)
    for town in sys.argv[1].split(','):
        t0 = time.monotonic()
        try:
            world = client.load_world(town)
            for _ in range(3):
                world.wait_for_tick(120)
            load_s = time.monotonic() - t0
            m = world.get_map()
            juncs = {w.get_junction().id for pair in m.get_topology() for w in pair if w.is_junction}
            s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = True, .05
            s.no_rendering_mode = NO_RENDER; world.apply_settings(s)
            bp = world.get_blueprint_library().find('vehicle.audi.a2')
            v = world.try_spawn_actor(bp, m.get_spawn_points()[0])
            t1 = time.monotonic()
            for _ in range(200):
                world.tick(120.)
            tick_ms = (time.monotonic() - t1) / 200 * 1000
            if v is not None:
                v.destroy()
            s.synchronous_mode, s.fixed_delta_seconds = False, None; world.apply_settings(s)
            log(event='TOWN_OK', town=town, load_s=round(load_s, 1), junctions=len(juncs), spawned=v is not None,
                tick_ms=round(tick_ms, 1), proc_alive=proc.poll() is None)
        except Exception as e:  # recorded, not retried
            log(event='TOWN_FAIL', town=town, after_s=round(time.monotonic() - t0, 1), error=repr(e)[:300],
                proc_alive=proc.poll() is None)
            if proc.poll() is not None:
                break
print('LOAD_TEST_END')
