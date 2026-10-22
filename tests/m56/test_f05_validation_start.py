"""F05 validation t_start/readiness admission is separate from an actual queue hold.

The 1s physical queue hold may accrue in initialization. No cue is active until
readiness starts validation. Arming never manufactures STOP, resets the physical
hold, changes the fixed3s release, or permits a missing/forged start receipt.
"""
from dataclasses import replace
from fractions import Fraction as F

import pytest


def gated_queue(root,defect=None,last=214):
    from tests.m56.test_f05_phase_events import f05_observations
    from tests.m56.source_cases import Sources
    from m56.catalog import _digest
    from m56.model import ControlPacket
    root.mkdir();c=f05_observations(root/'physical',last=last);s=Sources(root/'gated');s.refs.extend(c.s.refs)
    poses={'EGO':replace(c.fixture.poses['EGO'],x=-6.5),'NPC':replace(c.fixture.poses['NPC'],x=0.,y=0.)}
    fixture=replace(c.fixture,poses=poses,actors=tuple(replace(a,pose=poses[a.role]) for a in c.fixture.actors),
        environment={'readiness':{'targets_mps':{'EGO':F(0),'NPC':F(0)},
        'markers_m':{'EGO':F(7,2),'NPC':F(10)}},'validation_start':'recorded-readiness-start-v1'})
    hold=ControlPacket(0.,0.,.3,False,False,False,1);forward=ControlPacket(.2,0.,0.,False,False,False,1)
    frames=[]
    for raw in c.frames:
        number=raw.frame;e,n=raw.actors;moving=number>=192;position=F(max(0,number-191),10)
        control=forward if moving else hold
        n=replace(n,pose=replace(n.pose,x=float(position)),arc=F(10)+position,velocity=(2.,0.,0.) if moving else (0.,0.,0.),
            readback=control,commands=(replace(n.commands[0],cause='NPC_QUEUE_FORWARD' if moving else 'NPC_QUEUE_HOLD',
                target_kmh=F(36,5) if moving else F(0),control=control),))
        if defect=='not_ready' and number==128:e=replace(e,velocity=(.5,0.,0.))
        frame=replace(raw,actors=(e,n),integrity={})
        ref=s.source('observed-'+str(number),{'boot':frame.boot,'world':frame.world,'frame':number,'simtime':frame.simtime,'actors':frame.actors},number,frame.simtime)
        fields={'frame_refs':(ref,)}
        if frames:
            limits={'fixture_hash':_digest(fixture),'previous_actors':_digest(frames[-1].actors),'actors':_digest(frame.actors),
                    'previous_frame':number-1,'frame':number}
            fields['continuous_geometry']=s.capability('CONTINUOUS_GEOMETRY','bounded-interframe-body-v1',limits,(ref,),F(0))
        if number==131 and defect!='missing_start':
            limits={'fixture_hash':_digest(fixture),'frame':number,'actors_hash':_digest(frame.actors)}
            proof=s.capability('VALIDATION_START','recorded-readiness-start-v1',limits,(ref,),F(0))
            if defect=='alias':proof=replace(proof,raw_refs=(replace(ref,sha256='f'*64),))
            if defect=='future_start':proof=replace(proof,limits={**limits,'frame':132})
            fields['validation_start']=proof
        frames.append(replace(frame,integrity=fields))
    c.s=s;c.frames=tuple(frames);c.fixture=fixture
    return c


def test_f05_actual_queue_stop_in_warmup_cannot_trigger_or_retime_before_validation_readiness(tmp_path):
    from m56.metrics import detect_events
    c=gated_queue(tmp_path/'sources')
    assert not any(e.name=='TRIGGER' for e in detect_events(c.frames[:31],c.fixture))
    events=detect_events(c.frames,c.fixture)
    assert next(e.frame for e in events if e.name=='TRIGGER')==131
    # Existing actual 1s queue hold is retained, not restarted on readiness.
    assert {r.frame for r in next(e for e in events if e.name=='TRIGGER').witness_refs}==set(range(100,132))
    assert next(e.frame for e in events if e.name=='N_MOVE')==197
    assert next(e.frame for e in events if e.name=='NPC_ADVANCE_2M_CONFIRMED')==211


@pytest.mark.parametrize('defect',['missing_start','alias','future_start','not_ready'])
def test_f05_missing_forged_or_physically_unready_start_cannot_fall_back_to_early_queue_cue(tmp_path,defect):
    from m56.metrics import detect_events
    c=gated_queue(tmp_path/'sources',defect)
    events=detect_events(c.frames,c.fixture)
    assert not any(e.name in ('TRIGGER','N_MOVE','NPC_ADVANCE_2M_CONFIRMED') for e in events)


@pytest.mark.parametrize('ready,expected',[(131,((),())),(150,(('INITIALIZATION_INVALID',),())),
    ('unadmitted_start',(('INITIALIZATION_INVALID',),()))])
def test_f05_source_validation_clock_must_equal_independently_reviewed_ready_not_another_valid_stop_hold(tmp_path,ready,expected):
    from tests.m56.source_cases import Sources
    from m56.evidence import _initialization_integrity
    c=gated_queue(tmp_path/'physical')
    frames=tuple(replace(f,integrity={**f.integrity,'metric_context':{
        'reference':c.fixture.pair.reference,'pair_hash':c.fixture.pair.hash,'directed_route':c.fixture.routes['EGO'],
        'uncertainty':{name:F(0) for name in c.fixture.pair.names}}}) for f in c.frames)
    boundary=replace(frames[0],frame=99,simtime=-F(1,20),integrity={},
        actors=tuple(replace(a,commands=()) for a in frames[0].actors))
    s=Sources(tmp_path/'evidence');s.refs.extend(c.s.refs)
    episode=s.complete(frames,c.fixture,boundary,120,131 if ready=='unadmitted_start' else ready)
    if ready=='unadmitted_start':
        start=next(f for f in episode.raw if 'validation_start' in f.integrity)
        refs=start.integrity['validation_start'].raw_refs
        episode=replace(episode,source=tuple(r for r in episode.source if r not in refs))
        from m56.metrics import _authenticated_events
        assert _authenticated_events(episode,c.fixture) is None
    assert _initialization_integrity(episode,c.fixture)==expected
