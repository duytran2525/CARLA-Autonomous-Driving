"""Addendum S gate NPC_EDGE_SITE (offline, OpenDRIVE only): replay the M NPC through its junction connector with the pinned
stock LocalPlanner lateral law (m-npc-edge-sim.py: lateral_step / replay) and predict how far the NPC body leaves its lane.
- Path = connector lane centre (asel2-census.lane_centre, 0.5 m), oriented in travel direction (contact 'end' = decreasing
  s), with 30 m straight extensions along the entry / exit headings (shortcut: assumes the incoming / outgoing roads are
  straight for 30 m at the junction; B5 already requires axis-aligned approaches).
- Plan = path points every 2 m (as policy_maker plan_rows); lookahead base 2 m, ratio 0 (addendum R value) unless given.
- Vehicle: speed = nominal vN, kappa = C * steer, sideslip beta = atan(LR * kappa): C, LR = the mean fit over the five
  sealed turning M episodes (addendum R: c 0.39-0.43, lr 1.26-1.29). Footprint = the M NPC body (2*HL x 2*HW).
- Margin m = min over steps and body corners of (lane half width - |signed distance of the corner to the path|).
  PASS iff m >= MARGIN (0.45 m = addendum R gate 0.15 + replay calibration TOL 0.30).
python -I m-site-edge-gate.py --selftest | TOWN ROUTE VN   (ROUTE as in route_recipe, e.g. 529/-1→18980/-1→321/+2)"""
import importlib.util, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
C, LR, HL, HW, MARGIN = 0.414, 1.27, 2.45, 1.06, 0.45


def _mod(name, file):
    s = importlib.util.spec_from_file_location(name, HERE / file); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


SIM = _mod('npcsim', 'm-npc-edge-sim.py')


def seg_dist(p, a, b):
    """Signed distance of p to segment ab (left of travel > 0) and the clamped parameter."""
    dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
    t = 0. if L2 == 0 else max(0., min(1., ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    qx, qy = a[0] + t * dx, a[1] + t * dy
    d = math.hypot(p[0] - qx, p[1] - qy)
    return (d if dx * (p[1] - a[1]) - dy * (p[0] - a[0]) >= 0 else -d), t


def lateral(p, path):
    return min((seg_dist(p, a, b)[0] for a, b in zip(path, path[1:])), key=abs)


def extend(pts, ext=30.):
    (x0, y0), (x1, y1) = pts[0], pts[1]; h0 = math.atan2(y1 - y0, x1 - x0)
    (xa, ya), (xb, yb) = pts[-2], pts[-1]; h1 = math.atan2(yb - ya, xb - xa)
    pre = [(x0 - ext * (1 - i / 60) * math.cos(h0), y0 - ext * (1 - i / 60) * math.sin(h0)) for i in range(60)]
    post = [(xb + ext * i / 60 * math.cos(h1), yb + ext * i / 60 * math.sin(h1)) for i in range(1, 61)]
    return pre + list(pts) + post


def margin(path, half_width, vN, base=2., ratio=0.):
    plan, last = [], None
    for p in path:
        if last is None or math.hypot(p[0] - last[0], p[1] - last[1]) >= 2:
            last = p; plan.append(p)
    x, y = path[0]; h = math.atan2(path[1][1] - y, path[1][0] - x)
    steps = int(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])) / (float(vN) * .05))
    out = SIM.replay(plan[1:], x, y, h, [float(vN)] * max(steps, 1), C, base, ratio, 0, LR)
    worst = math.inf
    skip = int((HL + 1) / (float(vN) * .05)) + 1  # body corners behind the path start are not lateral offsets
    for px, py, yaw in out[skip:-skip:2]:
        for a, b in ((HL, HW), (HL, -HW), (-HL, HW), (-HL, -HW)):
            cx, cy = px + a * math.cos(yaw) - b * math.sin(yaw), py + a * math.sin(yaw) + b * math.cos(yaw)
            worst = min(worst, half_width - abs(lateral((cx, cy), path)))
    return worst


def connector_path(lane_centre, road, tl):
    pts = [(p[0], p[1]) for p in lane_centre(road, tl)]
    # travel direction: right lanes (id < 0) follow +s in OpenDRIVE
    if tl > 0:
        pts.reverse()
    sec = road.find('lanes').findall('laneSection')[0]
    lane = next(l for side in ('left', 'right') if sec.find(side) is not None for l in sec.find(side).findall('lane')
                if int(l.get('id')) == tl)
    w = float(lane.find('width').get('a'))
    return extend(pts), w / 2


def gate_road(lane_centre, road, tl, vN):
    """For the generator: (margin, pass) of connector `road` lane `tl` at speed vN."""
    path, hw = connector_path(lane_centre, road, tl)
    m = margin(path, hw, vN)
    return m, m >= MARGIN


def gate(town, route, vN):
    cen = _mod('cen', 'asel2-census.py')
    cen.load(town)
    (con, tl) = [(int(a), int(b)) for a, b in (s.split('/') for s in route.split('→'))][1]
    return gate_road(cen.lane_centre, cen.v2.trees[town][1][con], tl, vN)


def selftest():
    straight = [(float(i), 0.) for i in range(0, 80)]
    m = margin(straight, 1.75, 3.)
    assert abs(m - (1.75 - HW)) < .02, m  # no turn: the body stays centred
    r = 8.  # a 90 deg right turn of radius 8 m must cut deeper than one of radius 30 m
    arc = lambda R: extend([(R * math.sin(t / 50 * math.pi / 2), R - R * math.cos(t / 50 * math.pi / 2)) for t in range(51)])
    assert margin(arc(r), 1.75, 4.) < margin(arc(30.), 1.75, 4.), (margin(arc(r), 1.75, 4.), margin(arc(30.), 1.75, 4.))
    print('SELFTEST_OK')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest(); sys.exit(0)
    m, ok = gate(sys.argv[1], sys.argv[2], float(sys.argv[3]))
    print(f'{sys.argv[1]} {sys.argv[2]} vN={sys.argv[3]} margin={m:.3f} {"PASS" if ok else "FAIL"}')
