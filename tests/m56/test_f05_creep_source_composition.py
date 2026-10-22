"""Actual F05 bounded stock-creep source replay before moving NPC, not full queue acceptance."""
from dataclasses import replace

import pytest


@pytest.mark.parametrize('fault',[None,'late_brake','lost_current_path','missing_fixture','unadmitted_history'])
def test_f05_canonical_creep_source_replays_current_bound_admission_and_terminal_brake(tmp_path,fault):
    from tests.m56.creep_cases import creep_case
    from tests.m56.source_cases import Sources
    from m56.model import SourceRef
    from m56.evidence import _phase_integrity,_frame_integrity
    from m56.metrics import _authenticated_events
    c=creep_case(tmp_path/'physical',last=175);s=Sources(tmp_path/'composition');s.refs.extend(c.s.refs)
    provisional=[]
    for frame in c.frames:
        ego,npc=frame.actors;fields=dict(frame.integrity)
        if fault=='late_brake' and frame.frame==152:
            control=replace(ego.readback,brake=0.)
            ego=replace(ego,readback=control,commands=(replace(ego.commands[0],control=control),))
        packet={'boot':frame.boot,'world':frame.world,'frame':frame.frame,'actor_id':npc.id,'status':'CLEAR'}
        ref=s.source('priority-'+str(frame.frame),packet,frame.frame,frame.simtime)
        fields['npc_controls']={**packet,'witness_refs':(ref,)}
        provisional.append(replace(frame,actors=(ego,npc),integrity=fields))
    bound=s.bind_frames(tuple(provisional),c.fixture);frames=[]
    for i,frame in enumerate(bound):
        history=tuple(replace(f,integrity={k:v for k,v in f.integrity.items() if k in ('frame_refs','continuous_geometry')}) for f in bound[:i+1])
        ref=s.source('history-'+str(frame.frame),history)
        fields={**frame.integrity,'creep_history_ref':ref}
        if fault=='unadmitted_history' and frame.frame==140:s.refs.remove(ref)
        if fault=='lost_current_path' and frame.frame==140:fields.pop('queue_path',None)
        if fault=='missing_fixture' and frame.frame==140:fields.pop('creep_fixture_ref',None)
        frames.append(replace(frame,integrity=fields))
    boundary=replace(frames[0],frame=99,simtime=frames[0].simtime-frames[0].dt,integrity={},
        actors=tuple(replace(a,commands=()) for a in frames[0].actors))
    packet={'boot':boundary.boot,'world':boundary.world,'frame':99,'actor_id':2,'status':'CLEAR'}
    ref=s.source('boundary-priority',packet,99,boundary.simtime)
    boundary=replace(boundary,integrity={'npc_controls':{**packet,'witness_refs':(ref,)}})
    episode=s.episode(tuple(frames),c.fixture,boundary)
    assert _frame_integrity(episode,c.fixture)==((),())
    events=_authenticated_events(episode,c.fixture)
    assert events is not None
    assert next(e.frame for e in events if e.name=='TRIGGER')==120
    assert next(e.frame for e in events if e.name=='EGO_CREEP_STOPPING_BOUND')==151
    assert next(e.frame for e in events if e.name=='EGO_CREEP_STOP_CONFIRMED')==171
    expected=((),()) if fault is None else (('FORWARD_COMMAND_MISMATCH',),()) if fault=='late_brake' else ((),('FORWARD_COMMAND_REPLAY_UNPROVEN',))
    assert _phase_integrity(episode,c.fixture)==expected
    # This does not supply W01/W03/W05/independent destination or public COMPLETE.
