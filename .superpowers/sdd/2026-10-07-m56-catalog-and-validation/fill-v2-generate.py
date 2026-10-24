"""Census + deterministic assignment for the 15 empty M56 slots, implementing docs/m56/PREREG_M56_FILL_V2_20261024.md.
Reuses fill20-generate.py (dd2954c) helpers; only the registered rule changes F2-1..F2-4 differ. Reports the pools under
(a) fill20 code, (b) + objective fixes F2-1/F2-4, (c) + F2-2, (d) + F2-3 (= the v2 rule used for assignment).
Selector disclosure: CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT. Run ONLY after Duy approved the prereg commit:
python -I fill-v2-generate.py OUT.json APPROVED_PREREG_COMMIT"""
from fractions import Fraction as F
from pathlib import Path
import hashlib, importlib.util, json, math, random, sys
import xml.etree.ElementTree as ET

here = Path(__file__).parent
spec = importlib.util.spec_from_file_location('gen', here / 'fill20-generate.py'); gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
PREREG = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/docs/m56/PREREG_M56_FILL_V2_20261024.md')
SEED = int(hashlib.sha256(b'M56-FILL-V2-PREREG-2026-10-24').hexdigest()[:16], 16)
# Sites of the 31 C0-partial scenes (site-ledger-packet.json of C0 v4; junction members as junction-identity-evidence.py).
CURRENT_JUNCTIONS = {'Town04': {53, 1452, 148, 621, 785, 335, 459, 483, 870, 1249}, 'Town05': {396, 562, 720, 207, 838, 979},
                     'Town06': {452, 582}, 'Town07': {169, 543, 605}}
CURRENT_ROADS = {('Town04', 45), ('Town04', 39), ('Town05', 37), ('Town06', 40), ('Town06', 37), ('Town06', 38),
                 ('Town06', 49), ('Town06', 29)}
EXISTING = {('C', 'Town04'): 3, ('C', 'Town05'): 3, ('C', 'Town06'): 2, ('F', 'Town06'): 2, ('I', 'Town04'): 2,
            ('I', 'Town05'): 1, ('I', 'Town06'): 3, ('L', 'Town04'): 2, ('L', 'Town05'): 3, ('L', 'Town07'): 3,
            ('M', 'Town04'): 1, ('O', 'Town04'): 2, ('O', 'Town05'): 1, ('O', 'Town06'): 3}
RESOLUTIONS = gen.RESOLUTIONS + [
    'Exclusion anchors (30 m) = mean start point (XODR) of the connecting roads of each CURRENT junction member.',
    'F2-3 chains: consecutive laneSections of one road whose (inner, outer) lane pair continues by lane successor link '
    '(same id when no link); a chain continues onto the successor road only for a road-road link with contactPoint '
    'start (same orientation); every section satisfies every R1 condition and the 30 m exclusion.',
    'F2-4 uphill: lane id < 0 travels increasing s, so it is uphill where slope > 0; lane id > 0 where slope < 0.',
    'M indices: M02-M04 reuse the original chain k = 2, 3, 4; M05-M08 k = 5, 0, 6, -1 (fill20 section 4).',
]
trees = {}


def town_tree(town):
    if town not in trees:
        root = ET.parse(gen.ROOT / f'{town}.xodr').getroot()
        trees[town] = (root, {int(r.get('id')): r for r in root.findall('road')})
    return trees[town]


def anchors(town):
    root, roads = town_tree(town)
    out = []
    for j in root.findall('junction'):
        if int(j.get('id')) in CURRENT_JUNCTIONS[town]:
            starts = [gen.geometries(roads[int(c.get('connectingRoad'))])[0] for c in j.findall('connection')
                      if int(c.get('connectingRoad')) in roads]
            out.append((sum(g['x'] for g in starts) / len(starts), sum(g['y'] for g in starts) / len(starts)))
    return out


ANCHORS = {t: anchors(t) for t in gen.HASHES}


def far(town, xy_points):  # XODR coordinates on both sides
    return all(math.hypot(x - ax, y - ay) > 30. for x, y in xy_points for ax, ay in ANCHORS[town])


