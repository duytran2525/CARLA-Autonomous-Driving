"""2026-11-20 inverse of hold-tars-on-d-20261120.py: E has room again (>= 150 GB after the tars), so each held tar goes back
D:\\m56-hold-20261120\\<rel> -> E:\\m56-offload-20261116\\<rel>. Per tar: sha256 of the D copy must equal the sha256 the hold
logged (HELD_ON_D) -> copy to E -> sha256 of the E copy must equal it -> delete the D copy -> log. Run with the uploader
stopped (a half-written tar on E could be copied). usage: python -I unhold-tars-20261120.py [--dry]"""
import hashlib, json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
E, H = Path('E:/m56-offload-20261116'), Path('D:/m56-hold-20261120')
HOLD_LOG, LOG = OUT / 'm56_hold_20261120.jsonl', OUT / 'm56_unhold_20261120.jsonl'
MIN_E_AFTER_GB = 150


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


if __name__ == '__main__':
    held = {r['rel']: r for r in map(json.loads, HOLD_LOG.read_text(encoding='utf-8').splitlines()) if r['event'] == 'HELD_ON_D'}
    todo = [(rel, r) for rel, r in held.items() if (H / rel).is_file()]
    need = sum(r['bytes'] for _, r in todo) / 2**30
    e_free = shutil.disk_usage('E:/').free / 2**30
    if e_free - need < MIN_E_AFTER_GB:
        sys.exit(f'REFUSED: E free {e_free:.1f} GB - {need:.1f} GB < {MIN_E_AFTER_GB} GB')
    if '--dry' in sys.argv:
        print(len(todo), 'tars', round(need, 1), 'GB; E free after', round(e_free - need, 1)); sys.exit(0)
    for rel, r in todo:
        src, dst = H / rel, E / rel
        if sha(src) != r['sha256'] or src.stat().st_size != r['bytes']:
            say(event='UNHOLD_SRC_MISMATCH', rel=rel); sys.exit(5)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if sha(dst) != r['sha256']:
            say(event='UNHOLD_VERIFY_FAIL', rel=rel); dst.unlink(missing_ok=True); sys.exit(6)
        src.unlink()
        say(event='BACK_ON_E', rel=rel, bytes=r['bytes'], sha256=r['sha256'])
    say(event='UNHOLD_END', tars=len(todo), d_free_gb=round(shutil.disk_usage('D:/').free / 2**30, 1), e_free_gb=round(shutil.disk_usage('E:/').free / 2**30, 1))
