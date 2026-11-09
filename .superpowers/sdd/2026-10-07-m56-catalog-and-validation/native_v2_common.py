"""Shared pieces of the M56 runtime-recipe v2 driver (prereg d1c91ac, errata 737acbc, E5). Own server 2610 only."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from fractions import Fraction as F
from itertools import product
from pathlib import Path
import hashlib, json, math, socket, subprocess, sys, time

import os
WORK = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1')
WS = WORK / '.superpowers/sdd/2026-10-07-m56-catalog-and-validation'
# M56_CODE: optional checkout whose m56 package is imported (v5 native work before the merge: m56-v5-dev at a recorded
# commit, byte-identical to the post-merge product). Default = WORK (unchanged behaviour for every existing chain).
CODE = Path(os.environ.get('M56_CODE', str(WORK)))
for p in (str(WORK), str(WS), str(CODE)):
    if p not in sys.path:
        sys.path.insert(0, p)
import xodr_routes as xr  # noqa: E402
from m56 import runtime  # noqa: E402
from m56.catalog import _digest  # noqa: E402
from m56.geometry import _rotation_distance  # noqa: E402
from m56.model import (BodyRecord, BoundCertificate, CandidateRevision, DirectedRoute, FrozenResponse, LaneRef,  # noqa: E402
                       OwnershipReceipt, PolicyBundle, ReviewRecord, SourceRef, Transform6, decode_record, encode_record,
                       load_json)

EXE, RPC, WRITER = Path('E:/Carla/CarlaUE4.exe'), 2610, 'm56-claude'
OPS = (*runtime.READ_OPS, 'SETTINGS', 'LOAD_MAP', 'SPAWN', 'TICK', 'APPLY', 'DESTROY', 'VALIDATE_AB', 'tick', 'observe')
REV = Path(os.environ.get('M56_REV', str(WORK / 'outputs/m56_c0_partial_20261022T120227Z/c0-partial-frozen-revision.json')))
PREREG = WORK / 'docs/m56/PREREG_M56_RUNTIME_RECIPE_V2_20261023.md'
REVIEWER, DATE = 'CLAUDE_REVIEW_UNDER_DUY_DELEGATION', '2026-10-23'
A_REF = F(3, 2)
NOMINAL = {'C': F(4), 'L': F(2), 'M': F(4)}
RELEASE = F(21, 20)


def now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_ref(path, obj, kind, method='claude-g4'):
    data = (json.dumps(encode_record(obj), indent=1, sort_keys=True, default=str) + '\n').encode()
    with open(path, 'xb') as f:
        f.write(data)
    return SourceRef(str(path), hashlib.sha256(data).hexdigest(), len(data), '1', method, kind)


def candidates(categories=('C', 'L')):
    """C/L candidates of the frozen partial revision, decoded one by one (the whole revision does not re-decode:
    candidates[23] parameter 'k' has an unsupported unit, finding 2026-10-23)."""
    from types import SimpleNamespace
    data = load_json(REV)
    out = []
    for item in data['candidates']:
        if item['category'] in categories:
            c = decode_record('Candidate', item)
            assert not hasattr(c, 'errors'), (item['id'], c)
            out.append(c)
    return SimpleNamespace(candidates=tuple(out), c0_receipt=data['c0_receipt'], revision_id=data['revision_id'])


def port_open():
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', RPC)) == 0


@contextmanager
def own_server(log):
    """Start ONLY our own CarlaUE4 on 2610; refuse when another one runs or the port is busy; kill our tree after."""
    running = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq CarlaUE4*'], capture_output=True, text=True).stdout
    assert 'CarlaUE4' not in running, 'another CarlaUE4 is running: refuse'
    assert not port_open(), 'port 2610 busy: refuse'
    proc = subprocess.Popen([str(EXE), f'-carla-rpc-port={RPC}', '-RenderOffScreen', '-quality-level=Low', '-nosound'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    start = datetime.now(timezone.utc).isoformat()
    log(event='SERVER_LAUNCHED', pid=proc.pid)
    try:
        t0 = time.monotonic()
        while not port_open():
            assert proc.poll() is None and time.monotonic() - t0 < 180, 'server did not open its port'
            time.sleep(2)
        import carla
        client = carla.Client('127.0.0.1', RPC)
        for attempt in range(8):
            try:
                client.set_timeout(60); client.get_world(); break
            except RuntimeError as e:
                log(event='CONNECT_RETRY', attempt=attempt, error=str(e)); time.sleep(10)
        yield client, proc, start
    finally:
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)
        try:
            proc.wait(30)
        except subprocess.TimeoutExpired:
            pass
        time.sleep(5)
        log(event='SERVER_STOPPED', pid=proc.pid, port_still_open=port_open())


# Duy [chat] 2026-10-25: CARLA no_rendering_mode for the runs from now on (no camera: no metric depends on rendering),
# disclosed in every run receipt, after a probe showed physics and traffic lights unchanged (native-render-probe.py).
NO_RENDER = os.environ.get('M56_NO_RENDER', '0') == '1'
# v6 (docs/m56/PREREG_M56_V6_20261026.md): M56_RECIPE=v6 turns on items a-d of the bundled v6 recipe; the default
# (unset) keeps every v5 byte. Recorded in every v6 receipt / preparation record.
V6 = os.environ.get('M56_RECIPE', 'v5') == 'v6'
# dv1 (docs/m56/PREREG_M56_DRIVABLE_DV1_20261108.md, POST-NUMBER): drivable union with Shoulder lanes, a 0.25 m paved raster
# eroded 0.125 m, and coverage of the whole routes. Unset keeps every v6 byte.
DV1 = os.environ.get('M56_DRIVABLE', '') == 'dv1'


# A-SEL2 large maps (2026-11-08, native-largemap-smoke.py): actors > actor_active_distance (2000 m) from the spectator are
# dormant and tiles are not streamed. M56_SPECTATOR=1 puts the spectator 50 m above the scene centre (top-down) and streams
# 20 ticks BEFORE any spawn / ground query of a scene. Unset keeps every byte of the earlier behaviour.
SPECTATOR = os.environ.get('M56_SPECTATOR', '') == '1'
# A-SEL2 addendum 6 (Duy 2026-11-08): spawn every actor with the CARLA waypoint pitch/roll at its spawn point (consumer v11
# compares the first observation with this frozen pose). Unset keeps pitch = roll = 0.
SPAWN_TILT = os.environ.get('M56_SPAWN_TILT', '') == '1'


def spawn_tilt(m, x, y, z):
    """(pitch, roll) in degrees of the driving-lane waypoint at (x, y, z), normalised to [-180, 180)."""
    import carla
    w = m.get_waypoint(carla.Location(float(x), float(y), float(z)))
    n = lambda a: (a + 180.) % 360. - 180.
    return n(w.transform.rotation.pitch), n(w.transform.rotation.roll)


def stream_to(world, x, y, z):
    if not SPECTATOR:
        return None
    import carla
    world.get_spectator().set_transform(carla.Transform(carla.Location(float(x), float(y), float(z) + 50.), carla.Rotation(pitch=-90.)))
    for _ in range(20):
        world.tick(120.) if world.get_settings().synchronous_mode else world.wait_for_tick(120.)
    return {'spectator': [float(x), float(y), float(z) + 50.], 'stream_ticks': 20}


def load(client, town):
    client.set_timeout(600.)  # A-SEL2 technical fix 3: Town12/13 load_world takes 110-160 s (> the 60 s RPC timeout)
    world = client.load_world(town)
    client.set_timeout(60.)
    for _ in range(3):
        world.wait_for_tick(30)
    if NO_RENDER:
        s = world.get_settings(); s.no_rendering_mode = True; world.apply_settings(s)
        world.wait_for_tick(30)
    return world


def ownership(proc, start, world):
    return OwnershipReceipt(f'pid{proc.pid}@{start}', str(world.id), '127.0.0.1', proc.pid, start, {'rpc': RPC},
                            (F(0), F(36000)), WRITER, WRITER, OPS)


# -- routes from CARLA waypoints (erratum E2) ---------------------------------------------------------------------
def _yawdiff(a, b):
    return abs((a - b + 180) % 360 - 180)


def _wp_row(w):
    t = w.transform
    return {'x': t.location.x, 'y': t.location.y, 'z': t.location.z, 'pitch': t.rotation.pitch, 'yaw': t.rotation.yaw,
            'roll': t.rotation.roll, 'road': w.road_id, 'lane': w.lane_id, 's': w.s}


def _step(w, forward, step=.2):
    """Next/previous lane waypoint at most 0.25 m away (chord), halving the lane-s step on curves."""
    for d in (step, step / 2, step / 4):
        nxt = (w.next(d) if forward else w.previous(d))
        if not nxt:
            return []
        if all(math.dist((p.transform.location.x, p.transform.location.y, p.transform.location.z),
                         (w.transform.location.x, w.transform.location.y, w.transform.location.z)) <= .24 for p in nxt):
            return nxt
    return nxt


def route_rows(m, town, notation, approach, outgoing, start=None):
    """Rows along road/lane -> connector/lane -> outgoing/lane, `approach` metres before the junction (upstream lanes
    continue by the straight-through rule: least heading change) and `outgoing` metres after it. With `start`
    (x, y, z) the route instead begins at the driving-lane waypoint of that point (the frozen EGO arc 0, prereg 1)."""
    import carla
    (r1, l1), (rc, lc), (r2, l2) = ((int(a.split('/')[0]), int(a.split('/')[1])) for a in notation.split('→'))
    L1 = xr.length(town, r1)
    end = m.get_waypoint_xodr(r1, l1, L1 - .01 if l1 < 0 else .01)
    assert end is not None, f'NO_WAYPOINT:{r1}/{l1}'
    if start is not None:
        # `start` is the frozen v1 route (list of (x, y)): follow the CARLA lane waypoints closest to it, from 1 m
        # upstream of its arc 0 to its end (prereg 1: EGO keeps the frozen start and path).
        from shapely.geometry import LineString, Point
        guide3 = list(start)  # (x, y[, z]) of the frozen v1 polyline; z picks the right level on overpasses (M01)
        guide = [g[:2] for g in guide3]
        (x0, y0), (x1, y1) = guide[0], guide[1]
        n = math.dist(guide[0], guide[1])
        line = LineString([(x0 - 2 * (x1 - x0) / n, y0 - 2 * (y1 - y0) / n), *guide])  # v1 polyline, 2 m extended upstream
        def off(p):
            return line.distance(Point(p.transform.location.x, p.transform.location.y))
        z0 = guide3[0][2] if len(guide3[0]) > 2 else 0.
        w = m.get_waypoint(carla.Location(guide[0][0], guide[0][1], z0), project_to_road=True, lane_type=carla.LaneType.Driving)
        back = 0.
        while back < 1.:
            prev = _step(w, False)
            if not prev:
                break
            p = min(prev, key=lambda p: _yawdiff(p.transform.rotation.yaw, w.transform.rotation.yaw))
            back += math.dist((p.transform.location.x, p.transform.location.y), (w.transform.location.x, w.transform.location.y))
            w = p
        # Follow the notation lanes strictly (road/lane ids of the frozen notation); the v1 polyline only guides the
        # upstream extension roads. The deviation from the v1 polyline is recorded, not used to select.
        rows, out, worst = [_wp_row(w)], 0., 0.
        while True:
            nxt = _step(w, True)
            if not nxt:
                break
            pick = ([p for p in nxt if (p.road_id, p.lane_id) == (rc, lc)] or [p for p in nxt if (p.road_id, p.lane_id) == (r2, l2)]
                    or [p for p in nxt if (p.road_id, p.lane_id) == (r1, l1)]
                    or [p for p in nxt if (p.road_id, p.lane_id) == (w.road_id, w.lane_id)])
            reached_out = any((r['road'], r['lane']) == (r2, l2) for r in rows)

            def ahead(q, dist=8.):  # max deviation from v1 over the next `dist` m along q's lane (branch look-ahead)
                worst_q, cur, done = off(q), q, 0.
                while done < dist:
                    n_ = cur.next(1.)
                    if not n_:
                        break
                    cur = min(n_, key=off); done += 1.; worst_q = max(worst_q, off(cur))
                return worst_q
            nearest = min(nxt, key=ahead) if len(nxt) > 1 else nxt[0]
            if off(nearest) <= .5 and not reached_out:
                # on the frozen v1 path (it may cross junction connectors the notation does not name, M01 2026-10-24):
                # follow the lane waypoint closest to it
                pick = [nearest]
            elif not pick and reached_out:  # past the outgoing road: straight-through rule (as V3.3), not a failure
                pick = [min(nxt, key=lambda q: _yawdiff(q.transform.rotation.yaw, w.transform.rotation.yaw))]
            p = pick[0] if pick else nearest
            if ((w.road_id, w.lane_id) == (rc, lc) and (p.road_id, p.lane_id) not in ((rc, lc), (r2, l2))
                    and off(p) > .5):
                raise ValueError(f'ROUTE_LEFT_NOTATION:{notation}:{p.road_id}/{p.lane_id}')
            if reached_out or (p.road_id, p.lane_id) == (r2, l2):  # outgoing distance counts from the exit onward
                out += math.dist((p.transform.location.x, p.transform.location.y), (w.transform.location.x, w.transform.location.y))
            if not reached_out:
                worst = max(worst, off(p))
            rows.append(_wp_row(p)); w = p
            if out >= outgoing or len(rows) > 20000:
                break
        exit_index = next((i for i, r in enumerate(rows) if (r['road'], r['lane']) == (r2, l2)), None)
        if exit_index is None:
            seen = []
            for r in rows:
                if not seen or seen[-1] != (r['road'], r['lane']):
                    seen.append((r['road'], r['lane']))
            raise AssertionError(f'NO_OUTGOING:{notation}:visited={seen[:16]}:rows={len(rows)}')
        return rows, exit_index, {'max_offset_from_v1_m': worst}
    else:
        back, w, d = [], end, 0.
        while d < approach:
            prev = _step(w, False)
            if not prev:
                break
            nxt = min(prev, key=lambda p: _yawdiff(p.transform.rotation.yaw, w.transform.rotation.yaw))
            d += math.dist((nxt.transform.location.x, nxt.transform.location.y), (w.transform.location.x, w.transform.location.y))
            back.append(nxt); w = nxt
        rows = [_wp_row(x) for x in reversed(back)] + [_wp_row(end)]
    w, out, exit_index = end, 0., None
    while out < outgoing:
        nxt = _step(w, True)
        if not nxt:
            break
        on = w.road_id
        pick = ([p for p in nxt if p.road_id == rc and p.lane_id == lc] or [p for p in nxt if p.road_id == r2 and p.lane_id == l2]
                or [p for p in nxt if p.road_id == on and p.lane_id == w.lane_id])
        if not pick:
            if exit_index is None:
                raise ValueError(f'ROUTE_BREAK:{notation}:{on}/{w.lane_id}->{[(p.road_id, p.lane_id) for p in nxt]}')
            # v3.3: beyond the outgoing road, continue by the straight-through rule (least heading change)
            pick = [min(nxt, key=lambda q: _yawdiff(q.transform.rotation.yaw, w.transform.rotation.yaw))]
        p = pick[0]
        if p.road_id == r2 and exit_index is None:
            exit_index = len(rows)
        if exit_index is not None:
            out += math.dist((p.transform.location.x, p.transform.location.y), (w.transform.location.x, w.transform.location.y))
        rows.append(_wp_row(p)); w = p
    if exit_index is None:
        seen = sorted({(r['road'], r['lane']) for r in rows})
        raise AssertionError(f'NO_OUTGOING:{notation}:visited={seen[:12]}')
    return rows, exit_index, d


def arcs(rows):
    a, out = 0., [F(0)]
    for p, r in zip(rows, rows[1:]):
        a += math.dist((p['x'], p['y'], p['z']), (r['x'], r['y'], r['z']))
        out.append(F(round(a * 10 ** 6), 10 ** 6))
    return out


def directed(rows, arc, map_hash, town, notation, continuity, destination):
    refs = tuple(LaneRef(town, x.split('/')[0], 0, int(x.split('/')[1]), F(0)) for x in notation.split('→'))
    return DirectedRoute(refs, tuple(Transform6(r['x'], r['y'], r['z'], r['pitch'], r['yaw'], r['roll']) for r in rows),
                         tuple(arc), map_hash, (continuity,), destination)


# -- reviews / policies -------------------------------------------------------------------------------------------
def reviewer(authority):
    def review(payload, scope, refs, reasons=('Claude review under Duy delegation (A-G45), not independent',)):
        return ReviewRecord(_digest(payload), scope, tuple(dict.fromkeys(refs)), REVIEWER, DATE, 'APPROVED', tuple(reasons),
                            authority)
    return review


def plan_rows(rows, arc, start_station, every=2.):
    out, last = [], -1e9
    for r, a in zip(rows, arc):
        if float(a) >= start_station and float(a) - last >= every:
            out.append({'x': r['x'], 'y': r['y'], 'z': r['z'], 'road': r['road'], 'lane': r['lane'], 's': r['s']})
            last = float(a)
    return tuple(out)


# v5 P-NPC (prereg eda7680): fixed-order NPC longitudinal grid (K_P, K_I, K_D); entry 0 = stock (no binding key).
NPC_PID_GRID = ((F(1), F(1, 20), F(0)), (F(1, 2), F(1, 20), F(0)), (F(3, 10), F(1, 20), F(0)), (F(1, 2), F(1, 5), F(0)),
                (F(3, 10), F(1, 5), F(0)), (F(1, 5), F(1, 10), F(0)))


def npc_gains_binding(gains):
    return None if gains is None or tuple(gains) == NPC_PID_GRID[0] else {
        'K_P': F(gains[0]), 'K_I': F(gains[1]), 'K_D': F(gains[2]), 'dt': F(1, 20)}


def policy_maker(fixture, rows_by_role, review, source, npc_gains=None, ego_gains=None):
    """Reviewed stock binding per actor, made after spawn (names the real actor id). Plan = the role's own route lane
    waypoints (road/lane/s) every 2 m from 2 m ahead of the actor's current station. npc_gains (v5 P-NPC): the NPC's
    reviewed longitudinal gains; None or the stock entry = no binding key (byte-identical binding to v4)."""
    from m56.metrics import _metric_station

    def policy_for(response, actor):
        role = response.actor_role
        route = fixture.routes[role]
        loc = actor.get_location()
        station = _metric_station((loc.x, loc.y, loc.z), route)
        rows, arc = rows_by_role[role]
        plan = plan_rows(rows, arc, float(station or 0) + 2.)
        binding = {'response_hash': response.hash, 'response_record_hash': _digest(response),
                   'route_hash': _digest(response.route), 'actor_id': actor.id, 'source_refs': (source,), 'plan': plan,
                   'client_version': '0.9.16', 'server_version': '0.9.16'}
        if role == 'NPC' and npc_gains_binding(npc_gains) is not None:
            binding['npc_longitudinal'] = npc_gains_binding(npc_gains)
        if role == 'EGO' and npc_gains_binding(ego_gains) is not None:  # v5 erratum 2: same grid, EGO's own key
            binding['ego_longitudinal'] = npc_gains_binding(ego_gains)
        r = review(binding, 'STOCK_FORWARD_BINDING', (source,))
        return PolicyBundle('m56-v2', 'f' * 64, {}, {'stock_binding': {**binding, 'review': r}}, {}, (source,))
    return policy_for


def npc_response(category, vN, route, v6=None):
    """v6=None: the v5 NPC program byte for byte. v6 = v6_npc_program(...) without 'reason': TURN (after the speed
    marker) and/or PARK (after CLEAR_N + delay) appended in that order (prereg v6 a, d)."""
    rows = [{'cause': 'NOMINAL', 'after_event': 'CAPTURE_START', 'delay_s': RELEASE, 'requires': ()}]
    targets = {'SETTLE': F(0), 'NOMINAL': vN}
    markers = None
    if v6 and v6.get('turn'):
        rows.append({'cause': 'TURN', 'after_event': 'SPEED_MARKER:NPC:TURN', 'delay_s': F(0), 'requires': ()})
        targets['TURN'] = v6['turn']['v_mps']
        markers = ({'cause': 'TURN', 'marker_arc_m': v6['turn']['marker_arc_m']},)
    if v6 and v6.get('park'):
        rows.append({'cause': 'PARK', 'after_event': 'CLEAR_N_CONFIRMED', 'delay_s': v6['park']['delay_s'], 'requires': ()})
        targets['PARK'] = F(0)
    program = {'method': 'ordered-event-program-v1', 'initial': 'SETTLE', 'transitions': tuple(rows)}
    zero = {'method': 'quintic-arc-v1', 'segments': ({'start_arc_m': F(0), 'length_m': F(1), 'start_offset_m': F(0),
                                                      'end_offset_m': F(0)},)}
    phases = {'category': category, 'program': program, 'annex': 'prereg v2 2.2: temporary, never catalog'}
    if markers:
        phases['speed_markers'] = markers
    r = FrozenResponse('NPC', 'NPC_COMMON', route, targets, zero, phases, '')
    return replace(r, hash=_digest({k: getattr(r, k) for k in ('actor_role', 'action_id', 'route', 'targets', 'profile', 'phases')}))


def route_kappa(route):
    """Curvature per interior route point exactly as the G4 kit computes it (yaw change over the two neighbours)."""
    t, arc = route.transforms, [float(x) for x in route.arc]
    return [(arc[i], abs(math.radians((t[i + 1].yaw - t[i - 1].yaw + 180) % 360 - 180)) / (arc[i + 1] - arc[i - 1]))
            for i in range(1, len(t) - 1)]


def v6_npc_program(route, vN, region, body_len, cut):
    """Prereg v6 d (TURN) and a (PARK) on a frozen NPC route, before any outcome. Returns {'turn', 'park'} or
    {'reason'} (BLOCKED_FIXTURE). Budget 2.25 = 0.9 x the frozen 2.5 m/s^2; window 10 m + 1 m as erratum 4."""
    from m56.geometry import _derive_box_sections
    out = {'turn': None, 'park': None, 'rule': 'prereg v6 a+d'}
    secs = _derive_box_sections(route, region)
    assert not hasattr(secs, 'reasons'), f'V6_SECTIONS:{getattr(secs, "reasons", None)}'
    k = route_kappa(route); v2 = float(vN) ** 2
    hot = [(s, x) for s, x in k if v2 * x > 2.25]
    if hot:
        s_turn = hot[0][0]; kmax = max(x for s, x in k if s >= s_turn)
        v_turn = F(math.floor(math.sqrt(2.25 / kmax) * 8), 8)
        marker = F(math.floor((s_turn - 11.) * 1000), 1000)
        if v_turn < F(3, 2) or marker <= route.arc[0]:
            return {'reason': 'NPC_TURN_SPEED', 's_turn_m': s_turn, 'kappa_max': kmax, 'v_turn': v_turn, 'marker': marker}
        # A slowdown before the box exit would change the NPC's frozen speed vN inside the conflict and the
        # preparation's phasing (its probes carry no C/L/M events, so no marker): a decision for Duy, not a recipe.
        if v_turn < vN and marker < secs[1].route_station:
            return {'reason': 'NPC_TURN_BEFORE_EXIT', 's_turn_m': s_turn, 'marker': marker,
                    'n_exit_m': secs[1].route_station, 'v_turn': v_turn}
        if v_turn < vN:
            out['turn'] = {'v_mps': v_turn, 'marker_arc_m': marker, 's_turn_m': F(str(round(s_turn, 6))),
                           'kappa_max': F(str(round(kmax, 9)))}
    if cut:
        v_last = out['turn']['v_mps'] if out['turn'] else vN
        front_clear = float(secs[1].route_station) + .5 + float(body_len)
        room = float(route.arc[-1]) - front_clear
        margin = float(v_last) ** 2 / 3. + 5.
        if room < margin:
            return {'reason': 'NPC_PARK_ROOM', 'room_m': room, 'margin_m': margin}
        out['park'] = {'delay_s': F(math.floor((room - margin) / float(v_last) * 20), 20), 'room_m': F(str(round(room, 6))),
                       'margin_m': F(str(round(margin, 6)))}
    return out


# -- bodies, certificates, drivable area ---------------------------------------------------------------------------
def body_record(bbox, source):
    return BodyRecord((bbox['location'][0], bbox['location'][1], bbox['location'][2]), tuple(bbox['rotation']),
                      tuple(bbox['extent']), (), 'vehicle.audi.a2', {}, {}, source)


def up(x, grid=10 ** 6):
    return F(math.ceil(x * grid), grid)


def certificates(route, body, review, source):
    rh, bh, out = _digest(route), _digest(body), []
    src = replace(source, method='bounded-pose-tube-v1')
    for i, (a, b) in enumerate(zip(route.transforms, route.transforms[1:])):
        chord = math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))
        rot = _rotation_distance(a, b)
        bounds = {'route_hash': rh, 'body_hash': bh, 'translation_deviation_m': up(chord * rot / 8 + 1e-4),
                  'rotation_from_start_rad': up(rot + 1e-6)}
        packet = {'method': 'bounded-pose-tube-v1', 'interval': (route.arc[i], route.arc[i + 1]), 'bounds': bounds,
                  'error': F(1, 1000), 'source': src}
        out.append(BoundCertificate(**packet, review=review(packet, 'CONTINUOUS_BOUND', (src,),
                   ('lane-centre waypoint chord; deviation <= chord*angle/8 (circular arc sagitta) + 0.1 mm',))))
    return tuple(out)


def drivable_union(m, center, radius=90., world=None, routes=None):
    """v5: union of CARLA driving-lane quads (waypoints every 0.5 m, lane width) within radius of center.
    v6 b (prereg PREREG_M56_V6_20261026, needs world + routes): that union plus the paved surface actually present:
    a 0.5 m grid inside 12 m of either route (and the radius), each point paved iff its first cast_ray hit from the
    local route z + 3 m down to z - 3 m is labelled Roads or RoadLines; the paved cells are unioned and eroded by
    0.25 m (half a cell: conservative boundary). The lane union itself gets only a 0.25 m closing (seams < 0.5 m); a
    1 m closing reached sidewalks (probe 2026-10-26)."""
    import carla
    from shapely.geometry import Polygon, box, LineString, Point
    from shapely.ops import unary_union
    from shapely.prepared import prep
    quads = []
    for w in m.generate_waypoints(.5):
        if w.lane_type != carla.LaneType.Driving and not (DV1 and w.lane_type == carla.LaneType.Shoulder):
            continue
        loc = w.transform.location
        if math.dist((loc.x, loc.y), center) > radius:
            continue
        for n in w.next(.5)[:1]:
            pts = []
            for p, side in ((w, 1), (n, 1), (n, -1), (w, -1)):
                t = p.transform; yaw = math.radians(t.rotation.yaw); h = p.lane_width / 2
                pts.append((t.location.x - side * h * math.sin(yaw), t.location.y + side * h * math.cos(yaw)))
            quad = Polygon(pts)
            if quad.is_valid and quad.area > 0:
                quads.append(quad)
    union = unary_union(quads).buffer(0)
    if not V6:
        return union
    union = union.buffer(.25).buffer(-.25)  # v6 b: closes seams < 0.5 m between lane quads (L01: a 0.114 m sliver edge)
    assert world is not None and routes, 'V6_DRIVABLE_NEEDS_WORLD_AND_ROUTES'
    ref = [(float(t.x), float(t.y), float(t.z)) for r in routes.values() for t in r.transforms]
    corridor = unary_union([LineString([(x, y) for x, y, _ in [(float(t.x), float(t.y), 0) for t in r.transforms]]).buffer(12.)
                            for r in routes.values()])
    if not DV1:  # dv1: the raster covers the whole route corridor
        corridor = corridor.intersection(Point(center).buffer(radius))
    cell = .25 if DV1 else .5  # dv1: finer raster, eroded by half a cell
    zcell = {}
    for x, y, z in ref:  # local route z on a 2 m hash
        zcell.setdefault((round(x / 2), round(y / 2)), z)
    def local_z(x, y):
        for d in range(0, 8):
            for i in range(-d, d + 1):
                for j in range(-d, d + 1):
                    z = zcell.get((round(x / 2) + i, round(y / 2) + j))
                    if z is not None:
                        return z
        return None
    pc = prep(corridor); cells = []
    x0, y0, x1, y1 = corridor.bounds
    for i in range(int((x1 - x0) / cell) + 1):
        for j in range(int((y1 - y0) / cell) + 1):
            x, y = x0 + cell * i, y0 + cell * j
            if not pc.contains(Point(x, y)):
                continue
            z = local_z(x, y)
            if z is None:
                continue
            hits = world.cast_ray(carla.Location(x, y, z + 3.), carla.Location(x, y, z - 3.))
            if hits and str(hits[0].label) in ('Roads', 'RoadLines'):
                cells.append(box(x - cell / 2, y - cell / 2, x + cell / 2, y + cell / 2))
    paved = unary_union(cells).buffer(-cell / 2) if cells else Polygon()
    return unary_union([union, paved]).buffer(0)


def driving_boxes(drivable, route, z_lo, z_hi, corridor=6., cell=.5):
    """Axis-aligned boxes fully inside the drivable union, covering the route corridor (row runs of 0.5 m cells,
    merged vertically when identical). Conservative: boundary cells that are not fully inside are dropped."""
    from shapely.geometry import box
    xs = [t.x for t in route.transforms]; ys = [t.y for t in route.transforms]
    x0, x1 = math.floor(min(xs) - corridor), math.ceil(max(xs) + corridor)
    y0, y1 = math.floor(min(ys) - corridor), math.ceil(max(ys) + corridor)
    nx, ny = int((x1 - x0) / cell), int((y1 - y0) / cell)
    from shapely.prepared import prep
    inside = prep(drivable)
    runs = {}
    for j in range(ny):
        y = y0 + j * cell; i = 0
        while i < nx:
            if inside.contains(box(x0 + i * cell, y, x0 + (i + 1) * cell, y + cell)):
                k = i
                while k + 1 < nx and inside.contains(box(x0 + (k + 1) * cell, y, x0 + (k + 2) * cell, y + cell)):
                    k += 1
                runs.setdefault((i, k), []).append(j); i = k + 1
            else:
                i += 1
    boxes = []
    for (i, k), js in runs.items():
        js.sort(); start = prev = js[0]
        for j in js[1:] + [None]:
            if j is not None and j == prev + 1:
                prev = j; continue
            lo = (F(x0) + i * F(cell), F(y0) + start * F(cell), z_lo)
            hi = (F(x0) + (k + 1) * F(cell), F(y0) + (prev + 1) * F(cell), z_hi)
            boxes.append(tuple(tuple(float(hi[d] if s[d] else lo[d]) for d in range(3)) for s in product((0, 1), repeat=3)))
            if j is not None:
                start = prev = j
    return tuple(boxes)


def lane_width_region(m, rows_by_role, lo, hi):
    """V3.2 (prereg ab1fb09): widen the overlap AABB symmetrically about its centre so each horizontal extent is at least
    W + 1.0 m, W = the larger CARLA lane_width of the EGO and NPC lanes at their route points nearest the centre.
    Vertical extent +-1 m as in v2. Returns (region vertices, W, widths)."""
    from itertools import product
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    widths = {}
    for role, rows in rows_by_role.items():
        r = min(rows, key=lambda q: math.dist((q['x'], q['y']), (cx, cy)))
        widths[role] = m.get_waypoint_xodr(int(r['road']), int(r['lane']), float(r['s'])).lane_width
    W = max(widths.values())
    half = [max((hi[k] - lo[k]) / 2, (W + 1.0) / 2) for k in (0, 1)]
    # min/max with O itself plus 1 micrometre: centre +- half can round 1e-15 inside O (L01 compile 2026-10-24:
    # DOMAIN_DOES_NOT_ENCLOSE_SWEPT_CONFLICT on an axis where O is already wider than W + 1 m)
    a = (min(cx - half[0], lo[0]) - 1e-6, min(cy - half[1], lo[1]) - 1e-6, lo[2] - 1.)
    b = (max(cx + half[0], hi[0]) + 1e-6, max(cy + half[1], hi[1]) + 1e-6, hi[2] + 1.)
    return tuple(tuple(b[k] if sgn[k] else a[k] for k in range(3)) for sgn in product((0, 1), repeat=3)), W, widths


def v2_routes(prep, notation, town, plain):
    """The fixture routes exactly as the A/B compiles them (also the V3.1 EGO response route)."""
    rows_all = plain(json.loads(Path(prep['routes_v2']).read_text(encoding='utf-8')))
    cont = SourceRef(prep['routes_v2'], prep['routes_v2_sha256'], Path(prep['routes_v2']).stat().st_size, '1', 'claude-g4',
                     'NATIVE_ROUTE')
    rows, routes = {}, {}
    for role in ('EGO', 'NPC'):
        r = rows_all[role]
        a = arcs(r)
        rows[role] = (r, a)
        routes[role] = directed(r, a, prep['map_hash'], town, notation[role], cont, F(prep['destinations'][role]))
    if prep.get('category') == 'M':
        # Fix 2026-10-25 (found when every M fixture blocked DESTINATION_ROOM_UNPROVEN before any episode): the M domain
        # is the merge transition box, which extends past the junction exit, while the recipe rule put the destination
        # at junction exit + 5 m. compile_fixture requires destination >= domain exit + 5 m, so for M the destination
        # is max(junction exit + 5 m, domain exit + 5 m), from the region recorded by the preparation.
        from m56.geometry import _derive_box_sections
        region = tuple(tuple(float(v) for v in pt) for pt in plain(prep['region']))
        for role in routes:
            secs = _derive_box_sections(routes[role], region)
            if not hasattr(secs, 'reasons'):
                need = F(math.ceil((F(secs[1].route_station) + 5) * 1000), 1000)  # rounded UP to 1/1000 m
                if need > routes[role].destination:
                    routes[role] = replace(routes[role], destination=need)
    return routes, rows, cont


def merge_transition_region(m, rows_by_role, exit_index_ego):
    """v4 P3 (ccea1cc) M01: the transition box around the point where the EGO (branch) connector joins the target lane
    (first EGO row on the outgoing road), horizontal extents W + 1 m (W = larger CARLA lane width of the two lanes
    there), vertical from the route z - 1 m to + 3 m."""
    from itertools import product
    p = rows_by_role['EGO'][exit_index_ego]
    widths = {}
    for role, rows in rows_by_role.items():
        r = min(rows, key=lambda q: math.dist((q['x'], q['y']), (p['x'], p['y'])))
        widths[role] = m.get_waypoint_xodr(int(r['road']), int(r['lane']), float(r['s'])).lane_width
    half = (max(widths.values()) + 1.0) / 2
    a = (p['x'] - half, p['y'] - half, p['z'] - 1.)
    b = (p['x'] + half, p['y'] + half, p['z'] + 3.)
    return tuple(tuple(b[k] if sgn[k] else a[k] for k in range(3)) for sgn in product((0, 1), repeat=3)), widths
