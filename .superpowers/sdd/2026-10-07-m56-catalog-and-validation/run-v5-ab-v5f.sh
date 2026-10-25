#!/usr/bin/env bash
# Single v5 A/B (P5) on C0 partial v5f (outputs/m56_c0_partial_v5f_*, sha256 8a2b0e2e...) with the BODY_FIT drivable-radius
# fix (0b9cd59). C01/C02: Duy [chat] 2026-10-25 "chuẩn bị lại C01/C02 theo v5 và chạy A/B đúng một lần". C03, L04,
# L05, L06, L07: blocked at compile before any episode (harness defect), so this is their first A/B. L02: never ran.
cd "$(dirname "$0")"
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_v5_ab_v5f_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe
REVF=$(ls -d $A/m56_c0_partial_v5f_*/c0-partial-v5-frozen-revision.json | tail -1)
echo "revision $REVF code $(git -C ../../.. log -1 --format=%h)"
for spec in "Town04 M56-P-C01,M56-P-C02,M56-P-C03,M56-P-L02" "Town05 M56-P-L04,M56-P-L05" "Town07 M56-P-L06,M56-P-L07"; do
  set -- $spec; while tasklist | grep -qi CarlaUE4; do sleep 30; done
  $PY -I -X utf8 native-v2-ab.py $REVF $1 $2 > $LOG/ab-$1.log 2>&1
  grep -v "^INFO" $LOG/ab-$1.log | grep -E '"event": "(FIXTURE|ADMISSION|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
done
echo "v5f A/B finished $(date -u) logs=$LOG"
