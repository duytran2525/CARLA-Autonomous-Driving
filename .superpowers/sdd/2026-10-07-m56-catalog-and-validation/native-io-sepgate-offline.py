"""Offline lane-separation forecast (batch log 15/11 evening: O08-S2 IO_LANE_SEPARATION_MISMATCH 3.249 vs 13/4): at the
decision road-s, the world-axis lateral distance EGO lane centre -> target lane centre, rounded to the mm exactly as
native_io_common.io_geometry does, must equal the frozen lane-change offset of the candidate (O: EGO A, I: EGO B).
Uses the map loader and geometry of native-io-runin-offline.py (gate G). No CARLA server.
  M56_CODE=<product> python -I native-io-sepgate-offline.py REVISION.json ID[,ID..]"""
import importlib.util, json, sys
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('gateg', HERE / 'native-io-runin-offline.py')
G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
from m56.model import decode_record
from m56.response import _axis_right


def sep_check(c, m):
    g = G.ns['geometry'](c, m); R = g['road']
    e = m.get_waypoint_xodr(R, g['ego_lane'], g['front_t0_s']).transform
    t = m.get_waypoint_xodr(R, g['target_lane'], g['front_t0_s']).transform
    axis = _axis_right(e.rotation.yaw)
    if axis is None:
        return {'status': 'SEP_BLOCKED', 'reason': 'IO_ROAD_NOT_AXIS_ALIGNED'}
    lat, sign = axis
    pe, pt = (e.location.x, e.location.y), (t.location.x, t.location.y)
    sep = F(round((pt[lat] - pe[lat]) * sign * 1000), 1000)
    act = 'A' if c.category == 'O' else 'B'
    r = next(x for x in c.responses if x.actor_role == 'EGO' and x.action_id == act)
    want = next(s['end_offset_m'] for s in r.profile['segments'] if s['start_offset_m'] != s['end_offset_m'])
    raw = (pt[lat] - pe[lat]) * sign
    # prepare measures on its own route points (O08-S2: waypoints 3.24951, prepare 3.24936), so near a mm rounding edge
    # the waypoint value does not forecast prepare: pass only with a 0.25 mm margin (addendum K)
    status = 'SEP_MISMATCH' if sep != want else ('SEP_OK' if abs(raw - float(want)) < MARGIN_M else 'SEP_MARGINAL')
    return {'status': status, 'separation_mm': str(sep), 'raw_m': round(raw, 5), 'profile_offset_m': str(want)}


MARGIN_M = 0.00025


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
            maps.clear(); G.ns['road_length'].__defaults__[0].clear()
            maps[c.town] = G.carla.Map(c.town, G.xodr(c.town).read_text(encoding='utf-8'))
        try:
            r = {'id': cid, **sep_check(c, maps[c.town])}
        except AssertionError as e:
            r = {'id': cid, 'status': 'SEP_BLOCKED', 'reason': str(e.args[0] if e.args else e)}
        print(json.dumps(r, default=str), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
