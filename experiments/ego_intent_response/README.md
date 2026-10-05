# NPC response to ego intent in Town03

This independent harness compares scripted ego intentions while holding NPC
blueprints, initial transforms/velocities, routes, weather and lights fixed.
The checked-in catalog contains 24 scenes (six families, four gap/speed
variants). Its route bank contains explicit CARLA 0.9.16 Town03 coordinates;
runtime never discovers or substitutes scenes.

## Run

Start an otherwise empty CARLA **0.9.16** server, using the project Python
environment with the matching CARLA API, NumPy, pandas and PyYAML. Run from
the repository root:

```powershell
python scripts/run_ego_intent_response.py --list-scenes
python scripts/run_ego_intent_response.py --preflight-only
python scripts/run_ego_intent_response.py --resume
```

Preflight verifies the OpenDRIVE hash, driving-lane membership of every pinned
point, route length, separation and predicted conflict-zone timing. It fails
on an invalid fixture. Foreign vehicle/walker actors cause a failure before
loading or resetting a map; only actors created by this harness are destroyed.

The default run executes baseline first: 24 × 3 × 10 = 720 runs, then 720
reactive runs. Repetition seeds are `41021 + catalog_scene_index * 1000 +
repetition`, matched across intents/profiles. Selection never changes catalog
indices. Twelve same-seed pairs (six representative scenes × two profiles)
add 24 audit runs stored separately from the statistical observations.

```powershell
# Smoke run: six representatives, both profiles, three intents, one repetition.
python scripts/run_ego_intent_response.py --scene merge_01 --scene left_01 --scene overtake_01 --scene crossing_01 --scene cutin_01 --scene rear_01 --repetitions 1 --output-dir outputs/ego_intent_response_smoke --skip-audit

# Only one experiment cell; filters can be repeated.
python scripts/run_ego_intent_response.py --scene merge_01 --intent merge_now --profile tm_default --repetitions 2 --output-dir outputs/ego_intent_response_debug

# Rebuild statistical outputs without connecting to CARLA.
python scripts/run_ego_intent_response.py --analyze-only

# Separate server ports are supported for development/validation.
python scripts/run_ego_intent_response.py --port 2100 --tm-port 8100 --preflight-only
```

## Agent and simulator settings

Fixed delta is 0.05 s, substeps at most 0.01 s, rendering disabled, ClearNoon,
traffic lights frozen green. Every run reloads the empty world while preserving
synchronous settings, recreates actors, settles physics, calibrates velocities
within 0.25 m/s and horizontal positions within 0.10 m, and resets the TM seed.
Wheels are spun up at pinned poses before the measured initial state to avoid
stationary-wheel slip; headings must be within 0.5°. All setup is unrecorded.
This is a checkable reset, not a claim of exact bitwise physics determinism.
Audit outputs quantify remaining same-seed variability. World settings, weather
and light states are restored when the harness closes.

`tm_default` uses Traffic Manager, pinned `set_path` routes, auto lane changes
disabled, desired speeds per fixture, following distance 4 m, and normal
vehicle/light/sign detection (ignore percentages zero). The label means this
TM baseline configuration; it does not mean every TM option is untouched.

`reactive_yield_v1` replaces only critical NPC control with a deterministic
oracle using ground truth. It brakes for ego conflict-zone occupancy,
approaching arrival-time conflicts (3 s threshold), and a closing forward gap
within 10 m in the same lane. Other NPCs would remain controlled by TM.
Ego and reactive NPCs use fixed routes, pure pursuit and a bounded speed PID.
Intents share their pre-trigger route/speed and diverge at 3 s; delayed maneuvers
switch routes only after their fixed waiting interval. No ML weights/cameras
are required.

## Raw data and statistical outputs

Each `runs/<profile>/<scene>/<intent>/rep_XX/` contains `states.csv` and
`metadata.json`: world frame/time, relative run time, stable actor key, runtime
actor ID, global pose/velocity/acceleration, applied control, collision flag and
reaction reason. Metadata captures actual initial states/checksum, expected
fixture checksum, client/server versions, map/config/catalog hashes, blueprint
IDs, collision events and a SHA-256 digest of raw states. Failed setup attempts
are listed in `invalid_runs.csv`; the main manifest includes final run status.
An implementation hash also prevents mixing raw observations across changes
to setup/controller code. Ports, output paths and the requested repeat count
do not change this hash, allowing resume to extend a matrix safely.

