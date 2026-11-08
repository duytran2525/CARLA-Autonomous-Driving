"""2026-11-08 diagnostic only (no actors): at the deepest NPC footprint points outside the drivable union (C02, M07,
M06), the CARLA lane type (get_waypoint, any lane type) and the first cast_ray label straight down.
usage: python -I native-edge-surface-diag.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load
log = lambda **k: print(json.dumps(k, default=str), flush=True)
POINTS = {'Town04': [('C02', 342.5, -125.2)], 'Town05': [('M07', 20.3, 81.5), ('M06', -138.2, 141.8)]}
import carla
with own_server(log) as (client, proc, start):
    for town, pts in [(t, p) for t, p in POINTS.items() if len(sys.argv) < 2 or t in sys.argv[1:]]:
        world = load(client, town); m = world.get_map()
        for sid, x, y in pts:
            for dx, dy in ((0, 0), (.25, 0), (-.25, 0), (0, .25), (0, -.25)):
                loc = carla.Location(x + dx, y + dy, 0.)
                w = m.get_waypoint(loc, project_to_road=False, lane_type=carla.LaneType.Any)
                g = world.ground_projection(carla.Location(x + dx, y + dy, 5.), 15.)
                hits = world.cast_ray(carla.Location(x + dx, y + dy, (g.location.z if g else 0.) + 3.),
                                      carla.Location(x + dx, y + dy, (g.location.z if g else 0.) - 3.))
                log(event='SURFACE', scene=sid, xy=(round(x + dx, 2), round(y + dy, 2)),
                    lane=(w.road_id, w.lane_id, str(w.lane_type), round(w.lane_width, 2)) if w else None,
                    ray=str(hits[0].label) if hits else None, ground=str(g.label) if g else None)
print('DIAG_END')
