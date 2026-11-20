"""2026-11-20 v21 gate (addendum W) on REAL data, producer decision only (no metric is computed on the v20 F03 B episode):
the v20 F03-S1 arm B (outputs/m56_f_ab_Town12_20261119T191948Z) blocked at frame 7559 with REVERSE_RESERVATION_NOT_MAINTAINED
after a +2.19e-4 m step at 7558. Replays the runner's own dispatch (runtime._commands) for frames 7557..7559 with the recorded
phase and the events known online, under M56_CODE. Expect under v20: BLOCKED at 7559 (negative control); under v21: not
BLOCKED (REVERSE kernel command). Prints V21_F03_GATE PASS|FAIL <detail>; exit 0 / 3.
python -I native-v21-f03-gate.py EXPECT (EXPECT = blocked | not_blocked)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401,E402  (M56_CODE on sys.path)
from m56 import runtime  # noqa: E402
from m56.model import ScriptState, decode_record, load_json  # noqa: E402

B = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261119T191948Z\M56-P-F03-S1\run\episodes\M56-P-F03-S1\B')
LAST = 7559


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


def main(expect):
    fixture = decode_record('CompiledFixture', load_json(B / 'fixture.json'))
    b = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
    frames = frames_until(B / 'trajectory.json', LAST)
    events = runtime._known_events(tuple(frames), fixture)
    ego_id = next(a.id for a in frames[0].actors if a.role == 'EGO')
    out = []
    for f in frames:
        if f.frame < LAST - 2:
            continue
        i = frames.index(f)
        # the phase the runner held when it issued this frame's command = the cause recorded on the previous frame
        prev = next(a for a in frames[i - 1].actors if a.role == 'EGO').commands[0]
        states = {'EGO': ScriptState(prev.cause if prev.kind != 'BLOCKED' else 'FAILED', frames[0].simtime, ())}
        (c,) = runtime._commands(tuple(frames[:i + 1]), frames[0], states, (b,), {'EGO': ego_id}, fixture, events)
        out.append((f.frame, c.kind, c.cause))
    last = out[-1]
    blocked = last[1] == 'BLOCKED'
    ok = blocked if expect == 'blocked' else (not blocked and last[1] == 'REVERSE')
    print(json.dumps({'expect': expect, 'commands': out}))
    print('V21_F03_GATE', 'PASS' if ok else 'FAIL', last)
    return 0 if ok else 3


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
