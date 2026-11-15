"""Replay sealed I episodes (read-only) through native-io-ab-i12.Probe with the product's real _ready / world_vertices and one
detect_events call (events fed only once their time <= the frame time). Must reproduce asel2-i12-forecast.py (addendum H 4).
  M56_CODE=<product> python -I asel2-i12-probe-replay.py REVISION.json EPISODE_DIR [EPISODE_DIR ...]
Import side effects as test-native-io-ab-i12.py (two ImportTest output dirs): move them to the trash folder."""
import importlib.util, sys
from pathlib import Path

here = Path(__file__).resolve().parent
rev, eps = sys.argv[1], sys.argv[2:]
sys.argv = [str(here / 'native-io-ab-i12.py'), rev, 'ImportTest', 'M56-P-X']
s = importlib.util.spec_from_file_location('i12', here / 'native-io-ab-i12.py')
I = importlib.util.module_from_spec(s); s.loader.exec_module(I)
rt = I.runtime
from m56.evidence import _decode_source_record
from m56.metrics import detect_events

for ep in eps:
    e = rt.load_episode(ep)
    fx = _decode_source_record('CompiledFixture', e.fixture)
    fr = tuple(f for f in e.raw if f.simtime - e.raw[0].simtime <= 30)
    events = tuple(detect_events(fr, fx))
    p = I.Probe(fx)
    for i in range(len(fr)):
        p.see(fr[:i + 1], tuple(x for x in events if x.time <= fr[i].simtime))
        if p.stop:
            break
    g = p.gates()
    t0 = fr[0].simtime
    print(Path(ep).parent.name, Path(ep).name, 'stop', p.stop, 'at', float(fr[i].simtime - t0),
          {k: g[k] for k in ('pass', 'reasons', 'ready_after_first_frame_s', 't_clear_minus_trigger_s')},
          'trigger_from_first', None if p.trigger is None else float(p.trigger.time - t0), flush=True)
