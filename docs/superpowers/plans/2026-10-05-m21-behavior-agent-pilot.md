# M21 BehaviorAgent Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bổ sung mode M21 chạy pilot normal 30 raw episodes/20 paired observations với ego controller cũ, provenance từng run và phép đo mô tả, đồng thời chứng minh output phân tích legacy trên 720 TM runs không đổi.

**Architecture:** Giữ nguyên các module legacy, đặt adapter runner, protocol, provenance và measurement M21 trong package riêng; CLI cũ chỉ thêm nhánh dispatch mặc định-off. Capture baseline trước thay đổi feature, tái dùng fixture/controller/serialization legacy và BehaviorAgent nguyên bản. Mode M21 không có bộ phân loại đạt/rớt hoặc full-matrix runner trong phase này.

**Tech Stack:** Python hiện có trong môi trường dự án, CARLA client/server 0.9.16, CARLA agents từ `E:/Carla/PythonAPI/carla`, NumPy, pandas, PyYAML, pytest; pathlib/hashlib/json/csv/subprocess từ standard library. Không nâng cấp dependency để làm task này.

**Spec:** `docs/superpowers/specs/2026-10-05-m21-behavior-agent-pilot-design.md` (commit `e4dc6a3`; người dùng đã duyệt spec và pilot 30 episodes khi yêu cầu viết plan).

## Global Constraints

- Giữ nguyên controller ego cũ và chế độ phân tích cũ; được bổ sung mode M21 trong pipeline hiện có.
- Regression check: sau thay đổi, phân tích cũ trên đúng 720 run `tm_default` hiện có phải cho output giống hệt trước sửa.
- Manifest phải ghi sync mode, seed, CARLA version, GPU, session id; lưu quỹ đạo thô từng tick.
- Seed theo `(cảnh, rep, phiên)`, dùng chung cho mọi intent trong cảnh; bỏ `cặp` khỏi tuple seed.
- Town03, ClearNoon, fixed delta 0.05, no rendering=true, reload_world_each_run=true; đèn frozen theo `SceneSpec.traffic_light_state` (catalog hiện là Green).
- `BehaviorAgent(vehicle, behavior='normal')` với thông số mặc định, không sửa mã agent, không gọi ignore-lights, không chỉnh tốc độ/PID/safety/tailgating.
- Không xuất CI để kết luận, scene/type response label, pass count hoặc overall decision trong phase này.
- `protocol_status=pending`; không tự chọn mean/median hay cách gộp phiên để lấp phần thống kê còn thiếu.
- Pilot là 30 raw episodes để tạo đúng 20 paired observations trong một phiên; không tự chạy hết sau khi pilot xong.
- Giữ byte của `controllers.py`, `runner.py`, `scenario_catalog.py`, `metrics.py`, `report.py` và catalog/config legacy.
- Không reset, xóa, định dạng lại hoặc gom các file của người dùng vào commit của phần việc mới. Không dùng executor/lớp an toàn M55 trong M21.

## Review Focus

1. Report legacy đổi provenance dù số đo giống nhau: so SHA-256 cả CSV/JSON/Markdown và inventory, không chuẩn hóa nội dung (Task 1, Task 7).
2. Intent chờ/không làm bị đặt marker trễ hoặc lệch một tick: t=0 là kích hoạt intent chung, trước control/tick đầu tiên, không phải lúc xe chuyển động (Task 6).
3. Collision callback đến trễ hơn state flag: lấy event.frame và cắt cả hai quỹ đạo theo frame sớm nhất, không đo impulse hậu va chạm (Task 4, Task 6).
4. Đổi session ID nhưng cùng server boot hoặc resume dữ liệu bị sửa: không coi đổi tên/reload_world là phiên độc lập, không ghi đè complete cell khác hash (Task 3, Task 7).
5. Chỉ biết GPU có mặt hoặc thiếu noise calibration: ghi GPU unknown có lý do/onset null, không suy ra GPU đang dùng hoặc chế ngưỡng noise (Task 3, Task 4, Task 7).

---

## Phạm vi, workspace và file map

Đây là plan **pilot M21**, không phải plan M55 hoặc triển khai thống kê full. Spec §5 bảo toàn toàn bộ cặp/gradient/CI 98.3%/bootstrap 2000/tiêu chí cảnh-loại-toàn bài; những mục đó được chặn bởi Task 7, không triển khai classifier trước khi Dũng chốt estimator, gộp phiên, noise sampling và censoring conventions.

Trước execution dùng skill using-git-worktrees. Workspace hiện có pipeline/config/tests legacy chưa được track: worktree thông thường không chứa các dependency này. Chụp hashes và chỉ copy đúng dependency cần thiết sang workspace cô lập, không copy `.git`/venv/outputs lớn và không reset workspace gốc. **Cổng ownership:** trước commit có sửa CLI legacy, owner phải cung cấp baseline đã track hoặc phê duyệt riêng việc import dependency legacy vào baseline; không silently stage cả file untracked của người dùng. Nếu chưa có phê duyệt đó, vẫn có thể capture evidence/viết các module mới nhưng báo blocker cho commit CLI. Lệnh commit bên dưới giả định cổng này đã được xử lý; mỗi commit chỉ stage đường dẫn task chỉ định.

Giữ input TM ở workspace gốc bằng đường dẫn tuyệt đối khi worktree không có outputs. Dùng cùng Python executable/env cho cả baseline và regression, ghi `python --version` và package versions, không install/nâng cấp trong giữa hai lần.

