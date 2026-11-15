"""Offline self-test of native-io-ab-i12.py probe-3 logic and native-io-prepare-i12.py wiring (no CARLA).
  M56_CODE=<product> python -I test-native-io-ab-i12.py REVISION.json
Import side effects: native-io-ab.py creates outputs/m56_io_compile_ImportTest_<utc>/ (receipt only) and native-io-prepare.py
creates outputs/m56_v2_prepare_ImportTest_<utc>/ (empty): move both to the trash folder."""
import importlib.util, sys
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace as NS

here = Path(__file__).resolve().parent
rev = sys.argv[1]
sys.argv = [str(here / 'native-io-ab-i12.py'), rev, 'ImportTest', 'M56-P-X']
s = importlib.util.spec_from_file_location('i12', here / 'native-io-ab-i12.py')
I = importlib.util.module_from_spec(s); s.loader.exec_module(I)
rt = I.runtime
assert rt._known_events is I._known_hook and 'probe 3' in I.A.run_scene.__code__.co_filename
src = I.A._I12_RUN_SCENE_SRC
k = [src.index(x) for x in ("sd / 'probe3'", "_i12_probe3(ctx, backend", "sd / 'run'", "runtime.run_ab(")]
assert k == sorted(k) and src.count('Kit(authority') == 2 and src.count('runtime.bind_owned(ctx)') == 2, k
I.A.world_vertices = lambda body, pose: body.vertices   # synthetic frames below give world vertices directly

BOX = [(F(0), F(0), F(-1)), (F(10), F(0), F(-1)), (F(10), F(3), F(3)), (F(0), F(3), F(3))]   # source lane: y in [0, 3]
fx = NS(domain=NS(topology={'action_regions': {'EGO_TARGET': BOX}, 'category': 'I'}))
DT = F(1, 20)


def frame(t, npc_y):
    verts = [(F(5), F(npc_y) + d, F(0)) for d in (F(-1), F(1))]
    return NS(simtime=F(t), dt=DT, actors=(NS(role='NPC', body=NS(vertices=verts), pose=None),))


def run(ready_at, trig_at, clear_at, end=40):
    """Ticks of 0.05 s from 0.05; NPC inside the box until clear_at, then at y = 6."""
    rt._ready = lambda frames, settled, fixture: ready_at is not None and frames[-1].simtime >= ready_at
    p = I.Probe(fx); frames = []
    for k in range(1, int(end / DT)):
        t = k * DT
        frames.append(frame(t, 6 if clear_at is not None and t >= clear_at else 1))
        ev = (NS(name='TRIGGER', time=F(trig_at)),) if trig_at is not None and t >= trig_at else ()
        p.see(frames, ev)
        if p.stop:
            return p, t
    return p, None


p, t = run(F(5), F(8), F('9.5'))
g = p.gates()
assert g['pass'] and p.stop == 'T_CLEAR_SEEN' and t == F('9.5') and F(g['t_clear_minus_trigger_s']) == F('1.5'), g
assert F(g['ready_after_first_frame_s']) == 5, g
p, t = run(F(5), F(8), F('10.5'))
assert p.gates()['reasons'] == ['SOURCE_CLEAR_LATE'] and p.stop == 'TRIGGER_PLUS_2_3_S' and t == F('10.35'), (p.gates(), t)
p, t = run(F(5), F(8), F('10.3'))   # exactly 2.3 s: passes (<=)
assert p.gates()['pass'], p.gates()
p, t = run(None, None, None)
assert p.gates()['reasons'] == ['READINESS_PROBE3'] and t is None
p, t = run(F('14.05'), F(16), F(17))   # ready 14.05 s after the first frame (boundary 0) > 14.0
assert p.gates()['reasons'] == ['READINESS_PROBE3'], p.gates()
p, t = run(F(5), None, None)
assert p.stop == 'NO_TRIGGER' and t == F('25.05') and p.gates()['reasons'] == ['SOURCE_CLEAR_LATE']

# hook: sets VALIDATION_S = 0 only while a probe is active and has stopped
old = rt.VALIDATION_S
I._known = lambda frames, fixture: ()
I.PROBE['p'] = NS(see=lambda f, e: None, stop='X'); I._known_hook([frame(1, 1)], fx)
assert rt.VALIDATION_S == 0
rt.VALIDATION_S = old; I.PROBE['p'] = None; I._known_hook([frame(1, 1)], fx)
assert rt.VALIDATION_S == old

# prepare-i12 wiring: the G2 expression replaced once, wired where v16's io-v1.5 wrapper calls _prepare_o
sys.argv = [str(here / 'native-io-prepare-i12.py'), 'ImportTest', 'M56-P-X']
s = importlib.util.spec_from_file_location('p12', here / 'native-io-prepare-i12.py')
Pm = importlib.util.module_from_spec(s); s.loader.exec_module(Pm)
assert Pm.V._prepare_o is Pm.M._prepare_o_i12 and Pm.M._prepare_o is Pm.V._prepare_o_v15
assert 'io-i-v1.2 G2' in Pm.M._prepare_o_i12.__code__.co_filename
print('OK native-io-ab-i12 probe 3 + prepare-i12 wiring', I.A.root)
