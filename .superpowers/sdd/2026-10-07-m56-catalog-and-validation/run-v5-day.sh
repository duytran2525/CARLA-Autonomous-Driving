#!/usr/bin/env bash
# v5 day chain (2026-10-25), one own server at a time, logs in outputs/. Code = merged feat/m56-v1.
#  1. single RERUN (P5: proven harness defect = OUTER_TIMEOUT from the ~1.7 s/tick runner, fixed 6dc46b7) of the M A/B
#     of M02, M03, M06, M07 on C0 partial v5d (unchanged fixtures/recipes);
#  2. v5 preparation of the remaining C/L scenes (Town05-07);
#  3. C0 partial v5e with every v5 preparation, then the FIRST v5 A/B of each prepared C/L scene except C01/C02
#     (C01/C02 wait for Duy: v3.1 was "thêm đúng một lần").
cd "$(dirname "$0")"
O=../../../outputs; T=$(date -u +%Y%m%dT%H%M%SZ); LOG=$O/m56_v5_day_$T
mkdir -p $LOG
wait_free() { while tasklist | grep -qi CarlaUE4; do sleep 30; done; }
PY=../../../.venv-m56-native-v1/Scripts/python.exe
V5D=$O/m56_c0_partial_v5d_20261024T185251Z/c0-partial-v5-frozen-revision.json
for spec in "Town04 M56-P-M02" "Town05 M56-P-M03,M56-P-M06,M56-P-M07"; do
  set -- $spec; wait_free
  $PY -I -X utf8 native-v2-ab.py $V5D $1 $2 > $LOG/rerunM-$1.log 2>&1
  grep -v "^INFO" $LOG/rerunM-$1.log | grep -E '"event": "(FIXTURE|ADMISSION|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
done
for spec in "Town05 M56-P-C04,M56-P-C05,M56-P-C06,M56-P-L03,M56-P-L04,M56-P-L05" "Town06 M56-P-C07,M56-P-C08" "Town07 M56-P-L06,M56-P-L07,M56-P-L08"; do
  set -- $spec; wait_free
  $PY -I -X utf8 native-v2-prepare.py $1 $2 > $LOG/prep-$1.log 2>&1
  grep -v "^INFO" $LOG/prep-$1.log | grep -E '"event": "(SCENE|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
done
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'
PREPS="$A/m56_v2_prepare_Town04_20261024T173123Z $A/m56_v2_prepare_Town05_20261024T175606Z $A/m56_v2_prepare_Town06_20261024T182203Z $A/m56_v2_prepare_Town07_20261024T183632Z $(ls -d $A/m56_v2_prepare_Town0*_20261025T* | tr '\n' ' ')"
R=$A/m56_c0_partial_v5e_$(date -u +%Y%m%dT%H%M%SZ)
../../../.venv-m56-v1/Scripts/python.exe -I -X utf8 native-v5-revision.py $R $A/m56_site_identity_v5_20261024T172844Z.json $PREPS > $LOG/revision-v5e.log 2>&1
grep -E 'C0_PARTIAL|FREEZE|Traceback' $LOG/revision-v5e.log | cut -c1-300
REVF=$R/c0-partial-v5-frozen-revision.json
[ -f $REVF ] || { echo "NOT RUN: v5e not frozen"; exit 3; }
for t in Town04 Town05 Town06 Town07; do
  IDS=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(','.join(c['id'] for c in d['candidates'] if c['town']==sys.argv[2] and c['category'] in ('C','L') and c['id'] not in ('M56-P-C01','M56-P-C02') and (c['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED' and '20261025T' in (c['environment']['runtime_recipe_v2'].get('prepare_json') or '')))" $REVF $t)
  [ -z "$IDS" ] && { echo "$t: no v5-prepared C/L scene"; continue; }
  wait_free
  $PY -I -X utf8 native-v2-ab.py $REVF $t $IDS > $LOG/abCL-$t.log 2>&1
  grep -v "^INFO" $LOG/abCL-$t.log | grep -E '"event": "(FIXTURE|ADMISSION|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
done
echo "day chain finished $(date -u) logs=$LOG"
