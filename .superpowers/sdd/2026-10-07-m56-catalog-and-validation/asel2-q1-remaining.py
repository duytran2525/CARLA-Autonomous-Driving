"""Queue 3c helper (resume after a safe stop). For TOWN and comma ids, scan the native-v2-ab roots of that town and the
queue logs (outputs/m56_asel2_q3_<utc>/ab-<TOWN>.log, pair-v12.log) created since SINCE and print ONE line:
  RUN <ids>|PAIR <root/scene ...>|SKIP <id:REASON,...>
  RUN  = no event and no frozen fixture anywhere since SINCE (killed in stream/raster at most): its P5 A/B is unused;
  PAIR = DONE (ab-result.json) with a run dir and no pair status yet;
  SKIP = PAIRED | NO_RUN_DIR (DONE without run dir) | SCENE_ERROR | BLOCKED_FIXTURE | NOT_ADMITTED | INFRA_INTERRUPTED
         (fixture frozen + admitted, no result: spec 4 / P5, never re-run). A retry of any SKIP is a logged decision.
usage: python -I asel2-q1-remaining.py TOWN ids SINCE_UTC_COMPACT (e.g. 20261110T145000Z)"""
import glob, json, re, sys
from pathlib import Path
OUT = Path(__file__).resolve().parents[3] / 'outputs'
town, ids, since = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
recent = lambda pat: [p for p in sorted(glob.glob(str(OUT / pat))) if Path(p).name.rsplit('_', 1)[1] >= since]
roots = recent(f'm56_v2_ab_{town}_2*')
logs = recent('m56_asel2_q3_2*')
paired, events = set(), {}
for d in logs:
    f = Path(d) / 'pair-v12.log'
    if f.exists():
        paired |= set(re.findall(r'"scene": "(M56-P-[^"]+)", "status": "[A-Z_]+"', f.read_text(encoding='utf-8', errors='replace')))
    f = Path(d) / f'ab-{town}.log'
    if f.exists():
        for line in f.read_text(encoding='utf-8', errors='replace').splitlines():
            if line.startswith('{"event"'):
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get('event') in ('SCENE_ERROR', 'FIXTURE', 'ADMISSION', 'AB') and e.get('scene'):
                    events.setdefault(e['scene'], []).append((e['event'], e.get('status')))
run, pair, skip = [], [], []
for s in ids:
    dirs = [Path(r) / s for r in roots if (Path(r) / s).is_dir()]
    done = [d for d in dirs if (d / 'ab-result.json').exists()]
    ev = events.get(s, [])
    if done:
        if s in paired:
            skip.append(s + ':PAIRED')
        elif (done[-1] / 'run').is_dir():
            pair.append(str(done[-1]).replace('\\', '/'))
        else:
            skip.append(s + ':NO_RUN_DIR')
    elif any(k == 'SCENE_ERROR' for k, _ in ev):
        skip.append(s + ':SCENE_ERROR')
    elif ('FIXTURE', 'BLOCKED_FIXTURE') in ev:
        skip.append(s + ':BLOCKED_FIXTURE')
    elif any(k == 'ADMISSION' and v != 'ADMITTED' for k, v in ev):
        skip.append(s + ':NOT_ADMITTED')
    elif ev or any((d / 'fixture-frozen.json').exists() for d in dirs):
        skip.append(s + ':INFRA_INTERRUPTED')
    else:
        run.append(s)
print('RUN ' + ','.join(run) + '|PAIR ' + ' '.join(pair) + '|SKIP ' + ','.join(skip))
