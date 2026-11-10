"""Queue 3c helper (resume after the 11/11 safe stop). For TOWN and comma ids, scan every native-v2-ab root of that town
created since SINCE (outputs/m56_v2_ab_<TOWN>_<utc>/<scene>/) and print ONE line:
  RUN <ids not yet frozen anywhere>|PAIR <root/scene of DONE scenes with no pair status in any m56_asel2_q3_*/pair-v12.log>|SKIP <ids>
DONE = ab-result.json; a frozen fixture without ab-result is INFRA_INTERRUPTED (spec 4, P5): never re-run, reported in SKIP.
usage: python -I asel2-q1-remaining.py TOWN ids SINCE_UTC_COMPACT (e.g. 20261110T145000Z)"""
import glob, re, sys
from pathlib import Path
OUT = Path(__file__).resolve().parents[3] / 'outputs'
town, ids, since = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
roots = [r for r in sorted(glob.glob(str(OUT / f'm56_v2_ab_{town}_2*'))) if Path(r).name.rsplit('_', 1)[1] >= since]
paired = set()
for f in glob.glob(str(OUT / 'm56_asel2_q3_2*' / 'pair-v12.log')):
    if Path(f).parent.name.rsplit('_', 1)[1] < since:
        continue
    paired |= set(re.findall(r'"scene": "(M56-P-[^"]+)", "status": "[A-Z_]+"', open(f, encoding='utf-8', errors='replace').read()))
run, pair, skip = [], [], []
for s in ids:
    dirs = [Path(r) / s for r in roots if (Path(r) / s / 'fixture-frozen.json').exists()]
    if not dirs:
        run.append(s)
    elif (dirs[-1] / 'ab-result.json').exists():
        if s not in paired and (dirs[-1] / 'run').is_dir():
            pair.append(str(dirs[-1]).replace('\\', '/'))
        elif s in paired:
            skip.append(s + ':PAIRED')
    else:
        skip.append(s + ':INFRA_INTERRUPTED')
print('RUN ' + ','.join(run) + '|PAIR ' + ' '.join(pair) + '|SKIP ' + ','.join(skip))
