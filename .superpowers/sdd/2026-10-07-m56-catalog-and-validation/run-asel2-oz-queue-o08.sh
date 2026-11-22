#!/usr/bin/env bash
# 2026-11-23 O08-S3 only, second prepare (Duy [chat] 22/11 after the 14:35Z cguard stop: "Tôi đóng app rồi chạy lại"; O04-S3 stays
# BLOCKED). Otherwise identical to run-asel2-oz-queue.sh: addendum Z (docs/m56/PREREG_M56_IO_O_ADDENDUM_Z_20261122.md): O04-S3 and
# O08-S3 (Town13) with product m56-v15 036688b + spawn tilt and replacements 1..9, exactly as run-asel2-v15o-queue.sh, through
# run-asel2-io-z.sh (prepare = native-io-prepare-z.py). One prepare and at most one A/B per scene (P5). Refuses to run when the
# STOP file exists, m56-v15 is not clean at 036688b, addendum Z or the Z tooling is uncommitted, or either scene already has an A/B.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
W=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1
V15=D:/AI/CARLA-Funny-Moments.worktrees/m56-v15
Z=docs/m56/PREREG_M56_IO_O_ADDENDUM_Z_20261122.md
no() { echo "NOT RUN: $1"; echo "OZ_END $(date -u +%FT%TZ)"; exit 4; }
[ -f $R/m56_asel2_STOP ] && no "STOP file"
[ "$(git -C $V15 rev-parse --short=7 HEAD)" = 036688b ] && [ -z "$(git -C $V15 status --porcelain)" ] || no "m56-v15 is not clean at 036688b"
[ -z "$(git -C $W status --porcelain -- $Z .superpowers/sdd/2026-10-07-m56-catalog-and-validation/native-io-prepare-z.py .superpowers/sdd/2026-10-07-m56-catalog-and-validation/run-asel2-io-z.sh .superpowers/sdd/2026-10-07-m56-catalog-and-validation/run-asel2-oz-queue.sh)" ] || no "addendum Z or Z tooling uncommitted"
ZC=$(git -C $W log -1 --format=%h -- $Z); [ -n "$ZC" ] || no "addendum Z not committed"
for s in M56-P-O08-S3; do ls -d $R/m56_io_ab_*/$s >/dev/null 2>&1 && no "$s already has an A/B dir (P5)"; done
while [ -f $R/m56_asel2_HOLD ]; do sleep 60; done
echo "start $(date -u +%FT%TZ) addendum Z $ZC"
export M56_CODE=$V15 M56_SPAWN_TILT=1 M56_Z_COMMIT=$ZC \
M56_ASEL2_REPLACE=$R/m56_fill_v4_replace1_20261108.json,$R/m56_fill_v4_replace2b_20261108.json,$R/m56_fill_v4_replace3_20261108.json,$R/m56_fill_v4_replace4_20261109.json,$R/m56_fill_v4_replace5_20261111.json,$R/m56_fill_v4_replace6_20261115.json,$R/m56_fill_v4_replace7_1_20261115.json,$R/m56_fill_v4_replace8_1_20261115.json,$R/m56_fill_v4_replace9_c4_20261115.json
bash run-asel2-io-z.sh "Town13:M56-P-O08-S3"
echo "OZ_END $(date -u +%FT%TZ)"
