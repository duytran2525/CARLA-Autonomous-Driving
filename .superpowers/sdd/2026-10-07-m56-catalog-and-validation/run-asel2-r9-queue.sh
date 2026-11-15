#!/usr/bin/env bash
# 2026-11-15 night (addendum K, replacement 9 final m56_fill_v4_replace9_c4): after the v15 queue (V15Q_END) and only if it
# actually ran (suite 12 CHAIN_PASSED): I05-S2, I06-S2, I07-S2, I08-S2 (io-i-v1.2 + H + J) and O04-S3, O08-S3 (io-v1.5/1.6).
# Product m56-v15 + spawn tilt. One A/B per scene (P5).
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
until grep -q V15Q_END $R/m56_asel2_v15q.stdout.txt 2>/dev/null; do sleep 60; done
grep -q 'NOT RUN' $R/m56_asel2_v15q.stdout.txt && { echo "NOT RUN: v15 queue did not run (suite 12)"; echo R9Q_END; exit 4; }
while [ -f $R/m56_asel2_HOLD ]; do sleep 60; done
echo "start $(date -u +%FT%TZ)"
export M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v15 M56_SPAWN_TILT=1 \
M56_ASEL2_REPLACE=$R/m56_fill_v4_replace1_20261108.json,$R/m56_fill_v4_replace2b_20261108.json,$R/m56_fill_v4_replace3_20261108.json,$R/m56_fill_v4_replace4_20261109.json,$R/m56_fill_v4_replace5_20261111.json,$R/m56_fill_v4_replace6_20261115.json,$R/m56_fill_v4_replace7_1_20261115.json,$R/m56_fill_v4_replace8_1_20261115.json,$R/m56_fill_v4_replace9_c4_20261115.json
bash run-asel2-io-i12j.sh "Town12:M56-P-I07-S2,M56-P-I08-S2 Town13:M56-P-I05-S2,M56-P-I06-S2"
bash run-asel2-io-v16.sh "Town13:M56-P-O04-S3,M56-P-O08-S3"
echo "R9Q_END $(date -u +%FT%TZ)"
