"""Report-only probe (2026-10-26): CARLA surface label under body vertices that left the frozen drivable union
(Driving-lane quads only). Roads => the union is too narrow (junction interior / shoulders); Sidewalks/Terrain => the
vehicle really left the road. Empty world, own server 2610, one map load per process.
python -I native-surface-probe.py TOWN POINTS.json  (points from a read-only extraction of sealed episodes)"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load, now, WS

town, points = sys.argv[1], json.loads(Path(sys.argv[2]).read_text())
OUT = WS.parents[2] / 'outputs' / f'm56_surface_probe_{town}_{now()}.json'


def log(**k):
    print(json.dumps(k, default=str), flush=True)


rows = []
with own_server(log) as (client, proc, start):
    import carla
    world = load(client, town); m = world.get_map()
    for pt in points:
        top = carla.Location(pt['x'], pt['y'], pt['z'] + 2.)
        hits = world.cast_ray(top, carla.Location(pt['x'], pt['y'], pt['z'] - 3.))
        w = m.get_waypoint(carla.Location(pt['x'], pt['y'], pt['z']), project_to_road=False, lane_type=carla.LaneType.Any)
        rows.append({**pt, 'cast_ray': [[h.location.z, str(h.label)] for h in hits],
                     'lane_at_point': None if w is None else [w.road_id, w.lane_id, str(w.lane_type), w.is_junction]})
        log(**rows[-1])
with open(OUT, 'x', encoding='utf-8') as f:
    json.dump({'note': 'report-only surface probe, empty world', 'town': town, 'rows': rows}, f, indent=1)
print('DONE', OUT)
