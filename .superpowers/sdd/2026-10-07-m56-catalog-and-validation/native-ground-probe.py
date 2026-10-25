"""Report-only probe (2026-10-26): why recorded-ground-contact-v1 reports ~1.98 m ground error in M05-A (Town06).
Replays the kit's own query (world.ground_projection from 2 m above each bottom body corner, 10 m search) at the
recorded poses of the bad frames, in an EMPTY world (no actors), plus world.cast_ray over the same segment with
every labelled hit. If the empty world gives a ground hit at the corner height, the recorded hit was an actor.
Own server 2610, one map load. python -I native-ground-probe.py EPISODE_DIR TOWN FRAME[,FRAME...]"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load, now, WS
from m56.model import decode_record
from m56.geometry import world_vertices

run, town, frames = Path(sys.argv[1]), sys.argv[2], [int(x) for x in sys.argv[3].split(',')]
OUT = WS.parents[2] / 'outputs' / f'm56_ground_probe_{now()}.json'


def log(**k):
    print(json.dumps(k, default=str), flush=True)


from m56.runtime import load_episode
_BY = {f.frame: f for f in load_episode(run).raw}  # run = sealed EPISODE dir (frames by real frame id)


def actors_at(frame):
    return _BY[frame].actors


rows = []
with own_server(log) as (client, proc, start):
    import carla
    world = load(client, town)
    for fr in frames:
        for a in actors_at(fr):
            for v in sorted(world_vertices(a.body, a.pose), key=lambda v: v[2])[:4]:
                top = carla.Location(float(v[0]), float(v[1]), float(v[2]) + 2.)
                g = world.ground_projection(top, 10.)
                hits = world.cast_ray(top, carla.Location(float(v[0]), float(v[1]), float(v[2]) - 8.))
                rows.append({'frame': fr, 'role': a.role, 'corner': [float(c) for c in v],
                             'ground': None if g is None else [g.location.z, str(g.label)],
                             'error': None if g is None else abs(float(v[2]) - g.location.z),
                             'cast_ray': [[h.location.z, str(h.label)] for h in hits]})
                log(**rows[-1])
with open(OUT, 'x', encoding='utf-8') as f:
    json.dump({'note': 'report-only ground probe, empty world', 'run': str(run), 'town': town, 'rows': rows}, f, indent=1)
print('DONE', OUT)
