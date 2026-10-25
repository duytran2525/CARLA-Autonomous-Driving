"""perf 2026-10-25 (7): encode_record fast paths + cached typing introspection; route structural check cached."""
import os
os.chdir(r'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1')
p = 'm56/model.py'; s = open(p, encoding='utf-8').read()
old = """def _encode_typed(value, kind):
    origin,args=get_origin(kind),get_args(kind)"""
new = """@_lru_cache(maxsize=None)
def _kind_parts_cached(kind):
    return get_origin(kind),get_args(kind)


def _kind_parts(kind):
    try:
        return _kind_parts_cached(kind)
    except TypeError:  # unhashable annotation: no cache
        return get_origin(kind),get_args(kind)


@_lru_cache(maxsize=None)
def _field_names(cls):
    return tuple(f.name for f in fields(cls))


def _encode_typed(value, kind):
    origin,args=_kind_parts(kind)  # perf 2026-10-25: cached typing introspection"""
assert old in s; s = s.replace(old, new)
old = """def encode_record(record: object) -> dict[str, object]:
    if isinstance(record, Fraction):
        return {'numerator': record.numerator, 'denominator': record.denominator}
    if is_dataclass(record):
        hints=_type_hints(type(record))
        return {f.name: _encode_typed(getattr(record,f.name),hints[f.name]) for f in fields(record)}"""
new = """def encode_record(record: object) -> dict[str, object]:
    # perf 2026-10-25: exact-type fast paths first (same results as the generic chain below, which they cannot reach
    # differently: none of these exact types is a Fraction, dataclass, Mapping or sequence of another kind).
    t=type(record)
    if t is str or t is int or t is bool or record is None:
        return record
    if t is float:
        if not math.isfinite(record):
            raise ValueError('NONFINITE')
        return {'binary64': record.hex()}
    if t is tuple or t is list:
        return [encode_record(v) for v in record]
    if t is dict or t is types.MappingProxyType:
        return {k: encode_record(v) for k, v in record.items()}
    if isinstance(record, Fraction):
        return {'numerator': record.numerator, 'denominator': record.denominator}
    if is_dataclass(record):
        hints=_type_hints(t)
        return {name: _encode_typed(getattr(record,name),hints[name]) for name in _field_names(t)}"""
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)

p = 'm56/geometry.py'; s = open(p, encoding='utf-8').read()
old = """    if (len(point)!=3 or not all(isfinite(v) for v in point)
            or len(route.transforms)!=len(route.arc) or len(route.arc)<2
            or any(b<=a for a,b in zip(route.arc,route.arc[1:]))):
        return BlockedFixture(('INVALID_ROUTE_PROJECTION_INPUT',))
    import numpy as np
    px,py,pz=point
    table,arr,finite,degenerate=_route_floats(route)"""
new = """    if len(point)!=3 or not all(isfinite(v) for v in point) or not _route_shape_ok(route):
        return BlockedFixture(('INVALID_ROUTE_PROJECTION_INPUT',))
    import numpy as np
    px,py,pz=point
    table,arr,finite,degenerate=_route_floats(route)"""
assert old in s; s = s.replace(old, new)
old = """def _project_route(point: Vec3, route: DirectedRoute) -> Number | BlockedFixture:
    \"\"\"Exact nearest-segment station"""
new = """_ROUTE_SHAPES = {}


def _route_shape_ok(route):
    \"\"\"len(transforms) == len(arc) >= 2 and arc strictly increasing; a pure function of the frozen route, cached by
    identity (perf 2026-10-25: 9.4 M Fraction comparisons per evaluation). ponytail: bounded clear-all cache.\"\"\"
    hit=_ROUTE_SHAPES.get(id(route))
    if hit is not None and hit[0] is route:
        return hit[1]
    ok=(len(route.transforms)==len(route.arc) and len(route.arc)>=2
        and not any(b<=a for a,b in zip(route.arc,route.arc[1:])))
    if len(_ROUTE_SHAPES)>4096:
        _ROUTE_SHAPES.clear()
    _ROUTE_SHAPES[id(route)]=(route,ok)
    return ok


def _project_route(point: Vec3, route: DirectedRoute) -> Number | BlockedFixture:
    \"\"\"Exact nearest-segment station"""
assert s.count(old) == 1; s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)

p = 'tests/m56/test_v5_perf_caches.py'; t = open(p, encoding='utf-8').read()
t += '''

def _encode_reference(record):
    """The pre-2026-10-25 encode_record chain (reference for the fast paths)."""
    import math, types
    from dataclasses import fields, is_dataclass
    from collections.abc import Mapping
    from pathlib import Path
    from m56.model import _encode_typed, _type_hints
    if isinstance(record, F):
        return {'numerator': record.numerator, 'denominator': record.denominator}
    if is_dataclass(record):
        hints = _type_hints(type(record))
        return {f.name: _encode_typed(getattr(record, f.name), hints[f.name]) for f in fields(record)}
    if isinstance(record, Mapping):
        return {k: encode_record(v) for k, v in record.items()}
    if isinstance(record, (tuple, list)):
        return [encode_record(v) for v in record]
    if isinstance(record, float):
        if not math.isfinite(record):
            raise ValueError('NONFINITE')
        return {'binary64': record.hex()}
    if isinstance(record, Path):
        return str(record)
    if record is None or isinstance(record, (str, int, bool)):
        return record
    raise ValueError('UNSERIALIZABLE_RUNTIME_OBJECT')


def test_encode_record_fast_paths_match_the_reference():
    import types
    ref0 = SourceRef('synthetic://e', 'a' * 64, 1, '1', 'literal', 'SYNTHETIC_TEST', 3, F(1, 20))
    route = DirectedRoute((), tuple(Transform6(i / 4, -0.0, 1e-300, 0., 90., 0.) for i in range(5)),
                          tuple(F(i, 4) for i in range(5)), 'b' * 64, (ref0,), F(1))
    samples = [route, ref0, F(-7, 3), 1.5, -0.0, 0, True, None, 'x', [1, 2.5, F(1, 2)], (ref0, 'y'),
               {'a': route, 'b': [F(1), {'c': 2.25}]}, types.MappingProxyType({'k': (1, 2)})]
    for x in samples:
        assert encode_record(x) == _encode_reference(x)
    from m56.geometry import _route_shape_ok
    assert _route_shape_ok(route) and _route_shape_ok(route)
    bad = DirectedRoute((), route.transforms, (F(0), F(1), F(1), F(2), F(3)), 'b' * 64, (ref0,), F(1))
    assert not _route_shape_ok(bad)
'''
open(p, 'w', encoding='utf-8').write(t)
print('ok')
