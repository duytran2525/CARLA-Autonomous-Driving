"""M56 fill v4 (A-SEL2) generator: implements docs/m56/PREREG_M56_FILL_V4_ASEL2_20261108.md exactly.
Reuses fill20 / fill v2 / fill v3 helpers (via fill-v3-generate.py) and the C/L connection rules of asel2-census.py.
Selector disclosure: CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT. No hand-picking: deterministic pools, stable key, seeded
shuffle, first-fit under the registered constraints; every skipped reason is counted.
Run ONLY after the prereg commit: python -I fill-v4-generate.py OUT.json PREREG_COMMIT"""
import hashlib, importlib.util, json, math, random, re, sys
from fractions import Fraction as F
from pathlib import Path

here = Path(__file__).resolve().parent
def mod(name, file):
    s = importlib.util.spec_from_file_location(name, here / file); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m
v3 = mod('v3', 'fill-v3-generate.py')
v2, gen = v3.v2, v3.v2.gen
cen = mod('cen', 'asel2-census.py')
cen.v2, cen.gen = v2, gen  # one shared v2 instance (trees, exclusions)
_load0 = cen.load
cen.load = lambda town: v2.trees[town] if town in v2.trees else _load0(town)  # parse once; keep exclusions/anchors
sys.path.insert(0, 'D:/AI/CARLA-Funny-Moments.worktrees/m56-v9')
from m56.catalog import derive_g, delta

PREREG = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/docs/m56/PREREG_M56_FILL_V4_ASEL2_20261108.md')
SEED = int(hashlib.sha256(b'M56-FILL-V4-ASEL2-2026-11-08').hexdigest()[:16], 16)
TOWNS = cen.TOWNS
HASHES = {'Town01': '97a7f6ac67812567e5c8ee0599cd823b23f80f30f3f97c502212e38b72e2b709',
          'Town02': '953c05f17def231239ffcadba3307628a82d0d335b67b4e29c3098f7aed1dd7d',
          'Town04': '4dddd1560ab7812b0e89cd4a523d8b6f2b93947eafb496d9eeb83cc772116c85',
          'Town05': '7edc53b0be840e177598da7a4ed9571146d7b2595ce280d154c90f92e8a48851',
          'Town06': 'a90b613175fa837fdc128ddfaf5ddad25797b128fdbd8cd945974bc21a60496e',
          'Town07': 'be730652769e993e27f748ba5793dba9e49d299205146a7a8db0bcd17af877bf',
          'Town10HD': '5d883b799f634030af92be1e9d79d107845540ba04338e8c60e095be1aef7be7',
          'Town11': '52ffa8412425b87394afa6a37bf0b688c0584a24df6ae88fea53866acb91e222',
          'Town12': '26fa53d4902ac3397d35f948969f0c77c1bf023755ede2c67edf00bef817151f',
          'Town13': '5354326f2fe4d26f0dcb5c82acf462257e638278363ab7adecb97ec3aa1f426f',
          'Town15': '8e9c69cfb3e750ace3e5d6b057e46786952a073c3924f319bbabb1a166dc2c17'}
QUEUE = 30
vNk = lambda k: F(3) * F(5, 4) ** (k - 1)
series = lambda base, ratio, k: base * ratio ** (k - 1)
VE = {'C': F(4), 'L': F(2), 'M': F(4)}
SLOTS = {'C': {'C02': 2, 'C03': 3, 'C04': 4, 'C06': 6, 'C07': 7},
         'L': {'L02': 2, 'L03': 3, 'L05': 5, 'L06': 6, 'L07': 7, 'L08': 8},
         'M': {'M01': 1, 'M02': 2, 'M03': 3, 'M04': 4, 'M05': 5, 'M06': 0, 'M07': 6, 'M08': -1},
         'I': {'I01': 1, 'I02': 2, 'I05': 0, 'I06': -2, 'I07': -1, 'I08': 6},
         'O': {'O04': 4, 'O05': 0, 'O06': -2, 'O07': -1, 'O08': 6}}
