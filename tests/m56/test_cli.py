"""T16 explicit CLI: offline paths never import carla; operational paths never bind without authority."""
from fractions import Fraction as F
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from m56.model import (ApprovalBundle, OwnershipReceipt, PolicyBundle, PreparationRequest, RuntimeIdentity,
                       SourceRef, encode_record)

ROOT = Path(__file__).resolve().parents[2]


def write(path, record):
    path.write_text(json.dumps(encode_record(record), sort_keys=True), encoding='utf-8')
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def binds(monkeypatch):
    import m56.runtime as runtime
    seen = []
    monkeypatch.setattr(runtime, '_native_factory', lambda *a: seen.append(a) or pytest.fail('NATIVE_BIND'))
    return seen


@pytest.fixture
def offline26(catalog_case, tmp_path):
    c = catalog_case(count=26, junctions=13)
    paths = {'candidates': write(tmp_path/'candidates.json', c.revision), 'sites': write(tmp_path/'sites.json', c.sites),
             'policies': write(tmp_path/'policies.json', PolicyBundle('test', 'b'*64, {}, {}, {}, (c.ref,))),
             'reviews': tmp_path/'reviews.json'}
    paths['reviews'].write_text('[]', encoding='utf-8')
    return paths


def operational(tmp_path, scopes=()):
    ref = SourceRef('D:/receipt.json', 'a'*64, 1, '1', 'operator', 'OPERATOR_RECEIPT')
    env = RuntimeIdentity('b1', 'w7', '0.9.16', '0.9.16', '3.12.10', {}, 'Town04', {})
    own = OwnershipReceipt('b1', 'w7', '127.0.0.1', 1, 's', {'rpc': 2610}, (F(0), F(60)), 'm56', 'm56', scopes)
    files = {'environment': write(tmp_path/'environment.json', env), 'ownership': write(tmp_path/'ownership.json', own),
             'request': write(tmp_path/'request.json', PreparationRequest('d'*64, 'e'*64, ('IDENTITY',), {}, None)),
             'fixture': tmp_path/'fixture.json'}
    files['fixture'].write_text('{}', encoding='utf-8')
    approvals = ApprovalBundle((ref,), {k: sha(v) for k, v in files.items()}, scopes)
    files['approvals'] = write(tmp_path/'approvals.json', approvals)
    return files


def test_offline_audit_never_imports_carla(offline26, tmp_path, binds, require):
    main = require('m56.cli', 'main')
    out = tmp_path/'audit.json'
    code = main(['audit', '--candidates', str(offline26['candidates']), '--sites', str(offline26['sites']),
                 '--policies', str(offline26['policies']), '--reviews', str(offline26['reviews']), '--output', str(out)])
    assert code == 2
    assert binds == [] and 'carla' not in sys.modules
    report = json.loads(out.read_text(encoding='utf-8'))
    assert report['counts']['proposed'] == 26 and 'CANDIDATE_COUNT' in report['deficits']


def test_cli_help_without_native(tmp_path):
    probe = ("import runpy,sys;sys.argv=['cli.py','--help']\n"
             "try:\n runpy.run_path(sys.argv_path,run_name='__main__')\nexcept SystemExit as e:\n code=e.code\n"
             "print('EXIT',code,'carla' in sys.modules)")
    script = ROOT/'m56'/'cli.py'
    p = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', '-c', probe.replace('sys.argv_path', repr(str(script)))],
                       capture_output=True, text=True, cwd=tmp_path)
    assert p.returncode == 0, p.stderr
    for sub in ('schema-check', 'audit', 'stage-inputs', 'prepare', 'validate-ab', 'resume-audit', 'export'):
        assert sub in p.stdout
    assert 'EXIT 0 False' in p.stdout


