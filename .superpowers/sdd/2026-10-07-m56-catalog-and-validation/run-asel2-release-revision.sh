#!/usr/bin/env bash
# 2026-11-14 offline: release revision = run-asel2-revision.sh with BOTH F preparations that reached a PASS pair
# (F02 m56_v2_prepare_Town12_20261114T132922Z, F01-S2 m56_v2_prepare_Town06_20261114T142115Z); same env as run-f01-s2.sh.
export PATH=/usr/bin:$PATH
cd "$(dirname "$0")"
A='D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs'
export M56_ASEL2_IO=1 M56_ASEL2_F=1 M56_ASEL2_FSITES=$A/m56_f_sites_replace_f01_v3_20261114.json \
  M56_ASEL2_REPLACE=$A/m56_fill_v4_replace1_20261108.json,$A/m56_fill_v4_replace2b_20261108.json,$A/m56_fill_v4_replace3_20261108.json,$A/m56_fill_v4_replace4_20261109.json
bash run-asel2-revision.sh asel2release $A/m56_v2_prepare_Town12_20261114T132922Z $A/m56_v2_prepare_Town06_20261114T142115Z