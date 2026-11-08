#!/usr/bin/env bash
# 2026-11-08 A-SEL2: start the I/O batch as soon as the C/L/M batch (label m56_asel2_cl_t1213) has ended.
cd "$(dirname "$0")"
until grep -q ASEL2_CL_END ../../../outputs/m56_asel2_cl_t1213.stdout.txt 2>/dev/null; do sleep 60; done
while tasklist | grep -qi CarlaUE4; do sleep 15; done
bash run-asel2-io.sh "Town12:M56-P-I01-S1,M56-P-I05-S1,M56-P-I06,M56-P-O05-S1,M56-P-O06,M56-P-O07-S1 Town13:M56-P-I07-S1,M56-P-I08,M56-P-O04-S1,M56-P-I02-S2,M56-P-O08-S2"
echo CHAIN_DONE
