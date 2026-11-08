#!/usr/bin/env bash
# 2026-11-08 A-SEL2 capability smoke test (native-largemap-smoke.py), one fresh own server per town.
cd "$(dirname "$0")"
export M56_NO_RENDER=1
for t in Town12 Town13 Town11 Town15; do
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  timeout 1800 ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-largemap-smoke.py $t > ../../../outputs/m56_largemap_smoke_${t}_20261108b.log 2>&1
  grep -a -o '{"event": "SMOKE[^\r]*' ../../../outputs/m56_largemap_smoke_${t}_20261108b.log | cut -c1-1200
  grep -a "Traceback\|Error" ../../../outputs/m56_largemap_smoke_${t}_20261108b.log | head -3
done
echo SMOKE_ALL_DONE
