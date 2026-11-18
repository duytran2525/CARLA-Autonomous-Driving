"""2026-11-18 F03 capability probe v2 (observe-only, no scene, no A/B; Claude under Duy delegation, [chat] 18/11 "làm hết").
native-f03-grade-probe.py (09/11, r7): 0/6 grade sites (pitch 3.5-8.8 deg) rolled back after brake 2 s -> neutral; the backward
speed stayed exactly 0. Hypothesis (Claude's reading, not tested): the body was put to sleep at rest and releasing the brake
does not wake it. This probe releases the vehicle WITHOUT a prior standstill hold, three modes per site, fresh spawn each:
  motion-auto:   throttle 0.4 (automatic gear) until forward speed >= 0.8 m/s (<= 6 s), then throttle 0, brake 0;
  motion-neutral: same, then throttle 0, brake 0, manual_gear_shift gear 0;
  free:          spawn and never brake or throttle (control all zero from the first tick).
Per run: the backward speed series 10 s after release, the spec 8.1 F03 trigger (>= 0.20 m/s for >= 0.25 s) and the mean
backward speed over the first 2 s after it (F03 vN_char range [0.65, 1.54] in PREREG F part 1).
usage: python -I native-f03-rollback-probe.py TOWN [N=3]"""
import importlib.util
import json
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from native_v2_common import own_server, load, stream_to  # noqa: E402

log = lambda **k: print(json.dumps(k, default=str), flush=True)
TOWN = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 3
# r18f (advisor check 2): --brake = only mode motion-neutral, then the product F03 law: brake 0.3 from TRIGGER + 2 s
# (+1 tick); records rollback distance release -> rest and whether it stops (vs d0 = 5.2 m); --roads a,b keeps sites
BRAKE = '--brake' in sys.argv
ROADS = next((set(int(x) for x in a.split('=')[1].split(',')) for a in sys.argv if a.startswith('--roads=')), None)
s = importlib.util.spec_from_file_location('gen', here / 'fill20-generate.py'); gen = importlib.util.module_from_spec(s); s.loader.exec_module(gen)
import xodr_routes as xr  # noqa: E402
gen.ROOT = xr.xodr_path(TOWN).parent
gen.USED_JUNCTIONS[TOWN] = set(); gen.USED_ANCHORS[TOWN] = []
_, _, r3 = gen.scan(TOWN)
r3 = sorted(r3, key=lambda c: -(c['grade_run'][1] - c['grade_run'][0]))[:N]
if ROADS is not None:
    r3 = [c for c in r3 if c['road'] in ROADS]


def trigger(back):
    run = 0
    for i, b in enumerate(back):
        run = run + 1 if b >= .2 else 0
        if run == 6:
            return i
    return None


with own_server(log) as (client, proc, start):
    import carla
    world = load(client, TOWN); m = world.get_map()
    st = world.get_settings(); st.synchronous_mode, st.fixed_delta_seconds = True, .05; world.apply_settings(st)
    bp = world.get_blueprint_library().find('vehicle.audi.a2')
    for c in r3:
        s0, s1, _ = c['grade_run']
        w = m.get_waypoint_xodr(c['road'], c['lane'], s0 + (s1 - s0) * .3)  # low on the run: room to drive up first
        if w is None:
            log(event='NO_WAYPOINT', road=c['road'], lane=c['lane']); continue
        loc = w.transform.location
        stream_to(world, loc.x, loc.y, loc.z)
        for mode in (('motion-neutral',) if BRAKE else ('motion-auto', 'motion-neutral', 'free')):
            tr = w.transform; tr.location.z += .3
            v = world.try_spawn_actor(bp, tr)
            if v is None:
                log(event='SPAWN_FAIL', road=c['road'], lane=c['lane'], mode=mode); continue
            fwd = lambda: (lambda f, vel: vel.x * f.x + vel.y * f.y + vel.z * f.z)(v.get_transform().get_forward_vector(), v.get_velocity())
            for _ in range(20):  # settle the drop without a brake hold
                v.apply_control(carla.VehicleControl()); world.tick(120.)
            reached = None
            if mode != 'free':
                for t in range(120):
                    v.apply_control(carla.VehicleControl(throttle=.4)); world.tick(120.)
                    if fwd() >= .8:
                        reached = t; break
            release = (carla.VehicleControl(throttle=0., brake=0., hand_brake=False, manual_gear_shift=True, gear=0)
                       if mode == 'motion-neutral' else carla.VehicleControl(throttle=0., brake=0., hand_brake=False))
            back = []; p0 = v.get_location(); brake_at = None; rest = None
            for t in range(400 if BRAKE else 200):
                if BRAKE and brake_at is None and trigger(back) is not None:
                    brake_at = trigger(back) + 41  # TRIGGER + 2 s + one tick (metrics._detect_f03 due)
                ctl = release
                if BRAKE and brake_at is not None and t >= brake_at:
                    ctl = carla.VehicleControl(throttle=0., brake=.3, hand_brake=False, manual_gear_shift=True, gear=0)
                v.apply_control(ctl); world.tick(120.)
                back.append(-fwd())
                if BRAKE and brake_at is not None and t > brake_at and rest is None and all(abs(b) <= .1 for b in back[-10:]):
                    rest = t
                    break
            trig = trigger(back)
            if BRAKE:
                p1 = v.get_location()
                log(event='F03_ROLLBACK_BRAKE', town=TOWN, road=c['road'], lane=c['lane'], trigger_tick=trig,
                    brake_tick=brake_at, rest_tick=rest, stopped=rest is not None, peak_back=round(max(back), 3),
                    displacement_m=round(p0.distance(p1), 3), back_at_brake=None if brake_at is None else round(back[min(brake_at, len(back) - 1)], 3))
            mean2 = sum(back[trig:trig + 40]) / len(back[trig:trig + 40]) if trig is not None else None
            log(event='F03_ROLLBACK', town=TOWN, road=c['road'], lane=c['lane'], mode=mode,
                pitch=round(v.get_transform().rotation.pitch, 2), speed_reached_tick=reached, max_back=round(max(back), 3),
                trigger_tick=trig, mean_back_2s_after_trigger=None if mean2 is None else round(mean2, 3),
                ok=trig is not None, series=[round(back[i], 2) for i in (5, 20, 40, 80, 120, 199)])
            v.destroy(); world.tick(120.)
    st.synchronous_mode, st.fixed_delta_seconds = False, None; world.apply_settings(st)
print('F03_ROLLBACK_END')
