#!/usr/bin/env bash
# 2026-11-08 signal-phase v1 erratum 5 (docs/m56/ERRATUM_M56_SIGNAL_PHASE_V1_E5_20261108.md): re-prepare M01 (Town04)
# under v6 + cl-v1 + E5 (M56_SIG5=1) on the same prep revision as cl-v1, product m56-v9; freeze a revision; ONE A/B
# (P5) under the current fixture version dv1 (M56_DRIVABLE=dv1, A/B only, as C08); pair under consumer v9 and v6.
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v9
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_sig5_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe
REV_M=${CLV1_PREP_REV:-$(ls -d $A/m56_c0_partial_v5g_2*/c0-partial-v5-frozen-revision.json | tail -1)}
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
echo "product $(git -C $M56_CODE log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h)" | tee $LOG/head.txt
SPECS="Town04:M56-P-M01"
NEW=""
for spec in $SPECS; do
  t=${spec%%:*}; s=${spec#*:}
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  M56_SIG5=1 M56_REV=$REV_M $PY -I -X utf8 native-v2-prepare.py $t $s > $LOG/prep-$t.log 2>&1
  grep -v "^INFO" $LOG/prep-$t.log | grep -E '"event": "(SCENE|SCENE_ERROR|CL_V1_SPAWN_PITCH|CL_V1_LONG_PROBE|SIGNAL_E5)"|^DONE|^Traceback' | cut -c1-400
  NEW="$NEW $(done_path $LOG/prep-$t.log)"
done
R=$(bash run-io-revision.sh sig5 $NEW | tee $LOG/revision.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')
cat $LOG/revision.log | cut -c1-300
REVF=$R/c0-partial-v5-frozen-revision.json
[ -f "$REVF" ] || { echo "NOT RUN: revision not frozen"; echo SIG5_END; exit 4; }
for spec in $SPECS; do
  t=${spec%%:*}; scenes=${spec#*:}
  N=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));w=sys.argv[2].split(',');print(','.join(c['id'] for c in d['candidates'] if c['id'] in w and (c['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" $REVF $scenes)
  [ -z "$N" ] && { echo "$t: none prepared"; continue; }
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  M56_DRIVABLE=dv1 $PY -I -X utf8 native-v2-ab.py $REVF $t $N > $LOG/ab-$t.log 2>&1
  grep -v "^INFO" $LOG/ab-$t.log | grep -E '"event": "(FIXTURE|ADMISSION|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
  D=$(done_path $LOG/ab-$t.log)
  for s in $(echo $N | tr ',' ' '); do
    [ -d "$D/$s/run" ] || continue
    $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v9.log 2>&1
    M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v6 $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v6.log 2>&1
  done
done
grep -hE '"status"|Traceback' $LOG/pair-v9.log $LOG/pair-v6.log 2>/dev/null | cut -c1-300
echo "SIG5_END logs=$LOG"
