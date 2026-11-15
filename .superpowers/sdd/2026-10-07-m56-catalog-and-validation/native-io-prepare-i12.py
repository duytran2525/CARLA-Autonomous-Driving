"""native-io-prepare-v16.py (io-v1.5 + io-v1.6) plus io-i-v1.2 G2 (PREREG_M56_IO_I_RECIPE_V1_2_20261115.md 2.2): the EGO route
of a category-I scene ends at X + 2L + 10 m (L = EGO body length) instead of X + 5 m. O scenes are unchanged (X + 5 m).
Neither native-io-prepare.py nor native-io-prepare-v16.py is edited: _prepare_o is recompiled from its own bytes with that
one expression replaced, under a new name, and wired in where v16's io-v1.5 wrapper calls it.
  python -I native-io-prepare-i12.py TOWN ID[,ID...]   (same env as native-io-prepare.py)"""
import ast, importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ioprep16', HERE / 'native-io-prepare-v16.py')
V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)   # loads native-io-prepare.py as V.M (no main)
M, P = V.M, V.P
SRC = HERE / 'native-io-prepare.py'
OLD = "F(math.ceil((xs + 5) * 1000), 1000))}"
NEW = "F(math.ceil((xs + (2 * L + 10 if I else 5)) * 1000), 1000))}  # io-i-v1.2 G2"
_src = SRC.read_text(encoding='utf-8')
_fn = next(n for n in ast.parse(_src).body if isinstance(n, ast.FunctionDef) and n.name == '_prepare_o')
_seg = ''.join(_src.splitlines(keepends=True)[_fn.lineno - 1:_fn.end_lineno])
assert _seg.count(OLD) == 1 and _seg.count('def _prepare_o(') == 1, 'I12_TAIL_SITE'
exec(compile(_seg.replace(OLD, NEW).replace('def _prepare_o(', 'def _prepare_o_i12(', 1), str(SRC) + ' [io-i-v1.2 G2]', 'exec'),
     M.__dict__)
V._prepare_o = M._prepare_o_i12   # v16's io-v1.5 wrapper (M._prepare_o) now runs the G2 body; recursion still goes through it

_finish = P.finish
def finish(c, out):
    if getattr(c, 'category', None) == 'I':
        out['recipe_io_i12'] = 'io-i-v1.2 G2: EGO destination X + 2L + 10 m (native-io-prepare-i12.py)'
    return _finish(c, out)
P.finish = finish   # outermost: v16's finish (P.finish at import) is _finish here and still runs

if __name__ == '__main__':
    M.main()
