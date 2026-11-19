"""F03 replay gate (PREREG F part 2 section 4 + addendum A3): replay ONE runner-recorded episode (the pre-registered A-only
probe, native-f-ab.py --probe-a, F03Kit b_fields_in_a) through the product, offline:
  1. detect_events on the sealed frames: TRIGGER and NPC_STOP_CONFIRMED, no WITNESS_UNKNOWN;
  2. the NPC command causes in order NPC_HOLD -> NPC_APPROACH -> UNPOWERED -> F03_BRAKE (-> NPC_CLEAR);
  4. (addendum A3/A4) the product evaluator on the episode: physical not FAILED, no COLLISION_OBSERVED, DESTINATION_CONFIRMED;
     TRIGGER -> NPC_STOP_CONFIRMED >= the chosen reverse trial's stop_confirmed_s + 1/20 (prepare.json, 2nd argument);
  3. (addendum A5, v20) the runner's OWN dispatch on the decoded frozen fixture: runtime._bounded(B) is True and runtime._commands
     returns the bounded kernel's REVERSE command (manual gear -1, throttle <= 0.4) on every frame from TRIGGER for 2 s; calling
     response.reverse_intent directly is not enough (it skipped the dispatch rule that r19e got wrong).
Prints F03_REPLAY_PASS or F03_REPLAY_FAIL <reasons>; exit 0 / 3. A pass is a tooling gate, not an outcome.
  python -I native-f03-replay.py COMPILE_SCENE_DIR PREPARE_JSON (scene dir holds fixture-frozen.json and probe-a/)"""
import json
import sys
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401,E402  (M56_CODE on sys.path)
from m56 import runtime  # noqa: E402
from m56.metrics import detect_events, evaluate_episode  # noqa: E402
from m56.model import CompiledFixture, ScriptState, decode_record, load_json  # noqa: E402


def main(sd, prep_path):
    sd = Path(sd); prep = json.loads(Path(prep_path).read_text(encoding='utf-8'))
    fixture = decode_record('CompiledFixture', load_json(sd / 'fixture-frozen.json'))
    assert isinstance(fixture, CompiledFixture), fixture
    tj = sorted((sd / 'probe-a').rglob('trajectory.json'))
    assert len(tj) == 1, ('ONE_EPISODE_EXPECTED', [str(p) for p in tj])
    ev = runtime.load_episode(tj[0].parent)
    assert ev is not None, 'EPISODE_UNSEALED'
    frames = tuple(ev.raw); fails = []
    events = detect_events(frames, fixture); names = [e.name for e in events]
    out = {'frames': len(frames), 'events': [(e.name, e.frame) for e in events]}
    for need in ('TRIGGER', 'NPC_STOP_CONFIRMED'):
        if need not in names:
            fails.append(need + '_MISSING')
    if 'WITNESS_UNKNOWN' in names:
        fails.append('WITNESS_UNKNOWN')
    causes = []
    for f in frames:
        npc = next(a for a in f.actors if a.role == 'NPC')
        c = npc.commands[0].cause if npc.commands else None
        if c and (not causes or causes[-1] != c):
            causes.append(c)
    out['npc_causes'] = causes
    want = ['NPC_HOLD', 'NPC_APPROACH', 'UNPOWERED', 'F03_BRAKE']
    if causes[:4] != want or causes[4:] not in ([], ['NPC_CLEAR']):
        fails.append('NPC_PHASES_' + '>'.join(map(str, causes)))
    trig = next((e for e in events if e.name == 'TRIGGER'), None)
    if trig is not None:
        # addendum A5 (v20): the RUNNER's own dispatch (runtime._bounded + runtime._commands) on the DECODED frozen fixture,
        # never reverse_intent directly: r19e (v19) drove the stock forward PID because _bounded was never true here
        b = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
        out['bounded_B'] = runtime._bounded(b)
        if not out['bounded_B']:
            fails.append('BOUNDED_DISPATCH_FALSE')
        ego_id = next(a.id for a in frames[0].actors if a.role == 'EGO')
        states = {'EGO': ScriptState('HOLD', frames[0].simtime, ())}
        kernel = []
        for i, f in enumerate(frames):
            if f.frame < trig.frame or f.simtime > trig.time + 2:
                continue
            (c,) = runtime._commands(frames[:i + 1], frames[0], states, (b,), {'EGO': ego_id}, fixture, events)
            k = c.control
            kernel.append((f.frame, c.kind, c.cause, None if k is None else (k.throttle, k.steer, k.brake, k.reverse, k.manual_gear_shift, k.gear)))
            if (c.kind, c.cause) != ('REVERSE', 'REVERSE') or k is None or not (k.reverse and k.manual_gear_shift and k.gear == -1
                                                                                 and k.steer == 0 and 0 <= k.throttle <= .4):
                fails.append(f'DISPATCH_NOT_REVERSE_KERNEL@{f.frame}:{c.kind}/{c.cause}'); break
        out['kernel_first'] = kernel[:2]; out['kernel_n'] = len(kernel)
        if not kernel:
            fails.append('DISPATCH_NO_FRAMES')
    if '--dispatch-only' in sys.argv:  # offline demonstration of the dispatch check alone (skips the slow evaluator)
        print(json.dumps(out, default=str)); print('F03_DISPATCH_PASS' if not fails else 'F03_DISPATCH_FAIL ' + ' '.join(fails))
        return 0 if not fails else 3
    verdict = evaluate_episode(ev, fixture)
    out['verdict'] = {'spawn': str(verdict.spawn), 'physical': str(verdict.physical), 'witness': str(verdict.witness),
                      'reasons': list(verdict.reasons)}
    if 'FAILED' in str(verdict.physical):
        fails.append('PROBE_A_FAILED')
    if 'COLLISION_OBSERVED' in verdict.reasons:
        fails.append('COLLISION_OBSERVED')
    if 'DESTINATION_CONFIRMED' not in names:
        fails.append('DESTINATION_CONFIRMED_MISSING')
    stop = next((e for e in events if e.name == 'NPC_STOP_CONFIRMED'), None)
    if trig is not None and stop is not None:
        interval = stop.time - trig.time
        need = F(prep['reverse_calibration']['stop_confirmed_s']).limit_denominator(1000) + F(1, 20)
        out['npc_interval_s'], out['ego_b_needs_s'] = float(interval), float(need)
        if interval < need:
            fails.append('NPC_WINDOW_SHORTER_THAN_REVERSE_STOP')
    print(json.dumps(out, default=str))
    print('F03_REPLAY_PASS' if not fails else 'F03_REPLAY_FAIL ' + ' '.join(fails))
    return 0 if not fails else 3


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
