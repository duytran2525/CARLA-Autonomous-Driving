# M56 runtime proof contract (T12/T13)

Status 2026-10-20: author self-review. Offline tests: `tests/m56/test_runtime.py`, `tests/m56/test_runtime_owned.py`.
Native evidence so far: one read-only preflight (`outputs/m56_native_preflight_v1_20261020T041845Z`). The owned
spawn/tick/destroy adapter is written but has **never executed natively**; it needs an approved probe charter.

## Admission order (m56/runtime.py)

Every check runs before `_native_factory`, the only place that imports `carla`.

1. **Authority** → `BLOCKED_AUTHORITY`: every requested op is in both `ApprovalBundle.allowed_scopes` and
   `OwnershipReceipt.allowed_ops`; approval receipts exist and none is `SYNTHETIC*`; an owned `RunStore` is
   attached; non-read ops need a `charter_ref`. A preparation/probe receipt never admits `VALIDATE_AB`.
2. **Ownership** → `BLOCKED_OWNERSHIP`: loopback host, explicit RPC port, tick owner == writer == store writer,
   receipt boot/world == environment; after bind, live boot/world/map must equal the receipt.
3. **Source** → `BLOCKED_SOURCE`: client/server 0.9.16, Python 3.12.10, module hashes == recorded hashes,
   stock `basic_agent`/`local_planner`/`controller` == the plan's pinned SHA256.
4. Query: a missing `vehicle.audi.a2` blueprint is `BLOCKED_CAPABILITY`; no substitute vehicle.

## Backend boundary

```text
Backend.identity() -> RuntimeIdentity
Backend.query(request:PreparationRequest) -> QueryBundle
Backend.spawn(actors:tuple[ActorRecipe,...],due_tick_cue:bool) -> tuple[SpawnResponse,...]
Backend.listen(sensor_id:int,callback:Callable[[SensorPacket],None]) -> OperationResponse
Backend.apply(commands:tuple[CommandRecord,...]) -> tuple[OperationResponse,...]
Backend.tick(timeout_s:float) -> FrameRecord
Backend.stop_listeners(ids:tuple[int,...]) -> tuple[OperationResponse,...]
Backend.destroy(ids:tuple[int,...],timeout_s:float) -> tuple[OperationResponse,...]
Backend.restore(ownership:OwnershipReceipt,timeout_s:float) -> OperationResponse
```

`ReadOnlyCarlaBackend` implements `identity`/`query` only. `OwnedCarlaBackend` adds the T13 methods.

## Owned kernels (T13)

- `spawn_owned`: one batch with `due_tick_cue=False`; each success is registered in `owned/registry.jsonl`
  before anything moves. A missing or erroring response gives `EpisodeVerdict(spawn=FAILED)` with
  `SPAWN_ID_UNKNOWN`/`SPAWN_ERROR:<role>`: no movement, no respawn, no fallback. Sensor listeners attach before any tick.
- `tick_owned`: only owned actors receive commands. Another writer gives physical `FAILED`/witness `INVALID`.
  A foreign actor, world change or tick gap gives witness `INVALID`. Issued commands are never used as observations.
- `cleanup_owned`: matching boot/world only; stop listeners, then destroy sensors, then vehicles, in one pass
  bounded by `cleanup_s` (default 15 s). Error survivors give `ESCALATED`. A spent deadline or a lost world gives
  `BLOCKED_CLEANUP` with survivors listed. No retry, kill or server restart. `restore` runs only at
  `scope_phase=ENDING` with the `RESTORE` scope.

## Capability proofs

`verify_capability`: raw refs must come from this `QueryBundle` and carry an `APPROVED` review, else
`WITNESS_UNCERTAIN`. A boolean or synthetic raw is never proof. Stock 0.9.16 has no getter for wheel contact,
door collider, mechanical gear or collision-stream completeness, so those kinds return `BLOCKED_CAPABILITY`
until a separately reviewed recipe exists.
