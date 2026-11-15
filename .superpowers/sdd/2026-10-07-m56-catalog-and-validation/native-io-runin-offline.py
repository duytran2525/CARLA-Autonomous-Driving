"""Offline I/O route check (2026-11-15): runs the EXACT route-building functions of native-io-prepare.py (geometry,
geometry_fill, road_length, lane_rows, lane_rows_through, MAX_YAW_DEV; extracted by name from its source, no edit) on an
offline carla.Map built from the town's OpenDRIVE, with the run-in / tail lengths of _prepare_o. No server, no RAM-heavy
probe. Reproduces prepare's RUNIN_NOT_STRAIGHT / TAIL_NOT_STRAIGHT / NO_WAYPOINT before any CARLA time is spent.
  python -I native-io-runin-offline.py REVISION.json ID[,ID...]   (M56_CODE = product on sys.path, as for prepare)"""
import ast, json, math, sys
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import carla  # noqa: E402
from native_v2_common import _step, _wp_row  # noqa: E402,F401  (used by the extracted functions)
from m56.model import decode_record  # noqa: E402

SRC = here / 'native-io-prepare.py'
NAMES = {'geometry_fill', 'road_length', 'MAX_YAW_DEV', 'lane_rows_through', 'geometry', 'lane_rows'}
tree = ast.parse(SRC.read_text(encoding='utf-8'))
body = [n for n in tree.body if (getattr(n, 'name', None) in NAMES) or
        (isinstance(n, ast.Assign) and any(getattr(t, 'id', None) in NAMES for t in n.targets))]
assert {getattr(n, 'name', None) or n.targets[0].id for n in body} == NAMES, 'EXTRACT'
ns = {'math': math, '_step': _step, '_wp_row': _wp_row, '__builtins__': __builtins__}
exec(compile(ast.Module(body=body, type_ignores=[]), str(SRC), 'exec'), ns)
# constants of _prepare_o, read from the same source (asserted, not copied)
consts = {t.id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) for t in n.targets
          if getattr(t, 'id', None) in ('RUNIN_M', 'EGO_TAIL_M')}
pair = next(n for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Tuple)
            and [e.id for e in n.targets[0].elts] == ['NPC_BACK_M', 'NPC_TAIL_M'])
NPC_BACK_M, NPC_TAIL_M = ast.literal_eval(pair.value)
RUNIN_M, EGO_TAIL_M = consts['RUNIN_M'], consts['EGO_TAIL_M']
MAPS = Path('E:/Carla/CarlaUE4/Content/Carla/Maps')  # = asel2-census.MAPS


def xodr(town):
    p = MAPS / 'OpenDrive' / f'{town}.xodr'
    return p if p.exists() else MAPS / town / 'OpenDrive' / f'{town}.xodr'


def check(c, m, L):
    """The route rows _prepare_o builds before its first probe (first attempt, no retry run-in)."""
    g = ns['geometry'](c, m); sg, R = g['sign'], g['road']
    runin = float(math.ceil(RUNIN_M * float(g['vE']) / 9.375 - 1e-9))
    I = c.category == 'I'
    i_tail = 10 * float(g['vN']) if I else 0.
    s_e0, s_end = g['front_t0_s'] - sg * runin, g['X_s'] + sg * (g['gap'] + 2 * L + EGO_TAIL_M + i_tail)
    s_n0 = s_e0 + sg * (g['gap'] + L) if I else g['front_t0_s'] + sg * (g['gap'] + L)
    lr = ns['lane_rows_through'] if g.get('through') else None
    if lr:
        lr(m, R, g['ego_lane'], s_e0, s_end); lr(m, R, g['target_lane'], s_e0, s_end)
        _, cut = lr(m, R, g['npc_lane'], s_n0 - sg * NPC_BACK_M, s_end + sg * NPC_TAIL_M, strict=False)
        if I:
            lr(m, R, g['npc_target_lane'], s_n0 - sg * NPC_BACK_M, s_end + sg * NPC_TAIL_M - sg * cut, strict=False)
    else:
        for lane in (g['ego_lane'], g['target_lane']):
            ns['lane_rows'](m, R, lane, s_e0, s_end)
        cut = 0.
    return {'runin_m': runin, 'npc_tail_cut_m': round(cut, 2), 'road': R}


def main(rev_path, ids):
    rev = json.loads(Path(rev_path).read_text(encoding='utf-8'))
    want = ids.split(',')
    cands = {}
    for item in rev['candidates']:
        if item['id'] in want:
            item = {**item, 'parameters': {n: p for n, p in item['parameters'].items() if p.get('units') != 'index'}}
            cands[item['id']] = decode_record('Candidate', item)
    missing = [i for i in want if i not in cands]
    assert not missing, ('NOT_IN_REVISION', missing)
    maps = {}
    for cid in want:
        c = cands[cid]
        if c.town not in maps:
            maps.clear(); ns['road_length'].__defaults__[0].clear()  # one big map in RAM at a time
            maps[c.town] = carla.Map(c.town, xodr(c.town).read_text(encoding='utf-8'))
        L = 2 * float.fromhex('0x1.da498c0000000p+0')  # 2 x bbox extent x of the stock EGO, as in every prepare.json
        try:
            r = {'id': cid, 'status': 'ROUTES_OK', **check(c, maps[c.town], L)}
        except AssertionError as e:
            r = {'id': cid, 'status': 'ROUTE_BLOCKED', 'reason': str(e.args[0] if e.args else e)}
        print(json.dumps(r, default=str), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
