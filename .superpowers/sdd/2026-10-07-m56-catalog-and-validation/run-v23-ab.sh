#!/usr/bin/env bash
# 2026-11-22 addendum Y (PREREG_M56_V23_ADDENDUM_Y_20261122): the F03-S1 A/B under m56-v23 (Duy [chat] 22/11 chose "v23 hill-start (Recommended)").
# Same env as run-v22-ab.sh, product V23 (F03 only), kit flag M56_KIT_ADMIT_STOP_BOUND=1 (seals the stop-bound proof sources).
# Prepare + frozen revisions reused byte for byte.
#   run-v23-ab.sh SCENE compile REVF          compile + admission preview, no episode (no P5)
#   run-v23-ab.sh SCENE ab REVF PREREG        the single A/B (P5) + pairs under v23, v22
# room() before every CARLA start (no CARLA, commit >= M56_COMMIT_START_GB, C >= 10, D >= 80, E >= 150 GB).
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; PY=../../../.venv-m56-native-v1/Scripts/python.exe
WT=D:/AI/CARLA-Funny-Moments.worktrees; V23=$WT/m56-v23; V22=$WT/m56-v22
REPL=$A/m56_fill_v4_replace1_20261108.json,$A/m56_fill_v4_replace2b_20261108.json,$A/m56_fill_v4_replace3_20261108.json,$A/m56_fill_v4_replace4_20261109.json
export M56_ASEL2_IO=1 M56_ASEL2_F=1 M56_ASEL2_REPLACE=$REPL M56_NO_RENDER=1 M56_SPECTATOR=1 M56_SPAWN_TILT=1 M56_RECIPE=v6 M56_DRIVABLE=dv1 M56_CODE=$V23
export M56_KIT_ADMIT_STOP_BOUND=1
case "$1" in
  F03) export M56_ASEL2_F03=1 M56_ASEL2_FSITES=$A/m56_f_sites_f03_20261118.json; S=M56-P-F03-S1; PAIRS="v23 v22";;
  *) echo "usage: run-v23-ab.sh F03 compile REVF | ab REVF PREREG"; exit 2;;
esac
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
room() { while tasklist | grep -qi CarlaUE4; do sleep 15; done; python -I asel2-cguard.py --wait-commit-gb ${M56_COMMIT_START_GB:-32} | tail -1; }
echo "$1 addendum Y product $(git -C $V23 log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h) kit_flag $M56_KIT_ADMIT_STOP_BOUND"
EV='"event": "\(FIXTURE\|ADMISSION\|AB\|SCENE_ERROR\|CREEP_BOUND\|REVERSE_BOUND\)"\|^DONE\|^Traceback'
if [ "$2" = compile ]; then
  LOG=$A/m56_v23c_$1_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG; room
  $PY -I -X utf8 native-f-ab.py $3 Town12 $S > $LOG/compile.log 2>&1
  grep -a "$EV" $LOG/compile.log | cut -c1-600; echo V23_COMPILE_END; exit 0
fi
[ "$2" = ab ] || exit 2
LOG=$A/m56_v23ab_$1_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG; room
M56_F_PREREG="$4" M56_AB_AUTHORITY="Claude under Duy delegation: [chat] 2026-11-22 Duy \"làm tiếp\", chose \"v23 hill-start (Recommended)\" (one F03-S1 A/B under v23, P5); Duy 2026-11-22 overnight autonomy; addendum Y 20261122" \
  $PY -I -X utf8 native-f-ab.py $3 Town12 $S --ab > $LOG/ab.log 2>&1
grep -a "$EV" $LOG/ab.log | cut -c1-600
D=$(done_path $LOG/ab.log)
for e in A B; do echo "stop $e: $(cat $D/$S/run/episodes/$S/$e/runner/*.json 2>/dev/null | tr '\n' ' ')"; done
if [ -n "$D" ] && [ -d "$D/$S/run" ]; then
  for v in $PAIRS; do
    case $v in v23) C=$V23;; v22) C=$V22;; esac
    M56_CODE=$C $PY -I -X utf8 native-v6-pair.py $D/$S > $LOG/pair-$v.log 2>&1; echo "pair $v:"; tail -c 1200 $LOG/pair-$v.log
  done
fi
echo V23_AB_END
