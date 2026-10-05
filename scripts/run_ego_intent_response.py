"""Run or analyze the fixed Town03 ego-intent/NPC-response experiment."""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import hashlib
import json
import logging
from pathlib import Path
import sys
from typing import Any, Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.ego_intent_response.metrics import MetricsConfig, analyze_completed_runs
from experiments.ego_intent_response.report import write_reports, write_trajectory_plots
from experiments.ego_intent_response.runner import (
    ExperimentError,
    ExperimentRunner,
    load_experiment_config,
    read_complete_state_files,
)
from experiments.ego_intent_response.scenario_catalog import PROFILES, SceneSpec, load_catalog


MANIFEST_FIELDS = (
    "run_id", "status", "error", "seed", "states_path", "metadata_path", "profile",
    "scene_id", "intent", "repeat", "audit",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(PROJECT_ROOT / "configs/ego_intent_response_town03.yaml"))
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--tm-port", type=int)
    parser.add_argument("--output-dir")
    parser.add_argument("--list-scenes", action="store_true")
    parser.add_argument("--scene", action="append", default=[], help="Scene id; repeat to select multiple scenes.")
    parser.add_argument("--intent", action="append", default=[], help="Intent id; repeat to select multiple intents.")
    parser.add_argument("--profile", action="append", choices=PROFILES, default=[])
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--skip-audit", action="store_true")
    parser.add_argument("--plots", action="store_true", help="Write global XY mean-trajectory SVGs without additional dependencies.")
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--permutation-samples", type=int, default=2000)
    parser.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO")
    return parser.parse_args()


def _resolve_catalog_path(config_path: Path, catalog_path: str) -> Path:
    direct = Path(catalog_path)
    if direct.is_absolute():
        return direct
    for path in (config_path.parent / direct, config_path.parent.parent / direct, PROJECT_ROOT / direct):
        if path.exists():
            return path.resolve()
    raise ExperimentError(f"Pinned catalog not found: {catalog_path}")


def _scene_descriptor(scene: SceneSpec) -> dict[str, Any]:
    return {
        "scene_id": scene.scene_id,
        "category": scene.category,
        "trigger_s": scene.intents[next(iter(scene.intents))].trigger_s,
        "participant_keys": list(scene.participant_keys),
        "intent_ids": list(scene.intents),
    }


def _append_manifest(output_dir: Path, row: dict[str, Any], *, invalid: bool = False) -> None:
    path = output_dir / ("invalid_runs.csv" if invalid else "run_manifest.csv")
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def _selected_intents(scene: SceneSpec, requested: Iterable[str]) -> list[str]:
    wanted = {item for item in requested if item}
    unknown = wanted - set(scene.intents)
    if unknown:
        raise ExperimentError(f"Scene {scene.scene_id} has no requested intents {sorted(unknown)}")
    return [intent for intent in scene.intents if not wanted or intent in wanted]


