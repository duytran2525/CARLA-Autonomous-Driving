"""A-SEL2 offline census (2026-11-08), BEFORE any fill v4 prereg: no assignment, no candidate is proposed.
Per usable town (A-SEL2 §1) enumerate junction-level C / L / M site options from the pinned XODR and test whether a
G ladder exists per category (spec §6.4 diversity pair (vN, G): every pair of the 8 scenes needs vN and G to differ by
>= 20 %, i.e. ratio >= 5/4). G = product m56.catalog.derive_g(vE, vN(k), LrefN) exactly; LrefN = NPC connector
road/@length.

Option rules (census only; they become prereg rules only if registered later):
- connection = incoming road/lane -> connecting road/lane -> outgoing road/lane (fill20/v2 conventions, heading via
  fill v2 heading_change_fixed: + = left turn).
- C: EGO and NPC both straight (|dh| <= 10 deg), different incoming roads, incoming travel headings 60..120 deg apart.
- L: EGO left (60 <= dh <= 120), NPC straight from the opposite approach (incoming headings 150..210 deg apart).
- C and L: the two connector lane centrelines intersect in plan, |dz| <= 2 m there; no dynamic signal within 50 m
  of the junction on either incoming road (fill v2 signal_near_fixed).
- M: fill v2 merges_v2(wide=True) (registered fill v2 rule); NPC = branch, EGO = mainflow, vE = 4.
- Excluded: every junction used by the 39 candidates of the latest C0 revision.
Retained valid scenes (spec rules, results of 08/11): C01 G26 k1, C05 G16.5 k5, C08 G15.5 k8, L01 G11 k1, L04 G9 k4.
usage: python -I asel2-census.py OUT.json"""
import hashlib, importlib.util, itertools, json, math, sys
from fractions import Fraction as F
from pathlib import Path
import xml.etree.ElementTree as ET

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('v2', here / 'fill-v2-generate.py'); v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)
gen = v2.gen
sys.path.insert(0, 'D:/AI/CARLA-Funny-Moments.worktrees/m56-v9')
from m56.catalog import derive_g

MAPS = Path('E:/Carla/CarlaUE4/Content/Carla/Maps')
TOWNS = ['Town01', 'Town02', 'Town04', 'Town05', 'Town06', 'Town07', 'Town10HD', 'Town11', 'Town12', 'Town13', 'Town15']
REV = sorted((here / '../../../outputs').glob('m56_c0_partial_io_audit_*/c0-partial-v5-frozen-revision.json'))[-1]


def xodr(town):
    p = MAPS / 'OpenDrive' / f'{town}.xodr'
    return p if p.exists() else MAPS / town / 'OpenDrive' / f'{town}.xodr'


def load(town):
    root = ET.parse(xodr(town)).getroot()
    roads = {int(r.get('id')): r for r in root.findall('road')}
    v2.trees[town] = (root, roads)
    v2.ANCHORS[town] = []
    v2.CURRENT_JUNCTIONS.setdefault(town, set())
    return root, roads


def elevation(road):
    els = [(float(e.get('s')), *(float(e.get(k)) for k in 'abcd')) for e in road.find('elevationProfile').findall('elevation')] \
        if road.find('elevationProfile') is not None else []
    def z(s):
        r = max((e for e in els if e[0] <= s + 1e-9), key=lambda e: e[0], default=None)
        if r is None:
            return 0.
        d = s - r[0]
        return r[1] + r[2] * d + r[3] * d * d + r[4] * d ** 3
    return z


def lane_centre(road, lane_id):
    """Plan polyline (x, y, z) of a connector lane centre, 0.5 m steps, first laneSection widths."""
    gs = gen.geometries(road); z = elevation(road); L = float(road.get('length'))
    sec = road.find('lanes').findall('laneSection')[0]
    side = sec.find('left' if lane_id > 0 else 'right')
    lanes = {int(l.get('id')): l for l in (side.findall('lane') if side is not None else ())}
    def width(l, ds):
        ws = [(float(w.get('sOffset')), *(float(w.get(k)) for k in 'abcd')) for w in l.findall('width')]
        r = max((w for w in ws if w[0] <= ds + 1e-9), key=lambda w: w[0], default=(0, 0, 0, 0, 0))
        d = ds - r[0]
        return r[1] + r[2] * d + r[3] * d * d + r[4] * d ** 3
    pts = []
    n = max(2, int(L / .5) + 1)
    for i in range(n):
        s = L * i / (n - 1)
        x, y, h = gen.point(gs, s)
        off = sum(width(lanes[j], s) for j in range(1, abs(lane_id)) for j in [j * (1 if lane_id > 0 else -1)] if j in lanes)
        off += width(lanes[lane_id], s) / 2 if lane_id in lanes else 0.
        off *= 1 if lane_id > 0 else -1
        pts.append((x - off * math.sin(h), y + off * math.cos(h), z(s)))
    return pts


