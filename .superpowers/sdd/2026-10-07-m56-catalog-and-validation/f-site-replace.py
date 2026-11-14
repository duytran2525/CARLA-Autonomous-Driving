"""M56 A-SEL2 F B3 replacement site (2026-11-14; PREREG_M56_F_ASEL2_ADDENDUM_F01V2_20261114.md). Same registered algorithm
as f-site-generate.py (pool, stable key, seed, gates, town cap), run for ONE slot: the next first-fit after every site the
original run took (they stay taken and count toward the town cap). The other entries are copied byte-for-byte, so their
candidates do not change. The replaced entry gets candidate_id / replaces / descriptors from the addendum.
  python -I f-site-replace.py SITES_IN.json SLOT CANDIDATE_ID D0 OUT.json ADDENDUM_COMMIT [NEED_M]
NEED_M (addendum F01-v3, 2026-11-14): the site length/axis need in metres replaces length + vE^2/3 + 20 for this slot;
prepare's F_WINDOW_TOO_SHORT stays the exact gate."""
import hashlib, importlib.util, json, random, sys
from collections import Counter
from pathlib import Path

here = Path(__file__).resolve().parent
s_ = importlib.util.spec_from_file_location('fsg', here / 'f-site-generate.py')
S = importlib.util.module_from_spec(s_); s_.loader.exec_module(S)  # main only runs under __main__
G, v2, v3, cen = S.G, S.v2, S.v3, S.cen


def main(src, slot, cid, d0, out_path, commit, need_m=None):
    old = json.loads(Path(src).read_text(encoding='utf-8'))
    for t in G.TOWNS:
        assert hashlib.sha256(cen.xodr(t).read_bytes()).hexdigest() == G.HASHES[t], t
        cen.load(t)
    jun, used_roads = G.excluded_sets()
    f4_roads, f4_jun = S.fill_v4_sites()
    for t in G.TOWNS:
        v2.CURRENT_JUNCTIONS[t] = set(jun.get(t, ())) | {j for tt, j in f4_jun if tt == t}
    now_roads = set(used_roads) | f4_roads  # every road any fill v4 output uses TODAY (later rounds included)
    # the pool and its order are rebuilt with the ORIGINAL run's exclusions (same order as 11/09); today's are skipped below
    v2.CURRENT_ROADS = {tuple(r) for r in old['excluded_roads']}
    for t in G.TOWNS:
        v2.ANCHORS[t] = v2.anchors(t)
    pool = []
    for t in G.TOWNS:
        pool += v3.chains_v3(t, set(), set(v2.CURRENT_ROADS))
    v2.CURRENT_ROADS = v2.CURRENT_ROADS | now_roads
    key = lambda x: (x['town'], json.dumps(x.get('roads'), sort_keys=True), str(x.get('lanes', '')), str(x.get('travel', '')),
                     x['road'], x['section'])
    pool = sorted(pool, key=key); random.Random(S.SEED).shuffle(pool)
    assert len(pool) == old['pool_size'], ('POOL_CHANGED', len(pool), old['pool_size'])
    taken = {(e['site']['town'], e['site']['road']) for e in old['entries'] if e.get('site')}
    counts = Counter(t for t, _ in taken)
    length, vE = S.MECH[slot]
    if need_m is not None:  # S.gates needs length + vE^2/3 + 20; solve for the length term so need == NEED_M exactly
        length = float(need_m) - vE ** 2 / 3 - 20.
    why, chosen = Counter(), None
    for x in pool:
        if any((x['town'], r) in v2.CURRENT_ROADS for r in x['roads']):
            why['EXCLUDED_ROAD'] += 1; continue
        if (x['town'], x['road']) in taken:
            why['SITE_USED'] += 1; continue
        if counts[x['town']] >= S.CAP:
            why['TOWN_CAP'] += 1; continue
        w = S.gates(x, length, vE)
        if w:
            why[w] += 1; continue
        chosen = x; break
    entries = []
    for e in old['entries']:
        if e['slot'] != slot:
            entries.append(e); continue
        n = dict(e, skipped=dict(why), candidate_id=cid, replaces=f'M56-P-{slot}-S1',
                 descriptors={**e['descriptors'], 'd0': d0}, replacement='B3 (addendum ' + commit + ')',
                 site_need_m=None if need_m is None else str(need_m))
        if chosen is None:
            n.update(status='EMPTY_NO_ELIGIBLE_CANDIDATE'); n.pop('site', None)
        else:
            n['site'] = {k: chosen[k] for k in ('town', 'road', 'section', 'lanes', 'travel', 'roads', 'junctions_crossed', 'rule')}
        entries.append(n)
        print(json.dumps({'slot': slot, 'status': n['status'], 'site': n.get('site', {}).get('town'),
                          'road': n.get('site', {}).get('road'), 'skipped': dict(why)}), flush=True)
    report = dict(old, entries=entries, replacement_of=str(src), replacement_commit=commit)
    data = (json.dumps(report, indent=1, sort_keys=True, default=str) + '\n').encode()
    with open(out_path, 'xb') as f:
        f.write(data)
    print(json.dumps({'sha256': hashlib.sha256(data).hexdigest()}))


if __name__ == '__main__':
    main(*sys.argv[1:8])
