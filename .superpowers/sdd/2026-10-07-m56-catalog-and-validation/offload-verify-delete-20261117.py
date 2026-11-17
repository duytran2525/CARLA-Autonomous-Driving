"""2026-11-17: delete an offloaded outputs/ item from D: only when Google Drive's CLOUD copy is complete.
Cloud truth = DriveFS metadata DB (copied read-only with its WAL): items under My Drive/m56-offload-20261116/<rel> that have a
cloud id, not trashed/tombstoned. An item is deleted from D when cloud file count AND bytes equal the D copy, and DriveFS has no
pending operations. Appends {rel, files, bytes, cloud_verified} to outputs/m56_offload_20261116_DELETED.jsonl.
usage: python -I offload-verify-delete-20261117.py [--dry]"""
import json, shutil, sqlite3, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
PLAN = OUT / 'm56_offload_20261116_plan.json'
LOG = OUT / 'm56_offload_20261116_DELETED.jsonl'
TOP = 'm56-offload-20261116'
SRC = Path.home() / 'AppData/Local/Google/DriveFS/110182317752861355392'
dry = '--dry' in sys.argv

tmp = Path(tempfile.mkdtemp())
for n in ('metadata_sqlite_db', 'metadata_sqlite_db-wal', 'metadata_sqlite_db-shm'):
    if (SRC / n).exists():
        shutil.copy2(SRC / n, tmp / n)
db = sqlite3.connect(tmp / 'metadata_sqlite_db')
pending = db.execute('select count(*) from operations').fetchone()[0] + db.execute('select count(*) from local_stable_ids').fetchone()[0]
meta = {s: (t, f, z, bad) for s, t, f, z, bad in
        db.execute('select stable_id, local_title, is_folder, file_size, (trashed or is_tombstone) from items')}
kids = {}
for c, p in db.execute('select item_stable_id, parent_stable_id from stable_parents'):
    if c in meta and not meta[c][3]:
        kids.setdefault(p, {})[meta[c][0]] = c
top = [s for s, m in meta.items() if m[0] == TOP and m[1] and not m[3]]
assert len(top) == 1, f'TOP_FOLDER {top}'


def node(rel):
    s = top[0]
    for part in Path(rel).parts:
        s = kids.get(s, {}).get(part)
        if s is None:
            return None
    return s


def cloud(s):
    nf = nb = 0; stack = [s]
    while stack:
        x = stack.pop()
        if meta[x][1]:
            stack.extend(kids.get(x, {}).values())
        else:
            nf += 1; nb += meta[x][2] or 0
    return nf, nb


rels = [r[0] for r in json.loads(PLAN.read_text(encoding='utf-8'))['move']]
elig = OUT / 'm56_asel2_release_20261115T054325Z' / 'elig'
rels += [str(p.relative_to(OUT)) for p in sorted(elig.iterdir()) if p.is_dir()] if elig.is_dir() else []
done = skipped = 0
for rel in rels:
    d = OUT / rel
    if not d.exists():
        continue
    files = [f for f in d.rglob('*') if f.is_file()]
    lf, lb = len(files), sum(f.stat().st_size for f in files)
    s = node(rel)
    cf, cb = cloud(s) if s is not None else (0, 0)
    if pending or (cf, cb) != (lf, lb):
        skipped += 1; print(f'KEEP {rel} local {lf}/{lb} cloud {cf}/{cb} pending_ops {pending}'); continue
    if not dry:
        shutil.rmtree(d)
        with LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'rel': rel, 'files': lf, 'bytes': lb, 'cloud_verified': True,
                                'utc': datetime.now(timezone.utc).isoformat(timespec='seconds')}) + '\n')
    done += 1; print(f'{"WOULD_DELETE" if dry else "DELETED"} {rel} {lf} files {lb / 2**30:.2f} GB')
print(f'VERIFY_END deleted={done} kept={skipped} D_free={shutil.disk_usage("D:/").free / 2**30:.1f} GB')
