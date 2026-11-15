"""Replacement 9 final (mechanical): the accepted PROPOSED entry of each slot, from the lap that passed the offline gates
(gate G + separation gate + io16 build), into one replace output, so native-v5-revision gives each slot one round
(suffix S<n+1>). Source laps and their sha256 are recorded.
  python -I asel2-replace9-merge.py OUT.json SLOT=LAP_OUT.json [SLOT=LAP_OUT.json ...]"""
import hashlib, json, sys
from pathlib import Path
out, picks = Path(sys.argv[1]), [a.split('=', 1) for a in sys.argv[2:]]
entries, sources = [], {}
for slot, f in picks:
    p = Path(f)
    (e,) = [x for x in json.loads(p.read_text(encoding='utf-8'))['entries'] if x['slot'] == slot and x['status'] == 'PROPOSED']
    entries.append(e); sources[slot] = {'file': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
assert len({e['slot'] for e in entries}) == len(entries)
doc = {'note': 'A-SEL2 replacement 9 final: accepted lap entry per slot (asel2-replace9-merge.py), Claude quyet duoi uy quyen '
               '2026-11-15', 'sources': sources, 'entries': sorted(entries, key=lambda e: e['slot'])}
with open(out, 'x', encoding='utf-8') as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
print('merged', [e['slot'] for e in doc['entries']], out)
