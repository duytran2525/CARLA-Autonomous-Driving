#!/usr/bin/env bash
# I/O preparation chain (no A/B): for each Town:SCENE, prepare (native-io-prepare.py) -> one revision with all the new
# preparations -> native compile + admission (native-io-ab.py, no --ab) -> self-check. One own server at a time (2610).
# usage: M56_IO_SITE_SHIFT="M56-P-O01=95,..." bash run-io-prepare.sh TAG Town04:M56-P-O01 [Town05:M56-P-O02 ...]
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_CODE=${M56_CODE:-D:/AI/CARLA-Funny-Moments.worktrees/m56-v8}
O=../../../outputs; P=../../../.venv-m56-native-v1/Scripts/python.exe; TAG=$1; shift
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
echo "product $(git -C $M56_CODE log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h) shift '${M56_IO_SITE_SHIFT}'"
PREPS=""
for spec in "$@"; do
  t=${spec%%:*}; s=${spec#*:}
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  timeout 2400 $P -I -X utf8 native-io-prepare.py $t $s > $O/m56_io_prepare_${TAG}_$s.log 2>&1
  grep -E '"event": "(SCENE|SCENE_ERROR)"' $O/m56_io_prepare_${TAG}_$s.log | cut -c1-400
  PREPS="$PREPS $(done_path $O/m56_io_prepare_${TAG}_$s.log)"
done
bash run-io-revision.sh $TAG $PREPS > $O/m56_io_revision_$TAG.log 2>&1; cat $O/m56_io_revision_$TAG.log
R=$(grep "^REVISION" $O/m56_io_revision_$TAG.log | sed 's/^REVISION //')
for spec in "$@"; do
  t=${spec%%:*}; s=${spec#*:}
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  timeout 2400 $P -I -X utf8 native-io-ab.py $R/c0-partial-v5-frozen-revision.json $t $s > $O/m56_io_compile_${TAG}_$s.log 2>&1
  grep -v "^INFO\|refused" $O/m56_io_compile_${TAG}_$s.log | grep -E '"event"|^DONE' | cut -c1-700
  C=$(done_path $O/m56_io_compile_${TAG}_$s.log)
  [ -f "$C/$s/fixture-frozen.json" ] && $P -I -X utf8 native-io-selfcheck.py $C/$s 2>&1 | tail -6
done
echo "REVISION=$R"; echo CHAIN_END