def _write_analysis(runner: ExperimentRunner, scenes: list[SceneSpec], *, baseline_only: bool, args: argparse.Namespace) -> None:
    states = read_complete_state_files(runner.output_dir, catalog_hash=runner.catalog_hash, configuration_hash=runner.effective_hash)
    states = states[states.scene_id.isin([s.scene_id for s in scenes])]
    if args.profile:
        states = states[states.profile.isin(args.profile)]
    if baseline_only:
        states = states[states.profile == "tm_default"]
    if states.empty:
        logging.warning("No complete states available for analysis.")
    metrics = MetricsConfig(
        fixed_delta_s=runner.config.fixed_delta_s,
        bootstrap_samples=args.bootstrap_samples,
        permutation_samples=args.permutation_samples,
    )
    descriptors = [{**_scene_descriptor(scene), "required_repeats": runner.config.repetitions} for scene in scenes]
    actor, aggregate, summary = analyze_completed_runs(states, descriptors, metrics)
    # Entirely missing scene/profile cells also appear in the handoff.
    expected_profiles = ["tm_default"] if baseline_only else args.profile or list(PROFILES)
    existing = set(zip(summary.get("scene_id", []), summary.get("profile", [])))
    absent = [dict(scene_id=s.scene_id, category=s.category, profile=p, classification="incomplete", classification_reason="No completed runs")
              for s in scenes for p in expected_profiles if (s.scene_id, p) not in existing]
    if absent:
        summary = pd.concat([summary, pd.DataFrame(absent)], ignore_index=True)
    if runner.environment.world is not None:
        provenance = runner.environment.provenance()
    else:
        provenance = {"analysis_mode": "offline", "town": runner.config.town, "fixed_delta_s": runner.config.fixed_delta_s}
        for metadata_path in sorted((runner.output_dir / "runs").glob("*/*/*/rep_*/metadata.json")):
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("status") == "complete":
                provenance.update(metadata.get("provenance", {}))
                break
    provenance.update({"catalog_path": runner.config.catalog_path, "catalog_hash": runner.catalog_hash,
                       "config_hash": runner.effective_hash, "implementation_hash": runner.code_hash,
                       "config": runner.config.__dict__, "scenes_analyzed": [scene.scene_id for scene in scenes], "metrics": metrics.__dict__,
                       "scripted_controller": {"steering": "pure_pursuit", "lookahead_m": 7.0, "wheelbase_m": 2.85,
                                               "max_steer_angle_rad": .70, "speed_pid_kp": .35, "speed_pid_ki": .08,
                                               "speed_pid_kd": .005, "integral_bound": 3.0, "max_throttle": .75,
                                               "max_brake": 1.0, "max_steer_control": .8},
                       "npc_profiles": {"tm_default": {"controller": "CARLA Traffic Manager", "route": "pinned set_path",
                                                        "auto_lane_change": False, "desired_speed": "per NPC fixture (m/s converted to km/h)",
                                                        "following_distance_m": runner.config.tm_following_distance_m,
                                                        "ignore_vehicles_percent": 0, "ignore_lights_percent": 0, "ignore_signs_percent": 0},
                                        "reactive_yield_v1": {"oracle_ground_truth": True, "replaced_actor_keys": "critical NPCs only",
                                                              "min_ttc_s": runner.config.reactive_min_ttc_s,
                                                              "occupancy_radius_m": runner.config.reactive_occupancy_radius_m,
                                                              "follow_gap_m": runner.config.reactive_follow_gap_m,
                                                              "occupancy_npc_range_m": 18, "ttc_npc_range_m": 35, "follow_lateral_range_m": 2}}})
    paths = write_reports(
        runner.output_dir, actor_effects=actor, aggregate_effects=aggregate, summary=summary,
        provenance=provenance, baseline_only=baseline_only,
    )
    if args.plots:
        write_trajectory_plots(runner.output_dir, states)
    logging.info("Wrote analysis: %s", paths["summary"])


def _run_audit(runner: ExperimentRunner, scenes: list[SceneSpec], *, resume: bool = False) -> int:
    """24 audit runs: six category representatives × two profiles × two identical seeds."""
    representative: list[tuple[int, SceneSpec]] = []
    seen_categories: set[str] = set()
    failures = 0
    for index, scene in enumerate(scenes):
        if scene.category not in seen_categories:
            representative.append((index, scene))
            seen_categories.add(scene.category)
    for scene_index, scene in representative:
        intent = next(iter(scene.intents))
        audit_seed = 9_000_001 + scene_index
        for profile in PROFILES:
            for audit_repeat in (1, 2):
                runner.check_existing_cell(scene, profile, intent, audit_repeat, output_group="audits")
                if resume and runner.is_complete(scene, profile, intent, audit_repeat, output_group="audits"):
                    continue
                for _ in range(runner.config.max_setup_attempts):
                    result = runner.run_single(
                        scene, profile=profile, intent_id=intent, repeat=audit_repeat, scene_index=scene_index,
                        seed_override=audit_seed, output_group="audits",
                    )
                    if result["status"] == "complete":
                        break
                    _append_manifest(runner.output_dir, {**result, "audit": True, "profile":profile, "scene_id":scene.scene_id, "intent":intent, "repeat":audit_repeat}, invalid=True)
                failures += result["status"] != "complete"
                _append_manifest(runner.output_dir, {**result, "audit": True, "seed": audit_seed, "profile":profile, "scene_id":scene.scene_id, "intent":intent, "repeat":audit_repeat})
    return failures