Offline analysis accepts only completed, hash-verified raw files. It requires
all three intents, paired seeds, every tick in the [trigger−1, trigger+10] s
window and the requested repetitions. Partial runs/smoke tests are labelled
`incomplete` and never establish a full-matrix pass/fail result.

For position/velocity/acceleration, B is mean RMSE between the three intent
means, W is mean repeat-to-own-intent-mean RMSE, and R = B/max(W, floor).
Floors are 0.05 m, 0.05 m/s and 0.10 m/s². Scene B/W aggregate NPC results by
RMS. Paired seed-block bootstrap preserves NPC/intent correlations (2,000 draws)
and paired intent-label permutation preserves NPC correlations (2,000 draws).
BH correction is performed separately per profile. Stable SHA-derived analysis
seeds make repeated analysis independent of Python hash randomization.

A clear response requires a signal's lower 95% ratio CI ≥3, B at least
0.5 m / 0.25 m/s / 0.5 m/s², and q<0.05. Almost unchanged requires every upper
ratio CI <1.5 and all B below their physical thresholds. Other complete scenes
are inconclusive. Collision-associated effects are flagged: a trajectory change
after an impact alone is not evidence of intentional NPC response.

Outputs: `summary_by_scene.csv`, `actor_effects.csv`, `intent_pair_metrics.csv`,
`scene_signal_metrics.csv`, `response_report.md`, `decision.json`, and
`reproducibility_audit.csv`. Below-target baseline results immediately produce
`baseline_failure_notice.md` before the reactive phase. A pass needs a complete
24-scene, ≥10-repeat profile and at least 12 clearly responsive scenes.
Add `--plots` to generate dependency-free SVG mean trajectories in global XY;
solid paths represent ego and dashed paths NPCs.

## Validate and author fixtures

```powershell
python -m pytest tests/test_ego_intent_response.py -q
python -m pytest tests/test_ego_intent_response_carla.py -q
python -m experiments.ego_intent_response.discovery --xodr E:/Carla/CarlaUE4/Content/Carla/Maps/OpenDrive/Town03.xodr
```

The integration test is skipped by default. Enable it with
`$env:CARLA_EIR_INTEGRATION="1"`; set `CARLA_EIR_PORT` and `CARLA_EIR_TM_PORT`
if your empty validation server uses non-default ports. It preflights all 24
fixtures and runs the full 36-cell representative smoke. Its temporary raw
files are removed after testing; use the CLI smoke command to retain data.

Discovery prints a candidate JSON catalog; JSON is valid YAML. Review/pin its
coordinates and run preflight before replacing the checked-in manifest.
Discovery is an authoring utility only. Fixture changes require a new output
directory; resume never treats a different catalog/config as the same run.

CARLA guidance used for synchronous mode and reapplying seeds after resets:
[Traffic Manager documentation](https://carla.readthedocs.io/en/latest/adv_traffic_manager/).

## Implementation validation (2026-10-02)

CARLA server/client 0.9.16: all 24 pinned fixtures passed topology preflight.
The six-family smoke completed 36/36 cells. Extending `merge_01` from one to
two repeats via `--resume` preserved its first six runs and added six valid
runs. Two same-seed audit pairs (four runs) completed separately. Offline
analysis, 2,000-draw bootstrap/permutation, CSV/JSON/Markdown output and SVG
plots were verified after stopping the dedicated validation server.

Retained local validation data are under
`outputs/ego_intent_response_smoke_final/`; full-catalog preflight is under
`outputs/ego_intent_response_validation_final/`. Outputs are intentionally
git-ignored. Same-seed audits had identical initial XY poses and initial
velocity differences below 0.00005 m/s, but trajectories were not bitwise
deterministic (max XY difference 0.316 m for TM and 1.387 m for reactive in
these two pairs). This is measured simulator/controller noise, not proof of
general repeatability. The full 1,440-run matrix and 24-run audit have not been
executed; no 12/24 acceptance conclusion is available yet.
