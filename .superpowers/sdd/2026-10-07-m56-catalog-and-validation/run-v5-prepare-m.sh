#!/usr/bin/env bash
# v5: PREPARE (no A/B) M02-M08 from C0 partial v5 with the v5 product code of m56-v5-dev (8fa9632, byte-identical to the
# post-merge product). One own server (2610) at a time; never while another CarlaUE4 runs; stops before a town if
# full suite 9 has finished, so the pending single v3.1 A/B gets the server.
cd "$(dirname "$0")"
S='C:/Users/ADMIN/AppData/Local/Temp/claude/D--AI-CARLA-Funny-Moments-worktrees/c504d458-feeb-4c2b-a56c-62ae1fb312ee/scratchpad'
export M56_CODE='D:/AI/CARLA-Funny-Moments.worktrees/m56-v5-dev'
export M56_REV='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_c0_partial_v5_20261024T173011Z/c0-partial-v5-frozen-revision.json'
[ "$(git -C "$M56_CODE" log -1 --format=%h)" = 8fa9632 ] && [ -z "$(git -C "$M56_CODE" status --short)" ] || { echo "NOT RUN: code not at clean 8fa9632"; exit 2; }
for spec in "Town04 M56-P-M02,M56-P-M04" "Town05 M56-P-M03,M56-P-M06,M56-P-M07" "Town06 M56-P-M05" "Town07 M56-P-M08"; do
  set -- $spec
  [ -f m56-full-suite-9-20261024.run.json ] && { echo "STOPPED before $1: suite 9 finished (v3.1 A/B goes first)"; exit 0; }
  while tasklist | grep -qi CarlaUE4; do sleep 30; done
  ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-v2-prepare.py $1 $2 > "$S/v5prepM-$1.log" 2>&1
  grep -v "^INFO" "$S/v5prepM-$1.log" | grep -E '"event": "(SCENE|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-500
done
echo "M preparation finished $(date -u)"
