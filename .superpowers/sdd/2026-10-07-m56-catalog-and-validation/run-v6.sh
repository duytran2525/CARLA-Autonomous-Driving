#!/usr/bin/env bash
# M56 v6 (docs/m56/PREREG_M56_V6_20261026.md, APPROVED by Duy 2026-10-26, option i): for the given scenes, prepare
# again under v6, freeze a C0 partial revision (every earlier preparation, the v6 ones last = they win), run exactly
# ONE A/B per prepared scene (P5), then the pair-level result (fresh W05 + D09 + compare_ab, native-v6-pair.py).
# Product code feat/m56-v6 via M56_CODE; tooling recipe M56_RECIPE=v6; CARLA no_rendering_mode. One own server at a time.
# usage: bash run-v6.sh Town04:M56-P-C01[,M56-P-...] [Town05:...]   (M scenes are prepared on the erratum-3 revision v5g)
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v6
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_v6_run_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe; PYM=../../../.venv-m56-v1/Scripts/python.exe
ID=$A/m56_site_identity_v5_20261024T172844Z.json
REV_M=$(ls -d $A/m56_c0_partial_v5g_2*/c0-partial-v5-frozen-revision.json | tail -1)
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
echo "product $(git -C $M56_CODE log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h) args $*" | tee $LOG/head.txt
NEW=""
for spec in "$@"; do
  t=${spec%%:*}; scenes=${spec#*:}
  CL_=$(echo $scenes | tr ',' '\n' | grep -v -- '-M0' | paste -sd, -); M_=$(echo $scenes | tr ',' '\n' | grep -- '-M0' | paste -sd, -)
  for grp in "C:$CL_" "M:$M_"; do
    k=${grp%%:*}; s=${grp#*:}; [ -z "$s" ] && continue
    while tasklist | grep -qi CarlaUE4; do sleep 15; done
    if [ $k = M ]; then M56_REV=$REV_M $PY -I -X utf8 native-v2-prepare.py $t $s > $LOG/prep-$t-$k.log 2>&1
    else $PY -I -X utf8 native-v2-prepare.py $t $s > $LOG/prep-$t-$k.log 2>&1; fi
    grep -v "^INFO" $LOG/prep-$t-$k.log | grep -E '"event": "(SCENE|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
    NEW="$NEW $(done_path $LOG/prep-$t-$k.log)"
  done
done
E3=$A/m56_v5_m_e3_20261025T155257Z
CL="$A/m56_v2_prepare_Town04_20261025T055137Z $A/m56_v2_prepare_Town05_20261025T083106Z $A/m56_v2_prepare_Town06_20261025T092150Z $A/m56_v2_prepare_Town07_20261025T092316Z $A/m56_v2_prepare_Town04_20261025T120501Z"
MP=""; for t in Town04 Town05 Town06 Town07; do MP="$MP $(done_path $E3/prepM-$t.log)"; done
M4=$(done_path $(ls -td $A/m56_v5_m04_* | head -1)/prep-M04.log)
E4="$(done_path $A/m56_v5_e4_20261025T164551Z/prep-Town04.log) $(done_path $A/m56_v5_e4_20261025T164551Z/prep-Town05.log)"
H=$A/m56_c0_partial_v6_$(date -u +%Y%m%dT%H%M%SZ)
$PYM -I -X utf8 native-v5-revision.py $H $ID $CL $MP $M4 $E4 $NEW > $LOG/revision-v6.log 2>&1
grep -E 'C0_PARTIAL|FREEZE|Traceback' $LOG/revision-v6.log | cut -c1-300
REVF=$H/c0-partial-v5-frozen-revision.json
[ -f $REVF ] || { echo "NOT RUN: v6 revision not frozen"; exit 4; }
for spec in "$@"; do
  t=${spec%%:*}; scenes=${spec#*:}
  N=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));w=sys.argv[2].split(',');print(','.join(c['id'] for c in d['candidates'] if c['id'] in w and (c['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" $REVF $scenes)
  [ -z "$N" ] && { echo "$t: none prepared under v6"; continue; }
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  $PY -I -X utf8 native-v2-ab.py $REVF $t $N > $LOG/ab-$t.log 2>&1
  grep -v "^INFO" $LOG/ab-$t.log | grep -E '"event": "(FIXTURE|ADMISSION|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
  D=$(done_path $LOG/ab-$t.log)
  for s in $(echo $N | tr ',' ' '); do
    [ -d "$D/$s/run" ] && $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair.log 2>&1
  done
  grep -E '"status"|Traceback' $LOG/pair.log | tail -5 | cut -c1-300
done
echo "v6 run finished $(date -u) logs=$LOG"
