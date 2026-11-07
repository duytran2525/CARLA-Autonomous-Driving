"""Offline pair re-evaluation, ONE process per scene (a kill loses one scene; no cache spans scenes).
python -I native-pair-per-scene.py LOG.jsonl SCENE_DIR [...]   (env M56_CODE / M56_RECIPE / M56_NO_RENDER as for native-v6-pair.py)
Appends one JSON line per scene: exit, walltime, the evaluating interpreter's own peak working set / commit (Windows; measured
inside it, because a venv python.exe is only a launcher), the pair tool's last status line.
Safe stop: create LOG.STOP (empty = after the running scene; text 'now' = at once), exit 3 + a STOPPED_SAFE line.
Resume: the same command again; scenes already done in LOG are skipped. Delete LOG.STOP before resuming."""
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

log = Path(sys.argv[1]); STOP = Path(str(log) + '.STOP')


def stop_mode():
    """LOG.STOP absent: run; empty: stop after the running scene; 'now': stop at once (the running scene is redone on resume)."""
    try:
        return 'now' if STOP.read_text(encoding='utf-8').strip() == 'now' else 'graceful'
    except FileNotFoundError:
        return None


def record(row):
    with log.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row) + '\n')
    print(json.dumps(row)[:400], flush=True)


# Checkpoint = the log itself: a scene with exit 0 and a result line is done; resume = run the same command again.
done = {r['scene_dir'] for r in map(json.loads, log.read_text(encoding='utf-8').splitlines() if log.exists() else ())
        if r.get('exit') == 0 and r.get('result')}
for sd in sys.argv[2:]:
    if sd in done:
        print(f'SKIP done: {sd}', flush=True); continue
    if stop_mode():
        record({'event': 'STOPPED_SAFE', 'mode': 'graceful', 'next': sd, 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
        sys.exit(3)
    t0, out_file = time.time(), log.parent / f'{log.stem}.{Path(sd).name}.out'
    with out_file.open('w', encoding='utf-8') as out:
        p = subprocess.Popen([sys.executable, '-I', '-X', 'utf8', '-c', CHILD, str(HERE / 'native-v6-pair.py'), sd], cwd=HERE,
                             stdout=out, stderr=subprocess.STDOUT)
        while p.poll() is None:
            if stop_mode() == 'now':  # tree kill: the venv python.exe is a launcher with the real interpreter as child
                subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True); p.wait()
                record({'event': 'STOPPED_SAFE', 'mode': 'now', 'interrupted': sd, 'note': 'scene not done; redone on resume',
                        'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
                sys.exit(3)
            time.sleep(2)
    text = out_file.read_text(encoding='utf-8', errors='replace')
    status = [l for l in text.splitlines() if l.startswith('{"scene"')]
    pk = [l.split()[1:] for l in text.splitlines() if l.startswith('PEAK_GB')]
    record({'scene_dir': sd, 'exit': p.returncode, 'walltime_s': round(time.time() - t0),
            'peak_ws_gb': float(pk[-1][0]) if pk else None, 'peak_commit_gb': float(pk[-1][1]) if pk else None,
            'result': json.loads(status[-1]) if status else None, 'tail': None if status else text[-1500:]})
