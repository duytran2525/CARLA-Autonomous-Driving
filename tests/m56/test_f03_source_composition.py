"""Actual source F03 common coasting/brake must replay as forward, not reverse exception."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


@pytest.mark.parametrize('fault',[None,'coast_brake','missing_boundary_priority'])
def test_common_f03_unpowered_brake_source_program_is_not_npc_reverse_exception(tmp_path,fault):
    from tests.m56.test_f03_phase_events import f03_observations
    from tests.m56.source_cases import Sources
    from m56.catalog import _digest
    from m56.model import FrozenResponse,CommandRecord
    from m56.metrics import _authenticated_events
    from m56.evidence import _phase_integrity
    root=tmp_path/'sources';root.mkdir();(root/'physical').mkdir()
    physical=f03_observations(root/'physical')
    # Separate source namespace: never overwrite the immutable physical frame refs.
    s=Sources(root/'composition');s.refs.extend(physical.s.refs)
    ego=FrozenResponse('EGO','A',physical.fixture.routes['EGO'],{'HOLD':F(0)},
        {'method':'quintic-arc-v1','segments':()},
        {'category':'F','program':{'method':'ordered-event-program-v1','initial':'HOLD','transitions':()}},'e'*64)
    ego=replace(ego,hash=_digest({k:getattr(ego,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    fixture=replace(physical.fixture,responses=(ego,physical.response));frames=[]
    for f in physical.frames:
        e,n=f.actors
        command=CommandRecord(e.id,f.frame-1,f.frame,'CONTROL',F(0),F(0),e.readback,None,'HOLD',ego.hash)
        if fault=='coast_brake' and f.frame==102:
            control=replace(n.readback,brake=.3)
            n=replace(n,readback=control,commands=(replace(n.commands[0],control=control),))
        packet={'boot':f.boot,'world':f.world,'frame':f.frame,'actor_id':n.id,'status':'CLEAR'}
        ref=s.source('f03-priority-'+str(f.frame),packet,f.frame,f.simtime)
        frames.append(replace(f,actors=(replace(e,commands=(command,)),n),integrity={**f.integrity,
            'npc_controls':{**packet,'witness_refs':(ref,)}}))
    frames=s.bind_frames(tuple(frames),fixture)
    boundary=replace(frames[0],frame=99,simtime=-F(1,20),integrity={},
        actors=tuple(replace(a,commands=()) for a in frames[0].actors))
    if fault!='missing_boundary_priority':
        packet={'boot':boundary.boot,'world':boundary.world,'frame':99,'actor_id':2,'status':'CLEAR'}
        ref=s.source('f03-priority-boundary',packet,99,boundary.simtime)
        boundary=replace(boundary,integrity={'npc_controls':{**packet,'witness_refs':(ref,)}})
    episode=s.episode(frames,fixture,boundary)
    events=_authenticated_events(episode,fixture)
    assert events is not None
    assert next(e.frame for e in events if e.name=='TRIGGER')==105
    assert next(e.frame for e in events if e.name=='NPC_STOP_CONFIRMED')==157
    expected={'coast_brake':(('FORWARD_COMMAND_MISMATCH',),()),
              'missing_boundary_priority':((),('FORWARD_COMMAND_REPLAY_UNPROVEN',))}
    assert _phase_integrity(episode,fixture)==expected.get(fault,((),()))
    # This only tests W02 phase composition, not full public/contact/destination.
