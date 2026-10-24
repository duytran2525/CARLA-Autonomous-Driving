"""Census + deterministic assignment for the 7 slots left empty by fill v2, implementing
docs/m56/PREREG_M56_FILL_V3_20261024.md. Reuses fill20-generate.py / fill-v2-generate.py; only F3-0..F3-2 differ.
The 8 fill-v2 picks (outputs/m56_fill_v2_20261024T152517Z.json) are fixed and excluded like the 31 C0 scenes.
Selector disclosure: CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT. Run ONLY after Duy approved the prereg commit:
python -I fill-v3-generate.py OUT.json APPROVED_PREREG_COMMIT"""
from fractions import Fraction as F
from pathlib import Path
import hashlib, importlib.util, json, math, random, sys

here = Path(__file__).parent
spec = importlib.util.spec_from_file_location('v2', here / 'fill-v2-generate.py'); v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)
gen = v2.gen
PREREG = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/docs/m56/PREREG_M56_FILL_V3_20261024.md')
V2_OUT = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_fill_v2_20261024T152517Z.json')
V2_SHA = '46bc88b78da36b83bf29a94663eeb359c1657a741147c5c2c75a60691a8c1e74'
SEED = int(hashlib.sha256(b'M56-FILL-V3-PREREG-2026-10-24').hexdigest()[:16], 16)
K_FALLBACK = {'IO': (-2, 7, -3, 8, -4), 'M': (7, -2, 8, -3, 9)}  # F3-2, fixed order after the registered k
RESOLUTIONS = v2.RESOLUTIONS + [
    'F3-1 chains follow the travel direction: negative lanes walk increasing s (exit at the road end), positive lanes '
    'decreasing s (exit at the road start); lane links successor/predecessor are read in road s-direction.',
    'F3-1 junction crossing: exactly one connection of the exit junction whose incoming road is the current road maps '
    'both corridor lanes, its connecting road satisfies the R1 geometry/slope/width rules, the heading change from the '
    'current road exit to the next road entry is <= 2 deg, the current road has no dynamic signal within 50 m of that '
    'junction, the junction is not excluded, and the next road is an ordinary road; the broken-mark rule does not apply '
    'inside the junction. Otherwise the chain stops.',
    'Maximal chains: chains whose element sequence is a proper suffix of another chain are dropped.',
    'F3-0 axis stretch: headings sampled every 1 m over the non-junction sections in travel order; a run keeps every '
    'heading within 1 deg of one world axis and total variation <= 1 deg; junction elements break a run.',
    'Junctions crossed by a picked corridor are excluded for later picks (and vice versa for picked M junctions).',
]


def load_v2():
    data = V2_OUT.read_bytes()
    assert hashlib.sha256(data).hexdigest() == V2_SHA, 'fill v2 output changed'
    d = json.loads(data)
    picks = [e for e in d['entries'] if e['status'] == 'PROPOSED']
    counts = dict(v2.EXISTING)
    for e in picks:
        counts[(e['category'], e['site']['town'])] = counts.get((e['category'], e['site']['town']), 0) + 1
    used_j = {(e['site']['town'], e['site']['junction']) for e in picks if e['category'] == 'M'}
    used_r = {(e['site']['town'], r) for e in picks if e['category'] == 'F' for r in e['site'].get('roads', [e['site'].get('road')])}
    return d, picks, counts, used_j, used_r


def lanes_of(section_node):
    out = {}
    for side in ('left', 'right'):
        node = section_node.find(side)
        for ln in (node.findall('lane') if node is not None else ()):
            out[int(ln.get('id'))] = ln
    return out


def forward_link(lane, forward_increasing):
    lk = lane.find('link')
    nx = lk.find('successor' if forward_increasing else 'predecessor') if lk is not None else None
    return int(nx.get('id')) if nx is not None else None


