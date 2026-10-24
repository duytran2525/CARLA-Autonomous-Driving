#!/usr/bin/env bash
# v3.1: wait for full suite 9; run the single extra A/B (C01, C02) only if the chain PASSED. Duy 2026-10-24.
cd "$(dirname "$0")"
F=m56-full-suite-9-20261024.run.json
until [ -f $F ]; do sleep 120; done
V=$(python -c "import json;print(json.load(open('$F')).get('verdict_chain'))")
echo "suite9 verdict_chain=$V $(date -u)"
if [ "$V" != "CHAIN_PASSED" ]; then echo "NOT RUN: suite 9 did not pass"; exit 3; fi
S='C:/Users/ADMIN/AppData/Local/Temp/claude/D--AI-CARLA-Funny-Moments-worktrees/c504d458-feeb-4c2b-a56c-62ae1fb312ee/scratchpad'
tasklist | grep -qi CarlaUE4 && { echo "NOT RUN: another CarlaUE4 is running"; exit 4; }
../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-v2-ab.py ../../../outputs/m56_c0_partial_v3_20261024T031543Z/c0-partial-v2-frozen-revision.json Town04 > "$S/ab31-Town04.log" 2>&1
grep -v "^INFO" "$S/ab31-Town04.log" | grep -E '"event": "(FIXTURE|ADMISSION|AB|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-3000