| File tạo/sửa | Trách nhiệm |
|---|---|
| `scripts/check_m21_legacy_regression.py` | Capture/compare output legacy thực, không sửa analyzer |
| `experiments/ego_intent_response/m21/__init__.py` | Package nhẹ, không import agent/CARLA trong import package |
| `.../m21/protocol.py` | Config, cặp intent, cell schedule, seed và error type |
| `.../m21/provenance.py` | Session/software/GPU/config hashes, paths, raw integrity, load/finalize |
| `.../m21/measurements.py` | Tick alignment, max differences, supplied-noise/onset primitives |
| `.../m21/agent.py` | BehaviorAgent đúng nguồn, pinned global plan và route validation |
| `.../m21/runner.py` | Adapter fixture legacy, marker, controls/raw/events và attempts |
| `.../m21/report.py` | Diagnostic CSV/timing/quality, không decision labels |
| `.../m21/cli.py` | Điều phối pilot/preflight/analyze-only/resume và pending gate |
| `scripts/run_ego_intent_response.py:37-57,235-238` | Argument parsing và dispatch sớm sang M21; không đổi thân legacy analysis |
| `tests/test_m21_legacy_regression.py`, `tests/test_m21_protocol.py`, `tests/test_m21_provenance.py`, `tests/test_m21_measurements.py`, `tests/test_m21_agent.py`, `tests/test_m21_runner.py`, `tests/test_m21_cli.py`, `tests/test_m21_carla.py` | Test đúng module/flow tương ứng |
| `tests/m21_helpers.py` | Episode/fake-world fixtures dùng chung, không phải controller mới |
| `docs/superpowers/runbooks/2026-10-05-m21-pilot.md` | Lệnh vận hành, schema/units, evidence links và blockers thực tế |

`...` trong bảng là `experiments/ego_intent_response`; Files của từng task bên dưới dùng đường dẫn đầy đủ. Không tạo framework NPC/controller/plugin chung.

### Task 1: Capture baseline và harness hồi quy byte-for-byte

**Files:**
- Create: `scripts/check_m21_legacy_regression.py`
- Test: `tests/test_m21_legacy_regression.py`
- Evidence: `outputs/m21_legacy_regression/{stage,before,after,default_vs_explicit}/`

**Interfaces:**
- Consumes: legacy CLI `--analyze-only --profile tm_default --bootstrap-samples 2000 --permutation-samples 2000`; `implementation_hash() -> str`, `load_catalog(path) -> ScenarioCatalog`.
- Produces: `capture_baseline(source_root: Path, evidence_root: Path) -> None`; `compare_artifacts(before: Path, after: Path) -> dict[str, bool]`; `compare_baseline(evidence_root: Path, *, explicit_mode: bool = False) -> dict[str, bool]`; CLI `capture --source PATH --evidence PATH` / `compare --evidence PATH [--explicit-mode]`, exits 0 iff all checks pass, 2 on mismatch/error.

- [ ] **Step 1: Write failing tests for exact comparison and protected inputs.** In `tests/test_m21_legacy_regression.py`, define `test_inventory_and_provenance_are_not_normalized`: create before/after inventories with identical CSV bytes but `decision.json` differing only in provenance hash, assert comparison reports `decision.json=False`; remove a report and add a new report, assert both mismatches reported. Define `test_capture_rejects_incomplete_or_changed_raw`: invalid status, raw SHA mismatch, duplicate cell, missing rep or wrong catalog/config each raises before subprocess analysis. Fake subprocess fixtures must write known artifact bytes; assert source bytes unchanged and second capture refuses replacing existing baseline. Pin the byte comparison itself as code:
```python
def test_inventory_and_provenance_are_not_normalized(tmp_path):
    before, after = tmp_path / 'before', tmp_path / 'after'
    before.mkdir(); after.mkdir()
    (before / 'decision.json').write_text('{"provenance":{"hash":"old"}}')
    (after / 'decision.json').write_text('{"provenance":{"hash":"new"}}')
    (before / 'summary_by_scene.csv').write_text('same,data\n')
    (after / 'summary_by_scene.csv').write_text('same,data\n')
    assert compare_artifacts(before, after) == {
        'decision.json': False, 'summary_by_scene.csv': True}
    (before / 'response_report.md').write_text('missing afterwards')
    (after / 'extra.csv').write_text('unexpected')
    results = compare_artifacts(before, after)
    assert results['response_report.md'] is False and results['extra.csv'] is False
```

- [ ] **Step 2: Run failing tests.** `python -m pytest tests/test_m21_legacy_regression.py -q` → FAIL importing missing harness/functions, not an environment failure.

- [ ] **Step 3: Implement the capture/compare signatures in `scripts/check_m21_legacy_regression.py`.** Copy only `runs/tm_default` and `audits/tm_default` into fixed `evidence_root/stage`, never symlink writable raw to original. Validate exactly 24 ×3 ×10 distinct completed cells, metadata hashes/catalog/effective hash and legacy implementation hash `d3e3b9dea51124558cf1216a2a6f121a7c1bfcf2802f3bcb8168736830aa5b34`. Capture source/raw/config/package inventories. Use `sys.executable` to run the unchanged CLI with `--output-dir` pointing to that same stage path in both passes; preserve the stage path because provenance and audit CSV include paths. Snapshot generated root artifacts plus their inventory before/after, not copied legacy full-profile reports. Compare bytes/SHA-256 including provenance; no rounding, row sorting or excluded content. Include the seven always-generated files in spec §7 and `baseline_failure_notice.md` iff generated. Persist `comparison.json` with per-file before/after hashes and missing/extra files outside the stage artifact inventory.

- [ ] **Step 4: Run unit tests.** Same command → PASS; tampering/missing/extra fixtures correctly reject equality.

- [ ] **Step 5: Capture the real 720-run baseline before Tasks 2–7.** From original root:
```powershell
python scripts/check_m21_legacy_regression.py capture --source outputs/ego_intent_response --evidence outputs/m21_legacy_regression
```
Expected: exit 0; 720 eligible observations, 12 TM audit raw files, input/source inventory and immutable `before/` artifacts saved. In a worktree pass the original outputs absolute path. If any hash/env/coverage mismatch occurs, stop and report; do not bless a new baseline after feature changes.

- [ ] **Step 6: Commit harness/tests only.** `git add scripts/check_m21_legacy_regression.py tests/test_m21_legacy_regression.py` then `git commit -m "test: capture byte-exact legacy M21 regression baseline"`. Raw/evidence remain git-ignored.

### Task 2: Protocol, matched seeds và schedule pilot

**Files:**
- Create: `experiments/ego_intent_response/m21/__init__.py`, `experiments/ego_intent_response/m21/protocol.py`
- Test: `tests/test_m21_protocol.py`