def _write_audit_summary(output_dir: Path) -> None:
    """Compare the two same-seed audits; they are not analysis observations."""
    audit_root = output_dir / "audits"
    rows: list[dict[str, Any]] = []
    for first in sorted(audit_root.glob("*/*/*/rep_01/states.csv")) if audit_root.exists() else []:
        second = first.parent.parent / "rep_02" / "states.csv"
        if not second.exists():
            rows.append({"run_path": str(first), "status": "missing_second_run"})
            continue
        metadata = [json.loads(p.with_name("metadata.json").read_text(encoding="utf-8")) for p in (first, second)]
        if any(m.get("status") != "complete" or m.get("states_sha256") != hashlib.sha256(p.read_bytes()).hexdigest() for m, p in zip(metadata, (first, second))):
            rows.append({"run_path": str(first), "status": "invalid_metadata_or_hash"})
            continue
        if metadata[0]["seed"] != metadata[1]["seed"] or metadata[0]["config_hash"] != metadata[1]["config_hash"] or metadata[0]["catalog_hash"] != metadata[1]["catalog_hash"]:
            rows.append({"run_path": str(first), "status": "unmatched_fixture_or_seed"})
            continue
        left = pd.read_csv(first)
        right = pd.read_csv(second)
        keys = ["actor_key", "relative_time_s"]
        if left.duplicated(keys).any() or right.duplicated(keys).any():
            rows.append({"run_path": str(first), "status": "duplicate_ticks"})
            continue
        merged = left.merge(right, on=keys, suffixes=("_a", "_b"), how="inner", validate="one_to_one")
        if len(merged) != len(left) or len(merged) != len(right):
            rows.append({"run_path": str(first), "status": "missing_actor_or_ticks"})
            continue
        if merged.empty:
            rows.append({"run_path": str(first), "status": "missing_common_ticks"})
            continue
        position_error = ((merged.x_a - merged.x_b) ** 2 + (merged.y_a - merged.y_b) ** 2).pow(0.5)
        velocity_error = ((merged.vx_a - merged.vx_b) ** 2 + (merged.vy_a - merged.vy_b) ** 2).pow(0.5)
        initial_left, initial_right = [m.get("initial_states", {}) for m in metadata]
        initial_position_errors, initial_velocity_errors = [], []
        if set(initial_left) == set(initial_right) and initial_left:
            for actor_key in initial_left:
                a, b = initial_left[actor_key], initial_right[actor_key]
                initial_position_errors.append(((a["x"]-b["x"])**2+(a["y"]-b["y"])**2)**.5)
                initial_velocity_errors.append(((a["vx"]-b["vx"])**2+(a["vy"]-b["vy"])**2)**.5)
        rows.append({
            "run_path": str(first), "status": "complete", "n_common_rows": len(merged),
            "max_position_error_m": float(position_error.max()), "rms_position_error_m": float((position_error ** 2).mean() ** 0.5),
            "max_velocity_error_mps": float(velocity_error.max()),
            "initial_states_bitwise_equal": metadata[0].get("actual_initial_state_checksum") == metadata[1].get("actual_initial_state_checksum"),
            "max_initial_position_difference_m": max(initial_position_errors) if initial_position_errors else None,
            "max_initial_velocity_difference_mps": max(initial_velocity_errors) if initial_velocity_errors else None,
            "within_trajectory_reference_tolerance": bool(position_error.max() <= 0.10 and velocity_error.max() <= 0.25),
        })
    pd.DataFrame(rows).to_csv(output_dir / "reproducibility_audit.csv", index=False)


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="[%(asctime)s] %(levelname)s: %(message)s")
    config_path = Path(args.config).resolve()
    config, raw_config = load_experiment_config(config_path)
    for name in ("host", "port", "tm_port", "output_dir"):
        value = getattr(args, name)
        if value is not None:
            config = replace(config, **{name: value})
    if args.repetitions is not None:
        config = replace(config, repetitions=int(args.repetitions))
    catalog = load_catalog(_resolve_catalog_path(config_path, config.catalog_path))
    if catalog.town.lower() != config.town.lower():
        raise ExperimentError(f"Config town {config.town} does not match catalog town {catalog.town}.")
    scenes = list(catalog.select(args.scene or None))
    if args.list_scenes:
        for s in scenes:
            print(f"{s.scene_id}: {s.category}: {', '.join(s.intents)}")
        return 0
    if config.repetitions < 1 or args.bootstrap_samples < 1 or args.permutation_samples < 1:
        raise ExperimentError("Repetitions and resampling counts must be positive")
    if args.intent and not any(set(args.intent) & set(s.intents) for s in scenes):
        raise ExperimentError("No selected scene contains the requested intent(s)")
    unknown_intents = set(args.intent) - {intent for scene in scenes for intent in scene.intents}
    if unknown_intents:
        raise ExperimentError(f"Unknown selected intents: {sorted(unknown_intents)}")
    profiles = [profile for profile in PROFILES if not args.profile or profile in set(args.profile)]
    runner = ExperimentRunner(config, raw_config, catalog.source_hash)
    scene_indices = {scene.scene_id: index for index, scene in enumerate(catalog.scenes)}
    failed_runs = 0
    try:
        if args.analyze_only:
            _write_analysis(runner, scenes, baseline_only=False, args=args)
            _write_audit_summary(runner.output_dir)
            return 0
        existing_config_path = runner.output_dir / "experiment_config.json"
        if existing_config_path.exists():
            existing_config = json.loads(existing_config_path.read_text(encoding="utf-8"))
            if existing_config.get("config_hash") != runner.effective_hash or existing_config.get("catalog_hash") != runner.catalog_hash:
                raise ExperimentError("Output directory contains a different experiment configuration/catalog/implementation; choose a new --output-dir")
        runner.start()
        if runner.environment.provenance()["opendrive_sha256"] != catalog.opendrive_sha256:
            raise ExperimentError("Server OpenDRIVE differs from the pinned fixture catalog")
        preflight = runner.preflight(scenes)
        failures = {scene_id: reasons for scene_id, reasons in preflight.items() if reasons}
        if failures:
            raise ExperimentError("Preflight failed: " + json.dumps(failures, ensure_ascii=False))
        if args.preflight_only:
            logging.info("Preflight passed for %d scenes.", len(scenes))
            return 0
        for profile in profiles:
            for scene in scenes:
                scene_index = scene_indices[scene.scene_id]
                intents = [i for i in scene.intents if not args.intent or i in args.intent]
                for intent in intents:
                    for repeat in range(1, config.repetitions + 1):
                        runner.check_existing_cell(scene, profile, intent, repeat)
                        completed = runner.is_complete(scene, profile, intent, repeat)
                        if completed and not args.resume:
                            raise ExperimentError("Completed data already exists; use --resume or a different --output-dir")
                        if args.resume and completed:
                            logging.info("Resume: keeping completed %s/%s/%s/%d", profile, scene.scene_id, intent, repeat)
                            continue
                        result = {"status": "invalid", "error": "not attempted"}
                        for _attempt in range(config.max_setup_attempts):
                            result = runner.run_single(scene, profile=profile, intent_id=intent, repeat=repeat, scene_index=scene_index)
                            if result["status"] != "complete":
                                _append_manifest(runner.output_dir, {**result, "profile":profile,"scene_id":scene.scene_id,"intent":intent,"repeat":repeat}, invalid=True)
                            if result["status"] == "complete":
                                break
                        _append_manifest(runner.output_dir, {**result, "profile": profile, "scene_id": scene.scene_id, "intent": intent, "repeat": repeat})
                        if result["status"] != "complete":
                            failed_runs += 1
            # The full baseline phase emits its failure notice before reactive starts.
            if profile == "tm_default" and len(scenes) == 24 and config.repetitions == 10 and not args.intent:
                _write_analysis(runner, scenes, baseline_only=True, args=args)
        if not args.skip_audit and not args.scene and not args.intent and set(profiles) == set(PROFILES) and config.repetitions == 10:
            failed_runs += _run_audit(runner, scenes, resume=args.resume)
            _write_audit_summary(runner.output_dir)
        _write_analysis(runner, scenes, baseline_only=False, args=args)
        return 1 if failed_runs else 0
    finally:
        runner.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ExperimentError as exc:
        logging.error("Experiment failed: %s", exc)
        raise SystemExit(2)
