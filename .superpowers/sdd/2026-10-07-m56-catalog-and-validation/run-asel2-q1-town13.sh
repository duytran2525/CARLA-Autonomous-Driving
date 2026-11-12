#!/usr/bin/env bash
export PATH=/usr/bin:$PATH  # started from PowerShell, Git bash has no coreutils on PATH (r4: ran nothing, printed DONE)
# 2026-11-12 user: "đầu tiên hãy chạy Q1 Town13 trước" -> Q1 of queue 3c for Town13 ONLY (same commands, values, product
# m56-v12 and evidence rule as run-asel2-queue3c.sh lines 16-30), now with tech fix 5 (synchronous raster, 07077ac).
# Q2/Q3 are NOT started. A later queue 3c run computes Q1 from evidence again (these scenes then read PAIRED -> SKIP).
cd "$(dirname "$0")"
O=../../../outputs; V12=D:/AI/CARLA-Funny-Moments.worktrees/m56-v12; PY=../../../.venv-m56-native-v1/Scripts/python.exe
REV1=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_c0_partial_io_asel2prep_20261108T114946Z/c0-partial-v5-frozen-revision.json
LOG=$O/m56_asel2_q1t13_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $LOG
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
pair() { M56_CODE=$V12 $PY -I -X utf8 native-v6-pair.py $1 >> $LOG/pair-v12.log 2>&1
         s=$(basename $1); echo "$s v12: $(grep -o '"scene": "'$s'", "status": "[A-Z_]*"' $LOG/pair-v12.log | tail -1)"; }
echo "Q1 Town13 only (r4) $(date -u +%FT%TZ)"
t=Town13; R=$(python -I asel2-q1-remaining.py $t M56-P-C07-S1,M56-P-L03-S1,M56-P-L06-S1,M56-P-M01-S1,M56-P-M03-S1 20261110T145000Z)
echo "$t: $R"
[ -n "$R" ] || { echo "NO_PLAN"; exit 3; }
N=$(echo "$R" | cut -d'|' -f1 | sed 's/^RUN //'); P=$(echo "$R" | cut -d'|' -f2 | sed 's/^PAIR //')
for d in $P; do pair $d; done
if [ -n "$N" ]; then
  while tasklist | grep -qi CarlaUE4; do sleep 15; done
  M56_NO_RENDER=1 M56_RECIPE=v6 M56_SPECTATOR=1 M56_DRIVABLE=dv1 M56_CODE=$V12 $PY -I -X utf8 native-v2-ab.py $REV1 $t $N > $LOG/ab-$t.log 2>&1
  D=$(done_path $LOG/ab-$t.log)
  for s in $(echo $N | tr ',' ' '); do
    [ -d "$D/$s/run" ] || { echo "$s: no run dir"; continue; }
    pair $D/$s
  done
fi
echo "Q1_TOWN13_DONE $(date -u +%FT%TZ)"
