"""M56 v5 consumer changes (prereg eda7680), both rules kept: C1 route-distance run-in, C2 response nominal."""
from fractions import Fraction as F
from types import SimpleNamespace

from m56.model import BodyRecord, DirectedRoute, Section, SourceRef, Transform6

REF = SourceRef('synthetic://v5', 'a' * 64, 1, 'test', 'literal', 'SYNTHETIC_TEST')
BODY = BodyRecord((0., 0., 0.), (0., 0., 0.), (1., .5, .5), (), 'vehicle.audi.a2', {}, {}, REF)


def l_route():
    """EGO heads +y, then turns to +x at (0, 40): an L-shaped route sampled every 0.25 m."""
    pts = [(0., i / 4, 0., 90.) for i in range(161)] + [(i / 4, 40., 0., 0.) for i in range(1, 81)]
    t = tuple(Transform6(x, y, z, 0., yaw, 0.) for x, y, z, yaw in pts)
    arc = tuple(F(i, 4) for i in range(len(t)))
    return DirectedRoute((), t, arc, 'h', (REF,), arc[-1])


def test_runin_measures_route_distance_not_a_side_face_plane():
    from m56.evidence import _runin_route_ok, runin_old_rule
    route = l_route()
    # e_entry: a plane x = 2 with normal +x, crossed by the route after the turn (route station 42)
    entry = Section(((2., 39., -1.), (2., 41., -1.), (2., 39., 1.), (2., 41., 1.)), (1., 0., 0.), F(42), {})
    fixture = SimpleNamespace(routes={'EGO': route}, G=F(11), domain=SimpleNamespace(e_entry=entry))
    ego = SimpleNamespace(body=BODY, pose=Transform6(0., 5., 0., 0., 90., 0.))  # 36 m of route before e_entry
    assert _runin_route_ok(ego, fixture)               # new rule: route distance 36.5 > 11
    assert not runin_old_rule(ego, fixture)            # old rule: plane distance |0+0.5 - 2| = 1.5 <= 11
    late = SimpleNamespace(body=BODY, pose=Transform6(0., 35., 0., 0., 90., 0.))
    assert not _runin_route_ok(late, fixture)          # 42 - (35 + 1) = 6 <= 11


def test_normative_nominal_is_the_response_target():
    from m56.response import _nominal_v5, nominal_old_rule
    response = SimpleNamespace(targets={'NOMINAL': F(6), 'SETTLE': F(0)})
    fixture = SimpleNamespace(environment={'readiness': {'targets_mps': {'EGO': F(5793, 1000)}}})
    assert _nominal_v5(response) == 6
    assert nominal_old_rule(fixture) == F(5793, 1000)

