"""2026-11-21 addendum X: the W4c window-rule proxy (native-v21-f03-consumer-proxy.py: metrics._f_action_window :781 reverse readback on
every backward step, :795 last_retreat then an observed 0.5 s stop) applied to the v21 F03-S1 arm B frames instead of v20 B. Read-only,
rule firing only. M56_CODE=<worktree> M56_RECIPE=v6 python -I native-v22-f03-window-proxy.py [LAST_FRAME=9999]"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('w4c', HERE / 'native-v21-f03-consumer-proxy.py'); m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)  # type: ignore[union-attr]
m.B = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261120T192818Z\M56-P-F03-S1\run\episodes\M56-P-F03-S1\B')
if __name__ == '__main__':
    sys.exit(m.main(int(sys.argv[1]) if len(sys.argv) > 1 else 9999))