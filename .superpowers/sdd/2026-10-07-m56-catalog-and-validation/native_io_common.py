"""M56 I/O (pilot O) fixture pieces shared by native-v5-revision.py (candidate responses), native-io-ab.py (compile) and
native-io-selfcheck.py. Design: docs/m56/DESIGN_M56_IO_TOOLING_20261026.md. Every choice below is listed in the I/O recipe
prereg; nothing here runs CARLA or an A/B. NOT part of the m56 product.

Frames: the native EGO route (initial lane, CARLA waypoints <= 0.24 m) defines the arc frame. The frozen catalog arcs (route
arc 0 = its first point) are carried over by ONE offset: the native station of the catalog route's first point, so every
frozen length (Dlc, return_start, marker spacing) is kept exactly. The target-lane route uses the same arc frame
(projection of its points on the EGO route: reference switch E1-c, |arc - projected station| <= 0.05 m).
"""
import json
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from pathlib import Path

from native_v2_common import arcs, directed, npc_response
from m56.catalog import _digest
from m56.geometry import project_route
from m56.model import FrozenMetricPair, Section, SourceRef
from m56.response import _axis_right


def q6(x):
    return F(round(float(x) * 10 ** 6), 10 ** 6)


def hashed(r):
    return replace(r, hash=_digest({k: getattr(r, k) for k in ('actor_role', 'action_id', 'route', 'targets', 'profile', 'phases')}))


def io_routes(prep, plain, town):
    """(routes {'EGO','EGO_TARGET','NPC'}, rows {'EGO','EGO_TARGET','NPC': (rows, arc)}, continuity ref)."""
    path = Path(prep['routes_v2'])
    rows_all = plain(json.loads(path.read_text(encoding='utf-8')))
    cont = SourceRef(str(path), prep['routes_v2_sha256'], path.stat().st_size, '1', 'claude-g4', 'NATIVE_ROUTE')
    g = prep['geometry']
    dest = {k: F(prep['destinations'][k]) for k in ('EGO', 'NPC')}
    rows, routes = {}, {}
    for role, lane in (('EGO', g['ego_lane']), ('NPC', g['npc_lane'])):
        a = arcs(rows_all[role])
        rows[role] = (rows_all[role], a)
        routes[role] = directed(rows_all[role], a, prep['map_hash'], town, f"{g['road']}/{lane}", cont, dest[role])
    t = rows_all['EGO_TARGET']
    a = [q6(project_route((r['x'], r['y'], r['z']), routes['EGO'])) for r in t]
    assert all(y > x for x, y in zip(a, a[1:])), 'TARGET_ARC_NOT_INCREASING'
    rows['EGO_TARGET'] = (t, a)
    routes['EGO_TARGET'] = directed(t, a, prep['map_hash'], town, f"{g['road']}/{g['target_lane']}", cont, dest['EGO'])
    return routes, rows, cont


def catalog_offset(c, routes, prep=None):
    """Native EGO station of the frozen catalog EGO route's first point (one shift for every frozen arc), plus the
    proposed site-window shift along the travel direction when the preparation records one (0 otherwise)."""
    first = next(r for r in c.responses if r.actor_role == 'EGO').route.transforms[0]
    d = q6(project_route((first.x, first.y, first.z), routes['EGO']))
    shift = ((prep or {}).get('geometry') or {}).get('site_shift_travel_m')
    return d + q6(shift) if shift else d


def _shift(profile, d):
    return {**profile, 'segments': tuple({**s, 'start_arc_m': s['start_arc_m'] + d} for s in profile['segments'])}


def io_responses(c, routes, d):
    """The frozen EGO A/B (program, targets, profiles) on the native routes; every frozen arc + d. Switch routes: the
    TARGET_LANE_CONFIRMED switch -> the native target lane, RETURN_LANE_CONFIRMED -> the native EGO (home) route."""
    out = []
    for r in (x for x in c.responses if x.actor_role == 'EGO'):
        phases = dict(r.phases)
        if phases.get('reference_switches'):
            to = {'TARGET_LANE_CONFIRMED': routes['EGO_TARGET'], 'RETURN_LANE_CONFIRMED': routes['EGO']}
            phases['reference_switches'] = tuple({**s, 'marker_arc_m': s['marker_arc_m'] + d, 'route': to[s['event']],
                                                  'profile': _shift(s['profile'], d)} for s in phases['reference_switches'])
        out.append(hashed(replace(r, route=routes['EGO'], profile=_shift(r.profile, d), phases=phases, hash='')))
    return tuple(out)


def _point(route, station):
    for i, (a, b) in enumerate(zip(route.arc, route.arc[1:])):
        if a <= station <= b:
            s, e = route.transforms[i], route.transforms[i + 1]; u = float((station - a) / (b - a))
            return tuple(p + u * (q - p) for p, q in zip((s.x, s.y, s.z), (e.x, e.y, e.z))), s.yaw
    raise ValueError('STATION_OFF_ROUTE')


