"""M56 M-group feasibility check (Duy [chat] 22/11/2026 "Kiểm khả thi M trước"). Report-only: NOT a gate, no A/B, no P5.
For every M candidate site of lap 1 (outputs/m56_m_margin_estimate_20261122/margins.json: town, connector road, lane, vN)
build the dv1 drivable area around the NPC connector on our own CARLA (2610) and replay the stock NPC exactly as the
addendum S gate does (m-site-edge-gate.py: connector path + 30 m extensions, stock PID, lookahead 2 m, C 0.414, LR 1.27,
body 4.90 x 2.12 m). Margin = min signed distance of the body corners to the dv1 edge; a key (site, vN) PASSes iff
margin >= 0.45 m (0.15 contact proof + 0.30 replay TOL, addendum R/S).
dv1 = the native_v2_common.drivable_union construction (Driving|Shoulder lane quads every 0.5 m, 0.25 m closing, plus the
Roads|RoadLines cast_ray raster on 0.25 m cells eroded 0.125 m), on a 4 m corridor around the connector path +16 m each
side; poses are scored on the connector only (EXT_SCORE). Cells deeper than 0.5 m inside the lane union are not cast (they
are in dv1 anyway). A scene's real dv1 also covers 12 m around the EGO route, so this margin is a lower bound.
--validate N: the first N sites of the town are also built with native_v2_common.drivable_union itself (the exact
function, 12 m corridor around the same path) and both margins are printed.
--min-lane X: only sites whose offline lane-quad stock margin (LANEQ, a lower bound of dv1) is >= X.
--skip-done: skip sites already in an outputs/m56_m_dv1_feasibility_TOWN_*.jsonl (resume in chunks with --limit).
  python -I -X utf8 native-m-dv1-feasibility.py TOWN [--validate N] [--limit K] [--min-lane X] [--skip-done]   |   --selftest"""
import importlib.util, json, math, os, sys, time
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault('M56_RECIPE', 'v6'); os.environ.setdefault('M56_DRIVABLE', 'dv1')  # before native_v2_common import
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # python -I does not put the script dir on sys.path (native_v2_common)
OUT =HERE.parents[2] / 'outputs'
EST = OUT / 'm56_m_margin_estimate_20261122' / 'margins.json'
LANEQ = OUT / 'm56_m_margin_estimate_20261122' / 'lanequad_connector.jsonl'  # offline lane-quad lower bound per site
# EXT_SCORE 0: poses are scored on the connector only. The gate's 30 m straight extensions are a shortcut (incoming /
# outgoing roads assumed straight); against real lanes they put the ideal path off the lane on curved approaches (offline
# 22/11: 100 of 132 Town12 sites had their ideal-tracking minimum in the +-12 m extensions). They still drive the replay.
MARGIN, CORR, CELL, EXT_RAST, EXT_SCORE = .45, 4., .25, 16., 0.


def _mod(name, file):
    s = importlib.util.spec_from_file_location(name, HERE / file); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


S = _mod('sgate', 'm-site-edge-gate.py')


def corners(px, py, yaw):
    return [(px + a * math.cos(yaw) - b * math.sin(yaw), py + a * math.sin(yaw) + b * math.cos(yaw))
            for a, b in ((S.HL, S.HW), (S.HL, -S.HW), (-S.HL, S.HW), (-S.HL, -S.HW))]


def stock_poses(path, vN):
    """The poses m-site-edge-gate.margin scores (same plan, replay and end skip)."""
    plan, last = [], None
    for p in path:
        if last is None or math.hypot(p[0] - last[0], p[1] - last[1]) >= 2:
            last = p; plan.append(p)
    x, y = path[0]; h = math.atan2(path[1][1] - y, path[1][0] - x)
    steps = int(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])) / (vN * .05))
    out = S.SIM.replay(plan[1:], x, y, h, [vN] * max(steps, 1), S.C, 2., 0., 0, S.LR)
    skip = int((S.HL + 1) / (vN * .05)) + 1
    return out[skip:-skip:2]


def ideal_poses(path):
    return [(a[0], a[1], math.atan2(b[1] - a[1], b[0] - a[0])) for a, b in zip(path, path[1:])]


def mirror(poses):
    """OpenDRIVE (right-handed) -> CARLA (y flipped): distances are unchanged."""
    return [(x, -y, -yaw) for x, y, yaw in poses]


def sub(path, ext):
    """Connector part of an m-site-edge-gate path (60 points of 0.5 m before and after) plus `ext` m each side."""
    n = 60 - int(ext / .5)
    return path[n:len(path) - n]


def score(poses, area, score_line):
    """Min signed corner distance to the edge of `area` over the poses whose centre projects inside `score_line`."""
    from shapely.geometry import Point
    from shapely.prepared import prep
    pa, edge, L = prep(area), area.boundary, score_line.length
    worst = math.inf
    for x, y, yaw in poses:
        s = score_line.project(Point(x, y))
        if not (0. < s < L):
            continue
        for c in corners(x, y, yaw):
            p = Point(c); d = edge.distance(p)
            worst = min(worst, d if pa.contains(p) else -d)
    return worst


