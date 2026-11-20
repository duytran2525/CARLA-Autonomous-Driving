#!/usr/bin/env bash
# 2026-11-20 addendum W (PREREG_M56_V21_ADDENDUM_W_20261120): one A/B per scene under m56-v21 (Duy [chat] 20/11 "làm v21 cho tôi").
# Same env as run-f05-u20.sh (F05) / run-f03-u20.sh (F03), product V21. Prepare + frozen revisions reused byte for byte.
#   run-v21-ab.sh SCENE compile REVF          compile + admission preview, no episode (no P5)
#   run-v21-ab.sh SCENE ab REVF PREREG        the single A/B (P5) + pairs under v21, v20, v18 (+ v13 for F05)
# SCENE = F05 | F03. room() before every CARLA start (no CARLA, commit >= M56_COMMIT_START_GB, C >= 10, D >= 80, E >= 150 GB).
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; PY=../../../.venv-m56-native-v1/Scripts/python.exe
WT=D:/AI/CARLA-Funny-Moments.worktrees; V21=$WT/m56-v21; V20=$WT/m56-v20; V18=$WT/m56-v18; V13=$WT/m56-v13
REPL=$A/m56_fill_v4_replace1_20261108.json,$A/m56_fill_v4_replace2b_20261108.json,$A/m56_fill_v4_replace3_20261108.json,$A/m56_fill_v4_replace4_20261109.json
export M56_ASEL2_IO=1 M56_ASEL2_F=1 M56_ASEL2_REPLACE=$REPL M56_NO_RENDER=1 M56_SPECTATOR=1 M56_SPAWN_TILT=1 M56_RECIPE=v6 M56_DRIVABLE=dv1 M56_CODE=$V21
case "$1" in
  F05) export M56_ASEL2_F05=1 M56_ASEL2_FSITES=$A/m56_f_sites_replace_f01_v3_20261114.json; S=M56-P-F05; PAIRS="v21 v20 v18 v13";;
  F03) export M56_ASEL2_F03=1 M56_ASEL2_FSITES=$A/m56_f_sites_f03_20261118.json; S=M56-P-F03-S1; PAIRS="v21 v20 v18";;
  *) echo "usage: run-v21-ab.sh F05|F03 compile REVF | ab REVF PREREG"; exit 2;;
esac
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
room() { while tasklist | grep -qi CarlaUE4; do sleep 15; done; python -I asel2-cguard.py --wait-commit-gb ${M56_COMMIT_START_GB:-32} | tail -1; }
echo "$1 addendum W product $(git -C $V21 log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h)"
EV='"event": "\(FIXTURE\|ADMISSION\|AB\|SCENE_ERROR\|CREEP_BOUND\|REVERSE_BOUND\)"\|^DONE\|^Traceback'
if [ "$2" = compile ]; then
  LOG=$A/m56_v21c_$1_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG; room
  $PY -I -X utf8 native-f-ab.py $3 Town12 $S > $LOG/compile.log 2>&1
  grep -a "$EV" $LOG/compile.log | cut -c1-600; echo V21_COMPILE_END; exit 0
fi
[ "$2" = ab ] || exit 2
LOG=$A/m56_v21ab_$1_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG; room
M56_F_PREREG="$4" M56_AB_AUTHORITY="Claude under Duy delegation: [chat] 2026-11-20 Duy \"làm v21 cho tôi\" (v21 for F03 and F05, one A/B each); Duy 2026-11-10 autonomy; addendum W 20261120" \
  $PY -I -X utf8 native-f-ab.py $3 Town12 $S --ab > $LOG/ab.log 2>&1
grep -a "$EV" $LOG/ab.log | cut -c1-600
D=$(done_path $LOG/ab.log)
for e in A B; do echo "stop $e: $(cat $D/$S/run/episodes/$S/$e/runner/*.json 2>/dev/null | tr '\n' ' ')"; done
if [ -n "$D" ] && [ -d "$D/$S/run" ]; then
  for v in $PAIRS; do
    case $v in v21) C=$V21;; v20) C=$V20;; v18) C=$V18;; v13) C=$V13;; esac
    M56_CODE=$C $PY -I -X utf8 native-v6-pair.py $D/$S > $LOG/pair-$v.log 2>&1; echo "pair $v:"; tail -c 1200 $LOG/pair-$v.log
  done
fi
echo V21_AB_END
