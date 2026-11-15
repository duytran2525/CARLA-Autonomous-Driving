"""A-SEL2 replacement 9 state (2026-11-15 night, B3): from state 8 lap 1 -- O07 takes its replacement 8 site (O07-S2).
Successor slots (predecessors' sites stay in `tried`):
  I05, I06, I07: io-i-v1.2 3 (successor B3) under io-v1.6 + addendum J (NPC Dlc floor);  I08: io-i-v1.2 3;
  O08, O04: addendum K (site lane separation within 0.25 mm of a mm rounding edge, offline separation gate).
Lap 1 slots: I05 I06 I07 I08 O08. Lap n > 1: the slots still open are given in SLOTS=a,b,...; every PROPOSED site of the
earlier laps' outputs joins `tried`, and the accepted ones (their slot not in SLOTS) are `assigned`.
  [SLOTS=..] python -I asel2-replace-state9.py LAP [EARLIER_LAP_REPLACE_OUT.json ...] -> outputs/m56_asel2_replace_state_9_<LAP>.json"""
import json, os, sys
from pathlib import Path
O = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs')
lap, earlier = sys.argv[1], sys.argv[2:]
SLOTS = os.environ.get('SLOTS', 'I05,I06,I07,I08,O08').split(',')
s = json.loads((O / 'm56_asel2_replace_state_8_1.json').read_text(encoding='utf-8'))
(e8,) = json.loads((O / 'm56_fill_v4_replace8_1_20261115.json').read_text(encoding='utf-8'))['entries']
assert e8['slot'] == 'O07' and e8['status'] == 'PROPOSED'
s['assigned']['O07'] = e8['site']; s['tried'].append(e8['site'])
for k in SLOTS:
    assert s['assigned'][k] in s['tried'], f'{k} predecessor site must be tried'
for f in earlier:
    for e in json.loads(Path(f).read_text(encoding='utf-8'))['entries']:
        if e['status'] != 'PROPOSED':
            continue
        if e['site'] not in s['tried']:
            s['tried'].append(e['site'])
        if e['slot'] not in SLOTS:
            s['assigned'][e['slot']] = e['site']
s.update(slots=SLOTS, order=SLOTS,
         note=f'A-SEL2 replacement 9 lap {lap} (B3: io-i-v1.2 3 + addendum J for I; addendum K for O04/O08). Open slots '
              f'{SLOTS}; earlier lap outputs {len(earlier)}. Claude quyet duoi uy quyen 2026-11-15.')
with open(O / f'm56_asel2_replace_state_9_{lap}.json', 'x', encoding='utf-8') as f:
    json.dump(s, f, indent=1, ensure_ascii=False)
print('state 9 lap', lap, 'tried', len(s['tried']), 'slots', SLOTS)
