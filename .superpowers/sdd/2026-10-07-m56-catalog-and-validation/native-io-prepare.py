"""M56 I/O PREPARATION, pilot O (design docs/m56/DESIGN_M56_IO_TOOLING_20261026.md). Preparation only: no A/B, no
TRIGGER can fire (probe fixtures carry no domain and no metric pair). Duy 2026-10-26: "dựng tooling I/O với pilot O,
chỉ chuẩn bị". Every value Claude chooses here is listed in the I/O recipe prereg before any A/B.

Per O scene, on Claude's own server (2610), in spec 7.4 road-s geometry (site road R, EGO lanes initial->target,
NPC lane, front_t0 / X road-s, Dlc, return_start, gap):
  1. lane-centre routes from CARLA waypoints (chord <= 0.24 m): EGO initial lane from front_t0 - RUNIN_M to X + 20 m,
     EGO target lane over the same road-s span, NPC lane from 60 m behind its first guess to 30 m past the EGO end;
  2. probe 1 (real runner, catalog EGO B program relabelled A = NOMINAL only, catalog NPC program): EGO plateau before
     the decision (E6 window, PID grid as v5 erratum 2 / P-NPC), t0 = time the EGO front reaches front_t0;
  3. NPC start shifted along its lane so that its rear is `gap` ahead of the EGO front at t0 (straight, flat road: the
     NPC kinematics do not depend on its start);
  4. probe 2 -> targets, readiness markers (runner predicate), EGO ready before the decision, realised gap at t0.
Writes outputs/m56_v2_prepare_<town>_<stamp>/<scene>/prepare.json (+ routes-io.json).
  python -I native-io-prepare.py Town06 M56-P-O03
"""
import importlib.util, json, math, sys, traceback
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

here = Path(__file__).resolve().parent
TOWN, SCENES = sys.argv[1], sys.argv[2].split(',')
sys.argv = [str(here / 'native-v2-prepare.py'), TOWN]
_spec = importlib.util.spec_from_file_location('v2prep', here / 'native-v2-prepare.py')
P = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(P)  # shared root, authority, probe machinery

from native_v2_common import (NO_RENDER, V6, NPC_PID_GRID, REV, _step, _wp_row, arcs, body_record, directed, load, npc_response,  # noqa: E402
                              own_server, ownership, write_ref)
from m56 import runtime  # noqa: E402
from m56.catalog import _digest  # noqa: E402
from m56.metrics import _metric_station, _speed  # noqa: E402
from m56.model import Transform6, decode_record, encode_record, load_json  # noqa: E402
from m56.response import _f32  # noqa: E402

RUNIN_M = 100.          # EGO start = front_t0 - RUNIN_M * vE / 9.375 m of its lane, rounded up to 1 m (O03: 100 m;
                        # O01/O02 extension 2026-10-27: the 16 s probe must reach the decision at vE 6 / 7.5 m/s)
EGO_TAIL_M = 20.        # io-v1.1: EGO route ends X + gap + 2 bodies + 20 m (v1: X + 20 m). In B the NPC drives ~gap ahead;
                        # its front must stay on the EGO route through X_END or min_front_gap is unknown (O03 2026-10-27)
NPC_BACK_M, NPC_TAIL_M = 60., 30.
log = P.log


def io_candidates(ids):
    out = []
    for item in load_json(REV)['candidates']:
        if item['id'] in ids:
            # F2-5 (409911e): the index k (units 'index', fill20-v1 I/O) is not a model unit; dropped before decoding (its
            # value stays in the other parameters' rationale). The revision builder applies the same rule (f25_index_k).
            item = {**item, 'parameters': {n: p for n, p in item['parameters'].items() if p.get('units') != 'index'}}
            c = decode_record('Candidate', item)
            assert not hasattr(c, 'errors'), (item['id'], c)
            out.append(c)
    return out


