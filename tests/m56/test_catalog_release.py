"""T15 global eligibility and whitelisted final list export. Synthetic records only; never a release."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from m56.model import (ABVerdict, CatalogAudit, ComparisonRecord, EligibilityRecord, EpisodeVerdict, PhysicalState,
                       SourceRef, SpawnState, WitnessState)

def complete(catalog_case, tmp_path):
    """46 materialized synthetic candidates with weather/light, a C0 receipt, and a clean component audit.
    Evidence refs point at real bytes written here (kind NATIVE_RAW is a test label, verified by hash)."""
    import hashlib
    raw = tmp_path/'evidence-raw.json'; raw.write_bytes(b'{"test":"bytes"}')
    REAL = SourceRef(str(raw), hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_size, '1', 'native', 'NATIVE_RAW')
    c = catalog_case()
    # Materialized view: drop the fixture's test-label key; renderer must reject (not strip) it when present.
    candidates = tuple(replace(x, environment={**{k: v for k, v in x.environment.items() if k != 'kind'},
                                               'weather': {'preset': 'ClearNoon'}, 'light': {'street_lights': False}})
                       for x in c.revision.candidates)
    revision = replace(c.revision, candidates=candidates, c0_receipt=REAL)
    review = c.review_factory('d'*64, 'REALIZED_AB_COMPARABILITY_D09')
    review = replace(review, refs=(REAL,), authority_ref=REAL)
    pairs = tuple(ComparisonRecord((f'P{i:03}a', f'P{i:03}b'), (REAL,), ('A', 'B'), 'realized_scalar',
                                   ((F(1), F(2)),), (F(1, 2),), 'PASS', review, 'REALIZED') for i in range(155))
    audit = CatalogAudit({'proposed': 46, 'qualified_junctions': 23}, {}, {}, pairs, (), 'COMPONENT_COMPLETE')
    ok = EpisodeVerdict(SpawnState.CONFIRMED, PhysicalState.COMPLETE, WitnessState.VALID, (), (), {})
    evidence = tuple(EligibilityRecord(x.id, ABVerdict((ok, ok), (), (F(1), F(1, 2)), review, 'PASS'), (REAL,), (review,),
                                       (REAL,)) for x in candidates)
    return revision, audit, evidence


def test_component_complete_not_global_release(catalog_case, tmp_path, require):
    export = require('m56.catalog', 'export_catalog')
    revision, audit, evidence = complete(catalog_case, tmp_path)
    audit = replace(audit, comparisons=audit.comparisons[:-1])  # one inter-F/source descriptor review missing
    target = tmp_path/'m56_catalog.json'
    out = export(revision, audit, evidence, target)
    assert out.status == 'RELEASE_BLOCKED'
    assert not target.exists()


def test_list_has_complete_poses_units_routes(catalog_case, tmp_path, require):
    render = require('m56.catalog', 'render_catalog')
    revision, _, _ = complete(catalog_case, tmp_path)
    out = render(revision)
    assert len(out) == 46
    assert all(actor['pose']['z'] is not None for e in out for actor in e['actors'])
    assert all({'initial_speed_mps', 'route', 'destination', 'role', 'blueprint'} <= set(a) for e in out for a in e['actors'])
    assert all(e['environment'] == {'weather': {'preset': 'ClearNoon'}, 'light': {'street_lights': False}} for e in out)


def test_render_never_strips_unknown_fields(catalog_case, tmp_path, require):
    render = require('m56.catalog', 'render_catalog')
    revision, _, _ = complete(catalog_case, tmp_path)
    first = replace(revision.candidates[0], environment={**revision.candidates[0].environment, 'traffic_density': 3})
    out = render(replace(revision, candidates=(first, *revision.candidates[1:])))
    assert out.status == 'SCHEMA_ERROR' and any('traffic_density' in e.path for e in out.errors)


def test_unmaterialized_pose_rejected(catalog_case, tmp_path, require):
    render = require('m56.catalog', 'render_catalog')
    revision, _, _ = complete(catalog_case, tmp_path)
    c0 = revision.candidates[0]
    first = replace(c0, actors=(replace(c0.actors[0], pose=None), c0.actors[1]))
    assert render(replace(revision, candidates=(first, *revision.candidates[1:]))).status == 'SCHEMA_ERROR'


def test_npc_program_assignment_rejected(catalog_case, tmp_path, require):
    render = require('m56.catalog', 'render_catalog')
    revision, _, _ = complete(catalog_case, tmp_path)
    first = replace(revision.candidates[0], parameters={**revision.candidates[0].parameters, 'npc_driver': 'BehaviorAgent'})
    out = render(replace(revision, candidates=(first, *revision.candidates[1:])))
    assert out.status == 'SCHEMA_ERROR' and any(e.reason == 'NPC_PROGRAM_ASSIGNMENT_FORBIDDEN' for e in out.errors)


def test_155_pairs_not_duplicate_rows(catalog_case, tmp_path, require):
    export = require('m56.catalog', 'export_catalog')
    revision, audit, evidence = complete(catalog_case, tmp_path)
    pairs = (*audit.comparisons[:-1], audit.comparisons[0])  # 155 rows, one duplicate key
    out = export(revision, replace(audit, comparisons=pairs), evidence, tmp_path/'c.json')
    assert 'COMPARISON_COVERAGE' in out.reasons


def test_local_qualified_not_eligible(catalog_case, tmp_path, require):
    export = require('m56.catalog', 'export_catalog')
    revision, audit, evidence = complete(catalog_case, tmp_path)
    audit = replace(audit, counts={**audit.counts, 'qualified_junctions': 22}, deficits=('JUNCTION_SHORTFALL',))
    out = export(revision, audit, evidence, tmp_path/'c.json')
    assert out.status == 'RELEASE_BLOCKED' and 'JUNCTION_SHORTFALL' in out.reasons


def test_synthetic_export_is_not_release(catalog_case, tmp_path, require):
    export = require('m56.catalog', 'export_catalog')
    revision, audit, evidence = complete(catalog_case, tmp_path)
    synthetic = SourceRef('synthetic://x', 'b'*64, 1, '1', 'literal', 'SYNTHETIC_TEST')
    evidence = (replace(evidence[0], fixture=(synthetic,)), *evidence[1:])
    target = tmp_path/'c.json'
    out = export(revision, audit, evidence, target)
    assert out.status == 'RELEASE_BLOCKED' and 'SYNTHETIC_EVIDENCE' in out.reasons and not target.exists()


def test_target_exists_never_overwritten(catalog_case, tmp_path, require):
    export = require('m56.catalog', 'export_catalog')
    revision, audit, evidence = complete(catalog_case, tmp_path)
    target = tmp_path/'c.json'; target.write_bytes(b'original')
    out = export(revision, audit, evidence, target)
    assert out.status == 'RELEASE_BLOCKED' and target.read_bytes() == b'original'


def test_all_release_deficits_reported(catalog_case, tmp_path, require):
    export, summarize = require('m56.catalog', 'export_catalog'), require('m56.catalog', 'summarize')
    revision, audit, evidence = complete(catalog_case, tmp_path)
    audit = replace(audit, comparisons=audit.comparisons[:10], deficits=('JUNCTION_SHORTFALL',))
    evidence = evidence[:-1]
    out = export(revision, audit, evidence, tmp_path/'c.json')
    assert {'AB_PROOF', 'JUNCTION_SHORTFALL', 'COMPARISON_COVERAGE'} <= set(out.reasons)
    s = summarize(revision, audit, evidence)
    assert s['counts']['eligible'] == 45 and s['counts']['comparisons'] == 10 and s['status'] == 'RELEASE_BLOCKED'
    assert {'AB_PROOF', 'JUNCTION_SHORTFALL', 'COMPARISON_COVERAGE'} <= set(s['deficits'])


def test_tampered_evidence_bytes_block_release(catalog_case, tmp_path, require):
    export = require('m56.catalog', 'export_catalog')
    revision, audit, evidence = complete(catalog_case, tmp_path)
    (tmp_path/'evidence-raw.json').write_bytes(b'changed')
    out = export(revision, audit, evidence, tmp_path/'c.json')
    assert out.status == 'RELEASE_BLOCKED' and 'EVIDENCE_SOURCE_UNVERIFIED' in out.reasons


def test_clean_real_records_export_exactly_once(catalog_case, tmp_path, require):
    """Positive path with non-synthetic refs only: creates the list exclusively, never a second time."""
    export = require('m56.catalog', 'export_catalog')
    revision, audit, evidence = complete(catalog_case, tmp_path)
    target = tmp_path/'m56_catalog.json'
    out = export(revision, audit, evidence, target)
    assert out.status == 'EXPORTED' and target.exists()
    import json
    assert len(json.loads(target.read_text(encoding='utf-8'))) == 46
    assert export(revision, audit, evidence, target).status == 'RELEASE_BLOCKED'
