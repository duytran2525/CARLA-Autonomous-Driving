#!/usr/bin/env bash
# 2026-11-15 (Claude quyet duoi uy quyen; recipes approved by the session user [chat] 15/11): O scenes under io-v1.5 + io-v1.6.
#   Town12: O05-S1, O06 (re-run, new version: P5 one A/B), O07-S2 (B3 successor, replacement 8, O07-S1 WINDOW_TOO_SHORT);
#   Town13: O08-S2 (no A/B spent, io-v1.5 long probe).
# I scenes are NOT here: io-i-v1.2 G1/G3 (probe 3) and the v15 A-resume guard are not built yet.
# Starts after the replacement 7 batch (REPL7_END) and while no HOLD file exists. Product m56-v12 + spawn tilt.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
until grep -q REPL7_END $R/m56_asel2_repl7.stdout.txt 2>/dev/null; do sleep 60; done
while [ -f $R/m56_asel2_HOLD ]; do sleep 60; done
echo "start $(date -u +%FT%TZ)"
M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v12 M56_SPAWN_TILT=1 \
M56_ASEL2_REPLACE=$R/m56_fill_v4_replace1_20261108.json,$R/m56_fill_v4_replace2b_20261108.json,$R/m56_fill_v4_replace3_20261108.json,$R/m56_fill_v4_replace4_20261109.json,$R/m56_fill_v4_replace5_20261111.json,$R/m56_fill_v4_replace6_20261115.json,$R/m56_fill_v4_replace7_1_20261115.json,$R/m56_fill_v4_replace8_1_20261115.json \
bash run-asel2-io-v16.sh "Town12:M56-P-O05-S1,M56-P-O06,M56-P-O07-S2 Town13:M56-P-O08-S2"
echo "IO16_END $(date -u +%FT%TZ)"
