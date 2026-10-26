"""Report-only probe (2026-10-26, prereg v6 c): width of the Town06 road-mesh seam that makes ground_projection fall
through (label NONE at -1.98 m). For each corner of outputs/m56_ground_probe_v6.log whose v5 error > 0.05 m:
ground_projection at offsets r in {0.05 .. 0.5} m along +-x, +-y; label and error. Own server 2610, one map load.
python -I native-seam-probe.py GROUND_PROBE_JSON"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import own_server, load, now, WS

rows = [r for r in json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))['rows'] if (r['error'] or 0) > .05]
OUT = WS.parents[2] / 'outputs' / f'm56_seam_probe_{now()}.json'


def log(**k):
    print(json.dumps(k, default=str), flush=True)


res = []
with own_server(log) as (client, proc, start):
    import carla
    world = load(client, 'Town06')
    for r in rows:
        x, y, z = r['corner']; per = {}
        for d in (.05, .1, .15, .2, .3, .5):
            hits = []
            for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
                g = world.ground_projection(carla.Location(x + dx, y + dy, z + 2.), 10.)
                hits.append(None if g is None else (round(abs(z - g.location.z), 3), str(g.label)))
            per[str(d)] = hits
        res.append({'frame': r['frame'], 'role': r['role'], 'corner': r['corner'], 'by_offset': per}); log(**res[-1])
with open(OUT, 'x', encoding='utf-8') as f:
    json.dump({'note': 'report-only seam probe (v6 c)', 'rows': res}, f, indent=1)
print('DONE', OUT)
