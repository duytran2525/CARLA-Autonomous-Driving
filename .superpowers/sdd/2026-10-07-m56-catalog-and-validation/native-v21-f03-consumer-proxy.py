"""2026-11-20 addendum W check (advisor): do the CONSUMER's zero-tolerance F03 sites (metrics._f_action_window: step<0 needs reverse
readback, last_retreat = last b<a, then _observed_stop 0.5 s) fire on native stop noise? Proxy = the v20 F03-S1 arm B frames
(the BLOCKED command after 7558 held the observed reverse readback with brake 0.3, the same physics v21's STOPPING gives).
Computes ONLY rule firing in TRIGGER -> NPC_STOP_CONFIRMED: every backward step and its readback, last_retreat, whether an
observed 0.5 s stop follows it inside the window. No d_reverse / g_front_min / pair is computed. Read-only.
python -I native-v21-f03-consumer-proxy.py [LAST_FRAME=7800]"""
import json
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401,E402
from m56.metrics import _metric_station, _observed_stop, _reverse_throttle_cap, detect_events  # noqa: E402
from m56.model import decode_record, load_json  # noqa: E402
from m56.response import _f32  # noqa: E402

B = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261119T191948Z\M56-P-F03-S1\run\episodes\M56-P-F03-S1\B')


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


def main(last):
    fixture = decode_record('CompiledFixture', load_json(B / 'fixture.json'))
    frames = tuple(frames_until(B / 'trajectory.json', last))
    ev = {e.name: e for e in detect_events(frames, fixture)}
    trig, end = ev.get('TRIGGER'), ev.get('NPC_STOP_CONFIRMED')
    print('events', {k: v.frame for k, v in ev.items()})
    if trig is None or end is None:
        print('PROXY_INCOMPLETE (no TRIGGER or NPC_STOP_CONFIRMED in frames <=', last, ')'); return 2
    sel = tuple(f for f in frames if trig.frame <= f.frame <= end.frame)
    actors = tuple(next(a for a in f.actors if a.role == 'EGO') for f in sel)
    st = tuple(_metric_station((a.pose.x, a.pose.y, a.pose.z), fixture.routes['EGO']) for a in actors)
    cap = _f32(float(_reverse_throttle_cap(fixture)))
    back, mismatch = [], []
    for i, (a, b) in enumerate(zip(st, st[1:]), 1):
        if b < a:
            c = actors[i].readback
            ok = c is not None and c.reverse and c.manual_gear_shift and c.gear == -1 and c.steer == 0 and c.throttle <= cap and c.brake <= _f32(.30)
            back.append((sel[i].frame, float(b - a), ok))
            if not ok:
                mismatch.append((sel[i].frame, float(b - a), c and (c.reverse, c.gear, c.throttle, c.brake)))
    last_retreat = max((i for i, (a, b) in enumerate(zip(st, st[1:]), 1) if b < a), default=None)
    stop = _observed_stop(sel[last_retreat:]) if last_retreat is not None else None
    print(json.dumps({'window': [trig.frame, end.frame], 'backward_steps': len(back), 'last_backward': back[-5:],
                      'readback_mismatch_781': mismatch[:5], 'last_retreat_frame': sel[last_retreat].frame if last_retreat else None,
                      'observed_stop_after_it': stop.frame if stop else None}))
    fires = bool(mismatch) or stop is None
    print('CONSUMER_PROXY', 'FIRES' if fires else 'QUIET', '(781 mismatch)' if mismatch else '', '(795 no stop after last retreat)' if stop is None else '')
    return 0


if __name__ == '__main__':
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 7800))
