#!/usr/bin/env bash
# 2026-11-15 (Claude quyet duoi uy quyen, user request "sua tat ca nhung canh khac"): replacement 7 (B3 + addendum G route
# gate, lap 1 ROUTES_OK) O04-S1 (prepare RUNIN_NOT_STRAIGHT, no A/B) -> O04-S2 Town13 road 101. Same I/O batch as Q2
# (run-asel2-io.sh: prepare -> revision -> compile + self-check -> ONE A/B (P5) -> pair v12/v10), product m56-v12 + tilt,
# replacement rounds 1..7. Starts after the replacement 6 batch has ended and while no HOLD file exists.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
until grep -q REPL6_END $R/m56_asel2_repl6b.stdout.txt 2>/dev/null; do sleep 60; done
while [ -f $R/m56_asel2_HOLD ]; do sleep 60; done
echo "start $(date -u +%FT%TZ)"
M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v12 M56_SPAWN_TILT=1 \
M56_ASEL2_REPLACE=$R/m56_fill_v4_replace1_20261108.json,$R/m56_fill_v4_replace2b_20261108.json,$R/m56_fill_v4_replace3_20261108.json,$R/m56_fill_v4_replace4_20261109.json,$R/m56_fill_v4_replace5_20261111.json,$R/m56_fill_v4_replace6_20261115.json,$R/m56_fill_v4_replace7_1_20261115.json \
bash run-asel2-io.sh "Town13:M56-P-O04-S2"
echo "REPL7_END $(date -u +%FT%TZ)"
