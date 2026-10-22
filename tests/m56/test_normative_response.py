"""Approved target/phase rules, independently of a self-consistent recorded program."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('category,action',[('C','A'),('L','A'),('M','B')])
def test_crossing_program_obeys_approved_targets_and_guards(require,category,action):
    from tests.m56.response_cases import response_case
    c=response_case(category,action)
    fixture=SimpleNamespace(domain=SimpleNamespace(topology={'category':category}),environment={})
    assert require('m56.response','_forward_contract')(c.response,fixture) is None


@pytest.mark.parametrize('fault',['nominal','yield','resume','stop_guard','clear_guard','delay'])
def test_self_consistent_program_cannot_override_frozen_crossing_policy(require,fault):
    from tests.m56.response_cases import response_case
    c=response_case('C','A' if fault in ('stop_guard','clear_guard') else 'B');r=c.response;targets=dict(r.targets)
    program=dict(r.phases['program']);rows=list(program['transitions'])
    if fault=='nominal':targets['NOMINAL']=F(5)
    elif fault=='yield':targets['YIELD']=F(1,2)
    elif fault=='resume':targets['RESUME']=F(3)
    elif fault=='stop_guard':rows[1]={**rows[1],'requires':()}
    elif fault=='clear_guard':rows[1]={**rows[1],'after_event':'TRIGGER'}
    else:rows[0]={**rows[0],'delay_s':F(1,20)}
    program['transitions']=tuple(rows);r=replace(r,targets=targets,phases={**r.phases,'program':program})
    fixture=SimpleNamespace(domain=SimpleNamespace(topology={'category':'C'}),environment={})
    with pytest.raises(ValueError,match='NORMATIVE'):
        require('m56.response','_forward_contract')(r,fixture)


def test_public_evidence_does_not_admit_changed_reduced_speed(require):
    from tests.m56.response_cases import response_case
    from m56.model import CommandRecord
    c=response_case('C','B');r=replace(c.response,targets={**c.response.targets,'YIELD':F(1,2)})
    fixture=SimpleNamespace(domain=SimpleNamespace(topology={'category':'C'}),environment={},responses=(r,))
    command=CommandRecord(1,99,100,'CONTROL',F(9,5),F(0),None,None,'YIELD',r.hash)
    evidence=SimpleNamespace(raw=(SimpleNamespace(actors=(SimpleNamespace(commands=(command,)),)),))
    assert require('m56.evidence','_normative_integrity')(evidence,fixture)==(('NORMATIVE_RESPONSE_INVALID',),())


def following_case():
    from tests.m56.response_cases import response_case
    c=response_case('O','B');r=c.response
    profile={'method':'quintic-arc-v1','segments':({'start_arc_m':F(0),'length_m':F(1),'start_offset_m':F(0),'end_offset_m':F(0)},)}
    program={'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':(
        {'cause':'FOLLOW','after_event':'TRIGGER','delay_s':F(0),'requires':()},)}
    r=replace(r,targets={'NOMINAL':F(6),'FOLLOW':F(5,2)},profile=profile,phases={'category':'O','program':program})
    fixture=SimpleNamespace(domain=SimpleNamespace(topology={'category':'O'}),
        environment={'readiness':{'targets_mps':{'EGO':F(6),'NPC':F(5,2)}}})
    return r,fixture


def test_o_follow_uses_declared_nominal_then_two_point_five_without_lane_change(require):
    r,fixture=following_case()
    assert require('m56.response','_forward_contract')(r,fixture) is None


@pytest.mark.parametrize('fault',['target','delay','trigger','lateral','extra_phase'])
def test_self_consistent_o_follow_program_cannot_become_a_pass_or_faster_arm(require,fault):
    r,fixture=following_case();program=dict(r.phases['program']);rows=list(program['transitions'])
    if fault=='target':r=replace(r,targets={**r.targets,'FOLLOW':F(4)})
    elif fault=='delay':rows[0]={**rows[0],'delay_s':F(1,20)}
    elif fault=='trigger':rows[0]={**rows[0],'after_event':'RETURN_CLEAR_CONFIRMED'}
    elif fault=='lateral':r=replace(r,profile={'method':'quintic-arc-v1','segments':(
        {'start_arc_m':F(0),'length_m':F(18),'start_offset_m':F(0),'end_offset_m':F(3)},)})
    else:
        r=replace(r,targets={**r.targets,'PASS':F(6)})
        rows.append({'cause':'PASS','after_event':'RETURN_MARKER','delay_s':F(0),'requires':()})
    program['transitions']=tuple(rows);r=replace(r,phases={**r.phases,'program':program})
    with pytest.raises(ValueError,match='NORMATIVE'):
        require('m56.response','_forward_contract')(r,fixture)


def cut_in_case():
    r,fixture=following_case()
    rows=({'cause':'CHANGE','after_event':'SOURCE_CLEAR_CONFIRMED','delay_s':F(0),'requires':('TRIGGER','LANE_CHANGE_PATH_CLEAR')},
          {'cause':'TARGET','after_event':'TARGET_LANE_CONFIRMED','delay_s':F(0),'requires':('REFERENCE_MARKER:TARGET',)})
    r=replace(r,targets={'NOMINAL':F(6),'CHANGE':F(6),'TARGET':F(6)},phases={'category':'I',
        'program':{'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':rows}})
    fixture=SimpleNamespace(domain=SimpleNamespace(topology={'category':'I'}),
        environment={'readiness':{'targets_mps':{'EGO':F(6),'NPC':F(5)}}})
    return r,fixture


def test_i_b_keeps_nominal_and_requires_actual_clear_path_trigger(require):
    r,fixture=cut_in_case()
    assert require('m56.response','_forward_contract')(r,fixture) is None


@pytest.mark.parametrize('fault',['target','trigger','source_clear','path','delay','arrival'])
def test_self_consistent_i_b_cannot_change_nominal_or_clearance_policy(require,fault):
    r,fixture=cut_in_case();rows=list(r.phases['program']['transitions'])
    if fault=='target':r=replace(r,targets={**r.targets,'CHANGE':F(3)})
    elif fault=='trigger':rows[0]={**rows[0],'requires':('LANE_CHANGE_PATH_CLEAR',)}
    elif fault=='source_clear':rows[0]={**rows[0],'after_event':'TRIGGER'}
    elif fault=='path':rows[0]={**rows[0],'requires':('TRIGGER',)}
    elif fault=='delay':rows[0]={**rows[0],'delay_s':F(1,20)}
    else:rows[1]={**rows[1],'after_event':'SOURCE_CLEAR_CONFIRMED'}
    r=replace(r,phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}})
    with pytest.raises(ValueError,match='NORMATIVE'):
        require('m56.response','_forward_contract')(r,fixture)


def passing_case():
    r,fixture=following_case()
    rows=({'cause':'CHANGE','after_event':'TRIGGER','delay_s':F(0),'requires':('LANE_CHANGE_PATH_CLEAR',)},
          {'cause':'TARGET','after_event':'TARGET_LANE_CONFIRMED','delay_s':F(0),'requires':('REFERENCE_MARKER:TARGET',)},
          {'cause':'RETURN','after_event':'RETURN_MARKER','delay_s':F(0),
           'requires':('RETURN_CLEAR_CONFIRMED','RETURN_PATH_CLEAR')},
          {'cause':'HOME','after_event':'RETURN_LANE_CONFIRMED','delay_s':F(0),'requires':('REFERENCE_MARKER:HOME',)})
    r=replace(r,action_id='A',targets={'NOMINAL':F(6),'CHANGE':F(6),'TARGET':F(6),'RETURN':F(6),'HOME':F(6)},
        phases={'category':'O','program':{'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':rows}})
    # Geometry/lateral reference admission remains an independent contract.
    return r,fixture


def test_o_a_keeps_nominal_and_requires_fixed_marker_actual_clear_return(require):
    r,fixture=passing_case()
    assert require('m56.response','_forward_contract')(r,fixture) is None


@pytest.mark.parametrize('fault',['target','trigger','path','return_anchor','clear','return_path','delay','arrival','marker','extra'])
def test_self_consistent_o_pass_cannot_override_outbound_or_return_policy(require,fault):
    r,fixture=passing_case();rows=list(r.phases['program']['transitions'])
    if fault=='target':r=replace(r,targets={**r.targets,'RETURN':F(5,2)})
    elif fault=='trigger':rows[0]={**rows[0],'after_event':'SOURCE_CLEAR_CONFIRMED'}
    elif fault=='path':rows[0]={**rows[0],'requires':()}
    elif fault=='return_anchor':rows[2]={**rows[2],'after_event':'TARGET_LANE_CONFIRMED'}
    elif fault=='clear':rows[2]={**rows[2],'requires':('RETURN_PATH_CLEAR',)}
    elif fault=='return_path':rows[2]={**rows[2],'requires':('RETURN_CLEAR_CONFIRMED',)}
    elif fault=='delay':rows[2]={**rows[2],'delay_s':F(1,20)}
    elif fault=='arrival':rows[3]={**rows[3],'after_event':'RETURN_CLEAR_CONFIRMED'}
    elif fault=='marker':rows[3]={**rows[3],'requires':()}
    else:
        r=replace(r,targets={**r.targets,'FOLLOW':F(5,2)})
        rows.append({'cause':'FOLLOW','after_event':'X_END','delay_s':F(0),'requires':()})
    r=replace(r,phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}})
    with pytest.raises(ValueError,match='NORMATIVE'):
        require('m56.response','_forward_contract')(r,fixture)


def test_public_o_a_policy_rejects_return_on_lane_arrival_instead_of_fixed_marker(require):
    from m56.model import CommandRecord
    r,fixture=passing_case();rows=list(r.phases['program']['transitions'])
    rows[2]={**rows[2],'after_event':'TARGET_LANE_CONFIRMED'}
    r=replace(r,phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}})
    fixture=SimpleNamespace(**vars(fixture),responses=(r,))
    command=CommandRecord(1,99,100,'CONTROL',F(108,5),F(0),None,None,'RETURN',r.hash)
    evidence=SimpleNamespace(raw=(SimpleNamespace(actors=(SimpleNamespace(commands=(command,)),)),))
    assert require('m56.evidence','_normative_integrity')(evidence,fixture)==(('NORMATIVE_RESPONSE_INVALID',),())


def stop_for_cut_in_case():
    r,fixture=cut_in_case()
    rows=({'cause':'STOP','after_event':'TRIGGER','delay_s':F(0),'requires':()},
          {'cause':'RESUME','after_event':'SOURCE_CLEAR_CONFIRMED','delay_s':F(0),
           'requires':('STOP_AFTER_TRIGGER','NPC_TARGET_LANE_CONFIRMED')})
    r=replace(r,action_id='A',targets={'NOMINAL':F(6),'STOP':F(0),'RESUME':F(6)},
        phases={'category':'I','program':{'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':rows}})
    return r,fixture


def test_i_a_stops_in_initial_lane_until_actual_stop_and_npc_merge(require):
    r,fixture=stop_for_cut_in_case()
    assert require('m56.response','_forward_contract')(r,fixture) is None


@pytest.mark.parametrize('fault',['target','resume','stop','merge','clear','delay','lateral'])
def test_self_consistent_i_a_cannot_resume_without_stop_and_merged_npc(require,fault):
    r,fixture=stop_for_cut_in_case();rows=list(r.phases['program']['transitions'])
    if fault=='target':r=replace(r,targets={**r.targets,'STOP':F(1)})
    elif fault=='resume':r=replace(r,targets={**r.targets,'RESUME':F(4)})
    elif fault=='stop':rows[1]={**rows[1],'requires':('NPC_TARGET_LANE_CONFIRMED',)}
    elif fault=='merge':rows[1]={**rows[1],'requires':('STOP_AFTER_TRIGGER',)}
    elif fault=='clear':rows[1]={**rows[1],'after_event':'TRIGGER'}
    elif fault=='delay':rows[0]={**rows[0],'delay_s':F(1,20)}
    else:r=replace(r,profile={'method':'quintic-arc-v1','segments':(
        {'start_arc_m':F(0),'length_m':F(18),'start_offset_m':F(0),'end_offset_m':F(3)},)})
    r=replace(r,phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}})
    with pytest.raises(ValueError,match='NORMATIVE'):
        require('m56.response','_forward_contract')(r,fixture)


def test_public_i_a_policy_rejects_a_self_consistent_creep_instead_of_stop(require):
    from m56.model import CommandRecord
    r,fixture=stop_for_cut_in_case();r=replace(r,targets={**r.targets,'STOP':F(1)})
    fixture=SimpleNamespace(**vars(fixture),responses=(r,))
    command=CommandRecord(1,99,100,'CONTROL',F(18,5),F(0),None,None,'STOP',r.hash)
    evidence=SimpleNamespace(raw=(SimpleNamespace(actors=(SimpleNamespace(commands=(command,)),)),))
    assert require('m56.evidence','_normative_integrity')(evidence,fixture)==(('NORMATIVE_RESPONSE_INVALID',),())


def test_public_evidence_rejects_npc_common_release_policy_even_if_control_only(require,tmp_path):
    from tests.m56.reverse_cases import reverse_case
    from m56.model import CommandRecord
    from m56.catalog import _digest
    c=reverse_case(tmp_path/'sources',role='NPC')
    r=c.response;script={**r.phases['f_script'],'release_s':F(4)}
    r=replace(r,phases={**r.phases,'f_script':script})
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    fixture=replace(c.fixture,responses=(r,))
    command=CommandRecord(2,149,150,'CONTROL',F(0),F(0),None,None,'NPC_PREPARATION',r.hash)
    evidence=SimpleNamespace(raw=(SimpleNamespace(actors=(SimpleNamespace(commands=(command,)),)),))
    assert require('m56.evidence','_normative_integrity')(evidence,fixture)==(('NORMATIVE_RESPONSE_INVALID',),())


def test_public_evidence_rejects_o_follow_changed_target(require):
    from m56.model import CommandRecord
    r,fixture=following_case();r=replace(r,targets={**r.targets,'FOLLOW':F(4)})
    fixture=SimpleNamespace(**vars(fixture),responses=(r,))
    command=CommandRecord(1,99,100,'CONTROL',F(72,5),F(0),None,None,'FOLLOW',r.hash)
    evidence=SimpleNamespace(raw=(SimpleNamespace(actors=(SimpleNamespace(commands=(command,)),)),))
    assert require('m56.evidence','_normative_integrity')(evidence,fixture)==(('NORMATIVE_RESPONSE_INVALID',),())
