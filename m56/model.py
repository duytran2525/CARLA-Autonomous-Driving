"""Frozen records and strict source-aware JSON. No native imports or I/O effects."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING, dataclass as _dataclass, fields, is_dataclass
from enum import StrEnum
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Protocol, Union, get_args, get_origin, get_type_hints
from functools import lru_cache as _lru_cache


@_lru_cache(maxsize=None)
def _type_hints(kind):
    """get_type_hints is a pure function of the class; cached (perf 2026-10-25: ~45% of offline evaluation)."""
    return get_type_hints(kind)
import json
import math
import re
import types

Number = Fraction
Vec3 = tuple[float, float, float]
VertexSet = tuple[Vec3, ...]


class SpawnState(StrEnum):
    CONFIRMED = 'CONFIRMED'
    FAILED = 'FAILED'
    UNKNOWN = 'UNKNOWN'
    NOT_RUN = 'NOT_RUN'


class PhysicalState(StrEnum):
    COMPLETE = 'COMPLETE'
    FAILED = 'FAILED'
    INCOMPLETE = 'INCOMPLETE'
    UNKNOWN = 'UNKNOWN'
    NOT_RUN = 'NOT_RUN'


class WitnessState(StrEnum):
    VALID = 'VALID'
    UNKNOWN = 'UNKNOWN'
    UNCERTAIN = 'UNCERTAIN'
    INVALID = 'INVALID'
    NOT_RUN = 'NOT_RUN'


def _freeze(value):
    if isinstance(value, Mapping):
        return types.MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def dataclass(*, frozen):
    """Frozen schema records also own immutable copies of nested containers."""
    def decorate(cls):
        def post_init(self):
            for field in fields(self):
                object.__setattr__(self, field.name, _freeze(getattr(self, field.name)))
        cls.__post_init__ = post_init
        return _dataclass(frozen=frozen)(cls)
    return decorate


@dataclass(frozen=True)
class FieldError:
    path: str
    reason: str


@dataclass(frozen=True)
class SchemaErrors:
    errors: tuple[FieldError, ...]
    status: str = 'SCHEMA_ERROR'


@dataclass(frozen=True)
class SourceRef:
    uri: str
    sha256: str
    bytes: int
    version: str
    method: str
    kind: str
    frame: int | None = None
    time: Number | None = None


@dataclass(frozen=True)
class ReviewRecord:
    object_hash: str
    scope: str
    refs: tuple[SourceRef, ...]
    reviewer: str
    date: str
    verdict: str
    reasons: tuple[str, ...]
    authority_ref: SourceRef | None


@dataclass(frozen=True)
class Transform6:
    x: float
    y: float
    z: float
    pitch: float
    yaw: float
    roll: float


@dataclass(frozen=True)
class LaneRef:
    town: str
    road_id: str
    section_id: int
    lane_id: int
    s: Number


@dataclass(frozen=True)
class DirectedRoute:
    refs: tuple[LaneRef, ...]
    transforms: tuple[Transform6, ...]
    arc: tuple[Number, ...]
    map_hash: str
    continuity: tuple[SourceRef, ...]
    destination: Number


@dataclass(frozen=True)
class BodyRecord:
    bbox_offset: Vec3
    rotation: Vec3
    extents: Vec3
    vertices: VertexSet
    blueprint: str
    attrs: Mapping[str, str]
    physics: Mapping[str, object]
    source: SourceRef


@dataclass(frozen=True)
class Section:
    vertices: VertexSet
    normal: Vec3
    route_station: Number
    limits: Mapping[str, Number]


@dataclass(frozen=True)
class Domain:
    e_entry: Section
    e_exit: Section
    n_entry: Section
    n_exit: Section
    region: VertexSet
    topology: Mapping[str, object]
    proof: tuple[SourceRef, ...]
    hash: str


@dataclass(frozen=True)
class BoundCertificate:
    method: str
    interval: tuple[Number, Number]
    bounds: Mapping[str, object]
    error: Number
    source: SourceRef
    review: ReviewRecord


@dataclass(frozen=True)
class Sweep:
    volumes: tuple[VertexSet, ...]
    certificates: tuple[BoundCertificate, ...]
    vertical_limits: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class ActorRecipe:
    role: str
    blueprint: str
    initial_speed_mps: Number
    pose: Transform6 | None
    pose_recipe: Mapping[str, object]
    route_recipe: Mapping[str, object]
    destination: Number | None


@dataclass(frozen=True)
class ParameterProposal:
    name: str
    values: tuple[Number, ...]
    units: str
    rationale: str
    source: tuple[SourceRef, ...]
    status: str


@dataclass(frozen=True)
class FrozenResponse:
    actor_role: str
    action_id: str
    route: DirectedRoute | None
    targets: Mapping[str, Number]
    profile: Mapping[str, object]
    phases: Mapping[str, object]
    hash: str


@dataclass(frozen=True)
class Candidate:
    id: str
    slot: str
    version: str
    lineage: tuple[str, ...]
    category: str
    town: str
    site_id: str
    actors: tuple[ActorRecipe, ...]
    parameters: Mapping[str, ParameterProposal]
    responses: tuple[FrozenResponse, ...]
    environment: Mapping[str, object]
    refs: tuple[SourceRef, ...]


@dataclass(frozen=True)
class CandidateRevision:
    revision_id: str
    candidates: tuple[Candidate, ...]
    source_hash: str
    c0_receipt: SourceRef | None


@dataclass(frozen=True)
class IdentityMethod:
    method_id: str
    version: str
    hash: str
    rules: Mapping[str, object]


@dataclass(frozen=True)
class SiteRecord:
    id: str
    kind: str
    geography: Mapping[str, object]
    topology: Mapping[str, object]
    interaction_refs: tuple[SourceRef, ...]
    review: ReviewRecord | None


@dataclass(frozen=True)
class SiteLedger:
    method: IdentityMethod
    records: tuple[SiteRecord, ...]
    assignments: Mapping[str, str]
    freeze_ref: SourceRef | None


@dataclass(frozen=True)
class PolicyBundle:
    version: str
    hash: str
    approved_parameters: Mapping[str, ParameterProposal]
    event_specs: Mapping[str, object]
    descriptor_specs: Mapping[str, object]
    receipt_refs: tuple[SourceRef, ...]


@dataclass(frozen=True)
class FrozenMetricPair:
    names: tuple[str, str]
    units: tuple[str, str]
    estimators: tuple[str, str]
    window: tuple[tuple[str, str], tuple[str, str]]
    reference: str
    hash: str
    approval_level: str


@dataclass(frozen=True)
class CapabilityProof:
    kind: str
    method: str
    raw_refs: tuple[SourceRef, ...]
    uncertainty: Number | None
    limits: Mapping[str, object]
    review: ReviewRecord | None
    status: str


@dataclass(frozen=True)
class QueryBundle:
    boot: str
    world: str
    map: Mapping[str, object]
    routes: Mapping[str, DirectedRoute]
    bodies: Mapping[str, BodyRecord]
    poses: Mapping[str, Transform6]
    ground: Mapping[str, CapabilityProof]
    physics: Mapping[str, object]
    capabilities: tuple[CapabilityProof, ...]
    certificates: tuple[BoundCertificate, ...]
    refs: tuple[SourceRef, ...]


@dataclass(frozen=True)
class CompiledFixture:
    candidate_hash: str
    policy_hash: str
    actors: tuple[ActorRecipe, ...]
    environment: Mapping[str, object]
    poses: Mapping[str, Transform6]
    routes: Mapping[str, DirectedRoute]
    domain: Domain
    G: Number | None
    sections: Mapping[str, Section]
    responses: tuple[FrozenResponse, ...]
    pair: FrozenMetricPair
    proofs: tuple[CapabilityProof, ...]
    freeze_ref: SourceRef


@dataclass(frozen=True)
class ApprovalBundle:
    receipt_refs: tuple[SourceRef, ...]
    object_hashes: Mapping[str, str]
    allowed_scopes: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeIdentity:
    boot: str
    world: str
    client: str
    server: str
    python: str
    modules: Mapping[str, SourceRef]
    map: str
    source_hashes: Mapping[str, str]


@dataclass(frozen=True)
class OwnershipReceipt:
    boot: str
    world: str
    host: str
    pid: int
    start: str
    ports: Mapping[str, int]
    exclusive_window: tuple[Number, Number]
    tick_owner: str
    writer: str
    allowed_ops: tuple[str, ...]


@dataclass(frozen=True)
class RunStore:
    root: Path
    run_id: str
    writer: str
    journal: Path


@dataclass(frozen=True)
class PreparationRequest:
    candidate_hash: str
    recipe_hash: str
    query_ops: tuple[str, ...]
    bounds: Mapping[str, Number]
    charter_ref: SourceRef | None
    store: RunStore | None = None


@dataclass(frozen=True)
class ControlPacket:
    throttle: float
    steer: float
    brake: float
    hand_brake: bool
    reverse: bool
    manual_gear_shift: bool
    gear: int


@dataclass(frozen=True)
class CommandRecord:
    actor: int
    frame: int
    next_frame: int
    kind: str
    target_kmh: Number
    offset: Number
    control: ControlPacket | None
    light_state: int | None
    cause: str
    response_hash: str


@dataclass(frozen=True)
class ActorFrame:
    role: str
    id: int
    pose: Transform6
    velocity: Vec3
    body: BodyRecord
    arc: Number | None
    gaps: Mapping[str, Number | None]
    commands: tuple[CommandRecord, ...]
    readback: ControlPacket | None
    light_readback: int | None
    plan_queue: int
    route_valid: bool | None
    ground: CapabilityProof | None


@dataclass(frozen=True)
class EventRecord:
    name: str
    frame: int
    time: Number
    witness_refs: tuple[SourceRef, ...]


@dataclass(frozen=True)
class FrameRecord:
    boot: str
    world: str
    frame: int
    simtime: Number
    dt: Number
    actors: tuple[ActorFrame, ...]
    events: tuple[EventRecord, ...]
    integrity: Mapping[str, object]


@dataclass(frozen=True)
class ScriptState:
    phase: str
    start: Number
    events: tuple[EventRecord, ...]


@dataclass(frozen=True)
class ResponseState:
    command: CommandRecord
    state: ScriptState


@dataclass(frozen=True)
class MetricValue:
    name: str
    value: Number | None
    unit: str
    window: tuple[str, str]
    reference: str
    estimator: str
    frames: tuple[int, ...]
    uncertainty: Number | None
    status: str


@dataclass(frozen=True)
class ComparisonRecord:
    pair_ids: tuple[str, str]
    descriptor_refs: tuple[SourceRef, ...]
    source_actions: tuple[str, ...]
    aggregation: str
    values: tuple[tuple[Number | None, Number | None], ...]
    deltas: tuple[Number | None, ...]
    status: str
    review: ReviewRecord | None
    declared_or_realized: str


@dataclass(frozen=True)
class EpisodeVerdict:
    spawn: SpawnState
    physical: PhysicalState
    witness: WitnessState
    reasons: tuple[str, ...]
    events: tuple[EventRecord, ...]
    metrics: Mapping[str, MetricValue]


@dataclass(frozen=True)
class EpisodeEvidence:
    raw: tuple[FrameRecord, ...]
    journal: tuple[SourceRef, ...]
    fixture: SourceRef
    source: tuple[SourceRef, ...]
    manifest: SourceRef | None
    integrity: Mapping[str, object]
    verdict: EpisodeVerdict | None
    end_simtime: Number


@dataclass(frozen=True)
class ABVerdict:
    action_proofs: tuple[EpisodeVerdict, ...]
    metrics: tuple[MetricValue, ...]
    comparisons: tuple[Number | None, ...]
    review: ReviewRecord | None
    status: str


@dataclass(frozen=True)
class EligibilityRecord:
    scene: str
    AB: ABVerdict
    fixture: tuple[SourceRef, ...]
    review: tuple[ReviewRecord, ...]
    global_refs: tuple[SourceRef, ...]


@dataclass(frozen=True)
class CatalogAudit:
    counts: Mapping[str, int]
    towns: Mapping[str, object]
    sites: Mapping[str, object]
    comparisons: tuple[ComparisonRecord, ...]
    deficits: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class ReplacementTransaction:
    id: str
    slot: str
    old_hash: str
    new_hash: str
    phase: str
    reason: str
    refs: tuple[SourceRef, ...]
    reviewer: str
    approval: ReviewRecord | None
    counters: tuple[int, int]


@dataclass(frozen=True)
class ReplacementLedger:
    c0_hash: str | None
    transactions: tuple[ReplacementTransaction, ...]
    used: int


@dataclass(frozen=True)
class ReplacementResult:
    status: str
    ledger: ReplacementLedger
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ArtifactRef:
    relativepath: str
    hash: str
    size: int
    kind: str


@dataclass(frozen=True)
class IntegrityReport:
    status: str
    reasons: tuple[str, ...]
    refs: tuple[SourceRef, ...] = ()


@dataclass(frozen=True)
class AdmissionVerdict:
    status: str
    reasons: tuple[str, ...]
    refs: tuple[SourceRef, ...] = ()


@dataclass(frozen=True)
class BlockedPreparation:
    status: str
    reasons: tuple[str, ...]
    refs: tuple[SourceRef, ...] = ()


@dataclass(frozen=True)
class BlockedFixture:
    reasons: tuple[str, ...]
    status: str = 'BLOCKED_FIXTURE'
    refs: tuple[SourceRef, ...] = ()


@dataclass(frozen=True)
class ReleaseBlocked:
    status: str
    reasons: tuple[str, ...]
    refs: tuple[SourceRef, ...] = ()


@dataclass(frozen=True)
class ExportReceipt:
    status: str
    output: ArtifactRef
    refs: tuple[SourceRef, ...]


@dataclass(frozen=True)
class CampaignInputs:
    revision: CandidateRevision
    policies: PolicyBundle
    source_inventory: tuple[SourceRef, ...]
    deficits: Mapping[str, object]


@dataclass(frozen=True)
class OwnedRegistry:
    boot: str
    world: str
    owned_vehicle_ids: tuple[int, ...]
    owned_sensor_ids: tuple[int, ...]
    spawn_responses: tuple[SpawnResponse, ...]


@dataclass(frozen=True)
class CleanupReceipt:
    status: str
    destroyed: tuple[int, ...]
    survivors: tuple[int, ...]
    refs: tuple[SourceRef, ...]


@dataclass(frozen=True)
class RunSummary:
    attempted: tuple[str, ...]
    completed: tuple[str, ...]
    blocked: tuple[str, ...]
    invalid: tuple[str, ...]
    eligibility_refs: tuple[SourceRef, ...]


@dataclass(frozen=True)
class SpawnResponse:
    actor_id: int | None
    error: str | None
    source: SourceRef


@dataclass(frozen=True)
class OperationResponse:
    id: int | None
    error: str | None
    frame: int | None
    source: SourceRef


@dataclass(frozen=True)
class SensorPacket:
    sensor_id: int
    frame: int
    time: Number
    transform: Transform6
    actor_id: int
    other_actor_id: int | None
    normal_impulse: Vec3 | None
    raw_ref: SourceRef
    errors: tuple[str, ...]


class Backend(Protocol):
    def identity(self) -> RuntimeIdentity: ...
    def query(self, request: PreparationRequest) -> QueryBundle: ...
    def spawn(self, actors: tuple[ActorRecipe, ...], due_tick_cue: bool) -> tuple[SpawnResponse, ...]: ...
    def listen(self, sensor_id: int, callback) -> OperationResponse: ...
    def apply(self, commands: tuple[CommandRecord, ...]) -> tuple[OperationResponse, ...]: ...
    def tick(self, timeout_s: float) -> FrameRecord: ...
    def stop_listeners(self, ids: tuple[int, ...]) -> tuple[OperationResponse, ...]: ...
    def destroy(self, ids: tuple[int, ...], timeout_s: float) -> tuple[OperationResponse, ...]: ...
    def restore(self, ownership: OwnershipReceipt, timeout_s: float) -> OperationResponse: ...


@dataclass(frozen=True)
class RuntimeContext:
    backend: Backend | None
    identity: RuntimeIdentity
    ownership: OwnershipReceipt
    approvals: ApprovalBundle
    admission: AdmissionVerdict
    store: RunStore
    deadlines: Mapping[str, Number]
    scope_mode: str
    scope_phase: str


@dataclass(frozen=True)
class StockDriver:
    handle: object
    config: Mapping[str, object]
    hash: str


_RECORDS = {cls.__name__: cls for cls in (
    FieldError, SchemaErrors, SourceRef, ReviewRecord, Transform6, LaneRef, DirectedRoute,
    BodyRecord, Section, Domain, BoundCertificate, Sweep, ActorRecipe, ParameterProposal,
    FrozenResponse, Candidate, CandidateRevision, IdentityMethod, SiteRecord, SiteLedger,
    PolicyBundle, FrozenMetricPair, CapabilityProof, QueryBundle, CompiledFixture,
    ApprovalBundle, RuntimeIdentity, OwnershipReceipt, RunStore, PreparationRequest,
    ControlPacket, CommandRecord, ActorFrame, EventRecord, FrameRecord, ScriptState,
    ResponseState, MetricValue, ComparisonRecord, EpisodeVerdict, EpisodeEvidence,
    ABVerdict, EligibilityRecord, CatalogAudit, ReplacementTransaction, ReplacementLedger,
    ReplacementResult, ArtifactRef, IntegrityReport, AdmissionVerdict, BlockedPreparation,
    BlockedFixture, ReleaseBlocked, ExportReceipt, CampaignInputs, OwnedRegistry,
    CleanupReceipt, RunSummary, SpawnResponse, OperationResponse, SensorPacket,
    RuntimeContext, StockDriver,
)}


class _DecodeError(ValueError):
    def __init__(self, path, reason):
        self.error = FieldError(path, reason)
        super().__init__(reason)


def number(value: str | float | int) -> Number:
    if isinstance(value, bool):
        raise ValueError('BOOL_IS_NOT_NUMBER')
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('NONFINITE')
        return Fraction(*value.as_integer_ratio())
    if isinstance(value, (str, int, Decimal)):
        try:
            return Fraction(value)
        except (ValueError, OverflowError, ZeroDivisionError) as exc:
            raise ValueError('INVALID_NUMBER') from exc
    raise ValueError('INVALID_NUMBER')


def _decode(kind, value, path):
    origin, args = get_origin(kind), get_args(kind)
    if origin in (types.UnionType, Union):
        if value is None and type(None) in args:
            return None
        alternatives = [x for x in args if x is not type(None)]
        if len(alternatives) == 1:
            return _decode(alternatives[0], value, path)
        errors = []
        for option in alternatives:
            try:
                return _decode(option, value, path)
            except _DecodeError as exc:
                errors.append(exc)
        raise errors[0]
    if is_dataclass(kind):
        if not isinstance(value, dict):
            raise _DecodeError(path, 'EXPECTED_RECORD')
        definitions = {field.name: field for field in fields(kind)}
        unknown = set(value)-definitions.keys()
        if unknown:
            raise _DecodeError(f'{path}.{sorted(unknown)[0]}'.lstrip('.'), 'UNKNOWN_FIELD')
        hints = _type_hints(kind)
        output = {}
        for name, field in definitions.items():
            fieldpath = f'{path}.{name}'.lstrip('.')
            if name not in value:
                if field.default is MISSING and field.default_factory is MISSING:
                    raise _DecodeError(fieldpath, 'REQUIRED_FIELD')
                continue
            if kind is PreparationRequest and name == 'store' and value[name] is not None:
                raise _DecodeError(fieldpath, 'RUNTIME_ATTACHED_ONLY')
            if kind in (RuntimeContext, StockDriver) and name in ('backend', 'handle') and value[name] is not None:
                raise _DecodeError(fieldpath, 'RUNTIME_ATTACHED_ONLY')
            output[name] = _decode(hints[name], value[name], fieldpath)
        record = kind(**output)
        _validate(record, path)
        return record
    if origin is tuple:
        if not isinstance(value, (tuple, list)):
            raise _DecodeError(path, 'EXPECTED_SEQUENCE')
        if len(args) > 1 and args[1] is Ellipsis:
            return tuple(_decode(args[0], x, f'{path}[{i}]') for i, x in enumerate(value))
        if len(value) != len(args):
            raise _DecodeError(path, 'SEQUENCE_LENGTH')
        return tuple(_decode(k, v, f'{path}[{i}]') for i, (k, v) in enumerate(zip(args, value)))
    if origin in (dict, Mapping):
        if not isinstance(value, dict):
            raise _DecodeError(path, 'EXPECTED_MAPPING')
        return types.MappingProxyType({_decode(args[0], k, path): _decode(args[1], v, f'{path}.{k}'.lstrip('.')) for k, v in value.items()})
    if kind is Fraction:
        if isinstance(value, dict) and set(value) == {'numerator', 'denominator'}:
            if type(value['numerator']) is not int or type(value['denominator']) is not int:
                raise _DecodeError(path, 'RATIONAL_INTEGER_COMPONENTS')
            value = f"{value['numerator']}/{value['denominator']}"
        try:
            return number(value)
        except ValueError as exc:
            raise _DecodeError(path, str(exc)) from exc
    if kind is float:
        if isinstance(value, dict) and set(value) == {'binary64'}:
            try:
                value = float.fromhex(value['binary64'])
            except (TypeError, ValueError) as exc:
                raise _DecodeError(path, 'INVALID_BINARY64') from exc
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, Fraction)) or not math.isfinite(float(value)):
            raise _DecodeError(path, 'NONFINITE_OR_INVALID_FLOAT')
        return float(value)
    if isinstance(kind, type) and issubclass(kind, StrEnum):
        try:
            return kind(value)
        except (TypeError, ValueError) as exc:
            raise _DecodeError(path, 'UNKNOWN_STATUS_AXIS') from exc
    if kind in (int, str, bool):
        if type(value) is not kind:
            raise _DecodeError(path, 'TYPE_MISMATCH')
        return value
    if kind is Path:
        if not isinstance(value, str):
            raise _DecodeError(path, 'EXPECTED_PATH')
        return Path(value)
    if kind is object:
        # Extensible physics/source-packet/recipe payloads are data, never authority.
        if isinstance(value, dict):
            if set(value)=={'numerator','denominator'}:
                return _decode(Fraction,value,path)
            if set(value)=={'binary64'}:
                return _decode(float,value,path)
            return types.MappingProxyType({str(k): _decode(object, v, f'{path}.{k}') for k, v in value.items()})
        if isinstance(value, (tuple, list)):
            return tuple(_decode(object, v, f'{path}[{i}]') for i, v in enumerate(value))
        if isinstance(value, float) and not math.isfinite(value):
            raise _DecodeError(path, 'NONFINITE')
        if isinstance(value, Decimal):
            return str(value)
        if value is None or isinstance(value, (str, bool, int, float)):
            return value
        raise _DecodeError(path, 'INVALID_JSON_VALUE')
    if kind is Backend:
        if value is None:
            return None
        raise _DecodeError(path, 'RUNTIME_ATTACHED_ONLY')
    raise _DecodeError(path, 'UNSUPPORTED_SCHEMA_TYPE')


def _validate(record, path):
    def reject(field, reason):
        raise _DecodeError(f'{path}.{field}'.lstrip('.'), reason)
    for field in fields(record):
        value = getattr(record, field.name)
        if field.name in ('sha256', 'hash', 'source_hash', 'candidate_hash', 'policy_hash', 'object_hash', 'recipe_hash', 'old_hash', 'new_hash'):
            if value is not None and not re.fullmatch(r'[0-9a-f]{64}', value):
                reject(field.name, 'INVALID_SHA256')
    if isinstance(record, ActorRecipe):
        if record.role not in ('EGO', 'NPC'):
            reject('role', 'INVALID_ROLE')
        if record.initial_speed_mps != 0:
            reject('initial_speed_mps', 'INITIAL_SPEED_MUST_BE_ZERO')
    if isinstance(record, Candidate) and record.category not in ('C', 'I', 'L', 'M', 'O', 'F'):
        reject('category', 'INVALID_CATEGORY')
    if isinstance(record, ParameterProposal) and record.units not in ('m', 'm/s', 's', 'm/s^2', 'deg'):
        reject('units', 'UNSUPPORTED_UNIT')
    if isinstance(record, SourceRef) and record.bytes < 0:
        reject('bytes', 'NEGATIVE_SIZE')
    if isinstance(record, ControlPacket):
        for field in ('throttle', 'brake'):
            if not 0 <= getattr(record, field) <= 1:
                reject(field, 'CONTROL_RANGE')
        if not -1 <= record.steer <= 1:
            reject('steer', 'CONTROL_RANGE')
    if isinstance(record, BodyRecord) and any(v <= 0 for v in record.extents):
        reject('extents', 'NONPOSITIVE_EXTENT')
    if isinstance(record, DirectedRoute):
        if len(record.transforms) != len(record.arc) or len(record.arc) < 2 or any(b <= a for a, b in zip(record.arc, record.arc[1:])):
            reject('arc', 'INVALID_DIRECTED_ARC')
    if isinstance(record, CompiledFixture):
        if set(record.poses) != {'EGO', 'NPC'} or set(record.routes) != {'EGO', 'NPC'} or any(actor.pose is None for actor in record.actors):
            reject('poses', 'MATERIALIZATION_REQUIRED')
    if isinstance(record, ReplacementLedger) and (record.used < 0 or record.used != len(record.transactions)):
        reject('used', 'LEDGER_COUNTER_MISMATCH')


def decode_record(schema_name: str, payload: dict[str, object]) -> object | SchemaErrors:
    if schema_name not in _RECORDS:
        return SchemaErrors((FieldError('', 'UNKNOWN_SCHEMA_KIND'),))
    try:
        return _decode(_RECORDS[schema_name], payload, '')
    except _DecodeError as exc:
        return SchemaErrors((exc.error,))


def decode_revision(payload: dict[str, object]) -> CandidateRevision | SchemaErrors:
    return decode_record('CandidateRevision', payload)


def _encode_typed(value, kind):
    origin,args=get_origin(kind),get_args(kind)
    if kind is float:
        if isinstance(value,bool) or not isinstance(value,(int,float,Fraction,Decimal)):
            raise ValueError('INVALID_FLOAT_FIELD')
        return encode_record(float(value))
    if kind is Fraction:
        return encode_record(number(value))
    if origin in (types.UnionType,Union):
        if value is None:
            return None
        alternatives=[option for option in args if option is not type(None)]
        if len(alternatives)==1:
            return _encode_typed(value,alternatives[0])
    if origin is tuple:
        if len(args)>1 and args[1] is Ellipsis:
            return [_encode_typed(v,args[0]) for v in value]
        if len(value)!=len(args):
            raise ValueError('SEQUENCE_LENGTH')
        return [_encode_typed(v,k) for v,k in zip(value,args)]
    if origin in (dict,Mapping):
        return {k:_encode_typed(v,args[1]) for k,v in value.items()}
    return encode_record(value)


def encode_record(record: object) -> dict[str, object]:
    if isinstance(record, Fraction):
        return {'numerator': record.numerator, 'denominator': record.denominator}
    if is_dataclass(record):
        hints=_type_hints(type(record))
        return {f.name: _encode_typed(getattr(record,f.name),hints[f.name]) for f in fields(record)}
    if isinstance(record, Mapping):
        return {k: encode_record(v) for k, v in record.items()}
    if isinstance(record, (tuple, list)):
        return [encode_record(v) for v in record]
    if isinstance(record, float):
        if not math.isfinite(record):
            raise ValueError('NONFINITE')
        return {'binary64': record.hex()}
    if isinstance(record, Path):
        return str(record)
    if record is None or isinstance(record, (str, int, bool)):
        return record
    raise ValueError('UNSERIALIZABLE_RUNTIME_OBJECT')


def load_json(path: Path) -> object:
    def invalid_constant(value):
        raise ValueError(f'NONFINITE_JSON:{value}')
    return json.loads(path.read_text(encoding='utf-8'), parse_float=Decimal,
                      parse_constant=invalid_constant)
