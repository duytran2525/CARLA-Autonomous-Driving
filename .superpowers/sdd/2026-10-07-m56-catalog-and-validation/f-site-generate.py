"""M56 A-SEL2 F site selection: PREREG_M56_F_ASEL2_20261109.md section 3 (part 1 mechanisms F01, F02, F05, F06; F03 and
F04' wait for part 2). Implementation notes (committed with this file, before the run): F_SITE_NOTES_20261109.md.
Selector disclosure: CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT. Deterministic pool (fill v4 R1 = fill v3 chains_v3), stable
key, one shuffle with the registered seed, first-fit per mechanism in slot order; every skip reason is counted.
  python -I f-site-generate.py OUT.json PREREG_COMMIT"""
import glob, hashlib, importlib.util, json, random, sys
from collections import Counter
from pathlib import Path

here = Path(__file__).resolve().parent
s_ = importlib.util.spec_from_file_location('fv4', here / 'fill-v4-generate.py')
G = importlib.util.module_from_spec(s_); s_.loader.exec_module(G)  # helpers only (main runs under __main__)
v2, v3, gen, cen = G.v2, G.v3, G.gen, G.cen

PREREG = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/docs/m56/PREREG_M56_F_ASEL2_20261109.md')
SEED = int(hashlib.sha256(b'M56-F-ASEL2-2026-11-09').hexdigest()[:16], 16)
MECH = {'F01': (120., 4.), 'F02': (110., 5.5), 'F05': (120., 2.), 'F06': (120., 0.)}  # (length m, run-in vE m/s)
DESC = {'F01': {'vN_char': '17/5', 'd0': '57/5'}, 'F02': {'vN_char': '5', 'd0': '20'},
        'F05': {'vN_char': '2', 'd0': '4'}, 'F06': {'vN_char': '1/2', 'd0': '34/5'}}
CAP, SLOPE = 3, .02
WORK = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1')


def fill_v4_sites():
    """Every site any fill v4 output (base + replacement rounds) proposed or queued: roads (I/O) and junctions (C/L/M)."""
    roads, jun = set(), set()
    for f in sorted(glob.glob(str(WORK / 'outputs/m56_fill_v4*_2026*.json'))):
        for e in json.loads(Path(f).read_text(encoding='utf-8')).get('entries', []):
            for x in [e.get('site')] + [q['site'] for q in e.get('queue', [])]:
                if not x:
                    continue
                if 'junction' in x:
                    jun.add((x['town'], x['junction']))
                roads.update((x['town'], r) for r in x.get('roads', ()))
                jun.update((x['town'], j) for j in x.get('junctions_crossed', ()))
    return roads, jun


def gates(x, length, vE):
    """Site section only (native-f-prepare builds both routes on one laneSection): length, axis run (B5), slope."""
    road = v2.trees[x['town']][1][x['road']]
    _, s0, s1, _ = gen.sections(road)[x['section']]
    need = length + vE ** 2 / 3 + 20.
    if s1 - s0 - 2. < need:  # prepare uses [section entry + 1 m, exit - 1 m]
        return 'SECTION_SHORT'
    first = x['chain'][0]
    if v3.axis_run(x['town'], [first]) < need:
        return 'B5_AXIS_RUN_SHORT'
    sl = gen.slope_profile(road)
    if any(abs(sl(s0 + i)) > SLOPE for i in range(int(s1 - s0) + 1)):
        return 'SLOPE_GT_002'
    return None


def main(out_path, commit):
    for t in G.TOWNS:
        assert hashlib.sha256(cen.xodr(t).read_bytes()).hexdigest() == G.HASHES[t], t
        cen.load(t)
    jun, used_roads = G.excluded_sets()
    f4_roads, f4_jun = fill_v4_sites()
    for t in G.TOWNS:
        v2.CURRENT_JUNCTIONS[t] = set(jun.get(t, ())) | {j for tt, j in f4_jun if tt == t}
    v2.CURRENT_ROADS = set(used_roads) | f4_roads
    for t in G.TOWNS:
        v2.ANCHORS[t] = v2.anchors(t)
    pool = []
    for t in G.TOWNS:
        pool += v3.chains_v3(t, set(), set(v2.CURRENT_ROADS))
    key = lambda x: (x['town'], json.dumps(x.get('roads'), sort_keys=True), str(x.get('lanes', '')), str(x.get('travel', '')),
                     x['road'], x['section'])
    pool = sorted(pool, key=key); random.Random(SEED).shuffle(pool)
    taken_roads, counts, entries = set(), Counter(), []
    for slot, (length, vE) in MECH.items():
        why, chosen = Counter(), None
        for x in pool:
            if any((x['town'], r) in v2.CURRENT_ROADS for r in x['roads']):
                why['EXCLUDED_ROAD'] += 1; continue
            if (x['town'], x['road']) in taken_roads:
                why['SITE_USED'] += 1; continue
            if counts[x['town']] >= CAP:
                why['TOWN_CAP'] += 1; continue
            w = gates(x, length, vE)
            if w:
                why[w] += 1; continue
            chosen = x; break
        entry = {'id': f'M56-P-{slot}', 'slot': slot, 'category': 'F', 'mechanism': slot, 'skipped': dict(why),
                 'required_m': length + vE ** 2 / 3 + 20.}
        if chosen is None:
            entry['status'] = 'EMPTY_NO_ELIGIBLE_CANDIDATE'
        else:
            site = {k: chosen[k] for k in ('town', 'road', 'section', 'lanes', 'travel', 'roads', 'junctions_crossed', 'rule')}
            entry.update(status='PROPOSED', rule='first_fit', site=site, descriptors=DESC[slot])
            taken_roads.add((chosen['town'], chosen['road'])); counts[chosen['town']] += 1
        entries.append(entry)
        print(json.dumps({'slot': slot, 'status': entry['status'], 'site': entry.get('site', {}).get('town'),
                          'road': entry.get('site', {}).get('road')}), flush=True)
    for e in entries:
        e.update(selector='CLAUDE_PREREG_ALGORITHM_NOT_INDEPENDENT',
                 authority='Duy [chat] 2026-11-08 A-SEL2 "Claude soạn recipe F" (self-stated identity); prereg commit ' + commit,
                 review='CLAUDE_REVIEW_UNDER_DUY_DELEGATION; independent review waived by Duy 2026-10-24')
    report = {'prereg': str(PREREG), 'prereg_sha256': hashlib.sha256(PREREG.read_bytes()).hexdigest(), 'prereg_commit': commit,
              'seed': SEED, 'xodr_sha256': G.HASHES, 'pool_size': len(pool), 'excluded_roads': sorted(v2.CURRENT_ROADS),
              'entries': entries}
    data = (json.dumps(report, indent=1, sort_keys=True, default=str) + '\n').encode()
    with open(out_path, 'xb') as f:
        f.write(data)
    print(json.dumps({'sha256': hashlib.sha256(data).hexdigest(), 'pool': len(pool),
                      'empty': [e['slot'] for e in entries if e['status'] != 'PROPOSED']}))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