def test_schema_check_structured_errors(tmp_path, require):
    main = require('m56.cli', 'main')
    bad = tmp_path/'bad.json'; bad.write_text('{"uri": 1}', encoding='utf-8')
    out = tmp_path/'r.json'
    assert main(['schema-check', '--kind', 'SourceRef', '--input', str(bad), '--output', str(out)]) == 3
    assert json.loads(out.read_text(encoding='utf-8'))['status'] == 'SCHEMA_ERROR'
    assert main(['schema-check', '--kind', 'SourceRef', '--input', str(bad), '--output', str(out)]) == 3  # no overwrite


def test_parser_errors_are_structured_not_systemexit(require, capsys):
    main = require('m56.cli', 'main')
    assert main(['audit', '--candidates']) == 3
    assert json.loads(capsys.readouterr().out)['status'] == 'SCHEMA_ERROR'


def test_validate_without_authority_no_rpc(tmp_path, binds, require):
    main = require('m56.cli', 'main')
    f = operational(tmp_path, scopes=())
    code = main(['validate-ab', '--fixture', str(f['fixture']), '--approvals', str(f['approvals']), '--ownership',
                 str(f['ownership']), '--environment', str(f['environment']), '--run', str(tmp_path/'run')])
    assert code == 2 and binds == []


def test_prepare_without_authority_no_rpc(tmp_path, binds, require):
    main = require('m56.cli', 'main')
    f = operational(tmp_path, scopes=())
    code = main(['prepare', '--request', str(f['request']), '--approvals', str(f['approvals']), '--ownership',
                 str(f['ownership']), '--environment', str(f['environment']), '--output', str(tmp_path/'prep')])
    assert code == 2 and binds == []


@pytest.mark.parametrize('flag', ['--force', '--retry', '--server-start', '--kill', '--seed=1', '--gain=2'])
def test_cli_force_retry_not_supported(tmp_path, binds, require, flag):
    main = require('m56.cli', 'main')
    f = operational(tmp_path, scopes=('VALIDATE_AB',))
    code = main(['validate-ab', '--fixture', str(f['fixture']), '--approvals', str(f['approvals']), '--ownership',
                 str(f['ownership']), '--environment', str(f['environment']), '--run', str(tmp_path/'run'), flag])
    assert code == 3 and binds == []


def test_source_snapshot_hash_mismatch(tmp_path, binds, require):
    main = require('m56.cli', 'main')
    f = operational(tmp_path, scopes=('IDENTITY',))
    f['ownership'].write_text(f['ownership'].read_text(encoding='utf-8') + ' ', encoding='utf-8')  # byte changed
    code = main(['prepare', '--request', str(f['request']), '--approvals', str(f['approvals']), '--ownership',
                 str(f['ownership']), '--environment', str(f['environment']), '--output', str(tmp_path/'prep')])
    assert code == 3 and binds == []