def geometry_fill(c, m):
    """io-v1.3 (PREREG_M56_IO_RECIPE_V1_3_FILL_O_20261107): an O scene of the fill20/v2/v3 catalog (no spec 7.4 road-s
    table). The site window is the one FROZEN in the catalog EGO A profile (no shift): decision = start of its lane-change
    segment (road-s of the catalog route's first point + that arc); Dlc = the frozen segment length (= 3 vE, spec 7.4);
    gap = G_m; return_start = returnstart_m; X = decision + return_start + Dlc + 3.75 (spec 7.4)."""
    import carla
    p = {k: v.values[0] for k, v in c.parameters.items()}
    rr = next(a for a in c.actors if a.role == 'EGO').route_recipe
    road, (e0, e1) = int(rr['road']), [int(x) for x in rr['lanes']]
    sign = 1 if e0 < 0 else -1
    assert rr['travel'] == ('increasing s' if sign > 0 else 'decreasing s'), rr
    A = next(r for r in c.responses if r.actor_role == 'EGO' and r.action_id == 'A')
    seg = next(s for s in A.profile['segments'] if s['end_offset_m'] != s['start_offset_m'])
    assert seg['length_m'] == 3 * p['vE'], (seg['length_m'], p['vE'])
    # The catalog route starts AT the road boundary (s ~ 0), where CARLA may project onto the adjoining connector: project
    # the first catalog point at least 1 m inside, and take its arc back off (straight lane: arc = road-s distance).
    i = next(j for j, a in enumerate(A.route.arc) if a >= 1)
    pt = A.route.transforms[i]
    w = m.get_waypoint(carla.Location(pt.x, pt.y, pt.z), project_to_road=True, lane_type=carla.LaneType.Driving)
    assert (w.road_id, w.lane_id) == (road, e0), ('CATALOG_ROUTE_NOT_ON_SITE_LANE', w.road_id, w.lane_id)
    first_s = w.s - sign * float(A.route.arc[i])
    dec_s = first_s + sign * float(seg['start_arc_m'])
    xd = float(p['returnstart_m']) + float(seg['length_m']) + 3.75
    return {'road': road, 'ego_lane': e0, 'target_lane': e1, 'npc_lane': e0, 'sign': sign, 'through': True,
            'catalog_first_point_s': first_s, 'front_t0_s': dec_s, 'X_s': dec_s + sign * xd, 'Dlc': seg['length_m'],
            'gap': float(p['G_m']), 'return_start': p['returnstart_m'], 'vE': p['vE'], 'vN': p['vN'], 'k': p.get('k')}


def road_length(m, road, _cache={}):
    """Length of an OpenDRIVE road of the loaded map (parsed once from m.to_opendrive())."""
    if not _cache:
        import xml.etree.ElementTree as ET
        _cache.update({int(r.get('id')): float(r.get('length')) for r in ET.fromstring(m.to_opendrive()).iter('road')})
    return _cache[road]


MAX_YAW_DEV = 1.  # io-v1.3: every row of a native I/O route within 1 deg of the main-road heading (consumer axis rule: 1 deg)


