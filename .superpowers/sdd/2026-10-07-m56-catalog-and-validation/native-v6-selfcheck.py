"""Offline self-check of the v6 tooling (prereg docs/m56/PREREG_M56_V6_20261026.md items a, c, d); no server.
M56_RECIPE=v6 python -I native-v6-selfcheck.py   -> prints OK or raises."""
import math, os, sys
from fractions import Fraction as F
from itertools import product
from pathlib import Path
from types import SimpleNamespace
assert os.environ.get('M56_RECIPE') == 'v6', 'run with M56_RECIPE=v6'
sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common as c  # noqa: E402
import native_v2_kit as kit  # noqa: E402
from m56.model import DirectedRoute, SourceRef, Transform6  # noqa: E402

ref = SourceRef('synthetic://v6', 'a' * 64, 1, '1', 'literal', 'SYNTHETIC_TEST')


def route(points):
    arc = [F(0)]
    for (a, b) in zip(points, points[1:]):
        arc.append(arc[-1] + F(str(round(math.dist(a[:2], b[:2]), 9))))
    return DirectedRoute((), tuple(Transform6(x, y, 0., 0., yaw, 0.) for x, y, yaw in points), tuple(arc), 'b' * 64, (ref,),
                         arc[-1] - 5)


def shape(straight):
    """straight m along +x, a 90 deg left arc of radius 6 m, then 30 m straight along +y (0.5 m spacing)"""
    pts = [(x / 2, 0., 0.) for x in range(0, int(straight * 2) + 1)]
    for i in range(1, 19):
        a = math.radians(5 * i); pts.append((straight + 6 * math.sin(a), 6 - 6 * math.cos(a), 5. * i))
    return route(pts + [(straight + 6., 6 + y / 2, 90.) for y in range(1, 61)])


r = shape(50.)
region = tuple(product((10., 15.), (-3., 3.), (-1., 3.)))  # conflict box before the arc

# v5 program bytes are unchanged without v6
v5 = c.npc_response('C', F(4), r)
assert v5.phases['program']['transitions'] == ({'cause': 'NOMINAL', 'after_event': 'CAPTURE_START', 'delay_s': c.RELEASE,
                                                'requires': ()},) and set(v5.targets) == {'SETTLE', 'NOMINAL'}
assert 'speed_markers' not in v5.phases and list(v5.phases) == ['category', 'program', 'annex']

# d: TURN before the 6 m arc; a: PARK after the box exit
p = c.v6_npc_program(r, F(4), region, 3.7, cut=True)
assert not p.get('reason'), p
t = p['turn']
assert 50. <= float(t['s_turn_m']) <= 51., t
assert t['v_mps'] == F(math.floor(math.sqrt(2.25 / float(t['kappa_max'])) * 8), 8) and t['v_mps'] < 4, t
assert abs(float(t['kappa_max']) - 1 / 6) < .01, t
assert float(t['marker_arc_m']) == math.floor((float(t['s_turn_m']) - 11.) * 1000) / 1000
room = float(r.arc[-1]) - (15. + .5 + 3.7); margin = float(t['v_mps']) ** 2 / 3. + 5.
assert p['park']['delay_s'] == F(math.floor((room - margin) / float(t['v_mps']) * 20), 20), (p['park'], room, margin)
v6 = c.npc_response('C', F(4), r, p)
rows = v6.phases['program']['transitions']
assert [x['cause'] for x in rows] == ['NOMINAL', 'TURN', 'PARK']
assert rows[1]['after_event'] == 'SPEED_MARKER:NPC:TURN' and rows[2]['after_event'] == 'CLEAR_N_CONFIRMED'
assert v6.targets['TURN'] == t['v_mps'] and v6.targets['PARK'] == 0
assert v6.phases['speed_markers'] == ({'cause': 'TURN', 'marker_arc_m': t['marker_arc_m']},)
assert v6.hash != v5.hash

# no cut -> no PARK; slow NPC -> no TURN; too fast -> blocked; too short -> PARK blocked
assert c.v6_npc_program(r, F(4), region, 3.7, cut=False)['park'] is None
assert c.v6_npc_program(r, F(3), region, 3.7, cut=False)['turn'] is None  # 9/6 = 1.5 <= 2.25
assert c.v6_npc_program(r, F(4), region, 75., cut=True)['reason'] == 'NPC_PARK_ROOM'
late_box = tuple(product((55.5, 56.5), (8., 12.), (-1., 3.)))  # a conflict box after the arc: the slowdown precedes its exit
assert c.v6_npc_program(r, F(4), late_box, 3.7, cut=False)['reason'] == 'NPC_TURN_BEFORE_EXIT'
early = shape(6.)  # the arc starts 6 m after the start: the marker would precede it
assert c.v6_npc_program(early, F(4), region, 3.7, cut=False)['reason'] == 'NPC_TURN_SPEED'

# d: the kit's bound uses the active phase's target
resp = SimpleNamespace(targets={'NOMINAL': F(4), 'TURN': F(29, 8), 'SETTLE': F(0)})
assert kit.active_target(resp, 'TURN') == F(29, 8) and kit.active_target(resp, 'NPC_TRAFFIC_HOLD') == 0

# c: multi-ray ground error drops NONE hits (a ray through a mesh seam) when a labelled hit exists
class World:
    def __init__(self, hits):
        self.hits = iter(hits)
    def ground_projection(self, loc, dist):
        z, lab = next(self.hits)
        return None if z is None else SimpleNamespace(location=SimpleNamespace(z=z), label=lab)
assert kit.ground_error(World([(0., 'Roads')]), (0., 0., .002)) == .002  # labelled centre: one ray, the v5 value
none4 = [(-1.98, 'NONE')] * 4
seam = [(-1.98, 'NONE')] + none4 + [(-1.98, 'NONE'), (.01, 'Road'), (-1.98, 'NONE'), (0., 'Road')]  # found at 0.1 m
assert kit.ground_error(World(seam), (0., 0., .002)) == .002
assert kit.ground_error(World([(-1.98, 'NONE')] + none4 * 4), (0., 0., .002)) == abs(.002 + 1.98)  # none: v5 value
print('OK v6 tooling self-check')
