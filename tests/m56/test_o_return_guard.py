"""A switched target-lane profile does not grant return permission."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


@pytest.mark.parametrize('defect',['clear_missing','path_stale','valid'])
def test_switched_profile_cannot_begin_return_without_current_return_guards(tmp_path,defect):
    from tests.m56.o_cases import o_fixture
    from tests.m56.source_cases import Sources
    from tests.m56.response_cases import response_case
    from m56.model import EventRecord,ScriptState
    from m56.response import step_response,_lateral_contract,_forward_contract
    s=Sources(tmp_path/'sources');c=o_fixture(s);response=c.fixture.responses[0]
    _lateral_contract(response,c.fixture);_forward_contract(response,c.fixture)
    f=response_case('O','A',events=(),speed=6.).frame
    actor=replace(f.actors[0],pose=replace(f.actors[0].pose,x=49.3,y=3.5),arc=F(593,10),body=c.body)
    frame=replace(f,actors=(actor,))
    def event(name,number=frame.frame,time=frame.simtime):
        ref=s.source(name,{'name':name,'frame':number},number,time)
        return EventRecord(name,number,time,(ref,))
    events=[event('TRIGGER'),event('TARGET_LANE_CONFIRMED'),event('REFERENCE_MARKER:TARGET'),event('RETURN_MARKER')]
    if defect=='clear_missing':events.extend((event('LANE_CHANGE_PATH_CLEAR'),event('RETURN_PATH_CLEAR')))
    elif defect=='path_stale':
        events.extend((event('LANE_CHANGE_PATH_CLEAR'),event('RETURN_CLEAR_CONFIRMED'),
                       event('RETURN_PATH_CLEAR',frame.frame-1,frame.simtime-F(1,20))))
    else:events.extend((event('RETURN_CLEAR_CONFIRMED'),event('RETURN_PATH_CLEAR')))
    state=ScriptState('TARGET',frame.simtime,tuple(events))
    if defect=='valid':
        out=step_response(frame,state,response)
        assert out.state.phase=='RETURN' and out.command.kind=='CONTROL' and out.command.offset<0
        assert out.command.target_kmh==F(108,5)
    else:
        with pytest.raises(ValueError,match='RETURN_.*'):
            step_response(frame,state,response)


def test_o_fixed_marker_does_not_infer_clearance_from_estimated_body_length(tmp_path):
    from tests.m56.o_cases import complete_o
    # Constant nominal6/2.5 with actual4.5 body reaches rear clearance.50m
    # only at the fixed42m marker, not for the required preceding.25s.
    # Native prevalidation must resolve that; the software must not shift the
    # marker or silently permit return. This is not an accepted O site/run.
    with pytest.raises(ValueError,match='RETURN_GUARD_MISSING'):
        complete_o(tmp_path/'sources','A',body_length=F(9,2))