# retained valid scenes (spec 6.3 rows / C0 revision; town, k, descriptor values)
RETAINED = {'C': [('C01', 'Town04', {'vN': vNk(1), 'G': F(26), 'LrefN': F('21.96')}),
                  ('C05', 'Town05', {'vN': vNk(5), 'G': F(33, 2), 'LrefN': F('25.92')}),
                  ('C08', 'Town06', {'vN': vNk(8), 'G': F(31, 2), 'LrefN': F('47.88')})],
            'L': [('L01', 'Town04', {'vN': vNk(1), 'G': F(11), 'LrefN': F('18.77')}),
                  ('L04', 'Town05', {'vN': vNk(4), 'G': F(9), 'LrefN': F('30.13')})],
            'M': [],
            'I': [('I03', 'Town06', {'vE': series(F(6), F(5, 4), 3), 'gap': series(F(6), F(13, 10), 3)}),
                  ('I04', 'Town06', {'vE': series(F(6), F(5, 4), 4), 'gap': series(F(6), F(13, 10), 4)})],
            'O': [(o, t, {'vE': series(F(6), F(5, 4), k), 'G': series(F(15), F(13, 10), k)})
                  for o, t, k in (('O01', 'Town04', 1), ('O02', 'Town05', 2), ('O03', 'Town06', 3))]}
OFFSET = {'C': 11, 'L': 12, 'M': 13, 'I': 14, 'O': 15}
REL = {'C': ('vN', 'G', 'LrefN'), 'L': ('vN', 'G', 'LrefN'), 'M': ('vN', 'G', 'LrefN'), 'I': ('vE', 'gap'), 'O': ('vE', 'G')}


def comparable(cat, a, b):
    if cat in 'CL':
        return sum(delta(a[n], b[n]) >= F(1, 5) for n in ('vN', 'G', 'LrefN')) >= 2
    names = {'M': ('vN', 'G', 'LrefN'), 'I': ('vE', 'gap'), 'O': ('vE', 'G')}[cat]
    return all(delta(a[n], b[n]) >= F(1, 5) for n in names)


def runin(roads, conn, jid, need):
    """Prereg 3 run-in rule on the incoming road of `conn`: length >= need; on the last `need` m before J: no dynamic
    signal, |slope| <= 0.02 every 1 m, planView only line / arc with |curvature| <= 1/50. Returns None or a reason."""
    r = roads[conn['incoming']]; at_end = v2.touching_end(r, jid); L = float(r.get('length'))
    if at_end is None:
        return 'TOUCH_UNKNOWN'
    if L < need:
        return 'RUNIN_SHORT'
    s0, s1 = (L - need, L) if at_end else (0., need)
    sigs = r.find('signals')
    if sigs is not None and any(s.get('dynamic') == 'yes' and s0 - 1e-9 <= float(s.get('s')) <= s1 + 1e-9 for s in sigs.findall('signal')):
        return 'RUNIN_SIGNAL'
    slope = gen.slope_profile(r)
    if any(abs(slope(s0 + i)) > .02 for i in range(int(s1 - s0) + 1)):
        return 'RUNIN_SLOPE'
    for g in gen.geometries(r):
        if g['s'] < s1 and g['s'] + g['length'] > s0 and not (g['kind'] == 'line' or (g['kind'] == 'arc' and abs(g['curv']) <= 1 / 50)):
            return 'RUNIN_CURVE'
    return None


CHAIN = {'on': False}  # addendum E (replace mode with state['chain'])


def stretch_why(r, s0, s1):
    sigs = r.find('signals')
    if sigs is not None and any(s.get('dynamic') == 'yes' and s0 - 1e-9 <= float(s.get('s')) <= s1 + 1e-9 for s in sigs.findall('signal')):
        return 'RUNIN_SIGNAL'
    slope = gen.slope_profile(r)
    if any(abs(slope(s0 + i)) > .02 for i in range(int(s1 - s0) + 1)):
        return 'RUNIN_SLOPE'
    for g in gen.geometries(r):
        if g['s'] < s1 and g['s'] + g['length'] > s0 and not (g['kind'] == 'line' or (g['kind'] == 'arc' and abs(g['curv']) <= 1 / 50)):
            return 'RUNIN_CURVE'
    return None


