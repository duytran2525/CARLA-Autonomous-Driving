"""Joint command composition is not reverse endpoint/destination acceptance."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


@pytest.fixture(scope='module',params=['A','B'])
def joint(request,tmp_path_factory):
    from tests.m56.f06_cases import joint_f06_producer
    action=request.param;c=joint_f06_producer(tmp_path_factory.mktemp('f06-joint-'+action)/'sources',action,last=212)
    frames=c.sources.bind_frames(c.frames,c.fixture)
    return action,c,c.sources.episode(frames,c.fixture,c.boundary)


def test_f06_both_real_producers_receive_independent_role_corridors_before_npc_motion(joint):
    from m56.evidence import _phase_integrity
    from m56.metrics import _authenticated_events
    action,c,episode=joint;frames=episode.raw
    events=_authenticated_events(episode,c.fixture)
    assert events is not None and next(e.frame for e in events if e.name=='TRIGGER')==150
    assert not any(e.name in ('NPC_REVERSE_TARGET_STOP_CONFIRMED','DESTINATION_CONFIRMED') for e in events)
    issuing=next(f for f in frames if f.frame==210)
    assert set(issuing.integrity['reverse_corridors'])==({'NPC'} if action=='A' else {'EGO','NPC'})
    receiving=next(f for f in frames if f.frame==211)
    npc=next(a for a in receiving.actors if a.role=='NPC')
    assert (npc.commands[0].kind,npc.commands[0].target_kmh,npc.readback.throttle,npc.readback.gear)==('REVERSE',F(9,5),.25,-1)
    ego=next(a for a in receiving.actors if a.role=='EGO')
    assert ego.pose.x==(4. if action=='A' else 3.)
    assert ego.velocity==(0.,0.,0.)
    assert (ego.readback.throttle,ego.readback.brake)==(0.,.3)
    assert _phase_integrity(episode,c.fixture)==((),())


def test_f06_readable_owned_gear_request_requires_episode_admission_before_using_its_cue(joint):
    from m56.evidence import _frame_integrity
    from m56.metrics import _authenticated_events
    _,c,episode=joint
    observed=next(f for f in episode.raw if f.frame==149)
    ref=observed.integrity['preparation_request'].raw_refs[0]
    assert ref in episode.source
    facade=replace(episode,source=tuple(r for r in episode.source if r!=ref))
    invalid,uncertain=_frame_integrity(facade,c.fixture)
    assert 'FRAME_CAPABILITY_SOURCE_INVALID' in invalid,(invalid,uncertain)
    assert _authenticated_events(facade,c.fixture) is None


@pytest.mark.parametrize('action',['A','B'])
def test_f06_joint_peer_stop_and_applied_gear_allow_materialized_stock_intent_not_completion(tmp_path,action):
    from tests.m56.f06_cases import joint_f06_producer
    from m56.evidence import _phase_integrity
    from m56.metrics import _authenticated_events
    c=joint_f06_producer(tmp_path/'sources',action,last=305)
    frames=c.sources.bind_frames(c.frames,c.fixture)
    episode=c.sources.episode(frames,c.fixture,c.boundary)
    events=_authenticated_events(episode,c.fixture)
    assert events is not None
    assert next(e.frame for e in events if e.name=='NPC_REVERSE_TARGET_STOP_CONFIRMED')==301
    assert not any(e.name=='DESTINATION_CONFIRMED' for e in events)
    roles=('NPC',) if action=='A' else ('EGO','NPC')
    for role in roles:
        commands=[a.commands[0] for f in frames for a in f.actors if a.role==role]
        gear=next(command for command in commands if command.kind=='GEAR_TRANSITION' and command.frame==301)
        assert (gear.frame,gear.next_frame,gear.control.reverse,gear.control.gear)==(301,302,False,1)
        forward=next(command for command in commands if command.frame==302)
        assert (forward.next_frame,forward.kind,forward.target_kmh,forward.control.throttle)==(303,'CONTROL',F(36,5),.2)
    assert _phase_integrity(episode,c.fixture)==((),())
