"""native-io-ab.py under io-i-v1.2 for category-I scenes (PREREG_M56_IO_I_RECIPE_V1_2_20261115.md + addendum H,
PREREG_M56_IO_I_RECIPE_V1_2_ADDENDUM_H_PROBE3_20261115.md). native-io-ab.py is loaded as a module and NOT edited.
With --ab, before the one A/B (P5) of a scene, on the SAME compiled fixture and server, with its OWN store, owned backend
and Kit (built by the same setup lines as the A/B, recompiled from run_scene's bytes):
  G2  fixture check: DESTINATION - X >= L + 10 m (L = EGO body length)              else IO_I12_TAIL_SHORT
  probe 3: the product's own runtime.run_episode, action A, in <scene>/probe3 (never <scene>/run, never fed to a consumer),
      truncated by one stop rule (addendum H): stop at the first frame with t_clear seen, or > TRIGGER + 2.3 s, or
      > ready + NO_TRIGGER_S without TRIGGER. Truncation = runtime.VALIDATION_S set to 0 for that episode only.
  G1  ready - first frame <= 14.0 s (runner's own _ready predicate, replayed on the same frames)  else READINESS_PROBE3
  G3  t_clear - TRIGGER <= 2.3 s; t_clear = first frame >= TRIGGER with every NPC bbox vertex outside the fixture's
      EGO_TARGET lane box (the source lane)                                         else SOURCE_CLEAR_LATE
Any gate failing: BLOCKED_FIXTURE, no A/B (P5 unspent). All gates pass: run_scene's own A/B block, unchanged.
  python -I native-io-ab-i12.py REVISION.json TOWN ID[,ID...] --ab   (same env as native-io-ab.py)"""
import ast, importlib.util, json
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ioab', HERE / 'native-io-ab.py')
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)   # module level: argv, output root, receipt
runtime = A.runtime
from m56.evidence import open_run

G1_READY_S, G3_CLEAR_S, NO_TRIGGER_S = F(14), F(23, 10), F(20)
TAIL_EXTRA_M = 10


def _inside(box, x, y):
    """Point in the world-axis lane box (xy bounds of its 3D vertex set); the boundary counts as inside, so 'left the box'
    is the conservative reading."""
    xs = [p[0] for p in box]; ys = [p[1] for p in box]
    return min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys)


class Probe:
    """Online measurements of probe 3, fed by the runner's own per-tick _known_events call."""
    def __init__(self, fixture):
        self.fixture, self.box = fixture, fixture.domain.topology['action_regions']['EGO_TARGET']
        self.boundary = self.settled = self.ready = self.trigger = self.clear = self.event_clear = None
        self.stop = None

    def see(self, frames, events):
        f = frames[-1]
        if self.boundary is None:
            self.boundary = frames[0].simtime - frames[0].dt
        if self.settled is None:  # runner: first frame >= SETTLE_S after the boundary
            if f.simtime - self.boundary >= runtime.SETTLE_S:
                self.settled = f
            return
        if self.ready is None:
            if runtime._ready(frames, self.settled, self.fixture):
                self.ready = f
            return
        names = {e.name: e for e in events}
        if self.trigger is None and 'TRIGGER' in names:
            self.trigger = names['TRIGGER']
        if self.event_clear is None and 'SOURCE_CLEAR_CONFIRMED' in names:
            self.event_clear = names['SOURCE_CLEAR_CONFIRMED'].time
        if self.trigger is not None and self.clear is None and f.simtime >= self.trigger.time:
            npc = next((a for a in f.actors if a.role == 'NPC'), None)
            body = None if npc is None else A.world_vertices(npc.body, npc.pose)   # body.vertices are vehicle-local
            if body and not any(_inside(self.box, v[0], v[1]) for v in body):
                self.clear = f.simtime
        if self.clear is not None:
            self.stop = 'T_CLEAR_SEEN'
        elif self.trigger is not None and f.simtime - self.trigger.time > G3_CLEAR_S:
            self.stop = 'TRIGGER_PLUS_2_3_S'
        elif self.trigger is None and f.simtime - self.ready.simtime > NO_TRIGGER_S:
            self.stop = 'NO_TRIGGER'

    def gates(self):
        s = lambda t: None if t is None else str(t)
        ready_s = None if self.ready is None else self.ready.simtime - self.boundary
        clear_s = None if self.clear is None or self.trigger is None else self.clear - self.trigger.time
        reasons = []
        if ready_s is None or ready_s > G1_READY_S:
            reasons.append('READINESS_PROBE3')
        elif clear_s is None or clear_s > G3_CLEAR_S:
            reasons.append('SOURCE_CLEAR_LATE')
        return {'pass': not reasons, 'reasons': reasons, 'stop': self.stop, 'ready_after_first_frame_s': s(ready_s),
                'trigger_time': s(self.trigger and self.trigger.time), 't_clear': s(self.clear),
                't_clear_minus_trigger_s': s(clear_s), 'product_source_clear_confirmed_time': s(self.event_clear),
                'limits': {'G1_ready_s': '14', 'G3_clear_s': '23/10', 'no_trigger_after_ready_s': '20'}}


