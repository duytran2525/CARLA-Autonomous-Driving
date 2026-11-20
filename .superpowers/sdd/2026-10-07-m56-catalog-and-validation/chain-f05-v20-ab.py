"""2026-11-20 one-shot chain for the single F05 A/B under m56-v20 (P5; addendum V, Duy's choice 20/11). Claude under Duy's delegation.
Preconditions, checked in this order; any miss writes outputs/m56_f05_v20_ab_BLOCKED.txt and stops (nothing runs):
  1. the v20 F05 test run (pid TESTS_PID, stdout TESTS_OUT) has ended and its last line is "N passed ..." with no failed/error;
  2. native-f05-v20-gate.py (real v18 arm B replayed under v20) prints F05_V20_GATE PASS (run here, seconds);
  3. m56-v20 is at 22c57cf with a clean tree; the tooling files (*.py, *.sh of this dir) and addendum V have no uncommitted
     change; the frozen revision has sha256 REVF_SHA;
  4. P5: outputs/m56_f05_v20_ab_LAUNCHED does not exist AND exactly one outputs/m56_f_ab_Town12_* dir holds M56-P-F05 (the
     spent v18 one, 20261118T093346Z).
Then run-f05-u20.sh compile (admission preview, no P5): its log must show FIXTURE FROZEN and ADMISSION ADMITTED, else BLOCKED.
Then the marker is written and run-f05-u20.sh ab runs (room() waits: no CARLA, commit >= 25 GB, C >= 10, D >= 80, E >= 150 GB).
The marker is written BEFORE room() waits: if the chain dies while waiting, look for a new outputs/m56_f_ab_Town12_* dir holding
M56-P-F05 before treating P5 as spent (no new dir = not spent: delete the marker). usage: python -I chain-f05-v20-ab.py [--check|--selftest]"""
import hashlib, re, subprocess, sys, time, os
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = HERE.parents[2]
OUT = W / 'outputs'
TESTS_PID, TESTS_OUT = 23628, OUT / 'm56_v20_f05tests_20261120b.stdout.txt'
REVF = OUT / 'm56_c0_partial_io_asel2f05prep_20261118T092923Z/c0-partial-v5-frozen-revision.json'
REVF_SHA = 'e1b578183e4b10007cbbcf3d4101e7df35beb49d9b19297905a0bf0a2ee5fcf3'
V20, V20_HEAD = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v20'), '22c57cf'
SPENT_V18 = 'm56_f_ab_Town12_20261118T093346Z'
BLOCKED, LAUNCHED = OUT / 'm56_f05_v20_ab_BLOCKED.txt', OUT / 'm56_f05_v20_ab_LAUNCHED'
ADDENDUM = 'docs/m56/PREREG_M56_F05_ADDENDUM_V_20261120.md'
BASH, PY = 'D:/Git/bin/bash.exe', str(W / '.venv-m56-native-v1/Scripts/python.exe')


def alive(pid):
    return str(pid) in subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True).stdout


def git(cwd, *a):
    return subprocess.run(['git', '-C', str(cwd), *a], capture_output=True, text=True).stdout.strip()


def blocked(why):
    BLOCKED.write_text(f'{datetime.now(timezone.utc).isoformat(timespec="seconds")} {why}\n', encoding='utf-8')
    print('BLOCKED', why, flush=True); sys.exit(3)


def verdict_of_tests(text):
    last = [l for l in text.splitlines() if l.strip()][-1:] or ['']
    return bool(re.match(r'^=*\s*\d+ passed\b', last[0])) and not re.search(r'failed|error', last[0], re.I)


def f05_dirs():
    return sorted(d.name for d in OUT.glob('m56_f_ab_Town12_*') if (d / 'M56-P-F05').exists())


def preconditions():
    if not verdict_of_tests(TESTS_OUT.read_text(encoding='utf-8', errors='replace')):
        blocked('v20 F05 tests did not end with a clean "N passed" line')
    env = {**os.environ, 'M56_CODE': str(V20), 'M56_RECIPE': 'v6'}
    g = subprocess.run([PY, '-I', '-X', 'utf8', str(HERE / 'native-f05-v20-gate.py')], capture_output=True, text=True, env=env)
    if 'F05_V20_GATE PASS' not in g.stdout:
        blocked('native-f05-v20-gate.py did not print F05_V20_GATE PASS: ' + (g.stdout[-300:] or g.stderr[-300:]).replace('\n', ' '))
    if not git(V20, 'rev-parse', 'HEAD').startswith(V20_HEAD) or git(V20, 'status', '--porcelain'):
        blocked(f'm56-v20 is not clean at {V20_HEAD}')
    dirty = git(W, 'status', '--porcelain', '--', str(HERE.relative_to(W)).replace('\\', '/') + '/*.py',
                str(HERE.relative_to(W)).replace('\\', '/') + '/*.sh', ADDENDUM)
    if dirty:
        blocked('uncommitted tooling/addendum: ' + dirty.replace('\n', ' | '))
    if hashlib.sha256(REVF.read_bytes()).hexdigest() != REVF_SHA:
        blocked('F05 frozen revision bytes changed')
    if LAUNCHED.exists():
        blocked('an A/B launch marker exists already (P5: one A/B per scene per version)')
    if f05_dirs() != [SPENT_V18]:
        blocked(f'F05 A/B dirs are not exactly the spent v18 one: {f05_dirs()}')


def selftest():
    assert verdict_of_tests('....\n120 passed, 900 deselected in 1234.5s (0:20:34)\n')
    assert not verdict_of_tests('..\n1 failed, 119 passed in 9s\n') and not verdict_of_tests('...  [14%]\n') and not verdict_of_tests('')
    assert not verdict_of_tests('3 passed, 1 error in 9s\n')
    print('SELFTEST_OK')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest(); sys.exit(0)
    while alive(TESTS_PID):
        time.sleep(60)
    preconditions()
    if '--check' in sys.argv:
        print('PRECONDITIONS_OK'); sys.exit(0)
    prereg = f"F part 1 3fb9865 + addenda T/U (1475e9b, 3f1cefe, c4ec86b) + V {git(W, 'log', '-1', '--format=%h', '--', ADDENDUM)} (v20)"
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    log = OUT / f'm56_f05vab_r20_{stamp}.log'
    revf = str(REVF).replace('\\', '/')
    with log.open('w', encoding='utf-8') as f:
        rc = subprocess.run([BASH, 'run-f05-u20.sh', 'compile', revf], cwd=HERE, stdout=f, stderr=subprocess.STDOUT).returncode
    text = log.read_text(encoding='utf-8', errors='replace')
    if rc or '"status": "FROZEN"' not in text or '"status": "ADMITTED"' not in text or 'F05V_COMPILE_END' not in text:
        blocked(f'compile preview (rc {rc}) is not FROZEN + ADMITTED: see {log}')
    LAUNCHED.write_text(datetime.now(timezone.utc).isoformat(timespec='seconds'), encoding='utf-8')
    with log.open('a', encoding='utf-8') as f:
        rc = subprocess.run([BASH, 'run-f05-u20.sh', 'ab', revf, prereg], cwd=HERE, stdout=f, stderr=subprocess.STDOUT).returncode
    print('F05_V20_AB_END rc', rc, log, flush=True)
