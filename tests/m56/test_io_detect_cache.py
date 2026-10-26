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
