"""A-SEL2 replacement 7 state (2026-11-15, B3 + addendum G route gate): built from state 6 like 6 from 5 -- the slots of
replacement 6 (C07, L08) take their proposed sites in `assigned` and join `tried`; the new slot is O04 (O04-S1 prepare
RUNIN_NOT_STRAIGHT, no A/B spent). Lap n of the addendum G loop: sites the offline gate rejected in earlier laps join
`tried` too (they are passed as replace outputs whose entry is the rejected proposal).
  python -I asel2-replace-state7.py LAP [REJECTED_REPLACE_OUT.json ...]  -> outputs/m56_asel2_replace_state_7_<LAP>.json"""
import json, sys
from pathlib import Path
O = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs')
lap, rejected = sys.argv[1], sys.argv[2:]
s = json.loads((O / 'm56_asel2_replace_state_6.json').read_text(encoding='utf-8'))
r6 = json.loads((O / 'm56_fill_v4_replace6_20261115.json').read_text(encoding='utf-8'))
for e in r6['entries']:
    assert e['status'] == 'PROPOSED'
    s['assigned'][e['slot']] = e['site']; s['tried'].append(e['site'])
assert s['assigned']['O04'] in s['tried'], 'O04-S1 site must be tried'
for f in rejected:
    (e,) = json.loads(Path(f).read_text(encoding='utf-8'))['entries']
    assert e['slot'] == 'O04' and e['status'] == 'PROPOSED'
    s['tried'].append(e['site'])
s.update(slots=['O04'], order=['O04'],
         note=f'A-SEL2 replacement 7 lap {lap} (B3 + addendum G): O04-S1 prepare RUNIN_NOT_STRAIGHT 856/-2 46.15 m (no A/B). '
              f'C07/L08 hold their replacement 6 sites. Offline-gate rejects so far: {len(rejected)}. Claude quyet duoi uy quyen 2026-11-15.')
with open(O / f'm56_asel2_replace_state_7_{lap}.json', 'x', encoding='utf-8') as f:
    json.dump(s, f, indent=1, ensure_ascii=False)
print('state 7 lap', lap, 'tried', len(s['tried']))