def cross(p, q):
    for (a, b) in zip(p, p[1:]):
        for (c, d) in zip(q, q[1:]):
            den = (b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])
            if abs(den) < 1e-12:
                continue
            t = ((c[0] - a[0]) * (d[1] - c[1]) - (c[1] - a[1]) * (d[0] - c[0])) / den
            u = ((c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])) / den
            if 0 <= t <= 1 and 0 <= u <= 1:
                return abs((a[2] + t * (b[2] - a[2])) - (c[2] + u * (d[2] - c[2])))
    return None


def h_in(roads, c, jid):
    inc = roads[c['incoming']]; at_end = v2.touching_end(inc, jid)
    if at_end is None:
        return None
    h = gen.end_heading(gen.geometries(inc), at_end)
    return None if h is None else math.degrees(h + (0 if at_end else math.pi))


def connections(root, roads, j):
    jid = int(j.get('id')); out = []
    for c in j.findall('connection'):
        inc, con = int(c.get('incomingRoad')), int(c.get('connectingRoad'))
        if inc not in roads or con not in roads or roads[inc].get('junction') != '-1':
            continue
        link = roads[con].find('link'); contact = c.get('contactPoint')
        nxt = link.find('successor' if contact == 'start' else 'predecessor') if link is not None else None
        if nxt is None or nxt.get('elementType') != 'road' or int(nxt.get('elementId')) not in roads:
            continue
        for ll in c.findall('laneLink'):
            cc = {'incoming': inc, 'connecting': con, 'contact': contact, 'from': int(ll.get('from')), 'to': int(ll.get('to')),
                  'outgoing': int(nxt.get('elementId')), 'out_contact': nxt.get('contactPoint'),
                  'LrefN': float(roads[con].get('length'))}
            lane = next((l for sec in roads[con].find('lanes').findall('laneSection')[:1] for side in ('left', 'right')
                         if sec.find(side) is not None for l in sec.find(side).findall('lane') if int(l.get('id')) == cc['to']), None)
            if lane is None or lane.get('type') != 'driving':
                continue
            dh = v2.heading_change_fixed(roads, cc, jid); hi = h_in(roads, cc, jid)
            if dh is None or hi is None:
                continue
            out.append({**cc, 'dh': dh, 'h_in': hi})
    return out


def used_junctions():
    rev = json.loads(REV.read_text(encoding='utf-8'))
    used = {}
    for c in rev['candidates']:
        if c['category'] not in 'CLM':
            continue
        _, roads = v2.trees.get(c['town']) or load(c['town'])
        for a in c['actors']:
            for seg in a['route_recipe']['route'].split('→')[1:2]:
                r = roads.get(int(seg.split('/')[0]))
                if r is not None and r.get('junction') != '-1':
                    used.setdefault(c['town'], set()).add(int(r.get('junction')))
    return used


def options(town, excluded):
    root, roads = load(town)
    out = {'C': [], 'L': [], 'M': []}
    for j in root.findall('junction'):
        jid = int(j.get('id'))
        if jid in excluded.get(town, ()):
            continue
        cs = connections(root, roads, j)
        sig = lambda c: v2.signal_near_fixed(roads[c['incoming']], jid)
        seen = {'C': set(), 'L': set()}
        for e, n in itertools.permutations(cs, 2):
            if e['incoming'] == n['incoming'] or abs(n['dh']) > 10:
                continue
            ang = (n['h_in'] - e['h_in']) % 360
            if abs(e['dh']) <= 10 and (60 <= ang <= 120 or 240 <= ang <= 300):
                cat = 'C'
            elif 60 <= e['dh'] <= 120 and 150 <= ang <= 210:
                cat = 'L'
            else:
                continue
            key = (e['connecting'], e['to'], n['connecting'], n['to'])
            if key in seen[cat] or sig(e) or sig(n):
                continue
            seen[cat].add(key)
            dz = cross(lane_centre(roads[e['connecting']], e['to']), lane_centre(roads[n['connecting']], n['to']))
            if dz is None or dz > 2:
                continue
            out[cat].append({'town': town, 'junction': jid, 'ego': e, 'npc': n, 'LrefN': n['LrefN']})
    for m in v2.merges_v2(town, True):
        out['M'].append({'town': town, 'junction': m['junction'], 'ego': m['mainflow'], 'npc': m['branch'],
                         'LrefN': float(roads[m['branch']['connecting']].get('length'))})
    return out


