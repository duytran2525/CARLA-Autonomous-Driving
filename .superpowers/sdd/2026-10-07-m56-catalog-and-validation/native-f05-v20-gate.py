"""2026-11-20 offline gate before the F05 A/B under m56-v20 (addendum V). Lesson of the F03 v20 A/B: the v20 gate checked
dispatch but never ran arm B through the failing step. Here the REAL v18 F05 arm B (outputs/m56_f_ab_Town12_20261118T093346Z,
30 frames, ended RESPONSE_BLOCKED CREEP_ORIGIN_UNBOUND on the TRIGGER frame, kit defect a032cbf) is replayed under M56_CODE=m56-v20:
the creep fields the v18 kit wrote are stripped, the FIXED F05Kit regenerates them frame by frame (the runner's boundary
observation reaches seal_frame first and is dropped, as in native runs), step_response drives the EGO B program, and
1. every recorded command cause before the TRIGGER frame is reproduced;
2. the TRIGGER frame is NOT blocked any more (the failure being fixed);
3. kit.active_target accepts every recorded command (cause, kind) of both roles (the F03 seal crash).
Read-only on the v18 outputs. Prints F05_V20_GATE PASS|FAIL <reasons>; exit 0 / 3. python -I native-f05-v20-gate.py [B_EPISODE_DIR]"""
import json
import sys
import tempfile
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_v2_common import CODE  # noqa: E402  (puts the product on sys.path)
sys.path.insert(0, str(CODE))
from shapely.geometry import box  # noqa: E402
from m56.evidence import append_record, open_run  # noqa: E402
from m56.metrics import detect_events  # noqa: E402
from m56.model import ScriptState, SourceRef, decode_record, load_json  # noqa: E402
from m56.response import step_response  # noqa: E402
import native_v2_kit as kit  # noqa: E402
import importlib, os  # noqa: E402
# F05_KIT_MODULE / F05_KIT_PATH: negative control only (the kit as it was before a032cbf must be BLOCKED at TRIGGER)
if os.environ.get('F05_KIT_PATH'):
    sys.path.insert(0, os.environ['F05_KIT_PATH'])
F05Kit = importlib.import_module(os.environ.get('F05_KIT_MODULE', 'native_f05_kit')).F05Kit

B_DIR = Path(r'D:\AI\CARLA-Funny-Moments.worktrees\m56-v1\outputs\m56_f_ab_Town12_20261118T093346Z\M56-P-F05\run\episodes\M56-P-F05\B')
STRIP = {'queue_path', 'creep_fixture_ref', 'creep_history_ref'}


class FakeBackend:
    def __init__(self, store):
        self.store = store

    def _raw(self, stream, record, frame=None, time=None):  # m56.runtime.OwnedCarlaBackend._raw, verbatim logic
        self.count = getattr(self, 'count', 0) + 1
        a = append_record(self.store, f'{stream.rsplit(".", 1)[0]}/{self.count:07d}.json', record)
        return SourceRef(str(self.store.root / a.relativepath), a.hash, a.size, '1', 'native', 'NATIVE_RAW', frame, time)


