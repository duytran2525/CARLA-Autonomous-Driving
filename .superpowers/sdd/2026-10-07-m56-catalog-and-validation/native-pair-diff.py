"""Compare fresh pair results (outputs/m56_v6_pair_<utc>/<scene>/pair-result.json written after SINCE) with reference
results, field by field. No server.  python -I native-pair-diff.py SINCE_UTC SCENE=REF_PAIR_DIR [...]
SINCE_UTC like 20261107T0930 (compared with the pair dir name); REF_PAIR_DIR = outputs/m56_v6_pair_<utc> holding <scene>."""
import json, sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
KEYS = ('status', 'comparisons', 'metrics', 'episodes', 'w05', 'd09_snapshot', 'd09_binds', 'source_scene_dir')
since, refs = sys.argv[1], dict(a.split('=', 1) for a in sys.argv[2:])
fresh = {}
for f in sorted(OUT.glob('m56_v6_pair_*/*/pair-result.json')):
    if f.parent.parent.name[len('m56_v6_pair_'):] >= since:
        fresh[f.parent.name] = f  # latest wins
bad = 0
for scene, ref in refs.items():
    f = fresh.get(scene)
    if f is None:
        print(f'{scene}: NO FRESH RESULT'); bad += 1; continue
    a = json.loads(f.read_text(encoding='utf-8'))
    b = json.loads((OUT / ref / scene / 'pair-result.json').read_text(encoding='utf-8'))
    diff = [k for k in KEYS if a.get(k) != b.get(k)]
    bad += bool(diff)
    print(f"{scene}: {a['status']} (ref {b['status']} in {ref}) {'DIFF ' + str(diff) if diff else 'IDENTICAL'}  [{f.parent.parent.name}]")
print('ALL_IDENTICAL' if not bad else f'{bad} scene(s) differ or missing')
