"""A-SEL2 declared comparison audit (offline, product m56 catalog.compare_parameters) on a frozen revision, with the
descriptor sets of docs/m56/DESCRIPTOR_SPECS_M56_ASEL2_20261108.md (8bdf074). No D09 review exists yet, so a
pair that meets the diversity rule reports REVIEW_REQUIRED; DIVERSITY_DEFICIT / BLOCKED_COMPARABILITY are the problems.
Candidates listed in EXCLUDE (failed, trialed) are left out. usage: python -I asel2-declared-audit.py REVISION.json"""
import hashlib, json, sys
from collections import Counter
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parent), 'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1']
from m56.model import decode_record, PolicyBundle, SourceRef
from m56.catalog import compare_parameters

DOC = Path('D:/AI/CARLA-Funny-Moments.worktrees/m56-v1/docs/m56/DESCRIPTOR_SPECS_M56_ASEL2_20261108.md')
EXCLUDE = {'M56-P-M04-S1', 'M56-P-M07-S1'}  # addendum C: trialed failures, never counted
data = DOC.read_bytes()
ref = SourceRef(str(DOC), hashlib.sha256(data).hexdigest(), len(data), '1', 'sha256', 'DESCRIPTOR_SPEC')
D = lambda unit, q, aliases=(): {'unit': unit, 'physical_quantity': q, 'aggregation': 'declared_scalar', 'source_actions': ('A', 'B'),
                                'event': 't0', 'window': 'declared', 'reference': 'spec 2.3 + A-SEL2 4', 'refs': (ref,),
                                **({'aliases': aliases} if aliases else {})}
CL = {'vN': D('m/s', 'npc_speed'), 'G': D('m', 'ego_trigger_distance', ('G_m',)), 'LrefN': D('m', 'npc_connector_length')}
specs = {'by_category': {'C': CL, 'L': CL, 'M': {'vN': D('m/s', 'npc_speed'), 'G': D('m', 'ego_trigger_distance')},
                         'I': {'vE': D('m/s', 'ego_speed'), 'gap': D('m', 'trigger_gap', ('gap_m',))},
                         'O': {'vE': D('m/s', 'ego_speed'), 'G': D('m', 'follow_gap', ('G_m', 'gap'))}}}
pol = PolicyBundle('asel2-declared-audit', 'a' * 64, {}, {}, specs, (ref,))
rev = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
cands = []
for item in rev['candidates']:
    if item['id'] in EXCLUDE or item['category'] == 'F':
        continue
    item = {**item, 'parameters': {n: p for n, p in item['parameters'].items() if p.get('units') != 'index'}}
    c = decode_record('Candidate', item)
    if not hasattr(c, 'errors'):
        cands.append(c)
from itertools import combinations
res = Counter(); bad = []
for cat in 'CLMIO':
    cs = sorted((c for c in cands if c.category == cat), key=lambda c: c.slot)
    for a, b in combinations(cs, 2):
        r = compare_parameters(a, b, pol, ())
        res[(cat, r.status)] += 1
        if r.status != 'REVIEW_REQUIRED':
            bad.append((cat, a.id, b.id, r.status, [float(d) if d is not None else None for d in r.deltas]))
print('candidates per category', dict(Counter(c.category for c in cands)))
print('status', dict(res))
for row in bad[:40]:
    print(row)
