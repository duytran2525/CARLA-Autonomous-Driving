"""2026-11-09 F03 capability probe (observe-only, no scene, no A/B): does vehicle.audi.a2 roll back on a real grade?
Sites: the fill-v4 R3 grade pool (|slope| >= 0.05 over >= 40 m, line/arc). For the first N sites of TOWN: spawn on the
uphill-travel lane at the middle of the grade run with the waypoint pitch (A-SEL2 addendum 6), stream the spectator,
hold brake 1 for 2 s, then neutral (manual gear 0), no brake, no handbrake, for 10 s. Report the backward speed series
and whether it reaches >= 0.20 m/s for >= 0.25 s (spec 8.1 F03 trigger), plus the realised mean backward speed over the
first 2 s after the trigger (the F03 vN_char of the F prereg draft).
usage: python -I native-f03-grade-probe.py TOWN [N=3]"""
import importlib.util, json, math, sys
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from native_v2_common import own_server, load, stream_to

log = lambda **k: print(json.dumps(k, default=str), flush=True)
TOWN = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 3
s = importlib.util.spec_from_file_location('gen', here / 'fill20-generate.py'); gen = importlib.util.module_from_spec(s); s.loader.exec_module(gen)
import xodr_routes as xr
gen.ROOT = xr.xodr_path(TOWN).parent
gen.USED_JUNCTIONS[TOWN] = set(); gen.USED_ANCHORS[TOWN] = []
_, _, r3 = gen.scan(TOWN)
r3 = sorted(r3, key=lambda c: -(c['grade_run'][1] - c['grade_run'][0]))[:N]
with own_server(log) as (client, proc, start):
    import carla
    world = load(client, TOWN); m = world.get_map()
    st = world.get_settings(); st.synchronous_mode, st.fixed_delta_seconds = True, .05; world.apply_settings(st)
    bp = world.get_blueprint_library().find('vehicle.audi.a2')
    for c in r3:
        s0, s1, direction = c['grade_run']
        w = m.get_waypoint_xodr(c['road'], c['lane'], (s0 + s1) / 2)
        if w is None:
            log(event='NO_WAYPOINT', site=c['xpath']); continue
        loc = w.transform.location
        stream_to(world, loc.x, loc.y, loc.z)
        tr = w.transform; tr.location.z += .3
        v = world.try_spawn_actor(bp, tr)
        if v is None:
            log(event='SPAWN_FAIL', road=c['road'], lane=c['lane']); continue
        for _ in range(40):
            v.apply_control(carla.VehicleControl(brake=1.)); world.tick(120.)
        back = []
        for _ in range(200):
            v.apply_control(carla.VehicleControl(throttle=0., brake=0., hand_brake=False, manual_gear_shift=True, gear=0))
            world.tick(120.)
            f = v.get_transform().get_forward_vector(); vel = v.get_velocity()
            back.append(-(vel.x * f.x + vel.y * f.y + vel.z * f.z))
        run = best = 0; trig = None
        for i, b in enumerate(back):
            run = run + 1 if b >= .2 else 0
            if run > best:
                best = run
            if run == 6 and trig is None:
                trig = i
        mean2 = sum(back[trig:trig + 40]) / len(back[trig:trig + 40]) if trig is not None else None
        log(event='F03_GRADE', town=TOWN, road=c['road'], lane=c['lane'], grade_run=[round(s0, 1), round(s1, 1)],
            pitch=round(v.get_transform().rotation.pitch, 2), max_back=round(max(back), 3), trigger_tick=trig,
            mean_back_2s_after_trigger=None if mean2 is None else round(mean2, 3), ok=trig is not None,
            series=[round(back[i], 2) for i in (5, 20, 40, 80, 199)])
        v.destroy(); world.tick(120.)
    st.synchronous_mode, st.fixed_delta_seconds = False, None; world.apply_settings(st)
print('F03_PROBE_END')
