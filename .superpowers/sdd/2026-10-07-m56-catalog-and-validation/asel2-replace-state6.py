"""A-SEL2 replacement 6 state (2026-11-15, B3 + addendum F/B5), built from state 5 the same way state 5 was built from 4:
the slot filled by replacement 5 (M06 -> M06-S2) takes its proposed site in `assigned` and joins `tried`; the new slots are
C07 and L08, whose S1 scenes were trialed and FAILED (CLEAR_N_CONFIRMED_MISSING; both generated before the B5 axis gate).
  python -I asel2-replace-state6.py   -> outputs/m56_asel2_replace_state_6.json (create-exclusive)"""
import json
from pathlib import Path
O = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs')
s = json.loads((O / 'm56_asel2_replace_state_5.json').read_text(encoding='utf-8'))
r5 = json.loads((O / 'm56_fill_v4_replace5_20261111.json').read_text(encoding='utf-8'))
(e,) = r5['entries']
assert e['slot'] == 'M06' and e['status'] == 'PROPOSED'
s['assigned']['M06'] = e['site']
s['tried'].append(e['site'])
for slot in ('C07', 'L08'):
    assert s['assigned'][slot] in s['tried'], slot  # the trialed S1 site is never picked again (B3_TRIED)
s.update(slots=['C07', 'L08'], order=['C07', 'L08'],
         note='A-SEL2 replacement 6 (B3; addendum F B5 axis gate on): C07-S1 (Town13 Q1 12/11) and L08-S1 (Town12 Q3 12/11) '
              'trialed and FAILED, both CLEAR_N_CONFIRMED_MISSING (+ EARLY_ENTRY_BEFORE_NPC_CLEAR in B); both were generated '
              'before B5. M06 now holds M06-S2 (replacement 5). Chain run-in (E) kept. Claude quyet duoi uy quyen 2026-11-15.')
with open(O / 'm56_asel2_replace_state_6.json', 'x', encoding='utf-8') as f:
    json.dump(s, f, indent=1, ensure_ascii=False)
print('state 6 written; tried', len(s['tried']))
