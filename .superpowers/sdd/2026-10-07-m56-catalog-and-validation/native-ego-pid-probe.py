"""Report-only native measurement (own server 2610): does the PINNED stock EGO BasicAgent (spec 6.1 config, as
response.create_stock_driver) settle to a <= 0.10 m/s 2 s speed window at the I/O nominal speeds? No catalog, fixture
or A/B use. Also the NPC LocalPlanner with stock gains and the v5 P-NPC grid at one high speed, for comparison.
python -I native-ego-pid-probe.py"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load, now, WS
sys.path.insert(0, 'E:/Carla/PythonAPI/carla')

OUT = WS.parents[2] / 'outputs' / f'm56_ego_pid_probe_{now()}.json'
EGO_SPEEDS = (4., 6., 7.5, 9.375, 11.71875, 14.6484375, 18.310546875)
EXTRA = tuple(float(x) for x in sys.argv[1].split(',')) if len(sys.argv) > 1 else None  # EGO-only speeds
GRID = ((1., .05, 0.), (.5, .05, 0.), (.3, .05, 0.), (.5, .2, 0.), (.3, .2, 0.), (.2, .1, 0.))
SECONDS = 40.
rows = []


def log(**k):
    print(json.dumps(k), flush=True)


def straight_start(m, length=900.):
    """First driving waypoint (by road id) whose lane runs >= length m ahead with < 1 degree total yaw change."""
    import carla
    best = None
    for w in sorted(m.generate_waypoints(20.), key=lambda w: (w.road_id, w.lane_id, w.s)):
        if w.is_junction or w.lane_type != carla.LaneType.Driving:
            continue
        pts, cur, y0 = [w], w, w.transform.rotation.yaw
        dev = lambda p: abs((p.transform.rotation.yaw - y0 + 180) % 360 - 180)
        while len(pts) * 2. < length:
            nxt = [p for p in cur.next(2.) if p.lane_type == carla.LaneType.Driving]
            if not nxt or dev(min(nxt, key=dev)) > 1.:
                break
            cur = min(nxt, key=dev); pts.append(cur)
        if best is None or len(pts) > len(best):
            best = pts
    return best


def run(world, m, pts, kind, speed, gains):
    import carla
    from agents.navigation.basic_agent import BasicAgent
    from agents.navigation.local_planner import LocalPlanner, RoadOption
    bp = world.get_blueprint_library().find('vehicle.audi.a2')
    tf = pts[0].transform; tf.location.z += .3
    actor = world.spawn_actor(bp, tf)
    try:
        for _ in range(20):
            world.tick()
        opt = {'dt': .05, 'lateral_control_dict': {'K_P': 1.95, 'K_I': .05, 'K_D': .2, 'dt': .05},
               'longitudinal_control_dict': {'K_P': gains[0], 'K_I': gains[1], 'K_D': gains[2], 'dt': .05},
               'max_throttle': .75, 'max_brake': .3, 'max_steering': .8, 'follow_speed_limits': False}
        plan = [(p, RoadOption.LANEFOLLOW) for p in pts]
        if kind == 'EGO':
            opt.update(ignore_traffic_lights=True, ignore_stop_signs=True, ignore_vehicles=True)
            agent = BasicAgent(actor, target_speed=speed * 3.6, opt_dict=opt, map_inst=m)
            agent.follow_speed_limits(False); agent.set_target_speed(speed * 3.6)
            agent.get_local_planner().set_global_plan(plan, stop_waypoint_creation=True, clean_queue=True)
        else:
            agent = LocalPlanner(actor, opt_dict=opt, map_inst=m)
            agent.follow_speed_limits(False); agent.set_speed(speed * 3.6)
            agent.set_global_plan(plan, stop_waypoint_creation=True, clean_queue=True)
        v = []
        for i in range(int(min(SECONDS, (len(pts) * 2. - 60.) / speed + 6.) * 20)):
            actor.apply_control(agent.run_step())
            world.tick()
            s = actor.get_velocity(); v.append(math.hypot(s.x, s.y, s.z))
        windows = [(i / 20., max(v[i - 40:i]) - min(v[i - 40:i]), sum(v[i - 40:i]) / 40) for i in range(40, len(v) + 1)]
        ok = [w for w in windows if w[1] <= .10 and min(v[int(round(w[0] * 20)) - 40:int(round(w[0] * 20))]) > .5]
        row = {'kind': kind, 'target_mps': speed, 'gains': gains,
               'first_steady_t_s': ok[0][0] if ok else None, 'steady_mean_mps': ok[0][2] if ok else None,
               'min_window_range_mps': min(w[1] for w in windows),
               'last_10s_range_mps': max(v[-200:]) - min(v[-200:]), 'last_10s_mean_mps': sum(v[-200:]) / 200}
        log(**row); rows.append(row)
    finally:
        actor.destroy(); world.tick()


with own_server(log) as (client, proc, start):
    world = load(client, 'Town06')
    s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = True, .05
    s.substepping, s.max_substep_delta_time, s.max_substeps = True, .01, 10
    world.apply_settings(s)
    m = world.get_map(); pts = straight_start(m)
    log(event='STRETCH', road=pts[0].road_id, lane=pts[0].lane_id, s=pts[0].s, n=len(pts))
    for v in EXTRA or EGO_SPEEDS:
        run(world, m, pts, 'EGO', v, GRID[0])
    for g in (() if EXTRA else GRID):
        run(world, m, pts, 'NPC', 8.6, g)
with open(OUT, 'x', encoding='utf-8') as f:
    json.dump({'note': 'report-only stock PID probe; not catalog/fixture/A-B evidence', 'rows': rows}, f, indent=1)
print('DONE', OUT)
