"""io-v1.6 2b forecast gate on a compiled I/O fixture: kappa_max = (10/sqrt 3) |offset| / Dlc^2 of the EGO lane change (O: A,
I: B) must be <= 0.0624 (O01, PASS). Exit 0 = pass, 3 = LANE_CHANGE_CURVATURE (no A/B).
  python -I asel2-io16-kappa-gate.py FIXTURE_DIR/<scene>"""
import json, math, sys
from fractions import Fraction
from pathlib import Path
LIMIT = 0.0624
fx = lambda v: float.fromhex(v['binary64']) if 'binary64' in v else float(Fraction(v['numerator'], v['denominator']))
fz = json.loads((Path(sys.argv[1]) / 'fixture-frozen.json').read_text(encoding='utf-8'))
cat = fz['domain']['topology']['category']
r = next(x for x in fz['responses'] if x['actor_role'] == 'EGO' and x['action_id'] == ('A' if cat == 'O' else 'B'))
s = next(x for x in r['profile']['segments'] if fx(x['end_offset_m']) != fx(x['start_offset_m']))
k = 10 / math.sqrt(3) * abs(fx(s['end_offset_m']) - fx(s['start_offset_m'])) / fx(s['length_m']) ** 2
print(json.dumps({'gate': 'io-v1.6 2b', 'kappa_max': k, 'dlc_m': fx(s['length_m']), 'limit': LIMIT, 'pass': k <= LIMIT}))
sys.exit(0 if k <= LIMIT else 3)
