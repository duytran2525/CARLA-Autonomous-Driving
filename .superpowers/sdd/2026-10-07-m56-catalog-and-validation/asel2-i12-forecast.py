"""Offline G1/G3 forecast on sealed I episodes (read-only). argv: product dir, then episode dirs (.../episodes/<scene>/<A|B>)."""
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from m56 import runtime
from m56.metrics import detect_events
from m56.evidence import _decode_source_record
from m56.geometry import world_vertices

NAMES = ('TRIGGER', 'SOURCE_CLEAR_CONFIRMED', 'LANE_CHANGE_PATH_CLEAR', 'NPC_MERGED_AHEAD', 'TARGET_LANE_CONFIRMED',
         'X_END', 'DESTINATION_CONFIRMED', 'STOP_CONFIRMED')
for ep in sys.argv[2:]:
    e = runtime.load_episode(ep)
    if e is None:
        print(ep, 'UNSEALED'); continue
    fx = _decode_source_record('CompiledFixture', e.fixture)
    fr = e.raw; t0 = fr[0].simtime; fr = tuple(f for f in fr if f.simtime - t0 <= 30)
    ev = {}
    for x in detect_events(tuple(fr), fx):
        ev.setdefault(x.name, float(x.time - t0))
    # readiness: first frame where the runner predicate holds (settled = first frame >= SETTLE_S)
    settled = next(f for f in fr if f.simtime - t0 >= runtime.SETTLE_S)
    ready = next((float(fr[i].simtime - t0) for i in range(len(fr)) if fr[i].frame > settled.frame
                  and runtime._ready(fr[:i + 1], settled, fx)), None)
    # geometric t_clear: every NPC bbox vertex outside the EGO_TARGET (source lane) region box
    box = (fx.domain.topology.get('action_regions') or {}).get('EGO_TARGET')
    tclear = None
    if box:
        xs = [float(p[0]) for p in box]; ys = [float(p[1]) for p in box]
        lo, hi = (min(xs), min(ys)), (max(xs), max(ys))
        for f in fr:
            n = next((a for a in f.actors if a.role == 'NPC'), None)
            vs = world_vertices(n.body, n.pose) if n else None
            if vs and all(not (lo[0] <= float(v[0]) <= hi[0] and lo[1] <= float(v[1]) <= hi[1]) for v in vs):
                if 'TRIGGER' in ev and float(f.simtime - t0) >= ev['TRIGGER']:
                    tclear = float(f.simtime - t0); break
    tr = ev.get('TRIGGER')
    print(Path(ep).parent.name, Path(ep).name, 'trig-ready', None if tr is None or ready is None else round(tr - ready, 2), 'frames', len(fr), 'ready_s', ready and round(ready, 2),
          {k: round(v, 2) for k, v in ev.items() if k in NAMES},
          'clear-trig(event)', None if tr is None or 'SOURCE_CLEAR_CONFIRMED' not in ev else round(ev['SOURCE_CLEAR_CONFIRMED'] - tr, 2),
          'tclear_geom', tclear and round(tclear - tr, 2), 'box', bool(box))
