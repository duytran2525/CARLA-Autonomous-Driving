"""Addendum R gate NPC_EDGE (offline, read-only): replay the NPC of a sealed M scene with the pinned stock LocalPlanner's
lateral law and predict the NPC body clearance to the drivable dv1 edge for a given lookahead.
- Lateral law = agents/navigation/controller.py PIDLateralController (K_P 1.95, K_I .05, K_D .2, dt .05, 10-sample buffer),
  VehiclePIDController steer rate limit 0.1 / step and clamp 0.8; LocalPlanner target = first plan point (every 2 m on the
  NPC route) not closer than base + ratio * v[m/s] (local_planner.py 240-251).
- Vehicle: kinematic, speed = the recorded NPC speed per frame (longitudinal is not under study), yaw rate = v * c * steer
  with c fitted by least squares on the episode's own (applied steer, yaw rate) samples.
- Footprint = the recorded NPC body, clearance as in the diagnosis (min over hull vertices of the signed distance to the
  dv1 boundary). Calibration: with the stock lookahead the replay must reproduce the recorded minimum within TOL.
usage: M56_CODE=... python -I m-npc-edge-sim.py SCENE_DIR [SCENE_DIR ...]   |   --selftest"""
import math, sys
from collections import deque
from pathlib import Path

TOL = 0.30


def lateral_step(state, target, x, y, yaw):
    """One stock PID lateral step; state = (e_buffer, past_steer). Returns the applied steer."""
    buf, past = state
    vx, vy = math.cos(yaw), math.sin(yaw)
    wx, wy = target[0] - x, target[1] - y
    n = math.hypot(wx, wy)
    dot = 1. if n == 0 else math.acos(max(-1., min(1., (wx * vx + wy * vy) / n)))
    if vx * wy - vy * wx < 0:
        dot = -dot
    buf.append(dot)
    de, ie = ((buf[-1] - buf[-2]) / .05, sum(buf) * .05) if len(buf) >= 2 else (0., 0.)
    s = max(-1., min(1., 1.95 * dot + .2 * de + .05 * ie))
    s = min(s, past + .1) if s > past else max(s, past - .1)
    s = min(.8, s) if s >= 0 else max(-.8, s)
    return s


def replay(plan, x, y, yaw, speeds, c, base, ratio, k=0, lr=0.):
    """Kinematic replay; returns [(x, y, yaw)] one per speed sample. CARLA y is left-handed: steer > 0 turns right =
    yaw increases in CARLA's frame, the same sign convention as the cross product test above (applied in CARLA axes).
    k = steps between a steer command and its yaw response (fitted per episode)."""
    q, st, out, lag = deque(plan), (deque(maxlen=10), 0.), [], deque([0.] * k)
    for v in speeds:
        md = base + ratio * v
        while len(q) > 1 and math.hypot(q[0][0] - x, q[0][1] - y) < md:
            q.popleft()
        s = lateral_step(st, q[0], x, y, yaw)
        st = (st[0], s)
        lag.append(s)
        kap = c * lag.popleft()
        yaw += v * kap * .05
        b = math.atan(lr * kap)  # the pose is the body centre: its velocity leads the heading by the sideslip beta
        x += v * math.cos(yaw + b) * .05
        y += v * math.sin(yaw + b) * .05
        out.append((x, y, yaw))
    return out


def selftest():
    # straight plan along +x from the origin: no steer, no drift
    plan = [(2. * i, 0.) for i in range(1, 60)]
    p = replay(plan, 0., 0., 0., [5.] * 100, .1, 3., .5)
    assert abs(p[-1][1]) < 1e-9 and abs(p[-1][0] - 25.) < 1e-9, p[-1]
    # a 1 m lateral step: the replay converges to the new line
    plan = [(2. * i, 1.) for i in range(1, 60)]
    p = replay(plan, 0., 0., 0., [5.] * 200, .1, 3., 0.)
    assert abs(p[-1][1] - 1.) < .05, p[-1]
    print('SELFTEST_OK')


