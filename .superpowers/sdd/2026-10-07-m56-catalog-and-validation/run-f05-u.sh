#!/usr/bin/env bash
# 2026-11-18 F05 under addendum T/U (PREREG_M56_F05_ADDENDUM_T/U_20261118), product m56-v18. Claude under Duy delegation
# ([chat] 18/11 "làm hết cho tôi"). Stage 1 (no arg): base revision (F sites v3 + M56_ASEL2_F05=1) -> prepare (settle x2,
# creep calibration x4) -> revision -> compile + admission (no episode). Stage 2 (ab REVF): the single A/B (P5) + pair v18/v13.
# room (commit headroom, cguard) before every CARLA start. Prints F05U_STAGE1_END / F05U_END.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_f05u_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe; V18=D:/AI/CARLA-Funny-Moments.worktrees/m56-v18; V13=D:/AI/CARLA-Funny-Moments.worktrees/m56-v13
export M56_ASEL2_IO=1 M56_ASEL2_F=1 M56_ASEL2_F05=1 M56_ASEL2_FSITES=$A/m56_f_sites_replace_f01_v3_20261114.json \
  M56_ASEL2_REPLACE=$A/m56_fill_v4_replace1_20261108.json,$A/m56_fill_v4_replace2b_20261108.json,$A/m56_fill_v4_replace3_20261108.json,$A/m56_fill_v4_replace4_20261109.json \
  M56_NO_RENDER=1 M56_SPECTATOR=1 M56_SPAWN_TILT=1 M56_RECIPE=v6 M56_DRIVABLE=dv1 M56_CODE=$V18
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
room() { while tasklist | grep -qi CarlaUE4; do sleep 15; done; python -I asel2-cguard.py --wait-commit-gb ${M56_COMMIT_START_GB:-25} | tail -1; }
S=M56-P-F05
echo "F05 addendum T/U product $(git -C $V18 log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h)" | tee $LOG/head.txt
stage1() {
RB=$(bash run-asel2-revision.sh asel2f05base | tee $LOG/base.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')/c0-partial-v5-frozen-revision.json
[ -f "$RB" ] || { echo "F05 NOT RUN: base revision"; cut -c1-300 $LOG/base.log; echo F05U_STAGE1_END; exit 4; }
echo "RB $RB"
room
M56_REV=$RB $PY -I -X utf8 native-f-prepare.py Town12 $S > $LOG/prep.log 2>&1
grep -a '"event": "\(SCENE\|SCENE_ERROR\|PROBE\)"\|^DONE\|^Traceback' $LOG/prep.log | cut -c1-400
P=$(done_path $LOG/prep.log)
[ -n "$P" ] || { echo "F05 NOT RUN: prepare did not finish"; echo F05U_STAGE1_END; exit 4; }
R=$(bash run-asel2-revision.sh asel2f05prep $P | tee $LOG/revision.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')
REVF=$R/c0-partial-v5-frozen-revision.json
[ -f "$REVF" ] || { echo "F05 NOT RUN: revision not frozen"; cut -c1-300 $LOG/revision.log; echo F05U_STAGE1_END; exit 4; }
OK=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));c=[c for c in d['candidates'] if c['id']==sys.argv[2]];print(int(bool(c) and (c[0]['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" $REVF $S)
[ "$OK" = 1 ] || { echo "F05: not PREPARED"; echo F05U_STAGE1_END; exit 0; }
room
$PY -I -X utf8 native-f-ab.py $REVF Town12 $S > $LOG/compile.log 2>&1
grep -a '"event": "\(FIXTURE\|ADMISSION\|SCENE_ERROR\|CREEP_BOUND\)"\|^DONE\|^Traceback' $LOG/compile.log | cut -c1-600
echo "REVF $REVF"; echo F05U_STAGE1_END; exit 0
}
stage2() {
REVF=$1; LOG=$A/m56_f05uab_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
room
M56_F_PREREG="$2" M56_AB_AUTHORITY='Claude under Duy delegation: [chat] 2026-11-18 "làm hết cho tôi"; Duy 2026-11-10 autonomy (decide per own recommendations); PREREG F part 1 3fb9865 + addenda T/U 20261118' \
  $PY -I -X utf8 native-f-ab.py $REVF Town12 $S --ab > $LOG/ab.log 2>&1
grep -a '"event": "\(FIXTURE\|ADMISSION\|AB\|SCENE_ERROR\|CREEP_BOUND\)"\|^DONE\|^Traceback' $LOG/ab.log | cut -c1-600
D=$(done_path $LOG/ab.log)
for e in A B; do echo "stop $e: $(cat $D/$S/run/episodes/$S/$e/runner/stop.json 2>/dev/null)"; done
if [ -n "$D" ] && [ -d "$D/$S/run" ]; then
  M56_CODE=$V18 $PY -I -X utf8 native-v6-pair.py $D/$S > $LOG/pair-v18.log 2>&1; tail -c 1500 $LOG/pair-v18.log
  M56_CODE=$V13 $PY -I -X utf8 native-v6-pair.py $D/$S > $LOG/pair-v13.log 2>&1; tail -c 800 $LOG/pair-v13.log
fi
echo F05U_END
}
if [ "$1" = ab ]; then stage2 "$2" "$3"; else stage1; fi
