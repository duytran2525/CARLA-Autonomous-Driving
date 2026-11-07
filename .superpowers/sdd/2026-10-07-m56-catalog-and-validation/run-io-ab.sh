#!/usr/bin/env bash
# I/O A/B chain (approved prereg only): for each Town:SCENE run exactly ONE A/B (native-io-ab.py --ab, P5), then the
# pair-level result (native-v6-pair.py) under the product consumer and under each extra consumer given in EVAL_CODES.
# usage: M56_IO_PREREG_APPROVED=<commit> EVAL_CODES="D:/.../m56-v7" bash run-io-ab.sh REVISION.json Town04:M56-P-O01 [...]
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_CODE=${M56_CODE:-D:/AI/CARLA-Funny-Moments.worktrees/m56-v8}
T=${M56_RUN_TAG:+_$M56_RUN_TAG}  # 2026-11-07: per-run log suffix, never overwrite an earlier run's logs
O=../../../outputs; P=../../../.venv-m56-native-v1/Scripts/python.exe; REV=$1; shift
[ -n "$M56_IO_PREREG_APPROVED" ] || { echo "REFUSED: M56_IO_PREREG_APPROVED unset"; exit 3; }
for spec in "$@"; do
  [ -e "$O/m56_io_ab_${spec#*:}$T.log" ] && { echo "REFUSED: $O/m56_io_ab_${spec#*:}$T.log exists (set a new M56_RUN_TAG)"; exit 3; }
done
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
echo "A/B: product $(git -C $M56_CODE log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h) approved $M56_IO_PREREG_APPROVED kit_kappa ${M56_IO_KAPPA:-window-max-sum}"
for spec in "$@"; do
  t=${spec%%:*}; s=${spec#*:}
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  timeout 3000 $P -I -X utf8 native-io-ab.py $REV $t $s --ab > $O/m56_io_ab_$s$T.log 2>&1
  grep -v "^INFO\|refused" $O/m56_io_ab_$s$T.log | grep -E '"event"|^DONE' | cut -c1-500
  D=$(done_path $O/m56_io_ab_$s$T.log)
  [ -d "$D/$s/run" ] || { echo "$s: no run directory"; continue; }
  for code in $M56_CODE $EVAL_CODES; do
    M56_CODE=$code $P -I -X utf8 native-v6-pair.py $D/$s > $O/m56_io_pair_${s}_$(basename $code)$T.log 2>&1
    echo "$s pair under $(basename $code): $(grep '"status"' $O/m56_io_pair_${s}_$(basename $code)$T.log | tail -1 | cut -c1-300)"
  done
done
echo CHAIN_END
