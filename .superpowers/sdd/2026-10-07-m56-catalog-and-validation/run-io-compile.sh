#!/usr/bin/env bash
# I/O compile + admission (native-io-ab.py, no --ab, own server 2610) + self-check for prepared scenes of ONE town, on an
# existing revision (no preparation, no A/B). usage: M56_CODE=... bash run-io-compile.sh TAG REVISION.json TOWN SCENE[,SCENE]
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_CODE=${M56_CODE:-D:/AI/CARLA-Funny-Moments.worktrees/m56-v9}
O=../../../outputs; P=../../../.venv-m56-native-v1/Scripts/python.exe; TAG=$1 REV=$2 TOWN=$3 SC=$4
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
L=$O/m56_io_compile_${TAG}_$TOWN.log; [ -e "$L" ] && { echo "REFUSED: $L exists"; exit 3; }
echo "compile: product $(git -C $M56_CODE log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h) rev $REV"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
timeout 2400 $P -I -X utf8 native-io-ab.py "$REV" $TOWN $SC > $L 2>&1
grep -v "^INFO\|refused" $L | grep -E '"event"|^DONE' | cut -c1-700
C=$(done_path $L)
for s in ${SC//,/ }; do
  [ -f "$C/$s/fixture-frozen.json" ] && { echo "SELFCHECK $s"; $P -I -X utf8 native-io-selfcheck.py $C/$s 2>&1 | tail -6; }
done
echo "COMPILE_DIR=$C"; echo CHAIN_END