**Interfaces:**
- Consumes: legacy `ExperimentConfig`, `ScenarioCatalog`, `seed_for(base_seed: int, scene_index: int, repeat: int) -> int`.
- Produces frozen dataclasses: `M21Config(experiment: ExperimentConfig, agents_root: Path, output_root: Path, session_id: str, session_index: int, restart_evidence: dict[str, Any], protocol_status: str = 'pending', behavior_profile: str = 'normal')`; `RunCell(scene_id: str, scene_index: int, intent_id: str, rep: int, session_id: str, session_index: int, seed: int)`; `IntentPair(pair_id: str, intent_a: str, intent_b: str)`.
- Produces: `M21Error(ExperimentError)`; `seed_for_m21(scene_index: int, rep: int, session_index: int) -> int`; `validate_config(config: M21Config) -> None`; `pairs_for(category: str) -> tuple[IntentPair, ...]`; `pilot_cells(catalog: ScenarioCatalog, config: M21Config) -> list[RunCell]`.

- [ ] **Step 1: Write failing tests with the pinned values.**
```python
def test_seed_and_pilot_schedule():
    assert seed_for_m21(12, 1, 0) == 21_012_001
    assert seed_for_m21(12, 1, 1) == 22_012_001
    catalog = load_catalog('configs/ego_intent_response_town03_scenes.yaml')
    config = M21Config(ExperimentConfig(), Path('E:/Carla/PythonAPI/carla'),
                       Path('outputs/test'), 's0', 0, {'boot_token': 'boot-0'})
    cells = pilot_cells(catalog, config)
    assert len(cells) == 30
    assert {c.scene_id for c in cells} == {'crossing_01'}
    assert len({c.seed for c in cells}) == 10
    assert all(len({c.seed for c in cells if c.rep == r}) == 1 for r in range(1, 11))
    assert [(p.intent_a, p.intent_b) for p in pairs_for('cross_traffic')][:2] == [
        ('go_now', 'stop_before_crossing'), ('go_now', 'yield_then_go')]
```
Also name/assert `test_filter_does_not_renumber_scene_seed` (crossing index remains 12), `test_invalid_seed_and_session_values_rejected` (negative session, rep 0/11, scene -1/24, uint32 overflow, unsafe session path), and `test_pending_gate_rejects_non_normal_or_non_pilot_config` (profile aggressive or claimed approved status raises). Assert six categories' three pair tuples equal spec §5 table.

- [ ] **Step 2: Run tests red.** `python -m pytest tests/test_m21_protocol.py -q` → missing M21 package/functions FAIL.

- [ ] **Step 3: Implement the declared interfaces.** Seed = `21_000_000 + session_index*1_000_000 + seed_for(0, scene_index, rep)`, with scene 0..23, rep 1..10, session ≥0 and final seed ≤`2**32-1`. Session IDs allow only `[A-Za-z0-9_-]+`. Register pair IDs `p1/p2/p3` in spec order. Schedule loops rep then catalog intent order for crossing_01 only; duplicates of logical cell are errors, shared seeds across its intents intentional. Enforce actual experiment constraints: Town03/0.05/no_rendering/reload, run duration 14.0 s, default normal/pending, output root not legacy output directory or a descendant. Package `__init__.py` stays import-light.

- [ ] **Step 4: Run tests green.** Same command → PASS; no import of CARLA agents required.

- [ ] **Step 5: Commit.** `git add experiments/ego_intent_response/m21/__init__.py experiments/ego_intent_response/m21/protocol.py tests/test_m21_protocol.py` then `git commit -m "feat: define matched-seed M21 pilot protocol"`.

### Task 3: Session provenance, integrity và reusable episode records

**Files:**
- Create: `experiments/ego_intent_response/m21/provenance.py`, `tests/m21_helpers.py`
- Test: `tests/test_m21_provenance.py`

**Interfaces:**
- Consumes Task 2 types and legacy `config_hash(value) -> str`, `simulation_config(config) -> dict`, `read_complete_state_files(output_dir, *, catalog_hash=None, configuration_hash=None) -> DataFrame`.
- Produces dataclasses `RunPaths(states: Path, events: Path, metadata: Path)` and `Episode(states: pd.DataFrame, events: list[dict[str, Any]], metadata: dict[str, Any])`.
- Produces `episode_paths(root: Path, cell: RunCell, *, attempt: int | None = None) -> RunPaths`; `collect_gpu_provenance() -> dict[str, Any]`; `collect_provenance(environment: CarlaExperimentWorld, config: M21Config) -> dict[str, Any]`; `m21_implementation_hash(agents_root: Path) -> str`; `register_session(root: Path, config: M21Config, provenance: dict[str, Any]) -> None`; `finalize_episode(paths: RunPaths, metadata: dict[str, Any]) -> None`; `load_episode(paths: RunPaths, *, expected: dict[str, str] | None = None) -> Episode`.
- Test helper `make_episode(*, x: np.ndarray, y: np.ndarray, speed: np.ndarray, intent: str = 'a', seed: int = 1, collision_tick: int | None = None, marker_tick: int = 60, run_id: str = 'run-a') -> Episode`: creates NPC+ego rows, ticks `marker_tick + arange(n)`, dt .05, common scene `synthetic`, rep 1/session `s0`, explicit marker and optional collision; ego initially 5 m behind NPC, same supplied speed. Use `from m21_helpers import make_episode` in pytest tests.

- [ ] **Step 1: Write failing tests for provenance truthfulness and persisted integrity.** `test_gpu_inventory_is_not_renderer_evidence`: mock nvidia-smi inventory but no CARLA renderer evidence; assert inventory stored and `renderer_device='unknown'` with nonempty reason. `test_requested_sync_must_match_observed`: requested .05/true versus observed .1/false raises. `test_session_rename_is_not_new_boot`: same boot_token under a new session ID cannot assert independent session; duplicate session_index with different ID raises. `test_episode_integrity_checks_events_and_identity`: write raw/events, finalize/load succeeds; tamper events/raw, change expected config/catalog/session hash or duplicate state tick, assert M21Error; incomplete metadata cannot load. Assert canonical paths include session and no traversal. Primary GPU assertion (mock subprocess.run returning one inventory row, with no renderer evidence):
```python
def test_gpu_inventory_is_not_renderer_evidence(monkeypatch):
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k:
        SimpleNamespace(returncode=0, stdout='GPU-test, GPU-uuid, 999.0\n', stderr=''))
    gpu = collect_gpu_provenance()
    assert len(gpu['inventory']) == 1
    assert gpu['renderer_device'] == 'unknown' and gpu['reason']
```
For session tests, register session s0/index0/boot-0, then s1/index1/boot-0; read `root/sessions/s1/session_manifest.json` and assert `independence_verified is False`. Attempt s2/index0/boot-1 and assert `pytest.raises(M21Error)`.

