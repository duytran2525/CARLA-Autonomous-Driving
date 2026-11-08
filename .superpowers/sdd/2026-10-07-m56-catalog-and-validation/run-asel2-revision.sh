#!/usr/bin/env bash
# 2026-11-08 A-SEL2: freeze a C0 partial revision = run-io-revision.sh base + fill v4 C/L/M successors (M56_ASEL2_FILL),
# product m56-v10 (A-SEL2 towns), site identity incl. the fill-v4 sites; + given preparation dirs (last win). Offline.
# usage: bash run-asel2-revision.sh OUT_TAG [PREPARE_DIR ...]
cd "$(dirname "$0")"
export M56_RECIPE=v6 M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v10 M56_ASEL2_FILL=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_fill_v4a_20261108.json
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'; PYM=../../../.venv-m56-v1/Scripts/python.exe
ID=$A/m56_site_identity_asel2_20261108.json
done_path() { python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip().replace(chr(92),'/') if m else '')" "$1"; }
E3=$A/m56_v5_m_e3_20261025T155257Z
CL="$A/m56_v2_prepare_Town04_20261025T055137Z $A/m56_v2_prepare_Town05_20261025T083106Z $A/m56_v2_prepare_Town06_20261025T092150Z $A/m56_v2_prepare_Town07_20261025T092316Z $A/m56_v2_prepare_Town04_20261025T120501Z"
MP=""; for t in Town04 Town05 Town06 Town07; do MP="$MP $(done_path $E3/prepM-$t.log)"; done
M4=$(done_path $(ls -td $A/m56_v5_m04_* | head -1)/prep-M04.log)
E4="$(done_path $A/m56_v5_e4_20261025T164551Z/prep-Town04.log) $(done_path $A/m56_v5_e4_20261025T164551Z/prep-Town05.log)"
TAG=$1; shift
H=$A/m56_c0_partial_io_${TAG}_$(date -u +%Y%m%dT%H%M%SZ)
$PYM -I -X utf8 native-v5-revision.py $H $ID $CL $MP $M4 $E4 "$@" 2>&1 | grep -E 'C0_PARTIAL|FREEZE|Traceback|Error' | cut -c1-400
echo "REVISION $H"
