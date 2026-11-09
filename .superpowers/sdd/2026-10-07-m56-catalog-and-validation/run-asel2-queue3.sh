#!/usr/bin/env bash
# 2026-11-09 A-SEL2 CARLA queue 3 (tooling outer_s 1500 = A-SEL2 addendum 9; product m56-v12), one own server at a time,
# guarded by asel2-watchdog.py.
#  0. F capability smoke;
#  1. ONE A/B (P5, new tooling version) per PREPARED batch-1 scene on revision asel2prep, dv1 + spectator:
#     Town12 C02-S1, L02-S1 (first A/B ended OUTER_TIMEOUT under outer 300), L05-S1, M06-S1;
#     Town13 C07-S1, L03-S1, L06-S1, M01-S1, M03-S1;  pairs under v12;
#  2. I/O batch (v12 + tilt); 3. C/L/M batch 2 (v12 + tilt + E6 + TF2, replacement rounds 1, 2b, 3, 4).
cd "$(dirname "$0")"
O=../../../outputs; V12=D:/AI/CARLA-Funny-Moments.worktrees/m56-v12; PY=../../../.venv-m56-native-v1/Scripts/python.exe
REV1=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_c0_partial_io_asel2prep_20261108T114946Z/c0-partial-v5-frozen-revision.json
LOG=$O/m56_asel2_q3_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
echo "Q0 F smoke $(date -u +%FT%TZ)"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_NO_RENDER=1 timeout 1200 $PY -I -X utf8 native-f-capability-smoke.py 2>&1 | grep -v "^INFO" | grep -a '"event"\|F_SMOKE_END\|Traceback\|Error'
echo "Q1 batch-1 A/B $(date -u +%FT%TZ)"
for spec in "Town12:M56-P-C02-S1,M56-P-L02-S1,M56-P-L05-S1,M56-P-M06-S1" "Town13:M56-P-C07-S1,M56-P-L03-S1,M56-P-L06-S1,M56-P-M01-S1,M56-P-M03-S1"; do
  t=${spec%%:*}; N=${spec#*:}
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  M56_NO_RENDER=1 M56_RECIPE=v6 M56_SPECTATOR=1 M56_DRIVABLE=dv1 M56_CODE=$V12 $PY -I -X utf8 native-v2-ab.py $REV1 $t $N > $LOG/ab-$t.log 2>&1
  D=$(done_path $LOG/ab-$t.log)
  for s in $(echo $N | tr ',' ' '); do
    [ -d "$D/$s/run" ] || { echo "$s: no run dir"; continue; }
    M56_CODE=$V12 $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v12.log 2>&1
    echo "$s v12: $(grep -o '"scene": "'$s'", "status": "[A-Z_]*"' $LOG/pair-v12.log | tail -1)"
  done
done
echo "Q2 I/O $(date -u +%FT%TZ)"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_CODE=$V12 M56_SPAWN_TILT=1 bash run-asel2-io.sh "Town12:M56-P-I01-S1,M56-P-I05-S1,M56-P-I06,M56-P-O05-S1,M56-P-O06,M56-P-O07-S1 Town13:M56-P-I07-S1,M56-P-I08,M56-P-O04-S1,M56-P-I02-S2,M56-P-O08-S2"
echo "Q3 C/L/M batch 2 $(date -u +%FT%TZ)"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
M56_CODE=$V12 M56_SPAWN_TILT=1 M56_ASEL2_REPLACE=$R/m56_fill_v4_replace1_20261108.json,$R/m56_fill_v4_replace2b_20261108.json,$R/m56_fill_v4_replace3_20261108.json,$R/m56_fill_v4_replace4_20261109.json \
  bash run-asel2-cl2.sh "Town12:M56-P-C04-S2,M56-P-M05-S1,M56-P-L08-S1,M56-P-M07-S2,M56-P-M08-S2 Town13:M56-P-C03-S2,M56-P-C06-S1,M56-P-M02-S1,M56-P-L07-S2,M56-P-M04-S2"
echo "QUEUE3_DONE $(date -u +%FT%TZ)"
