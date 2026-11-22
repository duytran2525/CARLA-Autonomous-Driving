"""native-io-prepare-v16.py under addendum Z (docs/m56/PREREG_M56_IO_O_ADDENDUM_Z_20261122.md). v16 is loaded as a module and
NOT edited. One change, in memory: the NPC route rows of _prepare_o reach back NPC_BACK_M = max(60, gap + L + 15) m per scene
instead of a flat 60 m, so the io-v1.4 c NPC start (>= 5 m before the decision, i.e. a shift of about -(gap + L + 5)) lies inside
the rows instead of being clamped to their first point (O08-S3 16/11: shift -63.527 m, rows 60 m, gap realised 58.582 vs 55.694).
Scenes with gap + L + 15 <= 60 build exactly the rows they built before. prepare.json records npc_back_m and recipe_io_z.
  python -I native-io-prepare-z.py TOWN ID[,ID...]   (same env as native-io-prepare-v16.py)
  python -I native-io-prepare-z.py --selftest"""
import importlib.util, math, sys
from pathlib import Path

BASE_BACK_M, Z_MARGIN_M = 60., 15.  # margin = io-v1.4 c's 5 m + 10 m for the probe-dynamics error of the shift


def back_m(gap, L):
    return max(BASE_BACK_M, float(gap) + float(L) + Z_MARGIN_M)


if sys.argv[1:] == ['--selftest']:
    L = 2 * float.fromhex('0x1.da498c0000000p+0')
    assert back_m(32.955, L) == 60.                                    # O04-S3: unchanged
    assert math.isclose(back_m(55.694, L), 55.694 + L + 15) and back_m(55.694, L) > 63.527 + 5  # O08-S3 reaches its shift
    print('PREPARE_Z SELFTEST_OK'); sys.exit(0)

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ioprep16', here / 'native-io-prepare-v16.py')
V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)
M, P = V.M, V.P
assert M.NPC_BACK_M == BASE_BACK_M, M.NPC_BACK_M
_inner = M._prepare_o  # v16's _prepare_o_v15 (io-v1.5 long probe) around the frozen _prepare_o


def _prepare_o_z(c, client, proc, start, world, m, identity, body, bbox, *a, **k):
    back = back_m(M.geometry(c, m)['gap'], 2 * bbox['extent'][0])
    prev = P.finish

    def fin(c_, out):
        out.update(npc_back_m=back, recipe_io_z='addendum Z: NPC_BACK_M = max(60, gap + L + 15)')
        return prev(c_, out)
    M.NPC_BACK_M, P.finish = back, fin
    try:
        return _inner(c, client, proc, start, world, m, identity, body, bbox, *a, **k)
    finally:
        M.NPC_BACK_M, P.finish = BASE_BACK_M, prev


M._prepare_o = _prepare_o_z

if __name__ == '__main__':
    M.main()
