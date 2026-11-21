"""2026-11-22 v23 gate (addendum Y) on REAL data, producer decision only (no metric is computed on the v22 F03 B episode).
The v22 F03-S1 arm B (outputs/m56_f_ab_Town12_20261121T155336Z) reached DESTINATION_CONFIRMED with 0 BLOCKED, but rolled back
1.46-1.71 mm per tick at frames 8864-8870 after the forward gear (stock continuation, brake 0), and its pair was FAILED
(POST_END_UNPLANNED_REVERSE). Replays the runner's own dispatch (runtime._commands) under M56_CODE on the v22 B observations
from the TRIGGER to LAST, with the phase held then (cause recorded on the frame's own command; a phase starts at the
observation that ISSUED its first command, one tick before the first frame recording that cause):
  1. determinism: up to the first forward-gear observation the dispatch reproduces the recorded next command (kind, cause);
  2. forward start: for the observations from the forward-gear one (8863) to LAST:
       EXPECT=stock (v22, negative control): every command CONTROL FORWARD with control None (stock continuation);
       EXPECT=hold  (v23): CONTROL FORWARD with response.HILL_HOLD_CONTROL while (simtime - phase start) < HILL_HOLD_S, then
                    control None; never BLOCKED.
Prints V23_F03_HOLD_GATE PASS|FAIL <detail>; exit 0 / 3.  python -I native-v23-f03-hold-gate.py EXPECT [LAST=8900]"""
import importlib.util
import json
import sys
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_v2_common  # noqa: F401,E402
from m56 import response as R, runtime  # noqa: E402
from m56.model import ScriptState, decode_record, load_json  # noqa: E402

spec = importlib.util.spec_from_file_location('px', HERE / 'native-v22-f03-consumer-proxy.py'); px = importlib.util.module_from_spec(spec)
spec.loader.exec_module(px)  # type: ignore[union-attr]
B = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261121T155336Z\M56-P-F03-S1\run\episodes\M56-P-F03-S1\B')
PHASE = {'HOLD': 'HOLD', 'REVERSE': 'REVERSE', 'STOPPING': 'STOPPING', 'FORWARD_GEAR': 'WAIT_FORWARD_GEAR', 'FORWARD': 'FORWARD'}


def own(frame):
    return next(a for a in frame.actors if a.role == 'EGO').commands[0]


def main(expect, last):
    px.B = B
    fixture = decode_record('CompiledFixture', load_json(B / 'fixture.json'))
    b = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
    frames = px.load_frames(last)
    events = runtime._known_events(tuple(frames), fixture)
    trigger = next(e for e in events if e.name == 'TRIGGER')
    ego = next(a.id for a in frames[0].actors if a.role == 'EGO')
    causes = [own(f).cause if own(f).kind != 'BLOCKED' else 'BLOCKED' for f in frames]
    start = {}
    for i, f in enumerate(frames):
        start[i] = start[i - 1] if i and causes[i] == causes[i - 1] else (frames[i - 1].simtime if i else f.simtime)

    def decide(i):
        state = ScriptState(PHASE.get(causes[i], 'BLOCKED_CONTROLLER'), start[i], ())
        (c,) = runtime._commands(tuple(frames[:i + 1]), frames[0], {'EGO': state}, (b,), {'EGO': ego}, fixture, events)
        return c

    t0 = next(k for k, f in enumerate(frames) if f.frame == trigger.frame)
    gear = next(i for i, c in enumerate(causes) if c == 'FORWARD_GEAR')
    det_bad = []
    for i in range(t0, gear):
        c, rec = decide(i), own(frames[i + 1])
        if (c.kind, c.cause) != (rec.kind, rec.cause):
            det_bad.append((frames[i].frame, (c.kind, c.cause), (rec.kind, rec.cause)))
    hold_s = getattr(R, 'HILL_HOLD_S', None); hold_c = getattr(R, 'HILL_HOLD_CONTROL', None)
    fwd_start = frames[gear].simtime  # the forward-gear observation issues the first FORWARD command
    rows, bad = [], []
    for i in range(gear, len(frames)):
        c = decide(i); dt = frames[i].simtime - fwd_start
        rows.append((frames[i].frame, str(dt), c.kind, c.cause, None if c.control is None else (c.control.throttle, c.control.brake)))
        if (c.kind, c.cause) != ('CONTROL', 'FORWARD'):
            bad.append(rows[-1]); continue
        if expect == 'stock':
            want = None
        else:
            want = hold_c if (hold_s is not None and dt < hold_s) else None
        if c.control != want:
            bad.append(rows[-1])
    held = sum(1 for r in rows if r[4] is not None)
    ok = not det_bad and not bad and len(rows) > 0 and (held == 0 if expect == 'stock' else (hold_s is not None and held == int(hold_s / F(1, 20))))
    print(json.dumps({'expect': expect, 'hold_s': str(hold_s), 'determinism_mismatches': det_bad[:5], 'first_rows': rows[:3],
                      'last_held_and_first_stock': [r for r in rows if r[4] is not None][-1:] + [r for r in rows if r[4] is None][:1],
                      'bad': bad[:5]}, default=str))
    print('V23_F03_HOLD_GATE', 'PASS' if ok else 'FAIL', f'mismatches={len(det_bad)} rows={len(rows)} held={held} bad={len(bad)}')
    return 0 if ok else 3


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8900))
