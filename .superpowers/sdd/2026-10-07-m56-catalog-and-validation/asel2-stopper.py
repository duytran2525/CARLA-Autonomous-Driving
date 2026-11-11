"""A-SEL2 safe stop (2026-11-11). Runs detached BESIDE the queue (a running bash script must never be edited).
Every 15 s it checks for a trigger:
  - the file outputs/m56_asel2_STOP exists (content "now" = stop immediately, even mid-episode: that scene is then
    INFRA_INTERRUPTED and its P5 quota is spent; any other content = graceful), or
  - the time is past --at (UTC ISO, e.g. 2026-11-11T00:00:00Z).
Once triggered it stops at the first SAFE point. UNSAFE = (a) the newest scene dir of a running native A/B job
(native-v2-ab / native-io-ab / native-f-ab --ab) has fixture-frozen.json but no ab-result.json (the episode window: a
kill there spends the scene's single P5 A/B), or (b) a result writer runs (native-v6-pair, native-v5-revision/reeval).
Raster, prepare, probes and chain waits are safe. io/f A/B write no ab-result.json, so their whole fixture->next-scene
span counts as unsafe (conservative).
Stop = kill ONLY our own trees: the chain bash scripts first (so no next step starts), then native python jobs and the
watchdog, then the CarlaUE4 bound to -carla-rpc-port=2610. Then it writes outputs/m56_asel2_stop_<utc>.json (trigger,
killed processes, per-scene status of the A/B roots since --since) and outputs/M56_SAFE_TO_SHUTDOWN.txt.
usage: python -I asel2-stopper.py --at ISO [--since ISO] [--dry]"""
import argparse, glob, json, os, re, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / 'outputs'
STOP = OUT / 'm56_asel2_STOP'
now = lambda: datetime.now(timezone.utc)
iso = lambda t: t.isoformat(timespec='seconds')
OURS = re.compile(r'run-asel2-|run-f0[1-3]-|run-io-|asel2-watchdog\.py|native-[\w-]+\.py|native_f_\w+\.py|carla-rpc-port=2610')
AB = re.compile(r'native-(v2-ab|io-ab|f-ab)\.py')
WRITER = re.compile(r'native-v6-pair\.py|native-v5-revision\.py|native-v5-reeval\.py')
ROOTS = {'v2-ab': 'm56_v2_ab_{t}_2*', 'io-ab': 'm56_io_ab_{t}_2*', 'f-ab': 'm56_f_ab_{t}_2*'}
SINCE = [0.]  # epoch s; set from --since in main (roots older than this are ignored)


def procs():
    # 2026-11-11: foreign non-ASCII command lines crashed the utf-8 decode (stdout None) -> force UTF-8 + replace.
    ps = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
          "Get-CimInstance Win32_Process | ForEach-Object { '{0}|{1}|{2}' -f $_.ProcessId, $_.ParentProcessId, "
          "($_.CommandLine -replace '[\\r\\n]', ' ') }")
    r = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True, timeout=120,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f'PROCESS_LIST_FAILED rc={r.returncode}')
    out = []
    for line in r.stdout.splitlines():
        p = line.split('|', 2)
        if len(p) == 3 and p[0].isdigit() and int(p[0]) != os.getpid() and 'asel2-stopper.py' not in p[2]:
            out.append((int(p[0]), int(p[1] or 0), p[2]))
    return out


def scene_dirs(root):
    return sorted((d for d in Path(root).iterdir() if d.is_dir() and d.name.startswith('M56-P-')),
                  key=lambda d: (d / 'a2-bbox.json').stat().st_mtime if (d / 'a2-bbox.json').exists() else d.stat().st_mtime)


def unsafe(ps):
    why = []
    for pid, _, cmd in ps:
        if WRITER.search(cmd):
            why.append(f'result writer running pid {pid}: {WRITER.search(cmd).group(0)}')
        m = AB.search(cmd)
        if not m or (m.group(1) in ('f-ab', 'io-ab') and '--ab' not in cmd):  # compile mode runs no episode
            continue
        town = re.search(r'\b(Town\d+\w*)\b', cmd)
        roots = [r for r in sorted(glob.glob(str(OUT / ROOTS[m.group(1)].format(t=town.group(1) if town else '*'))))
                 if os.path.getmtime(r) >= SINCE[0]]  # an old root must never read as unsafe forever
        if not roots:
            continue
        ds = scene_dirs(roots[-1])
        if ds and (ds[-1] / 'fixture-frozen.json').exists() and not (ds[-1] / 'ab-result.json').exists():
            why.append(f'episode window: {Path(roots[-1]).name}/{ds[-1].name} (fixture frozen, no ab-result)')
    return why


