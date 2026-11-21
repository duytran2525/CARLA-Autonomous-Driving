"""2026-11-21 read-only diagnosis of the v22 F03-S1 arm B (outputs/m56_f_ab_Town12_20261121T155336Z), after its pair was FAILED
(POST_END_UNPLANNED_REVERSE, REVERSE_COMMAND_REPLAY_UNPROVEN). No metric is computed. Prints:
  1. detect_events, frame range, EGO command cause runs (first frame, cause, kind, count) and BLOCKED causes;
  2. every adjacent-frame EGO/NPC centre-station decrease after the end event that exceeds the CONTINUOUS_GEOMETRY tolerance
     (the metrics._forward_tail rule), with the EGO readback and command at that frame;
  3. metrics._forward_tail itself.
M56_CODE=<m56-v22> M56_RECIPE=v6 python -I diag-v22-f03-b.py [B_DIR]"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_v2_common  # noqa: F401,E402
from m56 import metrics  # noqa: E402
from m56.catalog import _digest  # noqa: E402
from m56.metrics import _continuous_proof, _metric_station, detect_events  # noqa: E402
from m56.model import decode_record, load_json  # noqa: E402

spec = importlib.util.spec_from_file_location('px', HERE / 'native-v22-f03-consumer-proxy.py'); px = importlib.util.module_from_spec(spec)
spec.loader.exec_module(px)  # type: ignore[union-attr]
B = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261121T155336Z\M56-P-F03-S1\run\episodes\M56-P-F03-S1\B')


def main():
    px.B = B
    fixture = decode_record('CompiledFixture', load_json(B / 'fixture.json'))
    frames = tuple(px.load_frames(10 ** 9))
    ev = detect_events(frames, fixture)
    print('frames', frames[0].frame, '..', frames[-1].frame, len(frames), 'events', [(e.name, e.frame) for e in ev])
    runs, blocked = [], {}
    for f in frames:
        ego = next(a for a in f.actors if a.role == 'EGO')
        c = ego.commands[0] if ego.commands else None
        key = (c.cause, c.kind) if c is not None else (None, None)
        if not runs or tuple(runs[-1][1:3]) != key:
            runs.append([f.frame, *key, 0])
        runs[-1][3] += 1
        if c is not None and c.kind == 'BLOCKED':
            blocked[c.cause] = blocked.get(c.cause, 0) + 1
    print('EGO command runs (first_frame, cause, kind, n):', len(runs))
    for r in runs[:40]:
        print('  ', r)
    if len(runs) > 40:
        print('   ...', runs[-5:])
    print('BLOCKED causes', blocked)
    end = next((e for e in ev if e.name == 'NPC_STOP_CONFIRMED'), None)
    if end is None:
        print('no NPC_STOP_CONFIRMED'); return 2
    fh = _digest(fixture); fires = []; small = 0
    for role in ('EGO', 'NPC'):
        route = fixture.routes[role]; prev = None
        for f in (x for x in frames if x.frame >= end.frame):
            a = next(a for a in f.actors if a.role == role)
            s = _metric_station((a.pose.x, a.pose.y, a.pose.z), route) if a.route_valid is True else None
            if prev is not None and s is not None and prev[1] is not None and s < prev[1]:
                p = _continuous_proof(prev[0], f, fh); tol = p.uncertainty if p is not None else 0
                if prev[1] - s > tol:
                    ego = next(x for x in f.actors if x.role == 'EGO'); c = ego.commands[0] if ego.commands else None
                    rb = ego.readback
                    fires.append((role, f.frame, float(prev[1] - s), float(tol), c and (c.kind, c.cause),
                                  rb and (rb.throttle, rb.brake, rb.reverse, rb.gear, round(rb.steer, 4))))
                else:
                    small += 1
            prev = (f, s)
    print('decreases after', end.name, end.frame, ': within tolerance', small, ', beyond:', len(fires))
    for r in fires[:25]:
        print('  FIRE', r)
    print('metrics._forward_tail ->', metrics._forward_tail(frames, fixture, end))
    return 0


if __name__ == '__main__':
    sys.exit(main())