- [ ] **Step 2: Run tests red.** `python -m pytest tests/test_m21_provenance.py -q` → missing interfaces FAIL.

- [ ] **Step 3: Implement the declared interfaces and test helper.** Canonical layout: `root/sessions/<session_id>/runs/normal/<scene>/<intent>/rep_XX/{states.csv,events.jsonl,metadata.json}`; attempt artifacts add `attempts/attempt_XX/` below that rep directory. This preserves the legacy loader glob inside each session; pre-validate M21 hashes/events before using that loader, never let its skip-invalid behavior hide corrupted canonical data. Complete metadata written atomically only after raw/events flush; include schema_version=1, run_id, scene_id, intent, repeat, session_id/index, seed, catalog_hash, config_hash, implementation_hash, states_sha256, events_sha256, initial states and provenance. `expected` keys are required equality checks when supplied. Configuration hash covers observation settings/source hashes, schema, fixed normal/pending and diagnostic conventions, not host/port/output path.

`collect_provenance` records requested and observed world/substep/weather/light settings, client/server versions, map/OpenDRIVE, GPU inventory/renderer evidence, Python/packages and session restart evidence. Require matching 0.9.16 client/server; missing API/server is a surfaced M21Error. GPU unknown is a warning with reason, not an invented UUID. GPU result keys are `inventory` (list of name/uuid/driver dictionaries), `renderer_device` (str), `reason` (str). Query `nvidia-smi --query-gpu=name,uuid,driver_version --format=csv,noheader` without shell and with a 5 s timeout. Hash M21 modules, CLI, reused legacy modules and all Python files under configured `agents/`; record per-file hashes and actual module origins later from Task 5. UTC/machine/GPU labels never seed RNGs. Session registry is `root/session_registry.json`; each `root/sessions/<id>/session_manifest.json` includes PID/start time or operator boot-token evidence and explicit `independence_verified` boolean, never infers restart from CARLA frame reset alone. The first observed boot records a baseline, not proof of multiple independent sessions; a new session using the same known boot records false.

- [ ] **Step 4: Run tests green.** Same command → PASS; missing nvidia-smi does not crash offline unit tests, and no integrity mismatch is accepted.

- [ ] **Step 5: Commit.** `git add experiments/ego_intent_response/m21/provenance.py tests/m21_helpers.py tests/test_m21_provenance.py` then `git commit -m "feat: persist M21 session provenance and raw integrity"`.

### Task 4: Deterministic descriptive measurement primitives

**Files:**
- Create: `experiments/ego_intent_response/m21/measurements.py`
- Test: `tests/test_m21_measurements.py`

**Interfaces:**
- Consumes `Episode`, `IntentPair`, `M21Error` and Task 3 test helper.
- Produces dataclass `PairDiagnostics` with fields: `scene_id, pair_id, intent_a, intent_b, rep, session, seed, collision, first_collision_tick, max_pos_diff_m, max_vel_diff_m, onset_tick, run_id_a, run_id_b, window_ticks, available_duration_s, last_sample_time_s, quality_status, reason, protocol_status, include_collision_tick`. IDs/reasons/status are str, rep/seed/window_ticks int, collision/policy bool; first_collision_tick/onset_tick `int | None`, scalar measures/durations `float | None`. Collision/onset ticks are relative to marker, not global frame.
- Produces `measure_pair(a: Episode, b: Episode, pair: IntentPair, *, include_collision_tick: bool, noise_t: np.ndarray | None = None) -> PairDiagnostics`; `onset_tick(position_difference_m: np.ndarray, noise_t: np.ndarray) -> int | None`; `noise_statistics(pairs: Sequence[tuple[Episode, Episode]], *, include_collision_tick: bool, quantile_method: str) -> dict[str, Any]`; `descriptive_spreads(samples: Sequence[PairDiagnostics], *, ddof: int) -> dict[str, float | None]`; `ego_context(a: Episode, b: Episode, onset: int) -> dict[str, float]`.

- [ ] **Step 1: Write failing tests with known trajectories.**
```python
def test_max_difference_is_not_rmse_and_onset_starts_at_first_tick():
    a = make_episode(x=np.zeros(161), y=np.zeros(161), speed=np.full(161, 5.0))
    bx, by = np.zeros(161), np.zeros(161)
    bx[10], by[10] = 3.0, 4.0
    b = make_episode(x=bx, y=by, speed=np.full(161, 7.0),
                     intent='b', run_id='run-b')
    d = measure_pair(a, b, IntentPair('p1', 'a', 'b'), include_collision_tick=False)
    assert d.max_pos_diff_m == 5.0 and d.max_vel_diff_m == 2.0
    assert d.window_ticks == 161 and d.available_duration_s == 8.0
    assert d.onset_tick is None and d.protocol_status == 'pending'
    assert onset_tick(np.array([0.0] * 3 + [0.2] * 10), np.zeros(13)) == 3
    assert onset_tick(np.array([0.2] * 9), np.zeros(9)) is None
```
Add `test_common_collision_frame_beats_late_flags`: A collision at tick 70, B at 90, flags still false; a huge position difference at tick 70+ is excluded with policy false; assert first_collision_tick=70, window_ticks=70, available_duration_s=3.5, last_sample_time_s=3.45. Pin tick 80 → duration 4.0 versus last sample 3.95, not a fabricated final cell label. Add `test_missing_duplicate_nonfinite_or_unmatched_data_rejected`, `test_noise_requires_same_action_distinct_independent_records`, `test_strict_onset_threshold_and_null_noise`, `test_sample_spread_and_ego_context`: noise linear p90 of constant differences [1,2] is 1.9, speed differences [2,4] gives 3.8; SD [1,3] with ddof=1 is sqrt(2); identical ego trajectories give signed speed/distance differences 0. Explicit late-collision assertion:
```python
def test_common_collision_frame_beats_late_flags():
    a = make_episode(x=np.zeros(161), y=np.zeros(161), speed=np.ones(161), collision_tick=70)
    bx = np.zeros(161); bx[70:] = 100.0
    b = make_episode(x=bx, y=np.zeros(161), speed=np.ones(161), intent='b',
                     run_id='run-b', collision_tick=90)
    a.states['collision'] = False; b.states['collision'] = False
    d = measure_pair(a, b, IntentPair('p1', 'a', 'b'), include_collision_tick=False)
    assert (d.first_collision_tick, d.window_ticks, d.max_pos_diff_m) == (70, 70, 0.0)
    assert d.available_duration_s == 3.5
    assert d.last_sample_time_s == pytest.approx(3.45)
```

