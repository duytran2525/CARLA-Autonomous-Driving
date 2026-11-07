import glob, json, math, os
from fractions import Fraction as F

O = 'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'
series = {k: 3 * (5 / 4) ** (k - 1) for k in range(-4, 12)}
for s in ('C03', 'L05', 'L06', 'M03', 'M05'):
    cands = sorted(glob.glob(f'{O}/m56_v2_prepare_*/M56-P-{s}/prepare.json'), key=os.path.getmtime)
    if not cands:
        print(s, 'no prep'); continue
    d = os.path.dirname(cands[-1]); p = json.load(open(cands[-1], encoding='utf-8'))
    rf = p.get('routes_v2') or next(iter(glob.glob(d + '/routes*.json')), None)
    r = json.load(open(rf, encoding='utf-8'))
    rows = r['NPC'] if 'NPC' in r else r['routes']['NPC']
    num = lambda x: float.fromhex(x['binary64']) if isinstance(x, dict) and 'binary64' in x else (
        x['numerator'] / x['denominator'] if isinstance(x, dict) else float(x))
    xy = [(num(row['x']), num(row['y']), num(row['yaw'])) for row in rows]
    arc = [0.]
    for a, b in zip(xy, xy[1:]):
        arc.append(arc[-1] + math.dist(a[:2], b[:2]))
    k = [abs(math.radians((xy[i + 1][2] - xy[i - 1][2] + 180) % 360 - 180)) / (arc[i + 1] - arc[i - 1]) for i in range(1, len(xy) - 1)]
    kmax = max(k); vmax = math.sqrt(2.25 / kmax)
    vn = p.get('geometry', {}).get('vN') or p.get('vN')
    ok = [(kk, v) for kk, v in series.items() if v <= vmax]
    best = max(ok, key=lambda t: t[1]) if ok else None
    print(f'{s}: kappa_max {kmax:.4f} 1/m (radius {1/kmax:.1f} m) -> vN_max {vmax:.3f} m/s; series best k={best[0]} vN={best[1]:.4f}'
          if best else f'{s}: none', '| prep', os.path.basename(os.path.dirname(d)))
