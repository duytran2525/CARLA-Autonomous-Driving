"""native-io-prepare.py under recipes io-v1.5 + io-v1.6 (PREREG_M56_IO_RECIPE_V1_5_LONG_PROBE_20261115.md,
PREREG_M56_IO_RECIPE_V1_6_DLC_FLOOR_20261115.md). native-io-prepare.py is loaded as a module and NOT edited (gate G
extracts from its bytes). Changes, all in memory:
  io-v1.6: geometry_fill accepts the frozen lane-change length Dlc_eff = max(3 vE, 18 m) (one asserted line);
  io-v1.5 2.1: a scene whose probe-1 pass ends EGO_NOT_AT_DECISION_IN_PROBE1 is prepared once more from probe 1 with
               runtime.READY_LIMIT_S = LONG_PROBE_S (60 s, cl-v1 b); prepare.json records io_v15_probe_ready_limit_s;
  io-v1.5 2.3: a PREPARED scene whose probe-2 readiness came later than 14.0 s after settle becomes BLOCKED_FIXTURE
               READY_AFTER_AB_LIMIT (measured ready_time - first probe-2 frame - SETTLE_S, which is >= the runner's own
               ready - settled interval, so the gate is at least as strict as written).
The A/B runner keeps READY_LIMIT_S 15 s (product unchanged).
  python -I native-io-prepare-v16.py TOWN ID[,ID...]   (same env as native-io-prepare.py)"""
import ast, importlib.util, sys
from pathlib import Path
here = Path(__file__).resolve().parent
SRC = here / 'native-io-prepare.py'
spec = importlib.util.spec_from_file_location('ioprep', SRC)
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)  # module-level: argv TOWN SCENES, P = v2 prepare
P, runtime = M.P, M.runtime

# io-v1.6: geometry_fill with the Dlc_eff assertion
OLD_A = "    assert seg['length_m'] == 3 * p['vE'], (seg['length_m'], p['vE'])\n"
NEW_A = "    assert seg['length_m'] == max(3 * p['vE'], 18), (seg['length_m'], p['vE'])  # io-v1.6\n"
_src = SRC.read_text(encoding='utf-8')
_fn = next(n for n in ast.parse(_src).body if isinstance(n, ast.FunctionDef) and n.name == 'geometry_fill')
_seg = ''.join(_src.splitlines(keepends=True)[_fn.lineno - 1:_fn.end_lineno])
assert _seg.count(OLD_A) == 1, 'IO16_ASSERT_SITE'
exec(compile(_seg.replace(OLD_A, NEW_A), str(SRC) + ' [io-v1.6]', 'exec'), M.__dict__)

LONG_PROBE_S, AB_READY_LIMIT_S, SETTLE_S = 60, 14.0, float(runtime.SETTLE_S)
STATE = {'long': False}


class _Retry(Exception):
    pass


_finish = P.finish


def finish(c, out):
    if out.get('reason') == 'EGO_NOT_AT_DECISION_IN_PROBE1' and not STATE['long']:
        raise _Retry()  # io-v1.5 2.1: nothing written for the short pass; its probe dirs stay as evidence
    if STATE['long']:
        out['io_v15_probe_ready_limit_s'] = LONG_PROBE_S
    if out.get('status') == 'PREPARED':
        first = out.get('_probe2_first_simtime')
        lag = None if first is None else out['ready_time'] - first - SETTLE_S
        out['io_v15_ready_after_settle_s'] = lag
        if lag is None or lag > AB_READY_LIMIT_S:
            out.update(status='BLOCKED_FIXTURE', reason='READY_AFTER_AB_LIMIT')
    out.pop('_probe2_first_simtime', None)
    out['recipe_io_v15_v16'] = 'io-v1.5 + io-v1.6 (native-io-prepare-v16.py)'
    return _finish(c, out)


_probe = P.probe
LAST = {}


def probe(*a, **k):
    raw = _probe(*a, **k)
    label = a[10] if len(a) > 10 else k.get('label')
    if raw and str(label).startswith('probe2'):
        LAST['probe2_first'] = float(raw[0].simtime)
    return raw


_prepare_o = M._prepare_o


def _prepare_o_v15(c, *a, **k):
    LAST.clear()
    orig_finish = P.finish

    def fin(c_, out):
        if 'probe2_first' in LAST:
            out['_probe2_first_simtime'] = LAST['probe2_first']
        return orig_finish(c_, out)
    P.finish = fin
    try:
        return _prepare_o(c, *a, **k)
    except _Retry:
        STATE['long'] = True
        old = runtime.READY_LIMIT_S
        runtime.READY_LIMIT_S = LONG_PROBE_S
        M.log(event='IO_V15_LONG_PROBE', scene=c.id, ready_limit_s=LONG_PROBE_S)
        try:
            LAST.clear()
            k = {**k, 'sfx': (k.get('sfx') or '') + '-long'}
            return _prepare_o(c, *a, **k)
        finally:
            runtime.READY_LIMIT_S = old
            STATE['long'] = False
    finally:
        P.finish = orig_finish


P.finish = finish
P.probe = probe
M._prepare_o = _prepare_o_v15

if __name__ == '__main__':
    M.main()