- [ ] **Step 2: Run tests red.** `python -m pytest tests/test_m21_measurements.py -q` → missing interfaces FAIL.

- [ ] **Step 3: Implement declared signatures.** Align by each explicit marker, require NPC and ego unique finite states on exact .05 ticks and matching scene/session/rep/seed for counterfactual pairs. Eight-second window uses relative ticks 0..160 inclusive. Earliest collision event for any owned ego/NPC actor across both episodes bounds both; a collision before marker gives `quality_status='pre_marker_collision'` and null measures. Missing ticks are errors, not interpolated. `include_collision_tick` is mandatory to keep the pending convention visible; pilot uses false as a **diagnostic pre-impact convention only**. Store duration to event/window boundary separately from last sample timestamp; censoring is `quality_status='collision_censored'`, not a response/pass classification.

Position = Euclidean XY difference, speed = absolute scalar `speed_mps` difference. Onset threshold is strictly `> max(noise_t, .1)` for 10 consecutive ticks; unequal/nonfinite noise is error, missing noise gives null onset/reason. `noise_statistics` takes explicitly supplied same-action independent pairs, validates unique source episodes/no reused episode across calibration pairs, returns p90 of maxima and per-tick p90 on their common valid window using the required quantile method; it does not select/claim the future four-scene noise sample. `ego_context` labels signed ego speed A−B, ego XY A/B separation and within-run ego–NPC center distances A/B and signed difference, never presents center distance as bumper gap. No median over censored onsets, CI/bootstrap, Bonferroni or classifier is implemented here.

- [ ] **Step 4: Run tests green.** Same command → PASS, including source-event censoring and no-noise nulls.

- [ ] **Step 5: Commit.** `git add experiments/ego_intent_response/m21/measurements.py tests/test_m21_measurements.py` then `git commit -m "feat: add descriptive M21 trajectory measurements"`.

### Task 5: Unmodified normal BehaviorAgent on pinned NPC routes

**Files:**
- Create: `experiments/ego_intent_response/m21/agent.py`
- Test: `tests/test_m21_agent.py`

**Interfaces:**
- Consumes legacy `TransformSpec`, configured agents root and `M21Error`.
- Produces `AgentBinding(agent: Any, plan_records: list[dict[str, Any]], source_hashes: dict[str, str])`; `load_behavior_agent(agents_root: Path) -> type[Any]`; `create_npc_agent(vehicle: Any, route: Sequence[TransformSpec], agents_root: Path) -> AgentBinding`.

- [ ] **Step 1: Write failing tests with fake CARLA waypoints and a patched loader.** `test_normal_agent_has_no_tuning_or_ignore_calls`: assert constructor `(vehicle, behavior='normal', opt_dict={})`, no set_target_speed/follow_speed_limits/ignore methods/autopilot call; assert `set_global_plan(plan, stop_waypoint_creation=True, clean_queue=True)`. `test_trace_passes_pinned_points_and_records_road_options`: fake each route segment, assert segment endpoints in catalog order and plan includes final waypoint plus road_id/lane_id/junction_id/RoadOption. `test_wrong_loaded_agents_or_detour_are_rejected`: preloaded module from another root, off-road point, reversed segment, wrong lane or 10 m detour each raises, with no fallback set_destination. In this test file define fake vehicle/route/agent-loader fixtures: ordered straight points x=0,4,8; road_id=11/lane_id=-1; each fake trace returns its two endpoints with LANEFOLLOW. Pin the stock-control contract:
```python
def test_normal_agent_has_no_tuning_or_ignore_calls(fake_vehicle, fake_agent_loader, tmp_path):
    route = tuple(TransformSpec(x, 0) for x in (0, 4, 8))
    binding = create_npc_agent(fake_vehicle, route, tmp_path)
    fake_agent_loader.assert_called_once_with(fake_vehicle, behavior='normal', opt_dict={})
    for name in ('set_target_speed', 'follow_speed_limits', 'ignore_traffic_lights',
                 'ignore_vehicles', 'ignore_stop_signs'):
        getattr(binding.agent, name).assert_not_called()
    assert binding.agent.set_global_plan.call_args.kwargs == {
        'stop_waypoint_creation': True, 'clean_queue': True}
    fake_vehicle.set_autopilot.assert_not_called()
```

- [ ] **Step 2: Run tests red.** `python -m pytest tests/test_m21_agent.py -q` → missing agent adapter FAIL.

- [ ] **Step 3: Implement declared signatures.** Agent import is lazy and strictly validates module origins beneath `agents_root/agents`; reject contaminated `sys.modules`, do not evict/rebind a foreign module silently. Instantiate normal with fresh empty opt_dict (BasicAgent mutates that dictionary internally). Map pinned coordinates to Driving waypoints, concatenate `BasicAgent.trace_route` over consecutive pinned points, deduplicate only adjacent identical waypoint IDs, retain RoadOption labels, then call `set_global_plan` once. Validate trace against the pinned polyline sampled every 1 m: within 1.0 m of that polyline, correct driving lane IDs for the corresponding ordered segment, no backward progress or unlisted lane change. These are fixture-fidelity checks, not behavior tuning. Save actual plan points, IDs/options and module source hashes; default library `LocalPlanner` remains untouched. An impossible trace reports the exact segment/lane and blocks that run.

