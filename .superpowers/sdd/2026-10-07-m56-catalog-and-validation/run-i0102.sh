#!/usr/bin/env bash
# 2026-11-08 io-i-v1.1 addendum E: prepare + compile I01 (Town04, shift +18) and I02 (Town05), then one A/B for each scene
# whose admission is ADMITTED with all three response checks OK.
cd "$(dirname "$0")"
export M56_CODE=${M56_CODE:-D:/AI/CARLA-Funny-Moments.worktrees/m56-v9} M56_IO_BOX_ANCHOR=midpoint M56_IO_SITE_SHIFT="M56-P-I01=18"
P=$(git -C ../../.. log -1 --format=%h); O=../../../outputs
bash run-io-prepare.sh i0102 Town04:M56-P-I01 Town05:M56-P-I02 > $O/m56_i0102_prep.log 2>&1
cat $O/m56_i0102_prep.log | grep -E '"event": "(SCENE|SCENE_ERROR|FIXTURE|ADMISSION)"|REVISION=' | cut -c1-300
R=$(grep -o 'REVISION=.*' $O/m56_i0102_prep.log | tail -1 | cut -d= -f2 | tr -d '\r')
for spec in Town04:M56-P-I01 Town05:M56-P-I02; do
  s=${spec#*:}
  grep -q "\"scene\": \"$s\", \"status\": \"ADMITTED\".*\"EGO:A\": \"OK\", \"EGO:B\": \"OK\", \"NPC:NPC_COMMON\": \"OK\"" $O/m56_io_compile_i0102_$s.log \
    || { echo "$s: not admitted cleanly, no A/B"; continue; }
  unset M56_IO_SITE_SHIFT
  M56_IO_KAPPA=pointwise M56_RUN_TAG=ioi11-20261108 M56_IO_PREREG_APPROVED=$P \
    M56_AB_AUTHORITY="[chat] 2026-11-07 Duy (self-stated): approved io-i-v1.1 and full delegation; Claude decided under it: one A/B of $s under io-i-v1.1 + addendum E (tooling $P), post-number recipe disclosed, consumer v9 1db746f" \
    EVAL_CODES=D:/AI/CARLA-Funny-Moments.worktrees/m56-v8 bash run-io-ab.sh "$R/c0-partial-v5-frozen-revision.json" $spec
done
echo I0102_END
