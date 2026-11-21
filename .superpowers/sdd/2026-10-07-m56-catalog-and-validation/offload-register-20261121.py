"""2026-11-21 (user: "upload các file cache và các file tạm không cần thiết nữa lên google drive"; precedent 17/11: upload to Drive,
then delete the local copy, keep only the cloud copy). Moves derived pair bundles (d09/w05 source copies; pair-result.json stays on D)
into the uploader's root E:\\m56-offload-20261116\\m56_pair_bundles_20261121\\<pair> and registers each as an item of
outputs/m56_offload_20261117_E.jsonl, so offload-pack-20261119.py tars it (verified entry by entry) and offload-e-to-drive-20261119.py
uploads the tar and deletes it from E only once DriveFS shows a cloud id with the same size.
  python -I offload-register-20261121.py e-bundles          E:\\m56_pair_bundles\\<pair> (same volume: a rename)
  python -I offload-register-20261121.py d-pairs DIR...      outputs\\m56_v6_pair_*\\<scene>\\{d09,w05-A,w05-B} -> E (copy, verify, delete D)
Log: outputs/m56_offload_20261121_register.jsonl. Rerun-safe (registered rels are not added twice)."""
import json, os, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
ROOT = Path('E:/m56-offload-20261116'); SUB = 'm56_pair_bundles_20261121'
ELIST, LOG = OUT / 'm56_offload_20261117_E.jsonl', OUT / 'm56_offload_20261121_register.jsonl'
BUNDLE_PARTS = ('d09', 'w05-A', 'w05-B')


def say(**k):
    k['utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(k) + '\n')
    print(json.dumps(k), flush=True)


def files_of(p):
    return {f.relative_to(p).as_posix(): f.stat().st_size for f in p.rglob('*') if f.is_file()}


def registered():
    if not ELIST.exists():
        return set()
    out = set()
    for l in ELIST.read_text(encoding='utf-8-sig').splitlines():
        if l.strip():
            r = json.loads(l)['rel']
            out.add((r[0] if isinstance(r, list) else r).replace('\\', '/'))
    return out


def register(rel, n, b):
    if rel not in registered():
        with ELIST.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'rel': rel, 'files': n, 'bytes': b, 'mode': 'dir', 'by': 'offload-register-20261121'}) + '\n')


def e_bundles():
    src_root = Path('E:/m56_pair_bundles')
    (ROOT / SUB).mkdir(parents=True, exist_ok=True)
    for d in sorted(p for p in src_root.iterdir() if p.is_dir()) if src_root.exists() else ():
        dst = ROOT / SUB / d.name
        if dst.exists():
            sys.exit(f'FAIL exists {dst}')
        before = files_of(d)
        os.rename(d, dst)  # same volume
        after = files_of(dst)
        if after != before:
            sys.exit(f'FAIL verify {dst}')
        register(f'{SUB}/{d.name}', len(after), sum(after.values()))
        say(event='MOVED_E', rel=f'{SUB}/{d.name}', files=len(after), bytes=sum(after.values()))
    if src_root.exists() and not any(src_root.iterdir()):
        src_root.rmdir()


def d_pairs(dirs):
    for pair in map(Path, dirs):
        for scene in (p for p in pair.iterdir() if p.is_dir()):
            if not (scene / 'pair-result.json').exists():
                sys.exit(f'FAIL no pair-result.json in {scene}')
            for part in BUNDLE_PARTS:
                src = scene / part
                if not src.exists():
                    continue
                dst = ROOT / SUB / pair.name / scene.name / part
                before = files_of(src)
                shutil.copytree(src, dst, dirs_exist_ok=True)
                if files_of(dst) != before:
                    sys.exit(f'FAIL verify {dst}')
                shutil.rmtree(src)
            rel = f'{SUB}/{pair.name}'
            got = files_of(ROOT / rel)
            say(event='MOVED_D', rel=rel, files=len(got), bytes=sum(got.values()), kept_on_d='pair-result.json')
        register(f'{SUB}/{pair.name}', *(lambda g: (len(g), sum(g.values())))(files_of(ROOT / SUB / pair.name)))


if __name__ == '__main__':
    if sys.argv[1] == 'e-bundles':
        e_bundles()
    elif sys.argv[1] == 'd-pairs':
        d_pairs(sys.argv[2:])
    else:
        sys.exit(__doc__)