- [ ] **Step 4: Run tests green.** Same command → PASS with no live server required. Confirm `LocalPlanner` name and unchanged agent sources by comparing SHA-256 inventories, not by modifying them.

- [ ] **Step 5: Commit.** `git add experiments/ego_intent_response/m21/agent.py tests/test_m21_agent.py` then `git commit -m "feat: bind stock BehaviorAgent to pinned M21 NPC routes"`.

### Task 6: Tick runner with legacy ego, explicit marker và durable attempts

**Files:**
- Create: `experiments/ego_intent_response/m21/runner.py`
- Modify test helpers: `tests/m21_helpers.py`
- Test: `tests/test_m21_runner.py`

**Interfaces:**
- Consumes Task 2 config/cells, Task 3 provenance/storage, Task 5 agent binding; legacy `CarlaExperimentWorld`, `ExperimentRunner`, `RouteSpeedController`, `speed_from_schedule`, `_row_for_actor` and `preflight_scene`.
- Produces `M21Runner(config: M21Config, catalog: ScenarioCatalog)` with `start() -> None`, `preflight() -> dict[str, list[str]]`, `run_cell(cell: RunCell, *, resume: bool = False) -> dict[str, Any]`, `close() -> None`; returned record keys `run_id,status,error,scene_id,intent,repeat,session_id,seed,states_path,events_path,metadata_path,attempts,setup_wall_s,simulation_wall_s,total_wall_s,simulated_s,raw_bytes,synchronous_mode,fixed_delta_s,carla_client_version,carla_server_version,gpu_renderer_device,session_manifest_sha256,implementation_hash,config_hash,catalog_hash`. Timing fields float, counts int, synchronous_mode bool; paths/IDs/hashes str. This is the row schema of `output_root/sessions/<id>/run_manifest.csv`.
- Test helper `make_fake_environment(scene: SceneSpec) -> Any` records apply/tick/snapshot order, lets tests inject late collision events/setup failures and supplies only owned actors. It must not simulate a new ego controller.

- [ ] **Step 1: Write failing fake-world regression tests.** `test_ego_control_sequence_matches_legacy`: run both existing `ExperimentRunner.run_single` (mock NPC control only) and new runner against identical fake actor states for all three crossing intents plus delayed merge intent; assert ego throttle/brake/steer sequence exactly equal at every tick. `test_common_marker_is_before_command_tick`: trigger=3.0, dt=.05, initial_frame=1000 → marker frame=1060/time=3.0, one marker, first post-action snapshot=1061, including no-action/delayed intent. `test_late_collision_event_is_flushed_before_cleanup`: injected event frame precedes recorded flag; assert frame retained in events and metadata before legacy cleanup clears events. `test_failed_attempts_and_resume_do_not_add_samples`: failed setup then success keeps same cell seed/rep, separate attempt logs, one canonical complete; resume executes zero controls; foreign actors remain undestroyed. Assert stored frames 0..280 relative, 281 snapshots ×2 actors for a full 14 s run. In the test file define a local `runner_trace(intent_id: str, *, legacy: bool) -> dict[str, Any]` wrapper over the two real runners and fresh identical fake environments; it returns captured ego_controls, marker_events, first_post_action_frame and raw_rows. It must not compute controls itself. Exact assertions:
```python
@pytest.mark.parametrize('intent_id', ['go_now', 'yield_then_go', 'stop_before_crossing'])
def test_ego_control_sequence_matches_legacy(intent_id):
    old = runner_trace(intent_id, legacy=True)
    new = runner_trace(intent_id, legacy=False)
    assert new['ego_controls'] == old['ego_controls']
    assert len(new['raw_rows']) == 281 * 2
    assert len(new['marker_events']) == 1
    marker = new['marker_events'][0]
    assert marker['frame'] == 1060 and marker['relative_time_s'] == 3.0
    assert new['first_post_action_frame'] == 1061
```
Add the same marker/control equality assertions for `merge_01/wait_then_merge` with the wrapper selecting that catalog scene.

- [ ] **Step 2: Run tests red.** `python -m pytest tests/test_m21_runner.py -q` → missing M21 runner FAIL.

- [ ] **Step 3: Implement `M21Runner` and fake helpers.** Compose/subclass the legacy runner/world only in the new module; reuse setup/calibration/validation/cleanup, .05 sync/substeps and lights unchanged. Seed Python/NumPy/TM before fixture setup (reload/calibration can otherwise consume RNGs), reapply TM seed after reload, instantiate fresh ego prefix/intent controllers and fresh normal NPC agent per episode. Never call `configure_tm_actor` for `npc_conflict` or enable its autopilot during measurement. Check world frame/time drift and map/source hashes. `preflight()` runs existing topology checks for all 24 scenes and, for route fidelity, temporarily spawns only the owned NPC at its pinned pose, builds its Task 5 binding without advancing a measured episode, then destroys it before the next scene. These are unmeasured fixture checks, not extra samples. Unit-test `test_route_exhaustion_is_invalid_not_random_extension`: if agent.done() before the run horizon, status invalid with `route_exhausted`, no destination extension/autonomous waypoint creation.

Mirror legacy `run_single` controller choice and `speed_from_schedule(..., time_s-dt)` exactly. Write initial snapshot plus every post-tick snapshot through `_row_for_actor`, adding session/seed, road_id/lane_id and schema without altering legacy fields. At the snapshot matching trigger, write the single explicit action_start event before applying the next controls. Export collision callbacks with actual event.frame, drain/capture pending callback records before stopping sensors/finalizing/legacy cleanup; bounded 2 s final drain is included in timing and recorded as a capture bound, not proof of arbitrary sensor delivery. Any observed event outside saved raw range or late event after finalization invalidates the affected episode; do not silently drop it.

Attempts store under Task 3 paths; failure retains artifacts/error and never canonical complete. Promote only verified success to canonical paths atomically and append the Task 6 run manifest after finalize. Failed attempt records go to `output_root/sessions/<id>/attempt_manifest.csv`; main manifest records final logical-cell status and cumulative time/attempt count, so retries are not counted as additional observations. Never leave two complete main-manifest rows for the same cell; resume adds no duplicate row. Reuse legacy completion/hash checks plus extra M21 events/session checks; corrupt complete cell is an explicit error, not auto-rerun/overwrite. A successful resume neither advances world nor changes files. Preserve setup/physics failures as invalid, never label them no-response.

