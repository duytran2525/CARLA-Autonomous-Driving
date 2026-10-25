"""Synthetic self-check of native-v2-prepare.npc_route_end (erratum 4): straight 100 m, then a 10 m-radius turn."""
import importlib.util, math, sys
from pathlib import Path
here = Path(__file__).resolve().parent
sys.argv = ['x', 'Town04']
src = (here / 'native-v2-prepare.py').read_text(encoding='utf-8')
ns = {}
start = src.index('def npc_route_end'); end = src.index('def min_station')
exec('import math\nfrom fractions import Fraction as F\n' + src[start:end], ns)
rows, arc = [], []
for i in range(800):  # 0.25 m steps (200 m); yaw turns at 0.25/10 rad per step after 100 m
    s = i * .25; yaw = 0. if s <= 100 else math.degrees((s - 100) / 10.)
    rows.append({'x': s, 'y': 0., 'z': 0., 'pitch': 0., 'yaw': yaw, 'roll': 0.}); arc.append(s)
e = ns['npc_route_end']((rows, arc), 120, 3.0)  # dest = 30 + 5 = 35 m; 9 * 0.1 = 0.9 < 2.5: no cut
assert e['cut_index'] is None, e
e = ns['npc_route_end']((rows, arc), 120, 6.0)  # 36 * 0.1 = 3.6 > 2.5 from s* ~100.25 -> end 89.25
assert abs(e['curve_station_m'] - 100.25) < .3 and abs(e['route_end_m'] - 89.25) < .3, e
e = ns['npc_route_end']((rows, arc), 360, 6.0)  # dest 95 m: end 89 < 100 -> blocked
assert e.get('reason') == 'NPC_ROUTE_CURVATURE', e
print('erratum4 selfcheck OK')