def lane_rows_through(m, road, lane, s_from, s_to, strict=True):
    """io-v1.3: lane_rows that may leave the site road. Inside the road it is lane_rows; beyond its ends it follows the
    CARLA lane continuation (next/previous waypoint with the closest yaw) through junction connectors by the missing
    distance. A row more than MAX_YAW_DEV from the main-road heading: strict -> AssertionError (scene BLOCKED, EGO);
    not strict -> the route is cut before it (NPC tail, recorded). Returns (rows, cut_m)."""
    sign, L = (1 if lane < 0 else -1), road_length(m, road)
    lo, hi = .5, L - .5  # > one 0.2 m lane_rows step from each end, so lane_rows never steps off the road
    clamp = lambda s: min(max(s, lo), hi)
    a0, a1 = clamp(s_from), clamp(s_to)
    w0 = m.get_waypoint_xodr(road, lane, a0)
    assert w0 is not None, f'NO_WAYPOINT:{road}/{lane}@{a0}'
    yaw0 = w0.transform.rotation.yaw
    dev = lambda w: abs((w.transform.rotation.yaw - yaw0 + 180) % 360 - 180)
    best = lambda ws, w: min(ws, key=lambda p: abs((p.transform.rotation.yaw - w.transform.rotation.yaw + 180) % 360 - 180))

    def walk(w, forward, metres):
        out, d = [], 0.
        while d < metres - 1e-9:
            nxt = _step(w, forward)
            if not nxt:
                return out, metres - d, 'LANE_ENDS'
            p = best(nxt, w)
            if dev(p) > MAX_YAW_DEV:
                return out, metres - d, 'YAW'
            d += math.dist((p.transform.location.x, p.transform.location.y), (w.transform.location.x, w.transform.location.y))
            w = p; out.append(_wp_row(w))
        return out, 0., None
    back = sign * (a0 - s_from)
    pre, miss, why = walk(w0, False, back) if back > 0 else ([], 0., None)
    assert not miss, f'RUNIN_NOT_STRAIGHT:{road}/{lane}:{why}:{miss:.2f}m'
    rows = lane_rows(m, road, lane, a0, a1)
    fwd = sign * (s_to - a1)
    post, miss, why = walk(m.get_waypoint_xodr(road, lane, rows[-1]['s']), True, fwd) if fwd > 0 else ([], 0., None)
    assert not (miss and strict), f'TAIL_NOT_STRAIGHT:{road}/{lane}:{why}:{miss:.2f}m'
    return pre[::-1] + rows + post, miss


def geometry(c, m=None):
    """Spec 7.4 site geometry of an O scene from the frozen candidate."""
    if 'aliases' not in c.environment:
        return geometry_fill(c, m)
    road = int(c.site_id.split('-R')[1])
    lanes = c.environment['aliases']['lanes']            # e.g. 'E-3→-4→-3,N-3'
    e, n = lanes.split(',')
    e_lanes = [int(x) for x in e[1:].split('→')]
    n_lane = int(n[1:])
    p = {k: v.values[0] for k, v in c.parameters.items()}
    # Site-window shift PROPOSAL (I/O recipe extension prereg, pending Duy): front_t0 and X move together by `shift` m of
    # road-s, every spec distance kept; recorded in prepare.json. Default 0 = the spec window (O03 bytes unchanged).
    import os
    shift = dict(kv.split('=') for kv in filter(None, os.environ.get('M56_IO_SITE_SHIFT', '').split(','))).get(c.id)
    shift = float(shift) if shift else 0.
    out = {'road': road, 'ego_lane': e_lanes[0], 'target_lane': e_lanes[1], 'npc_lane': n_lane,
            'sign': 1 if e_lanes[0] < 0 else -1,             # negative lanes increase road-s
            'front_t0_s': float(p['front_t0']) + shift, 'X_s': float(p['X']) + shift, 'Dlc': p['Dlc'], 'gap': float(p['gap']),
            'return_start': p.get('return_start'), 'vE': p['vE'], 'vN': p['vN']}
    if shift:
        out.update(site_shift_s=shift, site_shift_travel_m=out['sign'] * shift)
    return out


BOX_ANCHOR = __import__('os').environ.get('M56_IO_BOX_ANCHOR')  # 'midpoint' = io-v1.2 lane boxes (pending Duy); unset = v1.1


def lane_rows(m, road, lane, s_from, s_to):
    """Lane-centre waypoint rows of `road`/`lane` from road-s s_from to s_to in the driving direction (chord <= 0.24)."""
    w = m.get_waypoint_xodr(road, lane, s_from)
    assert w is not None, f'NO_WAYPOINT:{road}/{lane}@{s_from}'
    rows, sign = [_wp_row(w)], (1 if lane < 0 else -1)
    while (s_to - w.s) * sign > 0:
        nxt = [p for p in _step(w, True) if p.road_id == road and p.lane_id == lane]
        assert nxt, f'LANE_ENDS:{road}/{lane}@{w.s:.2f}'
        w = nxt[0]; rows.append(_wp_row(w))
    return rows