def test_cli_resume_does_not_execute(tmp_path, binds, require, capsys):
    main = require('m56.cli', 'main')
    from m56.evidence import open_run, seal, append_record
    run = tmp_path/'run'
    open_run(run, 'r1', 'm56')
    for action in ('A', 'B'):
        s = open_run(run/'episodes'/'C01'/action, 'r1', 'm56'); append_record(s, 'runner/stop.json', {'reasons': []}); seal(s)
    assert main(['resume-audit', '--run', str(run)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['completed'] == ['C01/A', 'C01/B'] and binds == []


def test_cli_export_deficit_no_list(tmp_path, offline26, binds, require):
    main = require('m56.cli', 'main')
    from m56.evidence import open_run
    run = tmp_path/'run'; open_run(run, 'r1', 'm56')
    target = run/'catalog'/'m56_catalog.json'
    assert main(['export', '--run', str(run), '--target', str(target)]) == 2
    assert not target.exists() and binds == []


def test_stage_inputs_retained_26_reports_missing_slots(tmp_path, binds, require):
    main = require('m56.cli', 'main')
    from m56.catalog import import_retained
    inputs = ROOT/'outputs/m56_offline_v1/inputs'
    spec, ref06 = inputs/'2026-10-07-m56-catalog-and-validation-design.md', inputs/'handoff_20261006/references/06_scene_proposal_and_validation_design.md'
    base = write(tmp_path/'base.json', import_retained(spec, ref06))
    sources = tmp_path/'sources.json'
    sources.write_text(json.dumps([encode_record(SourceRef(str(p), sha(p), p.stat().st_size, '1', 'sha256', 'APPROVED_SOURCE'))
                                   for p in (spec, ref06)]), encoding='utf-8')
    additions = tmp_path/'additions.json'; additions.write_text('[]', encoding='utf-8')
    policies = write(tmp_path/'policies.json', PolicyBundle('spec', 'f'*64, {}, {}, {}, ()))
    out = tmp_path/'staged'
    code = main(['stage-inputs', '--base', str(base), '--additions', str(additions), '--policies', str(policies),
                 '--sources', str(sources), '--output', str(out)])
    assert code == 2 and binds == []
    staged = json.loads((out/'campaign_inputs.json').read_text(encoding='utf-8'))
    assert staged['deficits']['missing_slots'] == {'I': 5, 'M': 4, 'O': 5, 'F': 6}
    assert len(staged['revision']['candidates']) == 26 and staged['revision']['c0_receipt'] is None
    assert set(json.loads((out/'input_manifest.json').read_text(encoding='utf-8'))['input_sha256']) == {
        'base', 'additions', 'policies', 'sources'}


def _admitted_inputs(tmp_path):
    from dataclasses import replace
    from m56 import runtime
    from tests.m56.test_runtime_ab import fixture, section
    fx = replace(fixture(), sections={'DESTINATION': section(14)})
    ops = ('VALIDATE_AB', 'SETTINGS', 'SPAWN', 'TICK', 'APPLY', 'DESTROY')
    receipt = tmp_path/'operator-receipt.json'; receipt.write_text('{"test": "operator receipt bytes"}', encoding='utf-8')
    rref = SourceRef(str(receipt), sha(receipt), receipt.stat().st_size, '1', 'operator', 'OPERATOR_RECEIPT')
    charter = tmp_path/'probe-charter.json'; charter.write_text('{"test": "probe charter bytes"}', encoding='utf-8')
    cref = SourceRef(str(charter), sha(charter), charter.stat().st_size, '1', 'operator', 'PROBE_CHARTER')
    env = RuntimeIdentity('b1', 'w7', '0.9.16', '0.9.16', '3.12.10', {}, 'Town04', dict(runtime.PINNED_STOCK))
    own = OwnershipReceipt('b1', 'w7', '127.0.0.1', 1, 's', {'rpc': 2610}, (F(0), F(300)), 'm56', 'm56', ops)
    files = {'fixture': write(tmp_path/'fixture.json', fx), 'ownership': write(tmp_path/'ownership.json', own),
             'environment': write(tmp_path/'environment.json', env)}
    files['approvals'] = write(tmp_path/'approvals.json', ApprovalBundle((rref, cref), {k: sha(v) for k, v in files.items()}, ('VALIDATE_AB',)))
    return fx, files


def test_validate_ab_needs_an_intact_probe_charter_receipt(tmp_path, monkeypatch, require, capsys):
    main = require('m56.cli', 'main')
    import m56.runtime as runtime
    from m56.model import decode_record, load_json
    fx, f = _admitted_inputs(tmp_path)
    monkeypatch.setattr(runtime, '_owned_factory', lambda ctx: pytest.fail('BOUND_WITHOUT_CHARTER'))
    bundle = decode_record('ApprovalBundle', load_json(f['approvals']))
    args = lambda run: ['validate-ab', '--fixture', str(f['fixture']), '--approvals', str(f['approvals']), '--ownership',
                        str(f['ownership']), '--environment', str(f['environment']), '--run', str(tmp_path/run)]
    write(f['approvals'], ApprovalBundle(bundle.receipt_refs[:1], bundle.object_hashes, bundle.allowed_scopes))
    assert main(args('no-charter')) == 2
    assert json.loads(capsys.readouterr().out) == {'status': 'BLOCKED_AUTHORITY', 'reasons': ['PROBE_CHARTER_MISSING']}
    write(f['approvals'], bundle)
    Path(bundle.receipt_refs[1].uri).write_text('{"test": "edited charter"}', encoding='utf-8')
    assert main(args('tampered')) == 3 and 'CHARTER_HASH_MISMATCH' in capsys.readouterr().out
    assert not (tmp_path/'no-charter').exists() and not (tmp_path/'tampered').exists()


def quick(t):
    # Ego leaves at 1 s and reaches the destination section (x=14) quickly so each episode ends early.
    return {'EGO': (F(6) if t < 1 else min(F(16), 6 + (t - 1) * 4), 0 if t < 1 or t > 3.5 else 4), 'NPC': (F(20), 0)}


def test_validate_ab_admitted_runs_one_ab_through_owned_seam(tmp_path, monkeypatch, require, capsys):
    main = require('m56.cli', 'main')
    import m56.runtime as runtime
    from tests.m56.test_runtime_ab import ScriptBackend
    fx, f = _admitted_inputs(tmp_path)
    bound = []
    monkeypatch.setattr(runtime, '_owned_factory', lambda ctx: bound.append(ctx) or ScriptBackend(tmp_path/'native', quick).bind(fx))
    monkeypatch.setattr(runtime, '_native_factory', lambda *a: pytest.fail('READ_ONLY_BIND'))
    run = tmp_path/'run'
    code = main(['validate-ab', '--fixture', str(f['fixture']), '--approvals', str(f['approvals']), '--ownership',
                 str(f['ownership']), '--environment', str(f['environment']), '--run', str(run)])
    report = json.loads(capsys.readouterr().out)
    assert len(bound) == 1 and report['status'] == 'LOCAL_AB_RECORDED'
    assert code == 2  # unreviewed initialization/W01 keep the witness from VALID: local completion is not claimed
    scene = run/'episodes'/fx.candidate_hash[:16]
    assert (scene/'A'/'manifest.json').exists() and (scene/'B'/'manifest.json').exists()
    # Re-invoking never repeats an action in the same run namespace.
    again = main(['validate-ab', '--fixture', str(f['fixture']), '--approvals', str(f['approvals']), '--ownership',
                  str(f['ownership']), '--environment', str(f['environment']), '--run', str(run)])
    assert again == 3 and len(bound) == 1


def test_export_rebuilds_eligibility_from_sealed_run(tmp_path, monkeypatch, require, capsys, catalog_case):
    main = require('m56.cli', 'main')
    import m56.runtime as runtime
    from tests.m56.test_runtime_ab import ScriptBackend
    fx, f = _admitted_inputs(tmp_path)
    monkeypatch.setattr(runtime, '_owned_factory', lambda ctx: ScriptBackend(tmp_path/'native', quick).bind(fx))
    run = tmp_path/'run'
    main(['validate-ab', '--fixture', str(f['fixture']), '--approvals', str(f['approvals']), '--ownership',
          str(f['ownership']), '--environment', str(f['environment']), '--run', str(run)])
    capsys.readouterr()
    assert runtime.load_episode(run/'episodes'/fx.candidate_hash[:16]/'A') is not None  # sealed, reconstructable
    (run/'catalog_inputs').mkdir()
    c = catalog_case()
    write(run/'catalog_inputs'/'revision.json', c.revision)
    from m56.catalog import check_catalog
    write(run/'catalog_inputs'/'audit.json', check_catalog(c.revision, c.sites, ()))
    target = run/'catalog'/'m56_catalog.json'
    assert main(['export', '--run', str(run), '--target', str(target)]) == 2
    out = json.loads(capsys.readouterr().out)
    assert 'AB_PROOF' in out['reasons'] and not target.exists()  # no reviews -> no eligibility record
