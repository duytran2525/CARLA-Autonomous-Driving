#!/usr/bin/env bash
# 2026-11-22 M-group dv1 feasibility check (Duy [chat] 22/11 "Kiểm khả thi M trước"; report-only, no A/B, no P5).
# Waits until the addendum Z O queue has ended (OZ_END), then per town: CARLA down + room() commit gate, then
# native-m-dv1-feasibility.py (own CARLA 2610). Refuses to run when the STOP file exists.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
PY=../../../.venv-m56-native-v1/Scripts/python.exe
Q=$R/m56_oz_queue_20261122b.stdout.txt
until grep -q '^OZ_END' $Q 2>/dev/null; do sleep 60; done
echo "start $(date -u +%FT%TZ) after $(grep '^OZ_END' $Q)"
room() { while tasklist | grep -qi CarlaUE4; do sleep 15; done; python -I asel2-cguard.py --wait-commit-gb ${M56_COMMIT_START_GB:-32} | tail -1; }
for t in Town05 Town12 Town13; do
  [ -f $R/m56_asel2_STOP ] && { echo "STOP file: end"; break; }
  room
  timeout ${M56_FEAS_TIMEOUT_S:-14400} $PY -I -X utf8 native-m-dv1-feasibility.py $t --validate 2 > $R/m56_m_dv1_feasibility_$t.log 2>&1
  echo "$t exit $? $(grep TOWN_DONE $R/m56_m_dv1_feasibility_$t.log | tail -1)"
done
echo "FEAS_END $(date -u +%FT%TZ)"