def runin_chain(town, conn, jid, need):
    """Addendum E: the NPC run-in may continue upstream through junctions with exactly one straight (|dh| <= 10 deg)
    connection into the current road/lane, no dynamic signal on the chain stretch, no light within 50 m before each
    upstream junction, every road/connector of the chain within the slope/curve rule."""
    root, roads = v2.trees[town]
    junctions = {int(j.get('id')): j for j in root.findall('junction')}
    r_id, lane, j, rem = conn['incoming'], conn['from'], jid, float(need)
    for hop in range(8):
        r = roads[r_id]; L = float(r.get('length')); at_end = v2.touching_end(r, j)
        if at_end is None:
            return 'TOUCH_UNKNOWN'
        take = min(L, rem)
        w = stretch_why(r, *((L - take, L) if at_end else (0., take)))
        if w:
            return w
        rem -= take
        if rem <= 1e-9:
            return None
        link = r.find('link'); far = link.find('predecessor' if at_end else 'successor') if link is not None else None
        if far is None or far.get('elementType') != 'junction' or int(far.get('elementId')) not in junctions:
            return 'RUNIN_SHORT'
        jup = int(far.get('elementId'))
        cs = [c for c in cen.connections(root, roads, junctions[jup])
              if c['outgoing'] == r_id and abs(c['dh']) <= 10 and out_lane(roads, c) == lane]
        if len(cs) != 1:
            return 'RUNIN_CHAIN_AMBIGUOUS'
        c = cs[0]; con = roads[c['connecting']]
        w = stretch_why(con, 0., float(con.get('length')))
        if w:
            return w
        if v2.signal_near_fixed(roads[c['incoming']], jup):
            return 'RUNIN_SIGNAL'
        rem -= float(con.get('length'))
        if rem <= 1e-9:
            return None
        r_id, lane, j = c['incoming'], c['from'], jup
    return 'RUNIN_CHAIN_LONG'


def out_lane(roads, c):
    croad = roads[c['connecting']]
    lane = next((ln for sec in croad.find('lanes').findall('laneSection')[-1 if c['contact'] == 'start' else 0:][:1]
                 for side in ('left', 'right') if sec.find(side) is not None
                 for ln in sec.find(side).findall('lane') if int(ln.get('id')) == c['to']), None)
    lk = lane.find('link') if lane is not None else None
    nx = lk.find('successor' if c['contact'] == 'start' else 'predecessor') if lk is not None else None
    return None if nx is None else int(nx.get('id'))


def notation(c, ol):
    return f"{c['incoming']}/{c['from']:+d}→{c['connecting']}/{c['to']:+d}→{c['outgoing']}/{ol:+d}"


