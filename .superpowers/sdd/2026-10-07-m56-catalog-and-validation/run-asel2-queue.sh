#!/usr/bin/env bash
# 2026-11-08 A-SEL2 CARLA queue (one own server at a time), started after the C/L/M batch 1 (label m56_asel2_cl_t1213):
#  1. I/O batch under consumer v11 + tilted spawns (A-SEL2 addendum 6): the 11 fill-v4 I/O picks (v4a + replacement 1);
#  2. C/L/M batch 2 under v11 + tilt + E6 + TF2: re-preparation of C04-S1, M05-S1, L08-S1 (Town12), C06-S1, M02-S1 (Town13)
#     on the new version (P5: one A/B per version), and the L07 successor of replacement 2b;
#  0. F capability smoke first (10 min; unblocks the F design). The watchdog (asel2-watchdog.py) checkpoints and guards every step.
cd "$(dirname "$0")"
O=../../../outputs; V11=D:/AI/CARLA-Funny-Moments.worktrees/m56-v11
until grep -q ASEL2_CL_END $O/m56_asel2_cl_t1213.stdout.txt 2>/dev/null; do sleep 60; done
echo "Q0 F smoke start $(date -u +%FT%TZ)"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_NO_RENDER=1 timeout 1200 ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-f-capability-smoke.py 2>&1 | grep -v "^INFO" | grep -a '"event"\|F_SMOKE_END\|Traceback\|Error'
echo "Q1 I/O start $(date -u +%FT%TZ)"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_CODE=$V11 M56_SPAWN_TILT=1 bash run-asel2-io.sh "Town12:M56-P-I01-S1,M56-P-I05-S1,M56-P-I06,M56-P-O05-S1,M56-P-O06,M56-P-O07-S1 Town13:M56-P-I07-S1,M56-P-I08,M56-P-O04-S1,M56-P-I02-S2,M56-P-O08-S2"
echo "Q2 C/L/M batch 2 start $(date -u +%FT%TZ)"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_CODE=$V11 M56_SPAWN_TILT=1 M56_ASEL2_REPLACE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_fill_v4_replace1_20261108.json,D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_fill_v4_replace2b_20261108.json \
  bash run-asel2-cl2.sh "Town12:M56-P-C04-S1,M56-P-M05-S1,M56-P-L08-S1 Town13:M56-P-C06-S1,M56-P-M02-S1,M56-P-L07-S2"
echo "QUEUE_DONE $(date -u +%FT%TZ)"
