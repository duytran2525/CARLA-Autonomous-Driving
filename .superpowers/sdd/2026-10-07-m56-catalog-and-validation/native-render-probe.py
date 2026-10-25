"""Duy [chat] 2026-10-25: before enabling CARLA no_rendering_mode, check on a probe that physics and traffic lights do
not change. Own server 2610. Three trials on Town04, each after a fresh load_world, synchronous dt 0.05 with the
runner's substepping: ON (rendering), ON again (baseline run-to-run variation), OFF (no_rendering_mode).
Each trial: EGO = stock BasicAgent at 6 m/s (the PID limit-cycle regime, sensitive) and NPC = stock LocalPlanner at
4 m/s on straight lanes, 40 s; every traffic light's (state, elapsed tick) per tick.
Pass: OFF-vs-ON differences no larger than the ON-vs-ON baseline (+1e-6) and identical light sequences.
python -I native-render-probe.py   (report-only; outputs/m56_render_probe_*.json)"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, now, WS
sys.path.insert(0, 'E:/Carla/PythonAPI/carla')

OUT = WS.parents[2] / 'outputs' / f'm56_render_probe_{now()}.json'
TICKS = 800


def log(**k):
    print(json.dumps(k), flush=True)


def straight(m, length=400.):
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


def trial(client, render):
    import carla
    from agents.navigation.basic_agent import BasicAgent
    from agents.navigation.local_planner import LocalPlanner, RoadOption
    client.set_timeout(120.)
    world = client.load_world('Town04')
    for _ in range(3):
        world.wait_for_tick(30)
    s = world.get_settings()
    s.synchronous_mode, s.fixed_delta_seconds = True, .05
    s.substepping, s.max_substep_delta_time, s.max_substeps = True, .01, 10
    s.no_rendering_mode = not render
    world.apply_settings(s)
    world.tick()
    m = world.get_map()
    pts = straight(m)
    side = pts[0].get_left_lane() or pts[0].get_right_lane()
    bp = world.get_blueprint_library().find('vehicle.audi.a2')
    t0 = pts[0].transform; t0.location.z += .3
    ego = world.spawn_actor(bp, t0)
    npc_start = side.next(10.)[0] if side is not None else pts[5]
    t1 = npc_start.transform; t1.location.z += .3
    npc = world.spawn_actor(bp, t1)
    for _ in range(20):
        world.tick()
    opt = {'dt': .05, 'lateral_control_dict': {'K_P': 1.95, 'K_I': .05, 'K_D': .2, 'dt': .05},
           'longitudinal_control_dict': {'K_P': 1., 'K_I': .05, 'K_D': 0., 'dt': .05},
           'max_throttle': .75, 'max_brake': .3, 'max_steering': .8, 'follow_speed_limits': False}
    eopt = dict(opt, ignore_traffic_lights=True, ignore_stop_signs=True, ignore_vehicles=True)
    a = BasicAgent(ego, target_speed=6 * 3.6, opt_dict=eopt, map_inst=m)
    a.follow_speed_limits(False); a.set_target_speed(6 * 3.6)
    a.get_local_planner().set_global_plan([(p, RoadOption.LANEFOLLOW) for p in pts], stop_waypoint_creation=True, clean_queue=True)
    lane = [npc_start]
    while len(lane) < 150 and lane[-1].next(2.):
        lane.append(lane[-1].next(2.)[0])
    lp = LocalPlanner(npc, opt_dict=dict(opt), map_inst=m)
    lp.follow_speed_limits(False); lp.set_speed(4 * 3.6)
    lp.set_global_plan([(p, RoadOption.LANEFOLLOW) for p in lane], stop_waypoint_creation=True, clean_queue=True)
    lights = sorted(world.get_actors().filter('traffic.traffic_light'), key=lambda x: x.id)
    rows = []
    for _ in range(TICKS):
        ego.apply_control(a.run_step()); npc.apply_control(lp.run_step())
        world.tick()
        row = {}
        for name, x in (('ego', ego), ('npc', npc)):
            tr, v = x.get_transform(), x.get_velocity()
            row[name] = (tr.location.x, tr.location.y, tr.location.z, tr.rotation.yaw, math.hypot(v.x, v.y, v.z))
        row['lights'] = tuple((l.id, str(l.get_state()), round(l.get_elapsed_time() * 20)) for l in lights)
        rows.append(row)
    ego.destroy(); npc.destroy(); world.tick()
    return rows


def diff(a, b):
    out = {}
    for name in ('ego', 'npc'):
        out[name + '_max_pos_m'] = max(math.dist(x[name][:3], y[name][:3]) for x, y in zip(a, b))
        out[name + '_max_speed_mps'] = max(abs(x[name][4] - y[name][4]) for x, y in zip(a, b))
    out['light_ticks_differing'] = sum(1 for x, y in zip(a, b) if x['lights'] != y['lights'])
    return out


# One fresh server per trial, the map loaded once per server (as the preparation and A/B tools do): reloading Town04
# inside one server crashed CARLA twice on 2026-10-25 (EXCEPTION_ACCESS_VIOLATION, same call stack).
trials = []
for render in (True, True, False):
    with own_server(log) as (client, proc, start):
        trials.append(trial(client, render))
on1, on2, off = trials
base, test = diff(on1, on2), diff(on1, off)
ok = (all(test[k] <= base[k] + 1e-6 for k in test if k != 'light_ticks_differing')
      and test['light_ticks_differing'] == 0 and base['light_ticks_differing'] == 0)
report = {'note': 'report-only render probe (Duy 2026-10-25)', 'ticks': TICKS, 'baseline_on_vs_on': base,
          'on_vs_off': test, 'lights': len(on1[0]['lights']), 'pass': ok}
with open(OUT, 'x', encoding='utf-8') as f:
    json.dump(report, f, indent=1)
log(**report)
print('DONE', OUT)