def io_geometry(c, prep, routes, d, plain):
    """Axis, lane boxes, domain box, sections, lane_geometry, map_reference, pair. Returns a dict, or {'reason'} (blocked)."""
    ego, tgt = routes['EGO'], routes['EGO_TARGET']
    a_resp = next(r for r in c.responses if r.actor_role == 'EGO' and r.action_id == 'A')
    dec = F(prep['decision_station']); xs = F(prep['X_station']); ret = F(prep['return_start_station'])
    (pi, yaw), (pt, _) = _point(ego, dec), _point(tgt, dec)
    axis = _axis_right(yaw)
    if axis is None:
        return {'reason': 'IO_ROAD_NOT_AXIS_ALIGNED'}
    lat, sign = axis; trv = 1 - lat
    tsg = 1 if (ego.transforms[-1].x, ego.transforms[-1].y)[trv] > (ego.transforms[0].x, ego.transforms[0].y)[trv] else -1
    w = {k: plain(v) for k, v in prep['lane_width_m'].items()}
    ci, ct = pi[lat], pt[lat]
    sep = F(round((ct - ci) * sign * 1000), 1000)
    mid_anchor = prep.get('box_anchor') == 'midpoint'
    if mid_anchor:
        # io-v1.2 (O01/O02 extension prereg, pending Duy): lane boxes centred on the lane centres at the midpoint of
        # [O_DECISION, DESTINATION + 3 m], so a road up to 1 deg off-axis drifts at most half its run inside the box
        # (O02: 1.03 m over decision -> X at 0.84 deg). v1/v1.1 (O03): anchored at O_DECISION.
        anchor = (dec + ego.destination + 3) / 2
        ci, ct = _point(ego, anchor)[0][lat], _point(tgt, anchor)[0][lat]
    moving = [s for s in a_resp.profile['segments'] if s['start_offset_m'] != s['end_offset_m']]
    if len(moving) != 1 or moving[0]['end_offset_m'] != sep:
        return {'reason': 'IO_LANE_SEPARATION_MISMATCH', 'separation_m': sep}
    mid = (ci + ct) / 2  # shared edge: the two boxes touch exactly, never overlap by a rounding
    lo_i, hi_i = sorted((ci - (w['initial'] / 2) * (1 if ct > ci else -1), mid))
    lo_t, hi_t = sorted((mid, ct + (w['target'] / 2) * (1 if ct > ci else -1)))
    tr = [(t.x, t.y)[trv] for r in (ego, tgt) for t in r.transforms]
    t_lo, t_hi = min(tr) - 10., max(tr) + 10.
    zs = [t.z for r in (ego, tgt, routes['NPC']) for t in r.transforms]
    z_lo, z_hi = min(zs) - 1., max(zs) + 3.

    def vbox(t0, t1, l0, l1):
        out = []
        for tv, lv, zv in product((t0, t1), (l0, l1), (z_lo, z_hi)):
            p = [0., 0., zv]; p[trv] = tv; p[lat] = lv; out.append(tuple(p))
        return tuple(out)
    regions = {'EGO_INITIAL': vbox(t_lo, t_hi, lo_i, hi_i), 'EGO_TARGET': vbox(t_lo, t_hi, lo_t, hi_t)}
    l_lo, l_hi = min(lo_i, lo_t), max(hi_i, hi_t)
    if mid_anchor:  # io-v1.2: section planes span both lanes over the whole route (drift included), + 0.5 m
        lats = [(t.x, t.y)[lat] for r in (ego, tgt) for t in r.transforms]
        half = max(w.values()) / 2 + .5
        l_lo, l_hi = min(l_lo, min(lats) - half), max(l_hi, max(lats) + half)

    def section(station):
        p, _ = _point(ego, station)
        verts = []
        for lv, zv in product((l_lo, l_hi), (z_lo, z_hi)):
            v = [0., 0., zv]; v[trv] = p[trv]; v[lat] = lv; verts.append(tuple(v))
        n = [0., 0., 0.]; n[trv] = float(tsg)
        return Section(tuple(verts), tuple(n), station, {})
    t_dec, t_x = _point(ego, dec)[0][trv], _point(ego, xs)[0][trv]
    region = vbox(min(t_dec, t_x), max(t_dec, t_x), l_lo, l_hi)
    sections = {'O_DECISION': section(dec), 'O_RETURN_START': section(ret), 'X': section(xs),
                'DESTINATION': section(ego.destination)}
    normals = tuple((-(b.y - a.y), b.x - a.x, 0.) for a, b in zip(ego.transforms, ego.transforms[1:]))
    reference = {'method': 'segment-map-normal-v1', 'route': ego, 'normals': normals, 'refs': ego.continuity}  # admitted SourceRefs
    spec = (('v_mean_E', 'e_lat_peak'), ('m/s', 'm'), ('mean_speed', 'map_lateral_peak'), (('TRIGGER', 'X_END'),) * 2,
            'map:' + _digest(reference))
    pair = FrozenMetricPair(*spec, _digest(spec), 'APPROVED_PROPOSAL_NOT_READY')
    lane_geometry = {'EGO': {'separation_m': sep, 'lane_width_m': {k: F(str(v)) for k, v in w.items()}}}
    return {'axis': (trv, tsg), 'lateral_axis': (lat, sign), 'regions': regions, 'region': region, 'sections': sections,
            'map_reference': reference, 'pair': pair, 'lane_geometry': lane_geometry, 'separation_m': sep,
            'z': (z_lo, z_hi), 'decision': dec, 'X': xs, 'return_start': ret}


def io_phase_plans(response, rows, every=2.):
    """Stock plan per reference switch: the switched lane's waypoints (road/lane/s) every 2 m from the switch marker."""
    from native_v2_common import plan_rows
    key = {'TARGET_LANE_CONFIRMED': 'EGO_TARGET', 'RETURN_LANE_CONFIRMED': 'EGO'}
    return {s['cause']: plan_rows(*rows[key[s['event']]], float(s['marker_arc_m']), every)
            for s in response.phases.get('reference_switches', ())}


def io_npc(c, routes):
    return npc_response(c.category, c.parameters['vN'].values[0], routes['NPC'])
