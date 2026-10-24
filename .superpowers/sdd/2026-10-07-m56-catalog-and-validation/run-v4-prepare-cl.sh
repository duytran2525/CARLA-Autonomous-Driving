#!/usr/bin/env bash
# v4 (ccea1cc) preparation of the remaining C/L scenes, one own server at a time (2610).
cd "$(dirname "$0")"
S='C:/Users/ADMIN/AppData/Local/Temp/claude/D--AI-CARLA-Funny-Moments-worktrees/c504d458-feeb-4c2b-a56c-62ae1fb312ee/scratchpad'
for spec in "Town04 M56-P-L01" "Town05 M56-P-C04,M56-P-C05,M56-P-C06,M56-P-L03,M56-P-L04,M56-P-L05" "Town06 M56-P-C07,M56-P-C08" "Town07 M56-P-L06,M56-P-L07,M56-P-L08"; do
  set -- $spec
  while tasklist | grep -qi CarlaUE4; do sleep 30; done
  ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-v2-prepare.py $1 $2 > "$S/v4prep-$1.log" 2>&1
  grep -v "^INFO" "$S/v4prep-$1.log" | grep -E '"event": "(SCENE|SCENE_ERROR)"|^DONE|^Traceback' | cut -c1-320
done
