#!/usr/bin/env bash
# 2026-11-15 evening: io-i-v1.2 + addendum H, I01-S1 only (user [chat] "Chay ngay"; I02-S2 held). Product m56-v12 + spawn tilt.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
while [ -f $R/m56_asel2_HOLD ]; do sleep 60; done
echo "start $(date -u +%FT%TZ)"
M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v12 M56_SPAWN_TILT=1 \
M56_ASEL2_REPLACE=$R/m56_fill_v4_replace1_20261108.json,$R/m56_fill_v4_replace2b_20261108.json,$R/m56_fill_v4_replace3_20261108.json,$R/m56_fill_v4_replace4_20261109.json,$R/m56_fill_v4_replace5_20261111.json,$R/m56_fill_v4_replace6_20261115.json,$R/m56_fill_v4_replace7_1_20261115.json,$R/m56_fill_v4_replace8_1_20261115.json \
bash run-asel2-io-i12.sh "Town12:M56-P-I01-S1"
echo "I12_END $(date -u +%FT%TZ)"
