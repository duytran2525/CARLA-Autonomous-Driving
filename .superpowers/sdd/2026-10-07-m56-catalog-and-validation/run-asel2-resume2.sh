#!/usr/bin/env bash
# 13/11 (Claude quyet duoi uy quyen): resume Q2/Q3 WITHOUT re-running any consumed A/B (P5).
#  1. wait for run-asel2-cl2-pair-town13.sh (CL2P_DONE), 2. pair those 4 Town13 Q3 scenes under the real v12 consumer,
#  3. A/B for the 5 admitted I scenes of Q2 (their A/B never ran: run-asel2-io.sh's O-only self-check stopped them with
#     KeyError reference_switches; prereg io-i-v1 j says admission is the I gate) on the existing revision asel2ioprep,
#     scene I01-S1 first as canary, then the rest only if it produced a run dir; pair under v12 and v10.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
A=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs; PY=../../../.venv-m56-native-v1/Scripts/python.exe
V12=D:/AI/CARLA-Funny-Moments.worktrees/m56-v12; V10=D:/AI/CARLA-Funny-Moments.worktrees/m56-v10
LOG=$A/m56_asel2_resume2_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
REVF=$A/m56_c0_partial_io_asel2ioprep_20261112T144015Z/c0-partial-v5-frozen-revision.json
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
until grep -q CL2P_DONE $A/m56_cl2_pair_town13_r1.stdout.txt 2>/dev/null; do sleep 30; done
D=$A/m56_v2_ab_Town13_20261112T224214Z
for s in M56-P-C03-S2 M56-P-C06-S1 M56-P-L07-S2 M56-P-M02-S1; do
  M56_CODE=$V12 $PY -I -X utf8 native-v6-pair.py $D/$s >> $LOG/pair-v12-town13q3.log 2>&1
  echo "$s v12: $(grep -o '"scene": "'$s'", "status": "[A-Z_]*"' $LOG/pair-v12-town13q3.log | tail -1)"
done
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_SPECTATOR=1 M56_CODE=$V12 M56_IO_BOX_ANCHOR=midpoint M56_ASEL2_IO=1 M56_SPAWN_TILT=1
for spec in Town12:M56-P-I01-S1 Town13:M56-P-I07-S1 Town12:M56-P-I05-S1 Town12:M56-P-I06 Town13:M56-P-I02-S2; do
  t=${spec%%:*}; s=${spec#*:}
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  M56_IO_KAPPA=pointwise M56_IO_PREREG_APPROVED=34bd4d8 M56_RUN_TAG=asel2 \
    M56_AB_AUTHORITY="[chat] 2026-11-08 Duy (self-stated): spec addendum A-SEL2 (9fa85f8); fill v4 prereg 03fb2ca + addenda A ddce811, B 34bd4d8; one A/B per scene (P5)" \
    timeout 3000 $PY -I -X utf8 native-io-ab.py $REVF $t $s --ab > $LOG/ab-$s.log 2>&1
  R=$(done_path $LOG/ab-$s.log)
  grep -a -E '"event": ?"(FIXTURE|ADMISSION|AB|SCENE_ERROR)"|Traceback|TICK_ERROR' $LOG/ab-$s.log | cut -c1-300
  if [ ! -d "$R/$s/run" ]; then echo "$s: no run directory"; [ "$s" = M56-P-I01-S1 ] && { echo "CANARY_FAILED: stop before the other I scenes"; echo RESUME2_END logs=$LOG; exit 5; }; continue; fi
  for code in $V12 $V10; do
    M56_CODE=$code $PY -I -X utf8 native-v6-pair.py $R/$s > $LOG/pair-$s-$(basename $code).log 2>&1
    echo "$s pair $(basename $code): $(grep '"status"' $LOG/pair-$s-$(basename $code).log | tail -1 | cut -c1-200)"
  done
done
echo "RESUME2_END logs=$LOG"