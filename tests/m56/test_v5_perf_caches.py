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


def test_safe_path_cache_still_rejects_a_directory_swapped_for_a_junction(tmp_path):
    import os, shutil, subprocess, pytest
    from m56.evidence import _safe_path
    root = tmp_path / 'run'; (root / 'native').mkdir(parents=True)
    assert _safe_path(root, 'native/a.json') == root / 'native' / 'a.json'
    assert _safe_path(root, 'native/b.json') == root / 'native' / 'b.json'  # cached ancestors
    outside = tmp_path / 'outside'; outside.mkdir()
    shutil.rmtree(root / 'native')
    made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(root / 'native'), str(outside)], capture_output=True)
    if made.returncode != 0:
        pytest.skip('junction creation unavailable')
    with pytest.raises(ValueError, match='PATH_REJECTED'):
        _safe_path(root, 'native/c.json')


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


def test_driver_hash_memo_is_per_object_and_rejects_a_tampered_hash():
    from dataclasses import replace
    import types
    from m56.catalog import _digest
    from m56.model import StockDriver
    from m56.response import _driver_hash_ok
    config = {'actor_id': 1, 'plan': ('a', 'b'), 'opt_dict': {'dt': .05}}
    good = StockDriver(object(), config, _digest(types.MappingProxyType(config)))
    assert isinstance(good.config, types.MappingProxyType)
    assert _driver_hash_ok(good) and _driver_hash_ok(good)
    bad = replace(good, hash='0' * 64)
    assert not _driver_hash_ok(bad) and _driver_hash_ok(good)


def test_partial_spawn_failure_destroys_the_spawned_actors(tmp_path):
    """Native 2026-10-25: EGO spawn collided, the spawned NPC stayed in the world and the next scene saw
    FOREIGN_ACTOR. A partial spawn now cleans its own successes before the episode stops."""
    from tests.m56.test_runtime_ab import ScriptBackend, fixture, context
    from m56.model import SpawnResponse
    from m56.runtime import run_episode
    from tests.m56.test_runtime_ab import META

    class Backend(ScriptBackend):
        def spawn(self, actors, due_tick_cue):
            self.ids = {a.role: 101 + i for i, a in enumerate(actors)}
            return tuple(SpawnResponse(None, 'Spawn failed because of collision at spawn position', META) if a.role == 'EGO'
                         else SpawnResponse(self.ids[a.role], None, META) for a in actors)
    fx = fixture()
    backend = Backend(tmp_path / 'native', lambda t: {'EGO': (F(6), 0), 'NPC': (F(20), 0)}).bind(fx)
    ev = run_episode(context(tmp_path, backend), fx, 'A')
    assert 'SPAWN_ERROR:EGO' in ev.verdict.reasons
    npc = next(i for i, a in zip((101, 102), fx.actors) if a.role == 'NPC')
    assert any(c[0] == 'destroy' and npc in c[1] for c in backend.calls if isinstance(c, tuple)), backend.calls
