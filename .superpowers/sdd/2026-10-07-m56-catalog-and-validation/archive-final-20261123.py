"""M56 final archive to Google Drive, then delete the local copy (Duy [chat] 23/11/2026: "đưa toàn bộ dữ liệu của m56 lên
drive ... không để ở máy"; "Xoá hẳn sau khi Drive xác nhận"; "Giữ các file nhỏ trên D").
Roots: every directory of outputs/ (D_<name>), the loose files of outputs/ (D__outputs_loose), every entry of
E:/m56-offload-20261116 (E_<name>). Per root:
  1. tar.zst (level 9) of the regular files into the E staging dir, sha256 while writing; verify = re-read sha256 +
     decompress, file count and bytes equal to the source inventory. Links (symlinks, junctions) are never followed nor
     archived: the manifest records each link and its target (outputs/m56_offline_v1/source_checkpoints is a junction to
     the E root E_m56_offline_v1, archived there);
  2. copy to G:/My Drive/M56_FINAL_ARCHIVE_20261123/ and check the size on G;
  3. wait until DriveFS reports the file uploaded (DriveFS DB, read-only in place: a cloud id, not 'local-...', and the same
     size); only then delete the source files except KEEP names and git-tracked files, unlink the links (the link only),
     remove the emptied directories and the staging tar. A file that cannot be deleted is logged, not fatal.
Throttle: at most INFLIGHT_GB of copied-but-not-uploaded archives; C: free >= MIN_C_GB (DriveFS cache); Drive free checked.
Resumable: roots with a DONE record in the manifest are skipped. Manifest outputs/m56_final_archive_20261123.jsonl (kept,
also copied to Drive at the end). No tasklist/WMI calls (they hang on this machine since 23/11 03:08Z).
  python -I -X utf8 archive-final-20261123.py [--dry] | --selftest   (system python 3.12: zstandard 0.25)"""
import hashlib, io, json, os, shutil, sqlite3, subprocess, sys, tarfile, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

import zstandard as zstd

WORK = Path(__file__).resolve().parents[3]
OUT = WORK / 'outputs'
EOFF = Path('E:/m56-offload-20261116')
STAGE = Path('E:/m56-final-archive-20261123')
TOP = 'M56_FINAL_ARCHIVE_20261123'
G = Path('G:/My Drive') / TOP
DB = Path.home() / 'AppData/Local/Google/DriveFS/110182317752861355392/metadata_sqlite_db'
MAN = OUT / 'm56_final_archive_20261123.jsonl'
KEEP = {'pair-result.json', 'ab-result.json', 'fixture-frozen.json', 'prepare.json', 'a2-bbox.json', 'plan-source.json',
        'ab_report.json', 'ab-log.json', 'stop.json',  # the 14/11 archive's in-place result files
        'm56_asel2_STOP', 'M56_SAFE_TO_SHUTDOWN.txt'}  # hand-written STOP/SAFE stay until the pending reboot
INFLIGHT_GB, MIN_C_GB, POLL_S, LEVEL = 3., 8., 60, 9
LOOSE = 'D__outputs_loose'


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def say(**k):
    k['utc'] = now(); line = json.dumps(k, default=str, ensure_ascii=False)
    print(line, flush=True)
    with MAN.open('a', encoding='utf-8') as f:
        f.write(line + '\n')


def tracked():
    r = subprocess.run(['git', '-C', str(WORK), 'ls-files', '-z', 'outputs'], capture_output=True, check=True)
    return {os.path.normcase(str(WORK / p)) for p in r.stdout.decode('utf-8').split('\0') if p}


def roots():
    """[(name, kind, path)]: kind 'dir' (whole tree) or 'loose' (the files directly in outputs/)."""
    out = [(f'D_{d.name}', 'dir', d) for d in sorted(OUT.iterdir()) if d.is_dir()]
    out.append((LOOSE, 'loose', OUT))
    if EOFF.exists():
        out += [(f'E_{d.name}', 'dir', d) for d in sorted(EOFF.iterdir())]
    return out


def inventory(kind, path):
    """(files [(path, size)], links [(path, target)], dirs): links are listed, never followed."""
    if kind == 'loose':
        return sorted((e.path, e.stat(follow_symlinks=False).st_size) for e in os.scandir(path)
                      if e.is_file(follow_symlinks=False) and not e.name.startswith(MAN.stem)), [], []  # own manifest + logs
    files, links, dirs, todo = [], [], [], [str(path)]
    while todo:
        d = todo.pop(); dirs.append(d)
        for e in os.scandir(d):
            if e.is_symlink() or e.is_junction():
                links.append((e.path, os.readlink(e.path)))
            elif e.is_dir(follow_symlinks=False):
                todo.append(e.path)
            else:
                files.append((e.path, e.stat(follow_symlinks=False).st_size))
    return sorted(files), links, dirs


