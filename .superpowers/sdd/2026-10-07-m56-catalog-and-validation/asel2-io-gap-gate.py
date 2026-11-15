"""Addendum L (2026-11-15): the gap realised at t0 in probe 2 must match the catalog gap before any compile / A/B.
native-io-prepare clamps the NPC start to the first row of the site road, so a negative shift that needs road before it
grows the gap by |shift| (I04 46.4 vs 13.2 m). Fail closed: no prepare.json, no gap, or |gap_at_t0_probe2 - gap| > 0.5 m.
  python -I asel2-io-gap-gate.py PREP_SCENE_DIR      (exit 0 GAP_OK, 3 GAP_NOT_REALISED / GAP_UNKNOWN)"""
import json, sys
from fractions import Fraction as F
from pathlib import Path

TOL = 0.5  # registered: PREREG_M56_IO_RECIPE_V1_20261026.md "|gap - spec| <= 0,5 m"; sweep: good <= 0.42, clamped >= 3.25


def num(v):
    if isinstance(v, dict) and 'binary64' in v:
        return float.fromhex(v['binary64'])
    return float(F(int(v['numerator']), int(v['denominator']))) if isinstance(v, dict) else float(v)


def gate(prep):
    try:
        j = json.loads((Path(prep) / 'prepare.json').read_text(encoding='utf-8'))
        gap, real = num(j['geometry']['gap']), num(j['gap_at_t0_probe2'])
    except (OSError, KeyError, TypeError, ValueError) as e:
        return 'GAP_UNKNOWN', repr(e)
    ok = abs(real - gap) <= TOL
    return ('GAP_OK' if ok else 'GAP_NOT_REALISED'), f'gap={gap:.3f} realised={real:.3f} shift={num(j["npc_shift_m"]):.3f}'


if __name__ == '__main__':
    st, why = gate(sys.argv[1])
    print(st, why)
    sys.exit(0 if st == 'GAP_OK' else 3)
