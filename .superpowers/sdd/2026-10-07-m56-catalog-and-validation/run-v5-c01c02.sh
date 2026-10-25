#!/usr/bin/env bash
# Duy [chat] 2026-10-25: "cho chuẩn bị lại C01/C02 theo v5 và chạy A/B đúng một lần với fixture v5 mới; ghi nguyên kết
# quả, báo cáo theo cả quy tắc cũ và mới". Waits for the running C/L A/B to release the server. Logs in outputs/.
cd "$(dirname "$0")"
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_v5_c01c02_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe
busy() { tasklist | grep -qi CarlaUE4 || powershell -NoProfile -Command "if (Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'native-v2-(ab|prepare)' }) { exit 0 } else { exit 1 }"; }
while busy; do sleep 30; done
echo "server free $(date -u)"
$PY -I -X utf8 native-v2-prepare.py Town04 M56-P-C01,M56-P-C02 > $LOG/prep-Town04.log 2>&1
grep -v "^INFO" $LOG/prep-Town04.log | grep -E '"event": "(SCENE|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
P=$(grep -o 'DONE .*' $LOG/prep-Town04.log | cut -c6- | tr '\' '/')
PREPS="$A/m56_v2_prepare_Town04_20261024T173123Z $A/m56_v2_prepare_Town05_20261024T175606Z $A/m56_v2_prepare_Town06_20261024T182203Z $A/m56_v2_prepare_Town07_20261024T183632Z $A/m56_v2_prepare_Town04_20261025T055137Z $A/m56_v2_prepare_Town05_20261025T083106Z $A/m56_v2_prepare_Town06_20261025T092150Z $A/m56_v2_prepare_Town07_20261025T092316Z $P"
R=$A/m56_c0_partial_v5f_$(date -u +%Y%m%dT%H%M%SZ)
../../../.venv-m56-v1/Scripts/python.exe -I -X utf8 native-v5-revision.py $R $A/m56_site_identity_v5_20261024T172844Z.json $PREPS > $LOG/revision-v5f.log 2>&1
grep -E 'C0_PARTIAL|FREEZE|Traceback' $LOG/revision-v5f.log | cut -c1-300
REVF=$R/c0-partial-v5-frozen-revision.json
[ -f $REVF ] || { echo "NOT RUN: v5f not frozen"; exit 3; }
N=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(','.join(c['id'] for c in d['candidates'] if c['id'] in ('M56-P-C01','M56-P-C02') and (c['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" $REVF)
[ -z "$N" ] && { echo "C01/C02 not prepared: no A/B"; exit 0; }
while busy; do sleep 30; done
$PY -I -X utf8 native-v2-ab.py $REVF Town04 $N > $LOG/ab-Town04.log 2>&1
grep -v "^INFO" $LOG/ab-Town04.log | grep -E '"event": "(FIXTURE|ADMISSION|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
echo "C01/C02 v5 finished $(date -u) logs=$LOG"
