"""Offline check of native_f_realized on the product's synthetic F01/F02 compositions (literal kinematics, known answers).
Run with M56_CODE=m56-v13 and the product dir on sys.path for tests.m56."""
import os, sys, tempfile
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, os.environ['M56_CODE'])
from native_f_realized import realized_action  # noqa: E402
from tests.m56.f01_cases import complete_f01  # noqa: E402
from tests.m56.f02_cases import complete_f02  # noqa: E402

DT = F(1, 20)
with tempfile.TemporaryDirectory() as tmp:
    for name, fn in (('F01', complete_f01), ('F02', complete_f02)):
        for act in ('A', 'B'):
            c = fn(Path(tmp) / f'{name}{act}', act)
            raw = c.episode.raw
            r = realized_action(raw, c.fixture, raw[0].simtime - DT)
            print(name, act, {k: (str(v), float(v)) if isinstance(v, F) else v for k, v in r.items()})
            assert r['ready_frame'] == 131, r
            # literal kinematics: F01 window frames 120..140, NPC 0 at 120 then 3 m/s -> 20*3/21; F02 NPC constant 5 by TRIGGER
            assert r['vN_char'] == (F(20, 7) if name == 'F01' else F(5)), r
            assert r['event_frame'] == (140 if name == 'F01' else 150), r
            assert r['d0'] is not None and r['d0'] > 0, r
print('ALL_OK')