PROBE = {'p': None}
_known = runtime._known_events


def _known_hook(frames, fixture):
    events = _known(frames, fixture)
    p = PROBE['p']
    if p is not None and frames:
        p.see(frames, events)
        if p.stop is not None:
            runtime.VALIDATION_S = 0   # runner breaks at its own validation check of this frame (after ready)
    return events


runtime._known_events = _known_hook
def tail_check(fixture, sd):
    """L = 2 x the native EGO body half-length (the a2-bbox.json compile wrote, as prepare's L)."""
    ext = json.loads((sd / 'a2-bbox.json').read_text(encoding='utf-8'))['extent'][0]
    L = F(float.fromhex(ext['binary64'])) * 2
    room = fixture.sections['DESTINATION'].route_station - fixture.sections['X'].route_station
    return {'destination_minus_x_m': str(room), 'L_m': float(L), 'pass': room >= L + TAIL_EXTRA_M}


def _i12_probe3(ctx, backend, fixture, scene, sd):
    """Called from the recompiled run_scene with the probe-3 context/backend (own store <scene>/probe3, own owned backend,
    own Kit: nothing it caches is shared with the A/B backend). True = all gates pass, run the A/B."""
    out = {'scene': scene, 'recipe': 'io-i-v1.2 + addendum H (native-io-ab-i12.py)'}
    if fixture.domain.topology.get('category') != 'I':
        reasons = ['IO_I12_NOT_CATEGORY_I']
    else:
        out['G2'] = tail_check(fixture, sd)
        reasons = [] if out['G2']['pass'] else ['IO_I12_TAIL_SHORT']
    if not reasons:
        p = PROBE['p'] = Probe(fixture); old = runtime.VALIDATION_S
        try:
            runtime.run_episode(replace(ctx, backend=backend), fixture, 'A')
        finally:
            PROBE['p'] = None; runtime.VALIDATION_S = old
        out['probe3'] = p.gates()
        stop = ctx.store.root / 'runner/stop.json'
        out['probe3']['runner_stop'] = stop.read_text(encoding='utf-8').splitlines()[-1] if stop.exists() else None
        reasons = out['probe3']['reasons']
    out.update(status='PASS' if not reasons else 'BLOCKED_FIXTURE', reasons=reasons)
    (sd / 'io-i12-gates.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    A.log(event='IO_I12_GATES', **out)
    return not reasons


# run_scene recompiled from native-io-ab.py's own bytes: its A/B setup block (run store, owned backend, Kit, plan source,
# policy bind) is inserted once more BEFORE itself with the namespace renamed to probe3, followed by the gate call.
_src = (HERE / 'native-io-ab.py').read_text(encoding='utf-8')
_fn = next(n for n in ast.parse(_src).body if isinstance(n, ast.FunctionDef) and n.name == 'run_scene')
_seg = ''.join(_src.splitlines(keepends=True)[_fn.lineno - 1:_fn.end_lineno])
START = "    store = open_run(sd / 'run', c.id, own.writer)\n"
END = "    out = runtime.run_ab(replace(ctx, backend=backend), fixture, c.id)\n"
assert _seg.count(START) == 1 and _seg.count(END) == 1, 'I12_RUN_SCENE_SITE'
_a, _b = _seg.index(START), _seg.index(END)
_block = _seg[_a:_b]
assert _block.count("sd / 'run'") == 1 and _block.count("sd / 'plan-source.json'") == 1, 'I12_BLOCK_SITE'
_probe = (_block.replace("sd / 'run'", "sd / 'probe3'").replace("sd / 'plan-source.json'", "sd / 'probe3-plan-source.json'")
          + "    if not _i12_probe3(ctx, backend, fixture, c.id, sd):  # io-i-v1.2 addendum H\n        return\n")
A._i12_probe3 = _i12_probe3
A._I12_RUN_SCENE_SRC = _seg[:_a] + _probe + _seg[_a:]
exec(compile(A._I12_RUN_SCENE_SRC, str(HERE / 'native-io-ab.py') + ' [io-i-v1.2 probe 3]', 'exec'), A.__dict__)

if __name__ == '__main__':
    A.main()
