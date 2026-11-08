"""A-SEL2 offline feasibility (2026-11-08), census only: C/L ladder under descriptors (vN, G, LrefN) KEEPING the
retained valid scenes, with junction-distinct sites and <= 3 per (category, town). Reads asel2-census pools.
usage: python -I asel2-ladder3b.py POOLS.json"""
import json, sys
from fractions import Fraction as F
sys.path.insert(0, 'D:/AI/CARLA-Funny-Moments.worktrees/m56-v9')
from m56.catalog import derive_g
pools = json.load(open(sys.argv[1], encoding='utf-8'))
VE = {'C': F(4), 'L': F(2)}; vN = lambda k: F(3) * F(5, 4) ** (k - 1)
RET = {'C': {1: ('Town04', F(26), F('21.96')), 5: ('Town05', F(33, 2), F('25.92')), 8: ('Town06', F(31, 2), F('47.88'))},
       'L': {1: ('Town04', F(11), F('18.77')), 4: ('Town05', F(9), F('30.13'))}}
far = lambda a, b: max(a, b) >= min(a, b) * F(5, 4)
for cat in 'CL':
    slots = [k for k in range(1, 9) if k not in RET[cat]]
    opts = {k: {} for k in slots}
    for t, j, l in pools[cat]:
        l = F(str(round(l, 6)))
        for k in slots:
            opts[k].setdefault((derive_g(VE[cat], vN(k), l), l), set()).add((t, j))
    fixed = [(g, l) for _, g, l in RET[cat].values()]
    towns0 = [t for t, _, _ in RET[cat].values()]
    order = sorted(slots, key=lambda k: len(opts[k])); sol = [None]
    def go(i, ch, used, towns):
        if sol[0]:
            return
        if i == len(order):
            sol[0] = list(ch); return
        k = order[i]
        for (g, l), sites in sorted(opts[k].items()):
            if not all(far(g, h) or far(l, m) for h, m in fixed + [(a, b) for a, b, _, _ in ch]):
                continue
            for t, j in sorted(sites):
                if (t, j) not in used and towns.count(t) < 3:
                    ch.append((g, l, t, j)); go(i + 1, ch, used | {(t, j)}, towns + [t]); ch.pop()
                    break
            if sol[0]:
                return
    pairs_ok = all(far(a[0], b[0]) or far(a[1], b[1]) for i, a in enumerate(fixed) for b in fixed[i + 1:])
    go(0, [], frozenset(), towns0)
    print(cat, 'retained pairwise ok', pairs_ok, 'feasible', sol[0] is not None,
          [(k, float(g), float(l), t, j) for k, (g, l, t, j) in zip(order, sol[0])] if sol[0] else None, flush=True)
