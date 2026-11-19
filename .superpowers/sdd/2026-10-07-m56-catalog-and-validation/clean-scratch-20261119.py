"""2026-11-19 (user: D: must be > 80 GB free before any CARLA start). Deletes ONLY these finished pytest/kit scratch dirs of
the M56 test runs (looked at first: pytest --basetemp trees, nothing in docs/m56 refers to them, no process had them open;
the v19 F-test result is in outputs/*ftests*.stdout.txt). pyt-v20 is NOT listed: the v20 run still writes there.
`rmdir /s /q` removes a symlink/junction itself without following it. usage: python -I clean-scratch-20261119.py [--dry]"""
import json, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
LOG = OUT / 'm56_scratch_clean_20261119.jsonl'
DIRS = [Path(p) for p in (
    r'D:\tmp\pyt-v19full', r'D:\tmp\pyt-v19b', r'D:\tmp\pyt-v19a', r'D:\tmp\pyt-u', r'D:\tmp\pyt-u3', r'D:\tmp\pyt-py2',
    r'D:\tmp\f05kit-4j3aragf', r'D:\tmp\f05kit-gcr849j0', r'D:\tmp\f05kit-i4gc_ou6', r'D:\tmp\f05kit-rq08q258', r'D:\tmp\f05kit-ixlndaru',
    str(OUT / 'pytest-tmp-v18'))]


def free():
    return round(shutil.disk_usage('D:/').free / 2**30, 1)


if __name__ == '__main__':
    for d in DIRS:
        row = {'dir': str(d), 'exists': d.exists(), 'd_free_gb_before': free(), 'utc': datetime.now(timezone.utc).isoformat(timespec='seconds')}
        if d.exists() and '--dry' not in sys.argv:
            assert d.parent in (Path(r'D:\tmp'), OUT), d
            row['rc'] = subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', str(d)]).returncode
            row['left'] = d.exists(); row['d_free_gb_after'] = free()
        with LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row) + '\n')
        print(json.dumps(row), flush=True)
