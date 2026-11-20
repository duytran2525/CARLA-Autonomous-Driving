"""2026-11-20 (user 19/11: D free > 80 GB and E free > 150 GB before any process continues). Drive uploads dropped to ~0.7 GB/h
(DriveFS read 0.19 MB/s), so E could not reach 150 GB in time. D has room above 80 GB: this holds NEED_GB of verified tars
that have NOT started uploading (no copy on G:) in D:\\m56-hold-20261120\\<rel> until E has room again. Per tar: copy to D ->
sha256 of both -> delete the E tar -> log. Nothing is deleted without an equal hash. Run it with the uploader stopped
(a tar moved while robocopy reads it would kill the uploader). The uploader skips items missing on E.
Move back later (E has room): robocopy D:\\m56-hold-20261120 E:\\m56-offload-20261116 /E /MOV, then the uploader sees them again.
usage: python -I hold-tars-on-d-20261120.py NEED_GB [--dry]"""
import hashlib, json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
E, G, H = Path('E:/m56-offload-20261116'), Path('G:/My Drive/m56-offload-20261116'), Path('D:/m56-hold-20261120')
LOG = OUT / 'm56_hold_20261120.jsonl'
MIN_D_AFTER_GB = 95  # leaves the A/B + pairs (about 10 GB) and the 80 GB gate with margin


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def say(**k):
    k['utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(k) + '\n')
    print(json.dumps(k), flush=True)


def pick(need_gb):
    tars = sorted((p for p in E.rglob('*.tar') if not (G / p.relative_to(E)).exists()), key=lambda p: -p.stat().st_size)
    out, tot = [], 0
    for p in tars:  # biggest first, never overshooting NEED_GB by more than 0.5 GB
        if tot >= need_gb * 2**30:
            break
        if tot + p.stat().st_size <= need_gb * 2**30 + 2**29:
            out.append(p); tot += p.stat().st_size
    return out, tot


if __name__ == '__main__':
    need = float(sys.argv[1])
    todo, tot = pick(need)
    d_free = shutil.disk_usage('D:/').free / 2**30
    if d_free - tot / 2**30 < MIN_D_AFTER_GB:
        sys.exit(f'REFUSED: D free {d_free:.1f} GB - {tot / 2**30:.1f} GB < {MIN_D_AFTER_GB} GB after the move')
    if '--dry' in sys.argv:
        for p in todo:
            print(p.relative_to(E), round(p.stat().st_size / 2**30, 2))
        print(len(todo), 'tars', round(tot / 2**30, 1), 'GB; D free after', round(d_free - tot / 2**30, 1)); sys.exit(0)
    for p in todo:
        rel = p.relative_to(E); dst = H / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
        a, b = sha(p), sha(dst)
        if a != b or p.stat().st_size != dst.stat().st_size:
            say(event='HOLD_VERIFY_FAIL', rel=rel.as_posix()); dst.unlink(missing_ok=True); sys.exit(5)
        p.unlink()
        say(event='HELD_ON_D', rel=rel.as_posix(), bytes=dst.stat().st_size, sha256=a)
    say(event='HOLD_END', tars=len(todo), d_free_gb=round(shutil.disk_usage('D:/').free / 2**30, 1), e_free_gb=round(shutil.disk_usage('E:/').free / 2**30, 1))
