#!/usr/bin/env bash
# 2026-11-15 (Claude quyet duoi uy quyen, user request "tiep tuc lam tiep nhung canh khac"): replacement 6 (B3 + B5) for
# C07-S1 / L08-S1 (both trialed FAILED, CLEAR_N_CONFIRMED_MISSING, generated before B5) -> C07-S2, L08-S2, both Town12.
# Same batch as queue 3c Q3 (run-asel2-cl2.sh: prepare -> revision -> ONE A/B per PREPARED scene (P5) -> pair v12/v10/v6),
# product m56-v12 + spawn tilt, replacement rounds 1..6. Starts only after the release --full run has written its report
# repl6b = repl6 + waits while outputs/m56_asel2_HOLD exists.
# (no CARLA while the release re-evaluates: RAM), and cl2 itself waits for no CarlaUE4.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
R=D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs
until [ -f $R/m56_asel2_release_20261115T054325Z/release-report.json ]; do
  tasklist | grep -q " 36160 " || { [ -f $R/m56_asel2_release_20261115T054325Z/release-report.json ] || { echo "RELEASE_GONE_NO_REPORT: not starting CARLA"; echo REPL6_END; exit 4; }; }
  sleep 60
done
while [ -f $R/m56_asel2_HOLD ]; do sleep 60; done  # offline work in progress (no offline job during a native episode)
echo "release report present, no HOLD $(date -u +%FT%TZ)"
M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v12 M56_SPAWN_TILT=1 \
M56_ASEL2_REPLACE=$R/m56_fill_v4_replace1_20261108.json,$R/m56_fill_v4_replace2b_20261108.json,$R/m56_fill_v4_replace3_20261108.json,$R/m56_fill_v4_replace4_20261109.json,$R/m56_fill_v4_replace5_20261111.json,$R/m56_fill_v4_replace6_20261115.json \
bash run-asel2-cl2.sh "Town12:M56-P-C07-S2,M56-P-L08-S2"
echo "REPL6_END $(date -u +%FT%TZ)"
