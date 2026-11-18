#!/usr/bin/env bash
# 2026-11-18 F03 capability probe v2 (observe-only, no scene, no A/B): Town12 and Town11 (r7 grade sites), room wait first.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
PY=../../../.venv-m56-native-v1/Scripts/python.exe
room() { while tasklist | grep -qi CarlaUE4; do sleep 15; done; python -I asel2-cguard.py --wait-commit-gb ${M56_COMMIT_START_GB:-25} | tail -1; }
for T in Town12 Town11; do room; $PY -I -X utf8 native-f03-rollback-probe.py $T 3; done
echo F03_ROLLBACK_ALL_DONE
