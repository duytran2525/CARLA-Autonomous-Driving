import json, math, sys
sys.path.insert(0, r'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/.superpowers/sdd/2026-10-07-m56-catalog-and-validation')
import xodr_routes as xr
from fractions import Fraction as F
d = json.load(open('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_c0_partial_20261022T120227Z/c0-partial-frozen-revision.json', encoding='utf-8'))
A = 1.5
def val(x): return F(x['numerator'], x['denominator'])
for c in d['candidates']:
    if c['category'] not in ('C', 'L'): continue
    p = {k: val(v['values'][0]) for k, v in c['parameters'].items()}
    vE = F(4) if c['category'] == 'C' else F(2)
    routes = {}
    for a in c['actors']:
        want = float(p['G'] + vE**2/(2*F(3,2)) + 20) if a['role']=='EGO' else float(p.get('LrefN', F(20)) + p['vN']**2/(2*F(3,2)) + 20)
        pts, arc, exit_arc, app, outl = xr.junction_route(c['town'], a['route_recipe']['route'], want, 15.)
        routes[a['role']] = (pts, arc)
    # first crossing of the two centre lines (lateral within 2.5 m = lanes overlap)
    (pe, ae), (pn, an) = routes['EGO'], routes['NPC']
    best = None
    for i, q in enumerate(pe):
        for j, r in enumerate(pn):
            dd = math.hypot(q[0]-r[0], q[1]-r[1])
            if dd < 2.5:
                best = (ae[i], an[j]); break
        if best: break
    if not best: print(c['id'], 'NO OVERLAP'); continue
    sE, sN = best
    vN = float(p['vN']); G = float(p['G'])
    # nominal times from rest (const accel A to v, then cruise); EGO release 1.05 s
    def t(s, v, delay):
        ta = v / A; sa = v*v/(2*A)
        return delay + (ta + (s - sa)/v if s > sa else math.sqrt(2*s/A))
    tE_conf = t(sE - 2.25, float(vE), 1.05)        # EGO front reaches conflict
    tE_trig = t(sE - 2.25 - G, float(vE), 1.05)
    tN_conf = t(sN - 2.25, vN, 0.0)
    want_N = tE_conf - (float(p.get('LrefN', 20)) + 5)/(2*vN)
    print(f"{c['id']} G={G} vN={vN:.3f} sE={sE:.1f} sN={sN:.1f} trig={tE_trig:.1f}s Ego@conf={tE_conf:.1f}s NPC@conf(no delay)={tN_conf:.1f}s wanted<= {want_N:.1f}s slack={want_N-tN_conf:+.1f}s")
