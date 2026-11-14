export PATH=/usr/bin:$PATH; cd "$(dirname "$0")"
export M56_ASEL2_IO=1 M56_ASEL2_F=1 M56_NO_RENDER=1 M56_SPECTATOR=1 M56_SPAWN_TILT=1 M56_RECIPE=v6 M56_DRIVABLE=dv1 M56_CODE=D:/AI/CARLA-Funny-Moments.worktrees/m56-v13
while tasklist | grep -qi CarlaUE4; do sleep 15; done
../../../.venv-m56-native-v1/Scripts/python.exe -I -X utf8 native-f-ab.py D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_c0_partial_io_asel2fprep_20261114T122622Z/c0-partial-v5-frozen-revision.json Town13 M56-P-F01-S1 > D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_f01v11_compile2.log 2>&1; grep -a '"event": "\(FIXTURE\|ADMISSION\|SCENE_ERROR\)"\|^DONE\|^Traceback\|Error' D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/outputs/m56_f01v11_compile2.log
echo F01V11_COMPILE_END