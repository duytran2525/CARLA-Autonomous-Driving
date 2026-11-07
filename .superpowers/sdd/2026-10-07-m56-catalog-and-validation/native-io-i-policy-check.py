"""io-i-v1 offline proof (2026-11-07, I03 A/B TICK_ERROR KeyError('NPC_TARGET') at frame 21): the NPC stock policy's
phase plans need the NPC_TARGET rows. Rebuilds the compile's io_routes rows from the scene's own preparation and calls
io_phase_plans on the sealed fixture's NPC response with the old (EGO, NPC, EGO_TARGET) and the fixed row set.
python -I native-io-i-policy-check.py SCENE_DIR   (M56_RECIPE=v6, M56_CODE set; absolute path)"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401  (M56_CODE first on sys.path)
from native_io_common import io_routes, io_phase_plans
from m56.model import decode_record, load_json

sd = Path(sys.argv[1])
fx = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
receipt = json.loads((sd.parent / 'duy-delegation-receipt.json').read_text(encoding='utf-8'))
rev = json.loads(Path(receipt['revision']['path']).read_text(encoding='utf-8'))
cand = next(c for c in rev['candidates'] if c['id'] == sd.name)
prep_path = Path(cand['environment']['runtime_recipe_v2']['prepare_json'])
import importlib.util
spec = importlib.util.spec_from_file_location('ioab_plain', Path(__file__).resolve().parent / 'native-io-ab.py')
src = spec.loader.get_source('ioab_plain'); ns = {'F': __import__('fractions').Fraction}
exec(src[src.index('def plain(x):'):src.index('def compile_scene')], ns); plain = ns['plain']  # the compile's own decoder
raw = json.loads(prep_path.read_text(encoding='utf-8'))
prep = {k: (v if k == 'poses' else plain(v)) for k, v in raw.items()}
_, rows, _ = io_routes(prep, plain, cand['town'])
npc = next(r for r in fx.responses if r.actor_role == 'NPC')
old = {k: rows[k] for k in ('EGO', 'NPC', 'EGO_TARGET')}
try:
    io_phase_plans(npc, old); print('OLD ROWS: no error (unexpected)')
except KeyError as e:
    print('OLD ROWS:', repr(e))
new = {k: rows[k] for k in ('EGO', 'NPC', 'EGO_TARGET', 'NPC_TARGET') if k in rows}
plans = io_phase_plans(npc, new)
print('NEW ROWS: phase plans', {k: len(v) for k, v in plans.items()})
assert set(plans) == {s['cause'] for s in npc.phases['reference_switches']} and all(plans.values())
print('I POLICY CHECK PASS')
