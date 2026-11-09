#!/usr/bin/env bash
# 2026-11-09: pair-level results of the 4 batch-1 Town12 A/Bs (offline, no CARLA) under consumer v12 (A-SEL2 8).
cd "$(dirname "$0")"
PY=../../../.venv-m56-native-v1/Scripts/python.exe; A=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_v2_ab_Town12_20261108T115001Z
for s in M56-P-C02-S1 M56-P-C03-S1 M56-P-C04-S1 M56-P-L02-S1; do
  for code in m56-v12; do
    M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/$code $PY -I -X utf8 native-v6-pair.py $A/$s > ../../../outputs/m56_asel2_pair_b1_${s}_${code}b.log 2>&1
    echo "$s $code: $(grep '"status"' ../../../outputs/m56_asel2_pair_b1_${s}_${code}b.log | tail -1 | cut -c1-200)"
  done
done
echo PAIR_B1_V12_END
