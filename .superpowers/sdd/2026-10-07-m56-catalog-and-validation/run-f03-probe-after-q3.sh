#!/usr/bin/env bash
cd "$(dirname "$0")"
until grep -q QUEUE3_DONE ../../../outputs/m56_asel2_queue_d.stdout.txt 2>/dev/null; do sleep 120; done
for t in Town11 Town12; do
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  M56_NO_RENDER=1 M56_SPECTATOR=1 timeout 1800 ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-f03-grade-probe.py $t 3 2>&1 | grep -a '"event"\|END\|Traceback\|Error' | grep -v SERVER
done
echo F03_ALL_DONE
