"""native-io-prepare-i13.py (io-i-v1.3 a) plus io-i-v1.3 b (PREREG_M56_IO_I_ADDENDUM_P_RUNIN_20261117.md): a category-I
scene whose probe-1 EGO readiness is READINESS_NOT_STEADY gets AT MOST ONE re-preparation with the EGO run-in x 3/2
(rounded up to 1 m), probe labels suffixed '-runin'. Why: I01-S1 17/11 - the EGO speed loop limit-cycled (throttle 0 ->
-3.5 m/s^2) for 4 cycles until ~12 s, so the fixed 2 s window before the decision station still saw it (range 0.141 > 0.10);
16/11 the same recipe settled after 1 cycle (0.073). The readiness rule (2 s window, 0.10 m/s) is unchanged; only the
distance the controller gets before the window. The first attempt's grid and probe-1 plateau are kept in prepare.json
(io_i13b_first). No file edited. python -I native-io-prepare-i14.py TOWN ID[,ID...] (same env as native-io-prepare.py)"""
import importlib.util, math, sys
from pathlib import Path

SCALE = 1.5
RUNIN_M = 100.  # native-io-prepare.py RUNIN_M (asserted equal after import)


def runin_long(vE, base=RUNIN_M):
    """The io-i-v1.3 b run-in: default ceil(RUNIN_M vE / 9.375) x 3/2, rounded up to 1 m."""
    return float(math.ceil(SCALE * math.ceil(base * float(vE) / 9.375 - 1e-9) - 1e-9))


if __name__ == '__main__' and '--selftest' in sys.argv:  # before any import: the prepare chain launches CARLA in main()
    assert runin_long(6) == 96.0 and runin_long(7.5) == 120.0, (runin_long(6), runin_long(7.5))
    print('SELFTEST_OK'); raise SystemExit(0)

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ioprep13', HERE / 'native-io-prepare-i13.py')
I13 = importlib.util.module_from_spec(spec); spec.loader.exec_module(I13)
M, P = I13.M, I13.P
assert M.RUNIN_M == RUNIN_M, M.RUNIN_M


class _NotSteady(Exception):
    pass


_inner = M._prepare_o  # io-v1.5 wrapper -> i13 body


def _prepare_o_i14(c, *a, **k):
    if getattr(c, 'category', None) != 'I' or k.get('runin_m') is not None or k.get('sfx'):
        return _inner(c, *a, **k)
    fin = P.finish

    def hold(c_, out):  # the first attempt: NOT_STEADY is held back (prepare.json is write-once), anything else is final
        if out.get('status') == 'BLOCKED_FIXTURE' and out.get('reason') == 'READINESS_NOT_STEADY':
            raise _NotSteady(out)
        return fin(c_, out)
    P.finish = hold
    try:
        return _inner(c, *a, **k)
    except _NotSteady as e:
        first = e.args[0]
        P.finish = lambda c_, out: fin(c_, {**out, 'io_i13b_first': {x: first.get(x) for x in ('runin_m', 'pid_grid', 'probe1', 'reason')}})
        runin = runin_long(first['geometry']['vE'])
        M.log(event='IO_I13B_RUNIN_RETRY', scene=c.id, runin_m=runin, first_runin_m=first.get('runin_m'))
        return _inner(c, *a, **{**k, 'runin_m': runin, 'sfx': '-runin'})
    finally:
        P.finish = fin


def finish_tag(c, out):
    if getattr(c, 'category', None) == 'I':
        out['recipe_io_i13b'] = 'io-i-v1.3 b: one re-preparation with EGO run-in x 3/2 on READINESS_NOT_STEADY (native-io-prepare-i14.py)'
    return _tagged(c, out)


_tagged = P.finish
P.finish = finish_tag
M._prepare_o = _prepare_o_i14

if __name__ == '__main__':
    M.main()
