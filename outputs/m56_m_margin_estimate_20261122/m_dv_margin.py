"""Offline estimate for an M-group proposal (22/11/2026; NOT a registered gate, no rule changes).
Runs the lap-1 generator (fill-v4-generate.py, state 10) and, for every M candidate it sends to S_NPC_EDGE, records four
body margins of the M NPC on its connector (path = m-site-edge-gate.connector_path, body 4.90 x 2.12 m):
  lane_stock  = addendum S gate: own-lane half width - |corner offset|, stock PID replay, lookahead 2 m (must match lap 1)
  area_stock  = same replay, signed distance of the corners to the edge of the Driving|Shoulder lane area of an offline
                carla.Map (the lane part of dv1; dv1 also adds the paved raster, so this is a lower bound of dv1)
  lane_ideal / area_ideal = ideal tracking (body centre on the lane centre, heading = tangent): the best any NPC
                controller can do
npc_edge returns False (as every M candidate did in lap 1), so the generator output is lap 1 again (scratchpad only).
  python -I -X utf8 m_dv_margin.py OUTDIR"""
import importlib.util, json, math, sys, time
from pathlib import Path

SDD = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/.superpowers/sdd/2026-10-07-m56-catalog-and-validation')
OUTS = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs')
sys.path.insert(0, str(SDD))


def mod(name, file):
    s = importlib.util.spec_from_file_location(name, SDD / file); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


G = mod('fv4', 'fill-v4-generate.py')
S = mod('sgate', 'm-site-edge-gate.py')
SEEN = {}


def record(x, vN):
    key = (x['town'], x['npc']['connecting'], x['npc']['to'], float(vN))
    SEEN.setdefault(key, {k: v for k, v in x['npc'].items() if isinstance(v, (int, float, str))})
    return False


def corners(px, py, yaw):
    return [(px + a * math.cos(yaw) - b * math.sin(yaw), py + a * math.sin(yaw) + b * math.cos(yaw))
            for a, b in ((S.HL, S.HW), (S.HL, -S.HW), (-S.HL, S.HW), (-S.HL, -S.HW))]


def stock_poses(path, vN, base=2., ratio=0.):  # = m-site-edge-gate.margin, returning the poses it scores
    plan, last = [], None
    for p in path:
        if last is None or math.hypot(p[0] - last[0], p[1] - last[1]) >= 2:
            last = p; plan.append(p)
    x, y = path[0]; h = math.atan2(path[1][1] - y, path[1][0] - x)
    steps = int(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])) / (vN * .05))
    out = S.SIM.replay(plan[1:], x, y, h, [vN] * max(steps, 1), S.C, base, ratio, 0, S.LR)
    skip = int((S.HL + 1) / (vN * .05)) + 1
    return out[skip:-skip:2]


def ideal_poses(path):
    skip = int((S.HL + 1) / .5) + 1
    return [(a[0], a[1], math.atan2(b[1] - a[1], b[0] - a[0])) for a, b in zip(path, path[1:])][skip:-skip]


def main(outdir):
    import carla
    from shapely.geometry import LineString, Point, box
    from shapely.ops import unary_union
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    G.npc_edge = record
    t0 = time.time()
    G.main(str(outdir / 'replace10_rerun.json'), 'offline-estimate-22-11', str(OUTS / 'm56_asel2_replace_state_10_1.json'))
    print(f'generator done {time.time() - t0:.0f}s, {len(SEEN)} M keys', flush=True)
    lt = carla.LaneType.Driving | carla.LaneType.Shoulder
    rows = []
    for town in sorted({k[0] for k in SEEN}):
        m = carla.Map(town, G.cen.xodr(town).read_text(encoding='utf-8'))
        print(f'{town}: map built {time.time() - t0:.0f}s', flush=True)
        for key in sorted(k for k in SEEN if k[0] == town):
            _, con, tl, vN = key
            road = G.v2.trees[town][1][con]
            path, hw = S.connector_path(G.cen.lane_centre, road, tl)
            z = sum(p[2] for p in G.cen.lane_centre(road, tl)) / max(1, len(G.cen.lane_centre(road, tl)))
            # lane area raster (0.25 m cells inside 6 m of the path), OpenDRIVE y -> CARLA -y, eroded by half a cell
            corr = LineString(path).buffer(6.)
            x0, y0, x1, y1 = corr.bounds
            cells, hit_con = [], 0
            nx, ny = int((x1 - x0) / .25) + 1, int((y1 - y0) / .25) + 1
            from shapely.prepared import prep
            pc = prep(corr)
            for i in range(nx):
                for j in range(ny):
                    cx, cy = x0 + (i + .5) * .25, y0 + (j + .5) * .25
                    if not pc.contains(Point(cx, cy)):
                        continue
                    w = m.get_waypoint(carla.Location(cx, -cy, z), project_to_road=False, lane_type=lt)
                    if w is not None:
                        cells.append(box(cx - .125, cy - .125, cx + .125, cy + .125))
            area = unary_union(cells).buffer(0).buffer(-.125) if cells else None
            # sanity: the connector lane centre itself must be inside the lane area
            cen_in = sum(1 for p in path[60:-60] if area is not None and area.contains(Point(p))) / max(1, len(path[60:-60]))
            edge = area.boundary if area is not None else None

            def area_m(poses):
                if area is None:
                    return -9.
                return min(edge.distance(Point(c)) * (1 if area.contains(Point(c)) else -1) for p in poses for c in corners(*p))

            def lane_m(poses):
                return min(hw - abs(S.lateral(c, path)) for p in poses for c in corners(*p))
            sp, ip = stock_poses(path, vN), ideal_poses(path)
            r = {'town': town, 'connecting': con, 'to': tl, 'vN': vN, 'lane_width': round(2 * hw, 3),
                 'gateS': round(S.margin(path, hw, vN), 3), 'lane_stock': round(lane_m(sp), 3), 'area_stock': round(area_m(sp), 3),
                 'lane_ideal': round(lane_m(ip), 3), 'area_ideal': round(area_m(ip), 3), 'centre_in_area': round(cen_in, 3),
                 **{k: v for k, v in SEEN[key].items() if k in ('dh', 'incoming', 'outgoing', 'LrefN')}}
            rows.append(r)
            print(json.dumps(r), flush=True)
        del m
    (outdir / 'margins.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
    sites = {(r['town'], r['connecting'], r['to']) for r in rows}
    summ = {'keys': len(rows), 'sites': len(sites)}
    for f in ('gateS', 'lane_stock', 'area_stock', 'lane_ideal', 'area_ideal'):
        ok = {(r['town'], r['connecting'], r['to']) for r in rows if r[f] >= .45}
        summ[f] = {'max': max(r[f] for r in rows), 'sites_ge_0.45': len(ok)}
    summ['min_centre_in_area'] = min(r['centre_in_area'] for r in rows)
    (outdir / 'summary.json').write_text(json.dumps(summ, indent=1), encoding='utf-8')
    print('SUMMARY', json.dumps(summ), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
