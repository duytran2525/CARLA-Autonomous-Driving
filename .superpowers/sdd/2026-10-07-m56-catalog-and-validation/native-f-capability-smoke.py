"""2026-11-08 A-SEL2 F capability smoke (PLAN_M56_F_ASEL2_20261108.md 3.1), observe-only, own server 2610. No scene.
(1) F03 rollback: vehicle.audi.a2 on the steepest stretch of the fill F03 site (Town04 road 40, uphill lane), held with
    brake 1 for 2 s, then released: throttle 0, brake 0, hand_brake False, manual_gear_shift True, gear 0 (neutral).
    Record backward speed (along -forward) per tick for 10 s: does it reach >= 0.20 m/s for >= 0.25 s?
(2) F06 reverse witness: on a flat straight (Town04 spawn point 0 lane), control reverse=True throttle 0.3 for 3 s:
    readback control.reverse, gear, light_state (Reverse bit), backward speed.
usage: python -I native-f-capability-smoke.py"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load

log = lambda **k: print(json.dumps(k, default=str), flush=True)
with own_server(log) as (client, proc, start):
    import carla
    world = load(client, 'Town04'); m = world.get_map()
    s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = True, .05; world.apply_settings(s)
    bp = world.get_blueprint_library().find('vehicle.audi.a2')
    # (1) steepest point of road 40 among its driving lanes (sample every 2 m)
    best = None
    for lane in (-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6):
        sv = 1.
        while True:
            w = m.get_waypoint_xodr(40, lane, sv)
            if w is None:
                break
            n = w.next(2.)
            if n:
                pitch = n[0].transform.location.z - w.transform.location.z
                if best is None or pitch > best[0]:
                    best = (pitch / 2., w)
            sv += 2.
    if best is None:
        log(event='F03_NO_SITE')
    else:
        grade, w = best
        t = w.transform; t.location.z += .3
        v = world.try_spawn_actor(bp, t)
        log(event='F03_SPAWN', grade=round(grade, 4), road=w.road_id, lane=w.lane_id, s=round(w.s, 1), spawned=v is not None)
        if v is not None:
            for _ in range(40):
                v.apply_control(carla.VehicleControl(brake=1.)); world.tick()
            back = []
            for i in range(200):
                v.apply_control(carla.VehicleControl(throttle=0., brake=0., hand_brake=False, manual_gear_shift=True, gear=0))
                world.tick()
                f = v.get_transform().get_forward_vector(); vel = v.get_velocity()
                back.append(-(vel.x * f.x + vel.y * f.y + vel.z * f.z))
            run = best_run = 0
            for b in back:
                run = run + 1 if b >= .2 else 0; best_run = max(best_run, run)
            log(event='F03_ROLLBACK', max_back_mps=round(max(back), 3), ticks_ge_0p2=sum(b >= .2 for b in back),
                longest_run_ticks=best_run, ok=best_run >= 5, at_s=[round(back[i], 3) for i in (10, 40, 80, 120, 199)])
            v.destroy(); world.tick()
    # (2) reverse witness on spawn point 0
    sp = m.get_spawn_points()[0]
    v = world.try_spawn_actor(bp, sp)
    if v is not None:
        for _ in range(20):
            v.apply_control(carla.VehicleControl(brake=1.)); world.tick()
        rows = []
        for i in range(60):
            v.apply_control(carla.VehicleControl(throttle=.3, reverse=True)); world.tick()
            c = v.get_control(); f = v.get_transform().get_forward_vector(); vel = v.get_velocity()
            rows.append((c.reverse, c.gear, str(v.get_light_state()), -(vel.x * f.x + vel.y * f.y)))
        log(event='F06_REVERSE', readback_reverse=all(r[0] for r in rows[5:]), gears=sorted({r[1] for r in rows}),
            lights=sorted({r[2] for r in rows}), back_mps_end=round(rows[-1][3], 3))
        v.destroy(); world.tick()
    s.synchronous_mode, s.fixed_delta_seconds = False, None; world.apply_settings(s)
print('F_SMOKE_END')
