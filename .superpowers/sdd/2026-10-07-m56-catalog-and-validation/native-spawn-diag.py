"""2026-11-08 diagnostic only (no A/B, no fixture, no TRIGGER): why does the EGO of M02/M08 fail to spawn ("collision at
spawn position") since erratum 3? Own server 2610. For each scene: the prepare pose (frozen v1 arc 0 + 2 cm, ground + 1 cm,
pitch 0) and variants (row pitch, z + 5/10/25 cm, 1/2/5 m downstream); try_spawn each, destroy at once. Also lists the
environment objects whose bbox contains the pose. Prints one JSON row per try.
usage: M56_REV=<v5g revision> python -I native-spawn-diag.py Town04:M56-P-M02 Town07:M56-P-M08"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import candidates, own_server, load

rows = []
log = lambda **k: (rows.append(k), print(json.dumps(k, default=str), flush=True))
rev = candidates(('C', 'L', 'M'))
import carla
with own_server(log) as (client, proc, start):
    for spec in sys.argv[1:]:
        town, sid = spec.split(':')
        c = next(x for x in rev.candidates if x.id == sid)
        world = load(client, town)
        bp = world.get_blueprint_library().find('vehicle.audi.a2')
        tr = next(r for r in c.responses if r.actor_role == 'EGO').route.transforms
        a, b = tr[0], tr[1]
        L = math.dist((a.x, a.y), (b.x, b.y)); ux, uy = (b.x - a.x) / L, (b.y - a.y) / L
        wp = world.get_map().get_waypoint(carla.Location(a.x, a.y, a.z))
        log(event='START', scene=sid, xyz=(a.x, a.y, a.z), yaw=a.yaw, wp_road=wp.road_id, wp_lane=wp.lane_id,
            wp_junction=wp.is_junction, wp_pitch=wp.transform.rotation.pitch, wp_z=wp.transform.location.z)
        for name, along, dz, pitch in [('prepare', .02, .01, 0.), ('row_pitch', .02, .01, wp.transform.rotation.pitch),
                                       ('corners', .02, None, 0.), ('z+3cm', .02, .03, 0.), ('z+4cm', .02, .04, 0.), ('z+5cm', .02, .05, 0.), ('z+10cm', .02, .10, 0.), ('z+25cm', .02, .25, 0.),
                                       ('down1m', 1., .01, 0.), ('down2m', 2., .01, 0.), ('down5m', 5., .01, 0.)]:
            x, y = a.x + ux * along, a.y + uy * along
            g = world.ground_projection(carla.Location(x, y, a.z + 2.), 10.)
            z = (g.location.z if g is not None else a.z) + (dz or 0.)
            if dz is None:  # 'corners': highest ground under the 4 footprint corners + centre, + 1 cm
                h = math.radians(a.yaw); ex, ey = 1.8527, 0.894
                pts = [(x, y)] + [(x + sx * ex * math.cos(h) - sy * ey * math.sin(h), y + sx * ex * math.sin(h) + sy * ey * math.cos(h))
                                  for sx in (-1, 1) for sy in (-1, 1)]
                gz = [world.ground_projection(carla.Location(px, py, a.z + 2.), 10.) for px, py in pts]
                z = max(q.location.z for q in gz if q is not None) + .01
                log(event='CORNERS', scene=sid, lift_m=z - .01 - g.location.z, grounds=[q.location.z if q else None for q in gz])
            t = carla.Transform(carla.Location(x, y, z), carla.Rotation(pitch, a.yaw, 0.))
            car = world.try_spawn_actor(bp, t)
            log(event='TRY', scene=sid, variant=name, ok=car is not None, ground=g.location.z if g else None,
                ground_label=str(g.label) if g else None, z=z)
            if car is not None:
                car.destroy()
        hits = []
        for o in world.get_environment_objects(carla.CityObjectLabel.Any):
            bb = o.bounding_box
            if bb.location.distance(carla.Location(a.x, a.y, a.z)) < 6:
                hits.append((o.name, str(o.type), round(bb.location.x, 2), round(bb.location.y, 2), round(bb.location.z, 2),
                             round(bb.extent.x, 2), round(bb.extent.y, 2), round(bb.extent.z, 2)))
        log(event='NEAR_OBJECTS', scene=sid, objects=hits[:40], n=len(hits))
print('DIAG_END')
