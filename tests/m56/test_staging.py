"""T17 authorized input staging of the retained 26, missing-20 preservation and freeze-manifest inputs.

Sources are the owned, hash-verified copies of the approved spec (§6.3/§7.4) and handoff reference 06.
Expected literals below are read from those documents, not computed with production code.
"""
from dataclasses import replace
from fractions import Fraction as F
import hashlib
from pathlib import Path

import pytest

from m56.model import ParameterProposal, PolicyBundle, ReviewRecord, SourceRef

INPUTS = Path(__file__).resolve().parents[2]/'outputs/m56_offline_v1/inputs'
SPEC = INPUTS/'2026-10-07-m56-catalog-and-validation-design.md'
REF06 = INPUTS/'handoff_20261006/references/06_scene_proposal_and_validation_design.md'


def ref(path, kind='APPROVED_SOURCE'):
    data = path.read_bytes()
    return SourceRef(str(path), hashlib.sha256(data).hexdigest(), len(data), '1', 'sha256', kind)


@pytest.fixture
def staged_inputs(require):
    imp = require('m56.catalog', 'import_retained')
    sources = (ref(SPEC), ref(REF06))
    assert sources[0].sha256.startswith('8e1e2ba3') and sources[1].sha256.startswith('47f678b7')
    base = imp(SPEC, REF06)
    alt1 = ParameterProposal('F06-ALT1', (F(3),), 'm', 'spec §13 / D39-D42: pair d_reserve_reverse_m+g_front_min_m, '
                             'fixed 3 s release, initial gap 3 m (D41)', (sources[0],), 'APPROVED_PROPOSAL_NOT_READY')
    policies = PolicyBundle('spec-8e1e2ba3', 'f'*64, {'F06-ALT1': alt1}, {}, {}, (sources[0],))
    return base, policies, sources


def test_stage_26_preserves_missing20_and_f06_proposal(staged_inputs, require):
    stage = require('m56.catalog', 'stage_inputs')
    base, policies, sources = staged_inputs
    out = stage(base, (), policies, sources)
    assert len(out.revision.candidates) == 26
    assert out.deficits['missing_slots'] == {'I': 5, 'M': 4, 'O': 5, 'F': 6}
    assert out.policies.approved_parameters['F06-ALT1'].status == 'APPROVED_PROPOSAL_NOT_READY'
    assert out.revision.c0_receipt is None


def test_import_preserves_spec_rows_aliases_and_pending_runtime(staged_inputs):
    base, _, _ = staged_inputs
    by = {c.slot: c for c in base.candidates}
    assert sorted(by) == sorted([f'{c}0{i}' for c in 'CL' for i in range(1, 9)] + [f'M0{i}' for i in range(1, 5)]
                                + ['I01', 'I02', 'I03', 'O01', 'O02', 'O03'])
    assert by['C01'].id == 'M56-P-C01' and by['C01'].town == 'Town04' and by['C01'].site_id == 'P04-J148'
    assert by['C01'].parameters['G'].values == (F(26),) and by['L08'].parameters['LrefN'].values == (F('18.002049'),)
    assert by['L03'].parameters['vN'].values == (F(3) * F(5, 4) ** 2,)  # exact k-expression, k=3
    assert by['O03'].parameters['X'].values == (F(21947, 88),) and by['O03'].parameters['return_start'].values == (F(2091, 44),)
    assert by['I03'].parameters['vE'].values == (F('9.375'),) and by['I03'].site_id == 'A06-R40'
    egos = [a for a in by['L01'].actors if a.role == 'EGO']
    assert egos[0].route_recipe['route'] == '29/-1→61/-1→27/-1' and egos[0].route_recipe['connection'] == 'c2'
    assert by['L01'].environment['aliases']['original_left_id'] == '53/2/-1'
    assert all(a.pose is None and a.pose_recipe['status'] == 'PENDING_RUNTIME_QUERY' and a.destination is None
               for c in base.candidates for a in c.actors)
    assert all(a.blueprint == 'vehicle.audi.a2' for c in base.candidates for a in c.actors)


def test_new_slots_need_selection_authority(staged_inputs, require):
    stage = require('m56.catalog', 'stage_inputs')
    base, policies, sources = staged_inputs
    new = replace(base.candidates[0], id='M56-P-I04', slot='I04', category='I', site_id='A04-R99')
    out = stage(base, (new,), policies, sources)
    assert out.status == 'SCHEMA_ERROR' and any(e.reason == 'SELECTION_AUTHORITY_MISSING' for e in out.errors)


def test_m05_to_m08_no_invented_G(staged_inputs, require):
    stage = require('m56.catalog', 'stage_inputs')
    base, policies, sources = staged_inputs
    out = stage(base, (), policies, sources)
    assert all(s not in out.policies.approved_parameters for s in ('M05', 'M06', 'M07', 'M08'))
    assert not any(c.slot in ('M05', 'M06', 'M07', 'M08') for c in out.revision.candidates)


