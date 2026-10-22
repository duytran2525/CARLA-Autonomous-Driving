"""M56 explicit CLI (T16). Offline subcommands never import carla; operational ones bind only after admission.

Exit codes: 0 = valid schema / deficit-free audit or staging / completed requested step / eligible export;
2 = blocked / scientific deficit / incomplete / review required; 3 = schema / integrity / ownership / operational.
Exit 0 of an operational or local step never implies a global catalog release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

if __name__ == '__main__':  # script bootstrap: only this package's parent, in-process
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class _CLIError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # structured schema error instead of argparse's SystemExit(2)
        raise _CLIError(message)


def _parser():
    p = _Parser(prog='m56', description='M56 catalog/validation CLI (no server start/kill, no retry/force/seed/gain).')
    sub = p.add_subparsers(dest='command', required=True, parser_class=_Parser)
    s = sub.add_parser('schema-check'); s.add_argument('--kind', required=True)
    s.add_argument('--input', required=True); s.add_argument('--output', required=True)
    s = sub.add_parser('audit')
    for k in ('candidates', 'sites', 'policies', 'reviews', 'output'):
        s.add_argument('--' + k, required=True)
    s = sub.add_parser('stage-inputs')
    for k in ('base', 'additions', 'policies', 'sources', 'output'):
        s.add_argument('--' + k, required=True)
    s = sub.add_parser('prepare')
    for k in ('request', 'approvals', 'ownership', 'environment', 'output'):
        s.add_argument('--' + k, required=True)
    s = sub.add_parser('validate-ab')
    for k in ('fixture', 'approvals', 'ownership', 'environment', 'run'):
        s.add_argument('--' + k, required=True)
    s = sub.add_parser('resume-audit'); s.add_argument('--run', required=True)
    s = sub.add_parser('export'); s.add_argument('--run', required=True); s.add_argument('--target', required=True)
    return p


def _report(payload, output=None):
    text = json.dumps(payload, indent=1, sort_keys=True, default=str)
    if output is None:
        print(text)
        return True
    try:
        with Path(output).open('x', encoding='utf-8') as stream:  # never overwrite a report
            stream.write(text + '\n')
        return True
    except FileExistsError:
        print(json.dumps({'status': 'OUTPUT_EXISTS', 'output': str(output)}))
        return False


def _load(kind, path):
    from m56.model import SchemaErrors, decode_record, load_json
    out = decode_record(kind, load_json(Path(path)))
    if isinstance(out, SchemaErrors):
        raise _CLIError(f'{kind}:{path}:' + ';'.join(f'{e.path}:{e.reason}' for e in out.errors))
    return out


def _verified_inputs(args, names):
    """Operational inputs must match the approval bundle's object hashes before anything is decoded or bound."""
    approvals = _load('ApprovalBundle', args.approvals)
    for name in names:
        expected = approvals.object_hashes.get(name)
        actual = hashlib.sha256(Path(getattr(args, name)).read_bytes()).hexdigest()
        if expected is None:
            raise _CLIError(f'INPUT_HASH_MISSING:{name}')
        if expected != actual:
            raise _CLIError(f'INPUT_HASH_MISMATCH:{name}')
    return approvals


def _schema_check(args):
    from m56.model import SchemaErrors, decode_record, load_json
    out = decode_record(args.kind, load_json(Path(args.input)))
    ok = not isinstance(out, SchemaErrors)
    payload = {'status': 'VALID' if ok else 'SCHEMA_ERROR', 'kind': args.kind,
               'errors': [] if ok else [{'path': e.path, 'reason': e.reason} for e in out.errors]}
    return (0 if ok else 3) if _report(payload, args.output) else 3


def _audit(args):
    from collections import Counter
    from m56.catalog import audit_diversity, check_catalog, load_candidates
    from m56.model import SchemaErrors, decode_record, load_json
    revision = load_candidates(Path(args.candidates))
    if isinstance(revision, SchemaErrors):
        raise _CLIError('candidates:' + ';'.join(e.reason for e in revision.errors))
    sites, policies = _load('SiteLedger', args.sites), _load('PolicyBundle', args.policies)
    reviews = tuple(decode_record('ReviewRecord', r) for r in load_json(Path(args.reviews)))
    if any(isinstance(r, SchemaErrors) for r in reviews):
        raise _CLIError('reviews:SCHEMA_ERROR')
    comparisons = audit_diversity(revision, policies, reviews)
    audit = check_catalog(revision, sites, comparisons)
    from m56.model import encode_record
    payload = {'status': audit.status, 'counts': dict(audit.counts), 'towns': dict(audit.towns),
               'deficits': list(audit.deficits), 'comparison_status': dict(Counter(c.status for c in comparisons)),
               'record': encode_record(audit), 'note': 'offline audit; never a release'}
    if not _report(payload, args.output):
        return 3
    return 2 if audit.deficits else 0


