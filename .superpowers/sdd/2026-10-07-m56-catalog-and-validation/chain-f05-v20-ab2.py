"""2026-11-20 one-shot chain for the F05 A/B rerun under m56-v20 (addendum V, section V6: Duy "chạy tiếp f05" after the
07:26Z unclean shutdown interrupted run 20261120T070548Z before arm B started). Same checks as chain-f05-v20-ab.py, except:
  - no wait on the test PID (the PID is from before the reboot; the test output is checked instead: "134 passed");
  - allowed F05 A/B dirs before launch = {the spent v18 one, the interrupted v20 one};
  - marker m56_f05_v20_ab2_LAUNCHED / BLOCKED file m56_f05_v20_ab2_BLOCKED.txt (the first marker stays as a record);
  - room() needs commit headroom >= COMMIT_GB (32, not 25: the interrupted run went from 25.3 to 7.8 GB before the crash).
If the chain dies after the marker: a new m56_f_ab_Town12_* dir with M56-P-F05 (besides the two above) means the rerun ran.
usage: python -I chain-f05-v20-ab2.py [--check|--selftest]"""
import hashlib, importlib.util, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('c1', HERE / 'chain-f05-v20-ab.py'); c1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c1)
OUT, W = c1.OUT, c1.W
ALLOWED = ['m56_f_ab_Town12_20261118T093346Z', 'm56_f_ab_Town12_20261120T070548Z']
BLOCKED, LAUNCHED = OUT / 'm56_f05_v20_ab2_BLOCKED.txt', OUT / 'm56_f05_v20_ab2_LAUNCHED'
COMMIT_GB = '32'
c1.BLOCKED = BLOCKED  # c1.blocked() writes here


def preconditions():
    if not c1.verdict_of_tests(c1.TESTS_OUT.read_text(encoding='utf-8', errors='replace')):
        c1.blocked('v20 F05 tests did not end with a clean "N passed" line')
    env = {**os.environ, 'M56_CODE': str(c1.V20), 'M56_RECIPE': 'v6'}
    g = subprocess.run([c1.PY, '-I', '-X', 'utf8', str(HERE / 'native-f05-v20-gate.py')], capture_output=True, text=True, env=env)
    if 'F05_V20_GATE PASS' not in g.stdout:
        c1.blocked('native-f05-v20-gate.py did not print F05_V20_GATE PASS: ' + (g.stdout[-300:] or g.stderr[-300:]).replace('\n', ' '))
    if not c1.git(c1.V20, 'rev-parse', 'HEAD').startswith(c1.V20_HEAD) or c1.git(c1.V20, 'status', '--porcelain'):
        c1.blocked(f'm56-v20 is not clean at {c1.V20_HEAD}')
    rel = str(HERE.relative_to(W)).replace('\\', '/')
    dirty = c1.git(W, 'status', '--porcelain', '--', rel + '/*.py', rel + '/*.sh', c1.ADDENDUM)
    if dirty:
        c1.blocked('uncommitted tooling/addendum: ' + dirty.replace('\n', ' | '))
    if hashlib.sha256(c1.REVF.read_bytes()).hexdigest() != c1.REVF_SHA:
        c1.blocked('F05 frozen revision bytes changed')
    if LAUNCHED.exists():
        c1.blocked('the rerun launch marker exists already (one rerun only)')
    if c1.f05_dirs() != ALLOWED:
        c1.blocked(f'F05 A/B dirs are not exactly the spent v18 and the interrupted v20 ones: {c1.f05_dirs()}')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        c1.selftest(); assert sorted(ALLOWED) == ALLOWED; sys.exit(0)
    preconditions()
    if '--check' in sys.argv:
        print('PRECONDITIONS_OK'); sys.exit(0)
    prereg = (f"F part 1 3fb9865 + addenda T/U (1475e9b, 3f1cefe, c4ec86b) + V {c1.git(W, 'log', '-1', '--format=%h', '--', c1.ADDENDUM)}"
              " (v20; V6 rerun after the 20/11 infra interruption)")
    env = {**os.environ, 'M56_COMMIT_START_GB': COMMIT_GB,
           'M56_F05V_AUTHORITY_EXTRA': '; rerun: [chat] 2026-11-20 Duy "chạy tiếp f05" after run 20261120T070548Z was interrupted by an unclean shutdown before arm B (addendum V6)'}
    log = OUT / f"m56_f05vab2_r20_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    revf = str(c1.REVF).replace('\\', '/')
    with log.open('w', encoding='utf-8') as f:
        rc = subprocess.run([c1.BASH, 'run-f05-u20.sh', 'compile', revf], cwd=HERE, stdout=f, stderr=subprocess.STDOUT, env=env).returncode
    text = log.read_text(encoding='utf-8', errors='replace')
    if rc or '"status": "FROZEN"' not in text or '"status": "ADMITTED"' not in text or 'F05V_COMPILE_END' not in text:
        c1.blocked(f'compile preview (rc {rc}) is not FROZEN + ADMITTED: see {log}')
    LAUNCHED.write_text(datetime.now(timezone.utc).isoformat(timespec='seconds'), encoding='utf-8')
    with log.open('a', encoding='utf-8') as f:
        rc = subprocess.run([c1.BASH, 'run-f05-u20.sh', 'ab', revf, prereg], cwd=HERE, stdout=f, stderr=subprocess.STDOUT, env=env).returncode
    print('F05_V20_AB2_END rc', rc, log, flush=True)
