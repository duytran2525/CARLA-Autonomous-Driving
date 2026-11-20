"""2026-11-20 chain for addendum W: one A/B per scene under m56-v21, F05 then F03-S1, one CARLA at a time. Claude under Duy's
delegation ([chat] 20/11 "làm v21 cho tôi"). Before anything starts (any miss -> outputs/m56_v21_ab_BLOCKED.txt, nothing runs):
  1. the v21 test selection (outputs/m56_v21_tests_20261120.stdout.txt) has ended (no running pytest with --basetemp ...pyt-v21) and
     its last line is "N passed ..." with no failed/error;
  2. real-data gates under v21: native-v21-f03-gate.py not_blocked, native-f05-v20-gate.py on the F05 rerun arm B PASS;
  3. m56-v21 clean at V21_HEAD; tooling *.py/*.sh and addendum W committed; both frozen revisions have their sha256;
  4. P5: no marker outputs/m56_v21_ab_<SCENE>_LAUNCHED, and the A/B dirs holding each scene are exactly the known spent ones.
Per scene: compile preview (FROZEN + ADMITTED, else BLOCKED for that scene and the chain stops), marker, the single A/B + pairs.
The marker is written BEFORE room() waits: if the chain dies, a new m56_f_ab_Town12_* dir holding the scene = that A/B ran.
usage: python -I chain-v21-ab.py [--check|--selftest]"""
import hashlib, importlib.util, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('c1', HERE / 'chain-f05-v20-ab.py'); c1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c1)
OUT, W, PY, BASH = c1.OUT, c1.W, c1.PY, c1.BASH
V21, V21_HEAD = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v21'), '27783f0'
TESTS_OUT = OUT / 'm56_v21_tests_20261120.stdout.txt'
ADDENDUM = 'docs/m56/PREREG_M56_V21_ADDENDUM_W_20261120.md'
BLOCKED = OUT / 'm56_v21_ab_BLOCKED.txt'
c1.BLOCKED = BLOCKED
F05_RERUN_B = OUT / 'm56_f_ab_Town12_20261120T143048Z/M56-P-F05/run/episodes/M56-P-F05/B'
SCENES = {  # scene: (frozen revision, sha256, spent A/B dirs that hold it)
    'F05': ('M56-P-F05', OUT / 'm56_c0_partial_io_asel2f05prep_20261118T092923Z/c0-partial-v5-frozen-revision.json',
            'e1b578183e4b10007cbbcf3d4101e7df35beb49d9b19297905a0bf0a2ee5fcf3',
            ['m56_f_ab_Town12_20261118T093346Z', 'm56_f_ab_Town12_20261120T070548Z', 'm56_f_ab_Town12_20261120T143048Z']),
    'F03': ('M56-P-F03-S1', OUT / 'm56_c0_partial_io_asel2f03prep_20261118T181450Z/c0-partial-v5-frozen-revision.json',
            'fd624362f51f74f28f048bf805441c6dbd560f8a8be9ff5a434c84922be298b0',
            ['m56_f_ab_Town12_20261118T192541Z', 'm56_f_ab_Town12_20261119T191948Z']),
}
PREREG = {'F05': 'F part 1 3fb9865 + addenda T/U + V + W {w} (v21)', 'F03': 'F part 2 c9ba62a+fb44b89, addendum A 780e8c2 + A5/A6 + W {w} (v21)'}


def marker(k):
    return OUT / f'm56_v21_ab_{k}_LAUNCHED'


def dirs(scene):
    return sorted(d.name for d in OUT.glob('m56_f_ab_Town12_*') if (d / scene).exists())


def tests_running():
    r = subprocess.run(['powershell', '-NoProfile', '-Command',
                        "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*pyt-v21*' }).Count"],
                       capture_output=True, text=True).stdout.strip()
    return r not in ('', '0')


