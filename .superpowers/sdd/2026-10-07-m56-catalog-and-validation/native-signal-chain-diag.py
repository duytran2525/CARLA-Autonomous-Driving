"""2026-11-08 diagnostic only (no actors spawned, observe-only ticks): which traffic light holds the NPC of C06/C07 in
probe 2 (an upstream junction, ~80 m before the conflict), and how its group's cycle relates to the anchored conflict
light. Per tick in synchronous mode (0.05 s) record the state of the anchor light and of every light whose stop
waypoint lies <= 3 m from the observed NPC hold-start position; print run lengths, cycle ticks and the green-start
offset (candidate - anchor) per anchor cycle. A constant offset = no choice of anchor repetition changes the upstream
phase the NPC meets.
usage: python -I native-signal-chain-diag.py [M56-P-C06,M56-P-C07]"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load

log = lambda **k: print(json.dumps(k, default=str), flush=True)
# (scene, town, NPC hold-start xy from probe2 observations, anchor light odr from the frozen phase predicate)
CASES_ALL = [('M56-P-C07', 'Town06', (-5.25, -42.88), '1228'), ('M56-P-C06', 'Town05', (-210.97, 3.06), '2389')]
CASES = [c for c in CASES_ALL if len(sys.argv) < 2 or c[0] in sys.argv[1].split(",")]
TICKS = 6000

with own_server(log) as (client, proc, start):
    for scene, town, hold, anchor in CASES:
        world = load(client, town)
        lights = list(world.get_actors().filter('traffic.traffic_light'))
        cand = []
        for t in lights:
            ds = [math.dist((w.transform.location.x, w.transform.location.y), hold) for w in t.get_stop_waypoints()]
            if ds and min(ds) <= 3.:
                cand.append(t)
                log(event='CANDIDATE', scene=scene, odr=str(t.get_opendrive_id()), stop_dist_m=round(min(ds), 2),
                    group=sorted(str(x.get_opendrive_id()) for x in t.get_group_traffic_lights()),
                    times=[t.get_green_time(), t.get_yellow_time(), t.get_red_time()])
        a = next(t for t in lights if str(t.get_opendrive_id()) == anchor)
        log(event='ANCHOR', scene=scene, odr=anchor, group=sorted(str(x.get_opendrive_id()) for x in a.get_group_traffic_lights()))
        s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = True, .05; world.apply_settings(s)
        track = [a] + cand
        seq = {str(t.get_opendrive_id()): [] for t in track}
        for _ in range(TICKS):
            world.tick()
            for t in track:
                seq[str(t.get_opendrive_id())].append(str(t.get_state()))
        s.synchronous_mode, s.fixed_delta_seconds = False, None; world.apply_settings(s)
        greens = {k: [i for i in range(1, len(v)) if v[i] == 'Green' and v[i - 1] != 'Green'] for k, v in seq.items()}
        for k, v in seq.items():
            g = greens[k]
            log(event='CYCLE', scene=scene, odr=k, green_starts=g[:8], cycle_ticks=sorted({b - a_ for a_, b in zip(g, g[1:])}))
        for t in cand:
            k = str(t.get_opendrive_id())
            offs = [min((c - g0) for c in greens[k] if c >= g0) if any(c >= g0 for c in greens[k]) else None for g0 in greens[anchor]]
            log(event='OFFSET', scene=scene, candidate=k, anchor=anchor, offset_ticks_per_anchor_cycle=offs)
print('DIAG_END')
