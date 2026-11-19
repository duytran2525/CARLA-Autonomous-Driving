"""2026-11-19 (user: keep uploading to Google Drive; D: > 80 GB and E: > 150 GB free before any CARLA start).
E: holds ~1.7 M files (82 GB), 99% under 1 MB, and DriveFS uploads them at ~1 GB/h. This packs every E: item that the cloud
uploader has not started yet (no G:\\My Drive copy) into ONE uncompressed PAX tar next to it (<rel>.tar; extracting it in the
parent dir restores the dir), checks every entry (name, kind, size) of the tar against the tree, registers <rel>.tar in the
uploader's item list (outputs/m56_offload_20261117_E.jsonl) and only then deletes the tree. offload-e-to-drive-20261119.py
(copies tars, or dirs already started on G:) uploads and deletes the tar once the cloud id exists.
Items are skipped when: G:\\My Drive\\m56-offload-20261116\\<rel> exists (copy under way), the item is a junction item, or
rel is already DELETED_E. Rerun-safe (a half-built <rel>.tar.part is rebuilt; a finished tar with a surviving tree is re-verified).
Marker outputs/m56_pack_20261119.running (kept while the run lives) tells the uploader to wait for more tars.
usage: python -I offload-pack-20261119.py [--dry] [--only SUBSTR] | --selftest"""
import json, os, shutil, stat, sys, tarfile, tempfile
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
E, G = Path('E:/m56-offload-20261116'), Path('G:/My Drive/m56-offload-20261116')
ELIST, JLIST = OUT / 'm56_offload_20261117_E.jsonl', OUT / 'm56_offload_20261117_junction.jsonl'
CLOUD, LOG, RUN = OUT / 'm56_offload_20261117_cloud.jsonl', OUT / 'm56_pack_20261119.jsonl', OUT / 'm56_pack_20261119.running'
MIN_E_SLACK_GB = 5


def say(**k):
    k['utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(k) + '\n')
    print(json.dumps(k), flush=True)


def inventory(src):
    """{arcname: (kind, size)} for src and everything under it; symlinks are entries, never followed (as tarfile.add)."""
    out = {src.name: ('d', 0)}
    for dp, dn, fn in os.walk(src):
        rel = Path(dp).relative_to(src)
        for n in dn + fn:
            mode = os.lstat(Path(dp) / n).st_mode
            kind = 'l' if stat.S_ISLNK(mode) else 'd' if stat.S_ISDIR(mode) else 'f'
            out[(Path(src.name) / rel / n).as_posix()] = (kind, os.lstat(Path(dp) / n).st_size if kind == 'f' else 0)
    return out


def contents(tar):
    got = {}
    with tarfile.open(tar) as t:
        for m in t:
            got[m.name.rstrip('/')] = ('d' if m.isdir() else 'l' if (m.issym() or m.islnk()) else 'f', m.size if m.isfile() else 0)
    return got


def lines(p):
    return [json.loads(l) for l in p.read_text(encoding='utf-8-sig').splitlines() if l.strip()] if p.exists() else []


def rel_of(row):
    r = row['rel']
    return (r[0] if isinstance(r, list) else r).replace('\\', '/')


def pack(src, dst, drop):
    """Tar src to dst (verified entry by entry), then drop(src). Returns (entries, bytes) or None when nothing was done."""
    inv = inventory(src)
    n, b = sum(v[0] == 'f' for v in inv.values()), sum(v[1] for v in inv.values())
    if not (dst.exists() and contents(dst) == inv):
        free = shutil.disk_usage(dst.parent).free / 2**30
        if free < b / 2**30 * 1.05 + MIN_E_SLACK_GB:
            sys.exit(f'FAIL room {src} needs {b / 2**30:.1f} GB, {dst.parent} free {free:.1f}')
        part = dst.with_name(dst.name + '.part')
        part.unlink(missing_ok=True); dst.unlink(missing_ok=True)
        with tarfile.open(part, 'w', format=tarfile.PAX_FORMAT) as t:
            t.add(src, arcname=src.name)
        if contents(part) != inv:
            sys.exit(f'FAIL verify {src}: tar entries differ from the tree')
        os.replace(part, dst)
    register(dst.relative_to(E).as_posix(), n, b)
    drop(src)
    return n, b


def register(rel, n, b):
    if rel not in {rel_of(r) for r in lines(ELIST)}:
        with ELIST.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'rel': rel, 'files': n, 'bytes': b, 'mode': 'tar', 'by': 'offload-pack-20261119'}) + '\n')


def candidates():
    junction = {rel_of(r) for r in lines(JLIST)}
    done = {rel_of(r) for r in lines(CLOUD) if r.get('event') == 'DELETED_E'}
    out = []
    for rel in dict.fromkeys(rel_of(r) for r in lines(ELIST)):
        p = E / rel
        if rel in junction or rel in done or rel.endswith('.tar') or not p.is_dir() or p.is_junction() or (G / rel).exists():
            continue
        out.append(rel)
    return out


def selftest():
    d = Path(tempfile.mkdtemp())
    try:
        s = d / 'item'; (s / 'a/b').mkdir(parents=True); (s / 'empty').mkdir()
        (s / 'a/x.bin').write_bytes(b'12345'); (s / 'a/b/y.txt').write_bytes(b''); (s / 'z.json').write_bytes(b'{}')
        inv = inventory(s)
        assert inv == {'item': ('d', 0), 'item/a': ('d', 0), 'item/a/b': ('d', 0), 'item/empty': ('d', 0), 'item/a/x.bin': ('f', 5),
                       'item/a/b/y.txt': ('f', 0), 'item/z.json': ('f', 2)}, inv
        t = d / 'item.tar'
        with tarfile.open(t, 'w', format=tarfile.PAX_FORMAT) as f:
            f.add(s, arcname='item')
        assert contents(t) == inv
        (s / 'a/x.bin').write_bytes(b'123456')
        assert contents(t) != inventory(s)  # a changed size is caught
        (s / 'a/x.bin').write_bytes(b'12345')
        global E, ELIST
        E, ELIST = d, d / 'list.jsonl'
        assert pack(s, t, shutil.rmtree) == (3, 7) and not s.exists() and t.exists()
        assert [rel_of(r) for r in lines(ELIST)] == ['item.tar']
        with tarfile.open(t) as f:
            f.extractall(d / 'back', filter='data')
        assert inventory(d / 'back/item') == inv
        print('SELFTEST_OK')
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest(); sys.exit(0)
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else ''
    todo = [r for r in candidates() if only in r]
    if '--dry' in sys.argv:
        for r in todo:
            print(r)
        print(len(todo), 'items'); sys.exit(0)
    RUN.write_text(datetime.now(timezone.utc).isoformat())
    try:
        for rel in todo:
            n, b = pack(E / rel, E / (rel + '.tar'), shutil.rmtree)
            say(event='PACKED', rel=rel, entries=n, bytes=b, tar=rel + '.tar')
    finally:
        RUN.unlink(missing_ok=True)
    say(event='PACK_END', items=len(todo), e_free_gb=round(shutil.disk_usage('E:/').free / 2**30, 1))
