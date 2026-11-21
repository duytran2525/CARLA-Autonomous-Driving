"""2026-11-22 chain for addendum Y: the single F03-S1 A/B under m56-v23 (Duy [chat] 22/11 "làm tiếp", then chose "v23 hill-start
(Recommended)"). One CARLA. Before anything starts (any miss -> outputs/m56_v23_ab_BLOCKED.txt, nothing runs):
  1. the three v23 test groups (outputs/m56_v23_tests_g{1,2,3}.stdout.txt, 463 selected tests) ended with "N passed", no failed/error,
     and the N sum to 463;
  2. real-data gates under v23, run here: native-v23-f03-hold-gate.py hold prints V23_F03_HOLD_GATE PASS and
     native-v22-f03-forward-gate.py not_blocked prints V22_F03_FORWARD_GATE PASS; recorded files: hold gate (v23) and its v22 negative
     control PASS, forward gate (v23) PASS, full A5 replay gate under v23 ends F03_REPLAY_PASS, admit proxy on v22 B ADMIT_PROXY PASS;
  3. m56-v23 clean at V23_HEAD; tooling *.py/*.sh and addendum Y committed; the kit has the M56_KIT_ADMIT_STOP_BOUND flag; the F03 frozen
     revision has its sha256;
  4. P5: no marker outputs/m56_v23_ab_F03_LAUNCHED, and the A/B dirs holding F03-S1 are exactly the four spent ones.
Then compile preview (FROZEN + ADMITTED, else BLOCKED), marker (written BEFORE room() waits: a new m56_f_ab_Town12_* dir holding the
scene = that A/B ran), the single A/B with M56_KIT_ADMIT_STOP_BOUND=1 + pairs under v23, v22.
usage: python -I chain-v23-ab.py [--check|--selftest]"""
import hashlib, importlib.util, os, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('c1', HERE / 'chain-f05-v20-ab.py'); c1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c1)
OUT, W, PY, BASH = c1.OUT, c1.W, c1.PY, c1.BASH
V23 = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v23')
V23_HEAD = '321ee7f'
ADDENDUM = 'docs/m56/PREREG_M56_V23_ADDENDUM_Y_20261122.md'
BLOCKED = OUT / 'm56_v23_ab_BLOCKED.txt'
c1.BLOCKED = BLOCKED
MARKER = OUT / 'm56_v23_ab_F03_LAUNCHED'
GROUPS = [OUT / f'm56_v23_tests_g{i}.stdout.txt' for i in (1, 2, 3)]
EXPECTED_TESTS = 463
RECORDED = {OUT / 'm56_v23_hold_gate_final.stdout.txt': 'V23_F03_HOLD_GATE PASS',
            OUT / 'm56_v23_hold_gate_negcontrol_v22.stdout.txt': 'V23_F03_HOLD_GATE PASS',
            OUT / 'm56_v23_forward_gate_final.stdout.txt': 'V22_F03_FORWARD_GATE PASS',
            OUT / 'm56_v23_admit_proxy_v22B.stdout.txt': 'ADMIT_PROXY PASS'}
REPLAY = OUT / 'm56_f03_gate_v23_full.stdout.txt'
KIT, KIT_FLAG = HERE / 'native_v2_kit.py', "os.environ.get('M56_KIT_ADMIT_STOP_BOUND') == '1'"
SCENE, REVF = 'M56-P-F03-S1', OUT / 'm56_c0_partial_io_asel2f03prep_20261118T181450Z/c0-partial-v5-frozen-revision.json'
REVF_SHA = 'fd624362f51f74f28f048bf805441c6dbd560f8a8be9ff5a434c84922be298b0'
SPENT = ['m56_f_ab_Town12_20261118T192541Z', 'm56_f_ab_Town12_20261119T191948Z', 'm56_f_ab_Town12_20261120T192818Z',
         'm56_f_ab_Town12_20261121T155336Z']
PREREG = 'F part 2 c9ba62a+fb44b89, addendum A 780e8c2 + A5/A6 + W + X + Y {y} (v23)'


def passed_count(text):
    last = [l for l in text.splitlines() if l.strip()][-1:] or ['']
    m = re.match(r'^=*\s*(\d+) passed\b', last[0])
    return int(m.group(1)) if m and not re.search(r'failed|error', last[0], re.I) else None


def tests_ok(texts):
    counts = [passed_count(t) for t in texts]
    return None not in counts and sum(counts) == EXPECTED_TESTS


def tests_running():
    r = subprocess.run(['powershell', '-NoProfile', '-Command',
                        "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*pyt-v23*' }).Count"],
                       capture_output=True, text=True).stdout.strip()
    return r not in ('', '0')


def dirs():
    return sorted(d.name for d in OUT.glob('m56_f_ab_Town12_*') if (d / SCENE).exists())


