"""Offline self-check of a compiled I/O (O) fixture (native-io-ab.py output), no server. Asserts:
  1. EGO A desired offsets: 0 before the lane change, +separation at its end, 0 after the return, on the frozen references
     (initial profile; TARGET switch on the target-lane route; HOME switch) - consumer desired_offset/_reference_response;
  2. reference lateral acceleration v_nominal^2 * profile_kappa <= 2.5 m/s^2 (consumer REFERENCE_LATERAL_BUDGET) with the
     kit's own profile_kappa at the lane-change midpoints; 0 for EGO B and the NPC;
  3. sections in order on the EGO route: O_DECISION < O_RETURN_START < X < DESTINATION < plan end - 5 m;
  4. return slack: earliest RETURN_CLEAR_CONFIRMED (rear gap >= 0.5 m held 0.25 s) before the vehicle centre reaches
     the fixed return-segment start, from the probe-2 plateaus and the realised gap at t0 (kinematic estimate, NOT evidence);
  5. X slack (reported): time from the end of the return segment to X_END.
  python -I native-io-selfcheck.py SCENE_DIR (holding fixture-frozen.json)   [M56_CODE = the consumer under test]
"""
import json, sys
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import WORK  # noqa: E402,F401  (puts M56_CODE first on sys.path)
from native_v2_kit import profile_kappa  # noqa: E402
from m56.model import decode_record, load_json  # noqa: E402
from m56.response import desired_offset, _reference_response, _program  # noqa: E402

sd = Path(sys.argv[1])
fx = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
a = next(r for r in fx.responses if r.actor_role == 'EGO' and r.action_id == 'A')
sep = fx.domain.topology['lane_geometry']['EGO']['separation_m']
seg = a.profile['segments'][0]; begin, L = seg['start_arc_m'], seg['length_m']
sw = a.phases['reference_switches']; ret = sw[0]['profile']['segments'][0]['start_arc_m']
ref = {c: _reference_response(a, c) for c in (_program(a)['initial'], *(t['cause'] for t in _program(a)['transitions']))}
assert desired_offset(begin - 1, ref['CHANGE']) == 0 and desired_offset(begin + L, ref['CHANGE']) == sep
assert desired_offset(begin + L, ref['TARGET']) == 0 and desired_offset(ret + L, ref['TARGET']) == -sep
assert desired_offset(ret + L + 1, ref['HOME']) == 0
print('1 offsets OK: separation', sep, 'lane change', float(begin), '->', float(begin + L), 'return', float(ret), '->', float(ret + L))
worst = {}
for r in fx.responses:
    v = max(r.targets.values())
    mids = [s['start_arc_m'] + s['length_m'] / 2 for p in (r.profile, *(w['profile'] for w in r.phases.get('reference_switches', ())))
            for s in p['segments']]
    worst[f'{r.actor_role}:{r.action_id}'] = max(float(v) ** 2 * profile_kappa(r, SimpleNamespace(arc=m)) for m in mids)
assert worst['EGO:A'] <= 2.5 and worst['EGO:B'] == 0 and worst['NPC:NPC_COMMON'] == 0, worst
print('2 reference lateral acceleration bound (m/s^2):', {k: round(x, 4) for k, x in worst.items()})
st = {k: fx.sections[k].route_station for k in ('O_DECISION', 'O_RETURN_START', 'X', 'DESTINATION')}
ego = fx.routes['EGO']
assert st['O_DECISION'] < st['O_RETURN_START'] < st['X'] < st['DESTINATION'] <= ego.arc[-1] - 5, st
print('3 sections OK:', {k: float(x) for k, x in st.items()}, 'plan end', float(ego.arc[-1]))
prep = json.loads(Path(fx.environment['runtime_recipe_v2']['prepare_json']).read_text(encoding='utf-8'))
fl = lambda x: float.fromhex(x['binary64']) if 'binary64' in x else x['numerator'] / x['denominator']  # noqa: E731
vE, vN, gap = fl(prep['probe2']['EGO']), fl(prep['probe2']['NPC']), fl(prep['gap_at_t0_probe2'])
body = 2 * fl(prep['bbox']['extent'][0]); half = body / 2
dec = float(st['O_DECISION'])
# The return segment starts at a fixed arc (the vehicle centre at `ret`): from then on step_response needs
# RETURN_CLEAR_CONFIRMED (EGO rear - NPC front >= 0.5 m held 0.25 s) or raises RETURN_GUARD_MISSING. Constant-speed
# kinematics from t0 (EGO front at O_DECISION, NPC rear gap ahead): estimate only, not evidence.
t_centre = (float(ret) + half - dec) / vE
t_clear = (gap + 2 * body + .5) / (vE - vN) + .25
slack = t_centre - t_clear
print(f'4 return slack {slack:.3f} s = {slack * vE:.2f} m (centre at return start {t_centre:.3f} s, earliest '
      f'RETURN_CLEAR_CONFIRMED {t_clear:.3f} s; vE {vE:.3f}, vN {vN:.3f}, gap at t0 {gap:.3f}) - estimate only')
assert slack > .05, 'PREDICTED_RETURN_GUARD_MISSING'
x_slack = (float(st['X']) + half - float(ret + L)) / vE
print(f'5 X slack {x_slack:.3f} s: return profile ends (centre {float(ret + L):.2f}) before X_END (centre '
      f'{float(st["X"]) + half:.2f}) - the stock lateral controller must settle in the initial box by then')
print('SELFCHECK PASS')