def test_f_concept_not_anchored_scene(staged_inputs, require):
    stage = require('m56.catalog', 'stage_inputs')
    base, policies, sources = staged_inputs
    out = stage(base, (), policies, sources)
    assert out.deficits['missing_slots']['F'] == 6 and not any(c.category == 'F' for c in out.revision.candidates)


def test_inconsistent_source_rationale_blocks(staged_inputs, require):
    stage = require('m56.catalog', 'stage_inputs')
    base, policies, sources = staged_inputs
    selection = SourceRef(str(SPEC), sources[0].sha256, sources[0].bytes, '1', 'operator', 'M56_SELECTION_RECEIPT')
    c = base.candidates[0]
    new = replace(c, id='M56-P-C09', slot='C09', site_id='P04-J999', refs=(selection,),
                  parameters={**c.parameters, 'G': replace(c.parameters['G'], values=(F(30),))})
    review = ReviewRecord('x', 'M56_SELECTION', (selection,), 'operator', '2026-10-20', 'APPROVED', ('scope',), selection)
    from m56.catalog import _digest
    new = replace(new, environment={**new.environment, 'selection_review': replace(review, object_hash=_digest(
        replace(new, environment={k: v for k, v in new.environment.items() if k != 'selection_review'})))})
    out = stage(base, (new,), policies, (*sources, selection))
    assert out.status == 'SCHEMA_ERROR' and any(e.reason == 'RATIONALE_REVIEW_MISSING' for e in out.errors)


def test_source_ref_must_verify(staged_inputs, require, tmp_path):
    stage = require('m56.catalog', 'stage_inputs')
    base, policies, sources = staged_inputs
    forged = replace(sources[1], sha256='0'*64)
    out = stage(base, (), policies, (sources[0], forged))
    assert out.status == 'SCHEMA_ERROR' and any(e.reason in ('SOURCE_REF_UNVERIFIED', 'BASE_SOURCE_UNBOUND')
                                                for e in out.errors)


def test_promoted_f_proposal_rejected(staged_inputs, require):
    stage = require('m56.catalog', 'stage_inputs')
    base, policies, sources = staged_inputs
    promoted = replace(policies, approved_parameters={'F06-ALT1': replace(policies.approved_parameters['F06-ALT1'],
                                                                          status='READY')})
    out = stage(base, (), promoted, sources)
    assert out.status == 'SCHEMA_ERROR' and any(e.reason == 'F_PROPOSAL_PROMOTION_FORBIDDEN' for e in out.errors)


def test_c0_requires_46_not_46eligible(catalog_case, require):
    freeze, check = require('m56.catalog', 'freeze_c0'), require('m56.catalog', 'check_catalog')
    from m56.catalog import _digest
    from m56.model import FrozenResponse
    c = catalog_case()
    proof = SourceRef('synthetic://m', 'a'*64, 1, '1', 'branch-to-mainflow-geometry-topology', 'SYNTHETIC_TEST')
    cands = []
    for x in c.revision.candidates:
        env = {k: v for k, v in x.environment.items() if k != 'kind'} | {'weather': {'w': 1}, 'light': {'l': 1}}
        responses = tuple(FrozenResponse('EGO', a, None, {'NOMINAL': F(4)}, {}, {'program': {'initial': 'NOMINAL'}}, 'b'*64)
                          for a in ('A', 'B'))
        params = {'vN': ParameterProposal('vN', (F(3),), 'm/s', 'synthetic', (c.ref,), 'TEST')}
        x = replace(x, environment=env, responses=responses, parameters=params)
        if x.category == 'M':  # true-M needs its own branch-to-mainflow review
            review = c.review_factory(_digest((x.id, x.category, x.actors)), 'CATEGORY:M')
            from m56.model import encode_record
            x = replace(x, environment={**x.environment, 'category_review': encode_record(replace(review, refs=(proof,)))})
        cands.append(x)
    revision = replace(c.revision, candidates=tuple(cands))
    review = c.review_factory(_digest({'revision': revision, 'sites': c.sites}), 'C0')
    frozen = freeze(revision, c.sites, review)
    assert frozen.c0_receipt is not None
    audit = check(frozen, c.sites, ())
    assert audit.counts['eligible'] == 0 and audit.status == 'RELEASE_BLOCKED'


