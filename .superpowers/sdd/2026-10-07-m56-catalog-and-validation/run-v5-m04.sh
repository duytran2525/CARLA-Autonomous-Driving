#!/usr/bin/env bash
# M04 under erratum 3 was stopped by FOREIGN_ACTOR:148 (the NPC left behind by M02's failed EGO spawn; harness defect
# fixed in 08e2b5c). Its preparation never ran a probe, so it is prepared again, then gets its single A/B (P5).
# Waits for the M erratum-3 chain; no_rendering_mode + deferred W05 as there.
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_DEFER_W05=1
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_v5_m04_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe; PYM=../../../.venv-m56-v1/Scripts/python.exe
ID=$A/m56_site_identity_v5_20261024T172844Z.json
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
E3=$(ls -td $A/m56_v5_m_e3_* | head -1)
until ls $E3/abM-Town06.log >/dev/null 2>&1 && grep -qE '^DONE|^Traceback' $E3/abM-Town06.log; do sleep 60; done
while tasklist | grep -qi CarlaUE4; do sleep 30; done
export M56_REV=$(ls -d $A/m56_c0_partial_v5g_2*/c0-partial-v5-frozen-revision.json | tail -1)
$PY -I -X utf8 native-v2-prepare.py Town04 M56-P-M04 > $LOG/prep-M04.log 2>&1
grep -v "^INFO" $LOG/prep-M04.log | grep -E '"event": "(SCENE|SCENE_ERROR|PROBE)"|^DONE|^Traceback' | cut -c1-300
P=$(done_path $LOG/prep-M04.log); unset M56_REV
MP=""
for t in Town05 Town06 Town07; do f=$(grep -l "^DONE" $E3/prepM-$t.log 2>/dev/null) && MP="$MP $(done_path $E3/prepM-$t.log)"; done
CL="$A/m56_v2_prepare_Town04_20261025T055137Z $A/m56_v2_prepare_Town05_20261025T083106Z $A/m56_v2_prepare_Town06_20261025T092150Z $A/m56_v2_prepare_Town07_20261025T092316Z $A/m56_v2_prepare_Town04_20261025T120501Z"
H=$A/m56_c0_partial_v5i_$(date -u +%Y%m%dT%H%M%SZ)
$PYM -I -X utf8 native-v5-revision.py $H $ID $CL $(done_path $E3/prepM-Town04.log) $MP $P > $LOG/revision-v5i.log 2>&1
grep -E 'C0_PARTIAL|FREEZE|Traceback' $LOG/revision-v5i.log | cut -c1-300
REVF=$H/c0-partial-v5-frozen-revision.json
[ -f $REVF ] || { echo "NOT RUN: v5i not frozen"; exit 4; }
N=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(','.join(c['id'] for c in d['candidates'] if c['id']=='M56-P-M04' and (c['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" $REVF)
[ -z "$N" ] && { echo "M04 not prepared: no A/B"; exit 0; }
while tasklist | grep -qi CarlaUE4; do sleep 30; done
$PY -I -X utf8 native-v2-ab.py $REVF Town04 $N > $LOG/ab-M04.log 2>&1
grep -v "^INFO" $LOG/ab-M04.log | grep -E '"event": "(FIXTURE|ADMISSION|AB_DEFERRED|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
echo "M04 chain finished $(date -u) logs=$LOG"
