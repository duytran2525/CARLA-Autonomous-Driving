"""2026-11-08 diagnostic only (no actors, no ticks, no A/B): how the frozen v1 EGO start of C07/C08 projects onto the map.
For each scene: guide heading (v1 arc 0 -> 1), get_waypoint (road, lane, yaw, junction), and for every notation lane the
nearest lane waypoint (distance, yaw) and the mean lateral offset of the v1 polyline from that lane's centre.
usage: M56_REV=<rev> python -I native-route-start-diag.py Town06 M56-P-C07,M56-P-C08"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import candidates, own_server, load

log = lambda **k: print(json.dumps(k, default=str), flush=True)
rev = candidates(('C', 'L', 'M'))
import carla
with own_server(log) as (client, proc, start):
    world = load(client, sys.argv[1]); m = world.get_map()
    for sid in sys.argv[2].split(','):
        c = next(x for x in rev.candidates if x.id == sid)
        for role in ('EGO', 'NPC'):
            notation = next(a for a in c.actors if a.role == role).route_recipe['route']
            resp = [r for r in c.responses if r.actor_role == role]
            tr = resp[0].route.transforms if resp and resp[0].route else None
            if not tr:
                log(event='NO_V1_ROUTE', scene=sid, role=role, notation=notation); continue
            a, b = tr[0], tr[1]
            head = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
            w = m.get_waypoint(carla.Location(a.x, a.y, a.z), project_to_road=True, lane_type=carla.LaneType.Driving)
            out = {'scene': sid, 'role': role, 'notation': notation, 'start': (round(a.x, 2), round(a.y, 2)),
                   'guide_heading': round(head, 1), 'proj': (w.road_id, w.lane_id, round(w.transform.rotation.yaw, 1), w.is_junction)}
            lanes = {}
            for seg in notation.split('→'):
                r, l = int(seg.split('/')[0]), int(seg.split('/')[1])
                for lane in sorted({l, l - 1, l + 1} - {0}):
                    pts = []
                    s = 0.
                    while s < 2000:
                        q = m.get_waypoint_xodr(r, lane, s)
                        if q is None:
                            break
                        pts.append(q); s += 1.
                    if not pts:
                        continue
                    near = min(pts, key=lambda q: math.dist((q.transform.location.x, q.transform.location.y), (a.x, a.y)))
                    offs = [min(math.dist((q.transform.location.x, q.transform.location.y), (t.x, t.y)) for q in pts) for t in tr[::5]]
                    lanes[f'{r}/{lane}'] = {'d_start': round(math.dist((near.transform.location.x, near.transform.location.y), (a.x, a.y)), 2),
                                            'yaw': round(near.transform.rotation.yaw, 1), 'mean_off_v1': round(sum(offs) / len(offs), 2)}
            out['lanes'] = lanes
            log(event='START_PROJECTION', **out)
print('DIAG_END')
