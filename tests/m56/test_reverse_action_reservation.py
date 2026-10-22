"""Public physical-action axis must not postpone an observed failed F06 reservation."""
import pytest


@pytest.mark.parametrize('delay',[10,61])
def test_f06_action_axis_reports_late_reserve_without_waiting_for_destination(tmp_path,delay):
    from tests.m56.joint_reverse_cases import joint_reverse_case
    from m56.metrics import detect_events,_f_action
    from m56.model import PhysicalState
    c=joint_reverse_case(tmp_path/'sources',ego_delay_frames=delay)
    events=detect_events(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='TRIGGER')==150
    assert next(e.frame for e in events if e.name=='NPC_REVERSE_TARGET_STOP_CONFIRMED')==301
    state,reasons=_f_action(c.frames,c.fixture,events)
    assert state==PhysicalState.FAILED,(state,reasons)
    assert 'RESERVATION_STOP_NOT_CONFIRMED' in reasons


def test_f06_action_axis_keeps_on_time_reserve_distinct_from_destination(tmp_path):
    from tests.m56.joint_reverse_cases import joint_reverse_case
    from m56.metrics import detect_events,_f_action
    from m56.model import PhysicalState
    c=joint_reverse_case(tmp_path/'sources')
    state,reasons=_f_action(c.frames,c.fixture,detect_events(c.frames,c.fixture))
    assert state==PhysicalState.INCOMPLETE,(state,reasons)
    assert 'DESTINATION_CONFIRMED_MISSING' in reasons
    assert 'RESERVATION_STOP_NOT_CONFIRMED' not in reasons
