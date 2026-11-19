"""2026-11-17 (user: after E:, upload to Drive and delete from the machine, keep only the cloud copy; the junction group too;
"toi uu upload"; then "upload xong file nao thi xoa luon file do"). Items = outputs/m56_offload_20261117_E.jsonl (moved
D -> E; a dir, or a .tar file) + outputs/m56_offload_20261117_junction.jsonl (D junction -> E, removed with the item).
A copier thread robocopies items E -> G:\\My Drive\\m56-offload-20261116\\<rel> (verify: every E file is on G with its size)
while at most INFLIGHT_GB of copied items still wait on E. Every POLL_S the main loop reads a fresh read-only copy of the
DriveFS metadata DB and deletes EACH E file whose G item has a cloud id (DriveFS keeps id 'local-...' until the upload
is done; local_stable_ids holds exactly those) and the same size. An item whose E files are all gone is logged
DELETED_E (and its D junction removed). Rerun is safe (done items skipped, half-swept items re-verified as a subset).
Log: outputs/m56_offload_20261117_cloud.jsonl. python -I offload-e-to-drive-20261117.py | --selftest"""
import json, os, shutil, sqlite3, subprocess, sys, tempfile, threading, time
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
E, G, TOP = Path('E:/m56-offload-20261116'), Path('G:/My Drive/m56-offload-20261116'), 'm56-offload-20261116'
DB = Path.home() / 'AppData/Local/Google/DriveFS/110182317752861355392'
LOG = OUT / 'm56_offload_20261117_cloud.jsonl'
MIN_C_GB, POLL_S, INFLIGHT_GB = 12, 60, 3
PACK_RUN = OUT / 'm56_pack_20261119.running'
LOCK = threading.Lock()


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def carla_up():
    """19/11 advisor: C: has ~16 GB; the uploader must not feed it while a CARLA episode runs (cguard never stops an A/B window)."""
    return 'carlaue4' in subprocess.run(['tasklist', '/NH'], capture_output=True, text=True).stdout.lower()


def say(**k):
    k['utc'] = now()
    with LOCK:
        print(json.dumps(k), flush=True)
        with LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(k) + '\n')


def files_of(p):
    """{relative posix path: size} of the files under p ('' for p itself when p is a file)."""
    if p.is_file():
        return {'': p.stat().st_size}
    return {f.relative_to(p).as_posix(): f.stat().st_size for f in p.rglob('*') if f.is_file()}


def snapshot():
    """(pending, meta, kids) from a fresh read-only copy of the DriveFS DB, or None when DriveFS held a lock or the copy
    caught the DB mid-write (malformed); the next poll retries. meta[s] = (title, is_folder, size, uploaded)."""
    tmp = Path(tempfile.gettempdir()) / 'm56-drivefs-snapshot'  # fixed path: a killed run's copy (0.5 GB) is reused, not left
    shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
    try:
        for n in ('metadata_sqlite_db', 'metadata_sqlite_db-wal', 'metadata_sqlite_db-shm'):
            for i in range(30):
                try:
                    if (DB / n).exists():
                        shutil.copyfile(DB / n, tmp / n)
                    break
                except PermissionError:
                    time.sleep(2)
            else:
                return None
        db = sqlite3.connect(tmp / 'metadata_sqlite_db')
        try:
            pending = db.execute('select count(*) from local_stable_ids').fetchone()[0]
            meta = {s: (t, d, z, not str(i).startswith('local-')) for s, i, t, d, z, bad in db.execute(
                'select stable_id, id, local_title, is_folder, file_size, (trashed or is_tombstone) from items') if not bad}
            kids = {}
            for c, p in db.execute('select item_stable_id, parent_stable_id from stable_parents'):
                if c in meta:
                    kids.setdefault(p, {})[meta[c][0]] = c
        except sqlite3.DatabaseError:
            return None
        finally:
            db.close()
        return pending, meta, kids
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cloud_files(snap, rel):
    """{relative posix path: (size, uploaded)} of the file items under TOP/rel ('' when rel is a file item)."""
    _, meta, kids = snap
    top = [s for s, m in meta.items() if m[0] == TOP and m[1]]
    s = top[0] if len(top) == 1 else None
    for part in Path(rel).parts:
        s = None if s is None else kids.get(s, {}).get(part)
    out, stack = {}, [] if s is None else [(s, '')]
    while stack:
        x, path = stack.pop()
        if meta[x][1]:
            stack.extend((c, f'{path}/{t}' if path else t) for t, c in kids.get(x, {}).items())
        else:
            out[path] = (meta[x][2] or 0, meta[x][3])
    return out


def sweep(snap, src, rel):
    """Delete each file under src (the E copy of rel) that is uploaded with the same size; returns (deleted, left)."""
    cf, gone, local = cloud_files(snap, rel), 0, files_of(src)
    for k, size in local.items():
        c = cf.get(k)
        if c is not None and c[1] and c[0] == size:
            try:
                (src / k if k else src).unlink(); gone += 1
            except OSError:  # open by a reader (Windows): retried next poll
                pass
    return gone, len(local) - gone


def items():
    seen = {}
    for name, junction in (('m56_offload_20261117_E.jsonl', False), ('m56_offload_20261117_junction.jsonl', True)):
        f = OUT / name
        for line in (f.read_text(encoding='utf-8-sig').splitlines() if f.exists() else ()):
            if line.strip():
                rel = json.loads(line)['rel']
                seen[(rel[0] if isinstance(rel, list) else rel).replace('\\', '/')] = junction
    return list(seen.items())


