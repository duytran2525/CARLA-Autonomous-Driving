"""Stock constructor doubles only: production adapter/config/intent code is real."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
import hashlib

import pytest
from tests.m56.test_response import switched_response
from tests.m56.test_lateral_contract import lateral_case


@pytest.fixture
def stock_case(tmp_path,monkeypatch,require):
    from tests.m56.response_cases import response_case
    from m56.model import SourceRef,ReviewRecord,PolicyBundle,ControlPacket
    from m56.catalog import _digest
    c=response_case(events=());calls=[]
    class FakeStock:
        def set_global_plan(self,plan,stop_waypoint_creation,clean_queue):calls.append(('plan',plan,stop_waypoint_creation,clean_queue))
        def follow_speed_limits(self,value):calls.append(('limits',value))
        def set_target_speed(self,value):calls.append(('speed',value))
        def set_speed(self,value):calls.append(('npc_speed',value))
        def set_offset(self,value):calls.append(('offset',value))
        def run_step(self):
            calls.append(('run',));return SimpleNamespace(throttle=.2,steer=.1,brake=0.,hand_brake=False,reverse=False,manual_gear_shift=False,gear=1)
    source=tmp_path/'stock-source.txt';source.write_bytes(b'synthetic stock source boundary, NOT native source')
    ref=SourceRef(str(source),hashlib.sha256(source.read_bytes()).hexdigest(),source.stat().st_size,'0.9.16','literal','SYNTHETIC_TEST')
    binding={'response_hash':c.response.hash,'response_record_hash':_digest(c.response),'route_hash':_digest(c.response.route),'actor_id':1,'source_refs':(ref,),
             'plan':('literal-wp-start','literal-wp-end'),'client_version':'0.9.16','server_version':'0.9.16'}
    review=ReviewRecord(_digest(binding),'STOCK_FORWARD_BINDING',(ref,),'SYNTHETIC_AUTHOR','2026-10-10','APPROVED',
                        ('software boundary only, no native qualification',),ref)
    policy=PolicyBundle('1','d'*64,{}, {'stock_binding':{**binding,'review':review}}, {},(ref,))
    fake=FakeStock();captured=[]
    def factory(actor,config):captured.append((actor,config));return fake
    create=require('m56.response','create_stock_driver')
    monkeypatch.setattr('m56.response._stock_factory',factory)
    def policy_for(response,phase_plans,fixture=None):
        new={**binding,'response_hash':response.hash,'response_record_hash':_digest(response),
             'route_hash':_digest(response.route),'phase_plans':phase_plans}
        sources=(ref,)
        if fixture is not None:
            from m56.evidence import _payload
            path=tmp_path/'stock-fixture.json';data=_payload(fixture);path.write_bytes(data)
            fixture_ref=SourceRef(str(path),hashlib.sha256(data).hexdigest(),len(data),'1','literal','SYNTHETIC_TEST')
            new['fixture_ref']=fixture_ref;sources=(*sources,fixture_ref)
        r=replace(review,object_hash=_digest(new),refs=sources)
        return replace(policy,event_specs={'stock_binding':{**new,'review':r}},receipt_refs=sources)
    return SimpleNamespace(c=c,policy=policy,calls=calls,captured=captured,actor=SimpleNamespace(id=1),fake=fake,create=create,source=source,policy_for=policy_for)


def test_stock_forward_flags_and_plan_exact(stock_case):
    s=stock_case;driver=s.create(s.actor,s.c.response,s.policy)
    config=s.captured[0][1]
    assert config['backend']=='BasicAgent'
    opt=config['opt_dict']
    assert {k:opt[k] for k in ('ignore_traffic_lights','ignore_stop_signs','ignore_vehicles')}==dict.fromkeys(('ignore_traffic_lights','ignore_stop_signs','ignore_vehicles'),True)
    assert opt['lateral_control_dict']=={'K_P':1.95,'K_I':.05,'K_D':.2,'dt':.05}
    assert opt['longitudinal_control_dict']=={'K_P':1.,'K_I':.05,'K_D':0.,'dt':.05}
    assert (opt['max_throttle'],opt['max_brake'],opt['max_steering'],opt['dt'])==(.75,.3,.8,.05)
    assert s.calls==[('plan',('literal-wp-start','literal-wp-end'),True,True),('limits',False)]
    assert driver.hash and driver.config['response_hash']==s.c.response.hash


def test_apply_intent_preserves_correlation_and_validates_stock_control(stock_case,require):
    s=stock_case;driver=s.create(s.actor,s.c.response,s.policy)
    step=require('m56.response','step_response');apply=require('m56.response','apply_intent')
    intent=step(s.c.frame,s.c.state,s.c.response).command
    out=apply(driver,intent)
    assert out.frame==100 and out.next_frame==101 and out.actor==1
    assert out.target_kmh==F(72,5) and out.offset==0 and out.response_hash==intent.response_hash
    assert (out.control.throttle,out.control.steer,out.control.brake,out.control.reverse,out.control.manual_gear_shift)==(.2,.1,0.,False,False)
    assert s.calls[-3:]==[('speed',14.4),('offset',0.),('run',)]
    with pytest.raises(ValueError,match='COMMAND_ORDER'):
        apply(driver,intent)


@pytest.mark.parametrize('fault',['source','actor','review','empty_plan'])
def test_stock_construction_rejects_unbound_inputs_before_factory(stock_case,fault):
    s=stock_case;policy=s.policy;actor=s.actor
    if fault=='source':s.source.write_bytes(b'changed')
    elif fault=='actor':actor=SimpleNamespace(id=2)
    else:
        binding=dict(policy.event_specs['stock_binding'])
        if fault=='review':binding['review']=replace(binding['review'],verdict='REJECTED')
        else:binding['plan']=()
        policy=replace(policy,event_specs={'stock_binding':binding})
    with pytest.raises(ValueError):s.create(actor,s.c.response,policy)
    assert s.captured==[] and s.calls==[]


@pytest.mark.parametrize('status,kmh',[('CLEAR',F(72,5)),('RED',F(0)),('UNKNOWN',F(0))])
def test_npc_local_planner_obeys_observed_control_gate_without_ego_ignore_flags(stock_case,require,status,kmh):
    from tests.m56.response_cases import response_case
    s=stock_case;c=response_case(role='NPC',action='NPC_COMMON',events=())
    policy=s.policy_for(c.response,{})
    driver=s.create(s.actor,c.response,policy)
    assert s.captured[0][1]['backend']=='LocalPlanner'
    assert not any(k.startswith('ignore_') for k in s.captured[0][1]['opt_dict'])
    traffic={'boot':'boot','world':'world','frame':100,'actor_id':1,'status':status,'witness_refs':(c.ref,)}
    intent=require('m56.response','step_response')(replace(c.frame,integrity={'npc_controls':traffic}),c.state,c.response).command
    result=require('m56.response','apply_intent')(driver,intent)
    assert result.target_kmh==kmh
    assert ('npc_speed',float(kmh)) in s.calls
    if status!='CLEAR':
        assert result.control.throttle==0 and result.control.brake==.3
        assert ('run',) not in s.calls
    else:
        assert result.control.throttle==.2
        assert ('run',) in s.calls


def test_stock_target_plan_switch_is_once_and_offset_resets(stock_case,lateral_case,require):
    from tests.m56.response_cases import response_case
    from m56.model import CompiledFixture,Domain,Section,FrozenMetricPair
    s=stock_case;r=lateral_case;c=response_case('I','B',events=('TRIGGER','SOURCE_CLEAR_CONFIRMED','LANE_CHANGE_PATH_CLEAR',
        'TARGET_LANE_CONFIRMED','REFERENCE_MARKER:TARGET'),speed=6.)
    section=Section(((0.,-1.,-1.),(0.,1.,1.)),(1.,0.,0.),F(0),{})
    domain=Domain(section,section,section,section,(),r.fixture.domain.topology,(),'d'*64)
    fixture=CompiledFixture('1'*64,'2'*64,(),r.fixture.environment,{'EGO':r.response.route.transforms[0],'NPC':r.response.route.transforms[0]},
        {'EGO':r.response.route,'NPC':r.response.route},domain,None,{},(r.response,),
        FrozenMetricPair(('v_mean_E','e_lat_peak'),('m/s','m'),('mean_speed','map_lateral_peak'),(('TRIGGER','X_END'),)*2,'map:test','e'*64,'APPROVED_PROPOSAL_NOT_READY'),(),r.response.route.continuity[0])
    plans={'TARGET':('target-wp-start','target-wp-end')}
    policy=s.policy_for(r.response,plans,fixture)
    driver=s.create(s.actor,r.response,policy)
    frame=replace(c.frame,actors=(replace(c.frame.actors[0],pose=replace(c.frame.actors[0].pose,x=30.,y=3.)),))
    intent=require('m56.response','step_response')(frame,replace(c.state,phase='CHANGE'),r.response).command
    apply=require('m56.response','apply_intent')
    out=apply(driver,intent)
    assert out.offset==0
    assert ('plan',plans['TARGET'],True,True) in s.calls
    assert s.calls.index(('plan',plans['TARGET'],True,True))<s.calls.index(('offset',0.))
    apply(driver,replace(intent,frame=101,next_frame=102))
    assert s.calls.count(('plan',plans['TARGET'],True,True))==1


def test_nonzero_lateral_stock_binding_requires_reviewed_fixture_before_constructor(stock_case,switched_response):
    s=stock_case;r=switched_response.response
    with pytest.raises(ValueError,match='STOCK_LATERAL_FIXTURE_MISSING'):
        s.create(s.actor,r,s.policy_for(r,{'CHANGE':('target-a','target-b')}))
    assert s.captured==[] and s.calls==[]


def test_default_stock_factory_remains_native_blocked_without_import():
    import sys
    from m56.response import _stock_factory
    with pytest.raises(RuntimeError,match='BLOCKED_NATIVE_ADMISSION'):
        _stock_factory(SimpleNamespace(id=1),{})
    assert 'carla' not in sys.modules


def test_response_content_change_with_same_hash_cannot_bypass_review(stock_case):
    s=stock_case;changed=replace(s.c.response,targets={**s.c.response.targets,'NOMINAL':F(99)})
    with pytest.raises(ValueError):s.create(s.actor,changed,s.policy)
    assert s.captured==[]


def test_early_empty_queue_brake_one_not_clamped_into_valid_control(stock_case,require):
    s=stock_case;driver=s.create(s.actor,s.c.response,s.policy)
    s.fake.run_step=lambda:SimpleNamespace(throttle=0.,steer=0.,brake=1.,hand_brake=False,reverse=False,manual_gear_shift=False,gear=1)
    intent=require('m56.response','step_response')(s.c.frame,s.c.state,s.c.response).command
    with pytest.raises(ValueError,match='STOCK_CONTROL_INVALID'):
        require('m56.response','apply_intent')(driver,intent)
    # A failed effect consumes the frame; no automatic same-frame retry.
    with pytest.raises(ValueError,match='COMMAND_ORDER'):
        require('m56.response','apply_intent')(driver,intent)


@pytest.mark.parametrize('field,value,ok', [
    ('steer', -0.800000011920929, True), ('steer', 0.800000011920929, True), ('throttle', 0.75, True),
    ('brake', 0.30000001192092896, True), ('steer', -0.8000001, False), ('brake', 0.3000001, False),
    ('throttle', 0.7500001, False)])
def test_stock_limits_accept_carla_float32_images_only(stock_case, require, field, value, ok):
    # CARLA's VehicleControl stores float32: the agent's 0.8 steer clamp reads back -0.800000011920929 (native 22/10).
    s = stock_case; driver = s.create(s.actor, s.c.response, s.policy)
    control = dict(throttle=0., steer=0., brake=0., hand_brake=False, reverse=False, manual_gear_shift=False, gear=1)
    s.fake.run_step = lambda: SimpleNamespace(**{**control, field: value})
    intent = require('m56.response', 'step_response')(s.c.frame, s.c.state, s.c.response).command
    if ok:
        assert getattr(require('m56.response', 'apply_intent')(driver, intent).control, field) == value
    else:
        with pytest.raises(ValueError, match='STOCK_CONTROL_INVALID'):
            require('m56.response', 'apply_intent')(driver, intent)
