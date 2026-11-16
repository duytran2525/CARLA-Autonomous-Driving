"""2026-11-16: list outputs/ dirs that can leave D: without changing any M56 result.
Keep rule (= what asel2-release.latest_pair reads): per scene, the newest PASS pair-result and the newest pair-result of any
status; every pair dir from today; and every A/B dir named by a kept pair's source_scene_dir. Also keep every A/B dir whose
scene has no pair at all yet (not re-derivable). Movable = other m56_v6_pair_* and m56_*_ab_* dirs, plus the superseded
release run 1. Prints JSON {move: [...], keep_ab: n, bytes}. Read-only. usage: python -I offload-plan-20261116.py"""
import json, sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
TODAY = '20261116'
SUPERSEDED = ['m56_asel2_release_20261114T151317Z']  # release --full run 1 (19/21, MemoryError); run 2 = 20261115T054325Z


def size(p):
    return sum(f.stat().st_size for f in p.rglob('*') if f.is_file())


pairs = {}  # scene -> [(dirname, status, source_scene_dir)]
for f in sorted(OUT.glob('m56_v6_pair_*/*/pair-result.json')):
    j = json.loads(f.read_text(encoding='utf-8'))
    pairs.setdefault(f.parent.name, []).append((f.parent.parent.name, j.get('status'), j.get('source_scene_dir')))

keep_pair = {d for d in (p.name for p in OUT.glob('m56_v6_pair_*')) if TODAY in d}
for scene, rows in pairs.items():
    rows.sort()
    keep_pair.add(rows[-1][0])
    passes = [r for r in rows if r[1] == 'PASS']
    if passes:
        keep_pair.add(passes[-1][0])

keep_ab = set()
for scene, rows in pairs.items():
    for d, _, src in rows:
        if d in keep_pair and src:
            keep_ab.add(Path(src).parent.name)  # source_scene_dir = <ab dir>/<scene>
paired = set(pairs)
ab_dirs = [p for p in OUT.iterdir() if p.is_dir() and '_ab_' in p.name and p.name.startswith('m56_')]
for p in ab_dirs:
    scenes = {c.name for c in p.iterdir() if c.is_dir() and c.name.startswith('M56-')}
    if scenes - paired or TODAY in p.name:
        keep_ab.add(p.name)  # unpaired scene inside, or today's run

move = [p.name for p in OUT.glob('m56_v6_pair_*') if p.is_dir() and p.name not in keep_pair]
move += [p.name for p in ab_dirs if p.name not in keep_ab]
move += [d for d in SUPERSEDED if (OUT / d).is_dir()]
assert not set(move) & keep_pair and not set(move) & keep_ab
total = 0
rows = []
for d in sorted(move):
    b = size(OUT / d); total += b; rows.append((d, b))
json.dump({'move': rows, 'keep_pair': len(keep_pair), 'keep_ab': len(keep_ab), 'bytes': total}, sys.stdout, indent=0)