- [ ] **Step 4: Run tests green.** `python -m pytest tests/test_m21_runner.py tests/test_ego_intent_response.py -q` → all PASS; same legacy implementation hash as Task 1, no diff in protected module bytes.

- [ ] **Step 5: Commit.** `git add experiments/ego_intent_response/m21/runner.py tests/m21_helpers.py tests/test_m21_runner.py` then `git commit -m "feat: record M21 pilot with unchanged scripted ego"`.

### Task 7: CLI/report integration, real regression và approved pilot evidence

**Files:**
- Create: `experiments/ego_intent_response/m21/cli.py`, `experiments/ego_intent_response/m21/report.py`
- Modify: `scripts/run_ego_intent_response.py:37-57,235-238` (additive arguments/early dispatch only)
- Test: `tests/test_m21_cli.py`, `tests/test_m21_carla.py`
- Create: `docs/superpowers/runbooks/2026-10-05-m21-pilot.md`

**Interfaces:**
- Consumes Tasks 1–6. Legacy entry remains `main() -> int` and unchanged analysis functions.
- Produces `m21.cli.main(args: argparse.Namespace) -> int`; `write_pilot_report(root: Path, diagnostics: Sequence[PairDiagnostics], manifest: pd.DataFrame) -> dict[str, Path]` returning `pairs, spreads, timing, report`.
- CLI additions: `--mode {legacy,m21}` default legacy; `--m21-phase {pilot,full,decision}` default pilot (full/decision always rejected in this phase); `--agents-root PATH` default `E:/Carla/PythonAPI/carla`; `--session-id`, `--session-index`, `--session-evidence PATH`. Evidence JSON contains boot_token/operator restart statement and PID/start time if available. Reuse transport/config/preflight/analyze-only/resume flags; absent M21 output-dir defaults to `outputs/m21_behavior_agent_pilot`, not the legacy root.

- [ ] **Step 1: Write failing integration/CLI/report tests.** `test_default_legacy_dispatch_never_imports_m21_agent` asserts no new agent imports, unchanged legacy invocation and explicit legacy equivalence even when `agents` unavailable. `test_pending_m21_rejects_full_decision_and_extra_profiles` asserts exit 2 before connecting/writing for full/decision/profile overrides or nonpilot scene/intent/repetition overrides. `test_pilot_deduplicates_shared_intent` asserts 30 run_cell calls and exactly 20 pair records with shared go_now source IDs. `test_report_has_no_inference_without_noise` asserts required CSV columns, speed units m/s despite `max_vel_diff_m`, null onset and no CI/classification/pass fields or decision.json. `test_analyze_only_and_resume_are_non_destructive` asserts no server connection offline, no modified complete episode on resume and explicit errors for legacy rows without M21 markers. Test timing totals from known manifest values and estimate `2160 * mean(total_wall_s)`, flagged extrapolation not a runtime guarantee. Gate assertion as code:
```python
@pytest.mark.parametrize('phase', ['full', 'decision'])
def test_pending_m21_rejects_full_decision_and_extra_profiles(monkeypatch, phase):
    from scripts import run_ego_intent_response as cli
    monkeypatch.setattr(sys, 'argv', ['experiment', '--mode', 'm21', '--m21-phase', phase])
    assert cli.main() == 2
```
Mock both legacy and M21 runner start methods to raise AssertionError if called in this test. In `test_report_has_no_inference_without_noise`, build a Task 4 diagnostic with no noise and a known one-run timing manifest; pin these assertions on `paths = write_pilot_report(tmp_path, [diagnostic], manifest)`:
```python
rows = pd.read_csv(paths['pairs'])
assert rows['onset_tick'].isna().all()
assert rows['protocol_status'].eq('pending').all()
assert {'max_pos_diff_m', 'max_vel_diff_m', 'run_id_a', 'run_id_b'} <= set(rows.columns)
assert not {'classification', 'passes', 'ci_low', 'ci_high'} & set(rows.columns)
assert not (tmp_path / 'decision.json').exists()
```

Add opt-in `tests/test_m21_carla.py`, gated by `CARLA_M21_INTEGRATION=1`: preflight Town03 catalog, run crossing_01 rep1 three intents in separate temporary output, verify live readback .05/sync/no_rendering, stock-agent origins/route, raw frames/marker/hash, three complete episodes/two descriptive pair rows and no decisions. Smoke-only identity uses `validation-01`, reserved session_index=100 so its independent validation episodes never reuse pilot seeds; report these three validation runs separately from the 30-run pilot. This smoke does not claim noise/session sufficiency.

- [ ] **Step 2: Run tests red.** `python -m pytest tests/test_m21_cli.py -q` → missing dispatch/report FAIL; not a failing CARLA availability check.

- [ ] **Step 3: Implement CLI dispatch and diagnostic report.** Dispatch immediately after parsing args, before legacy config/runner initialization; import M21 only in that branch. M21 accepts only crossing_01, normal, ten reps for live pilot; no hidden full schedule and no configurable bypass for protocol_status. Preflight may validate all 24 fixture routes without running their matrix. Offline analyze-only requires existing M21 session manifest/raw/events/source hashes, no CARLA agent import or nvidia-smi rerun. Keep legacy argparse defaults unchanged; record explicitly supplied option names on Namespace as `_explicit_options: frozenset[str]` (normalize `--name=value` to `--name`) so the default legacy bootstrap value is not mistaken for a requested M21 option. In M21 allow `--scene` absent or crossing_01 and `--repetitions` absent or 10; reject explicitly supplied profile/intent/resampling/skip-audit/plots options rather than silently ignore them.