def test_probe_charter_not_acceptance_trial(staged_inputs, require, monkeypatch):
    stage = require('m56.catalog', 'stage_inputs')
    import m56.runtime as runtime
    from m56.model import ApprovalBundle, OwnershipReceipt, RuntimeIdentity
    base, policies, sources = staged_inputs
    stage(base, (), policies, sources)
    binds = []
    monkeypatch.setattr(runtime, '_native_factory', lambda *a: binds.append(a))
    probe = ('IDENTITY', 'PROBE_REVERSE')
    env = RuntimeIdentity('b', 'w', '0.9.16', '0.9.16', '3.12.10', {}, 'Town04', dict(runtime.PINNED_STOCK))
    own = OwnershipReceipt('b', 'w', '127.0.0.1', 1, 's', {'rpc': 2610}, (F(0), F(1)), 'm56', 'm56', probe)
    receipt = SourceRef('D:/charter.json', 'c'*64, 1, '1', 'operator', 'PROBE_CHARTER')
    from types import SimpleNamespace
    out = runtime.admit(SimpleNamespace(freeze_ref=None, proofs=()), ApprovalBundle((receipt,), {}, probe), env, own)
    assert out.status == 'BLOCKED_AUTHORITY' and 'SCOPE_NOT_APPROVED:VALIDATE_AB' in out.reasons and binds == []


def _complete_revision(c):
    """The test_c0_requires_46 construction: every candidate has a complete recipe; M has its category review."""
    from m56.catalog import _digest
    from m56.model import FrozenResponse, encode_record
    proof = SourceRef('synthetic://m', 'a'*64, 1, '1', 'branch-to-mainflow-geometry-topology', 'SYNTHETIC_TEST')
    cands = []
    for x in c.revision.candidates:
        env = {k: v for k, v in x.environment.items() if k != 'kind'} | {'weather': {'w': 1}, 'light': {'l': 1}}
        responses = tuple(FrozenResponse('EGO', a, None, {'NOMINAL': F(4)}, {}, {'program': {'initial': 'NOMINAL'}}, 'b'*64)
                          for a in ('A', 'B'))
        x = replace(x, environment=env, responses=responses,
                    parameters={'vN': ParameterProposal('vN', (F(3),), 'm/s', 'synthetic', (c.ref,), 'TEST')})
        if x.category == 'M':
            review = c.review_factory(_digest((x.id, x.category, x.actors)), 'CATEGORY:M')
            x = replace(x, environment={**x.environment, 'category_review': encode_record(replace(review, refs=(proof,)))})
        cands.append(x)
    return replace(c.revision, candidates=tuple(cands))


def _drop(revision, sites, ids):
    kept = tuple(x for x in revision.candidates if x.id not in ids)
    return replace(revision, candidates=kept), replace(sites, assignments={k: v for k, v in sites.assignments.items() if k not in ids})


def _addendum(tmp_path):
    path = tmp_path/'addendum.md'; path.write_text('partial C0 addendum (test)', encoding='utf-8')
    return ref(path, 'SPEC_ADDENDUM')


def test_partial_c0_freezes_only_the_count_deficit_with_the_addendum(catalog_case, require, tmp_path):
    freeze, guard = require('m56.catalog', 'freeze_c0'), require('m56.catalog', 'validation_precondition')
    from m56.catalog import _digest
    c = catalog_case()
    revision, sites = _drop(_complete_revision(c), c.sites, {x.id for x in c.revision.candidates if x.category == 'I'})
    review = c.review_factory(_digest({'revision': revision, 'sites': sites}), 'C0')
    assert 'CANDIDATE_COUNT' in freeze(revision, sites, review).reasons  # old rule unchanged without the addendum
    frozen = freeze(revision, sites, review, partial=_addendum(tmp_path))
    assert frozen.c0_receipt is not None and frozen.c0_receipt.kind == 'C0_PARTIAL'
    verdict = guard(frozen)
    assert verdict.status == 'C0_PRESENT_NOT_RUNTIME_AUTHORITY' and 'C0_PARTIAL' in verdict.reasons


def test_partial_c0_never_waives_other_gates(catalog_case, require, tmp_path):
    freeze = require('m56.catalog', 'freeze_c0')
    from m56.catalog import _digest
    c = catalog_case()
    full = _complete_revision(c)
    revision, sites = _drop(full, c.sites, {x.id for x in full.candidates if x.category == 'I'})
    broken = replace(revision, candidates=(replace(revision.candidates[0], environment={
        k: v for k, v in revision.candidates[0].environment.items() if k != 'weather'}), *revision.candidates[1:]))
    review = c.review_factory(_digest({'revision': broken, 'sites': sites}), 'C0')
    out = freeze(broken, sites, review, partial=_addendum(tmp_path))
    assert out.reasons == ('INCOMPLETE_CANDIDATE_RECIPE',)  # recipe gate still blocks; count deficit waived only
    missing = tmp_path/'gone.md'
    unverified = SourceRef(str(missing), 'f'*64, 1, '1', 'sha256', 'SPEC_ADDENDUM')
    review = c.review_factory(_digest({'revision': revision, 'sites': sites}), 'C0')
    assert 'CANDIDATE_COUNT' in freeze(revision, sites, review, partial=unverified).reasons  # unverified addendum