def _stage_inputs(args):
    from m56.catalog import stage_inputs  # resolved only when this command runs (T17), never at import/help
    from m56.model import SchemaErrors, decode_record, encode_record, load_json
    base, policies = _load('CandidateRevision', args.base), _load('PolicyBundle', args.policies)
    additions = tuple(decode_record('Candidate', c) for c in load_json(Path(args.additions)))
    sources = tuple(decode_record('SourceRef', r) for r in load_json(Path(args.sources)))
    if any(isinstance(x, SchemaErrors) for x in (*additions, *sources)):
        raise _CLIError('additions/sources:SCHEMA_ERROR')
    out = stage_inputs(base, additions, policies, sources)
    if isinstance(out, SchemaErrors):
        _report({'status': 'SCHEMA_ERROR', 'errors': [{'path': e.path, 'reason': e.reason} for e in out.errors]})
        return 3
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)  # exclusive namespace; never reused
    manifest = {name: hashlib.sha256(Path(getattr(args, name)).read_bytes()).hexdigest()
                for name in ('base', 'additions', 'policies', 'sources')}
    if not (_report(encode_record(out), root / 'campaign_inputs.json')
            and _report({'input_sha256': manifest, 'deficits': encode_record(out.deficits)}, root / 'input_manifest.json')):
        return 3
    return 2 if out.deficits['missing_slots'] else 0


def _prepare(args):
    from dataclasses import replace
    from m56 import runtime
    from m56.evidence import open_run
    from m56.model import RunStore
    approvals = _verified_inputs(args, ('request', 'ownership', 'environment'))
    request, ownership = _load('PreparationRequest', args.request), _load('OwnershipReceipt', args.ownership)
    environment = _load('RuntimeIdentity', args.environment)
    blocked = runtime._authority_reasons(request.query_ops, approvals, ownership, request.charter_ref)
    if blocked:  # refuse before creating a namespace or binding anything
        _report({'status': 'BLOCKED_AUTHORITY', 'reasons': blocked})
        return 2
    store = open_run(Path(args.output), 'prepare', ownership.writer)
    if not isinstance(store, RunStore):
        raise _CLIError('OUTPUT_' + store.status)
    out = runtime.prepare(replace(request, store=store), approvals, environment, ownership)
    status = getattr(out, 'status', 'QUERY_COMPLETE')
    _report({'status': status, 'reasons': list(getattr(out, 'reasons', ()))})
    return 0 if status == 'QUERY_COMPLETE' else 2


