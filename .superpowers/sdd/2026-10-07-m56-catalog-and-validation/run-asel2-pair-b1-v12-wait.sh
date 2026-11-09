#!/usr/bin/env bash
cd "$(dirname "$0")"
until grep -q PAIR_B1_END ../../../outputs/m56_asel2_pair_b1.stdout.txt 2>/dev/null; do sleep 30; done
bash run-asel2-pair-b1-v12.sh
