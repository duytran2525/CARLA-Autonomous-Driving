"""G4 corroboration probe (addendum A-G45, prereg v2 §5). Own server 2610 only; no A/B, no catalog scene episode.

Answers, natively, the facts the v2 materializer needs:
  Q1 a2 bounding box (length budget 4.5 m);
  Q2 pose readback of a freshly spawned vehicle before and after the first tick (consumer requires boundary pose ==
     fixture pose);
  Q3 world.ground_projection at the body-bottom corners (ground error budget 0.05 m);
  Q4 collision sensor: listen, tick, drain, and the tick/ack fence (no deliberate collision);
  Q5 XODR lane-centre vs CARLA waypoint deviation along the C01 EGO and NPC routes.
Run with .venv-m56-native-v1: python -I native-g4-probe.py
"""
from datetime import datetime, timezone
from pathlib import Path
import collections, json, math, socket, subprocess, sys, time

WS = Path(__file__).parent
sys.path.insert(0, str(WS))
import xodr_routes as xr  # noqa: E402

EXE, RPC = Path('E:/Carla/CarlaUE4.exe'), 2610
out = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs') / f'm56_native_g4_probe_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}'
out.mkdir(parents=False, exist_ok=False)
rows = {}


def port_open():
    with socket.socket() as s:
        s.settimeout(1); return s.connect_ex(('127.0.0.1', RPC)) == 0


def tf(t):
    return [t.location.x, t.location.y, t.location.z, t.rotation.pitch, t.rotation.yaw, t.rotation.roll]


assert 'CarlaUE4' not in subprocess.run(['tasklist', '/FI', 'IMAGENAME eq CarlaUE4*'], capture_output=True, text=True).stdout
assert not port_open()
proc = subprocess.Popen([str(EXE), f'-carla-rpc-port={RPC}', '-RenderOffScreen', '-quality-level=Low', '-nosound'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    t0 = time.monotonic()
    while not port_open():
        assert proc.poll() is None and time.monotonic() - t0 < 180
        time.sleep(2)
    import carla
    client = carla.Client('127.0.0.1', RPC)
    for _ in range(6):
        try:
            client.set_timeout(60); client.get_world(); break
        except RuntimeError:
            time.sleep(10)
    world = client.load_world('Town04')
    s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = True, 0.05
    s.substepping, s.max_substep_delta_time, s.max_substeps = True, 0.01, 10
    world.apply_settings(s); world.tick()
    m = world.get_map()
    # Q5 route deviation (C01 notation from the frozen candidate)
    for role, notation, want in (('EGO', '0/+1→179/+1→51/-1', 51.3), ('NPC', '16/+1→209/+1→15/+1', 45.0)):
        pts, arc, exit_arc, app, outl = xr.junction_route('Town04', notation, want, 15.)
        dev = []
        for p in pts:
            w = m.get_waypoint(carla.Location(p[0], p[1], p[2]), project_to_road=True, lane_type=carla.LaneType.Driving)
            dev.append((math.hypot(w.transform.location.x - p[0], w.transform.location.y - p[1]), abs(w.transform.location.z - p[2])))
        rows[f'Q5_{role}'] = {'points': len(pts), 'max_xy_dev_m': max(d[0] for d in dev), 'max_z_dev_m': max(d[1] for d in dev),
                              'start': list(pts[0])}
    # Q1-Q3 spawn at the EGO route start
    start = rows['Q5_EGO']['start']
    gp = world.ground_projection(carla.Location(start[0], start[1], start[2] + 2), 10)
    rows['Q3_ground_at_start'] = {'xodr_z': start[2], 'ground_z': gp.location.z if gp else None,
                                  'label': str(gp.label) if gp else None}
    bp = world.get_blueprint_library().find('vehicle.audi.a2')
    z0 = (gp.location.z if gp else start[2]) + 0.01
    spawn_tf = carla.Transform(carla.Location(start[0], start[1], z0), carla.Rotation(yaw=start[3]))
    r = client.apply_batch_sync([carla.command.SpawnActor(bp, spawn_tf)], False)[0]
    assert not r.error, r.error
    car = world.get_actor(r.actor_id)
    before = tf(car.get_transform())
    snap_before = world.get_snapshot().find(car.id)
    world.tick()
    after1 = tf(car.get_transform())
    b = car.bounding_box
    rows['Q1_bbox'] = {'location': [b.location.x, b.location.y, b.location.z], 'extent': [b.extent.x, b.extent.y, b.extent.z],
                       'rotation': [b.rotation.pitch, b.rotation.yaw, b.rotation.roll], 'length_m': 2 * b.extent.x}
    rows['Q2_pose'] = {'requested': [start[0], start[1], z0, 0., start[3], 0.], 'before_tick': before,
                       'snapshot_has_actor_before_tick': snap_before is not None, 'after_tick1': after1}
    # Q3 ground under the bottom corners after settling 20 ticks
    for _ in range(20):
        world.tick()
    t = car.get_transform(); corners = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            local = carla.Location(b.location.x + sx * b.extent.x, b.location.y + sy * b.extent.y, b.location.z - b.extent.z)
            w = t.transform(local)
            g = world.ground_projection(carla.Location(w.x, w.y, w.z + 2), 10)
            corners.append({'corner_z': w.z, 'ground_z': g.location.z if g else None})
    rows['Q3_settled'] = {'pose': tf(t), 'velocity': [car.get_velocity().x, car.get_velocity().y, car.get_velocity().z],
                          'corners': corners, 'max_gap_m': max(abs(c['corner_z'] - c['ground_z']) for c in corners if c['ground_z'] is not None)}
    # Q4 collision sensor fence
    pending = collections.deque()
    sbp = world.get_blueprint_library().find('sensor.other.collision')
    sr = client.apply_batch_sync([carla.command.SpawnActor(sbp, carla.Transform(), car.id)], False)[0]
    sensor = world.get_actor(sr.actor_id)
    sensor.listen(lambda e: pending.append(e.frame))
    frames = [world.tick() for _ in range(10)]
    fence = world.tick()
    rows['Q4_collision'] = {'sensor_id': sensor.id, 'frames': [frames[0], frames[-1]], 'fence_frame': fence,
                            'packets': list(pending), 'remaining_after_fence': len(pending)}
    sensor.stop()
    client.apply_batch_sync([carla.command.DestroyActor(sensor.id), carla.command.DestroyActor(car.id)], False)
    world.tick()
    rows['survivors'] = [a.id for a in world.get_actors() if a.type_id.startswith(('vehicle.', 'sensor.other'))]
finally:
    subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)
    (out / 'g4-probe.json').write_text(json.dumps(rows, indent=1, default=str), encoding='utf-8')
print(json.dumps(rows, indent=1, default=str))
print('DONE', out)
