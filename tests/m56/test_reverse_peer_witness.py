"""A named NPC STOP is not authority to release EGO's reserved rear space."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


def peer_case(root,mechanism,mode):
    from tests.m56.joint_reverse_cases import joint_reverse_case
    c=joint_reverse_case(root,mechanism,mode)
    return c,c.frame


@pytest.mark.parametrize('mechanism',['F03','F06-ALT1'])
@pytest.mark.parametrize('mode',['gear','forward'])
def test_bound_actual_peer_endpoint_packet_retains_software_terminal_behavior(tmp_path,mechanism,mode):
    from m56.response import reverse_intent
    c,frame=peer_case(tmp_path/'sources',mechanism,mode)
    out=reverse_intent(frame,c.state,c.response,c.fixture)
    assert out.command.kind==('GEAR_TRANSITION' if mode=='gear' else 'CONTROL'),out
    # The baseline has actual mechanism history; packet defects below cannot
    # hide behind an already-invalid static peer. Still not native qualification.
    assert out.state.phase==('WAIT_FORWARD_GEAR' if mode=='gear' else 'FORWARD')


@pytest.mark.parametrize('mechanism',['F03','F06-ALT1'])
@pytest.mark.parametrize('mode',['gear','forward'])
@pytest.mark.parametrize('fault',['checksum','ego_only','future_clock','foreign_world'])
def test_named_peer_stop_with_unbound_packet_never_releases_reserve(tmp_path,mechanism,mode,fault):
    from m56.response import reverse_intent
    from m56.evidence import _read_trajectory
    c,frame=peer_case(tmp_path/'sources',mechanism,mode);event=frame.events[0]
    at=next(f for f in _read_trajectory(frame.integrity['reverse_history_ref']) if f.frame==event.frame)
    if fault=='checksum':ref=replace(event.witness_refs[0],sha256='0'*64)
    else:
        actors=tuple(a for a in at.actors if a.role=='EGO') if fault=='ego_only' else at.actors
        number=at.frame+1 if fault=='future_clock' else at.frame
        time=at.simtime+F(1,20) if fault=='future_clock' else at.simtime
        world='foreign' if fault=='foreign_world' else at.world
        ref=c.s.source('forged-peer-'+fault,{'boot':at.boot,'world':world,'frame':number,'simtime':time,'actors':actors},number,time)
    frame=replace(frame,events=(replace(event,witness_refs=(ref,)),))
    out=reverse_intent(frame,c.state,c.response,c.fixture)
    assert out.command.kind=='BLOCKED',out
    assert out.state.phase=='BLOCKED_CONTROLLER' and out.command.control.throttle==0
    assert out.command.target_kmh==0
