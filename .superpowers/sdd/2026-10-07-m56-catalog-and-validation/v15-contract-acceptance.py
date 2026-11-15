"""Offline acceptance of consumer v15 (no CARLA): the frozen-response contract loop of native-io-ab.py (lateral + forward +
reference per program cause) on compiled I/O fixtures, under the product named by M56_CODE. Prints one JSON line per fixture.
  M56_CODE=<product> python -I v15-contract-acceptance.py FIXTURE_DIR/<scene> [...]"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ['M56_CODE'])
from m56.model import decode_record, load_json
from m56.response import _forward_contract, _lateral_contract, _reference_response, _program

for d in sys.argv[1:]:
    fx = decode_record('CompiledFixture', load_json(Path(d) / 'fixture-frozen.json'))
    checks = {}
    for r in fx.responses:
        try:
            _lateral_contract(r, fx); _forward_contract(r, fx)
            for cause in (_program(r)['initial'], *(t['cause'] for t in _program(r)['transitions'])):
                _reference_response(r, cause)
            checks[f'{r.actor_role}:{r.action_id}'] = 'OK'
        except ValueError as e:
            checks[f'{r.actor_role}:{r.action_id}'] = str(e)
    print(json.dumps({'code': Path(os.environ['M56_CODE']).name, 'scene': Path(d).name, 'dir': Path(d).parent.name, 'checks': checks}))
