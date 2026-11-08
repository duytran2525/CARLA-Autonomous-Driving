#!/usr/bin/env bash
# 2026-11-08 A-SEL2 resume (A/B only): for the given frozen revision and "Town:ids" specs, run exactly ONE A/B for each
# PREPARED scene that the watchdog checkpoint (outputs/m56_asel2_checkpoint.json) does NOT show as AB_STARTED/AB_DONE.
# A scene whose A/B started but was interrupted is listed INFRA_INTERRUPTED and never re-run here (spec 4, P5).
# usage: [M56_CODE=...] [M56_DRIVABLE=dv1] bash run-asel2-ab-resume.sh REVISION.json "Town12:id,id Town13:id"
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_SPECTATOR=1 M56_CODE=${M56_CODE:-D:/AI/CARLA-Funny-Moments.worktrees/m56-v10}
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_asel2_cl_resume_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe; REVF=$1
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
for spec in $2; do
  t=${spec%%:*}
  N=$(python -I -c "
import json,sys
rev=json.load(open(sys.argv[1],encoding='utf-8')); ck=json.load(open(sys.argv[3],encoding='utf-8'))['scenes']
w=sys.argv[2].split(','); out=[]
for c in rev['candidates']:
    if c['id'] not in w or (c['environment'].get('runtime_recipe_v2') or {}).get('status')!='PREPARED': continue
    ab=ck.get(c['id'],{}).get('ab')
    if ab: print('SKIP',c['id'],ab if ab=='AB_DONE' else 'INFRA_INTERRUPTED',file=sys.stderr); continue
    out.append(c['id'])
print(','.join(out))" $REVF ${spec#*:} $A/m56_asel2_checkpoint.json)
  [ -z "$N" ] && { echo "$t: nothing to resume"; continue; }
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  M56_DRIVABLE=${M56_DRIVABLE:-dv1} $PY -I -X utf8 native-v2-ab.py $REVF $t $N > $LOG/ab-$t.log 2>&1
  D=$(done_path $LOG/ab-$t.log)
  for s in $(echo $N | tr ',' ' '); do
    [ -d "$D/$s/run" ] || continue
    $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v10.log 2>&1
    echo "$s v10: $(grep -o '"scene": "'$s'", "status": "[A-Z_]*"' $LOG/pair-v10.log | tail -1)"
  done
done
echo "ASEL2_RESUME_END logs=$LOG"
