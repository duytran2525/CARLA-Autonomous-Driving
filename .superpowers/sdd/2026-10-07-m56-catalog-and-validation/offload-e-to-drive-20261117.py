"""2026-11-17 (user: after E:, upload to Drive and delete from the machine, keep only the cloud copy; the junction group too;
then "toi uu upload"). Items = outputs/m56_offload_20261117_E.jsonl (moved D -> E; a dir, or a .tar file) +
outputs/m56_offload_20261117_junction.jsonl (D keeps a junction to E: deleted only with --delete-junctions).
Batches of ~BATCH_GB: wait C: >= MIN_C_GB -> robocopy each item E -> G:\\My Drive\\m56-offload-20261116\\<rel> -> verify G
-> poll the DriveFS metadata DB (read-only copy, retried while DriveFS locks it) until it has NO pending operations and
shows every batch item in the cloud with the same file count + bytes -> delete the batch's E copies (and junctions).
Batching keeps DriveFS's queue full (the one-item loop idled up to a poll per item) while the delete gate stays global
pending == 0. Rerun is safe (done items skipped). Log: outputs/m56_offload_20261117_cloud.jsonl.
python -I offload-e-to-drive-20261117.py [--delete-junctions] | --selftest"""
import json, shutil, sqlite3, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
E, G, TOP = Path('E:/m56-offload-20261116'), Path('G:/My Drive/m56-offload-20261116'), 'm56-offload-20261116'
DB = Path.home() / 'AppData/Local/Google/DriveFS/110182317752861355392'
LOG = OUT / 'm56_offload_20261117_cloud.jsonl'
MIN_C_GB, POLL_S, BATCH_GB = 12, 120, 3
DEL_J = '--delete-junctions' in sys.argv


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def say(**k):
    k['utc'] = now(); print(json.dumps(k), flush=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(k) + '\n')


def local(p):
    if p.is_file():
        return 1, p.stat().st_size
    fs = [f for f in p.rglob('*') if f.is_file()]
    return len(fs), sum(f.stat().st_size for f in fs)


def snapshot():
    """(pending, meta, kids) from a fresh read-only copy of the DriveFS metadata DB; DriveFS may lock a byte range of the
    file for a moment, so each copy is retried."""
    tmp = Path(tempfile.mkdtemp())
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
        pending = db.execute('select count(*) from operations').fetchone()[0] + db.execute('select count(*) from local_stable_ids').fetchone()[0]
        meta = {s: (t, d, z) for s, t, d, z, bad in db.execute(
            'select stable_id, local_title, is_folder, file_size, (trashed or is_tombstone) from items') if not bad}
        kids = {}
        for c, p in db.execute('select item_stable_id, parent_stable_id from stable_parents'):
            if c in meta:
                kids.setdefault(p, {})[meta[c][0]] = c
        db.close()
        return pending, meta, kids
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cloud(snap, rel):
    """(files, bytes) under TOP/rel in the snapshot (a file item counts itself)."""
    _, meta, kids = snap
    top = [s for s, m in meta.items() if m[0] == TOP and m[1]]
    s = top[0] if len(top) == 1 else None
    for part in Path(rel).parts:
        s = None if s is None else kids.get(s, {}).get(part)
    nf = nb = 0; stack = [] if s is None else [s]
    while stack:
        x = stack.pop()
        if meta[x][1]:
            stack.extend(kids.get(x, {}).values())
        else:
            nf += 1; nb += meta[x][2] or 0
    return nf, nb


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
    return {json.loads(l)['rel'].replace('\\', '/') for l in LOG.read_text(encoding='utf-8').splitlines()
            if '"DELETED_E"' in l or ('"KEPT_JUNCTION"' in l and not DEL_J)}


def copy(rel):
    src, dst = E / rel, G / rel
    if src.is_file():
        args = ['robocopy', str(src.parent), str(dst.parent), src.name]
    else:
        args = ['robocopy', str(src), str(dst), '/E']
    rc = subprocess.run(args + ['/COPY:DT', '/R:3', '/W:10', '/NFL', '/NDL', '/NP', '/NJH', '/NJS'], stdout=subprocess.DEVNULL).returncode
    if rc >= 8:
        say(event='FAIL_ROBOCOPY', rel=rel, rc=rc); sys.exit(2)
    n, b = local(src)
    if local(dst) != (n, b):
        say(event='FAIL_G_VERIFY', rel=rel, g=list(local(dst)), e=[n, b]); sys.exit(3)
    return n, b


def remove(rel, junction, n, b):
    if junction and not DEL_J:
        say(event='KEPT_JUNCTION', rel=rel, files=n, bytes=b, note='in cloud; E copy kept (code reads it via the D junction)')
        return
    if junction:
        j = OUT / rel
        if j.is_junction():
            j.rmdir()  # removes the link only, before the target goes
    src = E / rel
    src.unlink() if src.is_file() else shutil.rmtree(src)
    say(event='DELETED_E', rel=rel, files=n, bytes=b, cloud_verified=True, junction_removed=junction)


def run():
    idle = 0
    while idle < 2:
        done = done_set()
        todo = [(r, j) for r, j in items() if r not in done and (E / r).exists()]
        if not todo:
            idle += 1; time.sleep(600 if idle < 2 else 0); continue
        idle = 0; batch = []; size = 0
        for rel, junction in todo:
            if batch and size >= BATCH_GB * 2**30:
                break
            while shutil.disk_usage('C:/').free / 2**30 < MIN_C_GB:
                say(event='WAIT_C', rel=rel, c_free_gb=round(shutil.disk_usage('C:/').free / 2**30, 1)); time.sleep(POLL_S)
            n, b = copy(rel); batch.append((rel, junction, n, b)); size += b
        say(event='BATCH_COPIED', items=len(batch), gb=round(size / 2**30, 2))
        while True:
            snap = snapshot()
            if snap is not None:
                bad = [(r, cloud(snap, r), [n, b]) for r, _, n, b in batch if cloud(snap, r) != (n, b)]
                if snap[0] == 0 and not bad:
                    break
                say(event='WAIT_UPLOAD', pending=snap[0], items_short=len(bad), first=None if not bad else [bad[0][0], list(bad[0][1]), bad[0][2]])
            time.sleep(POLL_S)
        for rel, junction, n, b in batch:
            remove(rel, junction, n, b)


def selftest():
    snap = (0, {'t': (TOP, 1, None), 'a': ('a', 1, None), 'f': ('x.bin', 0, 5), 'g': ('y.tar', 0, 7)},
            {'root': {TOP: 't'}, 't': {'a': 'a', 'y.tar': 'g'}, 'a': {'x.bin': 'f'}})
    assert cloud(snap, 'a') == (1, 5) and cloud(snap, 'y.tar') == (1, 7) and cloud(snap, 'missing') == (0, 0)
    print('SELFTEST_OK')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest(); sys.exit(0)
    run()
    say(event='CLOUD_END', e_left_gb=round(sum(f.stat().st_size for f in E.rglob('*') if f.is_file()) / 2**30, 2) if E.exists() else 0)
