"""A-SEL2 diagnostic (read-only): which clause of m56.evidence._initialization_integrity rejects each batch-1 Town12
episode. Runs the product function on the sealed episode after wrapping every ValueError raise site: the source of
the product function is exec'd with `raise ValueError(...)` replaced by a recorder, so the product's exact logic is used.
usage: M56_CODE=<product> python -I asel2-init-clause.py AB_SCENE_DIR [...]"""
import inspect, re, sys, textwrap
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import CODE  # noqa: F401
import m56.evidence as ev_mod
from m56.model import decode_record, load_json
from m56.runtime import load_episode

src = textwrap.dedent(inspect.getsource(ev_mod._initialization_integrity))
src = re.sub(r"raise ValueError\('([^']*)'\)", r"raise ValueError('CLAUSE:\1')", src)
src = src.replace("except (KeyError,TypeError,ValueError,AttributeError,ZeroDivisionError):\n        return ('INITIALIZATION_INVALID',),()",
                  "except (KeyError,TypeError,ValueError,AttributeError,ZeroDivisionError) as _e:\n        return ('INITIALIZATION_INVALID:'+repr(_e)[:160],),()")
ns = dict(vars(ev_mod)); exec(compile(src, 'init_clause', 'exec'), ns)
probe = ns['_initialization_integrity']
import importlib.util, tempfile
_s = importlib.util.spec_from_file_location('pairmod', Path(__file__).resolve().parent / 'native-v6-pair.py')
pm = importlib.util.module_from_spec(_s)
_argv = sys.argv; sys.argv = [sys.argv[0]]
_s.loader.exec_module(pm)  # module-level OUT dir is created, unused
sys.argv = _argv
for d in (Path(x).resolve() for x in sys.argv[1:]):
    fx = decode_record('CompiledFixture', load_json(d / 'fixture-frozen.json'))
    for act in ('A', 'B'):
        dest = Path(tempfile.mkdtemp(prefix='m56init_'))
        e, _, _ = pm.evidence(d, act, dest, fx)  # the pair tool's exact episode (fresh W05, sealed pointers)
        print(d.name, act, probe(e, fx), flush=True)

# sub-conditions of the 'actual initial state' clause on the boundary (pre-observation) frame
from m56.evidence import _pre_observation
from m56.response import _f32
from m56.metrics import _speed
for d in (Path(x).resolve() for x in sys.argv[1:]):
    fx = decode_record('CompiledFixture', load_json(d / 'fixture-frozen.json'))
    e, _, _ = pm.evidence(d, 'A', Path(tempfile.mkdtemp(prefix='m56init_')), fx)
    b = _pre_observation(e)
    decl = {a.role: a for a in fx.actors}
    for a in b.actors:
        fz = fx.poses[a.role]; p = a.pose
        yaw = (p.yaw - _f32(fz.yaw) + 180) % 360 - 180
        print(d.name, a.role, {'dx': float(p.x - _f32(fz.x)), 'dy': float(p.y - _f32(fz.y)), 'dyaw': float(yaw),
              'dz': float(fz.z - p.z), 'pitch': float(p.pitch), 'fz_pitch': float(fz.pitch), 'roll': float(p.roll),
              'speed': float(_speed(a.velocity)) if _speed(a.velocity) is not None else None,
              'decl_speed0': decl[a.role].initial_speed_mps == 0, 'decl_pose_eq': decl[a.role].pose == fz,
              'bp_eq': a.body.blueprint == decl[a.role].blueprint, 'route_valid': a.route_valid}, flush=True)
