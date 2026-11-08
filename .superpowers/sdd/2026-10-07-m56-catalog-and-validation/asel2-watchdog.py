"""A-SEL2 watchdog + checkpoint (2026-11-08). Runs detached; every INTERVAL s:
1. CHECKPOINT: parse every A-SEL2 batch log dir (outputs/m56_asel2_cl*_*/, m56_asel2_io_*/) into per-scene states
   (PREPARED / BLOCKED_FIXTURE / SCENE_ERROR / AB_STARTED / AB_DONE + pair status) and write
   outputs/m56_asel2_checkpoint.json atomically (tmp + os.replace): a resume never has to guess.
2. HEALTH of the running native job (python native-*.py + own CarlaUE4 on 2610):
   OK   = new output files or log lines within STALL_S;
   SLOW = no new output but the job's or CARLA's CPU time still increases (progressing; e.g. the dv1 raster);
   HUNG = no new output AND no CPU increase for HUNG_S. Then: py-spy stack dump to outputs/, record the event, and
   kill ONLY our own tree (the python job and the CarlaUE4 bound to -carla-rpc-port=2610). Never restarts anything:
   spec 4 (infrastructure uncertainty -> no automatic re-execution); the batch script moves on, resume decides.
3. Every state change is appended to outputs/m56_asel2_watchdog.jsonl (append-only).
usage: python -I asel2-watchdog.py [INTERVAL_S=300] [STALL_S=1800] [HUNG_S=1800]"""
import glob, json, os, re, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
INTERVAL, STALL_S, HUNG_S = (int(x) for x in (sys.argv[1:4] + ['300', '1800', '1800'][len(sys.argv[1:4]):]))
PYSPY = Path(os.environ.get('USERPROFILE', 'C:/Users/ADMIN')) / '.local' / 'bin' / 'py-spy.exe'
now = lambda: datetime.now(timezone.utc).isoformat(timespec='seconds')


def procs():
    """[(pid, cpu_s, cmdline)] of our native jobs and our CarlaUE4 (PowerShell CIM, no third-party module)."""
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*native-*.py*' -or "
          "$_.CommandLine -like '*carla-rpc-port=2610*' } | ForEach-Object { $p = Get-Process -Id $_.ProcessId "
          "-ErrorAction SilentlyContinue; '{0}|{1}|{2}' -f $_.ProcessId, $(if ($p) { $p.CPU } else { 0 }), $_.CommandLine }")
    r = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True, timeout=120)
    out = []
    for line in r.stdout.splitlines():
        parts = line.split('|', 2)
        if len(parts) == 3 and parts[0].strip().isdigit():
            try:
                out.append((int(parts[0]), float(parts[1] or 0), parts[2]))
            except ValueError:
                pass
    return out


def scenes():
    st = {}
    for d in sorted(glob.glob(str(OUT / 'm56_asel2_cl*_2*')) + glob.glob(str(OUT / 'm56_asel2_io_2*'))):
        for f in sorted(glob.glob(d + '/*.log')):
            name = Path(f).name
            for line in open(f, encoding='utf-8', errors='replace'):
                m = re.search(r'"event": "SCENE", "scene": "([^"]+)", "status": "([A-Z_]+)", "reason": ("[^"]*"|null)', line)
                if m:
                    st.setdefault(m.group(1), {})['prepare'] = (m.group(2), m.group(3).strip('"'), d)
                m = re.search(r'"event": "SCENE_ERROR", "scene": "([^"]+)"', line)
                if m:
                    st.setdefault(m.group(1), {})[('ab' if name.startswith(('ab-', 'compile-')) else 'prepare') + '_error'] = d
                if name.startswith('ab-'):
                    for s in re.findall(r'"scene": "(M56-P-[^"]+)"', line):
                        st.setdefault(s, {}).setdefault('ab', 'AB_STARTED')
        stdout = OUT / (Path(d).name + '.stdout.txt')
        for f in [*glob.glob(d + '/pair-*.log'), str(stdout)]:
            if not os.path.exists(f):
                continue
            for line in open(f, encoding='utf-8', errors='replace'):
                for s, status in re.findall(r'"scene": "(M56-P-[^"]+)", "status": "([A-Z_]+)"', line):
                    st.setdefault(s, {})['ab'] = 'AB_DONE'; st[s]['pair'] = status
    return st


