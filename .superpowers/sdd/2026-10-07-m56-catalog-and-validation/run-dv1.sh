#!/usr/bin/env bash
# 2026-11-08 dv1 (docs/m56/PREREG_M56_DRIVABLE_DV1_20261108.md, POST-NUMBER): freeze a revision = run-io-revision base + the
# preparations of the old A/Bs (C02 v6, M07 v6, C08 08/11; last = they win), then exactly ONE A/B per scene with
# M56_DRIVABLE=dv1 (recipe v6, product m56-v9), pair results under consumer v9 and v6. No re-preparation.
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v9
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_dv1_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
echo "product $(git -C $M56_CODE log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h)" | tee $LOG/head.txt
R=$(bash run-io-revision.sh dv1 $A/m56_v2_prepare_Town05_20261026T095528Z $A/m56_v2_prepare_Town04_20261026T112631Z \
      $A/m56_v2_prepare_Town06_20261108T012553Z | tee $LOG/revision.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')
cat $LOG/revision.log | cut -c1-300
REVF=$R/c0-partial-v5-frozen-revision.json
[ -f "$REVF" ] || { echo "NOT RUN: revision not frozen"; echo DV1_END; exit 4; }
for spec in Town04:M56-P-C02 Town05:M56-P-M07 Town06:M56-P-C08; do
  t=${spec%%:*}; s=${spec#*:}
  N=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(','.join(c['id'] for c in d['candidates'] if c['id']==sys.argv[2] and (c['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" $REVF $s)
  [ -z "$N" ] && { echo "$s: not PREPARED in the revision"; continue; }
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  M56_DRIVABLE=dv1 $PY -I -X utf8 native-v2-ab.py $REVF $t $N > $LOG/ab-$s.log 2>&1
  grep -v "^INFO" $LOG/ab-$s.log | grep -E '"event": "(FIXTURE|ADMISSION|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
  D=$(done_path $LOG/ab-$s.log)
  [ -d "$D/$s/run" ] || continue
  $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v9.log 2>&1
  M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v6 $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v6.log 2>&1
  echo "$s v9: $(grep -o '"scene": "'$s'", "status": "[A-Z_]*"' $LOG/pair-v9.log | tail -1)  v6: $(grep -o '"scene": "'$s'", "status": "[A-Z_]*"' $LOG/pair-v6.log | tail -1)"
done
echo "DV1_END logs=$LOG"
