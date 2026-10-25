"""M56 v5 consumer changes (prereg eda7680), both rules kept: C1 route-distance run-in, C2 response nominal."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest
from tests.m56.test_lateral_contract import lateral_case  # noqa: F401 (fixture)

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



def _real_lateral(lateral_case, yaw=0., sep=3.5, target_shift=0., box_sep=None):
    """v5 C3 + erratum 1 (22c5cd4): a 0.25 m CARLA-like lane-centre route rotated by yaw, its target-lane switch route
    and axis lane boxes; sep is the reviewed right-vector separation."""
    from math import cos, sin, radians
    from itertools import product
    from m56.model import Transform6
    c = lateral_case; r = radians(yaw); f, rt = (cos(r), sin(r)), (-sin(r), cos(r))
    def route(offset):
        pts = tuple(Transform6(f[0]*i/4 + rt[0]*offset, f[1]*i/4 + rt[1]*offset, 0., 0., yaw, 0.) for i in range(401))
        return replace(c.response.route, transforms=pts, arc=tuple(F(i, 4) for i in range(401)))
    base = route(0.); target = route(sep + target_shift)
    b = sep if box_sep is None else box_sep
    def box(offset):  # axis box of the lane centred at offset (only valid for axis yaws)
        cx, cy = rt[0]*offset, rt[1]*offset
        xs = (min(0., f[0]*100) - 1 + cx, max(0., f[0]*100) + 1 + cx); ys = (min(0., f[1]*100) - 1 + cy, max(0., f[1]*100) + 1 + cy)
        xs = xs if abs(f[0]) > .5 else (cx - 1.75, cx + 1.75); ys = ys if abs(f[1]) > .5 else (cy - 1.75, cy + 1.75)
        return tuple(product(xs, ys, (-1., 1.)))
    switch = {**c.response.phases['reference_switches'][0], 'route': target}
    profile = c.profile(10, 18, 0, sep)
    response = replace(c.response, route=base, profile=profile, phases={**c.response.phases, 'reference_switches': (switch,)})
    topology = {**c.fixture.domain.topology, 'action_regions': {'EGO_INITIAL': box(0.), 'EGO_TARGET': box(b)},
                'lane_geometry': {'EGO': {'separation_m': F(sep), 'lane_width_m': {'initial': F(7, 2), 'target': F(7, 2)}}}}
    fixture = SimpleNamespace(domain=SimpleNamespace(topology=topology), environment=c.fixture.environment,
                              routes={'EGO': base})
    return response, fixture


@pytest.mark.parametrize('yaw,sep', [(0., 3.5), (0., -3.5), (90., 3.5), (180., 3.5), (270., -3.5)])
def test_v5_real_axis_route_lane_change_is_admitted(require, lateral_case, yaw, sep):
    response, fixture = _real_lateral(lateral_case, yaw, sep)
    assert require('m56.response', '_lateral_contract')(response, fixture) is None


@pytest.mark.parametrize('kw,error', [
    (dict(yaw=37.), 'LATERAL_GEOMETRY_UNSUPPORTED'),
    (dict(box_sep=-3.5), 'LATERAL_SEPARATION_INVALID'),
    (dict(box_sep=3.6), 'LATERAL_SEPARATION_INVALID'),
    (dict(target_shift=.2), 'REFERENCE_SWITCH_DISCONTINUOUS'),
])
def test_v5_real_route_faults_block(require, lateral_case, kw, error):
    response, fixture = _real_lateral(lateral_case, **kw)
    with pytest.raises(ValueError, match=error):
        require('m56.response', '_lateral_contract')(response, fixture)


def test_v5_real_route_not_the_fixture_route_blocks(require, lateral_case):
    response, fixture = _real_lateral(lateral_case)
    fixture.routes = {'EGO': lateral_case.response.route}
    with pytest.raises(ValueError, match='LATERAL_GEOMETRY_UNSUPPORTED'):
        require('m56.response', '_lateral_contract')(response, fixture)


def _c4_case(gap_x, proof_hash=None):
    """EGO +x on y=0; the NPC crosses it at the origin, then turns and comes back within 1.5 m of it at x=gap_x. Two
    disconnected overlap boxes: one at the crossing, one at x=gap_x."""
    from itertools import product
    from m56.catalog import _digest
    def route(points):
        return DirectedRoute((), tuple(Transform6(x, y, 0., 0., 0., 0.) for x, y in points),
                             tuple(F(i, 4) for i in range(len(points))), 'b' * 64, (REF,), F(len(points) // 2, 4))
    ego = route([(-50 + i / 4, 0.) for i in range(401)])
    legs = [(0., -50 + i / 4) for i in range(221)] + [(i / 4, 5.) for i in range(1, int(gap_x * 4) + 1)]
    legs += [(gap_x, 5 - i / 4) for i in range(1, 15)] + [(gap_x + i / 4, 1.5) for i in range(1, 161)]
    npc = route(legs)
    def box(cx, cy):
        return tuple(product((cx - 1, cx + 1), (cy - 1, cy + 1), (0., 2.)))
    selected = (box(0., 0.),); other = (box(gap_x, 0.),)
    proof = SimpleNamespace(kind='CONFLICT_COMPONENT_SELECTION', method='m', raw_refs=(), uncertainty=F(0), status='PROPOSED', review=None,
                            limits={'selected_component_hash': proof_hash or _digest(selected)})
    queries = SimpleNamespace(capabilities=(proof,), routes={'EGO': ego, 'NPC': npc})
    return selected + other, queries, selected, other


def test_v5_disconnected_conflict_selects_the_crossing_component(monkeypatch):
    import m56.geometry as g
    monkeypatch.setattr(g, '_proof_valid', lambda p, kind, binding: kind == p.kind)
    boxes, queries, selected, other = _c4_case(20.)
    assert g.disconnected_old_rule(boxes)
    assert g._selected_component(boxes, queries, 'x') == (selected, other)


@pytest.mark.parametrize('gap,hash_,error', [(6., None, 'CONFLICT_COMPONENTS_TOO_CLOSE'),
                                              (20., 'f' * 64, 'CONFLICT_COMPONENT_SELECTION_MISMATCH')])
def test_v5_disconnected_conflict_faults_block(monkeypatch, gap, hash_, error):
    import m56.geometry as g
    monkeypatch.setattr(g, '_proof_valid', lambda p, kind, binding: kind == p.kind)
    boxes, queries, _, _ = _c4_case(gap, hash_)
    assert g._selected_component(boxes, queries, 'x').reasons == (error,)


def test_v5_disconnected_conflict_without_review_keeps_old_reason():
    import m56.geometry as g
    boxes, queries, _, _ = _c4_case(20.)
    assert g._selected_component(boxes, queries, 'x').reasons == ('DISCONNECTED_CONFLICT_REVIEW_REQUIRED',)