def station_at_s(rows, arc, s, road=None):
    """Route arc of road-s s (linear in s between rows). road: only rows of that road (io-v1.3 routes leave the site road;
    road-s of another road would match by accident); a single-road route is unaffected."""
    for (r0, a0), (r1, a1) in zip(zip(rows, arc), zip(rows[1:], arc[1:])):
        if road is not None and not r0['road'] == r1['road'] == road:
            continue
        lo, hi = sorted((r0['s'], r1['s']))
        if lo <= s <= hi:
            f = 0. if r1['s'] == r0['s'] else (s - r0['s']) / (r1['s'] - r0['s'])
            return F(round((float(a0) + f * (float(a1) - float(a0))) * 10 ** 6), 10 ** 6)
    raise AssertionError(f'S_OUTSIDE_ROUTE:{s}')


def pose_on(world, rows, i):
    import carla
    a, b = rows[i], rows[i + 1]
    L = math.dist((a['x'], a['y']), (b['x'], b['y'])); along = .02
    t = Transform6(a['x'] + (b['x'] - a['x']) * along / L, a['y'] + (b['y'] - a['y']) * along / L, a['z'], 0., a['yaw'], 0.)
    g = world.ground_projection(carla.Location(t.x, t.y, t.z + 2.), 10.)
    z = (g.location.z if g is not None else t.z) + .01
    pose_on.grounds[id(rows)] = None if g is None else g.location.z
    return Transform6(_f32(t.x), _f32(t.y), _f32(z), 0., _f32(t.yaw), 0.)


pose_on.grounds = {}


def s_at_station(rows, arc, station, road=None):
    """Road-s of a route station (inverse of station_at_s; linear between rows); road: as station_at_s."""
    for (r0, a0), (r1, a1) in zip(zip(rows, arc), zip(rows[1:], arc[1:])):
        if road is not None and not r0['road'] == r1['road'] == road:
            continue
        if float(a0) <= station <= float(a1):
            return r0['s'] + (station - float(a0)) / (float(a1) - float(a0)) * (r1['s'] - r0['s'])
    return None


def relabel(response, route, action_id=None):
    r = replace(response, route=route, action_id=action_id or response.action_id, hash='')
    return replace(r, hash=_digest({k: getattr(r, k) for k in ('actor_role', 'action_id', 'route', 'targets', 'profile', 'phases')}))


def rear_station(actor, route):
    from m56.geometry import project_route, world_vertices
    s = [project_route(p, route) for p in world_vertices(actor.body, actor.pose)]
    s = [float(x) for x in s if not hasattr(x, 'reasons')]
    return min(s) if s else None


