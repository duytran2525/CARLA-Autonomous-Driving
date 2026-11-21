"""2026-11-21 offline diagnosis of the F03-S1 v21 A/B arm B (OUTER_TIMEOUT at 875 frames; pair reasons TARGET_PROGRAM_MISMATCH,
GROUND_PROOF_INVALID, CONTACT_PROOF_INVALID, REVERSE_COMMAND_REPLAY_UNPROVEN). Read-only on the sealed run, no CARLA, writes
nothing. Duy delegation "chẩn đoán offline cho tôi" 21/11.
usage: M56_CODE=<m56-v21> M56_RECIPE=v6 python -I diag-v21-f03-b-offline.py timing|events|integrity [ACTION=B]"""
import sys, time, json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401,E402
from m56.model import decode_record, load_json  # noqa: E402
from m56.runtime import load_episode, _ref, _known_events  # noqa: E402

RUN = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261120T192818Z\M56-P-F03-S1\run\episodes\M56-P-F03-S1')


def load(action):
    root = RUN / action
    fixture = decode_record('CompiledFixture', load_json(root / 'fixture.json'))
    ev = load_episode(root)
    store = SimpleNamespace(root=root)
    extra = {f.stem: _ref(store, f.name) for f in sorted(root.glob('*_ref.json'))}
    ev = replace(ev, integrity={**ev.integrity, **extra}, source=tuple(dict.fromkeys((*ev.source, *extra.values()))))
    return ev, fixture


def timing(action):
    import cProfile, pstats
    ev, fx = load(action)
    frames = list(ev.raw)
    print('frames', len(frames), 'first/last frame no', frames[0].frame, frames[-1].frame, 'simtime', float(frames[0].simtime), float(frames[-1].simtime))
    for n in [n for n in (50, 100, 200, 300, 450, 600, 750, 875) if n <= len(frames)]:
        t = time.perf_counter(); k = _known_events(frames[:n], fx); dt = time.perf_counter() - t
        print(f'n={n:4d} _known_events {dt:6.2f} s  events={[e.name for e in k]}', flush=True)
    pr = cProfile.Profile(); pr.enable(); _known_events(frames, fx); pr.disable()
    pstats.Stats(pr).sort_stats('cumulative').print_stats(14)


def events(action):
    from m56.metrics import detect_events
    ev, fx = load(action)
    frames = tuple(ev.raw)
    print('frames', len(frames), 'simtime', float(frames[0].simtime), '->', float(frames[-1].simtime))
    for e in detect_events(frames, fx):
        print(e.name, e.frame, float(e.time))
    for i in range(0, len(frames), max(1, len(frames) // 25)):
        f = frames[i]
        ego = next(a for a in f.actors if a.role == 'EGO')
        c = ego.readback
        print(i, f.frame, round(float(f.simtime), 2), 'ego speed', round(float(ego.velocity[0] ** 2 + ego.velocity[1] ** 2) ** .5, 3) if hasattr(ego, 'velocity') and ego.velocity else None,
              'gear', c.gear if c else None, 'rev', c.reverse if c else None, 'brake', float(c.brake) if c else None)


def history(action):
    """Cost of the per-tick reverse-history work at n rows (response._reverse_inputs lines 767-784): read+decode the cumulative
    history file the kit rewrote, then per row: payload + source bytes compare."""
    from m56.evidence import _read_trajectory, _source_bytes, _payload
    from m56.metrics import _frame_refs
    ev, fx = load(action)
    frames = list(ev.raw)
    for k in (100, 300, 600, 875):
        f = frames[k - 1]
        ref = decode_record('SourceRef', f.integrity['reverse_history_ref'] if isinstance(f.integrity['reverse_history_ref'], dict) else __import__('m56.model', fromlist=['encode_record']).encode_record(f.integrity['reverse_history_ref']))
        _read_trajectory.cache_clear() if hasattr(_read_trajectory, 'cache_clear') else None
        t = time.perf_counter(); h = _read_trajectory(ref); t_read = time.perf_counter() - t
        t = time.perf_counter(); ok = 0
        for o in h:
            refs = _frame_refs(o)
            payload = _payload({'boot': o.boot, 'world': o.world, 'frame': o.frame, 'simtime': o.simtime, 'actors': o.actors})
            ok += bool(refs) and any(_source_bytes(r) == payload for r in refs)
        t_rows = time.perf_counter() - t
        print(f'tick row {k}: history rows {len(h)} size {ref.bytes / 1e6:.1f} MB  read+decode {t_read:.2f} s  per-row checks {t_rows:.2f} s  ok {ok}', flush=True)


def forward(action):
    """After the reverse: EGO station/speed/commands vs NPC, every 20 frames from the reverse (is EGO commanded to move, and by what)."""
    import math
    from m56.metrics import _metric_station
    ev, fx = load(action)
    frames = tuple(ev.raw)
    er, nr = fx.routes['EGO'], fx.routes.get('NPC')
    for i in range(100, len(frames), 20):
        f = frames[i]
        e = next(a for a in f.actors if a.role == 'EGO')
        n = next((a for a in f.actors if a.role == 'NPC'), None)
        cmd = e.commands[0] if e.commands else None
        c = e.readback
        es = _metric_station((e.pose.x, e.pose.y, e.pose.z), er)
        ns = _metric_station((n.pose.x, n.pose.y, n.pose.z), nr) if n is not None and nr is not None else None
        d = math.dist((e.pose.x, e.pose.y), (n.pose.x, n.pose.y)) if n is not None else None
        sp = lambda a: round(math.hypot(float(a.velocity[0]), float(a.velocity[1])), 3) if a is not None and a.velocity else None  # noqa: E731
        print(f'{f.frame} t={float(f.simtime):6.1f} egoS={float(es):8.3f} egoV={sp(e)} npcS={float(ns) if ns is not None else None} npcV={sp(n)} '
              f'dist={round(d, 2) if d is not None else None} cmd={(cmd.kind, cmd.cause, float(cmd.target_kmh) if cmd.target_kmh is not None else None) if cmd else None} '
              f'rb(g={c.gear if c else None},thr={round(float(c.throttle), 2) if c else None},brk={round(float(c.brake), 2) if c else None}) plan={e.plan_queue}')


def dense(action, lo='8118', hi='8215'):
    """Every frame in [lo, hi]: command and the applied-control readback (steer / hand_brake are what reverse_intent checks)."""
    ev, _fx = load(action)
    for f in ev.raw:
        if int(lo) <= f.frame <= int(hi):
            e = next(a for a in f.actors if a.role == 'EGO')
            cmd = e.commands[0] if e.commands else None
            c = e.readback
            print(f.frame, (cmd.kind, cmd.cause) if cmd else None,
                  f'rb(g={c.gear} rev={c.reverse} manual={c.manual_gear_shift} steer={float(c.steer):.5f} hand={c.hand_brake} thr={float(c.throttle):.3f} brk={float(c.brake):.3f})' if c else None)


if __name__ == '__main__':
    {'timing': timing, 'events': events, 'history': history, 'forward': forward, 'dense': dense}[sys.argv[1]](*sys.argv[2:])
