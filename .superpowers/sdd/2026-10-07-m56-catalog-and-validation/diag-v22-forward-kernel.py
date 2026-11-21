"""2026-11-21 offline: why does the v22 kernel still BLOCK the forward phase on the recorded v21 F03 B frames
(REVERSE_TERMINAL_GEAR_UNPROVEN at 8124, REVERSE_TERMINAL_CONTROL_UNPROVEN at 8127+)? Replays response._reverse_forward's
own inputs for one observation and prints what each check sees. Read-only, no CARLA.
M56_CODE=<m56-v22> M56_RECIPE=v6 python -I diag-v22-forward-kernel.py [FRAME=8124]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401,E402
from m56 import response as R  # noqa: E402
from m56.metrics import _metric_station  # noqa: E402
from m56.model import decode_record, load_json  # noqa: E402

B = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261120T192818Z\M56-P-F03-S1\run\episodes\M56-P-F03-S1\B')


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


def main(at):
    fixture = decode_record('CompiledFixture', load_json(B / 'fixture.json'))
    resp = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
    frames = frames_until(B / 'trajectory.json', at)
    frame = frames[-1]
    actor, history, proof = R._reverse_inputs(frame, resp, fixture, forward=True)
    from m56.runtime import _known_events
    events = _known_events(tuple(frames), fixture)
    trig = next(e for e in events if e.name == 'TRIGGER')
    selected = tuple(f for f in history if f.frame >= trig.frame)
    pos = [_metric_station((a.pose.x, a.pose.y, a.pose.z), resp.route) for f in selected for a in f.actors if a.role == 'EGO']
    print('trigger', trig.frame, 'selected rows', len(selected), 'tolerance (proof.uncertainty)', float(proof.uncertainty))
    rev_idx = [i + 1 for i, (a, b) in enumerate(zip(pos, pos[1:])) if b < a]
    print('backward steps (index, frame, step) last 8:', [(i, selected[i].frame, float(pos[i] - pos[i - 1])) for i in rev_idx[-8:]])
    for i in range(max(0, len(selected) - 12), len(selected)):
        own = next(a for a in selected[i].actors if a.role == 'EGO'); c = own.readback
        print(selected[i].frame, 'station', round(float(pos[i]), 6), 'step', round(float(pos[i] - pos[i - 1]), 7) if i else None,
              'rb(gear', c.gear, 'rev', c.reverse, 'manual', c.manual_gear_shift, 'steer', round(float(c.steer), 5), 'brake', round(float(c.brake), 2), ')')
    last_rev = rev_idx[-1]
    gear_index = next((i for i in range(last_rev + 1, len(selected))
                       if (c := next(a for a in selected[i].actors if a.role == 'EGO').readback) is not None and not c.reverse and not c.manual_gear_shift and c.gear > 0), None)
    print('last_reverse index', last_rev, 'frame', selected[last_rev].frame, '| gear_index', gear_index, 'frame', selected[gear_index].frame if gear_index else None)
    # the first frame whose readback is a forward gear after the true reverse (first gear>0 frame at all after the TRUE reverse)
    first_gear = next(i for i in range(len(selected)) if selected[i].frame > 8100 and next(a for a in selected[i].actors if a.role == 'EGO').readback.gear > 0)
    print('first forward-gear frame', selected[first_gear].frame, 'index', first_gear)
    for k in (first_gear, gear_index):
        if k:
            print(f'_reverse_stop_tail(selected[:{k}]) =', R._reverse_stop_tail(selected[:k], 'EGO', resp.route))


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8124)
