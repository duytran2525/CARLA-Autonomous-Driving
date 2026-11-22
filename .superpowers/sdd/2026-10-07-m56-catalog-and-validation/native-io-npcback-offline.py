"""Offline check for addendum Z (2026-11-22): can the NPC route rows of _prepare_o reach back far enough for the io-v1.4 c
NPC start (>= 5 m before the decision)? Reuses native-io-runin-offline.py (the EXACT route builders of native-io-prepare.py on
an offline carla.Map from OpenDRIVE, no server). For each scene prints the old reach (NPC_BACK_M = 60) and the addendum-Z
reach max(60, gap + L + 15), relative to the decision, and whether the rows build.
  python -I native-io-npcback-offline.py REVISION.json ID[,ID...]   (M56_CODE = product on sys.path, as for prepare)"""
import importlib.util, json, math, sys
from pathlib import Path

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runin', here / 'native-io-runin-offline.py')
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
from m56.model import decode_record  # noqa: E402

L = 2 * float.fromhex('0x1.da498c0000000p+0')  # stock EGO body length, as in native-io-runin-offline.py


def back_z(gap):
    return max(60., float(gap) + L + 15.)


def reach(c, m, back):
    """Road-s of the first NPC row (relative to the decision, negative = before it) for a given NPC_BACK_M; rows must build."""
    g = R.ns['geometry'](c, m); sg, road = g['sign'], g['road']
    s_n0 = g['front_t0_s'] + sg * (g['gap'] + L)
    if g.get('through'):
        rows, cut = R.ns['lane_rows_through'](m, road, g['npc_lane'], s_n0 - sg * back, s_n0 + sg * 50, strict=False)
    else:
        rows = R.ns['lane_rows'](m, road, g['npc_lane'], s_n0 - sg * back, s_n0 + sg * 50)
    first = rows[0]
    rel = (first['s'] - g['front_t0_s']) * sg if first['road'] == road else None
    return {'first_road': first['road'], 'first_rel_decision_m': None if rel is None else round(rel, 2),
            'need_rel_decision_m': -5.0, 'gap': round(float(g['gap']), 3), 'vE': float(g['vE']), 'vN': float(g['vN'])}


def main(rev_path, ids):
    rev = json.loads(Path(rev_path).read_text(encoding='utf-8'))
    want = ids.split(',')
    cands = {i['id']: decode_record('Candidate', {**i, 'parameters': {n: p for n, p in i['parameters'].items()
                                                                       if p.get('units') != 'index'}})
             for i in rev['candidates'] if i['id'] in want}
    assert set(cands) == set(want), ('NOT_IN_REVISION', sorted(set(want) - set(cands)))
    maps = {}
    for cid in want:
        c = cands[cid]
        if c.town not in maps:
            maps.clear(); R.ns['road_length'].__defaults__[0].clear()
            maps[c.town] = R.carla.Map(c.town, R.xodr(c.town).read_text(encoding='utf-8'))
        m = maps[c.town]
        try:
            gap = R.ns['geometry'](c, m)['gap']
        except AssertionError as e:
            print(json.dumps({'id': cid, 'status': 'GEOMETRY_BLOCKED', 'reason': str(e.args[0] if e.args else e)}), flush=True)
            continue
        out = {'id': cid, 'L': round(L, 3), 'back_old': 60., 'back_z': round(back_z(gap), 3)}
        for tag, back in (('old', 60.), ('z', back_z(gap))):
            try:
                out[tag] = {'status': 'ROWS_OK', **reach(c, m, back)}
            except AssertionError as e:
                out[tag] = {'status': 'ROWS_BLOCKED', 'reason': str(e.args[0] if e.args else e)}
        print(json.dumps(out, default=str), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--selftest']:
        assert back_z(10) == 60. and math.isclose(back_z(55.694), 55.694 + L + 15)
        print('NPCBACK SELFTEST_OK'); sys.exit(0)
    main(sys.argv[1], sys.argv[2])