def chains_v3(town, excluded_j, excluded_r):
    """F2-3 chains extended by F3-1 (straight junction crossings), travel-direction aware."""
    root, roads = v2.town_tree(town)
    junctions = {int(j.get('id')): j for j in root.findall('junction')}
    out = []

    def sec_ok(rid, idx, a, b):
        road = roads[rid]; secs = gen.sections(road)
        _, s0, s1, lanes = secs[idx]
        inner, outer = (a, b) if abs(a) < abs(b) else (b, a)
        return (abs(outer) - abs(inner) == 1 and inner * outer > 0 and
                v2.section_ok(town, rid, gen.geometries(road), gen.slope_profile(road), s0, s1, lanes, inner, outer))

    def cross(rid, a, b, inc):
        """From road rid (lanes a, b, travel increasing s if inc) into the junction at its exit end."""
        road = roads[rid]; link = road.find('link')
        e = link.find('successor' if inc else 'predecessor') if link is not None else None
        if e is None or e.get('elementType') != 'junction':
            return None
        jid = int(e.get('elementId'))
        if jid not in junctions or (town, jid) in excluded_j or jid in v2.CURRENT_JUNCTIONS[town]:
            return None
        if v2.signal_near_fixed(road, jid):
            return None
        hits = []
        for c in junctions[jid].findall('connection'):
            if int(c.get('incomingRoad')) != rid or int(c.get('connectingRoad')) not in roads:
                continue
            ll = {int(x.get('from')): int(x.get('to')) for x in c.findall('laneLink')}
            if a not in ll or b not in ll:
                continue
            con = roads[int(c.get('connectingRoad'))]; cinc = c.get('contactPoint') == 'start'
            gs = gen.geometries(con); L = float(con.get('length'))
            secs = con.find('lanes').findall('laneSection')
            sec = secs[-1] if cinc else secs[0]
            cl = lanes_of(sec)
            if ll[a] not in cl or ll[b] not in cl or not all(gen.width_ok(cl[x]) for x in (ll[a], ll[b])):
                continue
            if not gen.corridor_ok(gs, 0., L, gen.slope_profile(con)):
                continue
            samples = [gen.point(gs, i * 5.)[:2] for i in range(int(L // 5) + 1)]
            if not v2.far(town, samples):
                continue
            na, nb = forward_link(cl[ll[a]], cinc), forward_link(cl[ll[b]], cinc)
            clink = con.find('link'); nx = clink.find('successor' if cinc else 'predecessor') if clink is not None else None
            if na is None or nb is None or nx is None or nx.get('elementType') != 'road':
                continue
            nrid = int(nx.get('elementId'))
            if nrid not in roads or roads[nrid].get('junction') != '-1' or (town, nrid) in v2.CURRENT_ROADS | excluded_r:
                continue
            ninc = nx.get('contactPoint') == 'start'
            h_out = gen.end_heading(gen.geometries(road), inc)
            h_in = gen.end_heading(gen.geometries(roads[nrid]), not ninc)
            if h_out is None or h_in is None:
                continue
            if not inc:
                h_out += math.pi
            if not ninc:
                h_in += math.pi
            if abs(math.degrees((h_in - h_out + math.pi) % (2 * math.pi) - math.pi)) > 2.:
                continue
            hits.append((jid, int(c.get('connectingRoad')), L, nrid, ninc, na, nb))
        return hits[0] if len(hits) == 1 else None

    for rid, road in sorted(roads.items()):
        if road.get('junction') != '-1' or (town, rid) in v2.CURRENT_ROADS | excluded_r:
            continue
        secs = gen.sections(road)
        for sign in (-1, 1):
            for i0, s0, s1, lanes in secs:
                ids = sorted((i for i in lanes if i * sign > 0 and lanes[i].get('type') == 'driving'), key=abs)
                for inner, outer in zip(ids, ids[1:]):
                    if not sec_ok(rid, i0, inner, outer):
                        continue
                    chain = [('S', rid, i0, s0, s1, inner, outer)]; crossed = []
                    cur, idx, a, b = rid, i0, inner, outer
                    inc = sign < 0
                    seen = {(rid, i0)}
                    while len(chain) < 200:
                        csecs = gen.sections(roads[cur]); lanes_now = csecs[idx][3]
                        na, nb = forward_link(lanes_now[a], inc), forward_link(lanes_now[b], inc)
                        nidx = idx + 1 if inc else idx - 1
                        if 0 <= nidx < len(csecs):
                            if na is None or nb is None or not sec_ok(cur, nidx, na, nb) or (cur, nidx) in seen:
                                break
                            idx, a, b = nidx, na, nb
                        else:
                            lk = roads[cur].find('link'); e = lk.find('successor' if inc else 'predecessor') if lk is not None else None
                            if e is not None and e.get('elementType') == 'road':
                                nrid = int(e.get('elementId'))
                                if (nrid not in roads or roads[nrid].get('junction') != '-1' or na is None or nb is None
                                        or (town, nrid) in v2.CURRENT_ROADS | excluded_r):
                                    break
                                ninc = e.get('contactPoint') == 'start'
                            else:
                                hop = cross(cur, a, b, inc)
                                if hop is None:
                                    break
                                jid, con, L, nrid, ninc, na, nb = hop
                                chain.append(('J', jid, con, 0., L, None, None)); crossed.append(jid)
                            nsecs = gen.sections(roads[nrid]); nidx = 0 if ninc else len(nsecs) - 1
                            if (nrid, nidx) in seen or not sec_ok(nrid, nidx, na, nb):
                                if chain[-1][0] == 'J':
                                    chain.pop(); crossed.pop()
                                break
                            cur, idx, a, b, inc = nrid, nidx, na, nb, ninc
                        seen.add((cur, idx))
                        _, t0, t1, _ = gen.sections(roads[cur])[idx]
                        chain.append(('S', cur, idx, t0, t1, a, b))
                    out.append({'town': town, 'road': rid, 'section': i0, 'chain': chain, 'junctions_crossed': crossed,
                                'roads': sorted({c[1] for c in chain if c[0] == 'S'}),
                                'length': sum(c[4] - c[3] for c in chain), 'lanes': [inner, outer],
                                'travel': 'increasing s' if sign < 0 else 'decreasing s',
                                'rule': 'R1' if len(chain) == 1 else ('F3-1 via junctions %s' % crossed if crossed else 'F2-3'),
                                'axis_run_m': axis_run(town, chain)})
    keys = [tuple(x['chain']) for x in out]
    def suffix(k):
        return any(len(o) > len(k) and o[len(o) - len(k):] == k for o in keys)
    return [x for x, k in zip(out, keys) if not suffix(k)]


def axis_run(town, chain):
    """F3-0: longest stretch (m) of non-junction sections whose headings stay within 1 deg of one world axis with total
    variation <= 1 deg, sampled every 1 m in chain order."""
    _, roads = v2.town_tree(town)
    best = run = 0.; prev = None; axis = None; var = 0.
    for kind, rid, idx, s0, s1, a, b in chain:
        if kind == 'J':
            run, prev, axis, var = 0., None, None, 0.; continue
        gs = gen.geometries(roads[rid]); n = max(1, int(s1 - s0))
        step = (s1 - s0) / n
        for i in range(n + 1):
            h = math.degrees(gen.point(gs, s0 + i * step)[2]) % 90.
            dev = min(h, 90. - h)
            near = round(math.degrees(gen.point(gs, s0 + i * step)[2]) / 90.) % 2  # axis line: x or y
            if dev > 1. or (axis is not None and near != axis):
                run, prev, axis, var = 0., None, None, 0.; continue
            if prev is not None:
                var += abs((h - prev + 45.) % 90. - 45.)
                if var > 1.:
                    run, var = 0., 0.
                else:
                    run += step
            axis, prev = near, h
            best = max(best, run)
    return best


def main(out_path, approved_commit):
    for town, h in gen.HASHES.items():
        assert hashlib.sha256((gen.ROOT / f'{town}.xodr').read_bytes()).hexdigest() == h, town
    prereg_hash = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    d2, picks, counts, used_j, used_r = load_v2()
    for e in picks:  # F3: the 30 m zone also covers the fill-v2 M junctions
        if e['category'] == 'M':
            x, y = e['site']['anchor_carla']; v2.ANCHORS[e['site']['town']].append((x, -y))
    v3_r1 = [x for t in gen.HASHES for x in chains_v3(t, used_j, used_r)]
    v2_r1 = [x for t in gen.HASHES for x in v2.chains(t)]
    m_pool = [x for t in gen.HASHES for x in v2.merges_v2(t, True) if (x['town'], x['junction']) not in used_j]
    key = lambda x: (x['town'], x.get('road', x.get('junction')), x.get('section', 0), str(x.get('lanes', '')), x.get('travel', ''))
    v3_r1.sort(key=key); m_pool.sort(key=key)
    cap_ok = lambda cat, town: counts.get((cat, town), 0) < 3
    used_roads = set(used_r); out = []
    free = lambda x: (not any((x['town'], r) in used_roads for r in x['roads'])
                      and not any((x['town'], j) in used_j for j in x.get('junctions_crossed', ())))
    used_k = {'I': {1, 2, 3, 4, 0, -1}, 'O': {1, 2, 3, 4, 0, -1}, 'M': {1, 2, 3, 4, 5, 0, -1}}

    def take(x):
        used_roads.update((x['town'], r) for r in x['roads'])
        used_j.update((x['town'], j) for j in x.get('junctions_crossed', ()))
    i_list = list(v3_r1); random.Random(SEED + 1).shuffle(i_list)
    for idx, k0 in (('06', 5), ('08', 6)):
        pick = None; tried = []
        for k in (k0, *K_FALLBACK['IO']):
            if k in used_k['I'] or k in used_k['O']:
                continue
            vE = gen.series(F(6), F(5, 4), k)
            if not vE > 3:
                tried.append({'k': k, 'reason': 'O needs vE > 3'}); continue
            gap = gen.series(F(6), F(13, 10), k); G = gen.series(F(15), F(13, 10), k)
            need_i = 7 * vE + 3.75 + vE * vE / (2 * gen.A) + gap + gen.MARGIN
            rs = max(3 * vE, vE * (G + 9.5) / (vE - 2.5))
            need_o = rs + 3 * vE + 3.75 + vE * vE / (2 * gen.A) + G + gen.MARGIN
            need_axis = max(3 * vE, rs + 3 * vE)  # F3-0 (C3 erratum 1): every lane-change segment on one axis stretch
            pick = next((x for x in i_list if free(x) and x['length'] >= max(need_i, need_o) and x['axis_run_m'] >= need_axis
                         and cap_ok('I', x['town']) and cap_ok('O', x['town'])), None)
            tried.append({'k': k, 'need_m': max(need_i, need_o), 'need_axis_m': need_axis, 'found': pick is not None})
            if pick is not None:
                break
        for cat in ('I', 'O'):
            entry = {'id': f'M56-P-{cat}{idx}', 'category': cat, 'k_tried': tried}
            if pick is None:
                entry['status'] = 'EMPTY_NO_ELIGIBLE_CANDIDATE'
            else:
                params = ({'k': k, 'vE': vE, 'vN': vE - 1, 'gap_m': gap} if cat == 'I'
                          else {'k': k, 'vE': vE, 'vN': 2.5, 'G_m': G, 'returnstart_m': rs})
                entry.update(status='PROPOSED', site=pick, parameters=params,
                             k_rule='registered' if k == k0 else 'F3-2 fallback from k=%d' % k0,
                             required_length_m=need_i if cat == 'I' else need_o, required_axis_run_m=need_axis)
                counts[(cat, pick['town'])] = counts.get((cat, pick['town']), 0) + 1
                used_k[cat].add(k)
            out.append(entry)
        if pick is not None:
            take(pick)
    # M07
    m_list = list(m_pool); random.Random(SEED + 3).shuffle(m_list)
    pick = None; tried = []
    for k in (6, *K_FALLBACK['M']):
        if k in used_k['M']:
            continue
        vN = gen.series(F(3), F(5, 4), k); GL = gen.series(F(4), F(13, 10), k)
        pick = next((x for x in m_list if (x['town'], x['junction']) not in used_j and cap_ok('M', x['town'])
                     and x['mainflow']['incoming_length'] >= GL + 16 / (2 * gen.A) + gen.MARGIN
                     and x['branch']['incoming_length'] >= GL + vN * vN / (2 * gen.A) + gen.MARGIN), None)
        tried.append({'k': k, 'found': pick is not None})
        if pick is not None:
            break
    entry = {'id': 'M56-P-M07', 'category': 'M', 'k_tried': tried}
    if pick is None:
        entry['status'] = 'EMPTY_NO_ELIGIBLE_CANDIDATE'
    else:
        entry.update(status='PROPOSED', site=pick, parameters={'k': k, 'vN': vN, 'GL_m': GL, 'vE_mainflow': 4.0},
                     k_rule='registered' if k == 6 else 'F3-2 fallback from k=6')
        counts[('M', pick['town'])] = counts.get(('M', pick['town']), 0) + 1
        used_j.add((pick['town'], pick['junction']))
    out.append(entry)
    # F05, F06
    f_r1 = list(v3_r1); random.Random(SEED + 4).shuffle(f_r1)
    for mech in ('F05', 'F06'):
        entry = {'id': f'M56-P-{mech}', 'category': 'F', 'mechanism': 'F06-ALT1' if mech == 'F06' else mech,
                 'parameters': 'spec 8.1 approved inputs' if mech != 'F06' else 'spec 13 F06-ALT1 (approved by Duy 2026-10-22)'}
        pick = next((x for x in f_r1 if free(x) and x['length'] >= 120 and cap_ok('F', x['town'])), None)
        if pick is None:
            entry['status'] = 'EMPTY_NO_ELIGIBLE_CANDIDATE'
        else:
            entry.update(status='PROPOSED', site=pick); counts[('F', pick['town'])] = counts.get(('F', pick['town']), 0) + 1
            take(pick)
        out.append(entry)
    for e in out:
        e.update(selector='CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT',
                 authority='Duy [chat] 2026-10-24 (self-stated identity); prereg approved at commit ' + approved_commit,
                 review='CLAUDE_REVIEW_UNDER_DUY_DELEGATION; independent review waived by Duy 2026-10-24',
                 prereg_sha256=prereg_hash, poses='PENDING_RUNTIME_QUERY', destination='PENDING_RUNTIME_QUERY',
                 weather_light='PENDING_RUNTIME_QUERY', npc_controller='NONE (not assigned by catalog)')
    pools = {'R1_v2_rule': len(v2_r1), 'R1_v3_rule': len(v3_r1),
             'R1_v3_with_junction_crossing': sum(bool(x['junctions_crossed']) for x in v3_r1),
             'R1_v3_max_length_m': max((x['length'] for x in v3_r1), default=0),
             'R1_v3_max_axis_run_m': max((x['axis_run_m'] for x in v3_r1), default=0), 'R2_remaining': len(m_pool)}
    filled = sum(e['status'] == 'PROPOSED' for e in out)
    report = {'prereg': str(PREREG), 'prereg_sha256': prereg_hash, 'approved_commit': approved_commit, 'seed': SEED,
              'fill_v2_output_sha256': V2_SHA, 'xodr_sha256': gen.HASHES, 'pool_sizes': pools, 'resolutions': RESOLUTIONS,
              'category_town_counts_after': {f'{c}/{t}': n for (c, t), n in sorted(counts.items())},
              'filled': filled, 'catalog_after': 39 + filled,
              'junctions_after': 23 + sum(e['status'] == 'PROPOSED' and e['category'] == 'M' for e in out), 'entries': out}
    data = (json.dumps(report, indent=1, sort_keys=True, default=str) + '\n').encode()
    with open(out_path, 'xb') as f:
        f.write(data)
    print(json.dumps({'filled': filled, 'catalog_after': report['catalog_after'], 'junctions_after': report['junctions_after'],
                      'pools': pools, 'sha256': hashlib.sha256(data).hexdigest()}))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
