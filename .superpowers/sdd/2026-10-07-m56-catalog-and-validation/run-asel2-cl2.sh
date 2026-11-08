#!/usr/bin/env bash
# 2026-11-08 A-SEL2 batch 2 (= run-asel2-cl.sh + erratum E6 + technical fix 2 + replacement rounds via M56_ASEL2_REPLACE), C/L/M (docs/m56/PREREG_M56_FILL_V4_ASEL2_20261108.md 6, frozen tooling):
#  1. freeze the A-SEL2 revision (fill v4 successors, no new preps) -> candidates for preparation;
#  2. per town: prepare the listed scenes (v6 + cl-v1 + E5 + spectator), product m56-v10;
#  3. freeze a revision with every new preparation; 4. exactly ONE A/B per PREPARED scene (P5) with dv1 + spectator;
#  5. pair under consumer v10 (= v9 consumer) and v6. One own server at a time. No re-run of any scene.
# usage: bash run-asel2-cl.sh "Town11:M56-P-M04-S1,M56-P-M07-S1 Town12:..."
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_SPECTATOR=1 M56_SPAWN_TILT=${M56_SPAWN_TILT:-} M56_ASEL2_REPLACE=${M56_ASEL2_REPLACE:-} M56_CODE=${M56_CODE:-D:/AI/CARLA-Funny-Moments.worktrees/m56-v10}
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_asel2_cl2_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
echo "product $(git -C $M56_CODE log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h) specs: $1" | tee $LOG/head.txt
R0=$(bash run-asel2-revision.sh asel2base2 | tee $LOG/revision0.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')
cut -c1-300 $LOG/revision0.log
[ -f "$R0/c0-partial-v5-frozen-revision.json" ] || { echo "NOT RUN: base revision not frozen"; echo ASEL2_CL_END; exit 4; }
NEW=""
for spec in $1; do
  t=${spec%%:*}; s=${spec#*:}
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  M56_SIG5=1 M56_E6=1 M56_TF2=1 M56_REV=$R0/c0-partial-v5-frozen-revision.json $PY -I -X utf8 native-v2-prepare.py $t $s > $LOG/prep-$t.log 2>&1
  grep -v "^INFO" $LOG/prep-$t.log | grep -E '"event": "(SCENE|SCENE_ERROR|STREAM_TO|SIGNAL_E5|CL_V1_LONG_PROBE|CL_V1_SPAWN_PITCH)"|^DONE|^Traceback' | cut -c1-400
  NEW="$NEW $(done_path $LOG/prep-$t.log)"
done
R=$(bash run-asel2-revision.sh asel2prep2 $NEW | tee $LOG/revision.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')
cut -c1-300 $LOG/revision.log
REVF=$R/c0-partial-v5-frozen-revision.json
[ -f "$REVF" ] || { echo "NOT RUN: revision not frozen"; echo ASEL2_CL_END; exit 4; }
for spec in $1; do
  t=${spec%%:*}; scenes=${spec#*:}
  N=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));w=sys.argv[2].split(',');print(','.join(c['id'] for c in d['candidates'] if c['id'] in w and (c['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" $REVF $scenes)
  [ -z "$N" ] && { echo "$t: none prepared"; continue; }
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  M56_DRIVABLE=dv1 $PY -I -X utf8 native-v2-ab.py $REVF $t $N > $LOG/ab-$t.log 2>&1
  grep -v "^INFO" $LOG/ab-$t.log | grep -E '"event": "(FIXTURE|ADMISSION|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
  D=$(done_path $LOG/ab-$t.log)
  for s in $(echo $N | tr ',' ' '); do
    [ -d "$D/$s/run" ] || continue
    $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v10.log 2>&1
    M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v10 $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v10abs.log 2>&1
    M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v6 $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v6.log 2>&1
    echo "$s v10: $(grep -o '"scene": "'$s'", "status": "[A-Z_]*"' $LOG/pair-v10.log | tail -1)  v6: $(grep -o '"scene": "'$s'", "status": "[A-Z_]*"' $LOG/pair-v6.log | tail -1)"
  done
done
echo "ASEL2_CL_END logs=$LOG"
