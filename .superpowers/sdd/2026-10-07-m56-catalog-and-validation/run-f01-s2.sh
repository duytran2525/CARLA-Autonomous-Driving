#!/usr/bin/env bash
# 2026-11-14 F01-S2 (B3 replacement, Town06 road 30) under f-v1.2 + addenda F01-v2/F01-v3. Stage 1 = base revision + prepare +
# revision + compile-only. Stage 2 (A/B, P5) only with Duy's approval: bash run-f01-s2.sh ab REVF '<Duy quote>'.
# f-v1 blocked F01/F02 at probe 1 (nominal-speed steady test). f-v1.1 = the I/O plateau + PID-grid readiness rule,
# POST-NUMBER (principle 6). F01 ONLY: F02 waits until this result is read. Same steps as run-f01-after-f03.sh, except
# M56_RECIPE=v6 / M56_DRIVABLE=dv1 are exported BEFORE the prepare (f-v1 r8 prepared without them), and the A/B waits
# for the Drive archive to end. Exactly ONE A/B (P5) if FROZEN + ADMITTED + all contracts OK. Prints F01S2_END.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_f01s2_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe; V13=D:/AI/CARLA-Funny-Moments.worktrees/m56-v13
export M56_ASEL2_IO=1 M56_ASEL2_F=1 M56_ASEL2_FSITES=$A/m56_f_sites_replace_f01_v3_20261114.json \
  M56_ASEL2_REPLACE=$A/m56_fill_v4_replace1_20261108.json,$A/m56_fill_v4_replace2b_20261108.json,$A/m56_fill_v4_replace3_20261108.json,$A/m56_fill_v4_replace4_20261109.json \
  M56_NO_RENDER=1 M56_SPECTATOR=1 M56_SPAWN_TILT=1 M56_RECIPE=v6 M56_DRIVABLE=dv1 M56_CODE=$V13
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
S=M56-P-F01-S2; RB=$(ls -d $A/m56_c0_partial_io_asel2f01s2base_* 2>/dev/null | tail -1)/c0-partial-v5-frozen-revision.json
echo "recipe f-v1.2 + F01-v2 (eabacab) + F01-v3 (e46ebf1/d95827e) product $(git -C $V13 log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h)" | tee $LOG/head.txt
stage1() {
# base revision from the F01-v3 sites file (offline), once
[ -f "$RB" ] || RB=$(bash run-asel2-revision.sh asel2f01s2base | tee $LOG/base.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')/c0-partial-v5-frozen-revision.json
[ -f "$RB" ] || { echo "F01-S2 NOT RUN: base revision"; cut -c1-300 $LOG/base.log; echo F01S2_STAGE1_END; exit 4; }
echo "RB $RB"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_REV=$RB $PY -I -X utf8 native-f-prepare.py Town06 $S > $LOG/prep.log 2>&1
grep -a '"event": "\(SCENE\|SCENE_ERROR\|PROBE\)"\|^DONE\|^Traceback' $LOG/prep.log | cut -c1-400
P=$(done_path $LOG/prep.log)
[ -n "$P" ] || { echo "F01 NOT RUN: prepare did not finish"; echo F01S2_END; exit 4; }
R=$(bash run-asel2-revision.sh asel2f01s2prep $P | tee $LOG/revision.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')
REVF=$R/c0-partial-v5-frozen-revision.json
[ -f "$REVF" ] || { echo "F01 NOT RUN: revision not frozen"; cut -c1-300 $LOG/revision.log; echo F01S2_END; exit 4; }
OK=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));c=[c for c in d['candidates'] if c['id']==sys.argv[2]];print(int(bool(c) and (c[0]['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" $REVF $S)
[ "$OK" = 1 ] || { echo "F01: not PREPARED"; echo F01S2_END; exit 0; }
# stage 1 stops here after a compile-only pass (no --ab: compile + admission + contracts, no episode); a human reads it
while tasklist | grep -qi CarlaUE4; do sleep 15; done
$PY -I -X utf8 native-f-ab.py $REVF Town06 $S > $LOG/compile.log 2>&1
grep -a '"event": "\(FIXTURE\|ADMISSION\|SCENE_ERROR\)"\|^DONE\|^Traceback' $LOG/compile.log | cut -c1-600
echo "REVF $REVF"; echo F01S2_STAGE1_END; exit 0
}
stage2() {
# addendum F01-v3 section 4.4: the F01-S2 A/B waits for Duy; arg 2 must quote his approval
[ -n "$2" ] || { echo 'F01-S2 A/B needs Duy approval (arg 2)'; exit 5; }; DUY="$2"
REVF=$1; LOG=$A/m56_f01s2ab_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
n=0; until grep -q 'ARCHIVE_END\|^STOP' $A/m56_drive_archive_r3.stdout.txt 2>/dev/null || [ $n -ge 180 ]; do sleep 30; n=$((n+1)); done
echo "archive wait done ($n x 30 s)"
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_F_PREREG=3fb9865 M56_AB_AUTHORITY='Duy [chat] 2026-11-08 A-SEL2 1.4 "Claude soạn recipe F" + 2026-11-09 "tiếp tục làm đi" + 2026-11-14 "đổi recipe f01 hỏi advisor các làm cho f01 thành công" + A/B approval: '"$DUY"' (self-stated identity); PREREG F part 1 3fb9865 + addenda F01-v2 eabacab, F01-v3 e46ebf1/d95827e' \
  $PY -I -X utf8 native-f-ab.py $REVF Town06 $S --ab > $LOG/ab.log 2>&1
grep -a '"event": "\(FIXTURE\|ADMISSION\|AB\|SCENE_ERROR\)"\|^DONE\|^Traceback' $LOG/ab.log | cut -c1-600
D=$(done_path $LOG/ab.log)
for e in A B; do echo "stop $e: $(cat $D/$S/run/episodes/$S/$e/runner/stop.json 2>/dev/null)"; done
[ -n "$D" ] && [ -d "$D/$S/run" ] && $PY -I -X utf8 native-v6-pair.py $D/$S > $LOG/pair-v13.log 2>&1
tail -c 1500 $LOG/pair-v13.log 2>/dev/null
echo F01S2_END
}
if [ "$1" = ab ]; then stage2 "$2" "$3"; else stage1; fi
