#!/usr/bin/env bash
# 2026-11-18 offline: the F03 base revision only (same env as run-f05-u.sh stage 1), to check the F05 candidate builder.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'
export M56_ASEL2_IO=1 M56_ASEL2_F=1 M56_ASEL2_F03=1 M56_ASEL2_FSITES=$A/m56_f_sites_f03_20261118.json \
  M56_ASEL2_REPLACE=$A/m56_fill_v4_replace1_20261108.json,$A/m56_fill_v4_replace2b_20261108.json,$A/m56_fill_v4_replace3_20261108.json,$A/m56_fill_v4_replace4_20261109.json \
  M56_NO_RENDER=1 M56_SPECTATOR=1 M56_SPAWN_TILT=1 M56_RECIPE=v6 M56_DRIVABLE=dv1
bash run-asel2-revision.sh asel2f03base
