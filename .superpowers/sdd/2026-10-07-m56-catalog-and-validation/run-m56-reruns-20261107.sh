#!/usr/bin/env bash
# M56 P5 reruns of O01 and O02, 2026-11-07. Claude decided these under Duy's full delegation (self-stated, ledger 114cba1).
# Waits for the offline chain (run-v8761970-chain.sh), then:
#   gate 1: native-pair-diff ALL_IDENTICAL on the 7 re-evaluated scenes (product 8761970 = references);
#   gate 2: online worst case (detection total + 0.14 s/tick for CARLA and kit) < 270 s on every timed episode;
#   per A/B: >= 8 GB RAM free, no other CarlaUE4 (run-io-ab.sh waits), no STOP file.
#   O01: io-v1.2 bound (M56_IO_KAPPA unset).  O02: pointwise bound (erratum ce3fc43).  One A/B each (P5).
#   Then pair results under v8 and v7, and the O02 old-bound recompute (native-io-kappa-recompute.py).
# Safe stop: create outputs/m56_reruns_20261107.STOP. It is honoured only BEFORE an A/B starts: an A/B in flight is never
# killed (that would spend the one P5 rerun). Exit 3 = STOPPED_SAFE; exit 4 = a gate failed (nothing run).
cd "$(dirname "$0")"
O=../../../outputs; C=$O/m56_chain_resume1_20261107.stdout.txt; STOP=$O/m56_reruns_20261107.STOP
REV='D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_c0_partial_io_o0102v12_20261027T033452Z\c0-partial-v5-frozen-revision.json'
P=../../../.venv-m56-native-v1/Scripts/python.exe
say() { echo "$(date -u +%FT%TZ) $*"; }
until grep -q "STEP2_END\|STEP1_END exit [^0]" $C 2>/dev/null; do sleep 30; done
grep -q "STEP2_END exit 0" $C || { say "GATE_FAIL: offline chain did not finish cleanly"; exit 4; }
R=m56_v6_pair_20261026T142613Z
python -I -X utf8 native-pair-diff.py 20261107T1107 M56-P-L04=$R M56-P-C01=$R M56-P-L01=$R M56-P-C05=$R \
  M56-P-O03=m56_v6_pair_20261027T023517Z M56-P-O01=m56_v6_pair_20261027T060958Z M56-P-O02=m56_v6_pair_20261027T070642Z
python -I -X utf8 native-pair-diff.py 20261107T1107 M56-P-L04=$R M56-P-C01=$R M56-P-L01=$R M56-P-C05=$R \
  M56-P-O03=m56_v6_pair_20261027T023517Z M56-P-O01=m56_v6_pair_20261027T060958Z M56-P-O02=m56_v6_pair_20261027T070642Z \
  | grep -q '^ALL_IDENTICAL$' || { say "GATE_FAIL: pair re-eval differs from the references"; exit 4; }
say "GATE1_PASS pair re-eval identical"
python -I -X utf8 -c "
import re, sys
rows = [re.match(r'(\S+ \S+): (\d+) ticks, detection total ([\d.]+) s', l) for l in open(sys.argv[1], encoding='utf-8')]
est = {m[1]: float(m[3]) + .14 * int(m[2]) for m in rows if m}
print('online worst-case estimate (s):', {k: round(v) for k, v in est.items()})
sys.exit(0 if len(est) >= 5 and max(est.values()) < 270 else 1)" $O/m56_v8761970_timing_20261107.txt \
  || { say "GATE_FAIL: online timing"; exit 4; }
say "GATE2_PASS online timing"
AUTH="[chat] 2026-11-07 Duy (self-stated): 'tôi cho bạn toàn quyền quyết định ... hoàn thiện task m56'; Claude decided under that delegation (not Duy's own review): P5 rerun"
run_one() {  # $1 Town:SCENE  $2 tag  $3 kappa ('' or pointwise)  $4 authority detail
  [ -e "$STOP" ] && { say "STOPPED_SAFE before $1"; exit 3; }
  until powershell -NoProfile -c "exit [int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB -lt 8)"; do say "waiting: < 8 GB RAM free"; sleep 60; done
  say "AB_START $1 kappa=${3:-window-max-sum}"
  M56_IO_KAPPA=$3 M56_RUN_TAG=$2 M56_IO_PREREG_APPROVED=90bc7a3 M56_AB_AUTHORITY="$AUTH $4" \
    EVAL_CODES=D:/AI/CARLA-Funny-Moments.worktrees/m56-v7 bash run-io-ab.sh "$REV" "$1"
  say "AB_END $1"
}
run_one Town04:M56-P-O01 p5rerun-20261107 '' "O01: harness perf bug proven offline, fix product 1fc1ac6+8761970; io-v1.2 bound."
run_one Town05:M56-P-O02 p5rerun-20261107 pointwise "O02: same perf bug + post-number pointwise lateral bound, erratum ce3fc43 (old bound reported)."
D=$(python -I -c "import re,sys;t=open(sys.argv[1],encoding='utf-8',errors='replace').read();m=re.findall(r'^DONE (.+)$',t,re.M);print(m[-1].strip() if m else '')" $O/m56_io_ab_M56-P-O02_p5rerun-20261107.log)
[ -n "$D" ] && M56_RECIPE=v6 M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v8 $P -I -X utf8 native-io-kappa-recompute.py "$D\\M56-P-O02"
say RERUNS_END
