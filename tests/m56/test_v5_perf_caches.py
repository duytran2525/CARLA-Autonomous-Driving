"""Perf caches (2026-10-25) are invisible: same encodings, digests and decoded source records as uncached code."""
import hashlib, json
from fractions import Fraction as F

from m56.model import DirectedRoute, SourceRef, Transform6, encode_record, get_type_hints


def test_type_hint_cache_matches_get_type_hints():
    from m56.model import _type_hints
    assert _type_hints(DirectedRoute) == get_type_hints(DirectedRoute)
    assert _type_hints(DirectedRoute) is _type_hints(DirectedRoute)


def test_route_digest_memo_and_source_decode_memo(tmp_path):
    from m56.catalog import _digest, _encode_digest
    from m56.evidence import _decode_source_record
    ref0 = SourceRef('synthetic://r', 'a' * 64, 1, '1', 'literal', 'SYNTHETIC_TEST')
    route = DirectedRoute((), tuple(Transform6(i / 4, 0., 0., 0., 0., 0.) for i in range(9)),
                          tuple(F(i, 4) for i in range(9)), 'b' * 64, (ref0,), F(2))
    assert _digest(route) == _encode_digest(route) == _digest(route)
    data = json.dumps(encode_record(route)).encode()
    path = tmp_path / 'route.json'; path.write_bytes(data)
    ref = SourceRef(str(path), hashlib.sha256(data).hexdigest(), len(data), '1', 'literal', 'SYNTHETIC_TEST')
    first, second = _decode_source_record('DirectedRoute', ref), _decode_source_record('DirectedRoute', ref)
    assert first == route and second is first
    bad = SourceRef(str(path), 'c' * 64, len(data), '1', 'literal', 'SYNTHETIC_TEST')
    assert _decode_source_record('DirectedRoute', bad) is None


def test_source_ok_reverifies_a_rewritten_file(tmp_path):
    import os
    from m56.evidence import _source_ok
    path = tmp_path / 'blob.bin'; path.write_bytes(b'abc')
    ref = SourceRef(str(path), hashlib.sha256(b'abc').hexdigest(), 3, '1', 'literal', 'SYNTHETIC_TEST')
    assert _source_ok(ref) and _source_ok(ref)
    path.write_bytes(b'abd'); os.utime(path, ns=(10 ** 18, 10 ** 18))
    assert not _source_ok(ref)


def test_vectorized_c4_helpers_equal_the_python_reference():
    import math, random
    from m56.geometry import _float_station, _float_stations, _closest_transform_pair
    rnd = random.Random(4)
    pts = tuple(Transform6(300 + 40 * math.cos(i / 160), -200 + 40 * math.sin(i / 160), .1 * math.sin(i / 50), 0., 0., 0.) for i in range(700))
    arc = [F(0)]
    for a, b in zip(pts, pts[1:]):
        arc.append(arc[-1] + F(str(round(math.dist((a.x, a.y, a.z), (b.x, b.y, b.z)), 6))))
    route = DirectedRoute((), pts, tuple(arc), 'b' * 64, (), arc[-1])
    probe = [(t.x + rnd.uniform(-5, 5), t.y + rnd.uniform(-5, 5), t.z) for t in rnd.sample(pts, 300)]
    # selection-only floats compared with a 5 m gap: equal up to float rounding (1 ulp observed), not bitwise
    assert all(abs(x - y) <= 1e-9 for x, y in zip(_float_stations(probe, route), [_float_station(p, route) for p in probe]))
    other = DirectedRoute((), tuple(Transform6(t.x + 3., t.y - 2., t.z, 0., 0., 0.) for t in pts[::3]), tuple(arc[::3]), 'b' * 64, (), arc[-1])
    ref = min(((a, b) for a in route.transforms for b in other.transforms),
              key=lambda st: sum((u - v) ** 2 for u, v in zip((st[0].x, st[0].y, st[0].z), (st[1].x, st[1].y, st[1].z))))
    assert _closest_transform_pair(route, other) == ref
