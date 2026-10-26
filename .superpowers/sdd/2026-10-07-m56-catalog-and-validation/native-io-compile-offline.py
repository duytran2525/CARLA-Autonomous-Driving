"""Offline I/O fixture compile (no server): native-io-ab.compile_scene with the drivable union read from an earlier
native compile's drivable-union.wkt and a stub server identity (map hash from the preparation). For iterating on the
compile/contract code only: the fixture is NOT admissible (stub boot/world); the native compile + admission runs once
through native-io-ab.py.  python -I native-io-compile-offline.py REVISION.json SCENE DRIVABLE.wkt
"""
import importlib.util, json, sys
from pathlib import Path
from fractions import Fraction as F
from types import SimpleNamespace
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
rev, scene, wkt_path = sys.argv[1:4]
import native_v2_common as C  # noqa: E402
from shapely import wkt  # noqa: E402
C.now = (lambda f: lambda: 'offline-' + f())(C.now)
C.drivable_union = lambda *a, **k: wkt.loads(Path(wkt_path).read_text(encoding='utf-8'))
data = json.loads(Path(rev).read_text(encoding='utf-8'))
town = next(c['town'] for c in data['candidates'] if c['id'] == scene)
sys.argv = [str(here / 'native-io-ab.py'), rev, town, scene]
spec = importlib.util.spec_from_file_location('ioab', here / 'native-io-ab.py'); AB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AB)
from m56.model import CompiledFixture, decode_record, load_json  # noqa: E402
c = decode_record('Candidate', next(x for x in load_json(Path(rev))['candidates'] if x['id'] == scene))
prep = json.loads(Path(c.environment['runtime_recipe_v2']['prepare_json']).read_text(encoding='utf-8'))
sd = AB.root / scene; sd.mkdir()
fx, drivable, rows, *_ = AB.compile_scene(c, SimpleNamespace(id='offline'), None, SimpleNamespace(map=prep['map_hash']),
                                          SimpleNamespace(pid=0), 'offline', sd)
if not isinstance(fx, CompiledFixture):
    print('BLOCKED_FIXTURE', list(fx.reasons)); sys.exit(1)
fref = AB.write_ref(sd / 'fixture-frozen.json', fx, 'FROZEN_FIXTURE')
from m56 import response as R  # noqa: E402
from m56.metrics import _map_offset  # noqa: E402
from m56.model import Transform6  # noqa: E402
for r in fx.responses:  # lateral + normative + every reference phase
    R._lateral_contract(r, fx); R._forward_contract(r, fx)
    for cause in (R._program(r)['initial'], *(t['cause'] for t in R._program(r)['transitions'])):
        R._reference_response(r, cause)
print('contracts OK (lateral, forward/normative, references)')
# map offset (e_lat_peak source): poses on the EGO route shifted along the CARLA right vector
import math  # noqa: E402
ego = fx.routes['EGO']; ref = fx.domain.topology['map_reference']
for st in (110., 150., 175.):
    i = max(k for k, a in enumerate(ego.arc) if float(a) <= st); t, u = ego.transforms[i], ego.transforms[i + 1]
    mx, my, yaw = (t.x + u.x) / 2, (t.y + u.y) / 2, math.radians(t.yaw)  # segment midpoint: a vertex is a refused corner tie
    for off in (0., 1.75, 3.5):
        v = _map_offset(Transform6(mx - math.sin(yaw) * off, my + math.cos(yaw) * off, t.z, 0., t.yaw, 0.), ref, fx.pair.reference)
        assert v is not None and abs(float(v) - off) < 1e-3, (st, off, v)
print('map offset OK at stations 110/150/175, offsets 0/1.75/3.5')
# stock binding dry run (create_stock_driver with a stub stock backend; no server)
class Stub:
    def __init__(self, actor, config): self.config = config
    def set_global_plan(self, plan, stop_waypoint_creation, clean_queue): assert plan
    def follow_speed_limits(self, value): pass
R._stock_factory = Stub
source = AB.write_ref(sd / 'plan-source.json', {'rule': 'offline dry run'}, 'G4_STOCK_SOURCE')
frows = {'EGO': rows['EGO'], 'NPC': rows['NPC'], 'EGO_TARGET': rows['EGO_TARGET']}
policy_for = AB.io_policy(fx, frows, source, fref, None, (F(1, 2), F(1, 20), F(0)))
for n, r in enumerate(fx.responses, 1):
    t = fx.routes[r.actor_role].transforms[0]
    actor = SimpleNamespace(id=n, get_location=lambda t=t: SimpleNamespace(x=t.x, y=t.y, z=t.z))
    d = R.create_stock_driver(actor, r, policy_for(r, actor))
    print('stock driver OK', r.actor_role, r.action_id, 'phase_plans', {k: len(v) for k, v in d.config['phase_plans'].items()})
print('COMPILED (offline, not admissible)', sd, {k: float(v.route_station) for k, v in fx.sections.items()})
