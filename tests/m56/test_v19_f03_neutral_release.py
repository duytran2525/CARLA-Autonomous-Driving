"""v19 (docs/m56/PREREG_M56_F_ASEL2_PART2_F03_20261118.md 2): F03 NPC neutral-in-motion release variant, flag-gated by
phases['release']; the v18 held/legacy variants stay the OLD RULE."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from tests.m56.test_f03_normative_response import f03_response, reseal


def neutral():
    r, fixture = f03_response()
    rows = ({'cause': 'NPC_APPROACH', 'after_event': 'CAPTURE_START', 'delay_s': F(21, 20), 'requires': ()},
            {'cause': 'UNPOWERED', 'after_event': 'CAPTURE_START', 'delay_s': F(81, 20), 'requires': ()},
            {'cause': 'F03_BRAKE', 'after_event': 'TRIGGER', 'delay_s': F(2), 'requires': ()},
            {'cause': 'NPC_CLEAR', 'after_event': 'NPC_STOP_CONFIRMED', 'delay_s': F(0), 'requires': ()})  # addendum A
    phases = {**r.phases, 'release': 'neutral-in-motion',
              'program': {'method': 'ordered-event-program-v1', 'initial': 'NPC_HOLD', 'transitions': rows}}
    targets = {'NPC_HOLD': F(0), 'NPC_APPROACH': F(4, 5), 'UNPOWERED': F(0), 'F03_BRAKE': F(0), 'NPC_CLEAR': F(2)}
    return reseal(replace(r, targets=targets, phases=phases)), fixture


def test_neutral_release_admitted():
    from m56.response import _f_script_contract, _forward_contract
    r, fixture = neutral()
    _f_script_contract(r)
    assert _forward_contract(r, fixture) is None


@pytest.mark.parametrize('fault', ['no_flag', 'fast_approach', 'early_release', 'powered_unpowered',
                                   'clear_before_stop', 'fast_clear', 'no_clear'])
def test_neutral_release_faults_blocked(fault):
    from m56.response import _f_script_contract
    r, _ = neutral(); phases = dict(r.phases); targets = dict(r.targets); rows = list(phases['program']['transitions'])
    if fault == 'no_flag':
        phases.pop('release')  # OLD RULE: the approach program is not a v18 variant
    elif fault == 'fast_approach':
        targets['NPC_APPROACH'] = F(2)
    elif fault == 'early_release':
        rows[1] = {**rows[1], 'delay_s': F(41, 20)}
    elif fault == 'powered_unpowered':
        targets['UNPOWERED'] = F(1, 5)
    elif fault == 'clear_before_stop':
        rows[3] = {**rows[3], 'after_event': 'TRIGGER'}
    elif fault == 'fast_clear':
        targets['NPC_CLEAR'] = F(3)
    else:  # the 3-row v19 eb9560c variant, superseded by addendum A
        rows.pop(); targets.pop('NPC_CLEAR')
    phases['program'] = {**phases['program'], 'transitions': tuple(rows)}
    with pytest.raises(ValueError):
        _f_script_contract(reseal(replace(r, phases=phases, targets=targets)))


def test_v18_variants_unchanged():
    from m56.response import _f_script_contract
    r, _ = f03_response()  # legacy UNPOWERED -> F03_BRAKE, no release flag
    _f_script_contract(r)


@pytest.mark.parametrize('flag,gear,manual', [(True, 0, True), (False, 1, False)])
def test_unpowered_command_is_neutral_only_with_flag(flag, gear, manual):
    from m56.model import ControlPacket, EventRecord, ScriptState
    from m56.response import step_response
    from tests.m56.response_cases import response_case
    r, _ = neutral() if flag else f03_response()
    c = response_case('F', role='NPC', events=(), speed=0.)
    auto = ControlPacket(0., 0., 0., False, False, False, 1)  # automatic forward gear, as read back natively
    frame = replace(c.frame, actors=(replace(c.frame.actors[0], readback=auto),), simtime=F(6))
    capture = EventRecord('CAPTURE_START', 100, F(1), (c.ref,))  # c.ref is (100, 1)
    state = ScriptState('NPC_APPROACH' if flag else 'UNPOWERED', F(1), (capture,))
    from m56.model import SourceRef
    witness = SourceRef('synthetic://npc', 'a' * 64, 1, '1', 'literal', 'SYNTHETIC_TEST', 100, F(6))
    frame = replace(frame, integrity={'npc_controls': {'boot': 'boot', 'world': 'world', 'frame': 100, 'actor_id': 1,
                                                       'status': 'CLEAR', 'witness_refs': (witness,)}})
    out = step_response(replace(frame, events=()), state, r)
    assert out.state.phase == 'UNPOWERED'
    control = out.command.control
    assert (control.throttle, control.brake, control.gear, control.manual_gear_shift, control.reverse) == (0., 0., gear, manual, False)
