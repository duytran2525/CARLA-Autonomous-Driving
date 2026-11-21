"""2026-11-21 offline diagnosis of the F05 v21 A/B (pair FAILED: arm A F05_END_MISSING + DESTINATION_CONFIRMED_MISSING in every
F05 run; arm B UNPLANNED_REVERSE + FORWARD_COMMAND_REPLAY_UNPROVEN). Read-only on the sealed run, no CARLA, writes nothing.
usage: M56_CODE=<m56-v21> M56_RECIPE=v6 python -I diag-v21-f05-offline.py A|B"""
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401,E402
from m56.catalog import _digest  # noqa: E402
from m56.metrics import _continuous_proof, _metric_station, _reverse_beyond_jitter, detect_events  # noqa: E402
from m56.model import decode_record, load_json  # noqa: E402
from m56.runtime import load_episode  # noqa: E402

RUN = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261120T181039Z\M56-P-F05\run\episodes\M56-P-F05')


def main(action):
    root = RUN / action
    fx = decode_record('CompiledFixture', load_json(root / 'fixture.json'))
    ev = load_episode(root)
    frames = tuple(ev.raw)
    print('frames', len(frames), 'simtime', float(frames[0].simtime), '->', float(frames[-1].simtime))
    print('events', {e.name: (e.frame, round(float(e.time), 2)) for e in detect_events(frames, fx)})
    route = fx.routes['EGO']
    st = []
    for f in frames:
        a = [x for x in f.actors if x.role == 'EGO']
        st.append(_metric_station((a[0].pose.x, a[0].pose.y, a[0].pose.z), route) if len(a) == 1 else None)
    print('station first/last', float(st[0]), float(st[-1]), 'max', float(max(s for s in st if s is not None)))
    dg = _digest(fx)
    neg, beyond = [], []
    for i in range(1, len(frames)):
        a, b = st[i - 1], st[i]
        if a is None or b is None or b >= a:
            continue
        proof = _continuous_proof(frames[i - 1], frames[i], dg)
        tol = proof.uncertainty if proof is not None else Fraction(0)
        neg.append((frames[i].frame, float(a - b), float(tol)))
        if _reverse_beyond_jitter(frames[i - 1], frames[i], a, b, fx):
            beyond.append((frames[i].frame, float(a - b), float(tol)))
    print('backward steps', len(neg), 'beyond jitter (UNPLANNED_REVERSE)', len(beyond))
    print('largest backward steps', sorted(neg, key=lambda x: -x[1])[:6])
    print('beyond-jitter steps', beyond[:10])
    for i in range(0, len(frames), max(1, len(frames) // 20)):
        f = frames[i]
        e = next(x for x in f.actors if x.role == 'EGO')
        c = e.readback
        print(i, f.frame, round(float(f.simtime), 1), 'station', round(float(st[i]), 3) if st[i] is not None else None,
              'gear', c.gear if c else None, 'throttle', float(c.throttle) if c else None, 'brake', float(c.brake) if c else None)


if __name__ == '__main__':
    main(sys.argv[1])
