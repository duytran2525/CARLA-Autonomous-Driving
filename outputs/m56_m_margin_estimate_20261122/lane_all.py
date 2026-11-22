"""Offline lane-quad margins (the lane part of dv1 = native_v2_common.drivable_union quads + 0.25 closing) for every M site
of lap 1, via native-m-dv1-feasibility.py's own functions on an offline carla.Map. No server. Aborts if CarlaUE4 starts
(memory). Output: OUTDIR/lanequad.jsonl + summary."""
import importlib.util, json, math, subprocess, sys, time
from pathlib import Path
SDD = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/.superpowers/sdd/2026-10-07-m56-catalog-and-validation')
sys.path.insert(0, str(SDD))
s = importlib.util.spec_from_file_location('feas', SDD / 'native-m-dv1-feasibility.py'); F = importlib.util.module_from_spec(s); s.loader.exec_module(F)
import carla
from shapely.geometry import LineString
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
carla_up = lambda: 'CarlaUE4' in subprocess.run(['tasklist', '/FI', 'IMAGENAME eq CarlaUE4*'], capture_output=True, text=True).stdout
est = json.loads(F.EST.read_text(encoding='utf-8'))
cen = F._mod('cen', 'asel2-census.py')
lt = (carla.LaneType.Driving, carla.LaneType.Shoulder)
rows = []
with open(out / 'lanequad.jsonl', 'w', encoding='utf-8') as f:
    for town in ('Town05', 'Town12', 'Town13'):
        if carla_up():
            print('ABORT CarlaUE4 running', flush=True); sys.exit(3)
        t0 = time.time(); cen.load(town)
        m = carla.Map(town, cen.xodr(town).read_text(encoding='utf-8'))
        sites = {}
        for r in est:
            if r['town'] == town:
                sites.setdefault((r['connecting'], r['to']), []).append(float(r['vN']))
        grid = {}
        for w in m.generate_waypoints(.5):
            if w.lane_type in lt:
                grid.setdefault((int(w.transform.location.x // 50), int(w.transform.location.y // 50)), []).append(w)
        print(f'{town}: map + waypoints {time.time() - t0:.0f}s, {len(sites)} sites', flush=True)
        for n, (con, tl) in enumerate(sorted(sites)):
            if n % 20 == 0 and carla_up():
                print('ABORT CarlaUE4 running', flush=True); sys.exit(3)
            path, _ = F.S.connector_path(cen.lane_centre, cen.v2.trees[town][1][con], tl)
            rast = [(x, -y) for x, y in F.sub(path, F.EXT_RAST)]
            cx, cy = sum(p[0] for p in rast) / len(rast), sum(p[1] for p in rast) / len(rast)
            rad = max(math.dist(p, (cx, cy)) for p in rast) + 10.
            local = [w for i in range(int((cx - rad) // 50), int((cx + rad) // 50) + 1)
                     for j in range(int((cy - rad) // 50), int((cy + rad) // 50) + 1) for w in grid.get((i, j), ())]
            lanes = F.lane_union(local, (cx, cy), rad)
            sl = LineString([(x, -y) for x, y in F.sub(path, F.EXT_SCORE)])
            r = {'town': town, 'connecting': con, 'to': tl, 'ideal': round(F.score(F.mirror(F.ideal_poses(path)), lanes, sl), 3),
                 'stock': {str(v): round(F.score(F.mirror(F.stock_poses(path, v)), lanes, sl), 3) for v in sorted(set(sites[(con, tl)]))}}
            r['best_stock'] = max(r['stock'].values())
            rows.append(r); f.write(json.dumps(r) + '\n'); f.flush()
        del m, grid
summ = {'sites': len(rows), 'stock_sites_ge_0.45': sum(r['best_stock'] >= .45 for r in rows),
        'stock_sites_ge_0.30': sum(r['best_stock'] >= .30 for r in rows), 'ideal_sites_ge_0.45': sum(r['ideal'] >= .45 for r in rows),
        'best_stock_max': max(r['best_stock'] for r in rows),
        'by_town': {t: {'sites': sum(r['town'] == t for r in rows), 'stock_ge_0.45': sum(r['town'] == t and r['best_stock'] >= .45 for r in rows)}
                    for t in ('Town05', 'Town12', 'Town13')}}
(out / 'summary.json').write_text(json.dumps(summ, indent=1), encoding='utf-8')
print('SUMMARY', json.dumps(summ), flush=True)
