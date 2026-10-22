"""Readable reverse files are not episode-admitted controller authority."""
from dataclasses import replace

import pytest


@pytest.fixture(scope='module')
def release(tmp_path_factory):
    from tests.m56.reverse_composition_cases import npc_release_case
    return npc_release_case(tmp_path_factory.mktemp('reverse-admission')/'sources')


def test_reverse_source_admission_control_has_actual_cue_and_valid_command_replay(release):
    from m56.metrics import _authenticated_events
    from m56.evidence import _phase_integrity
    events=_authenticated_events(release.episode,release.fixture)
    assert events is not None and next(e.frame for e in events if e.name=='TRIGGER')==150
    assert _phase_integrity(release.episode,release.fixture)==((),())


# 'history_observation' moved to the joint-F06 fixture below: in npc_release_case every nested history observation
# is also an episode raw frame (72/72 shared refs, 2026-10-20 diagnosis), so withholding one invalidates the episode
# frame first and the nested-history admission layer is unreachable there.
@pytest.mark.parametrize('missing',['history','corridor','stopping_bound','priority'])
def test_readable_but_unadmitted_reverse_context_cannot_authorize_receiving_torque(release,missing):
    from m56.metrics import _authenticated_events
    from m56.evidence import _phase_integrity,_read_trajectory
    from m56.metrics import _frame_refs
    c=release;observed=next(f for f in c.episode.raw if f.frame==210)
    history=_read_trajectory(observed.integrity['reverse_history_ref'])
    candidates={
        'history':observed.integrity['reverse_history_ref'],
        'corridor':observed.integrity['reverse_corridor'].raw_refs[0],
        'stopping_bound':next(p for p in c.fixture.proofs if p.kind=='REVERSE_STOP_BOUND').raw_refs[0],
        'priority':observed.integrity['npc_controls']['witness_refs'][0],
    }
    ref=candidates[missing]
    assert ref in c.episode.source
    facade=replace(c.episode,source=tuple(r for r in c.episode.source if r!=ref))
    # Neither original bytes/manifest nor the physical cue are rewritten. The
    # negative isolates authority membership, not a broken detector or setup.
    events=_authenticated_events(facade,c.fixture)
    assert events is not None and next(e.frame for e in events if e.name=='TRIGGER')==150
    invalid,uncertain=_phase_integrity(facade,c.fixture)
    assert not invalid,(invalid,uncertain)
    assert 'REVERSE_COMMAND_REPLAY_UNPROVEN' in uncertain,(invalid,uncertain)


@pytest.fixture(scope='module')
def joint_release(tmp_path_factory):
    """Joint F06 producer whose recorded reverse history starts at the boundary observation (frame 99),
    which is NOT an episode raw frame: a history-only prefix observation exists."""
    from types import SimpleNamespace
    from tests.m56.f06_cases import joint_f06_producer
    c=joint_f06_producer(tmp_path_factory.mktemp('joint-admission')/'sources','A',last=212)
    frames=c.sources.bind_frames(c.frames,c.fixture)
    return SimpleNamespace(episode=c.sources.episode(frames,c.fixture,c.boundary),fixture=c.fixture)


def test_unadmitted_nested_history_prefix_observation_cannot_authorize_receiving_torque(joint_release):
    from m56.metrics import _authenticated_events,_frame_refs
    from m56.evidence import _phase_integrity,_read_trajectory
    c=joint_release;observed=next(f for f in c.episode.raw if f.frame==210)
    history=_read_trajectory(observed.integrity['reverse_history_ref'])
    episode_refs={r for f in c.episode.raw for r in _frame_refs(f)}
    ref=next(r for f in history for r in _frame_refs(f) if r not in episode_refs)
    assert ref in c.episode.source
    facade=replace(c.episode,source=tuple(r for r in c.episode.source if r!=ref))
    events=_authenticated_events(facade,c.fixture)
    assert events is not None and next(e.frame for e in events if e.name=='TRIGGER')==150
    invalid,uncertain=_phase_integrity(facade,c.fixture)
    assert not invalid,(invalid,uncertain)
    assert 'REVERSE_COMMAND_REPLAY_UNPROVEN' in uncertain,(invalid,uncertain)
