#!/usr/bin/env bash
# 2026-11-08 A-SEL2 batch, I/O (docs/m56/PREREG_M56_FILL_V4_ASEL2_20261108.md 6 + addendum B): base revision with the
# fill v4 I/O candidates (M56_ASEL2_IO=1) and replacement round 1 -> per scene native-io-prepare (box anchor midpoint,
# spectator) -> revision with the new preps -> compile + self-check -> exactly ONE A/B per compiled scene (P5, kappa
# pointwise) -> pair under consumer v10 and v8. One own server at a time; no scene is ever re-run.
# usage: bash run-asel2-io.sh "Town12:M56-P-I01-S1,... Town13:..."
cd "$(dirname "$0")"
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_SPECTATOR=1 M56_CODE=${M56_CODE:-D:/AI/CARLA-Funny-Moments.worktrees/m56-v10} \
       M56_IO_BOX_ANCHOR=midpoint M56_ASEL2_IO=1 M56_SPAWN_TILT=${M56_SPAWN_TILT:-} \
       M56_ASEL2_REPLACE=${M56_ASEL2_REPLACE:-D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_fill_v4_replace1_20261108.json}
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_asel2_io_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
echo "product $(git -C $M56_CODE log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h) specs: $1" | tee $LOG/head.txt
R0=$(bash run-asel2-revision.sh asel2iobase | tee $LOG/revision0.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')
[ -f "$R0/c0-partial-v5-frozen-revision.json" ] || { echo "NOT RUN: base revision not frozen"; cut -c1-300 $LOG/revision0.log; echo ASEL2_IO_END; exit 4; }
PREPS=""
for spec in $1; do
  t=${spec%%:*}
  for s in $(echo ${spec#*:} | tr ',' ' '); do
    while tasklist | grep -qi CarlaUE4; do sleep 15; done
    M56_REV=$R0/c0-partial-v5-frozen-revision.json timeout 2400 $PY -I -X utf8 native-io-prepare.py $t $s > $LOG/prep-$s.log 2>&1
    grep -a -E '"event": "(SCENE|SCENE_ERROR)"' $LOG/prep-$s.log | cut -c1-400
    PREPS="$PREPS $(done_path $LOG/prep-$s.log)"
  done
done
R=$(bash run-asel2-revision.sh asel2ioprep $PREPS | tee $LOG/revision.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')
REVF=$R/c0-partial-v5-frozen-revision.json
[ -f "$REVF" ] || { echo "NOT RUN: revision not frozen"; cut -c1-300 $LOG/revision.log; echo ASEL2_IO_END; exit 4; }
for spec in $1; do
  t=${spec%%:*}
  for s in $(echo ${spec#*:} | tr ',' ' '); do
    st=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(next(((c['environment'].get('runtime_recipe_v2') or {}).get('status','') for c in d['candidates'] if c['id']==sys.argv[2]),'MISSING'))" $REVF $s)
    [ "$st" = "PREPARED" ] || { echo "$s: $st (no compile/A-B)"; continue; }
    while tasklist | grep -qi CarlaUE4; do sleep 15; done
    timeout 2400 $PY -I -X utf8 native-io-ab.py $REVF $t $s > $LOG/compile-$s.log 2>&1
    C=$(done_path $LOG/compile-$s.log)
    [ -f "$C/$s/fixture-frozen.json" ] || { echo "$s: compile failed"; grep -a '"event"' $LOG/compile-$s.log | tail -2 | cut -c1-300; continue; }
    $PY -I -X utf8 native-io-selfcheck.py $C/$s > $LOG/selfcheck-$s.log 2>&1 || { echo "$s: self-check failed"; tail -3 $LOG/selfcheck-$s.log; continue; }
    while tasklist | grep -qi CarlaUE4; do sleep 15; done
    M56_IO_KAPPA=pointwise M56_IO_PREREG_APPROVED=34bd4d8 M56_RUN_TAG=asel2 \
      M56_AB_AUTHORITY="[chat] 2026-11-08 Duy (self-stated): spec addendum A-SEL2 (9fa85f8); fill v4 prereg 03fb2ca + addenda A ddce811, B 34bd4d8; one A/B per scene (P5)" \
      timeout 3000 $PY -I -X utf8 native-io-ab.py $REVF $t $s --ab > $LOG/ab-$s.log 2>&1
    D=$(done_path $LOG/ab-$s.log)
    [ -d "$D/$s/run" ] || { echo "$s: no run directory"; grep -a '"event"' $LOG/ab-$s.log | tail -2 | cut -c1-300; continue; }
    for code in $M56_CODE D:/AI/CARLA-Funny-Moments.worktrees/m56-v10; do
      M56_CODE=$code $PY -I -X utf8 native-v6-pair.py $D/$s > $LOG/pair-${s}-$(basename $code).log 2>&1
      echo "$s pair $(basename $code): $(grep '"status"' $LOG/pair-${s}-$(basename $code).log | tail -1 | cut -c1-200)"
    done
  done
done
echo "ASEL2_IO_END logs=$LOG"