def patch_fill20():
    """Pool (a): the fill20 code itself with the v2 exclusion lists (its anchors are CARLA coordinates: y = -y)."""
    gen.USED_JUNCTIONS = CURRENT_JUNCTIONS
    gen.USED_ROADS = CURRENT_ROADS
    gen.USED_ANCHORS = {t: [(x, -y) for x, y in a] for t, a in ANCHORS.items()}


# -- F2-1: heading/signal at the end of the incoming road that touches junction J ---------------------------------
def touching_end(road, jid):
    link = road.find('link')
    for tag, at_end in (('successor', True), ('predecessor', False)):
        e = link.find(tag) if link is not None else None
        if e is not None and e.get('elementType') == 'junction' and int(e.get('elementId')) == jid:
            return at_end
    return None


def heading_change_fixed(roads, c, jid):
    inc = roads[c['incoming']]; out = roads[c['outgoing']]
    at_end = touching_end(inc, jid)
    if at_end is None:
        return None
    h_in = gen.end_heading(gen.geometries(inc), at_end)
    h_out = gen.end_heading(gen.geometries(out), c['out_contact'] == 'end')
    if h_in is None or h_out is None:
        return None
    if not at_end:
        h_in += math.pi  # entering J at the road start: travel against s
    if c['out_contact'] == 'end':
        h_out += math.pi
    return math.degrees((h_out - h_in + math.pi) % (2 * math.pi) - math.pi)


def signal_near_fixed(road, jid):
    sigs = road.find('signals')
    at_end = touching_end(road, jid)
    if sigs is None or at_end is None:
        return at_end is None  # cannot place J on this road: fail closed
    length = float(road.get('length'))
    return any(s.get('dynamic') == 'yes' and ((at_end and float(s.get('s')) >= length - 50) or
                                              (not at_end and float(s.get('s')) <= 50)) for s in sigs.findall('signal'))


def merges_v2(town, wide):
    """fill20 merges() with F2-1 always and F2-2 when wide."""
    root, roads = town_tree(town)
    out = []
    for j in root.findall('junction'):
        jid = int(j.get('id'))
        if jid in CURRENT_JUNCTIONS[town]:
            continue
        conns = []
        for c in j.findall('connection'):
            inc, con = int(c.get('incomingRoad')), int(c.get('connectingRoad'))
            if inc not in roads or con not in roads or roads[inc].get('junction') != '-1':
                continue
            link = roads[con].find('link'); contact = c.get('contactPoint')
            nxt = link.find('successor' if contact == 'start' else 'predecessor') if link is not None else None
            if nxt is None or nxt.get('elementType') != 'road':
                continue
            out_road = int(nxt.get('elementId'))
            if out_road not in roads or roads[out_road].get('junction') != '-1':
                continue
            for ll in c.findall('laneLink'):
                conns.append({'id': int(c.get('id')), 'incoming': inc, 'incoming_length': float(roads[inc].get('length')),
                              'connecting': con, 'contact': contact, 'from': int(ll.get('from')), 'to': int(ll.get('to')),
                              'outgoing': out_road, 'out_contact': nxt.get('contactPoint')})
        targets = {}
        for c in conns:
            croad = roads[c['connecting']]
            lane = next((ln for sec in croad.find('lanes').findall('laneSection')[-1 if c['contact'] == 'start' else 0:][:1]
                         for side in ('left', 'right') if sec.find(side) is not None
                         for ln in sec.find(side).findall('lane') if int(ln.get('id')) == c['to']), None)
            lk = lane.find('link') if lane is not None else None
            nx = lk.find('successor' if c['contact'] == 'start' else 'predecessor') if lk is not None else None
            if nx is None:
                continue
            dh = heading_change_fixed(roads, c, jid)
            if dh is not None:
                targets.setdefault((c['outgoing'], int(nx.get('id'))), []).append({**c, 'dheading_deg': dh})
        for (out_road, out_lane), cs in sorted(targets.items()):
            main = [c for c in cs if abs(c['dheading_deg']) <= 10]
            branch = sorted((c for c in cs if 10 < abs(c['dheading_deg']) <= 45
                             or (wide and 45 < abs(c['dheading_deg']) <= 100 and c['dheading_deg'] < 0)),
                            key=lambda c: c['id'])
            if (len(main) != 1 or not branch
                    or any(signal_near_fixed(roads[c['incoming']], jid) for c in (main[0], branch[0]))):
                continue
            starts = [gen.geometries(roads[c['connecting']])[0] for c in cs]
            anchor = (sum(g['x'] for g in starts) / len(starts), sum(g['y'] for g in starts) / len(starts))
            if not far(town, [anchor]):
                continue
            rule = 'F2-2 right turn %.1f deg' % branch[0]['dheading_deg'] if abs(branch[0]['dheading_deg']) > 45 else 'R2'
            out.append({'town': town, 'junction': jid, 'outgoing': [out_road, out_lane], 'mainflow': main[0],
                        'branch': branch[0], 'anchor_carla': [anchor[0], -anchor[1]], 'rule': rule,
                        'xpath': f"/OpenDRIVE/junction[@id='{jid}']"})
            break
    return out


