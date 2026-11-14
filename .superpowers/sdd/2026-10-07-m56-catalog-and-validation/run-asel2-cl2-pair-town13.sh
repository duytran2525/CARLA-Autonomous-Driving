#!/usr/bin/env bash
# 13/11: pair the 4 Town13 Q3 scenes whose A/B finished before the 06:30 safe stop (same 3 pair passes as run-asel2-cl2.sh).
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
PY=../../../.venv-m56-native-v1/Scripts/python.exe
D=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_v2_ab_Town13_20261112T224214Z
LOG=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_asel2_cl2p_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
echo "pairing Town13 Q3 $(date -u +%FT%TZ)"
for s in M56-P-C03-S2 M56-P-C06-S1 M56-P-L07-S2 M56-P-M02-S1; do
  [ -d "$D/$s/run" ] || { echo "$s no run dir"; continue; }
  $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v10.log 2>&1
  M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v10 $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v10abs.log 2>&1
  M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v6 $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v6.log 2>&1
  echo "$s v10: $(grep -o '"scene": "'$s'", "status": "[A-Z_]*"' $LOG/pair-v10.log | tail -1)  v6: $(grep -o '"scene": "'$s'", "status": "[A-Z_]*"' $LOG/pair-v6.log | tail -1)"
done
echo "CL2P_DONE logs=$LOG"