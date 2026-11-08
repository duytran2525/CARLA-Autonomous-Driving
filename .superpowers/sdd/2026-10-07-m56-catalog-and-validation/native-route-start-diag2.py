"""2026-11-08 diagnostic only (no actors): lane types/widths of road 13 (C07) and the heading-matching driving waypoints
within 3 m of the C08 v1 start. usage: python -I native-route-start-diag2.py"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load
log = lambda **k: print(json.dumps(k, default=str), flush=True)
import carla
with own_server(log) as (client, proc, start):
    world = load(client, 'Town06'); m = world.get_map()
    for lane in (-1, -2, -3, -4):
        q = m.get_waypoint_xodr(13, lane, 5.)
        if q: log(event='LANE', road=13, lane=lane, type=str(q.lane_type), width=round(q.lane_width, 2),
                  xy=(round(q.transform.location.x, 2), round(q.transform.location.y, 2)))
    x, y = -3.81, 41.29
    hits = []
    for w in m.generate_waypoints(.5):
        d = math.dist((w.transform.location.x, w.transform.location.y), (x, y))
        if d < 3:
            hits.append((round(d, 2), w.road_id, w.lane_id, round(w.transform.rotation.yaw, 1), w.is_junction))
    log(event='C08_NEAR', hits=sorted(hits)[:30])
print('DIAG_END')
