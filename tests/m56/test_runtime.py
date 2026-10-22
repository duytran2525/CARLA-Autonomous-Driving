"""T12 lazy runtime admission; native transport replaced at the seam only."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace

import pytest

from m56.model import (ApprovalBundle, CapabilityProof, OwnershipReceipt, PreparationRequest,
                       QueryBundle, ReviewRecord, RunStore, RuntimeIdentity, SourceRef)

READ = ('IDENTITY', 'READ_MAP', 'READ_SETTINGS', 'READ_ACTORS', 'READ_BLUEPRINTS')


def ref(kind='OPERATOR_RECEIPT', uri='file:///receipt.json', sha='a'*64):
    return SourceRef(uri, sha, 1, '1', 'operator', kind)


class FakeBackend:
    def __init__(self, identity, blueprints=('vehicle.audi.a2',)):
        self.live, self.blueprints, self.queries = identity, blueprints, []

    def identity(self):
        return self.live

    def query(self, request):
        self.queries.append(request.query_ops)
        r = ref('NATIVE_RAW', 'file:///raw.json', 'b'*64)
        return QueryBundle(self.live.boot, self.live.world, {'name': self.live.map,
                           'blueprints': self.blueprints}, {}, {}, {}, {}, {}, (), (), (r,))


@pytest.fixture
def rt(monkeypatch, tmp_path):
    import m56.runtime as runtime
    mods = {'carla': ref('MODULE', 'file:///libcarla.pyd', 'c'*64),
            **{k: ref('MODULE', f'file:///{k}.py', v) for k, v in runtime.PINNED_STOCK.items()}}
    env = RuntimeIdentity('pid42@2026-10-20T05:00:00Z', 'world7', '0.9.16', '0.9.16', '3.12.10',
                          mods, 'Carla/Maps/Town04', {k: m.sha256 for k, m in mods.items()})
    own = OwnershipReceipt(env.boot, env.world, '127.0.0.1', 42, '2026-10-20T05:00:00Z',
                           {'rpc': 2610}, (F(0), F(3600)), 'm56', 'm56', READ)
    store = RunStore(tmp_path, 'run1', 'm56', tmp_path / 'journal.jsonl')
    req = PreparationRequest('d'*64, 'e'*64, READ, {'timeout_s': F(10)}, None, store)
    approvals = ApprovalBundle((ref(),), {}, READ)
    backend = FakeBackend(env)
    binds = []

    def factory(ownership, timeout_s):
        binds.append((ownership.host, ownership.ports['rpc'], timeout_s))
        return backend
    monkeypatch.setattr(runtime, '_native_factory', factory)
    return SimpleNamespace(m=runtime, env=env, own=own, req=req, approvals=approvals,
                           backend=backend, binds=binds)


def test_unapproved_prepare_never_binds_native(rt):
    out = rt.m.prepare(rt.req, replace(rt.approvals, allowed_scopes=()), rt.env, rt.own)
    assert out.status == 'BLOCKED_AUTHORITY'
    assert rt.binds == []


def test_approved_read_only_preflight_queries_once(rt):
    out = rt.m.prepare(rt.req, rt.approvals, rt.env, rt.own)
    assert isinstance(out, QueryBundle) and out.world == 'world7'
    assert rt.binds == [('127.0.0.1', 2610, 10.0)] and rt.backend.queries == [READ]


def test_non_loopback_host_blocks(rt):
    out = rt.m.prepare(rt.req, rt.approvals, rt.env, replace(rt.own, host='10.0.0.5'))
    assert 'NON_LOOPBACK_HOST' in out.reasons and rt.binds == []


def test_missing_store_blocks(rt):
    out = rt.m.prepare(replace(rt.req, store=None), rt.approvals, rt.env, rt.own)
    assert 'OWNED_STORE_MISSING' in out.reasons and rt.binds == []


def test_stale_boot_blocks(rt):
    rt.backend.live = replace(rt.env, boot='pid43@2026-10-20T06:00:00Z')
    out = rt.m.prepare(rt.req, rt.approvals, rt.env, rt.own)
    assert out.status == 'BLOCKED_OWNERSHIP' and 'IDENTITY_MISMATCH:boot' in out.reasons
    assert rt.backend.queries == []


def test_receipt_for_other_boot_blocks_before_bind(rt):
    out = rt.m.prepare(rt.req, rt.approvals, rt.env, replace(rt.own, boot='pid1@old'))
    assert out.status == 'BLOCKED_OWNERSHIP' and 'STALE_BOOT' in out.reasons and rt.binds == []


def test_foreign_tick_owner_blocks(rt):
    out = rt.m.prepare(rt.req, rt.approvals, rt.env, replace(rt.own, tick_owner='m55'))
    assert out.status == 'BLOCKED_OWNERSHIP' and 'FOREIGN_TICK_OWNER' in out.reasons and rt.binds == []


def test_source_hash_mismatch_blocks(rt):
    env = replace(rt.env, source_hashes={**rt.env.source_hashes, 'carla': 'f'*64})
    out = rt.m.prepare(rt.req, rt.approvals, env, rt.own)
    assert out.status == 'BLOCKED_SOURCE' and 'SOURCE_HASH_MISMATCH:carla' in out.reasons and rt.binds == []


def test_stock_file_byte_change_blocks_against_pin(rt):
    changed = ref('MODULE', 'file:///basic_agent.py', 'e'*64)
    env = replace(rt.env, modules={**rt.env.modules, 'basic_agent': changed},
                  source_hashes={**rt.env.source_hashes, 'basic_agent': 'e'*64})
    out = rt.m.prepare(rt.req, rt.approvals, env, rt.own)
    assert out.status == 'BLOCKED_SOURCE' and 'STOCK_PIN_MISMATCH:basic_agent' in out.reasons and rt.binds == []


def test_version_mismatch_blocks(rt):
    out = rt.m.prepare(rt.req, rt.approvals, replace(rt.env, server='0.9.15'), rt.own)
    assert out.status == 'BLOCKED_SOURCE' and 'VERSION_MISMATCH:server' in out.reasons and rt.binds == []


def test_op_must_be_both_approved_and_owned(rt):
    out = rt.m.prepare(rt.req, rt.approvals, rt.env, replace(rt.own, allowed_ops=READ[:2]))
    assert 'OP_NOT_OWNED:READ_SETTINGS' in out.reasons and rt.binds == []


def test_probe_not_validation_permission(rt):
    probe = replace(rt.req, query_ops=('PROBE_REVERSE',))
    ops = READ + ('PROBE_REVERSE',)
    approvals, own = replace(rt.approvals, allowed_scopes=ops), replace(rt.own, allowed_ops=ops)
    out = rt.m.prepare(probe, approvals, rt.env, own)
    assert 'PROBE_CHARTER_MISSING' in out.reasons and rt.binds == []
    verdict = rt.m.admit(SimpleNamespace(freeze_ref=None, proofs=()), approvals, rt.env, own)
    assert verdict.status == 'BLOCKED_AUTHORITY' and 'SCOPE_NOT_APPROVED:VALIDATE_AB' in verdict.reasons


def test_a2_missing_no_fallback(rt):
    rt.backend.blueprints = ('vehicle.tesla.model3',)
    out = rt.m.prepare(rt.req, rt.approvals, rt.env, rt.own)
    assert out.status == 'BLOCKED_CAPABILITY' and 'BLUEPRINT_MISSING:vehicle.audi.a2' in out.reasons


def test_synthetic_receipts_never_live_admit(rt):
    approvals = replace(rt.approvals, receipt_refs=(ref('SYNTHETIC_TEST'),))
    out = rt.m.prepare(rt.req, approvals, rt.env, rt.own)
    assert out.status == 'BLOCKED_AUTHORITY' and 'SYNTHETIC_RECEIPT' in out.reasons and rt.binds == []


def _query(raw):
    return QueryBundle('b', 'w', {}, {}, {}, {}, {}, {}, (), (), (raw,))


def test_capability_boolean_not_proof(rt):
    raw = ref('NATIVE_RAW', 'file:///raw.json', 'b'*64)
    out = rt.m.verify_capability(CapabilityProof('REVERSE_STOP', 'probe', (), None, {}, None, 'PASS'),
                                 _query(raw))
    assert out.status == 'WITNESS_UNCERTAIN' and 'CAPABILITY_RAW_MISSING' in out.reasons
    assert 'CAPABILITY_REVIEW_MISSING' in out.reasons


def test_door_getter_not_invented(rt):
    raw = ref('NATIVE_RAW', 'file:///raw.json', 'b'*64)
    review = ReviewRecord('x', 'CAPABILITY', (raw,), 'r', '2026-10-20', 'APPROVED', (), raw)
    proof = CapabilityProof('DOOR_COLLIDER', 'get_door_state', (raw,), None, {}, review, 'PASS')
    out = rt.m.verify_capability(proof, _query(raw))
    assert out.status == 'BLOCKED_CAPABILITY' and 'UNSUPPORTED_NATIVE_GETTER:DOOR_COLLIDER' in out.reasons


def test_capability_raw_must_come_from_query(rt):
    raw = ref('NATIVE_RAW', 'file:///raw.json', 'b'*64)
    review = ReviewRecord('x', 'CAPABILITY', (raw,), 'r', '2026-10-20', 'APPROVED', (), raw)
    proof = CapabilityProof('REVERSE_STOP', 'probe', (raw,), None, {}, review, 'PASS')
    assert rt.m.verify_capability(proof, _query(raw)).status == 'VALID'
    other = _query(ref('NATIVE_RAW', 'file:///other.json', 'c'*64))
    assert 'CAPABILITY_RAW_NOT_IN_QUERY' in rt.m.verify_capability(proof, other).reasons


def test_bind_backend_requires_admission(rt):
    ctx = SimpleNamespace(admission=SimpleNamespace(status='BLOCKED_AUTHORITY', reasons=('X',)), ownership=rt.own,
                          deadlines={'rpc_s': 10})
    assert rt.m.bind_backend(ctx).status == 'BLOCKED_AUTHORITY' and rt.binds == []


def test_runtime_import_has_no_carla():
    import sys
    import m56.runtime  # noqa: F401
    assert 'carla' not in sys.modules


def test_identify_requires_identity_scope_before_bind(rt):
    own = replace(rt.own, allowed_ops=('READ_MAP',))
    out = rt.m.identify(own, rt.approvals, 10)
    assert out.status == 'BLOCKED_AUTHORITY' and 'OP_NOT_OWNED:IDENTITY' in out.reasons and rt.binds == []


def test_identify_returns_live_identity_only(rt):
    assert rt.m.identify(rt.own, rt.approvals, 10) == rt.env and rt.backend.queries == []
