"""Online detection cost of the evaluating product on a sealed episode, exactly as the native loop calls it: runtime._known_events
on every growing prefix (frames without events), one call per tick. No server.
python -I native-io-online-timing.py SCENE_DIR:ACTION [...]   (M56_CODE / M56_RECIPE set; absolute paths)"""
import sys, time
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401  (M56_CODE first on sys.path)
from m56.model import decode_record, load_json
from m56.runtime import load_episode, _known_events

for spec in sys.argv[1:]:
    sd, action = spec.rsplit(':', 1); sd = Path(sd)
    fixture = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
    ev = load_episode(sd / 'run' / 'episodes' / sd.name / action)
    frames = tuple(replace(f, events=()) for f in ev.raw)
    ticks, t_all = [], time.perf_counter()
    for n in range(1, len(frames) + 1):
        t = time.perf_counter(); events = _known_events(frames[:n], fixture); ticks.append(time.perf_counter() - t)
    q = len(ticks) // 4
    print(f'{sd.name} {action}: {len(frames)} ticks, detection total {time.perf_counter() - t_all:.1f} s, worst tick '
          f'{max(ticks):.3f} s, last-quarter median {sorted(ticks[3 * q:])[len(ticks[3 * q:]) // 2]:.3f} s, '
          f'events {[e.name for e in events]}', flush=True)
