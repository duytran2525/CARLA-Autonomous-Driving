"""Offline pair re-evaluation, ONE process per scene (a kill loses one scene; no cache spans scenes).
python -I native-pair-per-scene.py LOG.jsonl SCENE_DIR [...]   (env M56_CODE / M56_RECIPE / M56_NO_RENDER as for native-v6-pair.py)
Appends one JSON line per scene: exit, walltime, the evaluating interpreter's own peak working set / commit (Windows; measured
inside it, because a venv python.exe is only a launcher), the pair tool's last status line."""
import json, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHILD = r'''
import atexit, ctypes, runpy, sys
from ctypes import wintypes
class PMC(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [(n, ctypes.c_size_t) for n in (
        'PeakWorkingSetSize', 'WorkingSetSize', 'a', 'b', 'c', 'd', 'PagefileUsage', 'PeakPagefileUsage')]
def peak():
    c = PMC(); c.cb = ctypes.sizeof(c)
    k, m = ctypes.windll.kernel32, ctypes.windll.psapi
    k.GetCurrentProcess.restype = wintypes.HANDLE
    m.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD)
    m.GetProcessMemoryInfo(k.GetCurrentProcess(), ctypes.byref(c), c.cb)
    print('PEAK_GB', round(c.PeakWorkingSetSize / 2 ** 30, 2), round(c.PeakPagefileUsage / 2 ** 30, 2), flush=True)
atexit.register(peak)
sys.argv = sys.argv[1:]; sys.path.insert(0, sys.argv[0].rsplit('\\', 1)[0])
runpy.run_path(sys.argv[0], run_name='__main__')
'''

log = Path(sys.argv[1])
for sd in sys.argv[2:]:
    t0 = time.time()
    p = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-c', CHILD, str(HERE / 'native-v6-pair.py'), sd], cwd=HERE,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = p.stdout + p.stderr
    status = [l for l in out.splitlines() if l.startswith('{"scene"')]
    pk = [l.split()[1:] for l in out.splitlines() if l.startswith('PEAK_GB')]
    row = {'scene_dir': sd, 'exit': p.returncode, 'walltime_s': round(time.time() - t0),
           'peak_ws_gb': float(pk[-1][0]) if pk else None, 'peak_commit_gb': float(pk[-1][1]) if pk else None,
           'result': json.loads(status[-1]) if status else None, 'tail': None if status else out[-1500:]}
    with log.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row) + '\n')
    print(json.dumps(row)[:400], flush=True)
