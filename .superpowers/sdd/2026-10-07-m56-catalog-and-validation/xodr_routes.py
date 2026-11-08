"""Lane-centre routes from the pinned OpenDRIVE files, in CARLA coordinates (x, -y, z; yaw = -heading in degrees).

Only line/arc planView records are evaluated exactly (all Town04-07 roads are line/arc). Lane centre offset = sum of
inner lane widths + half own width (+ laneOffset if present); right-hand traffic: lane < 0 travels +s, lane > 0 -s.
"""
from pathlib import Path
import math
import xml.etree.ElementTree as ET

ROOT = Path('E:/Carla/CarlaUE4/Content/Carla/Maps/OpenDrive')
_cache = {}


def xodr_path(town):
    """A-SEL2: Town04-07 (and 01/02/10HD) live in Maps/OpenDrive; the large maps 11-15 in Maps/<town>/OpenDrive."""
    p = ROOT / f'{town}.xodr'
    return p if p.exists() else ROOT.parent / town / 'OpenDrive' / f'{town}.xodr'


def roads(town):
    if town not in _cache:
        root = ET.parse(xodr_path(town)).getroot()
        _cache[town] = {int(r.get('id')): r for r in root.findall('road')}
    return _cache[town]


def _ref_point(road, s):
    geos = road.find('planView').findall('geometry')
    g = max((x for x in geos if float(x.get('s')) <= s + 1e-9), key=lambda x: float(x.get('s')), default=geos[0])
    ds = s - float(g.get('s')); x, y, h = float(g.get('x')), float(g.get('y')), float(g.get('hdg'))
    kind = g[0]
    if kind.tag == 'arc' and abs(float(kind.get('curvature'))) > 1e-12:
        k = float(kind.get('curvature')); h2 = h + k * ds
        return x + (math.sin(h2) - math.sin(h)) / k, y - (math.cos(h2) - math.cos(h)) / k, h2
    if kind.tag not in ('line', 'arc'):
        raise ValueError(f'UNSUPPORTED_GEOMETRY:{kind.tag}')
    return x + ds * math.cos(h), y + ds * math.sin(h), h


def _poly(records, s, key='s'):
    rec = max((r for r in records if float(r.get(key)) <= s + 1e-9), key=lambda r: float(r.get(key)), default=None)
    if rec is None:
        return 0.
    d = s - float(rec.get(key))
    return sum(float(rec.get(c)) * d ** i for i, c in enumerate('abcd'))


def _lane_offset(road, lane, s):
    secs = road.find('lanes').findall('laneSection')
    sec = max((x for x in secs if float(x.get('s')) <= s + 1e-9), key=lambda x: float(x.get('s')))
    side = sec.find('left' if lane > 0 else 'right'); ds = s - float(sec.get('s'))
    widths = {int(l.get('id')): _poly(l.findall('width'), ds, 'sOffset') for l in side.findall('lane')}
    if lane not in widths:
        raise ValueError(f'LANE_MISSING:{lane}@s{s:.1f}')
    inner = sum(widths[i] for i in widths if 0 < abs(i) < abs(lane))
    t = inner + widths[lane] / 2
    base = _poly(road.find('lanes').findall('laneOffset'), s)
    return base + (t if lane > 0 else -t)


def lane_points(town, road_id, lane, s_from, s_to, step=1.0):
    """Points along lane centre from s_from to s_to (either order = travel order); CARLA (x, y, z, yaw_deg)."""
    road = roads(town)[road_id]
    n = max(1, int(abs(s_to - s_from) / step))
    elev = road.find('elevationProfile')
    out = []
    for i in range(n + 1):
        s = s_from + (s_to - s_from) * i / n
        x, y, h = _ref_point(road, s); t = _lane_offset(road, lane, s)
        px, py = x - t * math.sin(h), y + t * math.cos(h)
        z = _poly(elev.findall('elevation'), s) if elev is not None else 0.
        travel = h if s_to >= s_from else h + math.pi
        out.append((px, -py, z, -math.degrees(travel)))
    return out


def length(town, road_id):
    return float(roads(town)[road_id].get('length'))


def chain(pieces):
    """Concatenate point lists, dropping duplicate joints; return points + cumulative arc (m)."""
    pts = []
    for p in pieces:
        for q in p:
            if pts and math.hypot(q[0] - pts[-1][0], q[1] - pts[-1][1]) < 0.05:
                continue
            pts.append(q)
    arc = [0.]
    for a, b in zip(pts, pts[1:]):
        arc.append(arc[-1] + math.dist(a[:3], b[:3]))
    return pts, arc


