"""2026-11-21 v22 gate (addendum X) on REAL data, producer decision only (no metric is computed on the v21 F03 B episode).
The v21 F03-S1 arm B (outputs/m56_f_ab_Town12_20261120T192818Z) looped GEAR_TRANSITION -> CONTROL FORWARD -> BLOCKED
REVERSE_APPLIED_CONTROL_UNPROVEN from frame 8123: the forward continuation is the stock PID (readback steer ~ -0.002) and
reverse_intent demanded steer == 0 in every phase. Replays the runner's own dispatch (runtime._commands) under M56_CODE:
  1. determinism: for every observation from the TRIGGER up to the first forward-state one, the phase held then (cause recorded
     on that frame's own command; the command recorded on frame f was issued at observation f-1), the dispatch must reproduce
     the command recorded on frame f+1 (kind, cause). These decisions are identical in v21 and v22 (only the forward check changed);
  2. forward-state observations (recorded cause FORWARD, readback steer != 0): v21 must BLOCK (negative control, EXPECT=blocked),
     v22 must not BLOCK and must issue CONTROL FORWARD (EXPECT=not_blocked). First N=10 samples.
Prints V22_F03_FORWARD_GATE PASS|FAIL <detail>; exit 0 / 3.
python -I native-v22-f03-forward-gate.py EXPECT   (EXPECT = blocked | not_blocked)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401,E402  (M56_CODE on sys.path)
from m56 import runtime  # noqa: E402
from m56.model import ScriptState, decode_record, load_json  # noqa: E402

B = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261120T192818Z\M56-P-F03-S1\run\episodes\M56-P-F03-S1\B')
LAST = 8200
PHASE = {'HOLD': 'HOLD', 'REVERSE': 'REVERSE', 'STOPPING': 'STOPPING', 'FORWARD_GEAR': 'WAIT_FORWARD_GEAR', 'FORWARD': 'FORWARD'}
SAMPLES = 10


def frames_until(path, last):
    text = path.read_text(encoding='utf-8'); dec = json.JSONDecoder(); i = text.index('[') + 1; out = []
    while True:
        while text[i] in ' \n\r\t,':
            i += 1
        if text[i] == ']':
            return out
        obj, i = dec.raw_decode(text, i)
        f = decode_record('FrameRecord', obj); out.append(f)
        if f.frame >= last:
            return out


def own_command(frame):
    return next(a for a in frame.actors if a.role == 'EGO').commands[0]


def main(expect):
    fixture = decode_record('CompiledFixture', load_json(B / 'fixture.json'))
    b = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
    frames = frames_until(B / 'trajectory.json', LAST)
    events = runtime._known_events(tuple(frames), fixture)
    trigger = next(e for e in events if e.name == 'TRIGGER')
    ego_id = next(a.id for a in frames[0].actors if a.role == 'EGO')
    run_start, causes = {}, [own_command(f).cause if own_command(f).kind != 'BLOCKED' else 'BLOCKED' for f in frames]
    for i, f in enumerate(frames):  # start of the contiguous run of the same recorded cause
        run_start[i] = run_start[i - 1] if i and causes[i] == causes[i - 1] else f.simtime

    def decide(i):
        cause = causes[i]
        state = ScriptState(PHASE.get(cause, 'BLOCKED_CONTROLLER'), run_start[i], ())
        (c,) = runtime._commands(tuple(frames[:i + 1]), frames[0], {'EGO': state}, (b,), {'EGO': ego_id}, fixture, events)
        return c

    first_fwd = next(i for i, c in enumerate(causes) if c == 'FORWARD')
    det_bad = []
    for i in range(next(k for k, f in enumerate(frames) if f.frame == trigger.frame), first_fwd):
        c, rec = decide(i), own_command(frames[i + 1])
        if (c.kind, c.cause) != (rec.kind, rec.cause):
            det_bad.append((frames[i].frame, (c.kind, c.cause), (rec.kind, rec.cause)))
    fwd = []
    for i in [k for k, c in enumerate(causes) if c == 'FORWARD'][:SAMPLES]:
        steer = float(next(a for a in frames[i].actors if a.role == 'EGO').readback.steer)
        c = decide(i)
        fwd.append((frames[i].frame, steer, c.kind, c.cause))
    if expect == 'blocked':
        ok = all(k == 'BLOCKED' for _, _, k, _ in fwd)
    else:
        ok = all(k == 'CONTROL' and cause == 'FORWARD' for _, _, k, cause in fwd)
    ok = ok and not det_bad and len(fwd) == SAMPLES and all(s != 0 for _, s, _, _ in fwd)
    print(json.dumps({'expect': expect, 'determinism_mismatches': det_bad[:5], 'forward_state_samples': fwd}))
    print('V22_F03_FORWARD_GATE', 'PASS' if ok else 'FAIL', f'mismatches={len(det_bad)} samples={len(fwd)}')
    return 0 if ok else 3


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