def newest_output_age():
    """Age (s) of the newest file in the 3 newest A-SEL2 batch dirs and the 3 newest prepare / A-B / io run dirs
    (outputs/ holds ~2.5 M files: never walk all of it)."""
    best = 0.
    tops = []
    for pat in ('m56_asel2_cl*_2*', 'm56_asel2_io_2*', 'm56_v2_prepare_Town*', 'm56_v2_ab_Town*', 'm56_io_ab_*', 'm56_io_prepare_*'):
        ds = sorted(glob.glob(str(OUT / pat)), key=lambda d: os.path.getmtime(d), reverse=True)[:3]
        tops += ds
    for d in tops:
        for root, _, files in os.walk(d):
            for f in files:
                try:
                    best = max(best, os.path.getmtime(os.path.join(root, f)))
                except OSError:
                    pass
    for f in glob.glob(str(OUT / 'm56_asel2_*.stdout.txt')):
        if 'watchdog' not in f:  # never count the watchdog's own files as job progress
            best = max(best, os.path.getmtime(f))
    return time.time() - best if best else None


def write_json(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=1, default=str), encoding='utf-8')
    os.replace(tmp, path)


def event(**k):
    with open(OUT / 'm56_asel2_watchdog.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps({'t': now(), **k}, default=str) + '\n')


last_cpu, flat_since, last_state = {}, None, None
event(event='WATCHDOG_START', interval_s=INTERVAL, stall_s=STALL_S, hung_s=HUNG_S, pid=os.getpid())
while True:
    try:
        ps = procs()
        jobs = [p for p in ps if '-X utf8 native-' in p[2]]  # our M56 native jobs only (venv launcher + interpreter)
        carla = [p for p in ps if 'carla-rpc-port=2610' in p[2]]
        cpu_now = {p[0]: p[1] for p in jobs + carla}
        grew = any(cpu_now.get(pid, 0) > last_cpu.get(pid, -1) + 1. for pid in cpu_now)
        age = newest_output_age()
        if not jobs:
            state, flat_since = 'IDLE', None
        elif age is not None and age < STALL_S:
            state, flat_since = 'OK', None
        elif grew:
            state, flat_since = 'SLOW', None
        else:
            flat_since = flat_since or time.time()
            state = 'HUNG' if time.time() - flat_since >= HUNG_S else 'STALLED'
        ck = {'t': now(), 'state': state, 'newest_output_age_s': None if age is None else round(age),
              'jobs': [{'pid': p[0], 'cpu_s': round(p[1], 1), 'cmd': p[2][:300]} for p in jobs],
              'carla': [{'pid': p[0], 'cpu_s': round(p[1], 1)} for p in carla], 'scenes': scenes()}
        write_json(OUT / 'm56_asel2_checkpoint.json', ck)
        if state != last_state:
            event(event='STATE', state=state, newest_output_age_s=ck['newest_output_age_s'], jobs=[j['cmd'][:160] for j in ck['jobs']])
            last_state = state
        if state == 'HUNG':
            for p in jobs:
                dump = OUT / f"m56_asel2_hung_{p[0]}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.txt"
                if PYSPY.exists():
                    r = subprocess.run([str(PYSPY), 'dump', '--pid', str(p[0])], capture_output=True, text=True, timeout=120)
                    dump.write_text(r.stdout + r.stderr, encoding='utf-8')
            for p in jobs + carla:  # own tree only: native-*.py of this worktree and the CarlaUE4 on 2610
                subprocess.run(['taskkill', '/PID', str(p[0]), '/T', '/F'], capture_output=True)
            event(event='HUNG_KILLED', pids=[p[0] for p in jobs + carla], note='no automatic re-execution (spec 4); resume decides')
            flat_since, last_state = None, 'KILLED'
        last_cpu = cpu_now
    except Exception as e:  # the watchdog never dies on a transient error
        event(event='WATCHDOG_ERROR', error=repr(e)[:300])
    time.sleep(INTERVAL)
