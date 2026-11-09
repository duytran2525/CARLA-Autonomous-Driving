"""M56 A-SEL2 F native fixture helpers (PLAN_M56_F_NATIVE_TOOLING_20261109.md step 1; PREREG_M56_F_ASEL2_20261109.md part 1).
F01 only. Inputs: an 'f-v1' prepare.json from native-f-prepare.py (routes-f.json rows, sections_m, poses, markers)."""
import json
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from pathlib import Path

from native_v2_common import RELEASE, arcs, directed
from m56.catalog import _digest
from m56.geometry import project_route
from m56.model import FrozenMetricPair, FrozenResponse, Section, SourceRef
from m56.response import _axis_right

ZERO = {'method': 'quintic-arc-v1', 'segments': ({'start_arc_m': F(0), 'length_m': F(1), 'start_offset_m': F(0),
                                                  'end_offset_m': F(0)},)}
HALF_LANE = 2.5  # section half span across the lane (m): lane half width 1.75 + 0.75; bodies are 1.8 m wide


def q6(x):
    return F(round(float(x) * 10 ** 6), 10 ** 6)


def hashed(r):
    return replace(r, hash=_digest({k: getattr(r, k) for k in ('actor_role', 'action_id', 'route', 'targets', 'profile', 'phases')}))


def f_routes(prep, plain, town):
    """(routes {'EGO','NPC'}, rows {'EGO','NPC': (rows, arc)}, continuity ref). EGO destination = the prepared DESTINATION
    station; NPC destination = its route end - 5 m (as in the probes)."""
    path = Path(prep['routes_f'])
    rows_all = json.loads(path.read_text(encoding='utf-8'))
    cont = SourceRef(str(path), prep['routes_f_sha256'], path.stat().st_size, '1', 'claude-g4', 'NATIVE_ROUTE')
    site = prep['site']; note = f"{site['road']}/{site['lane']}"
    rows, routes = {}, {}
    for role in ('EGO', 'NPC'):
        a = arcs(rows_all[role]); rows[role] = (rows_all[role], a)
        dest = q6(plain(prep['sections_m']['DESTINATION']['station'])) if role == 'EGO' else a[-1] - 5
        routes[role] = directed(rows_all[role], a, prep['map_hash'], town, note, cont, dest)
    return routes, rows, cont


def f_responses(c, routes):
    """The frozen EGO A/B programs and targets of the candidate on the native EGO route (zero lateral profile)."""
    return tuple(hashed(replace(r, route=routes['EGO'], profile=ZERO, hash='')) for r in c.responses if r.actor_role == 'EGO')


def f_npc(mech, vN, route, policy_hash):
    """F01 NPC_COMMON (response.py _f_script_contract): SETTLE 0 -> NOMINAL vN after CAPTURE_START + release ->
    F01_BRAKE 0 at F01_BRAKE_MARKER -> NPC_RESTART vN at NPC_F01_STOP_HOLD_CONFIRMED."""
    assert mech == 'F01', mech
    rows = ({'cause': 'NOMINAL', 'after_event': 'CAPTURE_START', 'delay_s': RELEASE, 'requires': ()},
            {'cause': 'F01_BRAKE', 'after_event': 'F01_BRAKE_MARKER', 'delay_s': F(0), 'requires': ()},
            {'cause': 'NPC_RESTART', 'after_event': 'NPC_F01_STOP_HOLD_CONFIRMED', 'delay_s': F(0), 'requires': ()})
    phases = {'category': 'F', 'program': {'method': 'ordered-event-program-v1', 'initial': 'SETTLE', 'transitions': rows},
              'f_script': {'mechanism': 'F01', 'policy_hash': policy_hash}, 'brake': 'F01_BRAKE'}
    return hashed(FrozenResponse('NPC', 'NPC_COMMON', route,
                                 {'SETTLE': F(0), 'NOMINAL': vN, 'F01_BRAKE': F(0), 'NPC_RESTART': vN}, ZERO, phases, ''))


def _point(route, station):
    for i, (a, b) in enumerate(zip(route.arc, route.arc[1:])):
        if a <= station <= b:
            s, e = route.transforms[i], route.transforms[i + 1]; u = float((station - a) / (b - a))
            return tuple(p + u * (q - p) for p, q in zip((s.x, s.y, s.z), (e.x, e.y, e.z)))
    raise ValueError('STATION_OFF_ROUTE')


def f_geometry(prep, routes, plain):
    """Axis-aligned domain box, F01 sections (planes across the lane), metric pair. {'reason'} when blocked."""
    ego, npc = routes['EGO'], routes['NPC']
    axis = _axis_right(ego.transforms[0].yaw)
    if axis is None or any(_axis_right(t.yaw) != axis for r in (ego, npc) for t in r.transforms):
        return {'reason': 'F_ROAD_NOT_AXIS_ALIGNED'}
    lat, _ = axis; trv = 1 - lat
    tsg = 1 if (ego.transforms[-1].x, ego.transforms[-1].y)[trv] > (ego.transforms[0].x, ego.transforms[0].y)[trv] else -1
    lats = [(t.x, t.y)[lat] for r in (ego, npc) for t in r.transforms]
    l_lo, l_hi = min(lats) - HALF_LANE, max(lats) + HALF_LANE
    zs = [t.z for r in (ego, npc) for t in r.transforms]
    z_lo, z_hi = min(zs) - 1., max(zs) + 3.
    sm = {k: (v['route'], plain(v['station'])) for k, v in prep['sections_m'].items()}

    def section(role, station):
        p = _point(routes[role], q6(station))
        verts = []
        for lv, zv in product((l_lo, l_hi), (z_lo, z_hi)):
            v = [0., 0., zv]; v[trv] = p[trv]; v[lat] = lv; verts.append(tuple(v))
        n = [0., 0., 0.]; n[trv] = float(tsg)
        st = ego.destination if role == 'EGO' else q6(project_route(p, ego))  # every section in the EGO station frame
        return Section(tuple(verts), tuple(n), st, {})
    sections = {k: section(*sm[k]) for k in ('F01_BRAKE_START', 'F01_END', 'DESTINATION')}
    # domain box: along travel from 1 m past the NPC route start to 1 m before the shorter route end; across both lanes
    ends = [(r.transforms[k].x, r.transforms[k].y)[trv] for r in (ego, npc) for k in (0, -1)]
    a = (npc.transforms[0].x, npc.transforms[0].y)[trv] + tsg * 1.
    e_end, n_end = (ego.transforms[-1].x, ego.transforms[-1].y)[trv], (npc.transforms[-1].x, npc.transforms[-1].y)[trv]
    b = (min(e_end, n_end) if tsg > 0 else max(e_end, n_end)) - tsg * 1.
    region = []
    for tv, lv, zv in product(sorted((a, b)), (l_lo, l_hi), (z_lo, z_hi)):
        v = [0., 0., zv]; v[trv] = tv; v[lat] = lv; region.append(tuple(v))
    spec = (('a_peak_025', 'g_front_min_m'), ('m/s^2', 'm'), ('peak_decel_025', 'min_front_gap'),
            (('TRIGGER', 'F01_N_CLEAR'),) * 2, 'route:' + _digest(ego))
    pair = FrozenMetricPair(*spec, _digest(spec), 'APPROVED_PROPOSAL_NOT_READY')
    region = tuple(region)
    return {'region': region, 'sections': sections, 'pair': pair, 'z': (z_lo, z_hi), 'axis': (trv, tsg), 'ends': ends,
            'driving_regions': {'EGO': (region,), 'NPC': (region,)}}
