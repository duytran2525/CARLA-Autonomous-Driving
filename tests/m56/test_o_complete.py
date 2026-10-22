"""Source-backed full O actions; synthetic contract inputs, not native science."""
from fractions import Fraction as F

import pytest


@pytest.fixture(scope='module')
def complete_o_a(tmp_path_factory):
    from tests.m56.o_cases import complete_o
    return complete_o(tmp_path_factory.mktemp('o-a-composition')/'sources','A')


@pytest.fixture(scope='module')
def complete_o_b(tmp_path_factory,complete_o_a):
    from tests.m56.o_cases import complete_o
    return complete_o(tmp_path_factory.mktemp('o-b-composition')/'sources','B',complete_o_a.fixture.freeze_ref)


def test_source_o_pass_completes_outbound_fixed_return_and_independent_destination(complete_o_a):
    from m56.evidence import check_integrity
    from m56.metrics import evaluate_episode,_authenticated_events
    c=complete_o_a;out=check_integrity(c.episode,c.fixture)
    assert out.status=='WITNESS_VALID',out.reasons
    verdict=evaluate_episode(c.episode,c.fixture)
    assert (verdict.spawn,verdict.physical,verdict.witness)==('CONFIRMED','COMPLETE','VALID'),verdict.reasons
    assert verdict.metrics['v_mean_E'].value==6 and verdict.metrics['e_lat_peak'].value==F(7,2)
    events={e.name:e for e in _authenticated_events(c.episode,c.fixture)}
    assert events['TARGET_LANE_CONFIRMED'].frame<events['RETURN_MARKER'].frame
    assert events['RETURN_LANE_CONFIRMED'].frame<events['X_END'].frame<events['DESTINATION_CONFIRMED'].frame


def test_source_o_follow_completes_without_passing_or_lateral_motion(complete_o_b):
    from m56.evidence import check_integrity
    from m56.metrics import evaluate_episode,_authenticated_events
    c=complete_o_b;out=check_integrity(c.episode,c.fixture)
    assert out.status=='WITNESS_VALID',out.reasons
    verdict=evaluate_episode(c.episode,c.fixture)
    assert (verdict.spawn,verdict.physical,verdict.witness)==('CONFIRMED','COMPLETE','VALID'),verdict.reasons
    assert F(5,2)<verdict.metrics['v_mean_E'].value<3 and verdict.metrics['e_lat_peak'].value==0
    assert 'TARGET_LANE_CONFIRMED' not in {e.name for e in _authenticated_events(c.episode,c.fixture)}


def test_source_o_metric_separation_still_requires_bound_d09_review(complete_o_a,complete_o_b):
    from dataclasses import replace
    from m56.catalog import _digest
    from m56.metrics import _source_metrics,_ab_review_subject,compare_ab
    a,b=complete_o_a,complete_o_b
    assert _digest(a.fixture)==_digest(b.fixture)
    left,right=_source_metrics(a.episode,a.fixture),_source_metrics(b.episode,b.fixture)
    refs=tuple(dict.fromkeys(r for e in (a.episode,b.episode) for r in (e.fixture,e.manifest,*e.journal,*e.source)))
    review=a.sources.review(_ab_review_subject(a.episode,b.episode,a.fixture.pair,left,right),
        'REALIZED_AB_COMPARABILITY_D09',refs)
    review=replace(review,reasons=tuple(k+': synthetic author software contract only, not scientific qualification'
        for k in ('fulltrace','near_zero','nearstanding','identity','mechanism','comparability')))
    out=compare_ab(a.episode,b.episode,a.fixture.pair,review)
    assert out.status=='PASS',out
    assert out.comparisons[0]>=F(1,5) and out.comparisons[1]==1
    assert compare_ab(a.episode,b.episode,a.fixture.pair,None).status=='REVIEW_REQUIRED'
    assert compare_ab(a.episode,a.episode,a.fixture.pair,review).status=='INVALID'
