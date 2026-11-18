# M56 addendum U: F05 native (product m56-v18 + tooling), 18/11/2026

**Label:** CLAUDE_REVIEW_UNDER_DUY_DELEGATION, not independent. Written **before** any native F05 number (F05 has never
been prepared). It extends addendum T (`PREREG_M56_F05_ADDENDUM_T_20261118.md`).

**Authority:** the user in this session, [chat] 17/11 "làm F05/F06, F03/F04 và nhóm M" and [chat] 18/11 "làm hết cho tôi";
memory 2026-11-10 (Duy away: decide per own recommendations). Claude decides under Duy's delegation.

## 1. Two exact rules that block B natively (found by reading v18 before any F05 number)

| Where | v18 rule (OLD RULE) | Why it can never hold natively |
|---|---|---|
| `metrics._f05_creep_events` (EGO_CREEP_STOP_CONFIRMED) | `progress == 1 and continuous.uncertainty == 0` | A physical stop is never at exactly 1 m. The runtime's CONTINUOUS_GEOMETRY uncertainty is always 1/1000 (`runtime._bound_frame`). |
| `metrics._f_queue_action` (B physical state) | creep `reach` = first frame with `progress == 1` | Same: no frame is at exactly 1 m, so it always fails `CREEP_STOP_NOT_CONFIRMED`. |

Without the change, B never reaches FORWARD (it needs EGO_CREEP_STOP_CONFIRMED), and the evaluator always fails it.

**New rules (m56-v18):**

- `_creep_stop_within(progress, unc)`: the stop hold counts once the stopping bound has fired and
  `progress + unc <= 1`, i.e. inside the 1 m reservation.
- `_creep_reach(progress, frame, events)`: "reach" starts at the observed `EGO_CREEP_STOPPING_BOUND` frame, while
  `progress <= 1`. The hold from there to the release must contain an observed stop, as before.
- Old rules are kept: `_creep_stop_old_rule`, and `progress == 1` when the event is absent. Every F05 result is reported
  under both. Under the old rules B is always FAILED / blocked natively; this is a statement, not a measurement.
- Tests: `tests/m56/test_v18_creep_stop_within.py`. The F05 synthetic suite still passes (120 tests, plus a rerun of
  the evaluator tests).

## 2. Runtime hook (m56-v18)

`runtime._bound_frame`: if the kit has `seal_frame`, it gets the finished record and may add integrity fields.
Kits without `seal_frame` behave byte-identically.

## 3. Native facts checked before writing (sealed data, read-only)

- **TRIGGER needs `min_front_gap == queue_gap_m` exactly for ≥ 1 s.**
  - Parked CARLA vehicles become bit-identical after ~15 frames and stay so (up to 1127 frames in C07-S1 A).
  - A and B settle identically (F01-S1, F01-S2, F02).
  - The F02 prepare probe and the F02 A/B (two sessions) give bit-identical poses from frame 15 on.
  - So `queue_gap_m` is the exact settled gap measured by the prepare; two settle probes must agree.
- **Ground:** native ground error + uncertainty is at most 0.040 m on sealed F frames, within the 0.05 m limit.
- **Body hash:** the runtime-observed body differs from the prepare bbox in the 5th decimal. It is identical between the
  prepare probe and the A/B for the same spawn pose. So CREEP_STOP_BOUND binds the probe-observed EGO body.

## 4. Tooling (new code paths; F01/F02 unchanged)

1. **Revision:** `native-v5-revision.py` gets `f05_recipe` (the approved test programs `f05_ego_a` / `f05_ego_b` on the
   site route). It is gated by `M56_ASEL2_F05=1`, so other revisions stay byte-identical. Sites:
   `m56_f_sites_replace_f01_v3_20261114.json`, entry `M56-P-F05`, Town12 R164 lane −2.
2. **Prepare:** `native-f-prepare.py` `prepare_f05`.
   - EGO at the section entry + 1 m. NPC ahead with body gap d0 = 4 m (band 0.3 m, at most one corrective probe).
   - Two settle probes: both at 0, the gap constant over ≥ 40 frames, and both probes giving the identical value.
   - Readiness at rest via `first_ready`.
   - `nominal_front_t0_m` = settled EGO front; F05_END = front + 10; DESTINATION = front + 16.
3. **CREEP_STOP_BOUND calibration:** four creep probes on the frozen poses. EGO CREEP 1/2, then target 0 after T ∈
   {0.8, 1.2, 1.6, 2.0} s, through the product's own stock driver.
   - `stopping_distance_bound_m = ceil_0.01(max stop distance) + 0.05`.
   - `maximum_forward_speed_mps = max(1/2, ceil_0.01(max peak) + 0.10)`.
   - Uncertainty 1/100.
   - `stopping_boundary_m = 1 − bound − 1/100 − 1/100`.
   - Blocked if the boundary is ≤ 0.2 m.
   - This is a measured bound, not a certificate.
4. **Compile** (`native-f-ab.py`), in two passes. The proof binds the pass-1 recipe, response, route, body and stock
   hashes; pass 2 must keep the same recipe hash. RUNIN_ROOM for the standing queue: required = 0.1 m (readiness
   tolerance), reference = F05_END.
5. **Kit** (`native_f05_kit.F05Kit`, B episode only), per frame:
   - QUEUE_PATH: min front gap on the EGO route, floored to 1e-4 m;
   - `creep_fixture_ref`;
   - `creep_history_ref`: every row of the episode so far, each row keeping only `frame_refs`, `continuous_geometry`,
     `validation_start` and `queue_path`, as the synthetic producer does.
   - Offline check `test-f05-kit-offline.py`: the synthetic B episode, with its creep fields removed, is regenerated by
     the kit and run through the product's `step_response`.
6. **Chain:** `run-f05-u.sh`, with the cguard room before every CARLA start.
   - Stage 1: prepare → revision → compile/admission.
   - Stage 2: **one** A/B (P5), pair under v18 and under v13 (old rules).

## 5. Stop rules

- A blocked prepare or compile is recorded as measured: no threshold change, and no rerun with other values.
- A spent A/B is never rerun (P5).
