"""Literal F02 proposal policy: observed rear closing, then pace separation."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


def f02_response(action='B',role='EGO',settle=False):
    from tests.m56.response_cases import response_case
    from m56.catalog import _digest
    r=response_case('F',action,role=role).response
    nominal=F(4) if role=='EGO' else F(5)
    initial='NOMINAL';targets={'NOMINAL':nominal};rows=[]
    if role=='EGO':
        targets['ACTION']=F(4) if action=='A' else F(11,2)
        rows.append({'cause':'ACTION','after_event':'TRIGGER','delay_s':F(0),'requires':()})
    if settle:
        initial='SETTLE';targets['SETTLE']=F(0)
        rows.insert(0,{'cause':'NOMINAL','after_event':'CAPTURE_START','delay_s':F(21,20),'requires':()})
    phases={'category':'F','program':{'method':'ordered-event-program-v1','initial':initial,'transitions':tuple(rows)}}
    if role=='NPC':phases['f_script']={'mechanism':'F02','policy_hash':'2'*64}
    r=replace(r,action_id=action if role=='EGO' else 'NPC_COMMON',targets=targets,phases=phases)
    if role=='NPC':r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    return r,SimpleNamespace(domain=SimpleNamespace(topology={'category':'F','mechanism':'F02'}),policy_hash='2'*64,environment={})


@pytest.mark.parametrize('action,role,settle',[('A','EGO',False),('B','EGO',False),('B','EGO',True),
                                             ('NPC_COMMON','NPC',False),('NPC_COMMON','NPC',True)])
def test_f02_approved_constant_npc_and_observed_trigger_ego_policy(action,role,settle):
    from m56.response import _forward_contract
    r,fixture=f02_response(action,role,settle)
    assert _forward_contract(r,fixture) is None


@pytest.mark.parametrize('fault',['nominal','equal_pace','delay','anchor','extra_guard','extra_phase','lateral','switch'])
def test_self_consistent_f02_ego_cannot_override_speed_event_or_lane_policy(fault):
    from m56.response import _forward_contract
    r,fixture=f02_response();targets=dict(r.targets);program=dict(r.phases['program']);rows=list(program['transitions'])
    if fault=='nominal':targets['NOMINAL']=F(5)
    elif fault=='equal_pace':targets['ACTION']=F(5)
    elif fault=='delay':rows[0]={**rows[0],'delay_s':F(1,20)}
    elif fault=='anchor':rows[0]={**rows[0],'after_event':'CLEAR_N_CONFIRMED'}
    elif fault=='extra_guard':rows[0]={**rows[0],'requires':('STOP_AFTER_TRIGGER',)}
    elif fault=='extra_phase':
        targets['RESUME']=F(4);rows.append({'cause':'RESUME','after_event':'X_END','delay_s':F(0),'requires':()})
    elif fault=='lateral':
        r=replace(r,profile={'method':'quintic-arc-v1','segments':({'start_arc_m':F(0),'length_m':F(18),
            'start_offset_m':F(0),'end_offset_m':F(1,4)},)})
    else:r=replace(r,phases={**r.phases,'reference_switches':({'unapproved':True},)})
    r=replace(r,targets=targets,phases={**r.phases,'program':{**program,'transitions':tuple(rows)}})
    with pytest.raises(ValueError,match='NORMATIVE'):_forward_contract(r,fixture)


@pytest.mark.parametrize('fault',['target','ego_dependent','missing_script','wrong_policy','hash_alias','wrong_role'])
def test_common_f02_npc_cannot_use_a_self_consistent_alternate_script(fault):
    from m56.response import _forward_contract
    from m56.catalog import _digest
    r,fixture=f02_response('NPC_COMMON','NPC');phases=dict(r.phases)
    if fault=='target':r=replace(r,targets={'NOMINAL':F(4)})
    elif fault=='ego_dependent':
        phases['program']={**phases['program'],'transitions':({'cause':'FASTER','after_event':'EGO_TARGET_LANE_CONFIRMED',
            'delay_s':F(0),'requires':()},)};r=replace(r,targets={**r.targets,'FASTER':F(5)})
    elif fault=='missing_script':phases.pop('f_script')
    elif fault=='wrong_policy':phases['f_script']={'mechanism':'F02','policy_hash':'3'*64}
    elif fault=='wrong_role':r=replace(r,action_id='B')
    r=replace(r,phases=phases)
    if fault!='hash_alias':r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    else:r=replace(r,hash='a'*64)
    with pytest.raises(ValueError):_forward_contract(r,fixture)


def test_public_normative_axis_does_not_admit_f02_equal_pace_b():
    from m56.evidence import _normative_integrity
    from m56.model import CommandRecord
    r,fixture=f02_response();r=replace(r,targets={**r.targets,'ACTION':F(5)})
    fixture.responses=(r,)
    command=CommandRecord(1,99,100,'CONTROL',F(18),F(0),None,None,'ACTION',r.hash)
    evidence=SimpleNamespace(raw=(SimpleNamespace(actors=(SimpleNamespace(commands=(command,)),)),))
    assert _normative_integrity(evidence,fixture)==(('NORMATIVE_RESPONSE_INVALID',),())


@pytest.mark.parametrize('action,trigger,want',[('A',False,F(72,5)),('A',True,F(72,5)),
                                             ('B',False,F(72,5)),('B',True,F(99,5))])
def test_f02_actual_pure_producer_uses_observed_trigger_and_positive_kmh(action,trigger,want):
    from tests.m56.response_cases import response_case
    from m56.response import step_response
    r,_=f02_response(action)
    c=response_case('F',action,events=('TRIGGER',) if trigger else (),speed=4.)
    out=step_response(c.frame,c.state,r)
    assert out.command.kind=='CONTROL' and out.command.target_kmh==want and out.command.offset==0
    assert out.state.phase==('ACTION' if trigger else 'NOMINAL')


@pytest.mark.parametrize('status',['CLEAR','RED','UNKNOWN','YIELD'])
def test_f02_fixed_common_script_still_obeys_actual_npc_priority(status):
    from tests.m56.response_cases import response_case
    from m56.response import step_response
    r,_=f02_response('NPC_COMMON','NPC');c=response_case('F',role='NPC',events=(),speed=5.)
    frame=replace(c.frame,integrity={'npc_controls':{'boot':c.frame.boot,'world':c.frame.world,'frame':c.frame.frame,
        'actor_id':1,'status':status,'witness_refs':(c.ref,)}})
    out=step_response(frame,c.state,r)
    assert out.command.kind=='CONTROL' and out.command.offset==0
    if status=='CLEAR':
        assert out.command.target_kmh==18 and out.command.control is None
    else:
        assert out.command.cause=='NPC_TRAFFIC_HOLD' and out.command.target_kmh==0
        assert out.command.control.throttle==0 and out.command.control.brake==.3
