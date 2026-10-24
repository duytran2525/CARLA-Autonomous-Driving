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


def load(client, town):
    world = client.load_world(town)
    for _ in range(3):
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


def npc_response(category, vN, route):
    program = {'method': 'ordered-event-program-v1', 'initial': 'SETTLE',
               'transitions': ({'cause': 'NOMINAL', 'after_event': 'CAPTURE_START', 'delay_s': RELEASE, 'requires': ()},)}
    zero = {'method': 'quintic-arc-v1', 'segments': ({'start_arc_m': F(0), 'length_m': F(1), 'start_offset_m': F(0),
                                                      'end_offset_m': F(0)},)}
    r = FrozenResponse('NPC', 'NPC_COMMON', route, {'SETTLE': F(0), 'NOMINAL': vN}, zero,
                       {'category': category, 'program': program, 'annex': 'prereg v2 2.2: temporary, never catalog'}, '')
    return replace(r, hash=_digest({k: getattr(r, k) for k in ('actor_role', 'action_id', 'route', 'targets', 'profile', 'phases')}))


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


def drivable_union(m, center, radius=90.):
    """Union of CARLA driving-lane quads (waypoints every 0.5 m, lane width) within radius of center."""
    import carla
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    quads = []
    for w in m.generate_waypoints(.5):
        if w.lane_type != carla.LaneType.Driving:
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
    return unary_union(quads).buffer(0)


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
        region = tuple(tuple(float(v) for v in pt) for pt in prep['region'])
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
