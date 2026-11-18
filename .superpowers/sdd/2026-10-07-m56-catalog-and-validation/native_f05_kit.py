"""M56 F05 native kit (addendum U, docs/m56/PREREG_M56_F05_ADDENDUM_U_20261118.md). Product m56-v18 only: its runtime calls
kit.seal_frame(backend, record) on every finished frame record. In the B episode (EGO commands bound to the F05 B response)
each record gets, as response._creep_guard requires:
- creep_fixture_ref: the compiled fixture as a store source (one per episode);
- creep_history_ref: every record of this episode so far, the current one included (pre-seal records, one JSON list);
- queue_path: QUEUE_PATH / bounded-queue-exit-corridor-v1, minimum_forward_clearance_m = the EGO-route min front gap
  (NPC body rear - EGO body front), floored to 1e-4 m, for this exact frame.
The A episode gets nothing extra (its guard never runs). Claude review under Duy delegation, not independent."""
import hashlib
import json
import math
from dataclasses import replace
from fractions import Fraction

from native_v2_kit import Kit, UNC
from m56.catalog import _digest
from m56.evidence import _append_bytes, _payload, _ref, _safe_path, _writer
from m56.metrics import _route_observation, _route_ref
from m56.model import SourceRef, encode_record
from m56.response import _reverse_recipe_hash

WHY = ('native queue corridor from observed bodies (min front gap on the EGO route); Claude review under Duy delegation, '
       'not independent',)


def floor4(x):
    return Fraction(math.floor(x * 10 ** 4), 10 ** 4)


class F05Kit(Kit):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.b = next(r for r in self.fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
        self.recipe_hash = _reverse_recipe_hash(self.fixture)
        self.route_ref = _route_ref(self.fixture.routes['EGO'])
        self._reset(None)

    def _reset(self, ego_id):
        self.ego_id, self.rows, self.lines, self.action, self.fixture_ref = ego_id, [], [], None, None

    def _write_bytes(self, backend, stream, data, frame, time):
        """append_record for pre-encoded bytes (the history is one JSON list; rows are encoded once, not per frame)."""
        backend.count = getattr(backend, 'count', 0) + 1
        store = backend.store
        path = _safe_path(store.root, f'{stream}/{backend.count:07d}.json')
        with _writer(store):
            _append_bytes(store.journal, _payload({'operation': 'APPEND_INTENT', 'stream': path.relative_to(store.root).as_posix(),
                                                   'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}))
            path.parent.mkdir(parents=True, exist_ok=True)
            _append_bytes(path, data)
            a = _ref(store.root, path, 'STREAM')
        return SourceRef(str(store.root / a.relativepath), a.hash, a.size, '1', 'native', 'NATIVE_RAW', frame, time)

    def seal_frame(self, backend, record):
        ego = next((a for a in record.actors if a.role == 'EGO'), None)
        if ego is None:
            return record
        if ego.id != self.ego_id or (self.rows and record.frame != self.rows[-1].frame + 1):
            self._reset(ego.id)  # a new episode (new spawn) or a gap: never mix histories
        if self.action is None and ego.commands:
            self.action = 'B' if ego.commands[0].response_hash == self.b.hash else 'OTHER'
        if self.action == 'OTHER':  # A: no creep guard, keep no history
            self.rows, self.lines = [], []
            return record
        added = {}
        gap = _route_observation(record, {'directed_route': self.fixture.routes['EGO']}, self.route_ref, 'min_front_gap')
        if gap is not None:
            limits = {'fixture_recipe_hash': self.recipe_hash, 'boot': record.boot, 'world': record.world,
                      'frame': record.frame, 'actor_id': ego.id, 'actors_hash': _digest(record.actors),
                      'response_hash': self.b.hash, 'route_hash': _digest(self.b.route),
                      'minimum_forward_clearance_m': floor4(gap)}
            raw = backend._raw('creep/queue-path.json', limits, record.frame, record.simtime)
            recipe = self._recipe(backend, 'queue-path', {
                'method': 'bounded-queue-exit-corridor-v1', 'version': '1',
                'corridor': 'EGO route ahead of the EGO body front up to the NPC body rear (same lane)',
                'clearance': 'metrics._route_observation min_front_gap on the EGO route, floored to 1e-4 m'})
            added['queue_path'] = self.proof('QUEUE_PATH', 'bounded-queue-exit-corridor-v1', (raw,), UNC, limits,
                                             (recipe,), WHY)
        # history row = the detector-required source fields only (as tests/m56/source_cases bind_frames): no recursion
        merged = {**record.integrity, **added}
        row = replace(record, events=(), integrity={k: v for k, v in merged.items()
                                                    if k in ('frame_refs', 'continuous_geometry', 'validation_start', 'queue_path')})
        self.rows.append(row)
        self.lines.append(json.dumps(encode_record(row), sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                     allow_nan=False).encode('utf-8'))
        if self.action != 'B':  # action not known yet: the row is kept, the record itself stays unchanged
            return record
        if self.fixture_ref is None:
            self.fixture_ref = backend._raw('creep/fixture.json', self.fixture)
        added['creep_fixture_ref'] = self.fixture_ref
        added['creep_history_ref'] = self._write_bytes(backend, 'creep/history', b'[' + b','.join(self.lines) + b']\n',
                                                       record.frame, record.simtime)
        return replace(record, integrity={**record.integrity, **added})


def _selftest():
    assert floor4(Fraction(12345678, 10 ** 7)) == Fraction(12345, 10 ** 4)
    assert floor4(Fraction(-1, 10 ** 6)) == Fraction(-1, 10 ** 4)
    assert floor4(Fraction(3)) == 3
    print('SELFTEST_OK')


if __name__ == '__main__':
    _selftest()
