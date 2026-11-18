#!/usr/bin/env bash
# 2026-11-18 r18f: F03 advisor check 2 (observe-only): Town12 axis-aligned in-range sites 1062/1085, neutral release + brake 0.3.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
PY=../../../.venv-m56-native-v1/Scripts/python.exe
export M56_NO_RENDER=1 M56_SPECTATOR=1
while tasklist | grep -qi CarlaUE4; do sleep 15; done; python -I asel2-cguard.py --wait-commit-gb ${M56_COMMIT_START_GB:-25} | tail -1
$PY -I -X utf8 native-f03-rollback-probe.py Town12 3 --brake --roads=1085
echo F03_BRAKE_ALL_DONE