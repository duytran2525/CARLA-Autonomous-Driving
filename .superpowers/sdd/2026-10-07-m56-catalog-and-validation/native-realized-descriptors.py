"""A-SEL2 realized descriptors (docs/m56/DESCRIPTOR_SPECS_M56_ASEL2_20261108.md, frozen 8bdf074), offline from sealed raw.
Per scene A/B directory (fixture-frozen.json, ab-result.json, run/native/observation): for each action A and B the TRIGGER
frame (= the frozen t0 event of the category's metric window), then
  C/L/M: vN_r = NPC mean planar speed over the frames [T - 1 s, T]; G_r = e_entry route station - EGO front station at T
         (product m56.geometry project_route / world_vertices on the frozen EGO route);
  I/O:   vE_r = EGO mean planar speed over [T - 1 s, T].
Each value is exact (Fraction of the binary64 result) and bound to the sha256 of the observation file of frame T.
LrefN_r and gap_r: not implemented yet (reported missing; the comparison then stays BLOCKED, never guessed).
usage: python -I native-realized-descriptors.py OUT.json SCENE_AB_DIR [SCENE_AB_DIR ...]"""
import glob, hashlib, json, math, sys
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import CODE  # noqa: F401  (m56 import path)
from m56.model import decode_record
from m56.geometry import project_route, world_vertices

g = lambda x: float.fromhex(x['binary64']) if isinstance(x, dict) and 'binary64' in x else (
    float(F(x['numerator'], x['denominator'])) if isinstance(x, dict) else float(x))


def speed(actor):
    v = actor['velocity']; v = [g(c) for c in v] if isinstance(v, list) else [g(v[k]) for k in ('x', 'y', 'z')]
    return math.hypot(v[0], v[1])


def scene(d):
    d = Path(d); fx = json.loads((d / 'fixture-frozen.json').read_text(encoding='utf-8'))
    ab = json.loads((d / 'ab-result.json').read_text(encoding='utf-8'))
    cat = d.name.split('-')[2][0]
    files = {}
    for f in glob.glob(str(d / 'run' / 'native' / 'observation' / '*.json')):
        o = json.loads(Path(f).read_text(encoding='utf-8'))
        if o.get('actors'):
            files[o['frame']] = (f, o)
    route = decode_record('DirectedRoute', fx['routes']['EGO'])
    e_entry = F(fx['domain']['e_entry']['route_station']['numerator'], fx['domain']['e_entry']['route_station']['denominator']) \
        if cat in 'CLM' else None
    out = {}
    for act in ('A', 'B'):
        ev = dict((k, v) for k, v in ab['episodes'][act]['events'])
        T = ev.get('TRIGGER')
        if T is None or T not in files:
            continue
        path, obs = files[T]
        ref = {'uri': str(Path(path).resolve()), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
               'bytes': Path(path).stat().st_size, 'version': '1', 'method': 'sha256', 'kind': 'NATIVE_RAW', 'frame': T}
        win = [files[k][1] for k in range(T - 20, T + 1) if k in files]
        role = 'NPC' if cat in 'CLM' else 'EGO'
        sp = [speed(next(a for a in o['actors'] if a['role'] == role)) for o in win]
        out.setdefault('vN' if cat in 'CLM' else 'vE', {})[act] = (str(F(sum(sp) / len(sp))), ref, len(sp))
        if cat in 'CLM':
            ego = next(a for a in obs['actors'] if a['role'] == 'EGO')
            body = decode_record('BodyRecord', ego['body']); pose = decode_record('Transform6', ego['pose'])
            st = [project_route(p, route) for p in world_vertices(body, pose)]
            st = [F(x) for x in st if not hasattr(x, 'reasons')]
            if st:
                out.setdefault('G', {})[act] = (str(e_entry - max(st)), ref, 1)
    return {'scene': d.name, 'category': cat, 'values': out,
            'missing': [n for n in (('vN', 'G', 'LrefN') if cat in 'CL' else ('vN', 'G') if cat == 'M' else ('vE', 'gap' if cat == 'I' else 'G'))
                        if set(out.get(n, {})) != {'A', 'B'}]}


if __name__ == '__main__':
    rows = [scene(x) for x in sys.argv[2:]]
    Path(sys.argv[1]).open('x', encoding='utf-8').write(json.dumps({'spec': 'DESCRIPTOR_SPECS_M56_ASEL2_20261108 (8bdf074)', 'scenes': rows}, indent=1))
    for r in rows:
        print(r['scene'], {n: {a: float(F(v[0])) for a, v in vv.items()} for n, vv in r['values'].items()}, 'missing', r['missing'])
