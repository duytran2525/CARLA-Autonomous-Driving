"""2026-11-08 diagnostic only (no actors, no ticks): which light holds the NPC of M01 in probe 2 (37 s at ~4 m from the
conflict box centre) although signal-phase v1 S1 anchored light 1619, whose stop station (122 m) lies BEHIND the
phased NPC start (139 m). For every light with a stop waypoint <= 8 m from the hold-start position: station and lateral
offset of each stop waypoint on the frozen phased NPC route (routes-v2.json rows), and whether
World.get_traffic_lights_from_waypoint from the phased NPC start returns it.
usage: python -I native-signal-m01-diag.py <prepare dir>/M56-P-M01"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load

log = lambda **k: print(json.dumps(k, default=str), flush=True)
HOLD = (315.02, -229.26)
d = Path(sys.argv[1])
f = lambda x: float.fromhex(x['binary64'])
rows = json.load(open(d / 'routes-v2.json', encoding='utf-8'))['NPC']
pts = [(f(r['x']), f(r['y'])) for r in rows]
arc = [0.]
for a, b in zip(pts, pts[1:]):
    arc.append(arc[-1] + math.dist(a, b))
P = json.load(open(d / 'prepare.json', encoding='utf-8'))
s0, n_entry = f(P['npc_start_station_probe1']), f(P['n_entry_probe1'])
log(event='ROUTE', rows=len(rows), length_m=round(arc[-1], 2), n_entry_on_v2=round(n_entry - s0, 2))

def on_route(x, y):
    i = min(range(len(pts)), key=lambda j: math.dist(pts[j], (x, y)))
    return round(arc[i], 2), round(math.dist(pts[i], (x, y)), 3)

import carla
with own_server(log) as (client, proc, start):
    world = load(client, 'Town04'); m = world.get_map()
    r0 = rows[0]
    wp = m.get_waypoint_xodr(int(r0['road']), int(r0['lane']), f(r0['s']))
    along = {str(t.get_opendrive_id()) for t in world.get_traffic_lights_from_waypoint(wp, arc[-1] + 1.)}
    log(event='ALONG_FROM_PHASED_START', lights=sorted(along))
    for t in world.get_actors().filter('traffic.traffic_light'):
        sws = t.get_stop_waypoints()
        ds = [math.dist((w.transform.location.x, w.transform.location.y), HOLD) for w in sws]
        if ds and min(ds) <= 8.:
            log(event='CANDIDATE', odr=str(t.get_opendrive_id()), returned_along=str(t.get_opendrive_id()) in along,
                group=sorted(str(x.get_opendrive_id()) for x in t.get_group_traffic_lights()),
                stops=[{'road': w.road_id, 'lane': w.lane_id, 'xy': (round(w.transform.location.x, 2), round(w.transform.location.y, 2)),
                        'dist_hold_m': round(dd, 2), 'station_lateral_on_v2': on_route(w.transform.location.x, w.transform.location.y)}
                       for w, dd in zip(sws, ds)])
print('DIAG_END')
