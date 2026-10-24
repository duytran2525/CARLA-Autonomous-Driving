#!/usr/bin/env bash
# v5 (eda7680 + erratum 1): after suite 9 PASSED and the single v3.1 A/B finished, merge feat/m56-v5 into feat/m56-v1,
# run the affected tests, then PREPARE (no A/B) the C/L scenes under v5 (P-NPC grid, C1 route run-in, C4 component
# selection). One own server at a time (2610). Never runs while another CarlaUE4 runs.
cd "$(dirname "$0")"
S='C:/Users/ADMIN/AppData/Local/Temp/claude/D--AI-CARLA-Funny-Moments-worktrees/c504d458-feeb-4c2b-a56c-62ae1fb312ee/scratchpad'
F=m56-full-suite-9-20261024.run.json
until [ -f $F ]; do sleep 120; done
V=$(python -c "import json;print(json.load(open('$F')).get('verdict_chain'))")
[ "$V" != "CHAIN_PASSED" ] && { echo "NOT RUN: suite 9 verdict $V"; exit 3; }
until grep -qE '^DONE|^Traceback' "$S/ab31-Town04.log" 2>/dev/null; do sleep 60; done
while tasklist | grep -qi CarlaUE4; do sleep 30; done
echo "v3.1 finished $(date -u)"
W=../../..
git -C $W merge --no-edit feat/m56-v5 || { git -C $W merge --abort; echo "NOT RUN: merge failed"; exit 5; }
echo "merged $(git -C $W log -1 --format=%h)"
(cd $W && timeout 1800 .venv-m56-v1/Scripts/python.exe -I -B -X utf8 -m pytest -c tests/m56/pytest.ini --confcutdir tests/m56 -q \
  -p no:cacheprovider tests/m56/test_v5_consumer.py tests/m56/test_stock_adapter.py tests/m56/test_lateral_contract.py \
  tests/m56/test_response.py tests/m56/test_geometry.py tests/m56/test_v2_native_hooks.py) > "$S/v5-merge-tests.log" 2>&1 \
  || { tail -20 "$S/v5-merge-tests.log"; echo "NOT RUN: affected tests failed after merge"; exit 6; }
tail -1 "$S/v5-merge-tests.log"
for spec in "Town04 M56-P-C03,M56-P-L01,M56-P-L02" "Town05 M56-P-C04,M56-P-C05,M56-P-C06,M56-P-L03,M56-P-L04,M56-P-L05" \
            "Town06 M56-P-C07,M56-P-C08" "Town07 M56-P-L06,M56-P-L07,M56-P-L08"; do
  set -- $spec
  while tasklist | grep -qi CarlaUE4; do sleep 30; done
  ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-v2-prepare.py $1 $2 > "$S/v5prep-$1.log" 2>&1
  grep -v "^INFO" "$S/v5prep-$1.log" | grep -E '"event": "(SCENE|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-400
done
echo "v5 preparation finished $(date -u)"
