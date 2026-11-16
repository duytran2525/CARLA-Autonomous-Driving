#!/usr/bin/env bash
# 2026-11-15 night (replaces run-asel2-v15-queue.sh / run-asel2-r9-queue.sh before either ran a step): after full suite 12
# (v15 bytes) ends CHAIN_PASSED, product m56-v15 + spawn tilt, replacements 1..9 (9 = m56_fill_v4_replace9_c4, addendum K):
#   O05-S1, O06, O07-S2 (Town12; io-v1.6 + consumer v15), O04-S3, O08-S3 (Town13; addendum K, io-v1.5/1.6),
# NOT here: I01-S1, I02-S2, I05-S2, I06-S2, I07-S2, I08-S2 (I08-S2 has I02-S2's shape: fixed 2.3 s G3 does not forecast the B guard) -- held for the B lane-change timing recipe (user [chat] 2026-11-15 night).
# One A/B per scene (P5). Any other suite outcome: nothing runs.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
# 16/11 10:30 local: suite 13 was killed by a Start-menu shutdown at 27% (no checkpoint). User [chat] 16/11: "full suite chỉ
# chạy lần cuối thôi, trước hết phải tìm đủ các cảnh" -> the gate is the focused run of every test file v15 touched.
S=m56-v15-focus-20261116.run.json
until [ -f $S ] && grep -q '"end_utc"' $S; do sleep 60; done
grep -q '"verdict_chain": "CHAIN_PASSED"' $S || { echo "NOT RUN: v15 focused tests not passed"; grep -E '"(status|summary)"' $S; echo V15O_END; exit 4; }
while [ -f $R/m56_asel2_HOLD ]; do sleep 60; done
echo "start $(date -u +%FT%TZ)"
export M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v15 M56_SPAWN_TILT=1 \
M56_ASEL2_REPLACE=$R/m56_fill_v4_replace1_20261108.json,$R/m56_fill_v4_replace2b_20261108.json,$R/m56_fill_v4_replace3_20261108.json,$R/m56_fill_v4_replace4_20261109.json,$R/m56_fill_v4_replace5_20261111.json,$R/m56_fill_v4_replace6_20261115.json,$R/m56_fill_v4_replace7_1_20261115.json,$R/m56_fill_v4_replace8_1_20261115.json,$R/m56_fill_v4_replace9_c4_20261115.json
bash run-asel2-io-v16.sh "Town12:M56-P-O05-S1,M56-P-O06,M56-P-O07-S2 Town13:M56-P-O04-S3,M56-P-O08-S3"
echo "V15O_END $(date -u +%FT%TZ)"
