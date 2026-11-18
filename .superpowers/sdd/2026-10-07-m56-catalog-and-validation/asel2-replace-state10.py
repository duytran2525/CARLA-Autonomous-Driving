"""A-SEL2 replacement 10 state (2026-11-18, addendum S): state 9 lap 5 + the accepted replacement 9 entries (c4 merge) as
assigned / tried; open slots M01..M08 with the S_NPC_EDGE site gate. Lap n > 1 as state 9: SLOTS env + earlier lap outputs.
  [SLOTS=..] python -I asel2-replace-state10.py LAP [EARLIER_LAP_REPLACE_OUT.json ...] -> outputs/m56_asel2_replace_state_10_<LAP>.json"""
import json, os, sys
from pathlib import Path
O = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs')
lap, earlier = sys.argv[1], sys.argv[2:]
SLOTS = os.environ.get('SLOTS', 'M01,M02,M03,M04,M05,M06,M07,M08').split(',')
s = json.loads((O / 'm56_asel2_replace_state_9_5.json').read_text(encoding='utf-8'))
for e in json.loads((O / 'm56_fill_v4_replace9_c4_20261115.json').read_text(encoding='utf-8'))['entries']:
    assert e['status'] == 'PROPOSED'
    s['assigned'][e['slot']] = e['site']
    if e['site'] not in s['tried']:
        s['tried'].append(e['site'])
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
s.update(slots=SLOTS, order=SLOTS, npc_edge=True,
         note=f'A-SEL2 replacement 10 lap {lap} (addendum S: S_NPC_EDGE site gate for M). Open slots {SLOTS}; earlier lap '
              f'outputs {len(earlier)}. Claude quyet duoi uy quyen 2026-11-18.')
with open(O / f'm56_asel2_replace_state_10_{lap}.json', 'x', encoding='utf-8') as f:
    json.dump(s, f, indent=1, ensure_ascii=False)
print('state 10 lap', lap, 'tried', len(s['tried']), 'slots', SLOTS)
