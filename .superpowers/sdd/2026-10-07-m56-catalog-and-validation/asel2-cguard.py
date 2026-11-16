"""C: guard for native M56 batches (2026-11-16). C: filled to 0 on 15-16/11 (system-managed pagefile grew to 31 GB);
an episode dying on a full disk / commit is a spent P5 A/B. Every 60 s: log C: free, pagefile.sys size and commit headroom
to outputs/m56_cguard_<utc>.jsonl. If C: free < --min-gb, or commit headroom < --min-commit-gb, write a GRACEFUL STOP
(outputs/m56_asel2_STOP, empty) once, so asel2-stopper.py halts at the first safe point (never inside an A/B window).
Never overwrites an existing STOP file. usage: python -I asel2-cguard.py [--min-gb 10] [--min-commit-gb 4]"""
import argparse, ctypes, json, os, shutil, time
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
STOP = OUT / 'm56_asel2_STOP'


class MEMSTAT(ctypes.Structure):
    _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong)] + \
               [(n, ctypes.c_ulonglong) for n in ('total_phys', 'avail_phys', 'commit_limit', 'commit_avail',
                                                 'total_virtual', 'avail_virtual', 'avail_ext')]


def sample():
    m = MEMSTAT(); m.dwLength = ctypes.sizeof(MEMSTAT); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    try:
        pf = os.stat('C:/pagefile.sys').st_size
    except OSError:
        pf = None
    g = lambda b: None if b is None else round(b / 2**30, 2)
    return {'utc': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'c_free_gb': g(shutil.disk_usage('C:/').free),
            'pagefile_gb': g(pf), 'commit_limit_gb': g(m.commit_limit), 'commit_avail_gb': g(m.commit_avail),
            'phys_avail_gb': g(m.avail_phys)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--min-gb', type=float, default=10); ap.add_argument('--min-commit-gb', type=float, default=4)
    ap.add_argument('--once', action='store_true')
    # --wait-commit-gb N: block (CARLA down) until commit headroom >= N and C: free >= --min-gb, then exit 0. 16/11: Town12
    # CARLA + prepare took ~14.7 GB commit on a ~30 GB baseline of other apps (limit 48.2) -> tripped at 3.4 GB left.
    ap.add_argument('--wait-commit-gb', type=float); a = ap.parse_args()
    if a.wait_commit_gb is not None:
        t = 0
        while True:
            s = sample()
            if s['commit_avail_gb'] >= a.wait_commit_gb and s['c_free_gb'] >= a.min_gb:
                print('ROOM_OK', json.dumps(s), flush=True); raise SystemExit(0)
            if t % 300 == 0:
                print('ROOM_WAIT need', a.wait_commit_gb, json.dumps(s), flush=True)
            time.sleep(30); t += 30
    log = OUT / f"m56_cguard_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    fired = False
    while True:
        s = sample()
        low = s['c_free_gb'] < a.min_gb or s['commit_avail_gb'] < a.min_commit_gb
        if low and not fired:
            fired = True
            if STOP.exists():
                s['action'] = 'LOW (STOP file already present, left as is)'
            else:
                STOP.write_bytes(b''); s['action'] = 'LOW -> graceful STOP written'
        with log.open('a', encoding='utf-8') as f:
            f.write(json.dumps(s) + '\n')
        print(json.dumps(s), flush=True)
        if a.once:
            break
        time.sleep(60)
