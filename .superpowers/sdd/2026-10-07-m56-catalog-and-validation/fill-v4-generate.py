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


def comparable(cat, a, b):
    if cat in 'CL':
        return sum(delta(a[n], b[n]) >= F(1, 5) for n in ('vN', 'G', 'LrefN')) >= 2
    names = {'M': ('vN', 'G'), 'I': ('vE', 'gap'), 'O': ('vE', 'G')}[cat]
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
            if why:
                skips[cat]['NPC_' + why] += 1; continue
            out[cat].append({'town': town, 'junction': jid, 'LrefN': roads[n['connecting']].get('length'),
                             'ego': {**e, 'out_lane': ole}, 'npc': {**n, 'out_lane': oln},
                             'notation': {'EGO': notation(e, ole), 'NPC': notation(n, oln)}})
    ms = []
    for m in v2.merges_v2(town, True):
        mf, br, jid = m['mainflow'], m['branch'], m['junction']
        why = runin(roads, br, jid, 150.)
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


def main(out_path, commit):
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
    for cat in 'CLMIO':
        pool = sorted(pools[cat], key=key); random.Random(SEED + OFFSET[cat]).shuffle(pool)
        for slot, k in sorted(SLOTS[cat].items()):
            if cat in 'CLM':
                vN = vNk(k)
                def desc(x):
                    L = F(x['LrefN']); return {'vN': vN, 'G': derive_g(VE[cat], vN, L), 'LrefN': L}
                def fits(x, d):
                    why = runin(v2.trees[x['town']][1], x['ego'], x['junction'], float(d['G'] + VE[cat] ** 2 / 3 + 20))
                    return 'EGO_' + why if why else None
                free = lambda x: (x['town'], x['junction']) not in used_j
            else:
                vE = series(F(6), F(5, 4), k); gap = series(F(6), F(13, 10), k); G = series(F(15), F(13, 10), k)
                a = gen.A; vEf = float(vE)
                need_i = 7 * vEf + 3.75 + vEf ** 2 / (2 * a) + float(gap) + gen.MARGIN
                rs = max(3 * vEf, vEf * (float(G) + 9.5) / (vEf - 2.5)) if vEf > 2.5 else math.inf
                need_o = rs + 3 * vEf + 3.75 + vEf ** 2 / (2 * a) + float(G) + gen.MARGIN
                need = need_i if cat == 'I' else need_o
                need_axis = max(3 * vEf, (rs + 3 * vEf) if cat == 'O' else 3 * vEf)
                desc = lambda x: {'vE': vE, 'gap': gap} if cat == 'I' else {'vE': vE, 'G': G}
                def fits(x, d):
                    if x['length'] < need:
                        return 'LENGTH_SHORT'
                    if x.get('axis_run_m', 0.) < need_axis:
                        return 'AXIS_RUN_SHORT'
                    return None
                free = lambda x: (all(site_uses[(x['town'], r)] < 2 and (x['town'], r) not in used_roads for r in x['roads'])
                                  and not any((x['town'], j) in used_j for j in x.get('junctions_crossed', ())))
            chosen, queue, why_n = None, [], Counter()
            for x in pool:
                if not free(x):
                    why_n['SITE_USED'] += 1; continue
                if counts[(cat, x['town'])] >= 3:
                    why_n['TOWN_CAP'] += 1; continue
                d = desc(x); w = fits(x, d)
                if w:
                    why_n[w] += 1; continue
                if chosen is None:
                    if not all(comparable(cat, d, h) for h in held[cat]):
                        why_n['LADDER'] += 1; continue
                    chosen = (x, d)
                elif len(queue) < QUEUE:
                    queue.append((x, d))
                else:
                    break
            entry = {'id': f'M56-P-{slot}', 'slot': slot, 'category': cat, 'k': k, 'skipped': dict(why_n)}
            if chosen is None:
                entry['status'] = 'EMPTY_NO_ELIGIBLE_CANDIDATE'
            else:
                x, d = chosen
                entry.update(status='PROPOSED', site=x, descriptors={n: str(v) for n, v in d.items()},
                             queue=[{'site': q, 'descriptors': {n: str(v) for n, v in qd.items()}} for q, qd in queue])
                counts[(cat, x['town'])] += 1; held[cat].append(d)
                if cat in 'CLM':
                    used_j.add((x['town'], x['junction']))
                else:
                    for r in x['roads']:
                        site_uses[(x['town'], r)] += 1
                    used_j.update((x['town'], j) for j in x.get('junctions_crossed', ()))
            entries.append(entry)
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
    main(sys.argv[1], sys.argv[2])