def pack(path, files, dst):
    """Arcnames are relative to the root's parent: '<root>/<rel>' for a dir root, 'outputs/<file>' for the loose root."""
    h = hashlib.sha256(); cut = len(str(path.parent).rstrip('\\/')) + 1
    with open(dst, 'wb') as f:
        class W(io.RawIOBase):
            def writable(self): return True
            def write(self, b): h.update(b); return f.write(b)
        w = zstd.ZstdCompressor(level=LEVEL, threads=4).stream_writer(W(), closefd=False)
        with tarfile.open(fileobj=w, mode='w|', format=tarfile.PAX_FORMAT) as tf:
            for p, _ in files:
                tf.add(p, arcname=p[cut:].replace('\\', '/'), recursive=False)
        w.close()
    return h.hexdigest()


def verify(arc, nfiles, nbytes):
    h = hashlib.sha256(); n = b = 0
    with open(arc, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''):
            h.update(c)
    with open(arc, 'rb') as f, tarfile.open(fileobj=zstd.ZstdDecompressor().stream_reader(f), mode='r|') as tf:
        for m in tf:
            if m.isfile():
                n += 1; b += m.size
    return h.hexdigest(), (n, b) == (nfiles, nbytes)


def cloud(db_path=DB, top=TOP):
    """{file title: (size, uploaded)} of the items directly in My Drive/<top>, from DriveFS's DB read in place (read-only)."""
    db = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=30)
    try:
        f = db.execute('select stable_id from items where local_title=? and is_folder=1 and not (trashed or is_tombstone)',
                       (top,)).fetchall()
        if len(f) != 1:
            return {}
        rows = db.execute('select i.local_title, i.file_size, i.id from stable_parents sp join items i on i.stable_id = '
                          'sp.item_stable_id where sp.parent_stable_id = ? and not (i.trashed or i.is_tombstone)', (f[0][0],))
        return {t: (z or 0, not str(i).startswith('local-')) for t, z, i in rows}
    except sqlite3.DatabaseError:
        return {}
    finally:
        db.close()


def drop(files, links, dirs, keep):
    """Delete the files except keep, unlink the links (the link itself, never its target), remove the emptied dirs."""
    gone = kept = 0; fail = []
    for p, _ in files:
        if os.path.normcase(p) in keep or os.path.basename(p) in KEEP:
            kept += 1; continue
        try:
            os.remove(p); gone += 1
        except OSError as e:
            fail.append(f'{p}: {e}')
    for p, _ in links:
        try:
            os.unlink(p)  # CPython removes a directory symlink/junction with RemoveDirectoryW: the link only
        except OSError as e:
            fail.append(f'{p}: {e}')
    for d in sorted(dirs, key=len, reverse=True):
        try:
            os.rmdir(d)
        except OSError:
            pass  # not empty: holds kept files
    return gone, kept, fail


def done():
    return {json.loads(l)['root'] for l in MAN.read_text(encoding='utf-8').splitlines()
            if l.strip() and '"DONE"' in l} if MAN.exists() else set()


def main(dry):
    keep = tracked()
    todo = [r for r in roots() if r[0] not in done()]
    if dry:
        tot = nl = 0
        for name, kind, path in todo:
            fl, ln, _ = inventory(kind, path); b = sum(s for _, s in fl); tot += b; nl += len(ln)
            print(f'{name} {len(fl)} files {b / 2**20:.0f} MB' + (f' links {ln}' if ln else ''))
        print(len(todo), 'roots', round(tot / 2**30, 2), 'GB', nl, 'links;', len(keep), 'tracked'); return
    assert Path('G:/My Drive').exists(), 'G: not available'
    STAGE.mkdir(exist_ok=True); G.mkdir(exist_ok=True)
    pending = {}  # archive file name -> (root name, files, links, dirs, staged path, size)

    def finish(name, an, files, links, dirs, **k):
        gone, kept, fail = drop(files, links, dirs, keep)
        say(event='DONE', root=name, archive=an, deleted_files=gone, kept_files=kept, unlinked=len(links),
            delete_failed=len(fail), delete_failed_sample=fail[:20], **k)

    def sweep():
        if not pending:
            return
        c = cloud()
        for an, (name, files, links, dirs, st, size) in list(pending.items()):
            got = c.get(an)
            if got and got[1] and got[0] == size:
                finish(name, an, files, links, dirs, cloud_verified=True)
                st.unlink(missing_ok=True); del pending[an]

    for name, kind, path in todo:
        files, links, dirs = inventory(kind, path)
        nf, nb = len(files), sum(s for _, s in files)
        if nf == 0:
            say(event='LINKS', root=name, links=links); finish(name, None, files, links, dirs, note='no files'); continue
        an = f'{name}.tar.zst'; st = STAGE / an; part = STAGE / (an + '.part')
        sha = pack(path, files, part)
        sha2, ok = verify(part, nf, nb)
        if sha != sha2 or not ok:
            say(event='VERIFY_FAIL', root=name); part.unlink(missing_ok=True); continue
        os.replace(part, st); size = st.stat().st_size
        while True:  # throttle on the not-yet-uploaded bytes and the DriveFS cache (C:)
            inflight = sum(v[5] for v in pending.values()) / 2**30
            c_free = shutil.disk_usage('C:/').free / 2**30
            if (inflight + size / 2**30 <= INFLIGHT_GB or not pending) and c_free >= MIN_C_GB + size / 2**30:
                break
            if not pending:
                say(event='WAIT_C', root=name, c_free_gb=round(c_free, 2), archive_gb=round(size / 2**30, 2))
                time.sleep(15 * POLL_S); continue
            time.sleep(POLL_S); sweep()
        free_g = shutil.disk_usage('G:/').free
        if free_g < size + 2**30:
            say(event='STOP_DRIVE_FULL', root=name, drive_free_gb=round(free_g / 2**30, 2)); break
        shutil.copyfile(st, G / an)
        if (G / an).stat().st_size != size:
            say(event='FAIL_G_SIZE', root=name); sys.exit(3)
        pending[an] = (name, files, links, dirs, st, size)
        say(event='COPIED', root=name, archive=an, files=nf, bytes=nb, archive_bytes=size, sha256=sha, links=links)
        sweep()
    while pending:
        time.sleep(POLL_S); sweep()
    shutil.copyfile(MAN, G / MAN.name)
    say(event='ARCHIVE_END', staged_left=len(list(STAGE.glob('*'))) if STAGE.exists() else 0,
        drive_free_gb=round(shutil.disk_usage('G:/').free / 2**30, 2))


