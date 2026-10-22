"""Reviewed source F04 door requests and actual envelopes remain separate observations."""
from dataclasses import replace

import pytest


@pytest.mark.parametrize('fault',[None,'missing_open_request','missing_close_request','extra_close_request',
                                  'motor_throttle','missing_boundary_priority'])
def test_f04_source_request_kind_clock_and_hold_are_replayed_not_inferred_from_geometry(tmp_path,fault):
    from tests.m56.test_f04_spatial_phase_events import f04_spatial_observations
    from tests.m56.source_cases import Sources
    from m56.evidence import _phase_integrity,_frame_integrity
    from m56.metrics import _authenticated_events
    c=f04_spatial_observations(tmp_path/'physical',npc_schedule=True)
    s=Sources(tmp_path/'composition');s.refs.extend(c.s.refs)
    frames=[]
    for frame in c.frames:
        ego,npc=frame.actors;command=npc.commands[0]
        if (fault=='missing_open_request' and frame.frame==99) or (fault=='missing_close_request' and frame.frame==161):
            command=replace(command,kind='CONTROL')
        if fault=='extra_close_request' and frame.frame==162:command=replace(command,kind='DOOR_CLOSE_REQUEST')
        if fault=='motor_throttle' and frame.frame==102:
            control=replace(npc.readback,throttle=.2)
            npc=replace(npc,readback=control);command=replace(command,control=control)
        npc=replace(npc,commands=(command,))
        frames.append(replace(frame,actors=(ego,npc)))
    bound=s.bind_frames(tuple(frames),c.fixture)
    boundary=bound[0];frames=bound[1:]
    if fault=='missing_boundary_priority':
        boundary=replace(boundary,integrity={k:v for k,v in boundary.integrity.items() if k!='npc_controls'})
    episode=s.episode(frames,c.fixture,boundary)
    assert _frame_integrity(episode,c.fixture)==((),())
    events=_authenticated_events(episode,c.fixture)
    assert events is not None
    assert next(e.frame for e in events if e.name=='TRIGGER')==100
    assert next(e.frame for e in events if e.name=='DOOR_CLOSED_CLEAR_CONFIRMED')==161
    assert next(e.frame for e in events if e.name=='F04_HOME_CONFIRMED')==465
    expected=((),()) if fault is None else ((),('FORWARD_COMMAND_REPLAY_UNPROVEN',)) if fault=='missing_boundary_priority' else (('FORWARD_COMMAND_MISMATCH',),())
    assert _phase_integrity(episode,c.fixture)==expected
    # All controls and source packets are genuinely re-bound/reviewed, including
    # the mutation. Matching recorded geometry cannot approve wrong issue/control.
    # Not full W01/W03/W05/public action, native articulation/contact or destination.