def main(b_dir):
    b_dir = Path(b_dir)
    fixture = decode_record('CompiledFixture', load_json(b_dir / 'fixture.json'))
    raw = json.loads((b_dir / 'trajectory.json').read_text(encoding='utf-8'))
    frames = [decode_record('FrameRecord', f) for f in raw]
    recorded = {f.frame: next(a for a in f.actors if a.role == 'EGO').commands[0] for f in frames}
    fails = []
    # 3: the seal crash of F03 (a BLOCKED cause is not a phase) must not exist for any recorded command
    by_hash = {r.hash: r for r in fixture.responses}
    for f in frames:
        for a in f.actors:
            for c in a.commands:
                try:
                    kit.active_target(by_hash[c.response_hash], c.cause, c.kind)
                except Exception as e:  # noqa: BLE001
                    fails.append(f'ACTIVE_TARGET@{f.frame}:{a.role}:{c.kind}/{c.cause}:{e!r}')
    tmp = Path(tempfile.mkdtemp(prefix='f05v20gate-', dir='D:/tmp'))
    # 3b: the complete synthetic F05 B episode (creep -> stop -> forward) reaches every phase the real one will: the seal
    # (kit.finish -> _motion -> active_target) must accept each of its commands
    from tests.m56.f05_cases import complete_f05
    case = complete_f05(tmp / 'case', 'B')
    syn = {r.hash: r for r in case.fixture.responses}
    n_syn = 0
    for f in case.episode.raw:
        for a in f.actors:
            for c in a.commands:
                n_syn += 1
                try:
                    kit.active_target(syn[c.response_hash], c.cause, c.kind)
                except Exception as e:  # noqa: BLE001
                    fails.append(f'SYNTHETIC_ACTIVE_TARGET@{f.frame}:{a.role}:{c.kind}/{c.cause}:{e!r}')
    auth = tmp / 'authority.json'; auth.write_text('{"offline": "f05 v20 gate"}\n', encoding='utf-8')
    import hashlib
    aref = SourceRef(str(auth), hashlib.sha256(auth.read_bytes()).hexdigest(), auth.stat().st_size, '1', 'test', 'AUTH')
    store = open_run(tmp / 'run', 'f05v20gate', 'writer-f05v20gate')
    backend = FakeBackend(store)
    k = F05Kit(aref, fixture, (box(-1e4, -1e4, 1e4, 1e4), aref), aref, 'F05-v20-gate')
    frames = [replace(f, integrity={x: y for x, y in f.integrity.items() if x not in STRIP}) for f in frames]
    boundary = replace(frames[0], frame=frames[0].frame - 1, simtime=frames[0].simtime - F(1, 20))
    if k.seal_frame(backend, boundary) is not boundary and 'F05_KIT_MODULE' not in os.environ:
        fails.append('BOUNDARY_NOT_DROPPED')
    sealed = [k.seal_frame(backend, f) for f in frames]
    events = detect_events(tuple(sealed), fixture)
    names = [(e.name, e.frame) for e in events]
    ego_b = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
    state, causes, trigger = ScriptState('HOLD', -F(1, 20), ()), [], next((e.frame for e in events if e.name == 'TRIGGER'), None)
    if trigger is None:
        fails.append('TRIGGER_NOT_DETECTED')
    for f in sealed:
        observed = replace(f, events=tuple(e for e in events if e.frame == f.frame))
        try:
            out = step_response(observed, state, ego_b)
        except ValueError as e:
            fails.append(f'STEP_RAISED@{f.frame}:{e!r}'); break
        state = out.state
        causes.append((f.frame, out.command.kind, out.command.cause))
        if out.command.kind == 'BLOCKED' or out.command.cause.startswith('BLOCKED'):
            fails.append(f'BLOCKED@{f.frame}:{out.command.cause}'); break
        was = recorded.get(f.frame)
        if f.frame != trigger and was is not None and (was.kind, was.cause) != (out.command.kind, out.command.cause):
            fails.append(f'CAUSE_DIFFERS@{f.frame}: recorded {was.kind}/{was.cause} replay {out.command.kind}/{out.command.cause}')
    print(json.dumps({'synthetic_commands_checked': n_syn, 'frames': len(sealed), 'trigger': trigger, 'events': names, 'last_causes': causes[-3:],
                      'recorded_last': [(fr, c.kind, c.cause) for fr, c in list(recorded.items())[-2:]]}, default=str))
    print('F05_V20_GATE', 'PASS' if not fails else 'FAIL ' + '; '.join(fails[:6]))
    return 0 if not fails else 3


if __name__ == '__main__':
    import shutil
    before = set(Path('D:/tmp').glob('f05v20gate-*'))
    try:
        rc = main(sys.argv[1] if len(sys.argv) > 1 else B_DIR)
    finally:  # 20/11: each run left ~2.4 GB of scratch on D (D fell under the 80 GB gate)
        for p in set(Path('D:/tmp').glob('f05v20gate-*')) - before:
            shutil.rmtree(p, ignore_errors=True)
    sys.exit(rc)
