#!/usr/bin/env bash
# Erratum 4 (c49d79d, approved by Duy 2026-10-25): the NPC route ends before a post-destination curve with vN^2 k > 2.5.
# P5 rerun clause: scenes where an action was blocked ONLY by REFERENCE_LATERAL_BUDGET_UNPROVEN from that curve get
# their A/B again exactly once: C01 (action A, v5f A/B) and C05 (A and B, v5 A/B 2026-10-25T121205Z). Old results stay.
# Re-prepare both (same default revision as their v5 preparation), C0 partial v5j (every earlier preparation, the
# new ones last = they win), then the single A/B of each. no_rendering_mode + deferred W05. One own server at a time.
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_DEFER_W05=1
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_v5_e4_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe; PYM=../../../.venv-m56-v1/Scripts/python.exe
ID=$A/m56_site_identity_v5_20261024T172844Z.json
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
echo "code $(git -C ../../.. log -1 --format=%h)"
NEW=""
for spec in "Town04 M56-P-C01" "Town05 M56-P-C05"; do
  set -- $spec; while tasklist | grep -qi CarlaUE4; do sleep 30; done
  $PY -I -X utf8 native-v2-prepare.py $1 $2 > $LOG/prep-$1.log 2>&1
  grep -v "^INFO" $LOG/prep-$1.log | grep -E '"event": "(SCENE|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
  grep -o '"npc_route_end_e4": [^}]*}' $A/$(basename "$(done_path $LOG/prep-$1.log)")/$2/prepare.json 2>/dev/null | cut -c1-300
  NEW="$NEW $(done_path $LOG/prep-$1.log)"
done
E3=$A/m56_v5_m_e3_20261025T155257Z
CL="$A/m56_v2_prepare_Town04_20261025T055137Z $A/m56_v2_prepare_Town05_20261025T083106Z $A/m56_v2_prepare_Town06_20261025T092150Z $A/m56_v2_prepare_Town07_20261025T092316Z $A/m56_v2_prepare_Town04_20261025T120501Z"
MP=""; for t in Town04 Town05 Town06 Town07; do MP="$MP $(done_path $E3/prepM-$t.log)"; done
M4=$(done_path $(ls -td $A/m56_v5_m04_* | head -1)/prep-M04.log)
H=$A/m56_c0_partial_v5j_$(date -u +%Y%m%dT%H%M%SZ)
$PYM -I -X utf8 native-v5-revision.py $H $ID $CL $MP $M4 $NEW > $LOG/revision-v5j.log 2>&1
grep -E 'C0_PARTIAL|FREEZE|Traceback' $LOG/revision-v5j.log | cut -c1-300
REVF=$H/c0-partial-v5-frozen-revision.json
[ -f $REVF ] || { echo "NOT RUN: v5j not frozen"; exit 4; }
for spec in "Town04 M56-P-C01" "Town05 M56-P-C05"; do
  set -- $spec
  N=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(','.join(c['id'] for c in d['candidates'] if c['id']==sys.argv[2] and (c['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" $REVF $2)
  [ -z "$N" ] && { echo "$2 not prepared: no A/B"; continue; }
  while tasklist | grep -qi CarlaUE4; do sleep 30; done
  $PY -I -X utf8 native-v2-ab.py $REVF $1 $N > $LOG/ab-$1.log 2>&1
  grep -v "^INFO" $LOG/ab-$1.log | grep -E '"event": "(FIXTURE|ADMISSION|AB_DEFERRED|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
done
echo "erratum-4 chain finished $(date -u) logs=$LOG"