def _validate_ab(args):
    from m56 import runtime
    approvals = _verified_inputs(args, ('fixture', 'ownership', 'environment'))
    ownership, environment = _load('OwnershipReceipt', args.ownership), _load('RuntimeIdentity', args.environment)
    # The probe charter (spawn/tick/settings in an owned world) travels inside the approval bundle as a receipt;
    # its bytes must still match, otherwise it is not the approved charter.
    charter = runtime._charter(approvals)
    if charter is None and any(r.kind == 'PROBE_CHARTER' for r in approvals.receipt_refs):
        raise _CLIError('CHARTER_HASH_MISMATCH')
    blocked = runtime._authority_reasons(('VALIDATE_AB',), approvals, ownership, charter)
    if blocked:  # G3/G4/G5 receipts are part of approvals; nothing is inferred from the command line
        _report({'status': 'BLOCKED_AUTHORITY', 'reasons': blocked})
        return 2
    fixture = _load('CompiledFixture', args.fixture)
    verdict = runtime.admit(fixture, approvals, environment, ownership)
    if verdict.status != 'ADMITTED':
        _report({'status': verdict.status, 'reasons': list(verdict.reasons)})
        return 2
    from dataclasses import replace
    from m56.evidence import open_run
    from m56.model import RunStore, RunSummary, RuntimeContext
    store = open_run(Path(args.run), 'validate-ab', ownership.writer)  # create-exclusive; never reused
    if not isinstance(store, RunStore):
        raise _CLIError('OUTPUT_' + store.status)
    ctx = RuntimeContext(None, environment, ownership, approvals, verdict, store,
                         {'rpc_s': 10, 'tick_s': 5, 'cleanup_s': 15, 'outer_s': 300}, 'AB_PAIR', 'RUNNING')
    backend = runtime.bind_owned(ctx)
    if not hasattr(backend, 'tick'):
        _report({'status': backend.status, 'reasons': list(backend.reasons)})
        return 2
    ctx = replace(ctx, backend=backend)
    out = runtime.run_ab(ctx, fixture, fixture.candidate_hash[:16])
    if 'RESTORE' in ownership.allowed_ops:  # once, at the end of the A/B scope
        backend.restore(ownership, 15)
    if isinstance(out, RunSummary):
        _report({'status': 'BLOCKED', 'reasons': list(out.blocked)})
        return 2
    axes = {k: [str(v.verdict.spawn), str(v.verdict.physical), str(v.verdict.witness), list(v.verdict.reasons)]
            for k, v in zip('AB', out)}
    _report({'status': 'LOCAL_AB_RECORDED', 'axes': axes, 'note': 'local result only; never a catalog release'})
    ok = all((v.verdict.spawn, v.verdict.physical, v.verdict.witness) == ('CONFIRMED', 'COMPLETE', 'VALID') for v in out)
    return 0 if ok else 2


def _store(run):
    from m56.model import RunStore
    root = Path(run).resolve()
    meta = json.loads((root / 'writer.json').read_text(encoding='utf-8'))
    return RunStore(root, meta['run_id'], meta['writer'], root / 'journal.jsonl')


def _resume_audit(args):
    from m56.runtime import resume_audit
    s = resume_audit(_store(args.run))
    _report({'attempted': list(s.attempted), 'completed': list(s.completed), 'invalid': list(s.invalid),
             'note': 'audit only; nothing executed'})
    return 0 if s.attempted and not s.invalid and s.completed == s.attempted else 2


def _export(args):
    """Inputs: catalog_inputs/revision.json (frozen C0 revision) and audit.json (CatalogAudit or an audit report
    with 'record'); eligibility from catalog_inputs/eligibility.json or rebuilt from sealed episodes + reviews/."""
    from m56.catalog import export_catalog
    from m56.model import CatalogAudit, load_json, decode_record, SchemaErrors
    from m56.runtime import eligibility_from_run
    root = _store(args.run).root
    inputs = root / 'catalog_inputs'
    missing = [n for n in ('revision', 'audit') if not (inputs / f'{n}.json').exists()]
    if missing:
        _report({'status': 'RELEASE_BLOCKED', 'reasons': [f'GLOBAL_EVIDENCE_MISSING:{n}' for n in missing]})
        return 2
    revision = _load('CandidateRevision', inputs / 'revision.json')
    payload = load_json(inputs / 'audit.json')
    audit = decode_record('CatalogAudit', payload.get('record', payload) if isinstance(payload, dict) else payload)
    if not isinstance(audit, CatalogAudit):
        raise _CLIError('audit:SCHEMA_ERROR')
    if (inputs / 'eligibility.json').exists():
        evidence = tuple(decode_record('EligibilityRecord', e) for e in load_json(inputs / 'eligibility.json'))
    else:
        evidence = eligibility_from_run(root) if (root / 'episodes').is_dir() else ()
    if any(isinstance(e, SchemaErrors) for e in evidence):
        raise _CLIError('eligibility:SCHEMA_ERROR')
    out = export_catalog(revision, audit, evidence, Path(args.target))
    _report({'status': out.status, 'reasons': list(getattr(out, 'reasons', ()))})
    return 0 if out.status == 'EXPORTED' else 2


_COMMANDS = {'schema-check': _schema_check, 'audit': _audit, 'stage-inputs': _stage_inputs, 'prepare': _prepare,
             'validate-ab': _validate_ab, 'resume-audit': _resume_audit, 'export': _export}


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        return _COMMANDS[args.command](args)
    except _CLIError as e:
        _report({'status': 'SCHEMA_ERROR', 'reasons': [str(e)]})
        return 3
    except (OSError, ValueError, KeyError) as e:
        _report({'status': 'OPERATIONAL_FAILURE', 'reasons': [repr(e)]})
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
