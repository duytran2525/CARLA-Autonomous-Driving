#!/usr/bin/env bash
# 2026-11-09: profile one PREPARATION (no A/B) on Town12 with py-spy to find the per-tick wall cost of the runner on large
# maps. Scene L08-S1 (needs re-preparation under E6 anyway), flags of batch 2, product m56-v12.
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_SPECTATOR=1 M56_SPAWN_TILT=1 M56_SIG5=1 M56_E6=1 M56_TF2=1 M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v12
O=../../../outputs; R0=$O/m56_c0_partial_io_asel2base_20261108T083411Z/c0-partial-v5-frozen-revision.json
PY=../../../.venv-m56-native-v1/Scripts/python.exe
M56_REV=$R0 $PY -I -X utf8 native-v2-prepare.py Town12 M56-P-L08-S1 > $O/m56_asel2_profile_prep.log 2>&1 &
sleep 420
PID=$(powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -like '*native-v2-prepare.py Town12 M56-P-L08-S1*' -and \$_.Name -eq 'python.exe' -and \$_.CommandLine -like '*Python312*' }).ProcessId" | tr -d '\r' | head -1)
echo "profiling pid $PID"
/c/Users/ADMIN/.local/bin/py-spy record --pid $PID --duration 120 --format raw --output $O/m56_asel2_profile_prep.raw.txt --nonblocking 2>&1 | tail -2
wait
echo PROFILE_END
