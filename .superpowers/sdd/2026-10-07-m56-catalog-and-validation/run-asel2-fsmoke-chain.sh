#!/usr/bin/env bash
# 2026-11-08: F capability smoke after the A-SEL2 I/O chain (one own server at a time).
cd "$(dirname "$0")"
until grep -q CHAIN_DONE ../../../outputs/m56_asel2_io_chain.stdout.txt 2>/dev/null; do sleep 60; done
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_NO_RENDER=1 timeout 1200 ../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-f-capability-smoke.py 2>&1 | grep -v "^INFO" | grep -a '"event"\|F_SMOKE_END\|Traceback\|Error'
echo FSMOKE_DONE
