"""v5 harness performance fix: the float-prefiltered route projection equals the exact rational reference."""
import math, random
from fractions import Fraction as F

from m56.model import DirectedRoute, SourceRef, Transform6

REF = SourceRef('synthetic://proj', 'a' * 64, 1, 'test', 'literal', 'SYNTHETIC_TEST')


def route(points):
    pts = tuple(Transform6(x, y, z, 0., 0., 0.) for x, y, z in points)
    arc = [F(0)]
    for a, b in zip(pts, pts[1:]):
        arc.append(arc[-1] + F(str(round(math.dist((a.x, a.y, a.z), (b.x, b.y, b.z)), 6))))
    return DirectedRoute((), pts, tuple(arc), 'b' * 64, (REF,), arc[-1])


def curved():
    return route([(300 + 40 * math.cos(t / 160), -200 + 40 * math.sin(t / 160), .1 * math.sin(t / 50)) for t in range(800)])


def test_prefiltered_projection_equals_exact_reference():
    from m56.geometry import _project_route, _project_route_exact
    rnd = random.Random(56)
    for r in (curved(), route([(i / 4, 0., 0.) for i in range(400)])):
        for _ in range(300):
            t = rnd.choice(r.transforms)
            p = (t.x + rnd.uniform(-6, 6), t.y + rnd.uniform(-6, 6), t.z + rnd.uniform(-1, 1))
            assert _project_route(p, r) == _project_route_exact(p, r)
        far = (1e4, -1e4, 5.)
        assert _project_route(far, r) == _project_route_exact(far, r)


def test_ties_and_invalid_inputs_match_the_reference():
    from m56.geometry import _project_route, _project_route_exact
    v = route([(-1., 1., 0.), (0., 0., 0.), (1., 1., 0.)])  # symmetric V: equidistant to both legs above the apex
    tie = (0., 2., 0.)
    assert _project_route(tie, v) == _project_route_exact(tie, v)
    assert getattr(_project_route(tie, v), 'reasons', None) == ('NONUNIQUE_PROJECTION',)
    dup = route([(0., 0., 0.), (1., 0., 0.), (2., 0., 0.)])
    dup = DirectedRoute((), (*dup.transforms[:2], dup.transforms[1], dup.transforms[2]), (F(0), F(1), F(3, 2), F(2)), 'b' * 64, (REF,), F(2))
    for p in ((.5, .3, 0.), (float('nan'), 0., 0.)):
        assert _project_route(p, dup) == _project_route_exact(p, dup)