VE = {'C': F(4), 'L': F(2), 'M': F(4)}
K = {'C': [1, 2, 3, 4, 5, 6, 7, 8], 'L': [1, 2, 3, 4, 5, 6, 7, 8], 'M': [1, 2, 3, 4, 5, 0, 6, -1]}
RETAINED = {'C': {1: ('Town04', F(26)), 5: ('Town05', F(33, 2)), 8: ('Town06', F(31, 2))},
            'L': {1: ('Town04', F(11)), 4: ('Town05', F(9))}, 'M': {}}
vN = lambda k: F(3) * F(5, 4) ** (k - 1)


def ladder(cat, pool, retained):
    """Two stages. (1) G values only: backtrack over the slots (fewest distinct G first) for G values pairwise ratio
    >= 5/4, also against the retained G. (2) For a G solution, pick sites: junction distinct, <= 3 per town (retained
    towns count). Returns (retained_ok, assignment or None, distinct G per slot, G range per slot)."""
    slots = [k for k in K[cat] if k not in retained]
    sites = {k: {} for k in slots}
    for o in pool:
        for k in slots:
            g = derive_g(VE[cat], vN(k), F(str(round(o['LrefN'], 6))))
            sites[k].setdefault(g, set()).add((o['town'], o['junction']))
    fixed = [g for _, g in retained.values()]
    far = lambda g, h: max(g, h) >= min(g, h) * F(5, 4)
    fixed_ok = all(far(a, b) for a, b in itertools.combinations(fixed, 2))
    order = sorted(slots, key=lambda k: len(sites[k]))
    town0 = [t for t, _ in retained.values()]
    found = [None]
    def place(gs):  # stage 2: site choice for a fixed G vector (small backtrack)
        def go(i, used, towns):
            if i == len(order):
                return []
            for t, j in sorted(sites[order[i]][gs[i]]):
                if (t, j) not in used and towns.count(t) < 3:
                    r = go(i + 1, used | {(t, j)}, towns + [t])
                    if r is not None:
                        return [(gs[i], t, j, order[i])] + r
            return None
        return go(0, frozenset(), list(town0))
    def go(i, gs):
        if found[0] is not None:
            return
        if i == len(order):
            r = place(gs)
            if r is not None:
                found[0] = r
            return
        for g in sorted(sites[order[i]]):
            if all(far(g, h) for h in fixed + gs):
                go(i + 1, gs + [g])
    if fixed_ok:
        go(0, [])
    return (fixed_ok, found[0], {k: len(sites[k]) for k in slots},
            {k: (float(min(sites[k])), float(max(sites[k]))) if sites[k] else None for k in slots})


def main(out):
    excl = used_junctions()
    pools = {'C': [], 'L': [], 'M': []}
    per_town = {}
    for t in TOWNS:
        o = options(t, excl)
        per_town[t] = {c: (len(o[c]), len({x['junction'] for x in o[c]})) for c in o}
        for c in o:
            pools[c] += o[c]
        print(json.dumps({'town': t, 'options_(n, junctions)': per_town[t]}), flush=True)
    Path(out + '.pools.json').open('x', encoding='utf-8').write(json.dumps(
        {c: [(o['town'], o['junction'], o['LrefN']) for o in pools[c]] for c in pools}))
    res = {}
    for cat in 'MCL':
        variants = {'retained_all': RETAINED[cat], 'none': {}}
        variants.update({f'only_k{k}': {k: v} for k, v in RETAINED[cat].items()})
        if cat == 'C':
            variants['C01+C08'] = {k: v for k, v in RETAINED[cat].items() if k != 5}
            variants['C01+C05'] = {k: v for k, v in RETAINED[cat].items() if k != 8}
        for name, ret in variants.items():
            fixed_ok, sol, windows, ranges = ladder(cat, pools[cat], ret)
            res[f'{cat}/{name}'] = {'retained_pairwise_ok': fixed_ok, 'feasible': sol is not None,
                                    'assignment': [(float(g), t, j, k) for g, t, j, k in sol] if sol else None,
                                    'distinct_G_per_slot': windows, 'G_range_per_slot': ranges}
            print(json.dumps({'cat': cat, 'variant': name, 'retained_ok': fixed_ok, 'feasible': sol is not None,
                              'G_range_per_slot': ranges,
                              'assignment': [(float(g), t, j, k) for g, t, j, k in sol] if sol else None}), flush=True)
    data = json.dumps({'rev': str(REV), 'excluded': {k: sorted(v) for k, v in excl.items()}, 'per_town': per_town,
                       'results': res, 'xodr_sha256': {t: hashlib.sha256(xodr(t).read_bytes()).hexdigest() for t in TOWNS}},
                      indent=1, default=str)
    Path(out).open('x', encoding='utf-8').write(data)


if __name__ == '__main__':
    main(sys.argv[1])
