"""Offline check of native_f05_kit.F05Kit (addendum U) against the PRODUCT (M56_CODE=m56-v18): the synthetic F05 B episode
(tests/m56/f05_cases.complete_f05) with its producer creep fields REMOVED; F05Kit.seal_frame regenerates queue_path,
creep_fixture_ref and creep_history_ref per frame through a store-backed fake backend; then response.step_response runs
the EGO B program over every frame. PASS = no exception, the program reaches FORWARD, and the evaluator events
(TRIGGER, EGO_CREEP_STOPPING_BOUND, EGO_CREEP_STOP_CONFIRMED, QUEUE_CLEAR_CONFIRMED, N_MOVE, F05_END) are all detected."""
import sys
import tempfile
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import CODE  # noqa: E402  (puts the product on sys.path)
sys.path.insert(0, str(CODE))
from shapely.geometry import box  # noqa: E402
from tests.m56.f05_cases import complete_f05  # noqa: E402
from m56.evidence import append_record, open_run  # noqa: E402
from m56.metrics import detect_events  # noqa: E402
from m56.model import ScriptState, SourceRef  # noqa: E402
from m56.response import step_response  # noqa: E402
from native_f05_kit import F05Kit  # noqa: E402


class FakeBackend:
    def __init__(self, store):
        self.store = store

    def _raw(self, stream, record, frame=None, time=None):  # m56.runtime.OwnedCarlaBackend._raw, verbatim logic
        self.count = getattr(self, 'count', 0) + 1
        a = append_record(self.store, f'{stream.rsplit(".", 1)[0]}/{self.count:07d}.json', record)
        return SourceRef(str(self.store.root / a.relativepath), a.hash, a.size, '1', 'native', 'NATIVE_RAW', frame, time)


def main():
    tmp = Path(tempfile.mkdtemp(prefix='f05kit-', dir='D:/tmp'))
    case = complete_f05(tmp / 'case', 'B')
    fixture, frames = case.fixture, case.episode.raw
    strip = {'queue_path', 'creep_fixture_ref', 'creep_history_ref'}
    frames = [replace(f, integrity={k: v for k, v in f.integrity.items() if k not in strip}) for f in frames]
    auth = tmp / 'authority.json'; auth.write_text('{"offline": "f05 kit check"}\n', encoding='utf-8')
    import hashlib
    aref = SourceRef(str(auth), hashlib.sha256(auth.read_bytes()).hexdigest(), auth.stat().st_size, '1', 'test', 'AUTH')
    store = open_run(tmp / 'run', 'f05kit', 'writer-f05kit')
    backend = FakeBackend(store)
    kit = F05Kit(aref, fixture, (box(-1e4, -1e4, 1e4, 1e4), aref), aref, 'F05-offline')
    sealed = [kit.seal_frame(backend, f) for f in frames]
    have = sum('creep_history_ref' in f.integrity for f in sealed)
    events = detect_events(tuple(sealed), fixture)
    names = [e.name for e in events]
    print('frames', len(sealed), 'with creep refs', have, 'events', names)
    ego = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
    state = ScriptState('HOLD', -F(1, 20), ())
    phases = []
    for f in sealed:
        observed = replace(f, events=tuple(e for e in events if e.frame == f.frame))
        try:
            out = step_response(observed, state, ego)
        except ValueError as e:
            print('FAIL at frame', f.frame, 'phase', state.phase, repr(e)); return 1
        state = out.state
        if not phases or phases[-1] != state.phase:
            phases.append(state.phase)
        if out.command.cause.startswith('BLOCKED'):
            print('FAIL blocked at', f.frame, out.command.cause); return 1
    need = {'TRIGGER', 'EGO_CREEP_STOPPING_BOUND', 'EGO_CREEP_STOP_CONFIRMED', 'QUEUE_CLEAR_CONFIRMED', 'N_MOVE', 'F05_END'}
    ok = need <= set(names) and phases[-1] == 'FORWARD' and have > 0
    print('phases', phases, 'missing events', sorted(need - set(names)))
    print('F05_KIT_OFFLINE', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
