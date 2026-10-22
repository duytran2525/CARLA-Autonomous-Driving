"""Source-backed recurring guards: real event producer, no monkeypatched verdicts."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from tests.m56.test_metrics import (crossing_trace, rebind_trace, io_trace, io_action_trace,
                                   io_wait_trace, i_change_trace, o_return_trace, frame_capability)


def test_decoded_path_receipts_remain_usable_by_actual_event_producer(i_change_trace):
    from m56.model import encode_record,decode_record
    from m56.metrics import detect_events
    c=i_change_trace()
    frames=tuple(decode_record('FrameRecord',encode_record(f)) for f in c.frames)
    events=detect_events(frames,c.fixture)
    assert 'WITNESS_UNKNOWN' not in {e.name for e in events}
    assert next(e.frame for e in events if e.name=='SOURCE_CLEAR_CONFIRMED')==107
    assert any(e.name=='LANE_CHANGE_PATH_CLEAR' for e in events)


def test_decoded_return_receipts_remain_usable_by_actual_event_producer(o_return_trace):
    from m56.model import encode_record,decode_record
    from m56.metrics import detect_events
    c=o_return_trace(outbound_fault='missing')
    frames=tuple(decode_record('FrameRecord',encode_record(f)) for f in c.frames)
    events=detect_events(frames,c.fixture)
    assert {'RETURN_MARKER','RETURN_PATH_CLEAR','RETURN_CLEAR_CONFIRMED','X_END'}<={e.name for e in events}
    assert 'WITNESS_UNKNOWN' not in {e.name for e in events}


@pytest.mark.parametrize('missing,first_cruise',[((),108),((107,),109),((107,108,109),111)])
def test_source_backed_replay_matches_current_path_guard(tmp_path,i_change_trace,missing,first_cruise):
    # Replacing per-issuing-frame guards with the trace's last path event breaks this.
    from tests.m56.source_cases import Sources
    from m56.model import FrozenResponse, CommandRecord, ControlPacket
    from m56.evidence import _phase_integrity
    from m56.metrics import _authenticated_events
    c=i_change_trace();s=Sources(tmp_path/'sources')
    program={'method':'ordered-event-program-v1','initial':'HOLD','transitions':(
        {'cause':'CRUISE','after_event':'SOURCE_CLEAR_CONFIRMED','delay_s':F(0),'requires':('LANE_CHANGE_PATH_CLEAR',)},)}
    responses=tuple(FrozenResponse(role,'B' if role=='EGO' else 'NPC_COMMON',c.fixture.routes[role],
        {'HOLD':F(0),'CRUISE':F(2)}, {},{'program':program},h*64) for role,h in (('EGO','a'),('NPC','b')))
    fixture=replace(c.fixture,responses=responses)
    frames=[]
    for f in c.frames:
        control=ControlPacket(.2,0.,0.,False,False,False,1)
        cause='CRUISE' if f.frame>=first_cruise else 'HOLD'
        actors=tuple(replace(a,commands=(CommandRecord(a.id,f.frame-1,f.frame,'CONTROL',
            F(36,5) if cause=='CRUISE' else F(0),F(0),control,None,cause,r.hash),),readback=control)
                     for a,r in zip(f.actors,responses))
        fields={k:v for k,v in f.integrity.items() if k!='lane_change_path' or f.frame not in missing}
        frames.append(replace(f,actors=actors,integrity=fields))
    frames=s.bind_frames(tuple(frames),fixture)
    boundary=replace(frames[0],frame=99,simtime=-F(1,20),actors=tuple(replace(a,commands=()) for a in frames[0].actors))
    e=s.episode(frames,fixture,boundary)
    events=_authenticated_events(e,fixture)
    assert events is not None
    assert next(x.frame for x in events if x.name=='SOURCE_CLEAR_CONFIRMED')==107
    assert first_cruise-1 in {x.frame for x in events if x.name=='LANE_CHANGE_PATH_CLEAR'}
    assert _phase_integrity(e,fixture)==((),())
