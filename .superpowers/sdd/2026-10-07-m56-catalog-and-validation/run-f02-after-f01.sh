#!/usr/bin/env bash
# 2026-11-09 A-SEL2 F02 (PREREG F part 1 3fb9865; F02_RECIPE_NOTES_20261109; PLAN_M56_F_NATIVE_TOOLING; sites f-site-generate 9677a51; realized
# F_REALIZED_DESCRIPTORS_20261109): after the F01 chain (F01_END) (one own server at a time):
#  1. native-f-prepare (Town12, M56-P-F02) on the F base revision 2; 2. revision with that preparation;
#  3. native-f-ab --ab: compile + admission + response contracts, and only if FROZEN + ADMITTED + all contracts OK exactly
#  ONE A/B (P5), outer 1500 s, dv1; 4. pair under consumer v13. No re-run of any step with other values. Prints F01_END.
cd "$(dirname "$0")"
until grep -q F01_END ../../../outputs/m56_f01_chain3.stdout.txt 2>/dev/null; do sleep 120; done
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; LOG=$A/m56_f02_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe; V13=D:/AI/CARLA-Funny-Moments.worktrees/m56-v13
export M56_ASEL2_IO=1 M56_ASEL2_F=1 M56_ASEL2_FSITES=$A/m56_f_sites_20261109.json \
  M56_ASEL2_REPLACE=$A/m56_fill_v4_replace1_20261108.json,$A/m56_fill_v4_replace2b_20261108.json,$A/m56_fill_v4_replace3_20261108.json,$A/m56_fill_v4_replace4_20261109.json
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
S=M56-P-F02; RB=$A/m56_c0_partial_io_asel2fbase2_20261109T160045Z/c0-partial-v5-frozen-revision.json
echo "product $(git -C $V13 log -1 --format=%h) tooling $(git -C ../../.. log -1 --format=%h)" | tee $LOG/head.txt
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_NO_RENDER=1 M56_SPECTATOR=1 M56_SPAWN_TILT=1 M56_CODE=$V13 M56_REV=$RB $PY -I -X utf8 native-f-prepare.py Town12 $S > $LOG/prep.log 2>&1
grep -a '"event": "\(SCENE\|SCENE_ERROR\|PROBE\)"\|^DONE\|^Traceback' $LOG/prep.log | cut -c1-400
P=$(done_path $LOG/prep.log)
[ -n "$P" ] || { echo "F02 NOT RUN: prepare did not finish"; echo F02_END; exit 4; }
R=$(bash run-asel2-revision.sh asel2f02prep $P | tee $LOG/revision.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')
REVF=$R/c0-partial-v5-frozen-revision.json
[ -f "$REVF" ] || { echo "F02 NOT RUN: revision not frozen"; cut -c1-300 $LOG/revision.log; echo F02_END; exit 4; }
OK=$(python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));c=[c for c in d['candidates'] if c['id']==sys.argv[2]];print(int(bool(c) and (c[0]['environment'].get('runtime_recipe_v2') or {}).get('status')=='PREPARED'))" $REVF $S)
[ "$OK" = 1 ] || { echo "F02: not PREPARED"; echo F02_END; exit 0; }
export M56_NO_RENDER=1 M56_SPECTATOR=1 M56_SPAWN_TILT=1 M56_RECIPE=v6 M56_DRIVABLE=dv1 M56_CODE=$V13
# no timeout (a kill mid-episode would spend P5 and orphan the server; the watchdog handles a hang). --ab compiles, checks
# the contracts and admits first, and returns before any episode unless FROZEN + ADMITTED + every contract OK.
while tasklist | grep -qi CarlaUE4; do sleep 15; done
M56_F_PREREG=3fb9865 M56_AB_AUTHORITY='Duy [chat] 2026-11-08 A-SEL2 1.4 "Claude soạn recipe F" + 2026-11-09 "tiếp tục làm đi" (self-stated identity); PREREG F part 1 3fb9865; realized F_REALIZED_DESCRIPTORS_20261109; F02_RECIPE_NOTES_20261109' \
  $PY -I -X utf8 native-f-ab.py $REVF Town12 $S --ab > $LOG/ab.log 2>&1
grep -a '"event": "\(FIXTURE\|ADMISSION\|AB\|SCENE_ERROR\)"\|^DONE\|^Traceback' $LOG/ab.log | cut -c1-600
D=$(done_path $LOG/ab.log)
[ -n "$D" ] && [ -d "$D/$S/run" ] && M56_CODE=$V13 $PY -I -X utf8 native-v6-pair.py $D/$S > $LOG/pair-v13.log 2>&1
tail -c 1500 $LOG/pair-v13.log 2>/dev/null
echo F02_END
