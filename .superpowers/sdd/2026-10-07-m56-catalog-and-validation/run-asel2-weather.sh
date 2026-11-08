#!/usr/bin/env bash
# 2026-11-08 A-SEL2: stock weather/light + OpenDRIVE hash of the new towns, one fresh own server per town.
cd "$(dirname "$0")"
export M56_NO_RENDER=1
for t in Town01 Town02 Town10HD Town11 Town12 Town13 Town15; do
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  timeout 1500 ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-weather-query.py $t 2>&1 | grep -v "^INFO" | tail -3
done
echo WEATHER_ALL_DONE
