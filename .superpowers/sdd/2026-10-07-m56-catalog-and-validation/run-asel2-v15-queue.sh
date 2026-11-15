#!/usr/bin/env bash
# 2026-11-15 night (addendum J + consumer v15 prereg): after full suite 12 (v15 bytes in feat/m56-v1) ends CHAIN_PASSED:
#   1. I01-S1 under io-i-v1.2 + addendum H + J (run-asel2-io-i12j.sh);
#   2. O05-S1, O06, O07-S2 under io-v1.5/1.6 (run-asel2-io-v16.sh). P5 unspent for all four. Product m56-v15 + spawn tilt.
# Any other suite outcome: nothing runs.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
S=m56-full-suite-12-20261115.run.json
until [ -f $S ] && grep -q '"end_utc"' $S; do sleep 60; done
grep -q '"verdict_chain": "CHAIN_PASSED"' $S || { echo "NOT RUN: suite 12 not CHAIN_PASSED"; grep -E '"(status|summary)"' $S; echo V15Q_END; exit 4; }
while [ -f $R/m56_asel2_HOLD ]; do sleep 60; done
echo "start $(date -u +%FT%TZ)"
export M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v15 M56_SPAWN_TILT=1 \
M56_ASEL2_REPLACE=$R/m56_fill_v4_replace1_20261108.json,$R/m56_fill_v4_replace2b_20261108.json,$R/m56_fill_v4_replace3_20261108.json,$R/m56_fill_v4_replace4_20261109.json,$R/m56_fill_v4_replace5_20261111.json,$R/m56_fill_v4_replace6_20261115.json,$R/m56_fill_v4_replace7_1_20261115.json,$R/m56_fill_v4_replace8_1_20261115.json
bash run-asel2-io-i12j.sh "Town12:M56-P-I01-S1"
bash run-asel2-io-v16.sh "Town12:M56-P-O05-S1,M56-P-O06,M56-P-O07-S2"
echo "V15Q_END $(date -u +%FT%TZ)"
