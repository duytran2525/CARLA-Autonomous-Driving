"""Read-only route debugging on the own server (2610): prints the CARLA waypoint chain the guided builder sees along a
frozen v1 EGO route (no actors, no ticks). python -I native-route-debug.py Town04 M56-P-M01"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import candidates, own_server, load, _yawdiff

TOWN, SCENE = sys.argv[1], sys.argv[2]
c = [x for x in candidates(('C', 'L', 'M')).candidates if x.id == SCENE][0]
v1 = next(r for r in c.responses if r.actor_role == 'EGO').route
print('notation', [a.route_recipe['route'] for a in c.actors if a.role == 'EGO'])
with own_server(lambda **k: print(json.dumps(k))) as (client, proc, start):
    import carla
    m = load(client, TOWN).get_map()
    last = None
    for i, t in enumerate(v1.transforms):
        w = m.get_waypoint(carla.Location(t.x, t.y, t.z), project_to_road=True, lane_type=carla.LaneType.Driving)
        key = (w.road_id, w.lane_id)
        if key != last:
            d = math.dist((w.transform.location.x, w.transform.location.y), (t.x, t.y))
            print(f'v1[{i}] arc {float(v1.arc[i]):.1f} -> road/lane {key} junction={w.is_junction} off={d:.2f} '
                  f'dz={w.transform.location.z - t.z:.2f} yawdiff={_yawdiff(w.transform.rotation.yaw, t.yaw):.1f}')
            last = key
    from native_v2_common import route_rows
    guide = [(t.x, t.y, t.z) for t in v1.transforms]
    notation = [a.route_recipe['route'] for a in c.actors if a.role == 'EGO'][0]
    try:
        rows, ei, info = route_rows(m, TOWN, notation, 0., 15., guide)
        seq = []
        for r in rows:
            if not seq or seq[-1] != (r['road'], r['lane']):
                seq.append((r['road'], r['lane']))
        print('route_rows OK exit', ei, info, seq)
    except Exception as e:
        print('route_rows FAILED', repr(e)[:600])
    nn = [a.route_recipe['route'] for a in c.actors if a.role == 'NPC'][0]
    try:
        rows, ei, info = route_rows(m, TOWN, nn, 150., 15. + 60 * 3., None)
        seq = []
        for r in rows:
            if not seq or seq[-1] != (r['road'], r['lane']):
                seq.append((r['road'], r['lane']))
        print('NPC route_rows OK exit', ei, seq)
    except Exception as e:
        print('NPC route_rows FAILED', repr(e)[:600])
