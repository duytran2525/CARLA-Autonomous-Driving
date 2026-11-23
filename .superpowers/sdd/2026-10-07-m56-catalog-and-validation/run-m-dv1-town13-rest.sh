#!/usr/bin/env bash
# 2026-11-23 M feasibility, the 73 unchecked Town13 sites (Duy [chat] 23/11 "Kiểm nốt 73 site Town13"; report-only, no
# spawn, no A/B, no P5). The 23/11 r23c run lost ~1.5 GB of commit per minute across sites and reached 0.08 GB, so this
# runs chunks of ${M56_FEAS_CHUNK:-8} sites, one fresh CARLA per chunk, sites in 500 m spatial order (--skip-done resumes).
# Before every chunk: STOP file check, CARLA down, room() commit gate. Ends when a chunk reports sites 0, or after two
# failed chunks in a row.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
PY=../../../.venv-m56-native-v1/Scripts/python.exe
room() { while tasklist | grep -qi CarlaUE4; do sleep 15; done; python -I asel2-cguard.py --wait-commit-gb ${M56_COMMIT_START_GB:-32} | tail -1; }
echo "start $(date -u +%FT%TZ)"
# 23/11: the stopper's WMI process listing timed out after the 03:08Z memory event, so this runner kills CARLA itself when
# the cguard writes the STOP file (tasklist/taskkill, no WMI). own_server refuses to start beside another CarlaUE4, so any
# CarlaUE4 running during this runner is ours (port 2610).
( while [ ! -f $R/m56_asel2_STOP ]; do sleep 10; done
  tasklist | grep -qi CarlaUE4 && { taskkill //IM CarlaUE4-Win64-Shipping.exe //F; taskkill //IM CarlaUE4.exe //F; echo "STOP_WATCH killed CARLA $(date -u +%FT%TZ)"; } ) &
W=$!
trap 'kill $W 2>/dev/null' EXIT
fails=0
for n in $(seq 1 20); do
  [ -f $R/m56_asel2_STOP ] && { echo "STOP file: end"; break; }
  room
  L=$R/m56_m_dv1_feasibility_Town13_rest_$n.log
  timeout ${M56_FEAS_TIMEOUT_S:-3600} $PY -I -X utf8 native-m-dv1-feasibility.py Town13 --skip-done --min-lane 0 --limit ${M56_FEAS_CHUNK:-8} > $L 2>&1
  rc=$?; d=$(grep '"TOWN_DONE"' $L | tail -1)
  echo "chunk $n exit $rc $d"
  grep -q '"sites": 0' <<<"$d" && break
  if [ $rc -ne 0 ]; then fails=$((fails+1)); [ $fails -ge 2 ] && { echo "two failed chunks: end"; break; }; else fails=0; fi
done
echo "FEAS13_END $(date -u +%FT%TZ)"
