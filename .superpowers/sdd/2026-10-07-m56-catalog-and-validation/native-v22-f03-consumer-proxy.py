"""2026-11-21 addendum X check (advisor): would the CONSUMER reject what the EGO does right after the forward gear?
metrics._forward_tail (POST_END_UNPLANNED_REVERSE) compares adjacent CENTRE stations (not vertex-max) after the frozen end event and fires when a
single step decreases by more than that pair's reviewed CONTINUOUS_GEOMETRY uncertainty (per step, not cumulative). The native uphill release
after the gear shift rolled back 2.5e-4 m then 9.8e-4 m (v21 F03 B frames 8124-8125). This prints, on the v21 F03-S1 arm B frames (read-only),
for every adjacent-frame station decrease of either role: frame, decrease, the tolerance, margin, whether the rule fires, and the verdict of
metrics._forward_tail itself. Computes ONLY rule firing: no d_reverse / g_front_min / pair. Also the window rules (781/795) via the W4c proxy logic.
M56_CODE=<m56-v22 or m56-v21> M56_RECIPE=v6 python -I native-v22-f03-consumer-proxy.py [LAST_FRAME=9999]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401,E402
from m56 import metrics  # noqa: E402
from m56.catalog import _digest  # noqa: E402
from m56.metrics import _continuous_proof, _metric_station, detect_events  # noqa: E402
from m56.model import decode_record, load_json  # noqa: E402

B = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261120T192818Z\M56-P-F03-S1\run\episodes\M56-P-F03-S1\B')


def load_frames(last):
    text = (B / 'trajectory.json').read_text(encoding='utf-8'); dec = json.JSONDecoder(); i = text.index('[') + 1; out = []
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
    frames = tuple(load_frames(last))
    ev = {e.name: e for e in detect_events(frames, fixture)}
    print('events', {k: v.frame for k, v in ev.items()}, 'frames', frames[0].frame, '..', frames[-1].frame)
    end = ev.get('NPC_STOP_CONFIRMED')
    if end is None:
        print('CONSUMER_PROXY_INCOMPLETE (no NPC_STOP_CONFIRMED)'); return 2
    fh = _digest(fixture)
    rows = []
    for role in ('EGO', 'NPC'):
        route = fixture.routes[role]; prev = None
        for f in (x for x in frames if x.frame >= end.frame):
            a = next(a for a in f.actors if a.role == role)
            s = _metric_station((a.pose.x, a.pose.y, a.pose.z), route)
            if prev is not None and s is not None and prev[1] is not None and s < prev[1]:
                p = _continuous_proof(prev[0], f, fh); tol = p.uncertainty if p is not None else 0
                rows.append((role, f.frame, float(prev[1] - s), float(tol), float(tol - (prev[1] - s)), (prev[1] - s) > tol))
            prev = (f, s)
    for r in rows[:12]:
        print('decrease', r)
    print('decreases after the end event:', len(rows), 'of which firing:', sum(1 for r in rows if r[5]),
          'min margin (tolerance - decrease):', min((r[4] for r in rows), default=None))
    failed, unknown = metrics._forward_tail(frames, fixture, end)
    print('metrics._forward_tail ->', failed, unknown)
    print('CONSUMER_PROXY_X', 'FIRES' if failed else 'QUIET')
    return 0


if __name__ == '__main__':
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 9999))
