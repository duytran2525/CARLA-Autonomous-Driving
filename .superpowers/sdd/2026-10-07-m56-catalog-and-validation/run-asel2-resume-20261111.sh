#!/usr/bin/env bash
# Resume after the 2026-11-11 safe stop (asel2-stopper.py record outputs/m56_asel2_stop_*.json). Queue 3c skips DONE / INFRA_INTERRUPTED Q1 scenes (asel2-q1-remaining.py).
# Unlike 10/11, Q1 A/Bs were consumed, so the queue must NOT restart from its first step: 3c computes Q1 from evidence.
# Launches, detached and chained by their stdout markers (labels never reused; start-detached refuses an existing label):
#   watchdog -> queue 3c (QUEUE3B_DONE) -> F03 grade probe (F03_ALL_DONE) -> F01 chain (F01_END) -> F02 chain (F02_END)
# usage (once): bash run-asel2-resume-20261111.sh r3
cd "$(dirname "$0")"
S=${1:?usage: bash run-asel2-resume-20261111.sh SUFFIX  (e.g. r3)}; B=D:/Git/usr/bin/bash.exe
tasklist | grep -qi CarlaUE4 && { echo "REFUSED: a CarlaUE4 is running (port 2610 must be free)"; exit 4; }
python -I start-detached.py m56_asel2_watchdog_$S python -I -X utf8 asel2-watchdog.py 300 1800 1800 || exit 4
python -I start-detached.py m56_asel2_queue_$S $B run-asel2-queue3c.sh || exit 4
M56_WAIT_QUEUE=m56_asel2_queue_$S python -I start-detached.py m56_f03_probe_$S $B run-f03-probe-after-q3.sh || exit 4
M56_WAIT_F03=m56_f03_probe_$S python -I start-detached.py m56_f01_chain_$S $B run-f01-after-f03.sh || exit 4
M56_WAIT_F01=m56_f01_chain_$S python -I start-detached.py m56_f02_chain_$S $B run-f02-after-f01.sh || exit 4
echo "RESUMED $S: outputs/m56_asel2_queue_$S.stdout.txt, m56_f03_probe_$S, m56_f01_chain_$S, m56_f02_chain_$S"
