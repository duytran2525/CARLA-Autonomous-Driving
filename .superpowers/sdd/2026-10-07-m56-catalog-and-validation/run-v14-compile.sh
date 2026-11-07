#!/usr/bin/env bash
# io-i-v1.1 / io-v1.4 (2026-11-07): compile + admission for the five prepared scenes on revision v14b, one town at a time.
cd "$(dirname "$0")"
REV='D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_c0_partial_io_v14b_20261107T162712Z\c0-partial-v5-frozen-revision.json'
export M56_CODE=${M56_CODE:-D:/AI/CARLA-Funny-Moments.worktrees/m56-v9}
bash run-io-compile.sh v14b "$REV" Town06 M56-P-I03,M56-P-I04,M56-P-I07
bash run-io-compile.sh v14b "$REV" Town04 M56-P-I05,M56-P-O05
echo ALL_COMPILES_END
