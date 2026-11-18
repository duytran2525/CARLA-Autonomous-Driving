"""F03 replay gate (PREREG F part 2 section 4 + addendum A3): replay ONE runner-recorded episode (the pre-registered A-only
probe, native-f-ab.py --probe-a, F03Kit b_fields_in_a) through the product, offline:
  1. detect_events on the sealed frames: TRIGGER and NPC_STOP_CONFIRMED, no WITNESS_UNKNOWN;
  2. the NPC command causes in order NPC_HOLD -> NPC_APPROACH -> UNPOWERED -> F03_BRAKE (-> NPC_CLEAR);
  4. (addendum A3/A4) the product evaluator on the episode: physical not FAILED, no COLLISION_OBSERVED, DESTINATION_CONFIRMED;
     TRIGGER -> NPC_STOP_CONFIRMED >= the chosen reverse trial's stop_confirmed_s + 1/20 (prepare.json, 2nd argument);
  3. the EGO B kernel (response.reverse_intent, as runtime._commands) on every frame from TRIGGER for 2 s: REVERSE commands,
     never BLOCKED (the B-only frame fields: reverse_corridors, reverse_history_ref, REVERSE_STOP_BOUND, ground).
Prints F03_REPLAY_PASS or F03_REPLAY_FAIL <reasons>; exit 0 / 3. A pass is a tooling gate, not an outcome.
  python -I native-f03-replay.py COMPILE_SCENE_DIR PREPARE_JSON (scene dir holds fixture-frozen.json and probe-a/)"""
import json
import sys
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_v2_common  # noqa: F401,E402  (M56_CODE on sys.path)
from m56 import runtime  # noqa: E402
from m56.metrics import detect_events, evaluate_episode  # noqa: E402
from m56.model import CompiledFixture, ScriptState, decode_record, load_json  # noqa: E402
from m56.response import reverse_intent  # noqa: E402


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
        b = next(r for r in fixture.responses if r.actor_role == 'EGO' and r.action_id == 'B')
        state = ScriptState('HOLD', frames[0].simtime, ())
        kernel = []
        for f in frames:
            if f.frame < trig.frame or f.simtime > trig.time + 2:
                continue
            admitted = tuple(e for e in events if e.frame <= f.frame and e.time <= f.simtime and e.name != 'CAPTURE_START')
            rs = reverse_intent(f, replace(state, events=admitted), b, fixture)
            state = rs.state; kernel.append((f.frame, rs.command.cause, rs.command.kind,
                                             None if rs.command.control is None else rs.command.control.throttle))
        out['kernel_first'] = kernel[:3]; out['kernel_causes'] = sorted({k[1] for k in kernel})
        if not kernel or any(k[1] != 'REVERSE' for k in kernel):
            fails.append('KERNEL_' + ','.join(sorted({str(k[1]) for k in kernel})))
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
