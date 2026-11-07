#!/usr/bin/env bash
# M56 2026-11-07 resume chain, offline only (no CARLA): step 1 per-scene pair re-eval on M56_CODE, step 2 online timing.
# Safe stop: create outputs/m56_v8761970_pair_reeval_20261107.jsonl.STOP
#   empty file  -> stops after the scene / episode now running;  text 'now' -> stops at once (that one is redone).
#   Both print STOPPED_SAFE and exit 3; finished scenes/episodes are checkpointed in the .jsonl / timing file.
# Resume: delete the .STOP file and run this script again (done work is skipped).
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_CODE=${M56_CODE:-D:/AI/CARLA-Funny-Moments.worktrees/m56-v8}
O='D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs'; P=../../../.venv-m56-native-v1/Scripts/python.exe
J="$O\\m56_v8761970_pair_reeval_20261107.jsonl"
export M56_STOP="$J.STOP" M56_DONE="$O\\m56_v8761970_timing_20261107.txt"
echo "chain start $(date -u +%FT%TZ) product $(git -C $M56_CODE log -1 --format=%h) dirty=$(git -C $M56_CODE status --short | wc -l)"
$P -I -X utf8 native-pair-per-scene.py "$J" \
  "$O\\m56_v2_ab_Town05_20261026T113316Z\\M56-P-L04" "$O\\m56_io_ab_Town06_20261026T193247Z\\M56-P-O03" \
  "$O\\m56_io_ab_Town04_20261027T055306Z\\M56-P-O01" "$O\\m56_io_ab_Town05_20261027T065150Z\\M56-P-O02" \
  "$O\\m56_v2_ab_Town04_20261026T093209Z\\M56-P-C01" "$O\\m56_v2_ab_Town04_20261026T120702Z\\M56-P-L01" \
  "$O\\m56_v2_ab_Town05_20261026T133919Z\\M56-P-C05"
r=$?; echo "STEP1_END exit $r $(date -u +%FT%TZ)"; [ $r -eq 0 ] || exit $r
$P -I -X utf8 native-io-online-timing.py "$O\\m56_io_ab_Town06_20261026T193247Z\\M56-P-O03:B" \
  "$O\\m56_io_ab_Town04_20261027T055306Z\\M56-P-O01:A" "$O\\m56_io_ab_Town04_20261027T055306Z\\M56-P-O01:B"
r=$?; echo "STEP2_END exit $r $(date -u +%FT%TZ)"; exit $r
