"""2026-11-21 relaunch of chain-v21-ab.py after its test gate BLOCKED (outputs/m56_v21_ab_BLOCKED.txt, 17:50Z 20/11).
Cause: environment, not code. The v21 selection ended "448 passed, 851 deselected, 1 error": test_staging's fixture reads
gitignored inputs at <worktree>/outputs/m56_offline_v1/inputs, which the fresh m56-v21 worktree did not have (FileNotFoundError
in setup). The 8 input files were copied from m56-v1 (sha256 identical) and that one test was rerun alone: 1 passed.
Only the test gate changes, it is now: the original log ends with exactly that line, its only ERROR is that test with that
FileNotFoundError, and the rerun log ends "1 passed". Everything else (gates, P5, markers, order, room 32 GB) is chain-v21-ab.py.
Writes outputs/m56_v21_ab2_BLOCKED.txt on any miss. usage: python -I chain-v21-ab2.py [--check|--selftest]"""
import importlib.util, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('v21', HERE / 'chain-v21-ab.py'); v21 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v21)
RERUN = v21.OUT / 'm56_v21_tests_20261120_rerun_staging.stdout.txt'
TEST = 'test_staging.py::test_stage_26_preserves_missing20_and_f06_proposal'
v21.BLOCKED = v21.c1.BLOCKED = v21.OUT / 'm56_v21_ab2_BLOCKED.txt'


def tests_ok(original, rerun):
    lines = [l for l in original.splitlines() if l.strip()]
    errors = [l for l in lines if l.startswith('ERROR ')]
    return (bool(lines) and lines[-1].strip().startswith('448 passed, 851 deselected, 1 error in ')
            and len(errors) == 1 and errors[0].endswith(TEST)
            and "FileNotFoundError: [Errno 2] No such file or directory: 'D:\\\\AI\\\\CARLA-Funny-Moments.worktrees\\\\m56-v21\\\\outputs\\\\m56_offline_v1\\\\inputs\\\\" in original
            and ORIGINAL_VERDICT(rerun) and bool(re.search(r'^\s*1 passed\b', [l for l in rerun.splitlines() if l.strip()][-1])))


def gate(_text):
    return tests_ok(v21.TESTS_OUT.read_text(encoding='utf-8', errors='replace'), RERUN.read_text(encoding='utf-8', errors='replace'))


ORIGINAL_VERDICT = v21.c1.verdict_of_tests
v21.c1.verdict_of_tests = gate

if __name__ == '__main__':
    if '--selftest' in sys.argv:
        orig = v21.TESTS_OUT.read_text(encoding='utf-8', errors='replace')
        assert gate('') and not tests_ok(orig.replace('1 error', '1 failed'), '1 passed in 0.1s')
        assert not tests_ok(orig, '1 failed in 0.1s') and not tests_ok(orig + '\nERROR x::y\n448 passed, 851 deselected, 1 error in 1s', '1 passed')
        print('V21_AB2 SELFTEST_OK'); sys.exit(0)
    v21.preconditions()
    if '--check' in sys.argv:
        print('PRECONDITIONS_OK'); sys.exit(0)
    for k in ('F05', 'F03'):
        v21.run_scene(k)
    print('V21_CHAIN_END', flush=True)
