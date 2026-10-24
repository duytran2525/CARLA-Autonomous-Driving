"""v5 (fill v2/v3): physical-identity evidence across the 25 C0-partial sites + 8 new sites (M02-M08, F03): junction buckets (all connecting roads of their XODR junction ids)
and corridor windows, with the same rule as site-identity-evidence.py: two sites are the same physical place when their
modelled cross-sections touch or overlap (margin <= 0). Reporting only. Run: python -I junction-identity-evidence.py OUT.json
"""
import importlib.util, json, math, sys
from pathlib import Path
import xml.etree.ElementTree as ET

here = Path(__file__).parent
spec = importlib.util.spec_from_file_location('gen', here / 'fill20-generate.py'); gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
BUCKETS = {'P04-J53': [53], 'P04-J1452': [1452], 'P04-J148': [148], 'P04-J621': [621], 'P04-J785': [785],
           'P04-J459complex': [335, 459, 483, 870, 1249], 'P05-J396': [396], 'P05-J562': [562],
           'P05-J720': [720], 'P05-J207': [207], 'P05-J838': [838], 'P05-J979': [979], 'P06-J452': [452],
           'P06-J582': [582], 'P07-J169': [169], 'P07-J543': [543], 'P07-J605': [605],
           # fill v2 (409911e) / v3 (4a26a66) M sites
           'P04-J1368': [1368], 'P05-J1126': [1126], 'P04-J1103': [1103], 'P06-J838': [838], 'P05-J2240': [2240],
           'P07-J123': [123], 'P05-J2086': [2086]}
CORRIDORS = {'A04-R45': ('Town04', 45, 160., 340.), 'A05-R37': ('Town05', 37, 220., 400.), 'A06-R40': ('Town06', 40, 140., 300.),
             'Town06-R37-S0': ('Town06', 37, None, None), 'Town04-R39-S0': ('Town04', 39, None, None),
             'Town06-R38-S0': ('Town06', 38, None, None), 'Town06-R49-S0': ('Town06', 49, None, None),
             'Town06-R29-S0': ('Town06', 29, None, None), 'Town04-R40-S0': ('Town04', 40, None, None)}  # last = new F03
TOWN = {'P04': 'Town04', 'P05': 'Town05', 'P06': 'Town06', 'P07': 'Town07'}
trees = {}


def tree(town):
    if town not in trees:
        root = ET.parse(gen.ROOT / f'{town}.xodr').getroot()
        trees[town] = (root, {int(r.get('id')): r for r in root.findall('road')})
    return trees[town]


def widths(r, s):
    secs = r.find('lanes').findall('laneSection')
    sec = max((x for x in secs if float(x.get('s')) <= s + 1e-9), key=lambda x: float(x.get('s')))
    out = []
    for side in ('left', 'right'):
        node = sec.find(side); total = 0.
        for ln in (node.findall('lane') if node is not None else ()):
            ds = s - float(sec.get('s'))
            rec = max((w for w in ln.findall('width') if float(w.get('sOffset')) <= ds + 1e-9), key=lambda w: float(w.get('sOffset')), default=None)
            if rec is not None:
                x = ds - float(rec.get('sOffset')); total += sum(float(rec.get(k)) * x ** i for i, k in enumerate('abcd'))
        out.append(total)
    return out


def sample_road(town, rid, s0=None, s1=None):
    _, roads = tree(town); r = roads[rid]; gs = gen.geometries(r)
    s0 = 0. if s0 is None else s0; s1 = float(r.get('length')) if s1 is None else s1
    if s1 is None or s0 is None:
        return []
    pts = []
    for i in range(int((s1 - s0) // 2) + 1):
        s = s0 + i * 2.; x, y, h = gen.point(gs, s); l, rt = widths(r, s); pts.append((x, y, h, l, rt))
    return pts


def site_points(name):
    if name in CORRIDORS:
        town, rid, s0, s1 = CORRIDORS[name]
        if s0 is None:  # new corridor = its whole first laneSection
            _, roads = tree(town); secs = roads[rid].find('lanes').findall('laneSection')
            s0 = float(secs[0].get('s')); s1 = float(secs[1].get('s')) if len(secs) > 1 else float(roads[rid].get('length'))
        return town, sample_road(town, rid, s0, s1)
    town = TOWN[name[:3]]; root, roads = tree(town); pts = []
    for j in root.findall('junction'):
        if int(j.get('id')) in BUCKETS[name]:
            for c in j.findall('connection'):
                pts += sample_road(town, int(c.get('connectingRoad')))
    return town, pts


def margin(pa, pb):
    best = None
    for xa, ya, ha, la, ra in pa:
        for xb, yb, hb, lb, rb in pb:
            d = math.hypot(xb - xa, yb - ya)
            if best is not None and d - (max(la, ra) + max(lb, rb)) > best:
                continue
            wa = la if math.cos(ha) * (yb - ya) - math.sin(ha) * (xb - xa) > 0 else ra
            wb = lb if math.cos(hb) * (ya - yb) - math.sin(hb) * (xa - xb) > 0 else rb
            m = d - (wa + wb); best = m if best is None else min(best, m)
    return best


names = list(BUCKETS) + list(CORRIDORS)
pts = {n: site_points(n) for n in names}
rows = []
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if pts[a][0] != pts[b][0] or not pts[a][1] or not pts[b][1]:
            continue
        m = margin(pts[a][1], pts[b][1])
        rows.append({'a': a, 'b': b, 'town': pts[a][0], 'margin_m': round(m, 2), 'touch': m <= 0})
with open(sys.argv[1], 'x', encoding='utf-8') as f:
    json.dump({'rule': 'same physical place when modelled cross-sections touch/overlap (margin <= 0)', 'pairs': rows}, f, indent=1)
for r in sorted(rows, key=lambda r: r['margin_m'])[:20]:
    print(r)
