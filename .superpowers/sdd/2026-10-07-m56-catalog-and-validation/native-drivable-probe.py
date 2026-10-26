"""Report-only probe (2026-10-26, prereg v6 b): the v6 drivable union (v5 Driving quads + Roads/RoadLines raster,
0.5 m grid eroded 0.25 m) vs the frozen v5 union of a sealed scene.
  1. acceptance: first cast_ray hit label at a 0.5 m grid inside (v6 - v5) within 70 m of the conflict centre;
     v6 b passes only if >= 99 % Roads/RoadLines and none Sidewalks/Terrain/Vegetation/Buildings/Walls;
  2. effect: per actor, min road edge and frames < 0.15 m, and CONTINUOUS_FIT failures of the sealed motion envelopes
     against driving_boxes(v6 union) (the consumer's own _box_union_covers, margin 0.15 m + 1 mm).
Own server 2610, one map load. Run with M56_RECIPE=v6.  python -I native-drivable-probe.py TOWN SCENE_DIR:ACTION ..."""
import json, math, os, sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import V6, own_server, load, now, WS, drivable_union, driving_boxes
from m56.model import decode_record, load_json, VertexSet, _decode
from m56.evidence import _box_union_covers, _exact_bound
from m56.geometry import world_vertices
from m56.runtime import load_episode
assert V6, 'run with M56_RECIPE=v6'
from shapely import wkt
from shapely.geometry import MultiPoint, Point
from shapely.prepared import prep

town, args = sys.argv[1], sys.argv[2:]
OUT = WS.parents[2] / 'outputs' / f'm56_drivable_probe_{town}_{now()}.json'
BAD = {'Sidewalks', 'Terrain', 'Vegetation', 'Buildings', 'Walls'}


def log(**k):
    print(json.dumps(k, default=str), flush=True)


def edge_of(actor, union, pu):
    fp = MultiPoint([(float(v[0]), float(v[1])) for v in world_vertices(actor.body, actor.pose)]).convex_hull
    return fp.distance(union.boundary) if pu.contains(fp) else -fp.distance(union.boundary)


rows = []
with own_server(log) as (client, proc, start):
    import carla
    world = load(client, town); m = world.get_map()
    for arg in args:
        sd, action = arg.rsplit(':', 1); sd = Path(sd).resolve()
        fx = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
        old = wkt.loads((sd / 'drivable-union.wkt').read_text())
        reg = fx.domain.region
        center = (sum(float(v[0]) for v in reg) / len(reg), sum(float(v[1]) for v in reg) / len(reg))
        radius = max(90., max(math.dist((float(p.x), float(p.y)), center) for p in fx.poses.values()) + 20.)
        new = drivable_union(m, center, radius, world, fx.routes)
        added = new.difference(old)
        zref = sum(float(t.z) for r in fx.routes.values() for t in r.transforms) / sum(len(r.transforms) for r in fx.routes.values())
        pa = prep(added); labels = Counter(); bad_pts = []
        x0, y0, x1, y1 = added.bounds if not added.is_empty else (0, 0, 0, 0)
        pts = [(x0 + .5 * i, y0 + .5 * j) for i in range(int((x1 - x0) / .5) + 1) for j in range(int((y1 - y0) / .5) + 1)]
        pts = [p for p in pts if math.dist(p, center) <= 70. and pa.contains(Point(p))]
        step = max(1, len(pts) // 4000)
        for x, y in pts[::step]:
            hits = world.cast_ray(carla.Location(x, y, zref + 5.), carla.Location(x, y, zref - 5.))
            lab = str(hits[0].label) if hits else 'NO_HIT'
            labels[lab] += 1
            if lab in BAD and len(bad_pts) < 20:
                bad_pts.append((round(x, 2), round(y, 2), lab))
        total = sum(labels.values()); road = labels['Roads'] + labels['RoadLines']
        # effect on the sealed episode
        pu = prep(new); ev = load_episode(sd / 'run' / 'episodes' / sd.name / action)
        edge = {}
        for f in ev.raw:
            for a in f.actors:
                e = edge_of(a, new, pu); cur = edge.setdefault(a.role, [9e9, 0])
                cur[0] = min(cur[0], e); cur[1] += e < .151
        zlo = min(t.z for r in fx.routes.values() for t in r.transforms) - 1.
        zhi = max(t.z for r in fx.routes.values() for t in r.transforms) + 3.
        regions = {role: driving_boxes(new, fx.routes[role], zlo, zhi) for role in fx.routes}
        motion = json.loads((sd / 'run' / 'episodes' / sd.name / action / 'g4' / 'motion-intervals.json').read_text(encoding='utf-8'))
        fit = Counter()
        for row in motion:
            for role, p in row['actors'].items():
                env = _decode(VertexSet, p['envelope'], 'motion.envelope')
                if not _box_union_covers(env, regions[role], Fraction(3, 20), Fraction(1, 1000)):
                    fit[role] += 1
        r = {'scene': sd.name, 'action': action, 'added_area_m2': round(added.area, 1), 'samples': total,
             'labels': dict(labels), 'road_share': round(road / total, 4) if total else None, 'bad_points': bad_pts,
             'accept': bool(total) and road / total >= .99 and not any(labels[b] for b in BAD),
             'edge_v6': {k: {'min_m': round(v[0], 3), 'frames_below_0.15': v[1]} for k, v in edge.items()},
             'fit_fail_v6': dict(fit), 'intervals': len(motion)}
        rows.append(r); log(**r)
with open(OUT, 'x', encoding='utf-8') as f:
    json.dump({'note': 'report-only drivable probe (prereg v6 b)', 'town': town, 'rows': rows}, f, indent=1)
print('DONE', OUT)
