"""F05 actual <=1m creep/STOP/clear permission, not named intent or stock brake credit."""
import pytest


def test_f05_stop_bound_predicts_next_tick_before_hard_marker_then_observed_stop_and_current_clear(tmp_path):
    from tests.m56.creep_cases import creep_case
    from m56.metrics import detect_events
    c=creep_case(tmp_path/'sources')
    events=detect_events(c.frames,c.fixture);by_name={e.name:e for e in events}
    assert by_name['TRIGGER'].frame==120
    # Literal progress .775 + vmax .5 * dt .05 = .8 bound. Not hardmax1.
    assert by_name['EGO_CREEP_STOPPING_BOUND'].frame==151
    assert by_name['EGO_CREEP_STOP_CONFIRMED'].frame==171
    assert by_name['N_MOVE'].frame==186
    current=tuple(e for e in events if e.name=='QUEUE_CLEAR_CONFIRMED')
    assert tuple(e.frame for e in current)==tuple(range(186,191))
    assert {r.frame for r in by_name['EGO_CREEP_STOP_CONFIRMED'].witness_refs}==set(range(161,172))
    assert not any(e.name in ('F05_END','DESTINATION_CONFIRMED') for e in events)


def test_f05_calibration_recipe_remains_fixture_proof_not_timeless_metric_event_observation(tmp_path):
    from tests.m56.creep_cases import creep_case
    from m56.metrics import detect_events,measure
    from dataclasses import replace
    from fractions import Fraction as F
    c=creep_case(tmp_path/'sources')
    events=detect_events(c.frames,c.fixture)
    frames=tuple(replace(f,integrity={**f.integrity,'metric_context':{
        'reference':c.fixture.pair.reference,'pair_hash':c.fixture.pair.hash,'directed_route':c.fixture.routes['EGO'],
        'uncertainty':{name:F(0) for name in c.fixture.pair.names}}}) for f in c.frames)
    values=measure(frames,c.fixture.pair,events)
    # One metre before actual N_MOVE186; queue end genuinely absent. An extra
    # stopping permission cannot corrupt an otherwise complete frozen window.
    assert (values[0].value,values[0].status)==(1,'VALID'),values
    assert (values[1].value,values[1].status)==(None,'INCOMPLETE'),values
    stop=next(e for e in events if e.name=='EGO_CREEP_STOPPING_BOUND')
    assert all(r.frame is not None and r.time is not None for r in stop.witness_refs)
    assert c.proof.raw_refs  # Certificate remains independently source-reviewed.


@pytest.mark.parametrize('defect',['missing_bound','unsafe_bound','wrong_body','wrong_response'])
def test_f05_unreviewed_or_unbound_stopping_proposal_cannot_produce_stop_permission(tmp_path,defect):
    from tests.m56.creep_cases import creep_case
    from m56.metrics import detect_events
    c=creep_case(tmp_path/'sources',defect)
    events=detect_events(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='TRIGGER')==120
    assert not any(e.name in ('EGO_CREEP_STOPPING_BOUND','EGO_CREEP_STOP_CONFIRMED') for e in events)


@pytest.mark.parametrize('defect',['overshoot','rolling_stop'])
def test_f05_hard_bound_or_rolling_reported_zero_does_not_earn_actual_creep_stop(tmp_path,defect):
    from tests.m56.creep_cases import creep_case
    from m56.metrics import detect_events
    c=creep_case(tmp_path/'sources',defect)
    events=detect_events(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='TRIGGER')==120
    assert not any(e.name=='EGO_CREEP_STOP_CONFIRMED' for e in events)


@pytest.mark.parametrize('defect',['missing_path','path_hash_alias'])
def test_f05_current_clear_is_not_latched_across_missing_or_forged_corridor_receipt(tmp_path,defect):
    from tests.m56.creep_cases import creep_case
    from m56.metrics import detect_events
    c=creep_case(tmp_path/'sources',defect)
    events=detect_events(c.frames,c.fixture)
    assert any(e.name=='QUEUE_CLEAR_CONFIRMED' and e.frame==189 for e in events)
    assert not any(e.name=='QUEUE_CLEAR_CONFIRMED' and e.frame==190 for e in events)
