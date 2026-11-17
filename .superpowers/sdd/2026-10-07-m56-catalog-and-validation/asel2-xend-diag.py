"""A-SEL2 diagnostic (read-only): why an I/O episode has X_END_MISSING. Prints product events, the X section station, and the
EGO/NPC route station + speed every ~1 s after TRIGGER and at the last frame.
usage: M56_CODE=<product> python -I asel2-xend-diag.py AB_SCENE_DIR [ACTION]"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import CODE  # noqa: F401
from m56.model import decode_record, load_json
from m56.runtime import load_episode
from m56.metrics import detect_events

d = Path(sys.argv[1]).resolve(); act = sys.argv[2] if len(sys.argv) > 2 else 'A'
fx = decode_record('CompiledFixture', load_json(d / 'fixture-frozen.json'))
ev = load_episode(d / 'run' / 'episodes' / d.name / act)
evs = detect_events(ev.raw, fx)
for e in evs:
    print('EVENT', e.name, e.frame, float(e.time))
print('sections', {k: float(getattr(fx.domain, k).route_station) for k in ('e_entry', 'e_exit', 'n_entry', 'n_exit')}, 'topology', {k: v for k, v in fx.domain.topology.items() if k not in ('action_regions', 'source_region')})
trig = next((e for e in evs if e.name == 'TRIGGER'), None)


def row(f):
    out = []
    for a in f.actors:
        sp = round(math.hypot(float(a.velocity[0]), float(a.velocity[1])), 2)
        out.append(f'{a.role} arc={None if a.arc is None else round(float(a.arc), 2)} v={sp} gaps={ {k: None if g is None else round(float(g), 2) for k, g in a.gaps.items()} }')
    return f'frame {f.frame} t={float(f.simtime):.2f} ' + ' | '.join(out)


last = None
for f in ev.raw:
    if trig is not None and f.simtime >= trig.time and (last is None or f.simtime - last >= 1):
        print(row(f)); last = f.simtime
print('LAST', row(ev.raw[-1]), 'frames', len(ev.raw))