# -- F2-3 corridor chains / F2-4 uphill R3 --------------------------------------------------------------------------
def section_ok(town, road, gs, slope, s0, s1, lanes, inner, outer):
    samples = [gen.point(gs, s0 + i * 5.)[:2] for i in range(int((s1 - s0) // 5) + 1)]
    return (inner in lanes and outer in lanes and all(lanes[i].get('type') == 'driving' for i in (inner, outer))
            and gen.broken(lanes[inner]) and gen.width_ok(lanes[inner]) and gen.width_ok(lanes[outer])
            and gen.corridor_ok(gs, s0, s1, slope) and far(town, samples))


def lane_next(lane):
    lk = lane.find('link'); nx = lk.find('successor') if lk is not None else None
    return int(nx.get('id')) if nx is not None else int(lane.get('id'))


def chains(town):
    """Maximal R1 chains (F2-3). Each element: (road, section index, s0, s1, inner, outer)."""
    root, roads = town_tree(town)
    out = []
    for rid, road in sorted(roads.items()):
        if road.get('junction') != '-1' or (town, rid) in CURRENT_ROADS:
            continue
        secs = gen.sections(road); gs = gen.geometries(road); slope = gen.slope_profile(road)
        for sign in (-1, 1):
            for i0, s0, s1, lanes in secs:
                ids = sorted((i for i in lanes if i * sign > 0 and lanes[i].get('type') == 'driving'), key=abs)
                for inner, outer in zip(ids, ids[1:]):
                    if abs(outer) - abs(inner) != 1 or not section_ok(town, rid, gs, slope, s0, s1, lanes, inner, outer):
                        continue
                    # start only where the previous section does not continue this pair (maximal chains)
                    if i0 > 0:
                        _, p0, p1, plan = secs[i0 - 1]
                        prev = [(a, b) for a in plan for b in plan if lane_next(plan[a]) == inner and lane_next(plan[b]) == outer]
                        if any(section_ok(town, rid, gs, slope, p0, p1, plan, a, b) for a, b in prev):
                            continue
                    chain = [(rid, i0, s0, s1, inner, outer)]
                    cur_rid, cur_secs, idx, a, b = rid, secs, i0, inner, outer
                    while True:
                        na, nb = lane_next(cur_secs[idx][3][a]), lane_next(cur_secs[idx][3][b])
                        if idx + 1 < len(cur_secs):
                            idx += 1
                        else:  # road-road link, same orientation only
                            lk = roads[cur_rid].find('link'); sc = lk.find('successor') if lk is not None else None
                            if (sc is None or sc.get('elementType') != 'road' or sc.get('contactPoint') != 'start'
                                    or int(sc.get('elementId')) not in roads):
                                break
                            nrid = int(sc.get('elementId'))
                            if roads[nrid].get('junction') != '-1' or (town, nrid) in CURRENT_ROADS:
                                break
                            cur_rid, cur_secs, idx = nrid, gen.sections(roads[nrid]), 0
                        r = roads[cur_rid]; _, t0, t1, tl = cur_secs[idx]
                        if not section_ok(town, cur_rid, gen.geometries(r), gen.slope_profile(r), t0, t1, tl, na, nb):
                            break
                        chain.append((cur_rid, idx, t0, t1, na, nb)); a, b = na, nb
                        if len(chain) > 200:
                            break  # ponytail: loop guard for cyclic road links
                    out.append({'town': town, 'road': rid, 'section': i0, 'chain': chain,
                                'roads': sorted({c[0] for c in chain}),
                                'length': sum(c[3] - c[2] for c in chain), 'lanes': [inner, outer],
                                'travel': 'increasing s' if sign < 0 else 'decreasing s',
                                'rule': 'R1' if len(chain) == 1 else 'F2-3 chain of %d sections' % len(chain),
                                'xpath': [f"/OpenDRIVE/road[@id='{c[0]}']/lanes/laneSection[{c[1] + 1}]" for c in chain]})
    return out


def uphill(r3_entry, town):
    _, roads = town_tree(town)
    slope = gen.slope_profile(roads[r3_entry['road']])
    a, b, _ = r3_entry['grade_run']
    mid = slope((a + b) / 2)
    return (r3_entry['lane'] < 0 and mid > 0) or (r3_entry['lane'] > 0 and mid < 0)


def main(out_path, approved_commit):
    for town, h in gen.HASHES.items():
        assert hashlib.sha256((gen.ROOT / f'{town}.xodr').read_bytes()).hexdigest() == h, town
    prereg_hash = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    patch_fill20()
    pools = {}
    a = {'R1': [], 'R2': [], 'R3': []}
    for town in gen.HASHES:
        r1, r2, r3 = gen.scan(town); a['R1'] += r1; a['R2'] += r2; a['R3'] += r3
    b = {'R1': a['R1'], 'R2': [m for t in gen.HASHES for m in merges_v2(t, False)],
         'R3': [r for r in a['R3'] if uphill(r, r['town'])]}
    c = {**b, 'R2': [m for t in gen.HASHES for m in merges_v2(t, True)]}
    d = {**c, 'R1': [x for t in gen.HASHES for x in chains(t)]}
    for name, p in (('a_fill20', a), ('b_fixes', b), ('c_plus_F2-2', c), ('d_v2', d)):
        pools[name] = {k: len(v) for k, v in p.items()}
    key = lambda x: (x['town'], x.get('road', x.get('junction')), x.get('section', 0), str(x.get('lanes', x.get('lane', ''))))
    for k in d:
        d[k] = sorted(d[k], key=key)
    counts = dict(EXISTING); used_roads = set(); out = []
    cap_ok = lambda cat, town: counts.get((cat, town), 0) < 3
    free = lambda x: not any((x['town'], r) in used_roads for r in x.get('roads', [x.get('road')]))
    # I/O pairs: I06/O06 (k=5), I08/O08 (k=6)
    i_list = list(d['R1']); random.Random(SEED + 1).shuffle(i_list)
    for idx, k in (('06', 5), ('08', 6)):
        vE = gen.series(F(6), F(5, 4), k); gap = gen.series(F(6), F(13, 10), k); G = gen.series(F(15), F(13, 10), k)
        need_i = 7 * vE + 3.75 + vE * vE / (2 * gen.A) + gap + gen.MARGIN
        rs = max(3 * vE, vE * (G + 9.5) / (vE - 2.5))
        need_o = rs + 3 * vE + 3.75 + vE * vE / (2 * gen.A) + G + gen.MARGIN
        pick = next((x for x in i_list if free(x) and x['length'] >= max(need_i, need_o)
                     and cap_ok('I', x['town']) and cap_ok('O', x['town'])), None)
        for cat, params, need in (('I', {'k': k, 'vE': vE, 'vN': vE - 1, 'gap_m': gap}, need_i),
                                  ('O', {'k': k, 'vE': vE, 'vN': 2.5, 'G_m': G, 'returnstart_m': rs}, need_o)):
            entry = {'id': f'M56-P-{cat}{idx}', 'category': cat, 'parameters': params, 'required_length_m': need}
            if pick is None:
                entry['status'] = 'EMPTY_NO_ELIGIBLE_CANDIDATE'
            else:
                entry.update(status='PROPOSED', site=pick); counts[(cat, pick['town'])] = counts.get((cat, pick['town']), 0) + 1
            out.append(entry)
        if pick is not None:
            used_roads.update((pick['town'], r) for r in pick['roads'])
    # M02..M08
    m_list = list(d['R2']); random.Random(SEED + 3).shuffle(m_list); used_j = set()
    for j, k in zip(range(2, 9), (2, 3, 4, 5, 0, 6, -1)):
        vN = gen.series(F(3), F(5, 4), k); GL = gen.series(F(4), F(13, 10), k)
        pick = next((x for x in m_list if (x['town'], x['junction']) not in used_j and cap_ok('M', x['town'])
                     and x['mainflow']['incoming_length'] >= GL + 16 / (2 * gen.A) + gen.MARGIN
                     and x['branch']['incoming_length'] >= GL + vN * vN / (2 * gen.A) + gen.MARGIN), None)
        entry = {'id': f'M56-P-M{j:02d}', 'category': 'M', 'parameters': {'k': k, 'vN': vN, 'GL_m': GL, 'vE_mainflow': 4.0}}
        if pick is None:
            entry['status'] = 'EMPTY_NO_ELIGIBLE_CANDIDATE'
        else:
            entry.update(status='PROPOSED', site=pick); counts[('M', pick['town'])] = counts.get(('M', pick['town']), 0) + 1
            used_j.add((pick['town'], pick['junction']))
        out.append(entry)
    # F02, F03, F05, F06
    f_r1 = list(d['R1']); random.Random(SEED + 4).shuffle(f_r1)
    f_r3 = list(d['R3']); random.Random(SEED + 4).shuffle(f_r3)
    need_f = {'F02': 110, 'F05': 120, 'F06': 120}
    for mech in ('F02', 'F03', 'F05', 'F06'):
        entry = {'id': f'M56-P-{mech}', 'category': 'F', 'mechanism': 'F06-ALT1' if mech == 'F06' else mech,
                 'parameters': 'spec 8.1 approved inputs' if mech != 'F06' else 'spec 13 F06-ALT1 (approved by Duy 2026-10-22)'}
        if mech == 'F03':
            pick = next((x for x in f_r3 if (x['town'], x['road']) not in used_roads and cap_ok('F', x['town'])), None)
        else:
            pick = next((x for x in f_r1 if free(x) and x['length'] >= need_f[mech] and cap_ok('F', x['town'])), None)
        if pick is None:
            entry['status'] = 'EMPTY_NO_ELIGIBLE_CANDIDATE'
        else:
            entry.update(status='PROPOSED', site=pick); counts[('F', pick['town'])] = counts.get(('F', pick['town']), 0) + 1
            used_roads.update((pick['town'], r) for r in pick.get('roads', [pick['road']]))
        out.append(entry)
    for e in out:
        e.update(selector='CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT',
                 authority='Duy [chat] 2026-10-24 (self-stated identity); prereg approved at commit ' + approved_commit,
                 review='CLAUDE_REVIEW_UNDER_DUY_DELEGATION; independent review waived by Duy 2026-10-24',
                 prereg_sha256=prereg_hash, poses='PENDING_RUNTIME_QUERY', destination='PENDING_RUNTIME_QUERY',
                 weather_light='PENDING_RUNTIME_QUERY', npc_controller='NONE (not assigned by catalog)')
    report = {'prereg': str(PREREG), 'prereg_sha256': prereg_hash, 'approved_commit': approved_commit, 'seed': SEED,
              'xodr_sha256': gen.HASHES, 'pool_sizes': pools, 'resolutions': RESOLUTIONS,
              'category_town_counts_after': {f'{c}/{t}': n for (c, t), n in sorted(counts.items())},
              'filled': sum(e['status'] == 'PROPOSED' for e in out),
              'junctions_after': 17 + sum(e['status'] == 'PROPOSED' and e['category'] == 'M' for e in out), 'entries': out}
    data = (json.dumps(report, indent=1, sort_keys=True, default=str) + '\n').encode()
    with open(out_path, 'xb') as f:
        f.write(data)
    print(json.dumps({'filled': report['filled'], 'junctions_after': report['junctions_after'], 'pools': pools,
                      'sha256': hashlib.sha256(data).hexdigest()}))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