def prepare_o(c, client, proc, start, world, m, identity, body, bbox):
    g = geometry(c, m); sg = g['sign']; L = 2 * bbox['extent'][0]; R = g['road']
    runin = float(math.ceil(RUNIN_M * float(g['vE']) / 9.375 - 1e-9))
    (P.root / c.id).mkdir(parents=False, exist_ok=True)
    out = {'scene': c.id, 'town': c.town, 'category': c.category, 'recipe': 'io-v1',
           'recipe_version': 'io-v1.2' if BOX_ANCHOR == 'midpoint' else 'io-v1.1',
           **({'box_anchor': 'midpoint'} if BOX_ANCHOR == 'midpoint' else {}), 'geometry': g, 'bbox': bbox,
           'runin_m': runin, 'map_hash': identity.map, 'carla_no_rendering_mode': NO_RENDER,
           **({'m56_recipe': 'v6'} if V6 else {})}
    s_e0, s_end = g['front_t0_s'] - sg * runin, g['X_s'] + sg * (g['gap'] + 2 * L + EGO_TAIL_M)
    s_n0 = g['front_t0_s'] + sg * (g['gap'] + L)            # first guess: NPC rear `gap` ahead at time 0
    if g.get('through'):  # io-v1.3: run-in / tails may continue through straight junction connectors
        rows = {'EGO': lane_rows_through(m, R, g['ego_lane'], s_e0, s_end)[0],
                'EGO_TARGET': lane_rows_through(m, R, g['target_lane'], s_e0, s_end)[0]}
        rows['NPC'], cut = lane_rows_through(m, R, g['npc_lane'], s_n0 - sg * NPC_BACK_M, s_end + sg * NPC_TAIL_M, strict=False)
        out.update(npc_tail_cut_m=cut, roads={k: list(dict.fromkeys(r['road'] for r in v)) for k, v in rows.items()})
    else:
        rows = {'EGO': lane_rows(m, g['road'], g['ego_lane'], s_e0, s_end),
                'EGO_TARGET': lane_rows(m, g['road'], g['target_lane'], s_e0, s_end),
                'NPC': lane_rows(m, g['road'], g['npc_lane'], s_n0 - sg * NPC_BACK_M, s_end + sg * NPC_TAIL_M)}
    arc = {k: arcs(v) for k, v in rows.items()}
    dec = station_at_s(rows['EGO'], arc['EGO'], g['front_t0_s'], R)
    xs = station_at_s(rows['EGO'], arc['EGO'], g['X_s'], R)
    out.update(decision_station=dec, X_station=xs, return_start_station=(dec + g['return_start'])
               if g['return_start'] is not None else None)
    k0 = next(i for i, r in enumerate(rows['NPC']) if r['road'] == R and (r['s'] - s_n0) * sg >= 0)
    cont = write_ref(P.root / c.id / 'routes-io-probe1.json', rows, 'NATIVE_ROUTE')
    notation = {'EGO': f"{g['road']}/{g['ego_lane']}", 'NPC': f"{g['road']}/{g['npc_lane']}"}

    def routes_for(npc_k):
        r = {'EGO': directed(rows['EGO'], arc['EGO'], identity.map, c.town, notation['EGO'], cont, F(math.ceil((xs + 5) * 1000), 1000))}
        nr, na = rows['NPC'][npc_k:], [a - arc['NPC'][npc_k] for a in arc['NPC'][npc_k:]]
        r['NPC'] = directed(nr, na, identity.map, c.town, notation['NPC'], cont, na[-1] - 5)
        return r, {'EGO': (rows['EGO'], arc['EGO']), 'NPC': (nr, na)}
    routes, prow = routes_for(k0)
    poses = {'EGO': pose_on(world, rows['EGO'], 0), 'NPC': pose_on(world, prow['NPC'][0], 0)}
    ego_b = next(r for r in c.responses if r.actor_role == 'EGO' and r.action_id == 'B')
    npc = npc_response(c.category, g['vN'], routes['NPC'])     # prereg v2 2.2 annex NPC program (v5 bytes)
    responses = (relabel(ego_b, routes['EGO'], 'A'), relabel(npc, routes['NPC']))

    def run(label, rts, pr, ps, ng=None, eg=None):
        resp = (relabel(ego_b, rts['EGO'], 'A'), relabel(npc, rts['NPC']))
        return P.probe(client, proc, start, world, identity, c.id, rts, pr, ps, resp, label, None, ng, eg)
    p1 = run('probe1', routes, prow, poses)
    if not p1:
        out.update(status='BLOCKED_FIXTURE', reason='PROBE1_NO_FRAMES'); return P.finish(c, out)
    # PID grids exactly as the C/L/M preparation (v5 erratum 2 for the EGO, P-NPC for the NPC); e_entry = decision, G = 0
    ego_gains, npc_gains, grid = None, None, []
    plat = P.plateaus(p1, routes, body, float(dec), 0, npc_until='last')
    grid.append({'who': 'stock', 'EGO_range': plat.get('EGO_range'), 'NPC_range': plat.get('NPC_range')})
    if plat.get('EGO_range', 1.) > .10:
        for ei, eg in enumerate(NPC_PID_GRID[1:], 1):
            q = run(f'probe1-egopid{ei}', routes, prow, poses, None, eg)
            pq = P.plateaus(q, routes, body, float(dec), 0, npc_until='last') if q else {}
            grid.append({'who': 'EGO', 'gains': [str(x) for x in eg], 'EGO_range': pq.get('EGO_range')})
            if q and pq.get('EGO_range', 1.) <= .10:
                ego_gains, p1, plat = eg, q, pq; break
    if plat.get('NPC') is None:
        for gi, ng in enumerate(NPC_PID_GRID[1:], 1):
            q = run(f'probe1-pid{gi}', routes, prow, poses, ng, ego_gains)
            pq = P.plateaus(q, routes, body, float(dec), 0, npc_until='last') if q else {}
            grid.append({'who': 'NPC', 'gains': [str(x) for x in ng], 'NPC_range': pq.get('NPC_range')})
            if q and pq.get('NPC') is not None:
                npc_gains, p1, plat = ng, q, pq; break
    out.update(pid_grid=grid, ego_longitudinal=None if ego_gains is None else [str(x) for x in ego_gains],
               npc_longitudinal=None if npc_gains is None else [str(x) for x in npc_gains], probe1=plat)
    if plat.get('reason') or plat.get('NPC') is None:
        out.update(status='BLOCKED_FIXTURE', reason=plat.get('reason') or 'READINESS_NOT_STEADY'); return P.finish(c, out)
    # t0 = the first frame whose EGO front reaches the decision station
    def t0_and_rear(frames, rts):
        for f in frames:
            ego = next(x for x in f.actors if x.role == 'EGO')
            if P.front_station(ego, rts['EGO']) >= float(dec):
                npc_a = next(x for x in f.actors if x.role == 'NPC')
                return float(f.simtime), rear_station(npc_a, rts['NPC']), P.front_station(ego, rts['EGO'])
        return None, None, None
    t0, rear, _ = t0_and_rear(p1, routes)
    if t0 is None:
        out.update(status='BLOCKED_FIXTURE', reason='EGO_NOT_AT_DECISION_IN_PROBE1'); return P.finish(c, out)
    # decision road-s on the NPC lane, in the probe-1 NPC route frame (the route starts at k0, ahead of the decision)
    dec_npc = station_at_s(rows['NPC'], arc['NPC'], g['front_t0_s'], R) - arc['NPC'][k0]
    shift = float(dec_npc) + g['gap'] - rear                   # metres along the NPC lane (positive = further ahead)
    s_n = rows['NPC'][k0]['s'] + sg * shift
    k = next(i for i, r in enumerate(rows['NPC']) if r['road'] == R and (r['s'] - s_n) * sg >= 0)
    out.update(t0_probe1=t0, npc_rear_at_t0_probe1=rear, npc_shift_m=shift, npc_start_s=rows['NPC'][k]['s'])
    routes2, prow2 = routes_for(k)
    poses2 = {'EGO': poses['EGO'], 'NPC': pose_on(world, prow2['NPC'][0], 0)}
    grounds = {'EGO': pose_on.grounds[id(rows['EGO'])], 'NPC': pose_on.grounds[id(prow2['NPC'][0])]}
    cont2 = write_ref(P.root / c.id / 'routes-io.json', {'EGO': rows['EGO'], 'EGO_TARGET': rows['EGO_TARGET'],
                                                          'NPC': prow2['NPC'][0]}, 'NATIVE_ROUTE')
    p2 = run('probe2', routes2, prow2, poses2, npc_gains, ego_gains)
    plat2 = P.plateaus(p2, routes2, body, float(dec), 0) if p2 else {'reason': 'PROBE2_NO_FRAMES'}
    out['probe2'] = plat2
    if plat2.get('reason'):
        out.update(status='BLOCKED_FIXTURE', reason=plat2['reason']); return P.finish(c, out)
    targets = {'EGO': F(round(plat2['EGO'] * 1000), 1000), 'NPC': F(round(plat2['NPC'] * 1000), 1000)}
    ready = P.first_ready(p2, routes2, targets, boundary_t2=float(p2[0].simtime) - .05)
    if ready is None:
        out.update(status='BLOCKED_FIXTURE', reason='READINESS_NOT_REACHED_IN_PROBE2', targets=targets)
        return P.finish(c, out)
    fr, markers = ready
    ego_ready = P.front_station(next(x for x in fr.actors if x.role == 'EGO'), routes2['EGO'])
    t0b, rear_b, front_b = t0_and_rear(p2, routes2)
    # realised gap at t0 in road-s (the two stations live on different routes): NPC rear - EGO front
    gap_real = None if t0b is None else sg * (s_at_station(*prow2['NPC'], rear_b, R) - s_at_station(rows['EGO'], arc['EGO'], front_b, R))
    lw = {lane: m.get_waypoint_xodr(g['road'], lane, g['front_t0_s']).lane_width for lane in (g['ego_lane'], g['target_lane'])}
    out.update(targets=targets, markers=markers, ready_time=float(fr.simtime), ego_front_at_ready=ego_ready,
               ego_ready_before_decision=ego_ready < float(dec), t0_probe2=t0b, gap_at_t0_probe2=gap_real,
               lane_width_m={'initial': lw[g['ego_lane']], 'target': lw[g['target_lane']]},
               routes_v2=str(cont2.uri), routes_v2_sha256=cont2.sha256, grounds=grounds,
               poses={k_: encode_record(v) for k_, v in poses2.items()},
               destinations={'EGO': routes2['EGO'].destination, 'NPC': routes2['NPC'].destination})
    if not out['ego_ready_before_decision']:
        out.update(status='BLOCKED_FIXTURE', reason='EGO_READY_AFTER_DECISION'); return P.finish(c, out)
    out['status'] = 'PREPARED'
    return P.finish(c, out)


