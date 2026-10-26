"""Report-only probe (2026-10-26, v6 item e): why the EGO's YIELD (2 -> 1 m/s, category L) drops below the frozen
0.5 m/s floor (L01-B: 1.23 -> 0.30 m/s in one tick, no collision). Town04 straight lane, vehicle.audi.a2, the runner's
synchronous dt 0.05 with substeps 0.01 x 10, no_rendering_mode as the A/B runs. Own server 2610, ONE map load; each
trial spawns a fresh actor (no reload). Trials, each from a steady 2 m/s under the stock LocalPlanner:
  brake:b   -> constant VehicleControl(brake=b) for 3 s;
  pid:Kp    -> the stock PID (K_I 0.05, K_D 0) with target 1 m/s (what the YIELD phase does), 6 s.
python -I native-yield-probe.py   (report-only; outputs/m56_yield_probe_*.json)"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, now, WS
sys.path.insert(0, 'E:/Carla/PythonAPI/carla')

OUT = WS.parents[2] / 'outputs' / f'm56_yield_probe_{now()}.json'
# pid:Kp or pid:Kp/Ki (default Ki 0.05); coast:0 = throttle 0, brake 0. Optional argv[1] = comma list of trials.
TRIALS = (sys.argv[1].split(',') if len(sys.argv) > 1 else
          ['brake:0.3', 'brake:0.2', 'brake:0.1', 'brake:0.05', 'pid:1', 'pid:0.5', 'pid:0.25', 'pid:0.1'])


def log(**k):
    print(json.dumps(k), flush=True)


def straight(m, length=300.):
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
        if len(best) * 2. >= length:
            break
    return best


with own_server(log) as (client, proc, start):
    import carla
    from agents.navigation.local_planner import LocalPlanner, RoadOption
    client.set_timeout(120.)
    world = client.load_world('Town04')
    for _ in range(3):
        world.wait_for_tick(30)
    s = world.get_settings()
    s.synchronous_mode, s.fixed_delta_seconds = True, .05
    s.substepping, s.max_substep_delta_time, s.max_substeps = True, .01, 10
    s.no_rendering_mode = True
    world.apply_settings(s); world.tick()
    m = world.get_map(); pts = straight(m); bp = world.get_blueprint_library().find('vehicle.audi.a2')
    START = int(sys.argv[2]) if len(sys.argv) > 2 else 0  # start index on the 2 m waypoint list
    log(event='STRAIGHT', waypoints=len(pts), start=START)
    results = {}
    for trial in TRIALS:
        kind, val = trial.split(':'); ki = float(val.split('/')[1]) if '/' in val else .05; val = float(val.split('/')[0])
        t0 = pts[START].transform; t0.location.z += .3
        car = world.spawn_actor(bp, t0)
        hits = []
        coll = world.spawn_actor(world.get_blueprint_library().find('sensor.other.collision'), carla.Transform(),
                                 attach_to=car)
        coll.listen(lambda e: hits.append((e.frame, str(e.other_actor.type_id), round(e.normal_impulse.length(), 1))))
        for _ in range(20):
            world.tick()

        def planner(kp, ki=.05):
            opt = {'dt': .05, 'lateral_control_dict': {'K_P': 1.95, 'K_I': .05, 'K_D': .2, 'dt': .05},
                   'longitudinal_control_dict': {'K_P': kp, 'K_I': ki, 'K_D': 0., 'dt': .05},
                   'max_throttle': .75, 'max_brake': .3, 'max_steering': .8, 'follow_speed_limits': False}
            lp = LocalPlanner(car, opt_dict=opt, map_inst=m); lp.follow_speed_limits(False)
            lp.set_global_plan([(p, RoadOption.LANEFOLLOW) for p in pts[START:]], stop_waypoint_creation=True, clean_queue=True)
            return lp
        lp = planner(1.); lp.set_speed(2 * 3.6)
        for _ in range(160):  # 8 s to a steady 2 m/s
            car.apply_control(lp.run_step()); world.tick()
        v0 = car.get_velocity().length()
        if kind in ('pid', 'pidnb', 'pidg1', 'pidbc'):  # pidnb: the same PID with the brake suppressed while the target is > 0 (coast)
            lp = planner(val, .05 if kind == 'pidbc' else ki); lp.set_speed(1 * 3.6)
        speeds, brakes, throttles, gears, where = [], [], [], [], []
        for _ in range(60 if kind == 'brake' else 200):
            c = carla.VehicleControl(throttle=0., steer=0., brake=val) if kind in ('brake', 'coast') else lp.run_step()
            if kind == 'pidnb' or (kind == 'pidbc' and car.get_velocity().length() < ki):
                c.brake = 0.  # pidbc:Kp/V = brake only while the speed is >= V (above the low-speed brake snap)
            if kind == 'pidg1':  # diagnosis only: forced first gear (the frozen stock contract forbids manual gears)
                c.manual_gear_shift, c.gear = True, 1
            car.apply_control(c); world.tick()
            speeds.append(round(car.get_velocity().length(), 4)); brakes.append(round(c.brake, 3))
            throttles.append(round(c.throttle, 3)); gears.append(car.get_control().gear)
            loc = car.get_location(); where.append((round(loc.x, 2), round(loc.y, 2), round(loc.z, 3)))
        drops = [round(a - b, 3) for a, b in zip(speeds, speeds[1:])]
        results[trial] = {'v_start': round(v0, 3), 'v_min': min(speeds), 'below_0.5': sum(v < .5 for v in speeds),
                          'max_drop_per_tick': max(drops), 'tail_mean': round(sum(speeds[-60:]) / len(speeds[-60:]), 3),
                          'speeds': speeds, 'brakes': brakes, 'throttles': throttles, 'gears': gears,
                          'where': where, 'collisions': hits}
        log(event='TRIAL', trial=trial, v_start=round(v0, 3), v_min=min(speeds), max_drop=max(drops),
            below=results[trial]['below_0.5'], tail=results[trial]['tail_mean'])
        coll.stop(); coll.destroy(); car.destroy(); world.tick()
with open(OUT, 'x', encoding='utf-8') as f:
    json.dump({'note': 'report-only yield probe (v6 item e)', 'trials': results}, f, indent=1)
print('DONE', OUT)
