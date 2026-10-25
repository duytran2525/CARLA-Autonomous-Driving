#!/usr/bin/env bash
# Erratum 5 (APPROVED by Duy 2026-10-25, option 1): consumer without the face-corridor conjunct at entry crossings and
# EGO STOP_CONFIRMED, code on feat/m56-e5 (M56_CODE). P5: the single rerun of every scene PROVEN affected (events that
# appear only under the new consumer on its sealed episodes: outputs/m56_e5_rerun_list.json, frozen before this runs).
# Revision = the latest C0 partial (v5j). Started by hand after the erratum-4 chain ended. no_rendering_mode + deferred W05 (both with
# the erratum-5 code: M56_CODE is inherited). One own server at a time.
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_DEFER_W05=1 M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-e5
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_v5_e5_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe
LIST=$A/m56_e5_rerun_list.json
echo "code $(git -C $M56_CODE log -1 --format=%h) list sha256 $(sha256sum $LIST | cut -c1-64)"
while tasklist | grep -qi CarlaUE4; do sleep 30; done
REVF=$(ls -d $A/m56_c0_partial_v5j_*/c0-partial-v5-frozen-revision.json | tail -1)
echo "revision $REVF"
for t in Town04 Town05 Town06 Town07; do
  N=$(python -I -c "import json,sys;print(','.join(json.load(open(sys.argv[1]))['by_town'].get(sys.argv[2],[])))" $LIST $t)
  [ -z "$N" ] && continue
  while tasklist | grep -qi CarlaUE4; do sleep 30; done
  $PY -I -X utf8 native-v2-ab.py $REVF $t $N > $LOG/ab-$t.log 2>&1
  grep -v "^INFO" $LOG/ab-$t.log | grep -E '"event": "(FIXTURE|ADMISSION|AB_DEFERRED|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-300
done
echo "erratum-5 chain finished $(date -u) logs=$LOG"