Emit schema/units and paired observation CSV files under `analysis/pairs/<pair_id>/rep_XX.csv` (two source IDs plus brief's 12 required columns and quality fields), combined `analysis/pair_diagnostics.csv`, `analysis/descriptive_spreads.csv`, `analysis/pilot_timing.json`, `analysis/pilot_report.md`. Use include_collision_tick=false and ddof=1 explicitly recorded as provisional diagnostic conventions; quantile primitive tests use linear, but real pilot has no pooled four-scene noise → onset/noise-dependent values null with reason. Report pair-level descriptive spread, censored counts (not final scene×pair unassessable verdict), setup/simulation/total seconds, attempts/invalids, bytes and extrapolation. Preserve profile/session/restart/GPU warnings; emit no overall decision file and never call legacy write_reports from M21. Run failures/preflight/environment blockers write `blocker.json` with reason and exit 2; partial pilot reports remain explicitly incomplete.

- [ ] **Step 4: Run unit/regression tests.**
```powershell
python -m pytest tests/test_m21_legacy_regression.py tests/test_m21_protocol.py tests/test_m21_provenance.py tests/test_m21_measurements.py tests/test_m21_agent.py tests/test_m21_runner.py tests/test_m21_cli.py tests/test_ego_intent_response.py -q
python scripts/check_m21_legacy_regression.py compare --evidence outputs/m21_legacy_regression
python scripts/check_m21_legacy_regression.py compare --evidence outputs/m21_legacy_regression --explicit-mode
```
Expected: all unit tests PASS; both compare invocations exit 0 and every baseline artifact SHA-256/inventory identical. Input/protected source hashes unchanged. A numerical-only match does not pass this gate. Stop before CARLA pilot on any regression mismatch.

- [ ] **Step 5: Write the runbook.** Document Task 3 raw/manifest and Task 4 paired schema/units, commands below, legacy regression hashes/paths, pending statistics list from spec §5, safe cleanup, session/GPU caveats and no M55 conclusion. Use placeholders only for operator-specific session evidence/port in command examples, never for protocol values.

- [ ] **Step 6: Run opt-in live smoke on an empty dedicated server.** Read the runbook before launching; never kill an existing user-owned server. Operator supplies `outputs/m21_session_evidence.json` with actual restart/device evidence; use a new server boot for each claimed independent session. Configure integration test from `CARLA_M21_HOST`, `CARLA_M21_PORT`, `CARLA_M21_TM_PORT`, `CARLA_M21_AGENTS_ROOT`, `CARLA_M21_SESSION_EVIDENCE`.
```powershell
$env:CARLA_M21_INTEGRATION='1'
python -m pytest tests/test_m21_carla.py -q
```
Expected: test PASS against matching empty 0.9.16 server. With integration unset, SKIP is expected but is **not** live verification. Missing API/server/route/device evidence → retain blocker/logs and report, no fake completion.

- [ ] **Step 7: Run the approved 30-episode pilot, not full matrix.**
```powershell
python scripts/run_ego_intent_response.py --mode m21 --m21-phase pilot --session-id pilot-01 --session-index 0 --session-evidence outputs/m21_session_evidence.json --agents-root E:/Carla/PythonAPI/carla --output-dir outputs/m21_behavior_agent_pilot --preflight-only
python scripts/run_ego_intent_response.py --mode m21 --m21-phase pilot --session-id pilot-01 --session-index 0 --session-evidence outputs/m21_session_evidence.json --agents-root E:/Carla/PythonAPI/carla --output-dir outputs/m21_behavior_agent_pilot --resume
```
Expected: preflight exit 0, then pilot exits 0 iff all 30 canonical episodes complete; no extra runs for shared pair membership. Retain all attempts. Count 30 episodes, ten matched seed blocks, 20 pair CSVs/rows, explicit markers/raw hashes and timing. Incomplete/blocked counts are reported as such; no automatic continuation to 2160.

- [ ] **Step 8: Rebuild offline diagnostics and audit artifacts.** Stop only the dedicated server if this session owns it, then run the same M21 command with `--analyze-only`. Expected: no server connection, same diagnostic data excluding intentionally separate runtime timing provenance; missing noise yields null onset, not invented estimates. Verify 30 canonical metadata/raw/events hashes, `action_start` once/run, and absence of M21 CI/classifier/decision output. Link timing, raw/manifest, comparison.json and any warnings in runbook. Report measured pilot wall time and extrapolation; ask Dũng to finalize statistics before further phases.

- [ ] **Step 9: Commit source/tests/runbook only after audit.** Stage the three M21/CLI source paths and two test paths listed in this task; force-add only `docs/superpowers/runbooks/2026-10-05-m21-pilot.md`; `git diff --cached --check`; `git commit -m "feat: integrate gated M21 pilot and verify legacy outputs"`. Do not stage user-owned untracked dependency baseline or outputs. If the ownership gate is unresolved, do not claim this commit/task is complete.

## Self-review và evidence coverage

- Spec §1/§3.1/§7: Tasks 1 and 7 capture-before-feature, byte-exact legacy outputs and default-off dispatch; Tasks 2–6 leave legacy files untouched.
- Spec §3.2: Task 5 stock normal agent and pinned route, Task 6 real per-tick control and unchanged ego.
- Spec §3.3/§3.4: Tasks 2–3 seeds/session/settings/GPU/source integrity; Task 6 marker/raw/collision/attempt durability.
- Spec §4: Task 4 descriptive differences/noise/onset/spread/ego primitives; Task 7 pilot nulls where calibration is unavailable.
- Spec §5: intentionally deferred inference, aggregation, comparison with old TM under M21 and profile escalation. Task 7 rejects inference/full requests; a subsequent approved statistical spec/plan is required, not an uncovered implementation promise in this pilot.
- Spec §6/§8: Task 7 smoke, 30/20 live pilot/timing/offline checks and no silent blocker. All five Review Focus inputs have explicit named tests in their owning task.
- Interfaces: all cross-task records and functions are defined by producing tasks; legacy signatures referenced are existing. No unknown estimator, safety tuning or classifier is smuggled into pilot defaults.
- Status: this file is a plan, **not evidence that any test, regression capture or pilot has run**. M55 remains separate.

## Execution handoff

Review this plan before implementation. **Native** is recommended: seven sequential tasks share config/storage/tick interfaces and only one live pilot is authorized; native avoids repeated context startup while the regression gate gives strong mechanical checks. Subagent-driven remains an option for fresh task-by-task implementer/reviewer contexts. In either approach, perform an independent whole-branch review before integrating; no delegation is launched until the user selects/authorizes it. Do not treat writing this plan as approval to execute it.
