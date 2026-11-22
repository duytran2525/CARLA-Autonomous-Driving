"""Guarded scoped-pytest run for M56 (offline). Kills only its own child.

usage: python -I run-guarded.py LABEL NODE [NODE...] [--cap-gb 12] [--floor-gb 25] [--timeout-s 14400]
                                [--retain all|failed] [--resume FROM_LABEL]
Writes WS/LABEL.log (pytest -v output), WS/LABEL.collected.txt, WS/LABEL.run.json (receipt),
WS/LABEL.checkpoint.json (per-node state + source hashes), and appends progress.md.

Safe stop (status STOPPED_SAFE + checkpoint with passed/failed/remaining nodes):
  - create WS/LABEL.STOP (empty): graceful, the test now running finishes, then the runner stops;
  - write 'now' into WS/LABEL.STOP, or Ctrl-C/Ctrl-Break the runner: stop at once (the running test
    is lost and stays in 'remaining').
The pytest process TREE is killed (the venv python.exe is a launcher with a child interpreter).
A hard kill of the runner itself (TerminateProcess) cannot be caught: use the STOP file instead.
Resume: --resume FROM_LABEL runs only the nodes not yet passed in FROM's chain, under a NEW label, and
refuses if any m56/tests source hash changed. A chain is a whole-suite PASS only when every originally
collected node PASSED on identical sources (verdict_chain == CHAIN_PASSED).
--retain failed: pytest tmp_path_retention_policy=failed, a passed test's tmp dir is deleted at its
teardown (logs/receipts kept), bounding disk to the largest single test instead of the suite sum.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, signal, subprocess, time

HOME = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1')
# 2026-11-22 flag: M56_GUARDED_WORK = another worktree whose m56/ + tests/m56 are tested (m56-v23); unset = m56-v1 as before.
# Logs, venv and receipts stay in m56-v1.
WORK = Path(os.environ.get('M56_GUARDED_WORK', HOME))
WS = HOME / '.superpowers/sdd/2026-10-07-m56-catalog-and-validation'
PY = HOME / '.venv-m56-v1/Scripts/python.exe'
RECEIPTS = HOME / 'outputs/m56_offline_v1/pytest_receipts'
RESULT = re.compile(r'^(\S+::\S+) (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b')

ap = argparse.ArgumentParser()
ap.add_argument('label'); ap.add_argument('node', nargs='+')
ap.add_argument('--cap-gb', type=float, default=12); ap.add_argument('--floor-gb', type=float, default=25)
ap.add_argument('--timeout-s', type=int, default=14400)
ap.add_argument('--retain', choices=('all', 'failed'), default='all'); ap.add_argument('--resume')
a = ap.parse_args()

now = lambda: datetime.now(timezone.utc).isoformat()
out_files = {k: WS / f'{a.label}.{k}' for k in ('log', 'run.json', 'checkpoint.json', 'collected.txt')}
stop_file, base = WS / f'{a.label}.STOP', RECEIPTS / a.label
# --basetemp wipes an existing dir: never reuse a namespace or overwrite evidence.
for p in (*out_files.values(), stop_file, base):
    assert not p.exists(), f'Preserve existing evidence: {p}'
for p in (PY, WORK / 'tests/m56/pytest.ini', WORK / 'tests/m56', WORK / 'm56'):
    assert p.exists(), f'missing {p}'
assert all(n.startswith('tests/m56') and '..' not in n for n in a.node)

common = [str(PY), '-u', '-I', '-B', '-X', 'utf8', '-m', 'pytest', '-c', str(WORK / 'tests/m56/pytest.ini'),
          '--confcutdir', str(WORK / 'tests/m56')]
nodes = [str(WORK / n) for n in a.node]

def free(): return shutil.disk_usage('D:/').free
def size(p):
    n = b = 0
    for dp, _, fns in os.walk(p):
        for f in fns:
            try: b += os.stat(os.path.join(dp, f)).st_size; n += 1
            except OSError: pass
    return n, b
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(n): return n.replace(chr(92), '/').split('tests/m56/', 1)[-1]  # collect vs -v print paths differently
def progress(line):
    with open(WS / 'progress.md', 'a', encoding='utf-8', newline='\n') as s:
        s.write(line + '\n')

# Collect first so a stop can name exactly what remains. No basetemp/tests executed here.
col = subprocess.run([*common, '--collect-only', '-q', *nodes], cwd=WORK, capture_output=True, text=True)
collected = [norm(l.strip()) for l in col.stdout.splitlines() if '::' in l]
assert col.returncode == 0 and collected, f'collection failed exit={col.returncode}: {col.stdout[-2000:]}'

source = {p.relative_to(WORK).as_posix(): sha(p) for f in ('m56', 'tests/m56')
          for p in sorted((WORK / f).iterdir()) if p.is_file() and p.suffix in ('.py', '.ini')}
chain, chain_passed, chain_failed, original = [a.label], [], [], collected
if a.resume:
    prior = json.loads((WS / f'{a.resume}.checkpoint.json').read_text(encoding='utf-8'))
    assert prior['source_sha256'] == source, 'sources changed since the resumed run: start a fresh whole suite'
    original = prior.get('original') or (WS / f'{a.resume}.collected.txt').read_text(encoding='utf-8').split()
    assert set(collected) == set(original), 'collection differs from the resumed run'
    chain = [*prior.get('chain', [a.resume]), a.label]
    chain_passed = prior.get('chain_passed') or prior['passed']
    chain_failed = prior.get('chain_failed') or prior['failed']  # never retried: deterministic tests, no flake masking
    collected = [n for n in original if n not in set(chain_passed) and n not in {f.rsplit(' ', 1)[0] for f in chain_failed}]
    assert collected, 'nothing left to resume'
    nodes = [str(WORK / 'tests/m56' / n) for n in collected]
out_files['collected.txt'].write_text('\n'.join(collected) + '\n', encoding='utf-8')
retain = ['-o', 'tmp_path_retention_policy=failed'] if a.retain == 'failed' else []
if len(nodes) > 50:  # a resumed node list can exceed the Windows command-line limit (WinError 206): pytest @argsfile
    argsfile = WS / f'{a.label}.args.txt'
    argsfile.write_bytes(('\n'.join(nodes) + '\n').encode('utf-8'))
    nodes = ['@' + str(argsfile)]
cmd = [*common, *retain, '--basetemp', str(base), *nodes, '-v']
cap, floor = int(a.cap_gb * 1024**3), int(a.floor_gb * 1024**3)
r = {'label': a.label, 'node': a.node, 'resume': a.resume, 'chain': chain, 'retain': a.retain, 'command': cmd, 'cwd': str(WORK), 'basetemp': str(base),
     'budget': {'namespace_cap_bytes': cap, 'disk_free_floor_bytes': floor, 'timeout_s': a.timeout_s},
     'collected': len(collected), 'stop_file': str(stop_file),
     'start_utc': now(), 'disk_free_start': free(), 'peak_bytes': 0, 'peak_files': 0}
assert r['disk_free_start'] > floor + cap, 'insufficient free space for budget'
progress(f"Start: {a.label} UTC={r['start_utc']} runner=run-guarded.py collected={len(collected)} budget cap={a.cap_gb}GB "
         f"floor={a.floor_gb}GB timeout={a.timeout_s}s disk_free={r['disk_free_start']} stop_file={stop_file.name} "
         f"command={' '.join(cmd)}")

requested = []
for s in ('SIGINT', 'SIGBREAK'):
    if hasattr(signal, s):
        signal.signal(getattr(signal, s), lambda *_: requested.append('SIGNAL'))

def results():
    try:
        return sum(1 for l in out_files['log'].read_bytes().decode('utf-8', 'replace').splitlines() if RESULT.match(l.strip()))
    except OSError:
        return 0
def kill_tree(p):  # the venv python.exe launcher spawns the real interpreter: kill the whole tree
    subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True)
    try: p.wait(timeout=60)
    except subprocess.TimeoutExpired: p.kill(); p.wait()

t0 = time.monotonic(); status = None; last_size = 0.0; graceful_at = None
with open(out_files['log'], 'wb') as out:
    proc = subprocess.Popen(cmd, cwd=WORK, stdout=out, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    while proc.poll() is None:
        time.sleep(5)
        now_req = bool(requested) or (stop_file.exists() and 'now' in stop_file.read_text(errors='replace').lower())
        if stop_file.exists() and graceful_at is None and not now_req:
            graceful_at = results()
            progress(f"Stop requested: {a.label} UTC={now()} graceful (the running test finishes first)")
        if now_req or (graceful_at is not None and results() > graceful_at):
            status = 'STOPPED_SAFE'
        elif time.monotonic() - last_size >= 30:
            last_size = time.monotonic()
            n, b = size(base) if base.exists() else (0, 0)
            r['peak_bytes'], r['peak_files'] = max(r['peak_bytes'], b), max(r['peak_files'], n)
            if b > cap: status = 'BLOCKED_STORAGE_NAMESPACE_CAP'
            elif free() < floor: status = 'BLOCKED_STORAGE_DISK_FLOOR'
            elif time.monotonic() - t0 > a.timeout_s: status = 'TIMEOUT'
        if status:
            kill_tree(proc); break
code = proc.returncode
r.update(end_utc=now(), walltime_s=round(time.monotonic() - t0, 2), exit=code, disk_free_end=free())
r['final_files'], r['final_bytes'] = size(base) if base.exists() else (0, 0)
r['peak_bytes'] = max(r['peak_bytes'], r['final_bytes'])
text = out_files['log'].read_bytes().decode('utf-8', 'replace')
tail = text.strip().splitlines()
r['summary'] = tail[-1] if tail else ''
r['status'] = status or {0: 'PYTEST_PASSED', 1: 'PYTEST_TESTS_FAILED'}.get(code, f'PYTEST_EXIT_{code}_NOT_A_PRODUCT_RESULT')

done = {}
for line in text.splitlines():
    m = RESULT.match(line.strip())
    if m:
        done[norm(m.group(1))] = m.group(2)
ok = {'PASSED', 'SKIPPED', 'XFAIL'}
checkpoint = {'label': a.label, 'status': r['status'], 'utc': r['end_utc'], 'exit': code,
              'collected': len(collected), 'passed': sorted(k for k, v in done.items() if v in ok),
              'failed': sorted(f'{k} {v}' for k, v in done.items() if v not in ok),
              'remaining': [n for n in collected if n not in done],
              'log_sha256': sha(out_files['log']), 'source_sha256': source, 'basetemp': str(base),
              'original': original, 'chain': chain,
              'chain_passed': sorted({*chain_passed, *(k for k, v in done.items() if v in ok)}),
              'chain_failed': sorted({*chain_failed, *(f'{k} {v}' for k, v in done.items() if v not in ok)}),
              'note': ('A stopped run is partial; continue with --resume LABEL (new label, identical sources). '
                       'Whole-suite PASS only when verdict_chain == CHAIN_PASSED.')}
checkpoint['verdict_chain'] = ('CHAIN_PASSED' if not checkpoint['chain_failed'] and set(checkpoint['chain_passed']) == set(original)
                               else 'CHAIN_INCOMPLETE')
out_files['checkpoint.json'].write_text(json.dumps(checkpoint, indent=1), encoding='utf-8')
r['checkpoint'] = {k: len(checkpoint[k]) for k in ('passed', 'failed', 'remaining')}
r['verdict_chain'] = checkpoint['verdict_chain']
out_files['run.json'].write_text(json.dumps(r, indent=1), encoding='utf-8')
progress(f"Test: {a.label} actual_exit={code} status={r['status']} UTC={r['end_utc']} walltime={r['walltime_s']}s "
         f"peak_bytes={r['peak_bytes']} disk_free_end={r['disk_free_end']} checkpoint={r['checkpoint']} "
         f"chain={'+'.join(chain)} verdict_chain={r['verdict_chain']} "
         f"summary=[{r['summary']}] log={out_files['log'].name} checkpoint_file={out_files['checkpoint.json'].name}")
print(json.dumps({k: r[k] for k in ('status', 'exit', 'walltime_s', 'summary', 'peak_bytes', 'checkpoint')}))
