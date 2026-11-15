"""native-io-prepare-i12.py (io-v1.5 + io-v1.6 + io-i-v1.2 G2) plus addendum J (PREREG_M56_NPC_DLC_FLOOR_ADDENDUM_J_20261115.md):
the NPC cut-in of a category-I scene is Dlc_N = max(3 vN, 18 m) instead of 3 vN. npc_cut is recompiled from the bytes of
native-io-prepare.py with that one line replaced; no file is edited.
  python -I native-io-prepare-i12j.py TOWN ID[,ID...]   (same env as native-io-prepare.py)"""
import ast, importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ioprep12', HERE / 'native-io-prepare-i12.py')
J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
M, P = J.M, J.P
SRC = HERE / 'native-io-prepare.py'
OLD = "    length = 3 * F(g['vN'])\n"
NEW = "    length = max(3 * F(g['vN']), F(18))  # addendum J: NPC Dlc floor\n"
_src = SRC.read_text(encoding='utf-8')
_fn = next(n for n in ast.parse(_src).body if isinstance(n, ast.FunctionDef) and n.name == 'npc_cut')
_seg = ''.join(_src.splitlines(keepends=True)[_fn.lineno - 1:_fn.end_lineno])
assert _seg.count(OLD) == 1, 'I12J_NPC_CUT_SITE'
exec(compile(_seg.replace(OLD, NEW), str(SRC) + ' [addendum J]', 'exec'), M.__dict__)   # _prepare_o_i12 looks npc_cut up here

_finish = P.finish
def finish(c, out):
    if getattr(c, 'category', None) == 'I':
        out['recipe_npc_dlc_floor'] = 'addendum J: NPC cut-in max(3 vN, 18 m) (native-io-prepare-i12j.py)'
    return _finish(c, out)
P.finish = finish

if __name__ == '__main__':
    M.main()
