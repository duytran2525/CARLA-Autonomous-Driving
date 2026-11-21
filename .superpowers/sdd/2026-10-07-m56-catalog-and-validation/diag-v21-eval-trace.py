"""2026-11-21 offline diagnosis: re-run the consumer's evaluate_episode on one sealed arm of a v21 A/B with tracing, to see WHICH
check produced UNPLANNED_REVERSE / *_COMMAND_REPLAY_UNPROVEN. Same evidence construction and fixture as native-v6-pair.py
(fixture-frozen.json). The fresh W05 bundle goes to a scratch dir (default E:\\tmp\\diag-eval-<scene>-<arm>), not the run.
Hooks only observe: metrics._reverse_beyond_jitter, response.step_response, response.reverse_intent are wrapped and called
unchanged. Nothing is written to the run, no CARLA.
usage: M56_CODE=<m56-v21> M56_RECIPE=v6 python -I diag-v21-eval-trace.py SCENE_DIR ARM [SCRATCH]"""
import importlib.util, sys, traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('pair', HERE / 'native-v6-pair.py')
pair = importlib.util.module_from_spec(spec); spec.loader.exec_module(pair)
import m56.metrics as M  # noqa: E402
import m56.response as R  # noqa: E402
from m56.metrics import evaluate_episode  # noqa: E402
from m56.model import decode_record, load_json  # noqa: E402

LOG = []


def where():
    return [f'{Path(s.filename).name}:{s.lineno}' for s in traceback.extract_stack()[-4:-1]]


orig_jit = M._reverse_beyond_jitter


def jit(previous, frame, before, after, fixture):
    r = orig_jit(previous, frame, before, after, fixture)
    if r:
        LOG.append(('JITTER_TRUE', previous.frame if previous is not None else None, frame.frame, float(before - after),
                    'proof' if M._continuous_proof(previous, frame, M._digest(fixture)) is not None else 'NO_PROOF', where()))
    return r


M._reverse_beyond_jitter = jit
orig_step, orig_rev = R.step_response, R.reverse_intent


def wrap(name, orig):
    def f(frame, state, response, *a):
        try:
            r = orig(frame, state, response, *a)
        except Exception as e:  # noqa: BLE001
            LOG.append((name + '_RAISED', frame.frame, response.actor_role, f'{type(e).__name__}: {e}', where()))
            raise
        if r.command.kind == 'BLOCKED':
            LOG.append((name + '_BLOCKED', frame.frame, response.actor_role, r.command.cause, str(r.state.phase), where()))
        return r
    return f


R.step_response, R.reverse_intent = wrap('step_response', orig_step), wrap('reverse_intent', orig_rev)
import m56.evidence as E  # noqa: E402

orig_sj, orig_adm = E._source_json, E._admitted_source


def sj(evidence, packet):
    r = orig_sj(evidence, packet)
    if r is None:
        LOG.append(('SOURCE_JSON_NONE', str(packet)[:90], where()))
    return r


def adm(evidence, ref):
    r = orig_adm(evidence, ref)
    if not r:
        LOG.append(('ADMITTED_SOURCE_FALSE', str(getattr(ref, 'uri', ref))[-70:], where()))
    return r


E._source_json, E._admitted_source = sj, adm


def main(sd, arm, scratch):
    fixture = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
    scratch.mkdir(parents=True, exist_ok=False)
    ev, _auth, snap = pair.evidence(sd, arm, scratch, fixture)
    print('w05 snapshot', snap, flush=True)
    v = evaluate_episode(ev, fixture)
    print('RESULT', v.physical, v.witness, list(v.reasons))
    seen = {}
    for row in LOG:
        seen.setdefault((row[0], str(row[-1])), []).append(row)
    for k, rows in seen.items():
        print(f'{k[0]} x{len(rows)} via {k[1]}')
        for r in rows[:6]:
            print('   ', r[:-1])


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve(), sys.argv[2], Path(sys.argv[3] if len(sys.argv) > 3 else rf'E:\tmp\diag-eval-{Path(sys.argv[1]).name}-{sys.argv[2]}'))
