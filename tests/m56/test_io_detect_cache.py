"""Perf 2026-10-27 (M56 O03 native A/B hit the 300 s outer deadline): I/O detection resumes from a saved prefix state and
memoizes derived frames. Online prefix calls must equal a cold recomputation."""
from dataclasses import replace

from m56 import metrics
from tests.m56.o_cases import complete_o


def _cold(frames, fixture):
    metrics._CL_CACHE.clear(); metrics._DERIVED_CACHE.clear()
    return metrics.detect_events(frames, fixture)


def test_online_prefixes_equal_cold_recomputation(tmp_path):
    case = complete_o(tmp_path / 'o', 'A')
    frames = tuple(replace(f, events=()) for f in case.episode.raw)
    fixture = case.fixture
    _cold(frames[:2], fixture)
    online = {}
    for n in range(2, len(frames) + 1):
        online[n] = metrics.detect_events(frames[:n], fixture)
    for n in (2, 40, 120, 250, len(frames)):
        assert online[n] == _cold(frames[:n], fixture), n
    assert {'TRIGGER', 'RETURN_MARKER', 'X_END', 'DESTINATION_CONFIRMED'} <= {e.name for e in online[len(frames)]}


def test_identity_memos_do_not_keep_frames_alive():
    # 2026-11-07: 1fc1ac6 memos held strong refs, retaining every episode of a multi-scene process.
    import gc, weakref
    from fractions import Fraction
    from m56.model import FrameRecord
    frames = tuple(FrameRecord('b', 'w', n, Fraction(n, 20), Fraction(1, 20), (), (), {}) for n in range(3))
    assert metrics._contiguous(frames)
    route, region = object(), ((0, 0, 0), (1, 1, 1))
    for f in frames:
        metrics._predicate(f, 'X')
        metrics._frame_memo(metrics._STATION_CACHE, f, (0, id(route)), lambda: 1, guards=(route,))
        metrics._frame_memo(metrics._LANE_HOLD_CACHE, f, (id(region), 0), lambda: True, guards=(region,))
        metrics._frame_memo(metrics._EGO_OFFSET_CACHE, f, 'map:x', lambda: None)
    assert metrics._frame_memo(metrics._STATION_CACHE, frames[0], (0, id(route)), lambda: 2, guards=(route,)) == 1
    refs = [weakref.ref(f) for f in frames]
    del frames, f
    gc.collect()
    assert all(r() is None for r in refs)