def done_set():
    if not LOG.exists():
        return set()
    return {json.loads(l)['rel'].replace('\\', '/') for l in LOG.read_text(encoding='utf-8').splitlines() if '"DELETED_E"' in l}


def copy(rel):
    src, dst = E / rel, G / rel
    if src.is_file():
        args = ['robocopy', str(src.parent), str(dst.parent), src.name]
    else:
        args = ['robocopy', str(src), str(dst), '/E']
    rc = subprocess.run(args + ['/COPY:DT', '/R:3', '/W:10', '/NFL', '/NDL', '/NP', '/NJH', '/NJS'], stdout=subprocess.DEVNULL).returncode
    if rc >= 8:
        say(event='FAIL_ROBOCOPY', rel=rel, rc=rc); os._exit(2)
    e, g = files_of(src), files_of(dst)
    bad = [k for k, z in e.items() if g.get(k) != z]
    if bad:
        say(event='FAIL_G_VERIFY', rel=rel, missing_or_size=len(bad), first=bad[0]); os._exit(3)
    return len(e), sum(e.values())


def copier(live, state):
    idle = 0
    while idle < 2:
        done = done_set()
        with LOCK:
            busy = set(live)
        # 19/11: DriveFS uploads ~1 GB/h of small files, so only a tar (file item) or a dir whose copy to G: had already
        # started is copied; every other dir waits for offload-pack-20261119.py (running = PACK_RUN) to turn it into a tar.
        todo = [(r, j) for r, j in items() if r not in done and r not in busy and (E / r).exists()
                and ((E / r).is_file() or (G / r).exists())]
        if not todo:
            if PACK_RUN.exists():
                time.sleep(60); continue
            idle += 1; time.sleep(600 if idle < 2 else 0); continue
        idle = 0
        for rel, junction in todo:
            while True:
                with LOCK:
                    inflight = sum(b for _, _, b in live.values())
                if inflight < INFLIGHT_GB * 2**30 and shutil.disk_usage('C:/').free / 2**30 >= MIN_C_GB and not carla_up():
                    break
                time.sleep(POLL_S)
            if not (E / rel).exists():
                continue
            n, b = copy(rel)
            say(event='COPIED', rel=rel, files=n, bytes=b)
            with LOCK:
                live[rel] = (junction, n, b)
    state['copier_done'] = True


def run():
    live, state, polls = {}, {'copier_done': False}, 0
    threading.Thread(target=copier, args=(live, state), daemon=True).start()
    while True:
        time.sleep(POLL_S)
        if carla_up():  # an A/B window: no new G: copies (DriveFS cache) and no 0.5 GB DB snapshot on C:
            continue
        snap = snapshot()
        if snap is not None:
            with LOCK:
                todo = list(live.items())
            for rel, (junction, n, b) in todo:
                gone, left = sweep(snap, E / rel, rel)
                if left:
                    if gone:
                        say(event='DELETED_FILES', rel=rel, files=gone, left=left)
                    continue
                if junction and (OUT / rel).is_junction():
                    (OUT / rel).rmdir()  # the link only
                if (E / rel).exists():
                    shutil.rmtree(E / rel)  # empty dirs remain
                say(event='DELETED_E', rel=rel, files=n, bytes=b, cloud_verified=True, junction_removed=junction)
                with LOCK:
                    del live[rel]
            polls += 1
            if polls % 10 == 0:
                say(event='WAIT_UPLOAD', pending=snap[0], items_live=len(todo))
        with LOCK:
            if state['copier_done'] and not live:
                return


def selftest():
    snap = (0, {'t': (TOP, 1, None, True), 'a': ('a', 1, None, True), 'f': ('x.bin', 0, 5, True), 'h': ('z.bin', 0, 3, False),
                'g': ('y.tar', 0, 7, True)},
            {'root': {TOP: 't'}, 't': {'a': 'a', 'y.tar': 'g'}, 'a': {'x.bin': 'f', 'z.bin': 'h'}})
    assert cloud_files(snap, 'a') == {'x.bin': (5, True), 'z.bin': (3, False)} and cloud_files(snap, 'y.tar') == {'': (7, True)}
    assert cloud_files(snap, 'missing') == {}
    d = Path(tempfile.mkdtemp())
    try:
        (d / 'a').mkdir(); (d / 'a/x.bin').write_bytes(b'12345'); (d / 'a/z.bin').write_bytes(b'123'); (d / 'y.tar').write_bytes(b'1234567')
        assert sweep(snap, d / 'a', 'a') == (1, 1) and not (d / 'a/x.bin').exists() and (d / 'a/z.bin').exists()
        snap[1]['h'] = ('z.bin', 0, 3, True)
        assert sweep(snap, d / 'a', 'a') == (1, 0) and sweep(snap, d / 'y.tar', 'y.tar') == (1, 0)
    finally:
        shutil.rmtree(d)
    print('SELFTEST_OK')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest(); sys.exit(0)
    run()
    say(event='CLOUD_END', e_left_gb=round(sum(f.stat().st_size for f in E.rglob('*') if f.is_file()) / 2**30, 2) if E.exists() else 0)