def lane_union(wps, center, radius):
    """native_v2_common.drivable_union lane part (v6 closing), from cached Driving|Shoulder waypoints."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    quads = []
    for w in wps:
        loc = w.transform.location
        if math.dist((loc.x, loc.y), center) > radius:
            continue
        for n in w.next(.5)[:1]:
            pts = []
            for p, side in ((w, 1), (n, 1), (n, -1), (w, -1)):
                t = p.transform; yaw = math.radians(t.rotation.yaw); h = p.lane_width / 2
                pts.append((t.location.x - side * h * math.sin(yaw), t.location.y + side * h * math.cos(yaw)))
            q = Polygon(pts)
            if q.is_valid and q.area > 0:
                quads.append(q)
    return unary_union(quads).buffer(0).buffer(.25).buffer(-.25)


def raster(world, line, zs, lanes):
    """Roads|RoadLines cast_ray cells on a CELL grid inside CORR of `line`, skipping cells > 0.5 m inside `lanes`."""
    import carla, numpy as np, shapely
    from shapely.geometry import box
    from shapely.ops import unary_union
    corr = line.buffer(CORR); deep = lanes.buffer(-.5)
    x0, y0, x1, y1 = corr.bounds
    ni, nj = int((x1 - x0) / CELL) + 1, int((y1 - y0) / CELL) + 1
    gx = np.repeat(x0 + CELL * np.arange(ni, dtype=np.float64), nj); gy = np.tile(y0 + CELL * np.arange(nj, dtype=np.float64), ni)
    keep = shapely.contains_xy(corr, gx, gy) & ~shapely.contains_xy(deep, gx, gy)
    cells, rays = [], 0
    for x, y in zip(gx[keep], gy[keep]):
        z = zs(x, y); rays += 1
        hits = world.cast_ray(carla.Location(float(x), float(y), z + 3.), carla.Location(float(x), float(y), z - 3.))
        if hits and str(hits[0].label) in ('Roads', 'RoadLines'):
            cells.append(box(x - CELL / 2, y - CELL / 2, x + CELL / 2, y + CELL / 2))
    paved = unary_union(cells).buffer(-CELL / 2) if cells else None
    return paved, rays


def selftest():
    from shapely.geometry import LineString, box
    path = [(-30. + .5 * i, 0.) for i in range(60)] + [(.5 * i, 0.) for i in range(81)] + [(40.5 + .5 * i, 0.) for i in range(60)]
    area = box(-50., -1.75, 100., 1.75)  # a 3.5 m straight lane, body centred: margin = 1.75 - HW
    m = score(ideal_poses(path), area, LineString(sub(path, EXT_SCORE)))
    assert abs(m - (1.75 - S.HW)) < 1e-6, m
    assert abs(score(mirror(ideal_poses(path)), box(-50., -1.75, 100., 1.75), LineString([(x, -y) for x, y in sub(path, EXT_SCORE)]))
               - (1.75 - S.HW)) < 1e-6
    assert len(sub(path, 12.)) == len(path) - 2 * (60 - 24)
    sp = stock_poses(path, 3.)
    assert abs(score(sp, area, LineString(sub(path, EXT_SCORE))) - (1.75 - S.HW)) < .02
    print('DV1_FEASIBILITY SELFTEST_OK')


def main(town, validate=0, limit=None, min_lane=None, skip_done=False):
    import carla
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    from native_v2_common import own_server, load, drivable_union, now
    cen = _mod('cen', 'asel2-census.py'); cen.load(town)
    roads = cen.v2.trees[town][1]
    rows = [r for r in json.loads(EST.read_text(encoding='utf-8')) if r['town'] == town]
    sites = {}
    for r in rows:
        sites.setdefault((r['connecting'], r['to']), []).append(float(r['vN']))
    if min_lane is not None:  # Duy [chat] 22/11: only sites whose offline lane-quad stock margin (lower bound) >= min_lane
        lq = [json.loads(l) for l in LANEQ.read_text(encoding='utf-8').splitlines() if l.strip()]
        ok = {(r['connecting'], r['to']) for r in lq if r['town'] == town and r['best_stock'] >= min_lane}
        sites = {k: v for k, v in sites.items() if k in ok}
    if skip_done:  # 23/11: resume in chunks (Town13 server memory grew ~1.5 GB/min across sites); skip sites already scored
        done = {(r['connecting'], r['to']) for p in OUT.glob(f'm56_m_dv1_feasibility_{town}_*.jsonl')
                for r in map(json.loads, p.read_text(encoding='utf-8').splitlines()) if r}
        sites = {k: v for k, v in sites.items() if k not in done}
    mid = {}
    for k in sites:
        p = S.connector_path(cen.lane_centre, roads[k[0]], k[1])[0]; mid[k] = p[len(p) // 2]
    # 500 m cells, then x: neighbouring sites share streamed tiles (order only; every site is scored the same way)
    keys = sorted(sites, key=lambda k: (int(mid[k][0] // 500), int(mid[k][1] // 500), mid[k][0]))[:limit]
    if not keys:
        print(json.dumps({'event': 'TOWN_DONE', 'town': town, 'sites': 0, 'note': 'nothing left'}), flush=True); return
    out = OUT / f'm56_m_dv1_feasibility_{town}_{now()}.jsonl'
    log = lambda **k: print(json.dumps(k, default=str), flush=True)
    t0 = time.time(); n_pass = n_keys = 0; site_pass = set()
    with own_server(log) as (client, proc, start), open(out, 'x', encoding='utf-8') as f:
        world = load(client, town); m = world.get_map()
        s = world.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = True, .05; world.apply_settings(s); world.tick(120.)
        lt = (carla.LaneType.Driving, carla.LaneType.Shoulder)
        geo = {}
        for con, tl in keys:
            path, _ = S.connector_path(cen.lane_centre, roads[con], tl)
            geo[(con, tl)] = path
        allpts = [(x, -y) for p in geo.values() for x, y in sub(p, EXT_RAST)]
        hub = unary_union([Point(p).buffer(1.) for p in allpts[::8]]).buffer(80.)
        from shapely.prepared import prep
        ph = prep(hub)
        wps = [w for w in m.generate_waypoints(.5) if w.lane_type in lt
               and ph.contains(Point(w.transform.location.x, w.transform.location.y))]
        grid = {}  # 50 m buckets: lane_union only scans the buckets that touch a site's radius
        for w in wps:
            grid.setdefault((int(w.transform.location.x // 50), int(w.transform.location.y // 50)), []).append(w)
        near = lambda c, r: [w for i in range(int((c[0] - r) // 50), int((c[0] + r) // 50) + 1)
                             for j in range(int((c[1] - r) // 50), int((c[1] + r) // 50) + 1) for w in grid.get((i, j), ())]
        log(event='WAYPOINTS', town=town, kept=len(wps), sites=len(keys), secs=round(time.time() - t0))
        for i, (con, tl) in enumerate(keys):
            ts = time.time()
            path = geo[(con, tl)]
            rast = [(x, -y) for x, y in sub(path, EXT_RAST)]
            line, score_line = LineString(rast), LineString([(x, -y) for x, y in sub(path, EXT_SCORE)])
            zpts = []
            for x, y in rast[::4]:
                w = m.get_waypoint(carla.Location(x, y, 0.), project_to_road=True, lane_type=carla.LaneType.Driving)
                zpts.append((x, y, w.transform.location.z if w else 0.))
            zs = lambda x, y: min(zpts, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)[2]
            cx, cy = sum(p[0] for p in rast) / len(rast), sum(p[1] for p in rast) / len(rast)
            world.get_spectator().set_transform(carla.Transform(carla.Location(cx, cy, zs(cx, cy) + 50.), carla.Rotation(pitch=-90.)))
            for _ in range(20):
                world.tick(120.)
            radius = max(math.dist(p, (cx, cy)) for p in rast) + 10.
            local = near((cx, cy), radius)
            lanes = lane_union(local, (cx, cy), radius)
            paved, rays = raster(world, line, zs, lanes)
            dv1 = unary_union([lanes, paved]).buffer(0) if paved is not None else lanes
            row = {'town': town, 'connecting': con, 'to': tl, 'rays': rays, 'secs': None,
                   'ideal_dv1': round(score(mirror(ideal_poses(path)), dv1, score_line), 3), 'keys': []}
            exact = None
            if i < validate:
                route = SimpleNamespace(transforms=[SimpleNamespace(x=x, y=y, z=zs(x, y)) for x, y in rast])
                proxy = SimpleNamespace(generate_waypoints=lambda d: local)  # the function filters by radius itself
                exact = drivable_union(proxy, (cx, cy), radius, world, {'NPC': route})
                row['ideal_exact'] = round(score(mirror(ideal_poses(path)), exact, score_line), 3)
            for vN in sorted(set(sites[(con, tl)])):
                poses = mirror(stock_poses(path, vN))
                k = {'vN': vN, 'stock_dv1': round(score(poses, dv1, score_line), 3)}
                if exact is not None:
                    k['stock_exact'] = round(score(poses, exact, score_line), 3)
                k['pass'] = k['stock_dv1'] >= MARGIN
                n_keys += 1; n_pass += k['pass']
                if k['pass']:
                    site_pass.add((con, tl))
                row['keys'].append(k)
            row['secs'] = round(time.time() - ts, 1)
            f.write(json.dumps(row) + '\n'); f.flush()
            log(event='SITE', i=i, **{k: v for k, v in row.items() if k != 'keys'},
                best=max(k['stock_dv1'] for k in row['keys']), passes=sum(k['pass'] for k in row['keys']))
        log(event='TOWN_DONE', town=town, sites=len(keys), keys=n_keys, keys_pass=n_pass, sites_pass=len(site_pass),
            out=str(out), secs=round(time.time() - t0))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a == ['--selftest']:
        selftest(); sys.exit(0)
    v = int(a[a.index('--validate') + 1]) if '--validate' in a else 0
    lim = int(a[a.index('--limit') + 1]) if '--limit' in a else None
    ml = float(a[a.index('--min-lane') + 1]) if '--min-lane' in a else None
    main(a[0], v, lim, ml, '--skip-done' in a)