def preconditions():
    if not c1.verdict_of_tests(TESTS_OUT.read_text(encoding='utf-8', errors='replace')):
        c1.blocked('v21 test selection did not end with a clean "N passed" line')
    env = {**os.environ, 'M56_CODE': str(V21), 'M56_RECIPE': 'v6'}
    g3 = subprocess.run([PY, '-I', '-X', 'utf8', str(HERE / 'native-v21-f03-gate.py'), 'not_blocked'], capture_output=True, text=True, env=env)
    if 'V21_F03_GATE PASS' not in g3.stdout:
        c1.blocked('F03 real-data gate under v21: ' + (g3.stdout[-300:] or g3.stderr[-300:]).replace('\n', ' '))
    g5 = subprocess.run([PY, '-I', '-X', 'utf8', str(HERE / 'native-f05-v20-gate.py'), str(F05_RERUN_B)], capture_output=True, text=True, env=env)
    if 'F05_V20_GATE PASS' not in g5.stdout:
        c1.blocked('F05 real-data gate under v21: ' + (g5.stdout[-300:] or g5.stderr[-300:]).replace('\n', ' '))
    full = (OUT / 'm56_f03_gate_v21_full.stdout.txt').read_text(encoding='utf-8', errors='replace')
    if not full.rstrip().endswith('F03_REPLAY_PASS'):  # A5's registered F03 gate, rerun under v21 (advisor 20/11)
        c1.blocked('full F03 replay gate under v21 is not F03_REPLAY_PASS')
    if not c1.git(V21, 'rev-parse', 'HEAD').startswith(V21_HEAD) or c1.git(V21, 'status', '--porcelain'):
        c1.blocked(f'm56-v21 is not clean at {V21_HEAD}')
    rel = str(HERE.relative_to(W)).replace('\\', '/')
    dirty = c1.git(W, 'status', '--porcelain', '--', rel + '/*.py', rel + '/*.sh', ADDENDUM)
    if dirty:
        c1.blocked('uncommitted tooling/addendum: ' + dirty.replace('\n', ' | '))
    for k, (scene, revf, sha, spent) in SCENES.items():
        if hashlib.sha256(revf.read_bytes()).hexdigest() != sha:
            c1.blocked(f'{k} frozen revision bytes changed')
        if marker(k).exists():
            c1.blocked(f'{k}: a v21 launch marker exists already (P5)')
        if dirs(scene) != spent:
            c1.blocked(f'{k}: A/B dirs are not exactly the spent ones: {dirs(scene)}')


def run_scene(k):
    scene, revf, _, _ = SCENES[k]
    revf = str(revf).replace('\\', '/')
    log = OUT / f"m56_v21ab_chain_{k}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    env = {**os.environ, 'M56_COMMIT_START_GB': '32'}
    with log.open('w', encoding='utf-8') as f:
        rc = subprocess.run([BASH, 'run-v21-ab.sh', k, 'compile', revf], cwd=HERE, stdout=f, stderr=subprocess.STDOUT, env=env).returncode
    text = log.read_text(encoding='utf-8', errors='replace')
    if rc or '"status": "FROZEN"' not in text or '"status": "ADMITTED"' not in text or 'V21_COMPILE_END' not in text:
        c1.blocked(f'{k}: compile preview (rc {rc}) is not FROZEN + ADMITTED: see {log}')
    marker(k).write_text(datetime.now(timezone.utc).isoformat(timespec='seconds'), encoding='utf-8')
    prereg = PREREG[k].format(w=c1.git(W, 'log', '-1', '--format=%h', '--', ADDENDUM))
    with log.open('a', encoding='utf-8') as f:
        rc = subprocess.run([BASH, 'run-v21-ab.sh', k, 'ab', revf, prereg], cwd=HERE, stdout=f, stderr=subprocess.STDOUT, env=env).returncode
    print(f'V21_{k}_AB_END rc', rc, log, flush=True)


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        c1.selftest(); assert all(s[3] == sorted(s[3]) for s in SCENES.values()); print('V21 SELFTEST_OK'); sys.exit(0)
    while tests_running():
        time.sleep(60)
    preconditions()
    if '--check' in sys.argv:
        print('PRECONDITIONS_OK'); sys.exit(0)
    for k in ('F05', 'F03'):
        run_scene(k)
    print('V21_CHAIN_END', flush=True)
