#!/usr/bin/env bash
# Resume after the 2026-11-10 safe stop (docs/m56/M56_ASEL2_BATCH_LOG_20261108.md, "Dừng an toàn 10/11"). Nothing of
# queue 3b had reached a FIXTURE or an episode, so every P5 quota is unused and the queue restarts from its first step.
# Launches, detached and chained by their stdout markers (labels never reused; start-detached refuses an existing label):
#   watchdog -> queue 3b (QUEUE3B_DONE) -> F03 grade probe (F03_ALL_DONE) -> F01 chain (F01_END) -> F02 chain (F02_END)
# usage (once): bash run-asel2-resume-20261110.sh r1
cd "$(dirname "$0")"
S=${1:?usage: bash run-asel2-resume-20261110.sh SUFFIX  (e.g. r1)}; B=D:/Git/usr/bin/bash.exe
tasklist | grep -qi CarlaUE4 && { echo "REFUSED: a CarlaUE4 is running (port 2610 must be free)"; exit 4; }
python -I start-detached.py m56_asel2_watchdog_$S python -I -X utf8 asel2-watchdog.py 300 1800 1800 || exit 4
python -I start-detached.py m56_asel2_queue_$S $B run-asel2-queue3b.sh || exit 4
M56_WAIT_QUEUE=m56_asel2_queue_$S python -I start-detached.py m56_f03_probe_$S $B run-f03-probe-after-q3.sh || exit 4
M56_WAIT_F03=m56_f03_probe_$S python -I start-detached.py m56_f01_chain_$S $B run-f01-after-f03.sh || exit 4
M56_WAIT_F01=m56_f01_chain_$S python -I start-detached.py m56_f02_chain_$S $B run-f02-after-f01.sh || exit 4
echo "RESUMED $S: outputs/m56_asel2_queue_$S.stdout.txt, m56_f03_probe_$S, m56_f01_chain_$S, m56_f02_chain_$S"
