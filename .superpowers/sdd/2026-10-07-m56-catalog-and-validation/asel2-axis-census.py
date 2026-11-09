"""A-SEL2 census only (2026-11-09): how many C/L/M pool options (fill v4 rules, chained run-in) have both incoming
travel headings within TOL deg of a world axis at the conflict junction (the tooling's conflict region / sections are
axis-aligned boxes; a diagonal NPC leaves the n_exit section laterally before clearing it, Town12 batch 1 C03-S1).
Reports per (category, town) for TOL = 1, 3, 5 deg. usage: python -I asel2-axis-census.py STATE.json"""
import importlib.util, json, sys
from collections import Counter
from pathlib import Path
here = Path(__file__).resolve().parent
s = importlib.util.spec_from_file_location('g4', here / 'fill-v4-generate.py'); g = importlib.util.module_from_spec(s); s.loader.exec_module(g)
st = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
g.CHAIN['on'] = bool(st.get('chain'))
for t in g.TOWNS:
    g.cen.load(t)
jun, used_roads = g.excluded_sets()
for t in g.TOWNS:
    g.v2.CURRENT_JUNCTIONS[t] = set(jun.get(t, ()))
g.v2.CURRENT_ROADS = set(used_roads)
for t in g.TOWNS:
    g.v2.ANCHORS[t] = g.v2.anchors(t)
dev = lambda h: min(abs(((h - a + 180) % 360) - 180) for a in (0, 90, 180, 270))
res = {tol: Counter() for tol in (1, 3, 5)}; total = Counter()
for t in g.TOWNS:
    skips = {c: Counter() for c in 'CLMIO'}
    p = g.cl_pool(t, {k: v for k, v in jun.items()}, skips)
    for cat in 'CLM':
        for x in p[cat]:
            total[(cat, t)] += 1
            e, n = x['ego'], x['npc']
            he, hn = e.get('h_in'), n.get('h_in')
            if he is None or hn is None:
                import math
                roads = g.v2.trees[t][1]
                he = he if he is not None else g.cen.h_in(roads, e, x['junction'])
                hn = hn if hn is not None else g.cen.h_in(roads, n, x['junction'])
            for tol in res:
                if he is not None and hn is not None and dev(he) <= tol and dev(hn) <= tol:
                    res[tol][(cat, t)] += 1
    print(t, {c: (total[(c, t)], res[1][(c, t)], res[3][(c, t)], res[5][(c, t)]) for c in 'CLM'}, flush=True)
print('TOTAL (all, <=1, <=3, <=5 deg):', {c: (sum(v for (cc, _), v in total.items() if cc == c),
      *(sum(v for (cc, _), v in res[tol].items() if cc == c) for tol in (1, 3, 5))) for c in 'CLM'})
