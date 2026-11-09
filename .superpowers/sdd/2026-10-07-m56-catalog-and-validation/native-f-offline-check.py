"""Offline F01 compile test (no CARLA): fabricated straight x-axis prepare + box drivable -> native-f-ab compile_scene,
consumer contracts, pair contract. Run with M56_CODE=m56-v13."""
import importlib.util, json, sys, hashlib
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace

T = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\.superpowers\sdd\2026-10-07-m56-catalog-and-validation')
OUT = Path(sys.argv[1]); OUT.mkdir(parents=False, exist_ok=False)
REV = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_c0_partial_io_asel2fbase2_20261109T160045Z\c0-partial-v5-frozen-revision.json')
MECH = sys.argv[2] if len(sys.argv) > 2 else 'F01'
TOWN = {'F01': 'Town13', 'F02': 'Town12'}[MECH]
CID = {'F01': 'M56-P-F01-S1', 'F02': 'M56-P-F02'}[MECH]
sys.path.insert(0, str(T))
s_ = importlib.util.spec_from_file_location('fab', T / 'native-f-ab.py'); fab = importlib.util.module_from_spec(s_); s_.loader.exec_module(fab)
from native_v2_common import write_ref  # noqa: E402
from native_f_common import f_routes, f_responses  # noqa: E402
from m56.model import CompiledFixture, SourceRef, Transform6, decode_record, encode_record, load_json  # noqa: E402
from m56.metrics import _F_CONTRACTS  # noqa: E402
from m56.response import _forward_contract  # noqa: E402
from shapely.geometry import box  # noqa: E402

MAP = 'a' * 64
rows = [{'x': 0.2 * i, 'y': 0., 'z': 0., 'pitch': 0., 'yaw': 0., 'roll': 0., 'road': 1165, 'lane': -2, 's': 0.2 * i} for i in range(951)]
k = 225  # NPC route starts at x = 45
rf = OUT / 'routes-f.json'; rf.write_text(json.dumps({'EGO': rows, 'NPC': rows[k:] if MECH == 'F01' else rows}), encoding='utf-8')
bbox = {'location': [0., 0., .7684], 'extent': [1.8566, .9093, .7684], 'rotation': [0., 0., 0.]}
poses = ({'EGO': Transform6(.004, 0., .01, 0., 0., 0.), 'NPC': Transform6(45.004, 0., .01, 0., 0., 0.)} if MECH == 'F01'
         else {'EGO': Transform6(45.004, 0., .01, 0., 0., 0.), 'NPC': Transform6(.004, 0., .01, 0., 0., 0.)})
prep = {'scene': CID, 'town': TOWN, 'category': 'F', 'mechanism': MECH, 'recipe': 'f-v1', 'status': 'PREPARED',
        'bbox': bbox, 'site': {'road': 1165, 'lane': -2, 'section': 0}, 'map_hash': MAP,
        'targets': {'EGO': F(4), 'NPC': F(17, 5) if MECH == 'F01' else F(5)},
        'markers': {'EGO': F(10), 'NPC': F(20)} if MECH == 'F01' else {'EGO': F(55), 'NPC': F(30)},
        'routes_f': str(rf), 'routes_f_sha256': hashlib.sha256(rf.read_bytes()).hexdigest(),
        'poses': {r: encode_record(p) for r, p in poses.items()}, 'grounds': {'EGO': 0., 'NPC': 0.},
        'sections_m': ({'F01_BRAKE_START': {'route': 'NPC', 'station': 32.05}, 'F01_END': {'route': 'NPC', 'station': 52.05},
                        'DESTINATION': {'route': 'EGO', 'station': 110.75}} if MECH == 'F01' else
                       {'F02_END': {'route': 'EGO', 'station': 61.0123 + 60}, 'DESTINATION': {'route': 'EGO', 'station': 126.0123}})}
if MECH == 'F02':
    prep['nominal_front_t0_m'] = 61.0123
pref = write_ref(OUT / 'prepare.json', prep, 'G4_PREPARATION')
raw = json.loads((OUT / 'prepare.json').read_text(encoding='utf-8'))
pp = {k_: (v if k_ == 'poses' else fab.plain(v)) for k_, v in raw.items()}
routes, _, _ = f_routes(pp, fab.plain, TOWN)
data = load_json(REV)
c = decode_record('Candidate', next(x for x in data['candidates'] if x['id'] == CID))
readiness = {'targets_mps': prep['targets'], 'markers_m': prep['markers']}
c = replace(c, actors=tuple(replace(a, destination=routes[a.role].destination) for a in c.actors), responses=f_responses(c, routes),
            environment={**c.environment, 'readiness': readiness,
                         'runtime_recipe_v2': {'status': 'PREPARED', 'recipe': 'f-v1', 'prepare_json': str(OUT / 'prepare.json')}})
fab.init([str(REV), TOWN, c.id], out_root=OUT / 'abroot')
sd = fab.root / c.id; sd.mkdir()
dpath = OUT / 'drivable.wkt'; drv = box(-10., -6., 200., 6.); dpath.write_text(drv.wkt, encoding='utf-8')
dref = SourceRef(str(dpath), hashlib.sha256(dpath.read_bytes()).hexdigest(), dpath.stat().st_size, '1', 'test', 'NATIVE_DRIVABLE')
fixture, _, _, _ = fab.compile_scene(c, SimpleNamespace(map=MAP), 'pid0@t0', 'w1', sd, (drv, dref))
print('FIXTURE', type(fixture).__name__, getattr(fixture, 'reasons', ''))
assert isinstance(fixture, CompiledFixture), fixture
p = fixture.pair
assert (p.names, p.units, p.estimators, p.window) == _F_CONTRACTS[MECH], p
if MECH == 'F02':
    assert fixture.sections['F02_END'].route_station - fixture.domain.topology['nominal_front_t0_m'] == 60
    print('F02_END - nominal_front_t0 == 60 OK')
print('PAIR_CONTRACT OK')
for r in fixture.responses:
    print(r.actor_role, r.action_id, _forward_contract(r, fixture))
print('SECTIONS', {k_: str(v.route_station) for k_, v in fixture.sections.items()}, 'DEST', fixture.routes['EGO'].destination)
d = fixture.domain
print('DOMAIN', [str(x.route_station) for x in (d.e_entry, d.e_exit, d.n_entry, d.n_exit)])
print('ALL_OK')
