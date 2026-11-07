#!/usr/bin/env bash
# 2026-11-07 io-v1.4 / io-i-v1.1, sequential on the own server: (1) one A/B of O05 (after the I03 A/B frees CARLA),
# (2) re-preparation of I04, I07 (Town06) and I05 (Town04) with addendum D, then revision + compile of the new preps.
cd "$(dirname "$0")"
export M56_CODE=${M56_CODE:-D:/AI/CARLA-Funny-Moments.worktrees/m56-v9} M56_IO_BOX_ANCHOR=midpoint
P=$(git -C ../../.. log -1 --format=%h)
REV='D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_c0_partial_io_v14b_20261107T162712Z\c0-partial-v5-frozen-revision.json'
until ! tasklist | grep -qi CarlaUE4 && grep -q CHAIN_END ../../../outputs/m56_ab_I03_ioi11_20261107.stdout.txt 2>/dev/null \
      || ! tasklist | grep -qi CarlaUE4 && grep -q '"event": "SERVER_STOPPED"' ../../../outputs/m56_ab_I03_ioi11_20261107.stdout.txt; do sleep 20; done
echo "O05 A/B start $(date -u +%FT%TZ)"
M56_IO_KAPPA=pointwise M56_RUN_TAG=io14-20261107 M56_IO_PREREG_APPROVED=$P \
  M56_AB_AUTHORITY="[chat] 2026-11-07 Duy (self-stated): approved the O05 fix ('2.có') and full delegation; Claude decided under it: one A/B of O05 under io-v1.4 (PREREG_M56_IO_I_V1_1_AND_IO_V1_4_20261107, tooling $P), post-number rule disclosed, consumer v9 1db746f" \
  EVAL_CODES=D:/AI/CARLA-Funny-Moments.worktrees/m56-v8 bash run-io-ab.sh "$REV" Town04:M56-P-O05
echo "I re-preparation start $(date -u +%FT%TZ)"
bash run-io-prepare.sh v14d Town06:M56-P-I04,M56-P-I07 Town04:M56-P-I05
echo NEXT_END