def main():
    scenes = io_candidates(SCENES)
    log(event='SCENES', town=TOWN, ids=[c.id for c in scenes])
    with own_server(log) as (client, proc, start):
        world = load(client, TOWN); m = world.get_map()
        identity = runtime.ReadOnlyCarlaBackend(client, ownership(proc, start, world)).identity()
        settings = world.get_settings(); settings.synchronous_mode, settings.fixed_delta_seconds = True, .05
        world.apply_settings(settings)
        car = world.spawn_actor(world.get_blueprint_library().find('vehicle.audi.a2'), m.get_spawn_points()[0]); world.tick()
        b = car.bounding_box
        bbox = {'location': [b.location.x, b.location.y, b.location.z], 'extent': [b.extent.x, b.extent.y, b.extent.z],
                'rotation': [b.rotation.pitch, b.rotation.yaw, b.rotation.roll]}
        car.destroy(); world.tick(); settings.synchronous_mode = False; world.apply_settings(settings)
        body = body_record(bbox, write_ref(P.root / 'a2-bbox.json', {'town': TOWN, 'bbox': bbox}, 'NATIVE_BODY'))
        for c in scenes:
            try:
                assert c.category == 'O', 'pilot: O scenes only'
                prepare_o(c, client, proc, start, world, m, identity, body, bbox)
            except Exception as e:  # recorded, scene stays blocked; never retried with other values
                log(event='SCENE_ERROR', scene=c.id, error=repr(e), trace=traceback.format_exc()[-2500:])
    (P.root / 'prepare-log.json').write_text(json.dumps(P.log_rows, indent=1, default=str), encoding='utf-8')
    print('DONE', P.root)


if __name__ == '__main__':
    main()