def gate(script, arg, want):
    env = {**os.environ, 'M56_CODE': str(V23), 'M56_RECIPE': 'v6'}
    g = subprocess.run([PY, '-I', '-X', 'utf8', str(HERE / script), arg], capture_output=True, text=True, env=env)
    if want not in g.stdout:
        c1.blocked(f'{script} {arg} under v23: ' + (g.stdout[-300:] or g.stderr[-300:]).replace('\n', ' '))


def preconditions():
    if tests_running():
        c1.blocked('a v23 pytest group is still running')
    if not tests_ok([g.read_text(encoding='utf-8', errors='replace') for g in GROUPS]):
        c1.blocked(f'v23 test groups: not all "N passed" with a sum of {EXPECTED_TESTS}')
    gate('native-v23-f03-hold-gate.py', 'hold', 'V23_F03_HOLD_GATE PASS')
    gate('native-v22-f03-forward-gate.py', 'not_blocked', 'V22_F03_FORWARD_GATE PASS')
    for path, want in RECORDED.items():
        if want not in path.read_text(encoding='utf-8', errors='replace'):
            c1.blocked(f'recorded gate {path.name} is not {want}')
    if not REPLAY.read_text(encoding='utf-8', errors='replace').rstrip().endswith('F03_REPLAY_PASS'):
        c1.blocked('full F03 replay gate under v23 is not F03_REPLAY_PASS')
    if not c1.git(V23, 'rev-parse', 'HEAD').startswith(V23_HEAD) or c1.git(V23, 'status', '--porcelain'):
        c1.blocked(f'm56-v23 is not clean at {V23_HEAD}')
    rel = str(HERE.relative_to(W)).replace('\\', '/')
    dirty = c1.git(W, 'status', '--porcelain', '--', rel + '/*.py', rel + '/*.sh', ADDENDUM)
    if dirty:
        c1.blocked('uncommitted tooling/addendum: ' + dirty.replace('\n', ' | '))
    if KIT_FLAG not in KIT.read_text(encoding='utf-8'):
        c1.blocked('native_v2_kit.py has no M56_KIT_ADMIT_STOP_BOUND flag')
    if hashlib.sha256(REVF.read_bytes()).hexdigest() != REVF_SHA:
        c1.blocked('F03 frozen revision bytes changed')
    if MARKER.exists():
        c1.blocked('a v23 launch marker exists already (P5)')
    if dirs() != SPENT:
        c1.blocked(f'F03-S1 A/B dirs are not exactly the spent ones: {dirs()}')


def run_scene():
    revf = str(REVF).replace('\\', '/')
    log = OUT / f"m56_v23ab_chain_F03_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    env = {**os.environ, 'M56_COMMIT_START_GB': '32', 'M56_KIT_ADMIT_STOP_BOUND': '1'}
    with log.open('w', encoding='utf-8') as f:
        rc = subprocess.run([BASH, 'run-v23-ab.sh', 'F03', 'compile', revf], cwd=HERE, stdout=f, stderr=subprocess.STDOUT, env=env).returncode
    text = log.read_text(encoding='utf-8', errors='replace')
    if rc or '"status": "FROZEN"' not in text or '"status": "ADMITTED"' not in text or 'V23_COMPILE_END' not in text:
        c1.blocked(f'F03: compile preview (rc {rc}) is not FROZEN + ADMITTED: see {log}')
    MARKER.write_text(datetime.now(timezone.utc).isoformat(timespec='seconds'), encoding='utf-8')
    prereg = PREREG.format(y=c1.git(W, 'log', '-1', '--format=%h', '--', ADDENDUM))
    with log.open('a', encoding='utf-8') as f:
        rc = subprocess.run([BASH, 'run-v23-ab.sh', 'F03', 'ab', revf, prereg], cwd=HERE, stdout=f, stderr=subprocess.STDOUT, env=env).returncode
    print(f'V23_F03_AB_END rc', rc, log, flush=True)


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        ok = 'x\n120 passed, 900 deselected in 1.5s (0:00:01)\n'
        assert passed_count(ok) == 120 and passed_count('1 failed, 3 passed in 1s') is None and passed_count('..  [14%]') is None
        assert passed_count('3 passed, 1 error in 9s') is None and passed_count('') is None
        assert tests_ok(['1 passed in 1s', '1 passed in 1s', f'{EXPECTED_TESTS - 2} passed in 1s'])
        assert not tests_ok(['1 passed in 1s', '1 passed in 1s', f'{EXPECTED_TESTS - 3} passed in 1s']) and sorted(SPENT) == SPENT
        print('V23 SELFTEST_OK'); sys.exit(0)
    preconditions()
    if '--check' in sys.argv:
        print('PRECONDITIONS_OK'); sys.exit(0)
    run_scene()
    print('V23_CHAIN_END', flush=True)
