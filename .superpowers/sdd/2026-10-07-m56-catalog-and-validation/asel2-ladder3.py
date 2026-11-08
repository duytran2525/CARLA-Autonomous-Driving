"""A-SEL2 offline feasibility (2026-11-08), census only: with THREE declared descriptors (vN, G, LrefN) a pair passes
when >= 2 of them differ by >= 20 %. vN always differs between distinct k, so each pair needs G OR LrefN ratio >= 5/4.
Reads the pools written by asel2-census.py. usage: python -I asel2-ladder3.py POOLS.json"""
import json, sys, itertools
from fractions import Fraction as F
sys.path.insert(0, 'D:/AI/CARLA-Funny-Moments.worktrees/m56-v9')
from m56.catalog import derive_g
pools = json.load(open(sys.argv[1], encoding='utf-8'))
VE = {'C': F(4), 'L': F(2)}; vN = lambda k: F(3) * F(5, 4) ** (k - 1)
far = lambda a, b: max(a, b) >= min(a, b) * F(5, 4)
for cat in 'CL':
    Ls = sorted({F(str(round(l, 6))) for _, _, l in pools[cat]})
    opts = {k: sorted({(derive_g(VE[cat], vN(k), l), l) for l in Ls}) for k in range(1, 9)}
    order = sorted(opts, key=lambda k: len(opts[k])); sol = [None]
    def go(i, ch):
        if sol[0] or i == len(order):
            sol[0] = sol[0] or list(ch); return
        for g, l in opts[order[i]]:
            if all(far(g, h) or far(l, m) for h, m in ch):
                ch.append((g, l)); go(i + 1, ch); ch.pop()
                if sol[0]: return
    go(0, [])
    print(cat, 'LrefN range', float(Ls[0]), float(Ls[-1]), 'feasible(G or LrefN)', sol[0] is not None,
          [(float(g), float(l)) for g, l in sol[0]] if sol[0] else None, flush=True)
