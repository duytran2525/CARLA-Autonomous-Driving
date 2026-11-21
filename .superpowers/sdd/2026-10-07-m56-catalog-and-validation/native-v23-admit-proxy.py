"""2026-11-22 addendum Y check, offline and read-only: what the consumer says about a sealed arm once the fixture's stop-bound proof
sources are admitted, as native_v2_kit.stop_bound_sources (flag M56_KIT_ADMIT_STOP_BOUND=1) will snapshot them in the next A/B.
Same evidence construction as native-v6-pair.py (fresh W05 bundle in SCRATCH). evidence._admitted_source is wrapped: a ref that
the sealed arm does not admit is accepted ONLY when it is one of stop_bound_sources(fixture) and its file still has the declared
size and sha256 (exactly what snapshot_sources would copy). Nothing else changes. Prints the verdict, how many refs the emulation
admitted, and every REVERSE/FORWARD_COMMAND_* reason; ADMIT_PROXY PASS when no *_COMMAND_REPLAY_UNPROVEN and no *_MISMATCH remain.
usage: M56_CODE=<worktree> M56_RECIPE=v6 python -I native-v23-admit-proxy.py SCENE_DIR ARM SCRATCH"""
import hashlib
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('pair', HERE / 'native-v6-pair.py')
pair = importlib.util.module_from_spec(spec); spec.loader.exec_module(pair)  # type: ignore[union-attr]
import m56.evidence as E  # noqa: E402
from m56.metrics import evaluate_episode  # noqa: E402
from m56.model import decode_record, load_json  # noqa: E402
from native_v2_kit import stop_bound_sources  # noqa: E402

EMULATED = set()


def main(sd, arm, scratch):
    fixture = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
    allowed = set(stop_bound_sources(fixture))
    orig = E._admitted_source

    def adm(evidence, ref):
        if orig(evidence, ref):
            return True
        if ref in allowed:
            data = Path(ref.uri).read_bytes()
            if len(data) == ref.bytes and hashlib.sha256(data).hexdigest() == ref.sha256:
                EMULATED.add(ref.uri)
                return True
        return False

    E._admitted_source = adm
    scratch.mkdir(parents=True, exist_ok=False)
    ev, _auth, snap = pair.evidence(sd, arm, scratch, fixture)
    v = evaluate_episode(ev, fixture)
    cmd = [r for r in v.reasons if 'COMMAND' in r]
    print('stop_bound_sources', len(allowed), 'emulated_admitted', sorted(Path(u).name for u in EMULATED), 'w05', snap)
    print('RESULT', v.physical, v.witness, list(v.reasons))
    ok = not any(r.endswith('_REPLAY_UNPROVEN') or r.endswith('_MISMATCH') for r in cmd)
    print('ADMIT_PROXY', 'PASS' if ok else 'FAIL', cmd)
    return 0 if ok else 3


if __name__ == '__main__':
    sys.exit(main(Path(sys.argv[1]).resolve(), sys.argv[2], Path(sys.argv[3])))
