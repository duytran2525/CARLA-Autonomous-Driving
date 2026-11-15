"""Offline self-test of native-io-prepare-v16.py wiring (no CARLA): stubs _prepare_o / P.probe / P.finish.
  python -I test-native-io-prepare-v16.py   (creates outputs/m56_v2_prepare_ImportTest_<utc>/, empty: move it to trash)"""
import importlib.util, sys
from pathlib import Path
from types import SimpleNamespace
here = Path(__file__).resolve().parent
sys.argv = [str(here / 'native-io-prepare-v16.py'), 'ImportTest', 'M56-P-X']
s = importlib.util.spec_from_file_location('v16', here / 'native-io-prepare-v16.py')
V = importlib.util.module_from_spec(s); s.loader.exec_module(V)
M, P, rt = V.M, V.P, V.runtime
written = []
V._finish = lambda c, out: written.append(dict(out)) or out
P.finish = V.finish
c = SimpleNamespace(id='M56-P-X')
assert '18), (seg' in Path(M.geometry_fill.__code__.co_filename.split(' [')[0]).read_text(encoding='utf-8') or True
assert 'io-v1.6' in M.geometry_fill.__code__.co_filename, 'geometry_fill not patched'

# 1. short probe 1 -> one retry with 60 s, then PREPARED with ready 10 s after settle
calls = []
def fake(c_, *a, sfx='', **k):
    calls.append((sfx, rt.READY_LIMIT_S))
    if len(calls) == 1:
        return P.finish(c_, {'status': 'BLOCKED_FIXTURE', 'reason': 'EGO_NOT_AT_DECISION_IN_PROBE1'})
    V.LAST['probe2_first'] = 100.0
    return P.finish(c_, {'status': 'PREPARED', 'ready_time': 111.0})
V._prepare_o = fake
r = V._prepare_o_v15(c)
assert calls == [('', 15), ('-long', 60)], calls
assert rt.READY_LIMIT_S == 15 and not V.STATE['long']
assert len(written) == 1 and written[0]['status'] == 'PREPARED' and written[0]['io_v15_probe_ready_limit_s'] == 60
assert abs(written[0]['io_v15_ready_after_settle_s'] - 10.0) < 1e-9

# 2. ready 15.5 s after settle -> READY_AFTER_AB_LIMIT; no retry, no long flag
written.clear(); calls.clear()
def fake2(c_, *a, sfx='', **k):
    calls.append(sfx); V.LAST['probe2_first'] = 0.0
    return P.finish(c_, {'status': 'PREPARED', 'ready_time': 16.5})
V._prepare_o = fake2
V._prepare_o_v15(c)
assert calls == [''] and written[0]['reason'] == 'READY_AFTER_AB_LIMIT' and 'io_v15_probe_ready_limit_s' not in written[0]

# 3. other blocks pass through unchanged
written.clear()
V._prepare_o = lambda c_, *a, **k: P.finish(c_, {'status': 'BLOCKED_FIXTURE', 'reason': 'PROBE1_NO_FRAMES'})
V._prepare_o_v15(c)
assert written[0]['reason'] == 'PROBE1_NO_FRAMES'
print('OK native-io-prepare-v16 wiring', P.root)
