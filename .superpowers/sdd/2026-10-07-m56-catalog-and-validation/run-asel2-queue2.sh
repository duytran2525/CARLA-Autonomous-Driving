#!/usr/bin/env bash
# 2026-11-09 A-SEL2 CARLA queue 2 (after the safe stop of 08/11), one own server at a time, guarded by asel2-watchdog.py.
# Starts after the offline v12 re-evaluation of batch 1 (memory). Product m56-v12 (A-SEL2 addenda 6 + 8).
#  0. F capability smoke;
#  1. the PREPARED batch-1 scenes without an A/B (P5: one each) on revision asel2prep, dv1, spectator:
#     Town12 L05-S1, M06-S1; Town13 C07-S1, L03-S1, L06-S1, M01-S1, M03-S1 (M05-S1 is re-prepared in step 3);
#  2. I/O batch (v12 + tilt); 3. C/L/M batch 2 (v12 + tilt + E6 + TF2), incl. C03-S2/C04-S2 (replacement 4, B5).
cd "$(dirname "$0")"
O=../../../outputs; V12=D:/AI/CARLA-Funny-Moments.worktrees/m56-v12
REV1=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_c0_partial_io_asel2prep_20261108T114946Z/c0-partial-v5-frozen-revision.json
until grep -q PAIR_B1_V12_END $O/m56_asel2_pair_b1_v12.stdout.txt 2>/dev/null; do sleep 60; done
echo "Q0 F smoke $(date -u +%FT%TZ)"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_NO_RENDER=1 timeout 1200 ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-f-capability-smoke.py 2>&1 | grep -v "^INFO" | grep -a '"event"\|F_SMOKE_END\|Traceback\|Error'
echo "Q1 batch-1 remaining A/B $(date -u +%FT%TZ)"
M56_CODE=$V12 bash run-asel2-ab-resume.sh $REV1 "Town12:M56-P-L05-S1,M56-P-M06-S1 Town13:M56-P-C07-S1,M56-P-L03-S1,M56-P-L06-S1,M56-P-M01-S1,M56-P-M03-S1"
echo "Q2 I/O $(date -u +%FT%TZ)"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_CODE=$V12 M56_SPAWN_TILT=1 bash run-asel2-io.sh "Town12:M56-P-I01-S1,M56-P-I05-S1,M56-P-I06,M56-P-O05-S1,M56-P-O06,M56-P-O07-S1 Town13:M56-P-I07-S1,M56-P-I08,M56-P-O04-S1,M56-P-I02-S2,M56-P-O08-S2"
echo "Q3 C/L/M batch 2 $(date -u +%FT%TZ)"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_CODE=$V12 M56_SPAWN_TILT=1 M56_ASEL2_REPLACE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_fill_v4_replace1_20261108.json,D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_fill_v4_replace2b_20261108.json,D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_fill_v4_replace3_20261108.json,D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_fill_v4_replace4_20261109.json \
  bash run-asel2-cl2.sh "Town12:M56-P-C04-S2,M56-P-M05-S1,M56-P-L08-S1,M56-P-M07-S2,M56-P-M08-S2 Town13:M56-P-C03-S2,M56-P-C06-S1,M56-P-M02-S1,M56-P-L07-S2,M56-P-M04-S2"
echo "QUEUE2_DONE $(date -u +%FT%TZ)"
