"""Archive finished M56 run roots to Google Drive (G:), verify, then MOVE (never delete) the local heavy copy to
outputs/_TRASH_UPLOADED_<stamp>/ and put the small result files back in place.
Per root: tar.zst -> G:/My Drive/M56_ARCHIVE_<stamp>/<root>.tar.zst; verify = re-read, sha256 + member count + bytes
equal to the source file list; only then rename. Resumable: roots listed in the manifest as VERIFIED are skipped.
Skipped: roots touched in the last 3 h, m56_f_* (live F chain), roots < 50 MB, anything already in the manifest.
usage: PYTHONPATH=<dir with zstandard> python -I archive-to-drive.py [--dry]"""
import hashlib, io, json, os, re, shutil, sys, tarfile, time
from pathlib import Path

import zstandard as z

STAMP = '20261114'
OUT = Path(__file__).resolve().parents[3] / 'outputs'
DEST = Path('G:/My Drive') / f'M56_ARCHIVE_{STAMP}'
TRASH = OUT / f'_TRASH_UPLOADED_{STAMP}'
MAN = OUT / f'm56_drive_archive_manifest_{STAMP}.jsonl'
KEEP = {'pair-result.json', 'ab-result.json', 'fixture-frozen.json', 'prepare.json', 'a2-bbox.json', 'plan-source.json',
        'ab_report.json', 'ab-log.json', 'stop.json'}  # stop.json: runner/stop.json = the in-place sign an A/B was spent
MIN_MB, RECENT_S, MIN_FREE_GB = 50, 3 * 3600, 2


def files_of(root):
    return [(os.path.join(r, f), os.path.getsize(os.path.join(r, f))) for r, _, fs in os.walk(root) for f in fs]


def done():
    return {json.loads(l)['root'] for l in MAN.read_text(encoding='utf-8').splitlines() if l.strip()} if MAN.exists() else set()


def pack(root, tmp):
    h = hashlib.sha256()
    with open(tmp, 'wb') as f:
        class W(io.RawIOBase):  # hash while writing
            def writable(self): return True
            def write(self, b): h.update(b); return f.write(b)
        w = z.ZstdCompressor(level=9, threads=2).stream_writer(W(), closefd=False)
        with tarfile.open(fileobj=w, mode='w|') as tf:
            tf.add(root, arcname=root.name)
        w.close()
    return h.hexdigest()


def verify(tmp, root, nfiles, nbytes):
    h = hashlib.sha256(); n = b = 0
    with open(tmp, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''):
            h.update(c)
    with open(tmp, 'rb') as f, tarfile.open(fileobj=z.ZstdDecompressor().stream_reader(f), mode='r|') as tf:
        for m in tf:
            if m.isfile():
                n += 1; b += m.size
    return h.hexdigest(), n == nfiles and b == nbytes


def main(dry):
    if not dry and not Path('G:/My Drive').exists():
        sys.exit('G: not available')
    DEST.mkdir(parents=True, exist_ok=True); TRASH.mkdir(exist_ok=True)
    skip = done(); now = time.time()
    # 2026-11-14 r3: never archive live evidence. asel2-release --full re-reads the sealed episodes and D09 of every PASS
    # scene, and the A-SEL2 batch (roots stamped >= 20261108) is still under analysis; roots without a stamp are inputs.
    import csv
    passed = {r['scene'] for r in csv.DictReader(open(OUT / f'm56_results_digest_{STAMP}.csv', encoding='utf-8'))
              if r['kind'] == 'pair' and r['status'] == 'PASS'}

    def live(d):
        m = re.search(r'_(\d{8})T\d{6}Z$', d.name)
        return not m or m.group(1) >= '20261108' or any((d / s).is_dir() for s in passed)
    roots = sorted(d for d in OUT.iterdir() if d.is_dir() and d.name.startswith('m56_') and not d.name.startswith('m56_f_')
                   and d.name not in skip and now - d.stat().st_mtime > RECENT_S and not live(d))
    for root in roots:
        fl = files_of(root); nb = sum(s for _, s in fl)
        if nb < MIN_MB * 2**20:
            continue
        if dry:
            print(f'{root.name} {nb/2**20:.0f} MB {len(fl)} files'); continue
        free = shutil.disk_usage('G:/').free / 2**30
        if free < MIN_FREE_GB + nb / 2**30 / 8:
            print('STOP: Drive free', round(free, 1), 'GB'); return
        tmp = DEST / f'{root.name}.tar.zst.part'
        try:
            sha = pack(root, tmp)
            sha2, ok = verify(tmp, root, len(fl), nb)
        except Exception as e:
            print('FAIL', root.name, repr(e)[:200], flush=True); tmp.unlink(missing_ok=True); continue
        if sha != sha2 or not ok:
            print('VERIFY_FAIL', root.name, flush=True); continue
        fin = DEST / f'{root.name}.tar.zst'; os.replace(tmp, fin)
        dst = TRASH / root.name
        os.replace(root, dst)  # same drive rename: moved, not deleted
        for src, _ in fl:
            if os.path.basename(src) in KEEP:
                rel = os.path.relpath(src, root); keep = root / rel
                keep.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(dst / rel, keep)
        rec = {'root': root.name, 'drive_path': f'My Drive/M56_ARCHIVE_{STAMP}/{root.name}.tar.zst', 'sha256': sha,
               'files': len(fl), 'bytes': nb, 'archive_bytes': fin.stat().st_size, 'local_trash': str(dst),
               'kept_in_place': sorted(KEEP), 'verified': True, 't': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        with open(MAN, 'a', encoding='utf-8') as m:
            m.write(json.dumps(rec) + '\n')
        print('OK', root.name, f'{nb/2**30:.2f}GB -> {rec["archive_bytes"]/2**30:.2f}GB', flush=True)
    print('ARCHIVE_END', flush=True)


if __name__ == '__main__':
    main('--dry' in sys.argv)