def selftest():
    global MAN, OUT
    import _winapi
    d = Path(tempfile.mkdtemp())
    try:
        OUT = d / 'outputs'; (OUT / 'r1/sub').mkdir(parents=True); MAN = OUT / 'man.jsonl'
        (OUT / 'r1/sub/a.bin').write_bytes(os.urandom(5000)); (OUT / 'r1/pair-result.json').write_text('{}')
        (OUT / 'loose.txt').write_text('x' * 100); MAN.write_text('')
        ext = d / 'ext'; ext.mkdir(); (ext / 'precious.bin').write_text('p')  # a junction target outside the root
        _winapi.CreateJunction(str(ext), str(OUT / 'r1/sub/jn'))
        try:
            os.symlink(OUT / 'r1/sub', OUT / 'r1/cur', target_is_directory=True); nsym = 1
        except OSError:
            nsym = 0  # no symlink privilege: junction case still covered
        fl, ln, dl = inventory('dir', OUT / 'r1')
        assert len(fl) == 2 and len(ln) == 1 + nsym and len(dl) == 2, (fl, ln, dl)  # links not followed
        arc = d / 'r1.tar.zst'; sha = pack(OUT / 'r1', fl, arc)
        assert verify(arc, 2, sum(s for _, s in fl)) == (sha, True) and verify(arc, 3, 0)[1] is False
        with open(arc, 'rb') as f, tarfile.open(fileobj=zstd.ZstdDecompressor().stream_reader(f), mode='r|') as tf:
            assert sorted(m.name for m in tf) == ['r1/pair-result.json', 'r1/sub/a.bin']
        lf, _, _ = inventory('loose', OUT); assert [os.path.basename(p) for p, _ in lf] == ['loose.txt'], lf  # manifest out
        la = d / 'l.tar.zst'; pack(OUT, lf, la)
        with open(la, 'rb') as f, tarfile.open(fileobj=zstd.ZstdDecompressor().stream_reader(f), mode='r|') as tf:
            assert [m.name for m in tf] == ['outputs/loose.txt']
        assert drop(fl, ln, dl, set()) == (1, 1, [])
        assert (OUT / 'r1/pair-result.json').exists() and not (OUT / 'r1/sub').exists() and not (OUT / 'r1/cur').exists()
        assert (ext / 'precious.bin').exists()  # the junction's target survives
        e = d / 'E1'; (e / 'x').mkdir(parents=True); (e / 'x/b.bin').write_text('b')
        assert drop(*inventory('dir', e), set()) == (1, 0, []) and not e.exists()  # nothing kept: the root disappears
        k = OUT / 'kept.jsonl'; k.write_text('1'); assert drop([(str(k), 1)], [], [], {os.path.normcase(str(k))}) == (0, 1, [])
        g, _, fail = drop([(str(d / 'missing.bin'), 1)], [], [], set()); assert g == 0 and len(fail) == 1  # not fatal
        db = d / 'db'; c = sqlite3.connect(db)
        c.executescript('create table items(stable_id, id, local_title, is_folder, file_size, trashed, is_tombstone);'
                        'create table stable_parents(item_stable_id, parent_stable_id);'
                        "insert into items values (1,'X','TOPX',1,0,0,0),(2,'Y','a.tar.zst',0,10,0,0),(3,'local-9','b.tar.zst',0,7,0,0);"
                        'insert into stable_parents values (2,1),(3,1);'); c.commit(); c.close()
        assert cloud(db, 'TOPX') == {'a.tar.zst': (10, True), 'b.tar.zst': (7, False)} and cloud(db, 'NOPE') == {}
        print(f'ARCHIVE_FINAL SELFTEST_OK (symlink case {"run" if nsym else "skipped"})')
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--selftest']:
        selftest(); sys.exit(0)
    main('--dry' in sys.argv)
