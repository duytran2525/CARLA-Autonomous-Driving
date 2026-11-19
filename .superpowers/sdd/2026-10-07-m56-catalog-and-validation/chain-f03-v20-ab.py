"""2026-11-20 one-shot chain for the single F03 A/B under m56-v20 (P5; v19's A/B is spent, addendum A5). Claude under Duy's
delegation. Preconditions, checked in this order, any miss writes outputs/m56_f03_v20_ab_BLOCKED.txt and stops (nothing runs):
  1. the v20 F+runtime test run (pid TESTS_PID, stdout TESTS_OUT) has ended and its last line is "N passed ..." with no failed/error;
  2. outputs/m56_f03_gate_v20_full.stdout.txt ends F03_REPLAY_PASS (full offline gate on the r19d probe-A episode under v20);
  3. m56-v20 is at 22c57cf with a clean tree; the r19d revision file has sha256 REVF_SHA;
  4. outputs/m56_f03_v20_ab_LAUNCHED does not exist (written just before the launch: one A/B, never a second). It is written
     BEFORE room() waits, so if the chain dies while waiting, look for a new outputs/m56_f_ab_Town12_202611* dir before
     treating P5 as spent (no dir = not spent: delete the marker).
Then run-f03-u20.sh ab: its room() waits until no CARLA runs and cguard says commit >= 25 GB, C >= 10, D >= 80, E >= 150 GB
(Duy 19/11), and own_server asserts D/E again. usage: python -I chain-f03-v20-ab.py [--check]"""
import hashlib, re, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
W = HERE.parents[2]
OUT = W / 'outputs'
TESTS_PID, TESTS_OUT = 25468, OUT / 'm56_v20_ftests_r20.stdout.txt'
REVF = OUT / 'm56_c0_partial_io_asel2f03prep_20261118T181450Z/c0-partial-v5-frozen-revision.json'
REVF_SHA = 'fd624362f51f74f28f048bf805441c6dbd560f8a8be9ff5a434c84922be298b0'
V20, V20_HEAD = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v20'), '22c57cf'
PREREG = 'F part 2 c9ba62a+fb44b89, addendum A 780e8c2 + A5 e2fcb2e (v20)'
BLOCKED, LAUNCHED = OUT / 'm56_f03_v20_ab_BLOCKED.txt', OUT / 'm56_f03_v20_ab_LAUNCHED'


def alive(pid):
    r = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True).stdout
    return str(pid) in r


def git(*a):
    return subprocess.run(['git', '-C', str(V20), *a], capture_output=True, text=True).stdout.strip()


def blocked(why):
    BLOCKED.write_text(f'{datetime.now(timezone.utc).isoformat(timespec="seconds")} {why}\n', encoding='utf-8')
    print('BLOCKED', why, flush=True); sys.exit(3)


def verdict_of_tests(text):
    last = [l for l in text.splitlines() if l.strip()][-1:] or ['']
    return bool(re.match(r'^=*\s*\d+ passed\b', last[0])) and not re.search(r'failed|error', last[0], re.I)


def preconditions():
    if not verdict_of_tests(TESTS_OUT.read_text(encoding='utf-8', errors='replace')):
        blocked('v20 F+runtime tests did not end with a clean "N passed" line')
    gate = (OUT / 'm56_f03_gate_v20_full.stdout.txt').read_text(encoding='utf-8', errors='replace')
    if not gate.rstrip().endswith('F03_REPLAY_PASS'):
        blocked('full replay gate under v20 is not F03_REPLAY_PASS')
    if not git('rev-parse', 'HEAD').startswith(V20_HEAD) or git('status', '--porcelain'):
        blocked(f'm56-v20 is not clean at {V20_HEAD}')
    if hashlib.sha256(REVF.read_bytes()).hexdigest() != REVF_SHA:
        blocked('r19d revision file bytes changed')
    if LAUNCHED.exists():
        blocked('an A/B launch marker exists already (P5: one A/B per scene per version)')


def selftest():
    assert verdict_of_tests('....\n432 passed in 1234.5s (0:20:34)\n')
    assert verdict_of_tests('..\n36 passed, 2 warnings in 9s\n')
    assert not verdict_of_tests('..\n1 failed, 431 passed in 9s\n') and not verdict_of_tests('...  [14%]\n') and not verdict_of_tests('')
    print('SELFTEST_OK')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest(); sys.exit(0)
    while alive(TESTS_PID):
        time.sleep(60)
    preconditions()
    if '--check' in sys.argv:
        print('PRECONDITIONS_OK'); sys.exit(0)
    LAUNCHED.write_text(datetime.now(timezone.utc).isoformat(timespec='seconds'), encoding='utf-8')
    log = OUT / f"m56_f03uab_r20_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    with log.open('w', encoding='utf-8') as f:
        rc = subprocess.run(['D:/Git/bin/bash.exe', 'run-f03-u20.sh', 'ab', str(REVF).replace('\\', '/'), PREREG], cwd=HERE, stdout=f,
                            stderr=subprocess.STDOUT).returncode
    print('F03_V20_AB_END rc', rc, log, flush=True)
