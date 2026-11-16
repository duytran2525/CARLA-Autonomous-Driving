#!/usr/bin/env bash
# 2026-11-16 resume of the O queue + I01-S1 prepare after the cguard commit stop (03:31Z, inside O05-S1 prepare: no
# fixture, no P5). usage (once, from this dir): D:/Git/usr/bin/bash.exe run-asel2-resume-20261116.sh SUFFIX  (e.g. r16b)
# Renames (never deletes) a stale STOP / SAFE_TO_SHUTDOWN file, starts stopper (STOP file only) + watchdog + cguard
# backstop, then the O queue (label m56_asel2_v15o_SUFFIX) and the I01-S1 prepare (waits for that queue).
# Every CARLA start inside io-v16 / i13 first waits for commit headroom >= M56_COMMIT_START_GB (default 25 GB =
# Town12 CARLA ~14 + A/B harness <= ~7 + 4 margin), so the queue may sit in ROOM_WAIT until apps are closed.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
S=${1:?suffix}; O=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs; U=$(date -u +%Y%m%dT%H%M%SZ)
for f in m56_asel2_STOP M56_SAFE_TO_SHUTDOWN.txt; do [ -e $O/$f ] && mv $O/$f $O/$f.consumed_$U; done
python -I start-detached.py m56_asel2_stopper_$S python -I -X utf8 asel2-stopper.py --since $(date -u +%FT%TZ) || exit 4
python -I start-detached.py m56_asel2_watchdog_$S python -I -X utf8 asel2-watchdog.py 300 1800 1800 || exit 4
python -I start-detached.py m56_cguard_$S python -I -X utf8 asel2-cguard.py --min-gb 10 --min-commit-gb 4 || exit 4
python -I start-detached.py m56_asel2_v15o_$S D:/Git/usr/bin/bash.exe run-asel2-v15o-queue.sh || exit 4
M56_OQ=m56_asel2_v15o_$S python -I start-detached.py m56_asel2_i13prep_$S D:/Git/usr/bin/bash.exe run-asel2-i13-prep.sh || exit 4
echo "RESUMED $S $U"
