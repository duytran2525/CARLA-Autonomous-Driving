#!/usr/bin/env bash
# 2026-11-23 resume after the 22/11 14:35Z cguard commit stop (inside the O08-S3 prepare, Town13 load: no probe, no A/B, P5
# unused). Duy [chat] 22/11: "Tôi đóng app rồi chạy lại" (one more prepare for O08-S3 only, CARLA start gate 32 GB, then the
# M dv1 feasibility check). usage (once, from this dir): D:/Git/usr/bin/bash.exe run-asel2-resume-20261123.sh SUFFIX
# Renames (never deletes) the STOP / SAFE_TO_SHUTDOWN files, starts stopper (STOP file only) + watchdog (cguard 39648 still
# runs), then the O08-S3 queue (label m56_oz_queue_SUFFIX) and the feasibility runner that waits for its OZ_END.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
S=${1:?suffix}; O=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs; U=$(date -u +%Y%m%dT%H%M%SZ)
for f in m56_asel2_STOP M56_SAFE_TO_SHUTDOWN.txt; do [ -e $O/$f ] && mv $O/$f $O/$f.consumed_$U; done
python -I start-detached.py m56_asel2_stopper_$S python -I -X utf8 asel2-stopper.py --since $(date -u +%FT%TZ) || exit 4
python -I start-detached.py m56_asel2_watchdog_$S python -I -X utf8 asel2-watchdog.py 300 1800 1800 || exit 4
python -I start-detached.py m56_oz_queue_$S D:/Git/bin/bash.exe run-asel2-oz-queue-o08.sh || exit 4
M56_FEAS_AFTER=m56_oz_queue_$S M56_FEAS_MIN_LANE=0 python -I start-detached.py m56_m_dv1_feas_$S D:/Git/bin/bash.exe run-m-dv1-feasibility.sh || exit 4
echo "RESUMED $S $U"
