"""2026-11-17 (user: after E:, upload to Drive and delete from the machine, keep only the cloud copy).
Items = outputs/m56_offload_20261117_E.jsonl (moved D -> E, nothing on D reads them) + outputs/m56_offload_20261117_junction.jsonl
(D keeps a junction to E because code reads them: uploaded, but NOT deleted unless --delete-junctions).
Per item, in order: wait C: >= MIN_C_GB -> robocopy E -> G:\\My Drive\\m56-offload-20261116\\<rel> -> wait until the DriveFS
metadata DB (read-only copy) has no pending operations and shows the same file count + bytes in the cloud -> delete the E: copy
(for a junction item also the junction). Upload is ~0.25 MB/s, so this runs for many hours; rerun is safe (done items skipped).
Log: outputs/m56_offload_20261117_cloud.jsonl.  python -I offload-e-to-drive-20261117.py [--delete-junctions]"""
import json, shutil, sqlite3, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
E, G, TOP = Path('E:/m56-offload-20261116'), Path('G:/My Drive/m56-offload-20261116'), 'm56-offload-20261116'
DB = Path.home() / 'AppData/Local/Google/DriveFS/110182317752861355392'
LOG = OUT / 'm56_offload_20261117_cloud.jsonl'
MIN_C_GB, POLL_S = 12, 300
DEL_J = '--delete-junctions' in sys.argv


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def say(**k):
    k['utc'] = now(); print(json.dumps(k), flush=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(k) + '\n')


def local(p):
    fs = [f for f in p.rglob('*') if f.is_file()]
    return len(fs), sum(f.stat().st_size for f in fs)


def cloud(rel):
    """(pending, files, bytes) from a fresh read-only copy of the DriveFS metadata DB."""
    tmp = Path(tempfile.mkdtemp())
    try:
        for n in ('metadata_sqlite_db', 'metadata_sqlite_db-wal', 'metadata_sqlite_db-shm'):
            if (DB / n).exists():
                shutil.copy2(DB / n, tmp / n)
        db = sqlite3.connect(tmp / 'metadata_sqlite_db')
        pending = db.execute('select count(*) from operations').fetchone()[0] + db.execute('select count(*) from local_stable_ids').fetchone()[0]
        meta = {s: (t, d, z) for s, t, d, z, bad in db.execute(
            'select stable_id, local_title, is_folder, file_size, (trashed or is_tombstone) from items') if not bad}
        kids = {}
        for c, p in db.execute('select item_stable_id, parent_stable_id from stable_parents'):
            if c in meta:
                kids.setdefault(p, {})[meta[c][0]] = c
        db.close()
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
        return pending, nf, nb
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def items():
    seen = []
    for name, junction in (('m56_offload_20261117_E.jsonl', False), ('m56_offload_20261117_junction.jsonl', True)):
        f = OUT / name
        for line in (f.read_text(encoding='utf-8').splitlines() if f.exists() else ()):
            if line.strip():
                seen.append((json.loads(line)['rel'], junction))
    return seen


done = set()
if LOG.exists():
    done = {json.loads(l)['rel'] for l in LOG.read_text(encoding='utf-8').splitlines()
            if '"DELETED_E"' in l or ('"KEPT_JUNCTION"' in l and not DEL_J)}


def todo():
    # re-read each pass: the junction mover appends items while this runs; two idle passes 10 min apart end the run
    return [(r, j) for r, j in items() if r not in done and (E / r).exists()]


def run():
  idle = 0
  while idle < 2:
    batch = todo()
    if not batch:
        idle += 1; time.sleep(600 if idle < 2 else 0); continue
    idle = 0
    for rel, junction in batch:
        process(rel, junction)


def process(rel, junction):
    src = E / rel
    n, b = local(src)
    while shutil.disk_usage('C:/').free / 2**30 < MIN_C_GB:
        say(event='WAIT_C', rel=rel, c_free_gb=round(shutil.disk_usage('C:/').free / 2**30, 1)); time.sleep(POLL_S)
    rc = subprocess.run(['robocopy', str(src), str(G / rel), '/E', '/COPY:DT', '/R:3', '/W:10', '/NFL', '/NDL', '/NP', '/NJH', '/NJS'],
                        stdout=subprocess.DEVNULL).returncode
    if rc >= 8:
        say(event='FAIL_ROBOCOPY', rel=rel, rc=rc); sys.exit(2)
    gn, gb = local(G / rel)
    if (gn, gb) != (n, b):
        say(event='FAIL_G_VERIFY', rel=rel, g=[gn, gb], e=[n, b]); sys.exit(3)
    while True:
        pending, cn, cb = cloud(rel)
        if pending == 0 and (cn, cb) == (n, b):
            break
        say(event='WAIT_UPLOAD', rel=rel, pending=pending, cloud=[cn, cb], e=[n, b]); time.sleep(POLL_S)
    if junction and not DEL_J:
        say(event='KEPT_JUNCTION', rel=rel, files=n, bytes=b, note='in cloud; E copy kept (code reads it via the D junction)')
        done.add(rel); return
    if junction:
        j = OUT / rel
        if j.is_junction():
            j.rmdir()  # removes the link only, before the target goes
    shutil.rmtree(src)
    done.add(rel)
    say(event='DELETED_E', rel=rel, files=n, bytes=b, cloud_verified=True, junction_removed=junction)


run()
say(event='CLOUD_END', e_left_gb=round(sum(f.stat().st_size for f in E.rglob('*') if f.is_file()) / 2**30, 2) if E.exists() else 0)
