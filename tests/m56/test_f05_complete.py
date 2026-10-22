"""F05 producer/source/readiness/public queue acceptance, software ONLY.

One real compare_ab call itself evaluates BOTH actions through evaluate_episode
and check_integrity. Assert those actual returned public proofs as well as the
numeric result, instead of paying for repeated standalone/public/AB evaluations
of the same immutable inputs. No cached verdict is supplied to production.
"""
from fractions import Fraction as F


def test_f05_source_decoded_pair_requires_two_full_public_actions_and_keeps_numeric_failure(tmp_path):
    from dataclasses import replace
    from tests.m56.f05_cases import complete_f05
    from m56.catalog import _digest
    from m56.metrics import _source_metrics,_ab_review_subject,compare_ab
    print('F05 A source composition start',flush=True)
    a=complete_f05(tmp_path/'a-sources','A')
    print('F05 B source composition start, shared pretrace frozen fixture',flush=True)
    b=complete_f05(tmp_path/'b-sources','B',a.frozen)
    print('F05 both source compositions sealed; fresh public AB evaluation starts',flush=True)
    assert _digest(a.fixture)==_digest(b.fixture)
    left,right=_source_metrics(a.episode,a.fixture),_source_metrics(b.episode,b.fixture)
    refs=tuple(dict.fromkeys(r for e in (a.episode,b.episode) for r in (e.fixture,e.manifest,*e.journal,*e.source)))
    review=a.sources.review(_ab_review_subject(a.episode,b.episode,a.fixture.pair,left,right),'REALIZED_AB_COMPARABILITY_D09',refs)
    review=replace(review,reasons=tuple(k+': synthetic author source composition, no scientific qualification'
        for k in ('fulltrace','near_zero','nearstanding','identity','mechanism','comparability')))
    pair=compare_ab(a.episode,b.episode,a.fixture.pair,review)
    assert len(pair.action_proofs)==2,pair
    for action,c,out in zip(('A','B'),(a,b),pair.action_proofs):
        assert (out.spawn,out.physical,out.witness)==('CONFIRMED','COMPLETE','VALID'),out
        events={e.name:e for e in out.events if e.name!='QUEUE_CLEAR_CONFIRMED'}
        assert events['TRIGGER'].frame==131
        assert events['N_MOVE'].frame==197
        assert events['NPC_ADVANCE_2M_CONFIRMED'].frame==211
        assert events['F05_END'].frame==(347 if action=='A' else 323)
        assert events['DESTINATION_CONFIRMED'].frame==(389 if action=='A' else 365)
        if action=='B':
            assert events['EGO_CREEP_STOPPING_BOUND'].frame==162
            assert events['EGO_CREEP_STOP_CONFIRMED'].frame==182
            assert next(e.frame for e in out.events if e.name=='QUEUE_CLEAR_CONFIRMED')==197
        assert out.metrics['d_pre_move_m'].value==(0 if action=='A' else 1)
        assert out.metrics['t_queue_exit_s'].value==(F(15,2) if action=='A' else F(63,10))
        npc_commands=tuple(x.commands[0] for f in c.episode.raw for x in f.actors if x.role=='NPC')
        assert min(cmd.frame for cmd in npc_commands if cmd.target_kmh>0)==191
        assert all(cmd.target_kmh==0 for cmd in npc_commands if cmd.frame<191)
        ego_commands=tuple(x.commands[0] for f in c.episode.raw for x in f.actors if x.role=='EGO')
        assert min(cmd.frame for cmd in ego_commands if cmd.target_kmh==F(36,5))==(211 if action=='A' else 197)
        print(action,'public=',out.spawn,out.physical,out.witness,'metrics=',
              {k:(m.value,m.status) for k,m in out.metrics.items()},flush=True)
    assert pair.status=='NUMERIC_FAILED',pair
    assert pair.comparisons==(F(1),F(4,25)),pair.comparisons
    print('F05 SOFTWARE pair=',pair.status,pair.comparisons,'author D09 only; NOT scientific qualification',flush=True)
    # No measured stock stopping/body/contact/ground calibration, selected-scene
    # qualification, independent-person review, native or scientific success.
