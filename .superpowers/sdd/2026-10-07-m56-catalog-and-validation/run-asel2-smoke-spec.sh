#!/usr/bin/env bash
# 2026-11-08 A-SEL2 smoke variant: spectator above the pair before ticking (M56_SMOKE_SPECTATOR=1). Waits for the first smoke.
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_SMOKE_SPECTATOR=1
until grep -q SMOKE_ALL_DONE ../../../outputs/m56_asel2_smoke_20261108b.stdout.txt 2>/dev/null; do sleep 20; done
for t in Town12 Town13; do
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  timeout 1800 ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-largemap-smoke.py $t > ../../../outputs/m56_largemap_smoke_${t}_20261108spec.log 2>&1
  grep -a '"event": "SMOKE' ../../../outputs/m56_largemap_smoke_${t}_20261108spec.log | tr -d '\r' | cut -c1-1200
  grep -a "Traceback\|Error" ../../../outputs/m56_largemap_smoke_${t}_20261108spec.log | head -3
done
echo SMOKE_SPEC_DONE
