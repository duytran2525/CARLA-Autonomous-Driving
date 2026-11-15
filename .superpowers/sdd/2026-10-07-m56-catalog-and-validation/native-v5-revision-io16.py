"""native-v5-revision.py under recipe io-v1.6 (PREREG_M56_IO_RECIPE_V1_6_DLC_FLOOR_20261115.md): identical run, except that
catalog-recipes.io_recipe builds the EGO lane change with Dlc_eff = max(3 vE, 18 m) instead of 3 vE. Neither file is edited:
the one source line is replaced in memory (asserted unique) and io_recipe is re-defined in the catalog-recipes module.
  python -I native-v5-revision-io16.py <same arguments as native-v5-revision.py>"""
import ast, importlib.util, sys
from pathlib import Path
here = Path(__file__).resolve().parent
OLD, NEW = '    dlc = 3 * vE\n', '    dlc = max(3 * vE, F(18))  # io-v1.6: Dlc_eff = max(3 vE, 18 m)\n'


def io_recipe_v16(cr):
    """io_recipe with the one line replaced, defined in the catalog-recipes globals (same helpers)."""
    src = Path(cr.__file__).read_text(encoding='utf-8')
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == 'io_recipe')
    seg = ''.join(src.splitlines(keepends=True)[fn.lineno - 1:fn.end_lineno])
    assert seg.count(OLD) == 1, 'IO16_PATCH_SITE'
    ns = dict(cr.__dict__)
    exec(compile(seg.replace(OLD, NEW), cr.__file__ + ' [io-v1.6]', 'exec'), ns)
    return ns['io_recipe']


spec = importlib.util.spec_from_file_location('rev5', here / 'native-v5-revision.py')
rev5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(rev5)  # main() only runs under __main__
# Only the A-SEL2 fill I/O builder uses io-v1.6; the v1 C0 rebuild (asserted byte-identical) keeps the frozen recipe.
_v16, _asel2_io = io_recipe_v16(rev5.cr), rev5.asel2_io


def asel2_io_v16(*a, **k):
    old = rev5.cr.io_recipe
    rev5.cr.io_recipe = _v16
    try:
        return _asel2_io(*a, **k)
    finally:
        rev5.cr.io_recipe = old


rev5.asel2_io = asel2_io_v16
if __name__ == '__main__':
    rev5.main(*sys.argv[1:])
