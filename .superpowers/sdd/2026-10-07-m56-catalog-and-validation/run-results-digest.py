"""Digest of every M56 run result in outputs/ (2026-11-14), written BEFORE archiving to Drive so nobody has to
re-open the archives. Reads only small JSON files (pair-result.json, ab-result.json, prepare.json status).
usage: python -I run-results-digest.py  -> outputs/m56_results_digest_20261114.{csv,json} and prints a summary"""
import csv, glob, json
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
rows = []


def jl(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8', errors='replace'))
    except Exception:
        return None


for f in sorted(glob.glob(str(OUT / 'm56_*' / 'M56-*' / 'pair-result.json'))):
    d = jl(f)
    if not isinstance(d, dict):
        continue
    ep = d.get('episodes') or {}
    reasons = sorted({r for e in ep.values() if isinstance(e, dict) for r in e.get('reasons', [])})
    comp = [c for c in (d.get('comparisons') or []) if c]
    rows.append({'kind': 'pair', 'root': Path(f).parents[1].name, 'scene': d.get('scene'), 'status': d.get('status'),
                 'witness': '/'.join(str((ep.get(k) or {}).get('witness')) for k in 'AB'),
                 'physical': '/'.join(str((ep.get(k) or {}).get('physical')) for k in 'AB'),
                 'n_comparisons': len(comp), 'reasons': ';'.join(reasons)[:300]})

for f in sorted(glob.glob(str(OUT / 'm56_*' / 'M56-*' / 'ab-result.json'))):
    d = jl(f)
    if not isinstance(d, dict):
        continue
    rows.append({'kind': 'ab', 'root': Path(f).parents[1].name, 'scene': d.get('scene'),
                 'status': ','.join(sorted(str((v or {}).get('status', (v or {}).get('exit', '?'))) if isinstance(v, dict) else str(v)
                                           for v in (d.get('episodes') or {}).values())),
                 'witness': '', 'physical': '', 'n_comparisons': '', 'reasons': (d.get('fixture_sha256') or '')[:12]})

stamp = '20261114'
Path(OUT / f'm56_results_digest_{stamp}.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
with open(OUT / f'm56_results_digest_{stamp}.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['kind', 'root', 'scene', 'status', 'witness', 'physical', 'n_comparisons', 'reasons'])
    w.writeheader(); w.writerows(rows)
print(len(rows), 'rows')
from collections import Counter
print(Counter((r['kind'], r['status']) for r in rows).most_common(30))
