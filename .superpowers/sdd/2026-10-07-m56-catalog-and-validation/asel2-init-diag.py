"""A-SEL2 diagnostic (read-only, sealed raw): why every Town12 A/B of batch 1 is INITIALIZATION_INVALID.
For each action: the frozen spawn pose (fixture), the first post-spawn observation of each actor (product decode), and
each clause of m56.evidence._initial_state_matches (x, y, yaw within 1e-4 of the float32 image; 0 <= z_frozen - z_obs <= 0.02;
|pitch|, |roll| vs the rule of the loaded product; speed <= 0.10). Also where the evaluator takes the first observation.
usage: M56_CODE=<product> python -I asel2-init-diag.py AB_SCENE_DIR [...]"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import CODE  # noqa: F401  (M56_CODE first on sys.path)
from m56.model import decode_record, load_json
from m56.response import _f32
from m56.metrics import _speed
from m56.runtime import load_episode

for d in (Path(x).resolve() for x in sys.argv[1:]):
    fx = decode_record('CompiledFixture', load_json(d / 'fixture-frozen.json'))
    for act in ('A', 'B'):
        ev = load_episode(d / 'run' / 'episodes' / d.name / act)
        if ev is None:
            print(d.name, act, 'NOT_SEALED'); continue
        first = ev.raw[0] if ev.raw else None
        print(f'{d.name} {act}: frames {len(ev.raw)} first frame {first.frame if first else None} simtime {first.simtime if first else None}')
        for a in (first.actors if first else ()):
            fz = fx.poses[a.role]; p = a.pose
            yaw = (p.yaw - _f32(fz.yaw) + 180) % 360 - 180
            sp = _speed(a.velocity)
            print(f'  {a.role}: frozen ({float(fz.x):.4f},{float(fz.y):.4f},{float(fz.z):.4f}) p{float(fz.pitch):.3f} y{float(fz.yaw):.3f} r{float(fz.roll):.3f}'
                  f' | obs ({float(p.x):.4f},{float(p.y):.4f},{float(p.z):.4f}) p{float(p.pitch):.3f} y{float(p.yaw):.3f} r{float(p.roll):.3f}')
            print(f'     dx {float(p.x - _f32(fz.x)):+.5f} dy {float(p.y - _f32(fz.y)):+.5f} dyaw {float(yaw):+.5f}'
                  f' dz(fz-obs) {float(fz.z - p.z):+.4f} speed {float(sp) if sp is not None else None:.3f}')