def cl_pool(town, excluded, skips):
    root, roads = v2.trees[town]
    out = {'C': [], 'L': []}
    opts = cen.options(town, excluded)
    janchor = {}
    for j in root.findall('junction'):
        st = [gen.geometries(roads[int(c.get('connectingRoad'))])[0] for c in j.findall('connection') if int(c.get('connectingRoad')) in roads]
        if st:
            janchor[int(j.get('id'))] = (sum(g['x'] for g in st) / len(st), sum(g['y'] for g in st) / len(st))
    for cat in 'CL':
        for o in opts[cat]:
            e, n, jid = o['ego'], o['npc'], o['junction']
            if not v2.far(town, [janchor[jid]]):
                skips[cat]['ANCHOR_30M'] += 1; continue
            ole, oln = out_lane(roads, e), out_lane(roads, n)
            if ole is None or oln is None:
                skips[cat]['OUT_LANE_UNKNOWN'] += 1; continue
            why = runin(roads, n, jid, 150.)
            if why and CHAIN['on']:
                why = runin_chain(town, n, jid, 150.)
            if why:
                skips[cat]['NPC_' + why] += 1; continue
            out[cat].append({'town': town, 'junction': jid, 'LrefN': roads[n['connecting']].get('length'),
                             'ego': {**e, 'out_lane': ole}, 'npc': {**n, 'out_lane': oln},
                             'notation': {'EGO': notation(e, ole), 'NPC': notation(n, oln)}})
    ms = []
    for m in v2.merges_v2(town, True):
        mf, br, jid = m['mainflow'], m['branch'], m['junction']
        why = runin(roads, br, jid, 150.)
        if why and CHAIN['on']:
            why = runin_chain(town, br, jid, 150.)
        if why:
            skips['M']['NPC_' + why] += 1; continue
        ol = m['outgoing'][1]
        ms.append({'town': town, 'junction': jid, 'LrefN': roads[br['connecting']].get('length'), 'ego': mf, 'npc': br,
                   'notation': {'EGO': notation(mf, ol), 'NPC': notation(br, ol)}, 'rule': m['rule']})
    out['M'] = ms
    return out


def excluded_sets():
    rev = json.loads(cen.REV.read_text(encoding='utf-8'))
    jun = cen.used_junctions()
    roads = set()
    for c in rev['candidates']:
        if c['category'] in 'IOF':
            m_ = re.search(r'R(\d+)', c['site_id'] or '')
            if m_:
                roads.add((c['town'], int(m_.group(1))))
            rr = c['actors'][0]['route_recipe']
            if isinstance(rr.get('road'), int):
                roads.add((c['town'], rr['road']))
    return jun, roads


def kappa_max(town, road):
    """Addendum B1: max |curvature| over the arc records of a road (connector)."""
    r = v2.trees[town][1][road]
    return max([abs(float(g[0].get('curvature'))) for g in r.find('planView').findall('geometry') if g[0].tag == 'arc'] or [0.])


def flat(road, s0, s1, lim=.0015):
    """Addendum D (B4): |grade| <= lim every 1 m on [s0, s1] and no non-zero superelevation record overlapping it."""
    sl = gen.slope_profile(road)
    if any(abs(sl(s0 + i)) > lim for i in range(int(max(s1 - s0, 0)) + 1)):
        return False
    lp = road.find('lateralProfile')
    sups = sorted((float(e.get('s')), float(e.get('a'))) for e in (lp.findall('superelevation') if lp is not None else []))
    for i, (s, a) in enumerate(sups):
        nxt = sups[i + 1][0] if i + 1 < len(sups) else float(road.get('length'))
        if a != 0 and s < s1 and nxt > s0:
            return False
    return True


def b4_clm(x, need_ego):
    """B4 for C/L/M: EGO spawn region = first 10 m of its run-in; NPC = its whole 150 m run-in (incoming roads)."""
    for role, need, span in (('ego', need_ego, 10.), ('npc', 150., 150.)):
        c = x[role]; r = v2.trees[x['town']][1][c['incoming']]; L = float(r.get('length'))
        at_end = v2.touching_end(r, x['junction'])
        s_far = L - need if at_end else need          # run-in start (farthest from J)
        a, b = (s_far, min(s_far + span, L)) if at_end else (max(s_far - span, 0.), s_far)
        if not flat(r, a, b):
            return False
    return True


def section_length(x):
    """Addendum B2: length of the laneSection io_recipe builds on (site road, site section)."""
    roads = v2.trees[x['town']][1]; secs = gen.sections(roads[x['road']])
    _, s0, s1, _ = secs[x['section']]
    return s1 - s0


