"""cProfile of the v22 fast path per-tick work on real F03 B frames (see bench-v22-tick.py): ticks TRIGGER..ROWS, hot spots.
M56_CODE=<m56-v22> M56_RECIPE=v6 python -I prof-v22-tick.py [ROWS=500]"""
import cProfile
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location('bench', Path(__file__).resolve().parent / 'bench-v22-tick.py')
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)  # type: ignore[union-attr]
from m56 import runtime  # noqa: E402
from m56.model import ScriptState, decode_record, load_json  # noqa: E402


def main(rows):
    B = bench.B
    fixture = decode_record('CompiledFixture', load_json(B / 'fixture.json'))
    b = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
    frames = bench.load_frames()
    causes = [bench.cmd_of(f).cause if bench.cmd_of(f).kind != 'BLOCKED' else 'BLOCKED' for f in frames]
    start = {}
    for i, f in enumerate(frames):
        start[i] = start[i - 1] if i and causes[i] == causes[i - 1] else f.simtime
    ego_id = next(a.id for a in frames[0].actors if a.role == 'EGO')
    events_all = runtime._known_events(tuple(frames), fixture)
    trig = next(k for k, f in enumerate(frames) if f.frame == next(e for e in events_all if e.name == 'TRIGGER').frame)
    pr = cProfile.Profile()
    for i in range(trig, min(rows, len(frames))):
        pr.enable()
        events = runtime._known_events(tuple(frames[:i + 1]), fixture)
        state = ScriptState(bench.PHASE.get(causes[i], 'BLOCKED_CONTROLLER'), start[i], ())
        runtime._commands(tuple(frames[:i + 1]), frames[0], {'EGO': state}, (b,), {'EGO': ego_id}, fixture, events)
        pr.disable()
    pstats.Stats(pr).sort_stats('tottime').print_stats(22)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 500)
