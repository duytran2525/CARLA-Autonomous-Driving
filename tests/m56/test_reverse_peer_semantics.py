"""Release must be a real mechanism endpoint, not a true-but-static named STOP."""
from fractions import Fraction as F

import pytest


@pytest.mark.parametrize('mechanism',['F03','F06-ALT1'])
@pytest.mark.parametrize('mode',['gear','forward'])
def test_joint_source_physical_peer_endpoint_retains_terminal_controller_path(tmp_path,mechanism,mode):
    from tests.m56.joint_reverse_cases import joint_reverse_case
    from m56.response import reverse_intent
    c=joint_reverse_case(tmp_path/'sources',mechanism,mode)
    out=reverse_intent(c.frame,c.state,c.response,c.fixture)
    assert out.command.kind==('GEAR_TRANSITION' if mode=='gear' else 'CONTROL'),out
    assert out.state.phase==('WAIT_FORWARD_GEAR' if mode=='gear' else 'FORWARD')
    if mode=='gear':
        assert out.command.control.throttle==0 and out.command.control.brake==.3
        assert out.command.control.gear==1 and not out.command.control.reverse
    else:assert out.command.control is None and out.command.target_kmh==F(36,5)
    # No actual destination, W01-W05 full episode, calibration or native admission.
    assert out.state.phase!='COMPLETE'


@pytest.mark.parametrize('mechanism',['F03','F06-ALT1'])
@pytest.mark.parametrize('mode',['gear','forward'])
def test_static_peer_stop_with_exact_source_packets_does_not_release_mechanism_reserve(tmp_path,mechanism,mode):
    from tests.m56.reverse_cases import reverse_case,terminal_observation,forward_observations
    from m56.response import reverse_intent
    c=reverse_case(tmp_path/'sources',mechanism=mechanism,progress=F(1),speed=.5,reverse=True,
        phase='FORWARD' if mode=='forward' else 'STOPPING')
    terminal=terminal_observation(c,forward=mode=='forward',released=True)
    frame=forward_observations(c,terminal) if mode=='forward' else terminal
    out=reverse_intent(frame,c.state,c.response,c.fixture)
    assert out.command.kind=='BLOCKED',out
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.control.throttle==0
    assert out.command.target_kmh==0


@pytest.mark.parametrize('mode',['gear','forward'])
@pytest.mark.parametrize('delay',[10,61])
def test_f06_late_ego_reserve_cannot_be_rescued_by_actual_peer_end(tmp_path,mode,delay):
    from tests.m56.joint_reverse_cases import joint_reverse_case
    from m56.response import reverse_intent
    # Actual NPC still releases211/reaches2m290/STOP301. EGO waits to211,
    # retreats212..251 and stops252..262, too late despite valid terminal STOP.
    # delay10 yields STOP confirmation on211 itself, still not BEFORE NPC motion.
    c=joint_reverse_case(tmp_path/'sources',mode=mode,ego_delay_frames=delay)
    out=reverse_intent(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='FAILED' and out.command.kind=='BLOCKED',out
    assert out.command.control.throttle==0 and out.command.target_kmh==0
    assert out.command.cause=='RESERVATION_STOP_NOT_CONFIRMED'


@pytest.mark.parametrize('mechanism',['F03','F06-ALT1'])
def test_applied_forward_gear_cannot_precede_observation_of_peer_stop_endpoint(tmp_path,mechanism):
    from tests.m56.joint_reverse_cases import joint_reverse_case
    from m56.response import reverse_intent
    c=joint_reverse_case(tmp_path/'sources',mechanism,'forward',gear_early=True)
    out=reverse_intent(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.kind=='BLOCKED',out
    assert out.command.control.throttle==0 and out.command.target_kmh==0


@pytest.mark.parametrize('mode',['gear','forward'])
def test_f06_reserve_cannot_erode_before_peer_endpoint_even_with_terminal_stop(tmp_path,mode):
    from tests.m56.joint_reverse_cases import joint_reverse_case
    from m56.response import reverse_intent
    # EGO initially attains1m+STOP before NPC211, then advances .25m in
    # reverse gear221..230 while NPC still retreats. Cumulative retreat remains
    # 1m and both terminal STOPs exist; neither repairs the lost reservation.
    c=joint_reverse_case(tmp_path/'sources',mode=mode,reserve_erosion=True)
    out=reverse_intent(c.frame,c.state,c.response,c.fixture)
    assert out.command.kind=='BLOCKED' and out.state.phase in ('FAILED','BLOCKED_CONTROLLER'),out
    assert out.command.control.throttle==0 and out.command.target_kmh==0


@pytest.mark.parametrize('samples,allowed',[(10,False),(11,True)])
def test_npc_own_stop_is_observed_before_next_frame_gear_readback(tmp_path,samples,allowed):
    from tests.m56.reverse_cases import reverse_case,terminal_observation,forward_observations
    from m56.response import reverse_intent
    c=reverse_case(tmp_path/'sources',role='NPC',phase='NPC_FORWARD',waiting_s=F(3),progress=F(2),speed=.5,reverse=True)
    terminal=terminal_observation(c,samples=samples,forward=True)
    frame=forward_observations(c,terminal)
    out=reverse_intent(frame,c.state,c.response,c.fixture)
    assert out.state.phase==('NPC_FORWARD' if allowed else 'BLOCKED_CONTROLLER'),out
    assert out.command.kind==('CONTROL' if allowed else 'BLOCKED')
    if not allowed:assert out.command.control.throttle==0


def test_own_stop_confirmation_must_precede_applied_forward_gear_not_include_it(tmp_path):
    from tests.m56.joint_reverse_cases import joint_reverse_case
    from m56.response import reverse_intent
    # F03 actual peer endpoint157 is known before applied gear158. EGO's
    # shifted retreat108..147 stops148..158: its .50s STOP is only known158,
    # too late to have issued the already-applied forward gear in157.
    c=joint_reverse_case(tmp_path/'sources','F03','forward',ego_delay_frames=2)
    out=reverse_intent(c.frame,c.state,c.response,c.fixture)
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.kind=='BLOCKED',out
    assert out.command.control.throttle==0 and out.command.target_kmh==0