def status(since):
    rows = {}
    for pat in ROOTS.values():
        for root in sorted(glob.glob(str(OUT / pat.format(t='*')))):
            if os.path.getmtime(root) < since.timestamp():
                continue
            for d in scene_dirs(root):
                st = ('DONE' if (d / 'ab-result.json').exists() else 'FIXTURE_NO_RESULT' if (d / 'fixture-frozen.json').exists()
                      else 'NO_FIXTURE')
                rows[f'{Path(root).name}/{d.name}'] = st
    return rows


def kill(ps):
    ours = [(pid, ppid, cmd) for pid, ppid, cmd in ps if OURS.search(cmd) and 'claude' not in cmd.lower()]
    order = ([p for p in ours if 'bash' in p[2].lower() and '.sh' in p[2]]
             + [p for p in ours if 'python' in p[2].lower()]
             + [p for p in ours if 'carla-rpc-port=2610' in p[2]])
    done = []
    for pid, _, cmd in order:
        r = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, text=True)
        done.append({'pid': pid, 'cmd': cmd[:300], 'rc': r.returncode})
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--at', default='9999-01-01T00:00:00Z'); ap.add_argument('--since', default='2026-11-10T14:50:00Z')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    at = datetime.fromisoformat(a.at.replace('Z', '+00:00')); since = datetime.fromisoformat(a.since.replace('Z', '+00:00'))
    SINCE[0] = since.timestamp()
    if a.dry:
        ps = procs()
        print(json.dumps({'unsafe': unsafe(ps), 'would_kill': [c[:160] for _, _, c in ps if OURS.search(c) and 'claude' not in c.lower()],
                          'status': status(since)}, indent=1))
        return
    print(json.dumps({'t': iso(now()), 'event': 'STOPPER_START', 'at': iso(at), 'stop_file': str(STOP)}), flush=True)
    last = None
    while True:
        text = STOP.read_text(errors='replace').strip().lower() if STOP.exists() else None
        trigger = 'STOP_FILE_NOW' if text == 'now' else 'STOP_FILE' if text is not None else 'TIME' if now() >= at else None
        if trigger:
            try:
                ps = procs()
            except Exception as e:  # never die on a transient listing failure: retry next poll
                print(json.dumps({'t': iso(now()), 'event': 'PROCS_RETRY', 'error': repr(e)[:300]}), flush=True)
                time.sleep(15); continue
            why = [] if trigger == 'STOP_FILE_NOW' else unsafe(ps)
            if not why:
                killed = kill(ps); time.sleep(5)
                left = [c[:160] for _, _, c in procs() if OURS.search(c) and 'claude' not in c.lower()]
                port = subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout
                rec = {'t': iso(now()), 'event': 'STOPPED', 'trigger': trigger, 'killed': killed, 'left': left,
                       'port_2610_listening': ':2610 ' in port and 'LISTENING' in port.split(':2610 ', 1)[-1][:200],
                       'status': status(since)}
                f = OUT / f"m56_asel2_stop_{now().strftime('%Y%m%dT%H%M%SZ')}.json"
                f.write_text(json.dumps(rec, indent=1), encoding='utf-8')
                if not left and not rec['port_2610_listening']:  # never a false green light
                    (OUT / 'M56_SAFE_TO_SHUTDOWN.txt').write_text(
                        f"{rec['t']} STOPPED ({trigger}); record {f.name}\n", encoding='utf-8')
                else:
                    print(json.dumps({'event': 'NOT_SAFE_AFTER_KILL', 'left': left}), flush=True)
                print(json.dumps({k: rec[k] for k in ('t', 'event', 'trigger', 'left', 'port_2610_listening')}), 'RECORD', f, flush=True)
                return
            if why != last:
                print(json.dumps({'t': iso(now()), 'event': 'WAIT_UNSAFE', 'trigger': trigger, 'why': why}), flush=True)
                last = why
        time.sleep(15)


if __name__ == '__main__':
    main()
