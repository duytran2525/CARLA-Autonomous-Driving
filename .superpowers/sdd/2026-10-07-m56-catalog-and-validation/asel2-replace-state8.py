"""A-SEL2 replacement 8 state (2026-11-15, B3 under io-v1.6 3b + addendum G): from state 7 lap 1 -- O04 takes its replacement
7 site (O04-S2) in `assigned` and `tried`; the new slot is O07 (O07-S1 EXCLUDED under io-v1.6: WINDOW_TOO_SHORT 114.3 > 113.1 m).
Lap n: sites rejected in earlier laps (gate G or io16 build flag) join `tried` (given as their replace outputs).
  python -I asel2-replace-state8.py LAP [REJECTED_REPLACE_OUT.json ...] -> outputs/m56_asel2_replace_state_8_<LAP>.json"""
import json, sys
from pathlib import Path
O = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs')
lap, rejected = sys.argv[1], sys.argv[2:]
s = json.loads((O / 'm56_asel2_replace_state_7_1.json').read_text(encoding='utf-8'))
(e7,) = json.loads((O / 'm56_fill_v4_replace7_1_20261115.json').read_text(encoding='utf-8'))['entries']
assert e7['slot'] == 'O04' and e7['status'] == 'PROPOSED'
s['assigned']['O04'] = e7['site']; s['tried'].append(e7['site'])
assert s['assigned']['O07'] in s['tried'], 'O07-S1 site must be tried'
for f in rejected:
    (e,) = json.loads(Path(f).read_text(encoding='utf-8'))['entries']
    assert e['slot'] == 'O07' and e['status'] == 'PROPOSED'
    s['tried'].append(e['site'])
s.update(slots=['O07'], order=['O07'],
         note=f'A-SEL2 replacement 8 lap {lap} (B3, io-v1.6 3b + addendum G): O07-S1 EXCLUDED under io-v1.6 (WINDOW_TOO_SHORT '
              f'114.3>113.1 m). O04 holds O04-S2. Rejects so far: {len(rejected)}. Claude quyet duoi uy quyen 2026-11-15.')
with open(O / f'm56_asel2_replace_state_8_{lap}.json', 'x', encoding='utf-8') as f:
    json.dump(s, f, indent=1, ensure_ascii=False)
print('state 8 lap', lap, 'tried', len(s['tried']))