def main(dirs):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from native_v2_common import CODE  # noqa: F401
    from shapely import wkt
    from shapely.geometry import Point, Polygon
    from m56.model import decode_record, load_json
    from m56.runtime import load_episode
    from m56.geometry import world_vertices
    rows = []
    for d in map(Path, dirs):
        fx = decode_record('CompiledFixture', load_json(d / 'fixture-frozen.json'))
        area = wkt.loads((d / 'drivable-union.wkt').read_text()); edge = area.boundary
        ev = load_episode(sorted((d / 'run' / 'episodes').glob('*/*'))[0])
        fr = [(f, next(a for a in f.actors if a.role == 'NPC')) for f in ev.raw if any(a.role == 'NPC' for a in f.actors)]
        body, pose0 = fr[0][1].body, fr[0][1].pose
        # local footprint in the body frame (from frame 0)
        yaw0 = math.radians(float(pose0.yaw))
        loc = []
        for p in world_vertices(body, pose0):
            dx, dy = float(p[0]) - float(pose0.x), float(p[1]) - float(pose0.y)
            loc.append((dx * math.cos(yaw0) + dy * math.sin(yaw0), -dx * math.sin(yaw0) + dy * math.cos(yaw0)))

        def clear(x, y, yaw):
            pts = [(x + a * math.cos(yaw) - b * math.sin(yaw), y + a * math.sin(yaw) + b * math.cos(yaw)) for a, b in loc]
            return min(edge.distance(Point(p)) * (1 if area.contains(Point(p)) else -1) for p in Polygon(pts).convex_hull.exterior.coords[:-1])
        speeds = [math.hypot(float(a.velocity[0]), float(a.velocity[1])) for _, a in fr]
        yaws = [math.radians(float(a.pose.yaw)) for _, a in fr]
        steer = [float(a.commands[-1].control.steer) if a.commands and a.commands[-1].control is not None else 0. for _, a in fr]
        best = None
        for k in range(0, 21):  # least squares of yaw rate / v on the steer k steps earlier; keep the best residual
            num = den = 0.; pairs = []
            for i in range(k + 1, len(fr)):
                v = speeds[i - 1]
                if v > 1:
                    dyaw = (yaws[i] - yaws[i - 1] + math.pi) % (2 * math.pi) - math.pi
                    pairs.append((steer[i - 1 - k], dyaw / .05 / v))
            num = sum(s * r for s, r in pairs); den = sum(s * s for s, _ in pairs)
            ck = num / den if den else 0.
            res = sum((r - ck * s) ** 2 for s, r in pairs) / max(1, len(pairs))
            if best is None or res < best[0]:
                best = (res, ck, k)
        _, c, k = best
        num = den = 0.  # sideslip beta = atan2(step) - yaw ~ lr * kappa_cmd
        for i in range(1, len(fr)):
            a0, a1 = fr[i - 1][1], fr[i][1]
            dx, dy = float(a1.pose.x) - float(a0.pose.x), float(a1.pose.y) - float(a0.pose.y)
            if math.hypot(dx, dy) >= .05:
                beta = (math.atan2(dy, dx) - yaws[i - 1] + math.pi) % (2 * math.pi) - math.pi
                kap = c * steer[i - 1]; num += beta * kap; den += kap * kap
        lr = num / den if den else 0.
        tr = fx.routes['NPC'].transforms
        pts, last = [], None
        for t in tr:
            if last is None or math.hypot(float(t.x) - last[0], float(t.y) - last[1]) >= 2:
                last = (float(t.x), float(t.y)); pts.append(last)
        st = next(i for i, p in enumerate(pts) if math.hypot(p[0] - float(pose0.x), p[1] - float(pose0.y)) >= 2)
        plan = pts[st:]
        actual = min(clear(float(a.pose.x), float(a.pose.y), math.radians(float(a.pose.yaw))) for _, a in fr)
        res = {}
        for name, base, ratio in (('stock', 3., .5), ('r3m', 3., 0.)):
            path = replay(plan, float(pose0.x), float(pose0.y), yaw0, speeds, c, base, ratio, k, lr)
            res[name] = min(clear(*p) for p in path)
        ok_cal = abs(res['stock'] - actual) <= TOL
        rows.append((d.name, round(c, 4), k, round(actual, 3), round(res['stock'], 3), round(res['r3m'], 3), ok_cal))
        print(f"{d.name}: c={c:.4f} k={k} lr={lr:.2f} actual={actual:.3f} replay_stock={res['stock']:.3f} replay_3m={res['r3m']:.3f} "
              f"calibrated={ok_cal} NPC_EDGE={'PASS' if ok_cal and res['r3m'] - TOL >= .15 else 'FAIL'}", flush=True)
    return rows


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest(); sys.exit(0)
    main(sys.argv[1:])
