"""2026-11-21 v22 speed check on REAL data (v21 F03-S1 arm B frames, no CARLA, read-only): the per-tick work of the runner for
the F03 B response = runtime._known_events(prefix) + runtime._commands(...) (reverse_intent -> _reverse_inputs).
  1. equivalence: for every STEP-th observation, the command from the v21 code path (evidence._V22_FAST = False) must be
     identical (dataclass ==) to the one from the v22 fast path (True), same states, same frames;
  2. speed: sequential ticks from the TRIGGER to the last frame, fast path only: seconds per tick at 100/300/600/last rows.
Phases are the recorded ones (cause of the command recorded on that frame, as native-v22-f03-forward-gate.py).
M56_CODE=<m56-v22> M56_RECIPE=v6 python -I bench-v22-tick.py [STEP=60]"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401,E402
from m56 import evidence, runtime  # noqa: E402
from m56.model import ScriptState, decode_record, load_json  # noqa: E402

B = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261120T192818Z\M56-P-F03-S1\run\episodes\M56-P-F03-S1\B')
PHASE = {'HOLD': 'HOLD', 'REVERSE': 'REVERSE', 'STOPPING': 'STOPPING', 'FORWARD_GEAR': 'WAIT_FORWARD_GEAR', 'FORWARD': 'FORWARD'}


def load_frames():
    text = (B / 'trajectory.json').read_text(encoding='utf-8'); dec = json.JSONDecoder(); i = text.index('[') + 1; out = []
    while True:
        while text[i] in ' \n\r\t,':
            i += 1
        if text[i] == ']':
            return out
        obj, i = dec.raw_decode(text, i)
        out.append(decode_record('FrameRecord', obj))


def cmd_of(f):
    return next(a for a in f.actors if a.role == 'EGO').commands[0]


def main(step):
    fixture = decode_record('CompiledFixture', load_json(B / 'fixture.json'))
    b = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
    frames = load_frames()
    causes = [cmd_of(f).cause if cmd_of(f).kind != 'BLOCKED' else 'BLOCKED' for f in frames]
    start = {}
    for i, f in enumerate(frames):
        start[i] = start[i - 1] if i and causes[i] == causes[i - 1] else f.simtime
    ego_id = next(a.id for a in frames[0].actors if a.role == 'EGO')
    events_all = runtime._known_events(tuple(frames), fixture)
    trig = next(k for k, f in enumerate(frames) if f.frame == next(e for e in events_all if e.name == 'TRIGGER').frame)

    def decide(i, events):
        state = ScriptState(PHASE.get(causes[i], 'BLOCKED_CONTROLLER'), start[i], ())
        (c,) = runtime._commands(tuple(frames[:i + 1]), frames[0], {'EGO': state}, (b,), {'EGO': ego_id}, fixture, events)
        return c

    sample = list(range(trig, len(frames), step)) + [len(frames) - 1]
    old = {}
    evidence._V22_FAST = False
    t0 = time.perf_counter()
    for i in sample:
        t = time.perf_counter(); old[i] = decide(i, events_all); print(f'v21 path tick {i:4d} (rows {i + 1}): {time.perf_counter() - t:6.2f} s', flush=True)
    print(f'v21 path total {time.perf_counter() - t0:.1f} s over {len(sample)} ticks', flush=True)
    evidence._V22_FAST = True
    evidence._TRAJECTORIES.clear(); evidence._TRAJ_GROWTH.clear()
    t0 = time.perf_counter(); new = {}; marks = {}
    for i in range(trig, len(frames)):
        t = time.perf_counter()
        events = runtime._known_events(tuple(frames[:i + 1]), fixture)
        t1 = time.perf_counter()
        c = decide(i, events)
        t2 = time.perf_counter()
        if i in old:
            new[i] = c
        if (i + 1) in (100, 300, 600) or i == len(frames) - 1:
            marks[i + 1] = (round(t1 - t, 2), round(t2 - t1, 2))
    print(f'v22 path sequential {len(frames) - trig} ticks: total {time.perf_counter() - t0:.1f} s, '
          f'avg {(time.perf_counter() - t0) / (len(frames) - trig):.3f} s/tick', flush=True)
    print('v22 (known_events s, commands s) at rows:', marks)
    bad = [i for i in sample if old[i] != new[i]]
    print('EQUIVALENCE', 'PASS' if not bad else f'FAIL at ticks {bad[:5]}', f'({len(sample)} sampled ticks)')
    return 0 if not bad else 3


if __name__ == '__main__':
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 60))
