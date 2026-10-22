"""Source-bound exception consumer checks, not native dynamics evidence."""
from dataclasses import replace
from fractions import Fraction as F

import pytest


@pytest.mark.parametrize('kind',['REVERSE','REVERSE_HOLD','GEAR_TRANSITION'])
def test_exception_command_with_missing_program_cannot_escape_phase_witness_gate(tmp_path,kind):
    from tests.m56.reverse_cases import reverse_case
    from m56.model import CommandRecord
    from m56.evidence import _phase_integrity
    c=reverse_case(tmp_path/'sources')
    response=replace(c.response,phases={'category':'F','reverse':c.response.phases['reverse']})
    fixture=replace(c.fixture,responses=(response,))
    actor=c.frame.actors[0]
    command=CommandRecord(actor.id,c.frame.frame,c.frame.frame+1,kind,F(0),F(0),actor.readback,None,'HOLD',response.hash)
    receiving=replace(c.frame,frame=c.frame.frame+1,simtime=c.frame.simtime+F(1,20),
                      actors=(replace(actor,commands=(command,)),c.frame.actors[1]))
    episode=c.s.episode((receiving,),fixture,c.frame)
    assert _phase_integrity(episode,fixture)==((),('PHASE_PROGRAM_MISSING',))


def test_unbound_reverse_command_cannot_hide_in_empty_forward_program(tmp_path):
    from tests.m56.reverse_cases import reverse_case
    from m56.model import CommandRecord
    from m56.evidence import _phase_integrity
    c=reverse_case(tmp_path/'sources')
    response=replace(c.response,phases={'category':'F','program':{
        'method':'ordered-event-program-v1','initial':'HOLD','transitions':()}})
    fixture=replace(c.fixture,responses=(response,));actor=c.frame.actors[0]
    command=CommandRecord(actor.id,c.frame.frame,c.frame.frame+1,'REVERSE',F(9,5),F(0),actor.readback,None,'HOLD',response.hash)
    receiving=replace(c.frame,frame=c.frame.frame+1,simtime=c.frame.simtime+F(1,20),
                      actors=(replace(actor,commands=(command,)),c.frame.actors[1]))
    episode=c.s.episode((receiving,),fixture,c.frame)
    assert _phase_integrity(episode,fixture)==((),('REVERSE_COMMAND_PROGRAM_UNPROVEN',))


@pytest.mark.parametrize('tamper',[False,True])
def test_source_bound_npc_release_replays_full_bounded_command_not_just_cause(tmp_path,tamper):
    from tests.m56.reverse_composition_cases import npc_release_case
    from m56.metrics import _authenticated_events
    from m56.evidence import _phase_integrity
    c=npc_release_case(tmp_path/'sources',tamper=tamper)
    events=_authenticated_events(c.episode,c.fixture)
    assert events is not None
    assert [(e.frame,e.time) for e in events if e.name=='TRIGGER']==[(150,F(1,2))]
    out=_phase_integrity(c.episode,c.fixture)
    assert out==((('REVERSE_COMMAND_MISMATCH',),()) if tamper else ((),())),out
    if tamper:
        from m56.evidence import check_integrity
        public=check_integrity(c.episode,c.fixture)
        assert 'REVERSE_COMMAND_MISMATCH' in public.reasons and public.status!='WITNESS_VALID',public


def test_source_npc_terminal_stop_gear_and_forward_are_distinct_from_metric_end(tmp_path):
    from tests.m56.reverse_composition_cases import npc_release_case
    from m56.metrics import _authenticated_events
    from m56.evidence import _phase_integrity
    c=npc_release_case(tmp_path/'sources',terminal=True)
    events=_authenticated_events(c.episode,c.fixture)
    assert events is not None
    assert [(e.frame,e.time) for e in events if e.name=='NPC_REVERSE_TARGET_STOP_CONFIRMED']==[(301,F(161,20))]
    commands=[a.commands[0] for f in c.episode.raw for a in f.actors if a.role=='NPC']
    gear=next(cmd for cmd in commands if cmd.kind=='GEAR_TRANSITION')
    forward=next(cmd for cmd in commands if cmd.cause=='NPC_FORWARD')
    assert (gear.frame,gear.next_frame,gear.control.throttle,gear.control.reverse,gear.control.gear)==(301,302,0,False,1)
    assert (forward.frame,forward.next_frame,forward.kind,forward.target_kmh)==(302,303,'CONTROL',F(36,5))
    assert _phase_integrity(c.episode,c.fixture)==((),())
    assert not any(e.name=='DESTINATION_CONFIRMED' for e in events)
    assert not any(cmd.cause=='COMPLETE' for cmd in commands)
