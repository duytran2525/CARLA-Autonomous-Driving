"""A-SEL2 diagnostic (read-only): why CLEAR_N_CONFIRMED never fires although the NPC drives through (Town12 batch 1).
For each frame after the NPC front passes n_exit: product _section_margin(NPC vertices, n_exit) and _section_corridor,
plus the NPC body z range vs the section z limits.
usage: M56_CODE=<product> python -I asel2-clear-diag.py AB_SCENE_DIR [ACTION]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import CODE  # noqa: F401
from m56.model import decode_record, load_json
from m56.runtime import load_episode
from m56.geometry import world_vertices, project_route
from m56.metrics import _section_margin, _section_corridor

d = Path(sys.argv[1]).resolve(); act = sys.argv[2] if len(sys.argv) > 2 else 'A'
fx = decode_record('CompiledFixture', load_json(d / 'fixture-frozen.json'))
ev = load_episode(d / 'run' / 'episodes' / d.name / act)
sec = fx.domain.n_exit
print('n_exit station', float(sec.route_station), 'limits', {k: float(v) for k, v in sec.limits.items()})
shown = 0
for f in ev.raw:
    npc = next((a for a in f.actors if a.role == 'NPC'), None)
    if npc is None:
        continue
    vs = world_vertices(npc.body, npc.pose)
    st = [project_route(p, fx.routes['NPC']) for p in vs]
    front = max(float(s) for s in st if not hasattr(s, 'reasons')) if any(not hasattr(s, 'reasons') for s in st) else None
    if front is None or front < float(sec.route_station):
        continue
    m = _section_margin(vs, sec); c = _section_corridor(vs, sec)
    if 0 <= shown <= 16:
        print(f'frame {f.frame} front {front:.2f} margin_min {None if m is None else round(float(min(m)), 3)} corridor {c}'
              f' y [{min(float(v[1]) for v in vs):.3f}, {max(float(v[1]) for v in vs):.3f}] x [{min(float(v[0]) for v in vs):.2f}, {max(float(v[0]) for v in vs):.2f}] yaw {float(npc.pose.yaw):.2f}')
    shown += 1
    if shown > 200:
        break
