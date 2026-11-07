"""Launch a command fully detached (same flags as start-guarded.ps1): no console, own process group, broken away from any
job, orphaned at once. A Claude Code background shell can be reaped (2026-11-07, memory pressure); a native A/B is a P5
single rerun and must survive that.
python -I start-detached.py LABEL CMD [ARG ...]   -> outputs/LABEL.stdout.txt / .stderr.txt (never overwritten), prints PID"""
import subprocess, sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
label, cmd = sys.argv[1], sys.argv[2:]
flags = 0x01000000 | 0x00000008 | 0x00000200  # CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
with open(OUT / f'{label}.stdout.txt', 'xb') as out, open(OUT / f'{label}.stderr.txt', 'xb') as err:
    p = subprocess.Popen(cmd, cwd=Path(__file__).resolve().parent, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                         creationflags=flags, close_fds=True)
print(f'STARTED label={label} pid={p.pid} stdout={OUT / (label + ".stdout.txt")}')