def junction_route(town, notation, approach_m, outgoing_m):
    """'road/±lane→connector/±lane→outgoing/±lane' -> (points, arc, exit_arc, approach_available_m)."""
    (r1, l1), (rc, lc), (r2, l2) = ((int(a.split('/')[0]), int(a.split('/')[1])) for a in notation.split('→'))
    L1, Lc, L2 = length(town, r1), length(town, rc), length(town, r2)
    a = min(approach_m, L1)
    app = lane_points(town, r1, l1, L1 - a, L1) if l1 < 0 else lane_points(town, r1, l1, a, 0.)
    con = lane_points(town, rc, lc, 0., Lc) if lc < 0 else lane_points(town, rc, lc, Lc, 0.)
    o = min(outgoing_m, L2)
    out = lane_points(town, r2, l2, 0., o) if l2 < 0 else lane_points(town, r2, l2, L2, L2 - o)
    up, got_up = extend(town, r1, l1, True, approach_m - a) if a < approach_m else ([], 0.)
    down, got_down = extend(town, r2, l2, False, outgoing_m - o) if o < outgoing_m else ([], 0.)
    up_pts = [lane_points(town, r, l, s0, s1) for r, l, s0, s1 in reversed(up)]
    down_pts = [lane_points(town, r, l, s0, s1) for r, l, s0, s1 in down]
    pts, arc = chain((*up_pts, app, con))
    exit_arc = arc[-1]
    pts, arc = chain((*up_pts, app, con, out, *down_pts))
    return pts, arc, exit_arc, a + got_up, o + got_down


def _junctions(town):
    root = ET.parse(xodr_path(town)).getroot()
    return {int(j.get('id')): j for j in root.findall('junction')}


def _lane_link(road, lane, which, at_start):
    secs = road.find('lanes').findall('laneSection'); sec = secs[0] if at_start else secs[-1]
    side = sec.find('left' if lane > 0 else 'right')
    ln = next((l for l in (side.findall('lane') if side is not None else ()) if int(l.get('id')) == lane), None)
    nxt = ln.find('link').find(which) if ln is not None and ln.find('link') is not None else None
    return int(nxt.get('id')) if nxt is not None else None


def _heading_at(town, road_id, lane, at_start, travel_sign):
    pts = lane_points(town, road_id, lane, 0. if at_start else length(town, road_id),
                      min(1., length(town, road_id)) if at_start else max(0., length(town, road_id) - 1.))
    return pts[0][3] if travel_sign > 0 else pts[0][3] + 180.


def _turn(town, con, lane, contact):
    """|heading change| along a connector lane (degrees): the straight-through rule picks the minimum."""
    L = length(town, con)
    try:
        pts = lane_points(town, con, lane, 0., L) if lane < 0 else lane_points(town, con, lane, L, 0.)
    except ValueError:
        return 999.
    return abs((pts[-1][3] - pts[0][3] + 180.) % 360. - 180.)


def extend(town, road_id, lane, upstream, need, hops=6):
    """Lane pieces continuing beyond road_id along road/lane links, upstream (toward where traffic comes from) or
    downstream, until `need` metres or no link. At a junction the connection with the smallest heading change is
    taken (declared straight-through rule). Returns ([(road, lane, s_from, s_to)], metres)."""
    rs = roads(town); js = None; out = []; got = 0.; cur, ln = road_id, lane
    for _ in range(hops):
        road = rs[cur]; travel = 1 if ln < 0 else -1
        # boundary we leave through
        at_start = (travel > 0) == upstream
        link = road.find('link'); nxt = link.find('predecessor' if at_start else 'successor') if link is not None else None
        if nxt is None:
            break
        nln = _lane_link(road, ln, 'predecessor' if at_start else 'successor', at_start)
        if nxt.get('elementType') == 'road':
            nid, contact = int(nxt.get('elementId')), nxt.get('contactPoint')
            if nln is None or nid not in rs:
                break
        else:
            js = js or _junctions(town); j = js.get(int(nxt.get('elementId')))
            best = None
            for c in (j.findall('connection') if j is not None else ()):
                con = int(c.get('connectingRoad'))
                if upstream:  # connector must end at our road; take its lane that links into ours
                    cl = rs[con].find('link'); end = cl.find('successor') if cl is not None else None
                    side_end = True
                    if end is None or int(end.get('elementId')) != cur:
                        end = cl.find('predecessor') if cl is not None else None; side_end = False
                        if end is None or int(end.get('elementId')) != cur:
                            continue
                    for l2 in range(-6, 7):
                        if l2 == 0 or _lane_link(rs[con], l2, 'successor' if side_end else 'predecessor', not side_end) != ln:
                            continue
                        cand = (con, l2, 'end' if side_end else 'start')
                        best = min((x for x in (best, cand) if x is not None), key=lambda x: _turn(town, *x))
                else:
                    if int(c.get('incomingRoad')) != cur:
                        continue
                    for ll in c.findall('laneLink'):
                        if int(ll.get('from')) == ln:
                            cand = (con, int(ll.get('to')), c.get('contactPoint'))
                            best = min((x for x in (best, cand) if x is not None), key=lambda x: _turn(town, *x))
            if best is None:
                break
            nid, nln, contact = best
        L = length(town, nid)
        take = min(L, need - got)
        # traverse nid toward/away from the contact point
        if upstream:
            s_to = L if contact == 'end' else 0.; s_from = s_to - take if contact == 'end' else take
        else:
            s_from = 0. if contact == 'start' else L; s_to = take if contact == 'start' else L - take
        out.append((nid, nln, s_from, s_to)); got += take
        if got >= need - 1e-6:
            break
        cur, ln = nid, nln
    return out, got
