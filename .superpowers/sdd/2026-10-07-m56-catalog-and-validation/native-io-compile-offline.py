"""Offline I/O fixture compile (no server): native-io-ab.compile_scene with the drivable union read from an earlier
native compile's drivable-union.wkt and a stub server identity (map hash from the preparation). For iterating on the
compile/contract code only: the fixture is NOT admissible (stub boot/world); the native compile + admission runs once
through native-io-ab.py.  python -I native-io-compile-offline.py REVISION.json SCENE DRIVABLE.wkt
"""
import importlib.util, json, sys
from pathlib import Path
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
fx, *_ = AB.compile_scene(c, SimpleNamespace(id='offline'), None, SimpleNamespace(map=prep['map_hash']),
                          SimpleNamespace(pid=0), 'offline', sd)
if not isinstance(fx, CompiledFixture):
    print('BLOCKED_FIXTURE', list(fx.reasons)); sys.exit(1)
AB.write_ref(sd / 'fixture-frozen.json', fx, 'FROZEN_FIXTURE')
from m56.response import _lateral_contract, _reference_response, _program  # noqa: E402
for r in fx.responses:
    _lateral_contract(r, fx)
    for cause in (_program(r)['initial'], *(t['cause'] for t in _program(r)['transitions'])):
        _reference_response(r, cause)
print('COMPILED (offline, not admissible)', sd, {k: float(v.route_station) for k, v in fx.sections.items()})
