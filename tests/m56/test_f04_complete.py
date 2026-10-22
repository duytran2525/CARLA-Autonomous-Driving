"""Real F04 producer -> sealed W01-W05 -> public action; synthetic software only."""
from fractions import Fraction as F

import pytest


@pytest.fixture(scope='module')
def f04_a(tmp_path_factory):
    from tests.m56.f04_cases import complete_f04
    return complete_f04(tmp_path_factory.mktemp('f04-a-composition')/'sources','A')


@pytest.fixture(scope='module')
def f04_b(tmp_path_factory,f04_a):
    from tests.m56.f04_cases import complete_f04
    return complete_f04(tmp_path_factory.mktemp('f04-b-composition')/'sources','B',f04_a.fixture.freeze_ref)


@pytest.mark.parametrize('action',['A','B'])
def test_f04_full_source_public_action_requires_actual_clearance_or_offset_return_then_independent_destination(action,request):
    from m56.evidence import check_integrity
    from m56.metrics import evaluate_episode
    c=request.getfixturevalue('f04_'+action.lower())
    integrity=check_integrity(c.episode,c.fixture)
    out=evaluate_episode(c.episode,c.fixture)
    assert integrity.status=='WITNESS_VALID',integrity
    assert (out.spawn,out.physical,out.witness)==('CONFIRMED','COMPLETE','VALID'),out
    events={e.name:e for e in out.events}
    assert events['TRIGGER'].frame==132
    assert events['DOOR_CLOSED_CLEAR_CONFIRMED'].frame==193
    assert events['F04_END'].frame==(329 if action=='A' else 404)
    assert events['DESTINATION_CONFIRMED'].frame==(504 if action=='A' else 674)
    if action=='A':
        assert events['STOP_AFTER_TRIGGER'].frame==143
        assert out.metrics['e_lat_peak_m'].value==0
    else:
        assert events['F04_OFFSET_CONFIRMED'].frame==257
        assert events['F04_RETURN_MARKER'].frame==468
        assert events['F04_RETURN_REFERENCE_MARKER'].frame==588
        assert events['F04_HOME_CONFIRMED'].frame==593
        assert out.metrics['e_lat_peak_m'].value==F(3,4)
    assert events['DESTINATION_CONFIRMED'].frame>events['F04_END'].frame
    assert out.metrics['passage_time_s'].value==(F(197,20) if action=='A' else F(68,5))
    npc_commands=tuple(a.commands[0] for f in c.episode.raw for a in f.actors if a.role=='NPC')
    assert tuple(cmd.frame for cmd in npc_commands if cmd.kind=='DOOR_OPEN_REQUEST')==(131,)
    assert tuple(cmd.frame for cmd in npc_commands if cmd.kind=='DOOR_CLOSE_REQUEST')==(192,)
    assert all(cmd.target_kmh==0 and cmd.control.throttle==0 for cmd in npc_commands)
    # No native dynamics, selected fixture qualification, actual blueprint/door
    # calibration, independent-person review or scientific A/B acceptance claim.


def test_f04_source_decoded_pair_metric_separation_still_needs_bound_d09_author_review(f04_a,f04_b):
    from dataclasses import replace
    from m56.catalog import _digest
    from m56.metrics import _source_metrics,_ab_review_subject,compare_ab
    a,b=f04_a,f04_b
    assert _digest(a.fixture)==_digest(b.fixture)
    left,right=_source_metrics(a.episode,a.fixture),_source_metrics(b.episode,b.fixture)
    refs=tuple(dict.fromkeys(r for e in (a.episode,b.episode) for r in (e.fixture,e.manifest,*e.journal,*e.source)))
    review=a.sources.review(_ab_review_subject(a.episode,b.episode,a.fixture.pair,left,right),
        'REALIZED_AB_COMPARABILITY_D09',refs)
    review=replace(review,reasons=tuple(k+': synthetic author software composition, not scientific qualification'
        for k in ('fulltrace','near_zero','nearstanding','identity','mechanism','comparability')))
    out=compare_ab(a.episode,b.episode,a.fixture.pair,review)
    assert out.status=='PASS',out
    assert out.comparisons==(F(75,272),F(1)),out.comparisons
    assert compare_ab(a.episode,b.episode,a.fixture.pair,None).status=='REVIEW_REQUIRED'
    assert compare_ab(a.episode,a.episode,a.fixture.pair,review).status=='INVALID'
