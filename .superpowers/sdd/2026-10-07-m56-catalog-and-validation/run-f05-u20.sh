#!/usr/bin/env bash
# 2026-11-20 F05 under m56-v20 (PREREG_M56_F05_ADDENDUM_V_20261120; same F05 code as v18, Duy's choice 20/11). Reuses the r18c
# prepare + frozen revision byte for byte (no prepare). Two stages, both start CARLA only after room() (no CARLA running, cguard:
# commit >= 25 GB, C >= 10, D >= 80, E >= 150 GB):
#   compile REVF          compile + admission preview, no episode (no P5)
#   ab REVF PREREG        the single A/B (P5) + pairs under v20, v18, v13
# Prints F05V_COMPILE_END / F05V_END.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_f05vc_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe
V20=D:/AI/CARLA-Funny-Moments.worktrees/m56-v20; V18=D:/AI/CARLA-Funny-Moments.worktrees/m56-v18; V13=D:/AI/CARLA-Funny-Moments.worktrees/m56-v13
export M56_ASEL2_IO=1 M56_ASEL2_F=1 M56_ASEL2_F05=1 M56_ASEL2_FSITES=$A/m56_f_sites_replace_f01_v3_20261114.json \
  M56_ASEL2_REPLACE=$A/m56_fill_v4_replace1_20261108.json,$A/m56_fill_v4_replace2b_20261108.json,$A/m56_fill_v4_replace3_20261108.json,$A/m56_fill_v4_replace4_20261109.json \
  M56_NO_RENDER=1 M56_SPECTATOR=1 M56_SPAWN_TILT=1 M56_RECIPE=v6 M56_DRIVABLE=dv1 M56_CODE=$V20
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
room() { while tasklist | grep -qi CarlaUE4; do sleep 15; done; python -I asel2-cguard.py --wait-commit-gb ${M56_COMMIT_START_GB:-25} | tail -1; }
S=M56-P-F05
echo "F05 addendum V product $(git -C $V20 log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h)" | tee $LOG/head.txt
compile() {
REVF=$1; room
$PY -I -X utf8 native-f-ab.py $REVF Town12 $S > $LOG/compile.log 2>&1
grep -a '"event": "\(FIXTURE\|ADMISSION\|SCENE_ERROR\|CREEP_BOUND\)"\|^DONE\|^Traceback' $LOG/compile.log | cut -c1-600
echo "REVF $REVF"; echo F05V_COMPILE_END
}
stage2() {
REVF=$1; LOG=$A/m56_f05vab_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
room
M56_F_PREREG="$2" M56_AB_AUTHORITY='Claude under Duy delegation: [chat] 2026-11-20 Duy chose "F05 dưới v20" (which CARLA run); Duy 2026-11-10 autonomy (decide per own recommendations); PREREG F part 1 3fb9865 + addenda T/U 20261118 + V 20261120'"${M56_F05V_AUTHORITY_EXTRA:-}" \
  $PY -I -X utf8 native-f-ab.py $REVF Town12 $S --ab > $LOG/ab.log 2>&1
grep -a '"event": "\(FIXTURE\|ADMISSION\|AB\|SCENE_ERROR\|CREEP_BOUND\)"\|^DONE\|^Traceback' $LOG/ab.log | cut -c1-600
D=$(done_path $LOG/ab.log)
for e in A B; do echo "stop $e: $(cat $D/$S/run/episodes/$S/$e/runner/stop.json 2>/dev/null)"; done
if [ -n "$D" ] && [ -d "$D/$S/run" ]; then
  pair() { M56_CODE=$2 $PY -I -X utf8 native-v6-pair.py $D/$S > $LOG/pair-$1.log 2>&1; echo "pair $1:"; tail -c 1200 $LOG/pair-$1.log; }
  pair v20 $V20; pair v18 $V18; pair v13 $V13
fi
echo F05V_END
}
case "$1" in compile) compile "$2";; ab) stage2 "$2" "$3";; *) echo "usage: run-f05-u20.sh compile REVF | ab REVF PREREG"; exit 2;; esac
