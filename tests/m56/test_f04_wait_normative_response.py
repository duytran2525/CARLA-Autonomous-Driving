"""F04 A waits on observed closed-clear and its own STOP, never door RPC success."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import pytest


def f04_ego_a():
    from tests.m56.response_cases import response_case
    from m56.catalog import _digest
    r=response_case('F','A',events=(),speed=2.).response
    r=replace(r,targets={'NOMINAL':F(2),'WAIT':F(0),'FORWARD':F(2)},phases={'category':'F',
        'program':{'method':'ordered-event-program-v1','initial':'NOMINAL','transitions':(
            {'cause':'WAIT','after_event':'TRIGGER','delay_s':F(0),'requires':()},
            {'cause':'FORWARD','after_event':'DOOR_CLOSED_CLEAR_CONFIRMED','delay_s':F(0),
             'requires':('STOP_AFTER_TRIGGER',)},)}})
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    fixture=SimpleNamespace(domain=SimpleNamespace(topology={'category':'F','mechanism':'F04'}),
        environment={},policy_hash='2'*64)
    return r,fixture


def test_f04_a_nominal_two_stop_and_observed_closed_clear_release_policy():
    from m56.response import _forward_contract
    r,fixture=f04_ego_a()
    assert _forward_contract(r,fixture) is None


@pytest.mark.parametrize('fault',['nominal','stop','forward','trigger_timer','stop_delay','stop_guard',
    'rpc_release','release_timer','no_own_stop','release_delay','extra','lateral'])
def test_f04_a_self_consistent_targets_cannot_replace_actual_stop_closed_clear(fault):
    from m56.catalog import _digest
    from m56.response import _forward_contract
    r,fixture=f04_ego_a();targets=dict(r.targets);rows=list(r.phases['program']['transitions'])
    if fault=='nominal':targets['NOMINAL']=F(3)
    elif fault=='stop':targets['WAIT']=F(1)
    elif fault=='forward':targets['FORWARD']=F(3)
    elif fault=='trigger_timer':rows[0]={**rows[0],'after_event':'CAPTURE_START'}
    elif fault=='stop_delay':rows[0]={**rows[0],'delay_s':F(1,20)}
    elif fault=='stop_guard':rows[0]={**rows[0],'requires':('DOOR_CLOSED_CLEAR_CONFIRMED',)}
    elif fault=='rpc_release':rows[1]={**rows[1],'after_event':'DOOR_CLOSE_COMMAND'}
    elif fault=='release_timer':rows[1]={**rows[1],'after_event':'TRIGGER','delay_s':F(3)}
    elif fault=='no_own_stop':rows[1]={**rows[1],'requires':()}
    elif fault=='release_delay':rows[1]={**rows[1],'delay_s':F(1,20)}
    elif fault=='extra':
        targets['FASTER']=F(3);rows.append({'cause':'FASTER','after_event':'F04_END','delay_s':F(0),'requires':()})
    else:r=replace(r,profile={'method':'quintic-arc-v1','segments':(
        {'start_arc_m':F(0),'length_m':F(6),'start_offset_m':F(0),'end_offset_m':F(3,4)},)})
    r=replace(r,targets=targets,phases={**r.phases,'program':{**r.phases['program'],'transitions':tuple(rows)}})
    r=replace(r,hash=_digest({k:getattr(r,k) for k in ('actor_role','action_id','route','targets','profile','phases')}))
    with pytest.raises(ValueError):_forward_contract(r,fixture)
