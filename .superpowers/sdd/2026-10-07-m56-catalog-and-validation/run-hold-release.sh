#!/usr/bin/env bash
# 2026-11-15: keep outputs/m56_asel2_HOLD (no CARLA) while the offline full suite runner (pid $1) is alive; then rename
# the HOLD file (no delete) so the queued native batches (repl6b, repl7) may start.
export PATH=/usr/bin:$PATH
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
while tasklist //FI "PID eq $1" | grep -q " $1 "; do sleep 60; done
mv $R/m56_asel2_HOLD $R/m56_asel2_HOLD.released_$(date -u +%Y%m%dT%H%M%SZ) && echo "HOLD_RELEASED $(date -u +%FT%TZ)"
