"""M56 F03 native kit (PREREG F part 2 + addendum A, 20261118). Product m56-v19: its runtime calls kit.seal_frame(backend,
record) on every finished frame record (the runner boundary observation is skipped, F05 lesson a032cbf). Per record:
- rollback (every frame, A and B; metrics._detect_f03 needs it on every frame before TRIGGER): ROLLBACK /
  unpowered-grade-motion-v1, gravity_along_reverse_mps2 = g * sin(grade) of the NPC route segment under the NPC
  (dz / 3-D segment length; uphill along travel > 0), floored to 1e-4;
- B only (EGO commands bound to the F03 B response), as response._reverse_inputs requires:
  reverse_corridors {'EGO': REVERSE_CORRIDOR / bounded-reverse-corridor-v1}, minimum_rear_clearance_m = min over the EGO
  body vertices of the distance along travel to the rear face of topology reverse_regions['EGO'], floored to 1e-4;
  reverse_history_ref = every record of this episode so far (current included; rows keep frame_refs, continuous_geometry,
  validation_start, rollback), one JSON list.
b_fields_in_a=True (pre-registered A-only probe, native-f-ab.py --probe-a) also writes the B fields in A, for the offline
replay of a runner-recorded episode. Claude review under Duy delegation, not independent."""
import json
import math
from dataclasses import replace
from fractions import Fraction

from native_v2_kit import UNC
from native_f05_kit import F05Kit, floor4
from m56.catalog import _digest
from m56.geometry import project_route, world_vertices
from m56.model import encode_record
from m56.response import _v14_axis_route

G = 9.81
WHY = ('native grade from the frozen NPC route geometry under the observed NPC pose; Claude review under Duy delegation, '
       'not independent',)
WHY_C = ('native rear corridor from the observed EGO body vs the frozen reverse region; Claude review under Duy delegation, '
         'not independent',)


def grade_sin(route, station):
    """sin of the route grade on the segment containing `station` (route.arc stations)."""
    for i, (a, b) in enumerate(zip(route.arc, route.arc[1:])):
        if a <= station <= b:
            s, e = route.transforms[i], route.transforms[i + 1]
            length = math.dist((s.x, s.y, s.z), (e.x, e.y, e.z))
            return (e.z - s.z) / length if length > 0 else None
    return None


def rear_clearance(region, body, pose, route):
    """min over body vertices of the along-travel distance to the region rear face (negative = outside)."""
    lat, trv = _v14_axis_route(route)
    tsg = 1 if (route.transforms[-1].x, route.transforms[-1].y)[trv] > (route.transforms[0].x, route.transforms[0].y)[trv] else -1
    face = min(p[trv] for p in region) if tsg > 0 else max(p[trv] for p in region)
    return min(tsg * (v[trv] - face) for v in world_vertices(body, pose))


class F03Kit(F05Kit):
    def __init__(self, *a, b_fields_in_a=False, **k):
        super().__init__(*a, **k)
        self.b_fields_in_a = b_fields_in_a
        self.region = self.fixture.domain.topology['reverse_regions']['EGO']
        self.npc_route = self.fixture.routes['NPC']

    def _rollback(self, backend, record):
        npc = next((a for a in record.actors if a.role == 'NPC'), None)
        if npc is None:
            return None
        st = project_route((npc.pose.x, npc.pose.y, npc.pose.z), self.npc_route)
        if hasattr(st, 'reasons'):
            return None
        sin = grade_sin(self.npc_route, st)
        if sin is None or sin <= 0:
            return None
        limits = {'fixture_hash': self.fixture_hash, 'boot': record.boot, 'world': record.world, 'frame': record.frame,
                  'actor_id': npc.id, 'actors_hash': _digest(record.actors), 'gravity_along_reverse_mps2': floor4(Fraction(G * sin))}
        raw = backend._raw('f03/rollback.json', limits, record.frame, record.simtime)
        recipe = self._recipe(backend, 'rollback', {
            'method': 'unpowered-grade-motion-v1', 'version': '1',
            'grade': 'frozen NPC route segment under the projected NPC pose: dz / 3-D segment length (uphill along travel > 0)',
            'gravity': 'g = 9.81 m/s^2 times the grade sine, floored to 1e-4; observed downward displacement is the detector rule'})
        return self.proof('ROLLBACK', 'unpowered-grade-motion-v1', (raw,), UNC, limits, (recipe,), WHY)

    def _corridor(self, backend, record, ego):
        clear = rear_clearance(self.region, ego.body, ego.pose, self.fixture.routes['EGO'])
        limits = {'fixture_recipe_hash': self.recipe_hash, 'boot': record.boot, 'world': record.world, 'frame': record.frame,
                  'actor_id': ego.id, 'actors_hash': _digest(record.actors), 'response_hash': self.b.hash,
                  'region_hash': _digest(self.region), 'minimum_rear_clearance_m': floor4(Fraction(clear))}
        raw = backend._raw('f03/reverse-corridor.json', limits, record.frame, record.simtime)
        recipe = self._recipe(backend, 'reverse-corridor', {
            'method': 'bounded-reverse-corridor-v1', 'version': '1',
            'corridor': 'frozen lane box behind the EGO (topology reverse_regions EGO); nothing else is spawned in it',
            'clearance': 'min over EGO body vertices of the along-travel distance to the box rear face, floored to 1e-4 m'})
        return self.proof('REVERSE_CORRIDOR', 'bounded-reverse-corridor-v1', (raw,), UNC, limits, (recipe,), WHY_C)

    def seal_frame(self, backend, record):
        ego = next((a for a in record.actors if a.role == 'EGO'), None)
        if ego is None:
            return record
        if ego.id != self.ego_id or (self.rows and record.frame != self.rows[-1].frame + 1):
            self._reset(ego.id)
            self.boundary_frame = record.frame  # runner boundary: never in its frames, never in the history (a032cbf)
            return record
        if record.frame == getattr(self, 'boundary_frame', None):
            return record
        if self.action is None and ego.commands:
            self.action = 'B' if ego.commands[0].response_hash == self.b.hash else 'OTHER'
        added = {}
        rollback = self._rollback(backend, record)
        if rollback is not None:
            added['rollback'] = rollback
        b = self.action == 'B' or (self.action == 'OTHER' and self.b_fields_in_a)
        if self.action == 'OTHER' and not self.b_fields_in_a:
            self.rows, self.lines = [], []
            return replace(record, integrity={**record.integrity, **added})
        merged = {**record.integrity, **added}
        row = replace(record, events=(), integrity={k: v for k, v in merged.items()
                                                    if k in ('frame_refs', 'continuous_geometry', 'validation_start', 'rollback')})
        self.rows.append(row)
        self.lines.append(json.dumps(encode_record(row), sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                     allow_nan=False).encode('utf-8'))
        if not b:  # action not known yet: the row is kept
            return replace(record, integrity=merged)
        added['reverse_corridors'] = {'EGO': self._corridor(backend, record, ego)}
        added['reverse_history_ref'] = self._write_bytes(backend, 'reverse/history', b'[' + b','.join(self.lines) + b']\n',
                                                         record.frame, record.simtime)
        return replace(record, integrity={**record.integrity, **added})


def _selftest():
    from types import SimpleNamespace as N
    route = N(arc=(0, 5, 10), transforms=(N(x=0., y=0., z=0.), N(x=3., y=0., z=4.), N(x=6., y=0., z=8.)))
    assert abs(grade_sin(route, 7) - .8) < 1e-12 and grade_sin(route, 11) is None
    print('SELFTEST_OK')


if __name__ == '__main__':
    _selftest()
