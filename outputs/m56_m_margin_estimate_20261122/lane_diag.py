"""Where along the scored line is the ideal-tracking minimum? Town12 sites, lane-quad union (offline)."""
import importlib.util, json, math, sys
from pathlib import Path
SDD = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/.superpowers/sdd/2026-10-07-m56-catalog-and-validation')
sys.path.insert(0, str(SDD))
s = importlib.util.spec_from_file_location('feas', SDD / 'native-m-dv1-feasibility.py'); F = importlib.util.module_from_spec(s); s.loader.exec_module(F)
import carla
from shapely.geometry import LineString, Point
from shapely.prepared import prep
d = Path(sys.argv[1]); town = sys.argv[2]
rows = [json.loads(l) for l in (d / 'lanequad' / 'lanequad.jsonl').read_text(encoding='utf-8').splitlines()]
rows = [r for r in rows if r['town'] == town]
cen = F._mod('cen', 'asel2-census.py'); cen.load(town)
m = carla.Map(town, cen.xodr(town).read_text(encoding='utf-8'))
lt = (carla.LaneType.Driving, carla.LaneType.Shoulder)
grid = {}
for w in m.generate_waypoints(.5):
    if w.lane_type in lt:
        grid.setdefault((int(w.transform.location.x // 50), int(w.transform.location.y // 50)), []).append(w)
from collections import Counter
where = Counter(); conn_ideal = []
for r in rows:
    con, tl = r['connecting'], r['to']
    path, _ = F.S.connector_path(cen.lane_centre, cen.v2.trees[town][1][con], tl)
    rast = [(x, -y) for x, y in F.sub(path, F.EXT_RAST)]
    cx, cy = sum(p[0] for p in rast) / len(rast), sum(p[1] for p in rast) / len(rast)
    rad = max(math.dist(p, (cx, cy)) for p in rast) + 10.
    local = [w for i in range(int((cx - rad) // 50), int((cx + rad) // 50) + 1)
             for j in range(int((cy - rad) // 50), int((cy + rad) // 50) + 1) for w in grid.get((i, j), ())]
    lanes = F.lane_union(local, (cx, cy), rad)
    sl = LineString([(x, -y) for x, y in F.sub(path, F.EXT_SCORE)]); L = sl.length
    conn = LineString([(x, -y) for x, y in F.sub(path, 0.)])
    pa, edge = prep(lanes), lanes.boundary
    worst = (math.inf, None); wc = math.inf
    for x, y, yaw in F.mirror(F.ideal_poses(path)):
        sp = sl.project(Point(x, y))
        if not (0 < sp < L):
            continue
        for c in F.corners(x, y, yaw):
            p = Point(c); dd = edge.distance(p); v = dd if pa.contains(p) else -dd
            if v < worst[0]:
                worst = (v, sp)
            if 12. < sp < L - 12.:
                wc = min(wc, v)
    zone = 'ext_in' if worst[1] <= 12. else ('ext_out' if worst[1] >= L - 12. else 'connector')
    where[zone] += 1; conn_ideal.append(wc)
    if r['ideal'] < 0 and len([1 for z in where.values()]) and where[zone] <= 3:
        print(json.dumps({'site': f'{con}/{tl}', 'ideal': r['ideal'], 'min_at_s': round(worst[1], 1), 'L': round(L, 1), 'zone': zone,
                          'connector_only_ideal': round(wc, 3)}), flush=True)
print('WHERE', dict(where), 'connector-only ideal >= 0.45:', sum(v >= .45 for v in conn_ideal), 'of', len(conn_ideal),
      'min', round(min(conn_ideal), 3), flush=True)
