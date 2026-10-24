#!/usr/bin/env bash
# The single A/B (P5) of each PREPARED new M scene on C0 partial v5d (outputs/m56_c0_partial_v5d_20261024T185251Z,
# v5b: relative prepare paths; v5c: M destination before domain exit + 5 m; both harness defects before any episode), code m56-v5-dev 8fa9632. Stops before a town once full suite 9 has finished (v3.1 A/B first).
cd "$(dirname "$0")"
S='C:/Users/ADMIN/AppData/Local/Temp/claude/D--AI-CARLA-Funny-Moments-worktrees/c504d458-feeb-4c2b-a56c-62ae1fb312ee/scratchpad'
export M56_CODE='D:/AI/CARLA-Funny-Moments.worktrees/m56-v5-dev'
[ "$(git -C "$M56_CODE" log -1 --format=%h)" = 8fa9632 ] && [ -z "$(git -C "$M56_CODE" status --short)" ] || { echo "NOT RUN: code not at clean 8fa9632"; exit 2; }
REVF='../../../outputs/m56_c0_partial_v5d_20261024T185251Z/c0-partial-v5-frozen-revision.json'
for spec in "Town04 M56-P-M02" "Town05 M56-P-M03,M56-P-M06,M56-P-M07" "Town06 M56-P-M05" "Town07 M56-P-M08"; do
  set -- $spec
  [ -f m56-full-suite-9-20261024.run.json ] && { echo "STOPPED before $1: suite 9 finished (v3.1 A/B goes first)"; exit 0; }
  while tasklist | grep -qi CarlaUE4; do sleep 30; done
  ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-v2-ab.py "$REVF" $1 $2 > "$S/v5abM-$1.log" 2>&1
  grep -v "^INFO" "$S/v5abM-$1.log" | grep -E '"event": "(SCENES|AB|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-1500
done
echo "M A/B finished $(date -u)"
