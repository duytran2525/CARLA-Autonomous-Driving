"""2026-11-17 (user: "tiep tuc toi uu upload het du lieu khong can thiet nua o o D va o E len o G"). Round 3: move every
old run dir on D to E:\\m56-offload-20261116\\<rel> now (local copy, minutes), so D is freed at once; the cloud uploader
(offload-e-to-drive-20261117.py) then takes everything on E to Drive and deletes it. Selection (read rules of the code):
  - m56_v2_ab_*, m56_io_ab_*, m56_f_ab_*: whole dir, unless stamped today (17/11, still in use). Not m56_v2_prepare_*:
    the revision builder (run-asel2-revision-io16.sh) reads 25/10 prepare dirs.
  - m56_v6_pair_*: whole dir copied, but every */pair-result.json STAYS on D (asel2-release.latest_pair globs
    outputs/m56_v6_pair_*/<id>/pair-result.json; the 16/11 archive lost two PASS results by moving them). Release --full,
    re-pairing an old scene or a diagnostic must first restore the dir from Drive.
  - m56_offline_v1/diagnostics: whole dir. m56_offline_v1/pytest_receipts: one uncompressed tar (184 inner symlinks,
    which robocopy follows and Drive cannot store).
Kept on D: today's dirs, m56_offline_v1/{inputs,wheels} (tests read them), logs, revisions, everything small.
Per item: copy -> verify file count + bytes on E -> delete from D (pair dirs: all but pair-result.json). Log appends to
outputs/m56_offload_20261117_E.jsonl (the uploader's item list). python -I offload-d-to-e-20261117c.py [--dry]"""
import json, os, re, shutil, subprocess, sys, tarfile
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
E = Path('E:/m56-offload-20261116')
LOG = OUT / 'm56_offload_20261117_E.jsonl'
TODAY = datetime.now(timezone.utc).strftime('%Y%m%d')
WHOLE = re.compile(r'^m56_(v2_ab|io_ab|f_ab)_.*_(\d{8})T\d{6}Z$')  # not v2_prepare: run-asel2-revision-io16.sh reads 25/10 prepare dirs
PAIR = re.compile(r'^m56_v6_pair_(\d{8})T\d{6}Z$')
KEEP = 'pair-result.json'


def stamp_ok(day):
    return day < TODAY


def plan(names):
    """[(rel, mode)] for the top-level names of outputs (pure; self-tested)."""
    out = []
    for n in sorted(names):
        m = WHOLE.match(n)
        if m and stamp_ok(m.group(2)):
            out.append((n, 'dir'))
        m = PAIR.match(n)
        if m and stamp_ok(m.group(1)):
            out.append((n, 'pair'))
    return out


def tree(p):
    n = b = 0
    for dp, _, fn in os.walk(p):
        for f in fn:
            n += 1; b += os.stat(os.path.join(dp, f), follow_symlinks=False).st_size
    return n, b


def say(**k):
    k['utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(k) + '\n')
    print(json.dumps(k), flush=True)


def move(rel, mode):
    src, dst = OUT / rel, E / rel
    if src.is_symlink() or src.is_junction() or not src.is_dir():
        return
    n, b = tree(src)
    rc = subprocess.run(['robocopy', str(src), str(dst), '/E', '/COPY:DT', '/R:2', '/W:5', '/NFL', '/NDL', '/NP', '/NJH', '/NJS'],
                        stdout=subprocess.DEVNULL).returncode
    if rc >= 8:
        sys.exit(f'FAIL robocopy {rel} rc={rc}')
    if tree(dst) != (n, b):
        sys.exit(f'FAIL verify {rel} {tree(dst)} != {(n, b)}')
    if mode == 'pair':
        kept = 0
        for dp, dn, fn in os.walk(src, topdown=False):
            for f in fn:
                if f == KEEP:
                    kept += 1
                else:
                    os.remove(os.path.join(dp, f))
            for d in dn:
                try:
                    os.rmdir(os.path.join(dp, d))
                except OSError:
                    pass  # still holds a pair-result.json
        say(rel=rel, files=n, bytes=b, e=str(dst), mode='pair', kept_on_d=kept)
    else:
        shutil.rmtree(src)
        say(rel=rel, files=n, bytes=b, e=str(dst), mode='dir')


def receipts_tar():
    rel = 'm56_offline_v1/pytest_receipts'; src = OUT / rel; dst = E / (rel + '.tar')
    if not src.is_dir() or src.is_junction():
        return
    entries = sum(len(dn) + len(fn) for _, dn, fn in os.walk(src)) + 1
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dst, 'w', format=tarfile.PAX_FORMAT) as t:
        t.add(src, arcname='pytest_receipts')  # symlinks stored as links (tarfile does not follow by default)
    with tarfile.open(dst) as t:
        got = len(t.getmembers())
    if got != entries:
        sys.exit(f'FAIL tar {rel} members {got} != {entries}')
    shutil.rmtree(src)
    say(rel=rel + '.tar', files=1, bytes=dst.stat().st_size, e=str(dst), mode='tar', members=got)


def selftest():
    p = plan(['m56_v2_ab_Town04_20261025T123841Z', 'm56_io_ab_Town13_20261117T072227Z', 'm56_v6_pair_20261116T110910Z',
              'm56_v6_pair_20261117T074252Z', 'm56_v2_prepare_Town12_20261116T141740Z', 'm56_offline_v1', 'm56_asel2_io_20261117T065652Z'])
    assert p == [('m56_v2_ab_Town04_20261025T123841Z', 'dir'),
                 ('m56_v6_pair_20261116T110910Z', 'pair')], p
    print('SELFTEST_OK')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest(); sys.exit(0)
    items = plan(p.name for p in OUT.iterdir() if p.is_dir()) + [('m56_offline_v1/diagnostics', 'dir')]
    if '--dry' in sys.argv:
        for r, m in items:
            print(m, r)
        print(len(items), 'items'); sys.exit(0)
    for r, m in items:
        move(r, m)
    receipts_tar()
    print('E_END D_free={:.1f} GB E_free={:.1f} GB'.format(shutil.disk_usage('D:/').free / 2**30, shutil.disk_usage('E:/').free / 2**30))
