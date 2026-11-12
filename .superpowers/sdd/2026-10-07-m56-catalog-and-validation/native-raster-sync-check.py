"""2026-11-12 check for A-SEL2 technical fix 5 (synchronous raster): recompute the dv1 drivable union of already-run scenes
with the current native_v2_common and compare the WKT bytes with the ones the A/B wrote. No fixture, no episode, no A/B.
Same inputs as native-v2-ab.run_scene up to drivable-union.wkt (routes, centre, radius). Scenes run in the given order on
one fresh server, so the first one rasters right after load_world (the slow case).
env as the A/B: M56_RECIPE=v6 M56_DRIVABLE=dv1 M56_SPECTATOR=1 M56_NO_RENDER=1 M56_CODE=<product>
usage: python -I native-raster-sync-check.py REVISION.json TOWN AB_ROOT SCENE[,SCENE...]   -> prints SAME/DIFF per scene"""
import hashlib, json, math, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import (WORK, DV1, V6, drivable_union, load, own_server, stream_to, v2_routes)
from m56.model import decode_record, load_json

assert V6 and DV1, 'run with M56_RECIPE=v6 M56_DRIVABLE=dv1'
REVISION, TOWN, AB_ROOT, IDS = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), sys.argv[4].split(',')
log = lambda **k: print(json.dumps({'t': time.strftime('%H:%M:%S'), **k}, default=str), flush=True)


def plain(x):
    from fractions import Fraction as F
    if isinstance(x, dict):
        if set(x) == {'binary64'}:
            return float.fromhex(x['binary64'])
        if set(x) == {'numerator', 'denominator'}:
            return F(x['numerator'], x['denominator'])
        return {k: plain(v) for k, v in x.items()}
    return [plain(v) for v in x] if isinstance(x, list) else x


cands = {c['id']: c for c in load_json(REVISION)['candidates']}
with own_server(log) as (client, proc, start):
    world = load(client, TOWN); m = world.get_map()
    for sid in IDS:
        c = decode_record('Candidate', cands[sid])
        v2 = dict(c.environment['runtime_recipe_v2'])
        pj = Path(v2['prepare_json']) if Path(v2['prepare_json']).is_absolute() else WORK / v2['prepare_json']
        raw = json.loads(pj.read_text(encoding='utf-8'))
        prep = {k: (v if k == 'poses' else plain(v)) for k, v in raw.items()}
        notation = {a.role: a.route_recipe['route'] for a in c.actors}
        routes, rows, cont = v2_routes(prep, notation, c.town, plain)
        poses = {k: decode_record('Transform6', v) for k, v in prep['poses'].items()}
        ref = (AB_ROOT / sid / 'drivable-union.wkt').read_bytes()
        # centre = the conflict overlap box centre, as in run_scene; read back from the A/B log instead of recomputing the
        # certificates (the spectator point of STREAM_TO is that centre + 50 m in z)
        ev = json.loads((AB_ROOT / 'ab-log.json').read_text(encoding='utf-8'))
        sp = next(e['spectator'] for e in ev if e.get('event') == 'STREAM_TO' and e.get('scene') == sid)
        stream_to(world, sp[0], sp[1], sp[2] - 50.)
        center = (sp[0], sp[1])
        radius = max(90., max(math.dist((poses[r].x, poses[r].y), center) for r in poses) + 20.)
        radius = max(radius, max(math.dist((float(t.x), float(t.y)), center) for r in routes.values() for t in r.transforms) + 20.)
        sync0 = world.get_settings().synchronous_mode
        t0 = time.monotonic()
        wkt = drivable_union(m, center, radius, world, routes).wkt.encode('utf-8')
        log(event='RASTER', scene=sid, seconds=round(time.monotonic() - t0, 1), sync_before=sync0,
            sync_after=world.get_settings().synchronous_mode, result='SAME' if wkt == ref else 'DIFF',
            sha_new=hashlib.sha256(wkt).hexdigest()[:16], sha_ref=hashlib.sha256(ref).hexdigest()[:16],
            len_new=len(wkt), len_ref=len(ref))
    log(event='CHECK_END')
