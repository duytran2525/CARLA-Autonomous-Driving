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

import os
STOP = Path(os.environ['M56_STOP']) if os.environ.get('M56_STOP') else None   # same STOP file as the chain: empty / 'now'
DONE = Path(os.environ['M56_DONE']) if os.environ.get('M56_DONE') else None   # checkpoint: one result line per spec


def stop_mode():
    try:
        return STOP and ('now' if STOP.read_text(encoding='utf-8').strip() == 'now' else 'graceful')
    except FileNotFoundError:
        return None


done = DONE.read_text(encoding='utf-8') if DONE and DONE.exists() else ''
for spec in sys.argv[1:]:
    sd, action = spec.rsplit(':', 1); sd = Path(sd)
    if f'{sd.name} {action}:' in done:
        print(f'SKIP done: {sd.name} {action}', flush=True); continue
    if stop_mode():
        print(f'STOPPED_SAFE graceful before {sd.name} {action}', flush=True); sys.exit(3)
    fixture = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
    ev = load_episode(sd / 'run' / 'episodes' / sd.name / action)
    frames = tuple(replace(f, events=()) for f in ev.raw)
    ticks, t_all = [], time.perf_counter()
    for n in range(1, len(frames) + 1):
        t = time.perf_counter(); events = _known_events(frames[:n], fixture); ticks.append(time.perf_counter() - t)
        if n % 50 == 0 and stop_mode() == 'now':
            print(f'STOPPED_SAFE now in {sd.name} {action} at tick {n} (redone on resume)', flush=True); sys.exit(3)
    q = len(ticks) // 4
    line = (f'{sd.name} {action}: {len(frames)} ticks, detection total {time.perf_counter() - t_all:.1f} s, worst tick '
            f'{max(ticks):.3f} s, last-quarter median {sorted(ticks[3 * q:])[len(ticks[3 * q:]) // 2]:.3f} s, '
            f'events {[e.name for e in events]}')
    print(line, flush=True)
    if DONE:
        with DONE.open('a', encoding='utf-8') as f:
            f.write(line + '\n')
