"""Common F05 actual source intent/terminal hold/current priority, not full PID dynamics."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


@pytest.mark.parametrize('fault',[None,'coast_while_hold','throttle_while_hold','red_at_fixed_release','missing_boundary_priority'])
def test_f05_common_source_replays_mandatory_hold_and_actual_fixed_release_priority(tmp_path,fault):
    from tests.m56.test_f05_phase_events import f05_observations
    from tests.m56.source_cases import Sources
    from m56.evidence import _frame_integrity,_phase_integrity
    from m56.metrics import _authenticated_events
    c=f05_observations(tmp_path/'physical',last=195);s=Sources(tmp_path/'composition');s.refs.extend(c.s.refs)
    frames=[]
    for raw in c.frames:
        ego,npc=raw.actors
        if raw.frame==150 and fault in ('coast_while_hold','throttle_while_hold'):
            control=replace(npc.readback,brake=0.,throttle=.2 if fault=='throttle_while_hold' else 0.)
            npc=replace(npc,readback=control,commands=(replace(npc.commands[0],control=control),))
        packet={'boot':raw.boot,'world':raw.world,'frame':raw.frame,'actor_id':2,
            'status':'RED' if fault=='red_at_fixed_release' and raw.frame==180 else 'CLEAR'}
        ref=s.source('traffic-'+str(raw.frame),packet,raw.frame,raw.simtime)
        frames.append(replace(raw,actors=(ego,npc),integrity={**raw.integrity,'npc_controls':{**packet,'witness_refs':(ref,)}}))
    frames=s.bind_frames(tuple(frames),c.fixture)
    boundary=replace(frames[0],frame=99,simtime=-F(1,20),integrity={},
        actors=tuple(replace(a,commands=()) for a in frames[0].actors))
    if fault!='missing_boundary_priority':
        packet={'boot':boundary.boot,'world':boundary.world,'frame':99,'actor_id':2,'status':'CLEAR'}
        ref=s.source('boundary-priority',packet,99,boundary.simtime)
        boundary=replace(boundary,integrity={'npc_controls':{**packet,'witness_refs':(ref,)}})
    episode=s.episode(frames,c.fixture,boundary)
    assert _frame_integrity(episode,c.fixture)==((),())
    events=_authenticated_events(episode,c.fixture)
    assert events is not None
    assert next(e.frame for e in events if e.name=='TRIGGER')==120
    assert next(e.frame for e in events if e.name=='N_MOVE')==186
    expected=((),()) if fault is None else ((),('FORWARD_COMMAND_REPLAY_UNPROVEN',)) if fault=='missing_boundary_priority' else (('FORWARD_COMMAND_MISMATCH',),())
    assert _phase_integrity(episode,c.fixture)==expected
    # Real stock-positive PID controls are not recreated here. The mandatory
    # zero-target motor hold and source priority cannot disappear behind a
    # matching phase/target/hash or an observed motion trajectory.
