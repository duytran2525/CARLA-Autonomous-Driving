#!/usr/bin/env bash
# 2026-11-15 night: io-i-v1.3 a first native use, PREPARE ONLY (no revision with the prep, no compile, no A/B; P5 untouched).
# Waits for the O queue (V15O_END in m56_asel2_v15o3.stdout.txt) and no CARLA, then prepares I01-S1 with
# native-io-prepare-i13.py (NPC start by arc) and prints: SCENE event, gate L (addendum L), npc_cut, NPC start road.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'
until grep -q V15O_END $A/m56_asel2_v15o3.stdout.txt 2>/dev/null; do sleep 60; done
grep -q 'NOT RUN' $A/m56_asel2_v15o3.stdout.txt && { echo "NOT RUN: O queue did not run (suite 13)"; echo I13P_END; exit 4; }
while [ -f $A/m56_asel2_HOLD ]; do sleep 60; done
export M56_NO_RENDER=1 M56_RECIPE=v6 M56_SPECTATOR=1 M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v15 \
       M56_IO_BOX_ANCHOR=midpoint M56_ASEL2_IO=1 M56_SPAWN_TILT=1 \
       M56_ASEL2_REPLACE=$A/m56_fill_v4_replace1_20261108.json,$A/m56_fill_v4_replace2b_20261108.json,$A/m56_fill_v4_replace3_20261108.json,$A/m56_fill_v4_replace4_20261109.json,$A/m56_fill_v4_replace5_20261111.json,$A/m56_fill_v4_replace6_20261115.json,$A/m56_fill_v4_replace7_1_20261115.json,$A/m56_fill_v4_replace8_1_20261115.json,$A/m56_fill_v4_replace9_c4_20261115.json
LOG=$A/m56_asel2_i13prep_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
PY=../../../.venv-m56-native-v1/Scripts/python.exe
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
echo "start $(date -u +%FT%TZ) tooling $(git -C ../../.. log -1 --format=%h)"
R0=$(bash run-asel2-revision-io16.sh asel2iobase | tee $LOG/revision0.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')
[ -f "$R0/c0-partial-v5-frozen-revision.json" ] || { echo "NOT RUN: base revision not frozen"; echo I13P_END; exit 4; }
for s in M56-P-I01-S1; do
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  M56_REV=$R0/c0-partial-v5-frozen-revision.json timeout 2400 $PY -I -X utf8 native-io-prepare-i13.py Town12 $s > $LOG/prep-$s.log 2>&1
  grep -a -E '"event": "(SCENE|SCENE_ERROR)"' $LOG/prep-$s.log | cut -c1-400
  D="$(done_path $LOG/prep-$s.log)/$s"
  python -I asel2-io-gap-gate.py "$D"
  python -I -c "import json,sys;j=json.load(open(sys.argv[1]));print('status',j.get('status'),j.get('reason'),'npc_cut',(j.get('npc_cut') or {}).get('reason'),'npc_start_s',j.get('npc_start_s'))" "$D/prepare.json"
  # advisor 16/11: also build the offline revision with this prep (no compile, no A/B) and show its builder flags / status
  RP=$(bash run-asel2-revision-io16.sh asel2i13dry "$(done_path $LOG/prep-$s.log)" | tee $LOG/revision-$s.log | grep -o 'REVISION .*' | tail -1 | cut -d' ' -f2 | tr -d '\r')
  grep -E 'C0_PARTIAL|FREEZE|Traceback|Error' $LOG/revision-$s.log | cut -c1-300
  [ -f "$RP/c0-partial-v5-frozen-revision.json" ] && python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));c=next(c for c in d['candidates'] if c['id']==sys.argv[2]);print('revision',(c['environment'].get('runtime_recipe_v2') or {}).get('status'),c.get('flags') or c['environment'].get('flags'))" "$RP/c0-partial-v5-frozen-revision.json" $s || echo "revision not frozen"
done
echo "I13P_END $(date -u +%FT%TZ) logs=$LOG"
