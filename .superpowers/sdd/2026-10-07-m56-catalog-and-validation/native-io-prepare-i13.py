"""native-io-prepare-i12j.py (io-v1.5 + io-v1.6 + io-i-v1.2 G2 + addendum J) plus io-i-v1.3 a (NPC placement by arc):
the probe-2 NPC start of a category-I scene is the first NPC row whose ARC is >= arc(k0) + shift, instead of the first row
ON THE SITE ROAD at road-s >= s_n. The old rule clamps a negative shift at the start of the site road, so the gap at t0
grew by |shift| (addendum L: I04 46.4 vs 13.2 m). shift is already arc metres from k0 (rear/dec_npc are NPC-route
stations), so the new rule is the same quantity without the clamp. Too few rows behind k0: BLOCKED_FIXTURE NPC_RUNIN_SHORT.
O scenes keep the old rule. No file is edited: _prepare_o is recompiled from its bytes with the i12 G2 line and this line.
  python -I native-io-prepare-i13.py TOWN ID[,ID...]   (same env as native-io-prepare.py)"""
import ast, importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ioprep12j', HERE / 'native-io-prepare-i12j.py')
J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
M, P, V = J.M, J.P, J.J.V
SRC = HERE / 'native-io-prepare.py'
G2_OLD, G2_NEW = J.J.OLD, J.J.NEW
OLD = "    k = next(i for i, r in enumerate(rows['NPC']) if r['road'] == R and (r['s'] - s_n) * sg >= 0)\n"
NEW = ("    if I:  # io-i-v1.3 a: arc placement, no clamp at the site-road start\n"
       "        a_k = arc['NPC'][k0] + shift\n"
       "        k = next((i for i, a in enumerate(arc['NPC']) if a >= a_k), None)\n"
       "        if k is None or a_k < arc['NPC'][0]:\n"
       "            out.update(status='BLOCKED_FIXTURE', reason='NPC_RUNIN_SHORT', npc_shift_m=shift); return P.finish(c, out)\n"
       "    else:\n"
       "        k = next(i for i, r in enumerate(rows['NPC']) if r['road'] == R and (r['s'] - s_n) * sg >= 0)\n")


def place(arc_npc, k0, shift):
    """The NEW rule as a pure function (self-check)."""
    a_k = arc_npc[k0] + shift
    k = next((i for i, a in enumerate(arc_npc) if a >= a_k), None)
    return None if k is None or a_k < arc_npc[0] else k


_src = SRC.read_text(encoding='utf-8')
_fn = next(n for n in ast.parse(_src).body if isinstance(n, ast.FunctionDef) and n.name == '_prepare_o')
_seg = ''.join(_src.splitlines(keepends=True)[_fn.lineno - 1:_fn.end_lineno])
assert _seg.count(OLD) == 1 and _seg.count(G2_OLD) == 1 and _seg.count('def _prepare_o(') == 1, 'I13_SITE'
exec(compile(_seg.replace(G2_OLD, G2_NEW).replace(OLD, NEW).replace('def _prepare_o(', 'def _prepare_o_i13(', 1),
             str(SRC) + ' [io-i-v1.2 G2 + io-i-v1.3 a]', 'exec'), M.__dict__)
V._prepare_o = M._prepare_o_i13

_finish = P.finish
def finish(c, out):
    if getattr(c, 'category', None) == 'I':
        out['recipe_io_i13a'] = 'io-i-v1.3 a: NPC probe-2 start by arc, no site-road clamp (native-io-prepare-i13.py)'
    return _finish(c, out)
P.finish = finish

if __name__ == '__main__':
    M.main()
