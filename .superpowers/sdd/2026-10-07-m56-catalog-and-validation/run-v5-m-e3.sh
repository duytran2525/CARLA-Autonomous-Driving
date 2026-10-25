#!/usr/bin/env bash
# v5 erratum 3 (06144be, approved by Duy 2026-10-25): M02-M08 with spec 6.2 G + LrefN -> C0 partial v5g -> native
# preparation -> C0 partial v5h -> the single A/B (P5) of each prepared M scene. Old M preparations (2026-10-24, G = GL)
# are NOT passed to any revision. Waits for the v5f A/B chain. One own server at a time; logs in outputs/.
cd "$(dirname "$0")"
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_v5_m_e3_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe; PYM=../../../.venv-m56-v1/Scripts/python.exe
ID=$A/m56_site_identity_v5_20261024T172844Z.json
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
until ls $A/m56_v5_ab_v5f_*/ab-Town07.log >/dev/null 2>&1 && grep -qE '^DONE|^Traceback' $A/m56_v5_ab_v5f_*/ab-Town07.log; do sleep 60; done
while tasklist | grep -qi CarlaUE4; do sleep 30; done
CL="$A/m56_v2_prepare_Town04_20261025T055137Z $A/m56_v2_prepare_Town05_20261025T083106Z $A/m56_v2_prepare_Town06_20261025T092150Z $A/m56_v2_prepare_Town07_20261025T092316Z $A/m56_v2_prepare_Town04_20261025T120501Z"
G=$A/m56_c0_partial_v5g_$(date -u +%Y%m%dT%H%M%SZ)
$PYM -I -X utf8 native-v5-revision.py $G $ID $CL > $LOG/revision-v5g.log 2>&1
grep -E 'C0_PARTIAL|FREEZE|Traceback' $LOG/revision-v5g.log | cut -c1-300
[ -f $G/c0-partial-v5-frozen-revision.json ] || { echo "NOT RUN: v5g not frozen"; exit 3; }
export M56_REV="$G/c0-partial-v5-frozen-revision.json"
MP=""
for spec in "Town04 M56-P-M02,M56-P-M04" "Town05 M56-P-M03,M56-P-M06,M56-P-M07" "Town06 M56-P-M05" "Town07 M56-P-M08"; do
  set -- $spec; while tasklist | grep -qi CarlaUE4; do sleep 30; done
  $PY -I -X utf8 native-v2-prepare.py $1 $2 > $LOG/prepM-$1.log 2>&1
  grep -v "^INFO" $LOG/prepM-$1.log | grep -E '"event": "(SCENE|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
  MP="$MP $(done_path $LOG/prepM-$1.log)"
done
unset M56_REV
H=$A/m56_c0_partial_v5h_$(date -u +%Y%m%dT%H%M%SZ)
$PYM -I -X utf8 native-v5-revision.py $H $ID $CL $MP > $LOG/revision-v5h.log 2>&1
grep -E 'C0_PARTIAL|FREEZE|Traceback' $LOG/revision-v5h.log | cut -c1-300
REVF=$H/c0-partial-v5-frozen-revision.json
[ -f $REVF ] || { echo "NOT RUN: v5h not frozen"; exit 4; }
for spec in "Town04 M56-P-M02,M56-P-M04" "Town05 M56-P-M03,M56-P-M06,M56-P-M07" "Town06 M56-P-M05" "Town07 M56-P-M08"; do
  set -- $spec
  N=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(','.join(c['id'] for c in d['candidates'] if c['id'] in sys.argv[2].split(',') and (c['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" $REVF $2)
  [ -z "$N" ] && { echo "$1: no prepared M"; continue; }
  while tasklist | grep -qi CarlaUE4; do sleep 30; done
  $PY -I -X utf8 native-v2-ab.py $REVF $1 $N > $LOG/abM-$1.log 2>&1
  grep -v "^INFO" $LOG/abM-$1.log | grep -E '"event": "(FIXTURE|ADMISSION|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
done
echo "M erratum-3 chain finished $(date -u) logs=$LOG"
