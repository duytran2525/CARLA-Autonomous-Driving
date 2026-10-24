#!/usr/bin/env bash
# v5: after the M preparation chain, rebuild C0 partial v5 with the preparation records, then run the single A/B (P5:
# one run per scene) for every PREPARED new M scene (M02-M08 only), code = m56-v5-dev 8fa9632. Stops before a town if
# full suite 9 has finished (the pending v3.1 A/B gets the server).
cd "$(dirname "$0")"
S='C:/Users/ADMIN/AppData/Local/Temp/claude/D--AI-CARLA-Funny-Moments-worktrees/c504d458-feeb-4c2b-a56c-62ae1fb312ee/scratchpad'
O='../../../outputs'
until grep -qE 'M preparation finished|STOPPED|NOT RUN' "$S/../tasks/bzmjwr1lm.output" 2>/dev/null; do sleep 30; done
export M56_CODE='D:/AI/CARLA-Funny-Moments.worktrees/m56-v5-dev'
[ "$(git -C "$M56_CODE" log -1 --format=%h)" = 8fa9632 ] && [ -z "$(git -C "$M56_CODE" status --short)" ] || { echo "NOT RUN: code not at clean 8fa9632"; exit 2; }
R=$O/m56_c0_partial_v5b_$(date -u +%Y%m%dT%H%M%SZ)
PREPS=$(ls -d $O/m56_v2_prepare_Town0*_20261024T17* $O/m56_v2_prepare_Town0*_20261024T18* $O/m56_v2_prepare_Town0*_20261024T19* $O/m56_v2_prepare_Town0*_20261024T2* $O/m56_v2_prepare_Town0*_20261025T* 2>/dev/null)
echo "preparations: $PREPS"
../../../.venv-m56-v1/Scripts/python.exe -I -X utf8 native-v5-revision.py $R $O/m56_site_identity_v5_20261024T172844Z.json \
  $O/m56_v2_prepare_Town04_20261024T025829Z $O/m56_v2_prepare_Town04_20261024T093306Z $PREPS > "$S/v5b-revision.log" 2>&1
grep -E 'C0_PARTIAL_V5_FROZEN|FREEZE_BLOCKED|Traceback' "$S/v5b-revision.log" | cut -c1-300
REVF=$R/c0-partial-v5-frozen-revision.json
[ -f "$REVF" ] || { echo "NOT RUN: revision not frozen"; tail -5 "$S/v5b-revision.log"; exit 3; }
for spec in "Town04 M56-P-M02,M56-P-M04" "Town05 M56-P-M03,M56-P-M06,M56-P-M07" "Town06 M56-P-M05" "Town07 M56-P-M08"; do
  set -- $spec
  N=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(sum(1 for c in d['candidates'] if c['id'] in sys.argv[2].split(',') and (c['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" "$REVF" "$2")
  [ "$N" = 0 ] && { echo "$1: no prepared M scene"; continue; }
  [ -f m56-full-suite-9-20261024.run.json ] && { echo "STOPPED before $1: suite 9 finished (v3.1 A/B goes first)"; exit 0; }
  while tasklist | grep -qi CarlaUE4; do sleep 30; done
  ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-v2-ab.py "$REVF" $1 $2 > "$S/v5abM-$1.log" 2>&1
  grep -v "^INFO" "$S/v5abM-$1.log" | grep -E '"event": "(SCENES|FIXTURE|ADMISSION|AB|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-1500
done
echo "M A/B finished $(date -u)"