def main(out_path, commit, state_path=None):
    """state_path (addendum B3, replace mode): JSON {"slots": [...to (re)fill...], "assigned": {slot: site}, "tried":
    [sites ever assigned]}; every other slot keeps its current site (it counts in caps, junctions, roads, ladder)."""
    state = json.loads(Path(state_path).read_text(encoding='utf-8')) if state_path else None
    CHAIN['on'] = bool(state and state.get('chain'))
    for t in TOWNS:
        assert hashlib.sha256(cen.xodr(t).read_bytes()).hexdigest() == HASHES[t], t
        cen.load(t)
    prereg_hash = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    jun, used_roads = excluded_sets()
    for t in TOWNS:  # prereg 1: exclusion = used junctions + 30 m anchors (fill v2 convention)
        v2.CURRENT_JUNCTIONS[t] = set(jun.get(t, ()))
    v2.CURRENT_ROADS = set(used_roads)
    for t in TOWNS:
        v2.ANCHORS[t] = v2.anchors(t)
    from collections import Counter
    skips = {c: Counter() for c in 'CLMIO'}
    pools = {c: [] for c in 'CLMIO'}
    for t in TOWNS:
        p = cl_pool(t, {k: v for k, v in jun.items()}, skips)
        for c in 'CLM':
            pools[c] += p[c]
        r1 = v3.chains_v3(t, set(), set(used_roads))
        pools['I'] += r1; pools['O'] += r1
    key = lambda x: (x['town'], x.get('junction', 0), json.dumps(x.get('notation', x.get('roads')), sort_keys=True),
                     str(x.get('lanes', '')), str(x.get('travel', '')))
    counts = Counter((cat, t) for cat in RETAINED for _, t, _ in RETAINED[cat])
    held = {cat: [d for _, _, d in RETAINED[cat]] for cat in RETAINED}
    used_j = set(); site_uses = Counter(); entries = []
    LIMIT = 300000  # addendum A: node limit per lookahead search (deterministic; exceeding it counts as infeasible)

    def static(cat, k, pool):
        """(x, d) in shuffled order passing the static rules (run-in / length / axis), plus skip counts."""
        out, why = [], Counter()
        if cat in 'CLM':
            vN = vNk(k)
            for x in pool:
                L = F(x['LrefN']); d = {'vN': vN, 'G': derive_g(VE[cat], vN, L), 'LrefN': L}
                w = runin(v2.trees[x['town']][1], x['ego'], x['junction'], float(d['G'] + VE[cat] ** 2 / 3 + 20))
                if w:
                    why['EGO_' + w] += 1
                elif state and float(vN) ** 2 * kappa_max(x['town'], x['npc']['connecting']) > 2.25:
                    why['B1_TURN_GATE'] += 1
                elif state and state.get('b4') and not b4_clm(x, float(d['G'] + VE[cat] ** 2 / 3 + 20)):
                    why['B4_START_SLOPE'] += 1
                elif state and tried(x):
                    why['B3_TRIED'] += 1
                else:
                    out.append((x, d))
            return out, why
        vE = series(F(6), F(5, 4), k); gap = series(F(6), F(13, 10), k); G = series(F(15), F(13, 10), k)
        a = gen.A; vEf = float(vE)
        need_i = 7 * vEf + 3.75 + vEf ** 2 / (2 * a) + float(gap) + gen.MARGIN
        rs = max(3 * vEf, vEf * (float(G) + 9.5) / (vEf - 2.5)) if vEf > 2.5 else math.inf
        need_o = rs + 3 * vEf + 3.75 + vEf ** 2 / (2 * a) + float(G) + gen.MARGIN
        need = need_i if cat == 'I' else need_o
        need_axis = max(3 * vEf, (rs + 3 * vEf) if cat == 'O' else 3 * vEf)
        d = {'vE': vE, 'gap': gap} if cat == 'I' else {'vE': vE, 'G': G}
        for x in pool:
            if x['length'] < need:
                why['LENGTH_SHORT'] += 1
            elif x.get('axis_run_m', 0.) < need_axis:
                why['AXIS_RUN_SHORT'] += 1
            elif any((x['town'], r) in used_roads for r in x['roads']):
                why['EXCLUDED_ROAD'] += 1
            elif state and section_length(x) < vEf ** 2 / 3 + 20 + ((7 * vEf + 3.75) if cat == 'I' else (rs + 3 * vEf + 3.75)) + 15:
                why['B2_ONE_ROAD_WINDOW'] += 1
            elif state and state.get('b4') and not flat(v2.trees[x['town']][1][x['road']], *gen.sections(v2.trees[x['town']][1][x['road']])[x['section']][1:3]):
                why['B4_START_SLOPE'] += 1
            elif state and tried(x):
                why['B3_TRIED'] += 1
            else:
                out.append((x, d))
        return out, why

    def site_free(cat, x, uj, uses):
        if cat in 'CLM':
            return (x['town'], x['junction']) not in uj
        return (all(uses[(x['town'], r)] < 2 for r in x['roads'])
                and not any((x['town'], j) in uj for j in x.get('junctions_crossed', ())))

    def take(cat, x, uj, cnt, uses):
        uj, cnt, uses = set(uj), Counter(cnt), Counter(uses)
        cnt[(cat, x['town'])] += 1
        if cat in 'CLM':
            uj.add((x['town'], x['junction']))
        else:
            for r in x['roads']:
                uses[(x['town'], r)] += 1
            uj.update((x['town'], j) for j in x.get('junctions_crossed', ()))
        return uj, cnt, uses

    def feasible(cat, rest, elig, hl, uj, cnt, uses):
        """Addendum A: does an assignment of the remaining slots exist (sites, caps, ladder)? Exhaustive over distinct
        descriptor values, one site per town per value; node limit LIMIT."""
        groups = {}
        for s in rest:
            g = {}
            for x, d in elig[s]:
                g.setdefault(tuple(d[n] for n in REL[cat]), (d, []))[1].append(x)  # only the compared descriptors matter
            groups[s] = g
        order = sorted(rest, key=lambda s: len(groups[s])); nodes = [0]
        def go(i, hl, uj, cnt, uses):
            nodes[0] += 1
            if nodes[0] > LIMIT:
                raise OverflowError
            if i == len(order):
                return True
            for d, xs in groups[order[i]].values():
                if not all(comparable(cat, d, h) for h in hl):
                    continue
                towns = set()
                for x in xs:
                    if x['town'] in towns or cnt[(cat, x['town'])] >= 3 or not site_free(cat, x, uj, uses):
                        continue
                    towns.add(x['town'])
                    if go(i + 1, hl + [d], *take(cat, x, uj, cnt, uses)):
                        return True
            return False
        try:
            return go(0, list(hl), uj, cnt, uses)
        except OverflowError:
            return False

    sk = lambda x: json.dumps({k_: x.get(k_) for k_ in ('town', 'junction', 'road', 'section', 'notation', 'roads', 'lanes')}, sort_keys=True)
    tried_keys = {sk(x) for x in (state or {}).get('tried', [])}
    tried = lambda x: sk(x) in tried_keys
    if state:
        for slot_, x in sorted(state['assigned'].items()):
            if slot_ in state['slots']:
                continue
            cat_ = slot_[0]; k_ = SLOTS[cat_][slot_]
            if cat_ in 'CLM':
                vN_ = vNk(k_); L_ = F(x['LrefN']); held[cat_].append({'vN': vN_, 'G': derive_g(VE[cat_], vN_, L_), 'LrefN': L_})
            else:
                vE_ = series(F(6), F(5, 4), k_)
                held[cat_].append({'vE': vE_, 'gap': series(F(6), F(13, 10), k_)} if cat_ == 'I' else {'vE': vE_, 'G': series(F(15), F(13, 10), k_)})
            used_j, counts, site_uses = take(cat_, x, used_j, counts, site_uses)
    for cat in 'CLMIO':
        pool = sorted(pools[cat], key=key); random.Random(SEED + OFFSET[cat]).shuffle(pool)
        slots = (sorted(s_ for s_ in SLOTS[cat] if not state or s_ in state['slots']) if not (state and state.get('order'))
                 else [s_ for s_ in state['order'] if s_[0] == cat])  # addendum C: explicit order (M04, M07 first)
        elig, swhy = {}, {}
        for s in slots:
            elig[s], swhy[s] = static(cat, SLOTS[cat][s], pool)
        for i, slot in enumerate(slots):
            rest = slots[i + 1:]
            chosen, fallback, queue, why_n = None, None, [], Counter(swhy[slot])
            for x, d in elig[slot]:
                if chosen is not None:
                    if len(queue) >= QUEUE:
                        break
                    if site_free(cat, x, used_j, site_uses) and counts[(cat, x['town'])] < 3:
                        queue.append((x, d))
                    continue
                if not site_free(cat, x, used_j, site_uses):
                    why_n['SITE_USED'] += 1; continue
                if counts[(cat, x['town'])] >= 3:
                    why_n['TOWN_CAP'] += 1; continue
                if not all(comparable(cat, d, h) for h in held[cat]):
                    why_n['LADDER'] += 1; continue
                if fallback is None:
                    fallback = (x, d)
                if not rest or feasible(cat, rest, elig, held[cat] + [d], *take(cat, x, used_j, counts, site_uses)):
                    chosen = (x, d)
                else:
                    why_n['LOOKAHEAD_INFEASIBLE'] += 1
            rule = 'lookahead'
            if chosen is None and fallback is not None:
                chosen, rule = fallback, 'fallback_first_fit'
            entry = {'id': f'M56-P-{slot}', 'slot': slot, 'category': cat, 'k': SLOTS[cat][slot], 'skipped': dict(why_n)}
            if chosen is None:
                entry['status'] = 'EMPTY_NO_ELIGIBLE_CANDIDATE'
            else:
                x, d = chosen
                entry.update(status='PROPOSED', rule=rule, site=x, descriptors={n: str(v) for n, v in d.items()},
                             queue=[{'site': q, 'descriptors': {n: str(v) for n, v in qd.items()}} for q, qd in queue])
                held[cat].append(d)
                used_j, counts, site_uses = take(cat, x, used_j, counts, site_uses)
            entries.append(entry)
            print(json.dumps({'slot': slot, 'status': entry['status'], 'rule': entry.get('rule'),
                              'town': (entry.get('site') or {}).get('town')}), flush=True)
    for e in entries:
        e.update(selector='CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT',
                 authority='Duy [chat] 2026-11-08 A-SEL2 (self-stated identity); prereg commit ' + commit,
                 review='CLAUDE_REVIEW_UNDER_DUY_DELEGATION; independent review waived by Duy 2026-10-24')
    filled = sum(e['status'] == 'PROPOSED' for e in entries)
    report = {'prereg': str(PREREG), 'prereg_sha256': prereg_hash, 'prereg_commit': commit, 'seed': SEED, 'xodr_sha256': HASHES,
              'excluded_junctions': {t: sorted(v) for t, v in jun.items()}, 'excluded_roads': sorted(used_roads),
              'pool_sizes': {c: len(pools[c]) for c in pools}, 'pool_skips': {c: dict(v) for c, v in skips.items()},
              'category_town_counts_after': {f'{c}/{t}': n for (c, t), n in sorted(counts.items())},
              'filled': filled, 'junctions_after_proposed': 5 + sum(e['status'] == 'PROPOSED' and e['category'] in 'CLM' for e in entries),
              'entries': entries}
    data = (json.dumps(report, indent=1, sort_keys=True, default=str) + '\n').encode()
    with open(out_path, 'xb') as f:
        f.write(data)
    print(json.dumps({'filled': filled, 'pools': report['pool_sizes'], 'sha256': hashlib.sha256(data).hexdigest(),
                      'empty': [e['slot'] for e in entries if e['status'] != 'PROPOSED']}))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == '--replace' else None)
