"""Fast tests for the standalone ego-intent response experiment."""
from __future__ import annotations

import math
from pathlib import Path
import unittest
from dataclasses import replace
import hashlib
import json
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

from experiments.ego_intent_response.controllers import ReactiveYieldController, RouteSpeedController
from experiments.ego_intent_response.metrics import (
    MetricsConfig,
    analyze_completed_runs,
    benjamini_hochberg,
    between_within,
    classify_scene,
    ratio_between_within,
    MetricsError,
    compute_scene_profile_metrics,
)
from experiments.ego_intent_response.report import write_reports, write_trajectory_plots
from experiments.ego_intent_response.runner import seed_for, ExperimentConfig, ExperimentRunner, ExperimentError, read_complete_state_files, CarlaExperimentWorld, preflight_scene
from experiments.ego_intent_response.scenario_catalog import ACTOR_STATE_FIELDS, CatalogError, ConflictZone, TransformSpec, SpeedPhase, load_catalog


class _Vector:
    def __init__(self, x: float, y: float, z: float = 0.0) -> None:
        self.x, self.y, self.z = x, y, z


class _Rotation:
    def __init__(self, yaw: float) -> None:
        self.yaw = yaw


class _Transform:
    def __init__(self, x: float, y: float, yaw: float = 0.0) -> None:
        self.location = _Vector(x, y)
        self.rotation = _Rotation(yaw)


class _Actor:
    def __init__(self, x: float, y: float, vx: float, vy: float = 0.0) -> None:
        self._location = _Vector(x, y)
        self._velocity = _Vector(vx, vy)
        self._transform = _Transform(x, y, math.degrees(math.atan2(vy, vx)) if vx or vy else 0.0)

    def get_location(self):
        return self._location

    def get_velocity(self):
        return self._velocity

    def get_transform(self):
        return self._transform


class ScenarioCatalogTests(unittest.TestCase):
    def test_pinned_catalog_has_six_four_scene_families_and_three_intents(self):
        catalog = load_catalog(Path("configs/ego_intent_response_town03_scenes.yaml"))
        self.assertEqual(catalog.town, "Town03")
        self.assertEqual(len(catalog.scenes), 24)
        categories = {scene.category for scene in catalog.scenes}
        self.assertEqual(len(categories), 6)
        for category in categories:
            self.assertEqual(sum(scene.category == category for scene in catalog.scenes), 4)
        self.assertTrue(all(len(scene.intents) == 3 for scene in catalog.scenes))
        self.assertTrue(all(scene.ego.actor_key == "ego" for scene in catalog.scenes))
        self.assertTrue(all(scene.critical_keys for scene in catalog.scenes))

    def test_actor_keys_are_stable_and_unique(self):
        catalog = load_catalog("configs/ego_intent_response_town03_scenes.yaml")
        for scene in catalog.scenes:
            self.assertEqual(len(scene.actor_keys), len(set(scene.actor_keys)))
            self.assertEqual(scene.participant_keys, ("npc_conflict",))

    def test_invalid_coordinate_is_rejected(self):
        with self.assertRaises(CatalogError):
            TransformSpec.from_mapping({"x": float("nan"), "y": 1}, label="test")

    def test_nonfinite_speed_and_zone_are_rejected(self):
        with self.assertRaises(CatalogError):
            SpeedPhase.from_mapping(dict(start_s=0, speed_mps=float("inf")), label="test")
        with self.assertRaises(CatalogError):
            ConflictZone.from_mapping(dict(x=0, y=0, radius_m=float("nan")), label="test")

    def test_stay_and_abort_intents_are_distinct(self):
        catalog = load_catalog("configs/ego_intent_response_town03_scenes.yaml")
        scene = catalog.by_id("overtake_01")
        self.assertNotEqual(scene.intents["follow_slow"].speed_at(8), scene.intents["abort_pass"].speed_at(8))
        rear = catalog.by_id("rear_01")
        self.assertAlmostEqual(rear.intents["cruise"].speed_at(8), 30/3.6)
        self.assertNotEqual(catalog.by_id("merge_01").ego.transform, catalog.by_id("cutin_01").ego.transform)

    def test_unknown_scene_cannot_be_silently_replaced(self):
        catalog = load_catalog("configs/ego_intent_response_town03_scenes.yaml")
        with self.assertRaises(CatalogError):
            catalog.select(["unknown_scene"])

    def test_lane_changes_have_common_prefix_until_trigger(self):
        catalog = load_catalog("configs/ego_intent_response_town03_scenes.yaml")
        for scene in catalog.scenes:
            if scene.category in {"merge", "cut_in", "overtake_slow"}:
                routes = [i.route for i in scene.intents.values()]
                self.assertTrue(all(r[:8] == scene.ego.route[:8] for r in routes))
            self.assertTrue(all(i.route_switch_s >= i.trigger_s for i in scene.intents.values()))


class ControllerTests(unittest.TestCase):
    def test_reactive_controller_yields_when_ego_occupies_zone(self):
        route = (TransformSpec(0, 0), TransformSpec(20, 0), TransformSpec(40, 0))
        controller = ReactiveYieldController(RouteSpeedController(route), ConflictZone(10, 0, 6))
        ego = _Actor(10, 0, 0)
        npc = _Actor(5, 0, 6)
        output = controller.step(npc, ego, desired_speed_mps=8)
        self.assertEqual(output.reason, "yield_ego_occupies_conflict_zone")
        self.assertGreater(output.brake, 0.0)
        self.assertEqual(output.mode, "reactive_yield_v1")

    def test_seed_is_matched_across_intent_and_profile_but_changes_by_scene_or_repeat(self):
        self.assertEqual(seed_for(41021, 2, 4), seed_for(41021, 2, 4))
        self.assertNotEqual(seed_for(41021, 2, 4), seed_for(41021, 2, 5))
        self.assertNotEqual(seed_for(41021, 2, 4), seed_for(41021, 3, 4))

    def test_lookahead_does_not_skip_forward_each_stationary_tick(self):
        route = tuple(TransformSpec(i, 0) for i in range(0, 100, 4))
        controller = RouteSpeedController(route)
        actor = _Actor(0, 0, 0)
        self.assertEqual(controller._target(actor), controller._target(actor))

    def test_reactive_does_not_yield_to_vehicle_behind_it(self):
        controller = ReactiveYieldController(RouteSpeedController((TransformSpec(0,0), TransformSpec(100,0))), ConflictZone(100,0,5))
        output = controller.step(_Actor(30,0,8), _Actor(25,0,3), 8)
        self.assertEqual(output.reason, "no_yield_condition")

    def test_reactive_does_not_predict_arrival_when_ego_moves_away(self):
        controller = ReactiveYieldController(RouteSpeedController((TransformSpec(0,0), TransformSpec(100,0))), ConflictZone(60,0,5))
        self.assertTrue(math.isinf(controller._time_to_zone(_Actor(80,0,8))))

    def test_reactive_closing_gap_causes_braking(self):
        controller = ReactiveYieldController(RouteSpeedController((TransformSpec(0,0), TransformSpec(100,0))), ConflictZone(100,0,5))
        output = controller.step(_Actor(10,0,8), _Actor(15,0,3), 8)
        self.assertEqual(output.reason, "yield_closing_gap")
        self.assertGreater(output.brake, 0)


class MetricsTests(unittest.TestCase):
    @staticmethod
    def _tensor(effect: float, noise: float) -> np.ndarray:
        data = np.zeros((3, 4, 8, 2), dtype=float)
        for intent in range(3):
            for repeat in range(4):
                data[intent, repeat, :, 0] = intent * effect + (repeat - 1.5) * noise
        return data

    def test_between_within_separates_effect_from_noise(self):
        between, within = between_within(self._tensor(effect=2.0, noise=0.1))
        self.assertGreater(between, 1.5)
        self.assertGreater(within, 0.0)
        self.assertGreater(ratio_between_within(between, within, 0.05), 3.0)

    def test_zero_noise_uses_pre_registered_floor(self):
        between, within = between_within(self._tensor(effect=0.2, noise=0.0))
        self.assertEqual(within, 0.0)
        self.assertAlmostEqual(ratio_between_within(between, within, 0.05), between / 0.05)

    def test_bh_adjustment_is_monotone_in_rank_order(self):
        q = benjamini_hochberg([0.001, 0.02, 0.04, 0.8])
        self.assertLessEqual(q[0], q[1])
        self.assertLessEqual(q[1], q[2])
        self.assertLessEqual(q[2], q[3])

    def test_nonfinite_measurements_are_rejected(self):
        data = self._tensor(1, 0.1)
        data[0,0,0,0] = float("nan")
        with self.assertRaises(MetricsError):
            between_within(data)

    def test_large_effect_with_high_noise_does_not_mean_clear_response(self):
        between, within = between_within(self._tensor(2, 10))
        self.assertLess(ratio_between_within(between, within, .05), 3)

    def test_small_absolute_effect_does_not_pass_despite_huge_ratio(self):
        rows = [dict(signal=s, between=.01, ratio_ci_low=50, ratio_ci_high=100, q_value=.001) for s in ("position","velocity","acceleration")]
        self.assertNotEqual(classify_scene(rows, MetricsConfig())[0], "clear_response")

    def test_classification_needs_ratio_effect_and_fdr(self):
        config = MetricsConfig()
        rows = [
            {"signal": "position", "between": 0.7, "ratio_ci_low": 3.1, "ratio_ci_high": 4.1, "q_value": 0.01},
            {"signal": "velocity", "between": 0.1, "ratio_ci_low": 1.0, "ratio_ci_high": 1.2, "q_value": 0.9},
            {"signal": "acceleration", "between": 0.1, "ratio_ci_low": 1.0, "ratio_ci_high": 1.2, "q_value": 0.9},
        ]
        self.assertEqual(classify_scene(rows, config)[0], "clear_response")
        rows[0]["q_value"] = 0.2
        self.assertEqual(classify_scene(rows, config)[0], "inconclusive")

    def test_analysis_and_report_accept_valid_raw_schema(self):
        rows = []
        for intent_index, intent in enumerate(("a", "b", "c")):
            for repeat in range(1, 4):
                for tick in range(8):
                    row = {field: 0 for field in ACTOR_STATE_FIELDS}
                    row.update({
                        "run_id": f"{intent}_{repeat}", "scene_id": "synthetic", "category": "merge", "profile": "tm_default",
                        "intent": intent, "repeat": repeat, "seed": repeat, "tick": tick, "time_s": tick * 0.05,
                        "relative_time_s": tick * 0.05, "actor_key": "npc_conflict", "actor_id": 1,
                        "actor_role": "critical_conflict", "actor_type": "vehicle.audi.tt",
                        "x": intent_index + repeat * 0.01, "y": tick * 0.1, "vx": intent_index * 0.2,
                        "vy": 0.0, "ax": 0.0, "ay": 0.0, "reaction_reason": "test", "controller_mode": "test",
                    })
                    rows.append(row)
        states = pd.DataFrame(rows)
        config = MetricsConfig(analysis_start_offset_s=0, analysis_end_offset_s=0.35, bootstrap_samples=20, permutation_samples=20)
        actor, aggregate, summary = analyze_completed_runs(
            states,
            [{"scene_id": "synthetic", "category": "merge", "trigger_s": 0, "participant_keys": ["npc_conflict"], "intent_ids": ["a", "b", "c"]}],
            config,
        )
        self.assertEqual(len(actor), 3)
        self.assertEqual(len(aggregate), 3)
        self.assertEqual(len(summary), 1)
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            outputs = write_reports(temp, actor_effects=actor, aggregate_effects=aggregate, summary=summary, provenance={"test": True})
            self.assertTrue(outputs["summary"].exists())
            self.assertTrue(outputs["report"].exists())

    def test_missing_and_duplicate_ticks_are_not_silently_dropped(self):
        rows = [dict(scene_id="s", profile="p", intent=i, repeat=r, seed=r, actor_key="npc", relative_time_s=t*.05,
                     x=0.,y=0.,vx=0.,vy=0.,ax=0.,ay=0.) for i in "abc" for r in [1,2] for t in range(3)]
        config = MetricsConfig(analysis_start_offset_s=0, analysis_end_offset_s=.1, bootstrap_samples=5, permutation_samples=5)
        kwargs = dict(scene_id="s",profile="p",category="merge",trigger_s=0,participant_keys=["npc"],intents=list("abc"),config=config)
        with self.assertRaises(MetricsError):
            compute_scene_profile_metrics(pd.DataFrame(rows[:-1]), **kwargs)
        with self.assertRaises(MetricsError):
            compute_scene_profile_metrics(pd.DataFrame(rows + [rows[0]]), **kwargs)
        with self.assertRaises(MetricsError):
            compute_scene_profile_metrics(pd.DataFrame([x for x in rows if x["relative_time_s"] != .05]), **kwargs)
        # Ego rows must not hide a tick absent from every NPC repetition.
        ego_rows = [{**x, "actor_key": "ego"} for x in rows]
        with self.assertRaises(MetricsError):
            compute_scene_profile_metrics(pd.DataFrame([x for x in rows if x["relative_time_s"] != .05]+ego_rows), **kwargs)

    def test_resampling_is_reproducible(self):
        rows = [dict(scene_id="s", profile="p", intent=i, repeat=r, seed=r, actor_key="npc", relative_time_s=t*.05,
                     x=float(ord(i)-97)+r*.01,y=0.,vx=0.,vy=0.,ax=0.,ay=0.) for i in "abc" for r in [1,2,3] for t in range(3)]
        kwargs = dict(scene_id="s",profile="p",category="merge",trigger_s=0,participant_keys=["npc"],intents=list("abc"),
                      config=MetricsConfig(analysis_start_offset_s=0,analysis_end_offset_s=.1,bootstrap_samples=30,permutation_samples=30))
        first = compute_scene_profile_metrics(pd.DataFrame(rows), **kwargs)
        self.assertEqual(first, compute_scene_profile_metrics(pd.DataFrame(rows), **kwargs))

    def test_empty_report_does_not_claim_success(self):
        with TemporaryDirectory() as folder:
            paths = write_reports(folder, actor_effects=pd.DataFrame(), aggregate_effects=pd.DataFrame(), summary=pd.DataFrame(), provenance={})
            decision = json.loads(paths["decision"].read_text())
            self.assertFalse(decision["matrix_complete"])
            self.assertIsNone(decision["baseline_passes_half_scene_target"])

    def test_baseline_failure_notice_contains_numeric_diagnosis(self):
        rows = []
        for index in range(24):
            row = dict(scene_id=f"s_{index}",profile="tm_default",category="merge",classification="almost_unchanged",
                       classification_reason="effect_below_absolute_threshold",n_repeats=10)
            for signal in ("position","velocity","acceleration"):
                row.update({signal+"_between": .01, signal+"_within": .02, signal+"_ratio": .5})
            rows.append(row)
        with TemporaryDirectory() as folder:
            paths = write_reports(folder,actor_effects=pd.DataFrame(),aggregate_effects=pd.DataFrame(),summary=pd.DataFrame(rows),provenance={},baseline_only=True)
            text = paths["baseline_failure_notice"].read_text()
            self.assertIn("0/24",text)
            self.assertIn("B=0.010, W=0.020, R=0.50",text)
            self.assertFalse(json.loads(paths["decision"].read_text())["baseline_passes_half_scene_target"])

    def test_optional_trajectory_plot_is_valid_svg(self):
        rows = [dict(scene_id="s",profile="tm_default",intent=i,actor_key=a,relative_time_s=t*.05,x=t,y=float(ord(i)-97))
                for i in "abc" for a in ["ego","npc"] for t in range(3)]
        with TemporaryDirectory() as folder:
            paths = write_trajectory_plots(folder,pd.DataFrame(rows))
            self.assertEqual(len(paths),1)
            import xml.etree.ElementTree as ET
            self.assertEqual(ET.parse(paths[0]).getroot().tag,"{http://www.w3.org/2000/svg}svg")

    def test_collision_observation_remains_valid_but_flagged(self):
        rows = [dict(scene_id="s", profile="p", intent=i, repeat=r, seed=r, actor_key="npc", relative_time_s=t*.05,
                     x=float(ord(i)-97), y=0., vx=0., vy=0., ax=0., ay=0., collision=(i=="a"))
                for i in "abc" for r in [1,2,3] for t in range(3)]
        _, _, summary = analyze_completed_runs(pd.DataFrame(rows), [dict(scene_id="s",category="merge",trigger_s=0,participant_keys=["npc"],intent_ids=list("abc"))],
                     MetricsConfig(analysis_start_offset_s=0,analysis_end_offset_s=.1,bootstrap_samples=10,permutation_samples=10))
        self.assertEqual(summary.iloc[0].collision_run_count,3)
        self.assertTrue(summary.iloc[0].collision_associated)
        self.assertNotEqual(summary.iloc[0].classification,"incomplete")


class RunnerTests(unittest.TestCase):
    def test_config_rejects_nonfinite_timing(self):
        with self.assertRaises(ExperimentError):
            ExperimentConfig.from_mapping({"fixed_delta_s": float("nan")})

    def test_resume_verifies_catalog_configuration_and_file_hash(self):
        scene = load_catalog("configs/ego_intent_response_town03_scenes.yaml").scenes[0]
        with TemporaryDirectory() as folder:
            runner = ExperimentRunner(replace(ExperimentConfig(), output_dir=folder), {}, "catalog1")
            states, metadata = runner._run_paths(scene, "tm_default", "merge_now", 1)
            states.parent.mkdir(parents=True)
            states.write_text("valid,data\n", encoding="utf-8")
            metadata.write_text(json.dumps(dict(status="complete",config_hash=runner.effective_hash,catalog_hash="catalog1",states_sha256=hashlib.sha256(states.read_bytes()).hexdigest())))
            self.assertTrue(runner.is_complete(scene,"tm_default","merge_now",1))
            states.write_text("corrupt", encoding="utf-8")
            self.assertFalse(runner.is_complete(scene,"tm_default","merge_now",1))

    def test_completed_cell_cannot_be_overwritten_after_fixture_change(self):
        scene = load_catalog("configs/ego_intent_response_town03_scenes.yaml").scenes[0]
        with TemporaryDirectory() as folder:
            runner = ExperimentRunner(replace(ExperimentConfig(),output_dir=folder),{},"new_catalog")
            _, metadata = runner._run_paths(scene,"tm_default","merge_now",1)
            metadata.parent.mkdir(parents=True)
            metadata.write_text(json.dumps(dict(status="complete",config_hash=runner.effective_hash,catalog_hash="old_catalog")))
            with self.assertRaises(ExperimentError):
                runner.check_existing_cell(scene,"tm_default","merge_now",1)

    def test_repetition_and_transport_changes_do_not_change_observation_hash(self):
        first = ExperimentRunner(ExperimentConfig(),{},"catalog")
        second = ExperimentRunner(replace(ExperimentConfig(),port=2100,repetitions=20,output_dir="other"),{},"catalog")
        self.assertEqual(first.effective_hash,second.effective_hash)
        changed = ExperimentRunner(replace(ExperimentConfig(),tm_following_distance_m=8),{},"catalog")
        self.assertNotEqual(first.effective_hash,changed.effective_hash)

    def test_spawn_failure_is_invalid_and_cleanup_runs(self):
        scene = load_catalog("configs/ego_intent_response_town03_scenes.yaml").scenes[0]
        with TemporaryDirectory() as folder:
            runner = ExperimentRunner(replace(ExperimentConfig(),output_dir=folder),{},"catalog")
            runner.environment = Mock()
            runner.environment.spawn_fixture.side_effect = ExperimentError("spawn blocked")
            runner.environment.provenance.return_value = {}
            runner.environment._collision_events = []
            result = runner.run_single(scene,profile="tm_default",intent_id="merge_now",repeat=1,scene_index=0)
            self.assertEqual(result["status"],"invalid")
            self.assertFalse(Path(result["states_path"]).exists())
            self.assertIn("spawn blocked",json.loads(Path(result["metadata_path"]).read_text())["error"])
            runner.environment.cleanup_fixture.assert_called_once()

    def test_foreign_traffic_is_rejected_not_destroyed(self):
        env = CarlaExperimentWorld(ExperimentConfig())
        env.world = Mock()
        foreign = Mock(id=999,type_id="vehicle.foreign")
        env.world.get_actors.return_value.filter.side_effect = lambda pattern: [foreign] if pattern=="vehicle.*" else []
        with self.assertRaises(ExperimentError):
            env._require_empty_world()
        foreign.destroy.assert_not_called()

    def test_preflight_rejects_offroad_short_and_overlapping_fixture(self):
        scene = load_catalog("configs/ego_intent_response_town03_scenes.yaml").scenes[0]
        ego = replace(scene.ego,route=scene.ego.route[:2])
        npc = replace(scene.npcs[0],transform=scene.ego.transform)
        scene = replace(scene,ego=ego,npcs=(npc,))
        world = Mock()
        world.get_map.return_value.get_waypoint.return_value = None
        with patch("experiments.ego_intent_response.runner.carla",Mock()):
            errors = preflight_scene(world,scene)
        self.assertTrue(any("not on a driving lane" in x for x in errors))
        self.assertTrue(any("shorter than 40m" in x for x in errors))
        self.assertTrue(any("initial overlap" in x for x in errors))

    def test_nested_completed_state_loader_excludes_invalid_runs_and_audits(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)/"runs"/"p"/"s"/"i"/"rep_01"
            root.mkdir(parents=True)
            state = root/"states.csv"
            state.write_text("scene_id,actor_key\ns,npc\n")
            meta = root/"metadata.json"
            meta.write_text(json.dumps(dict(status="complete",states_sha256=hashlib.sha256(state.read_bytes()).hexdigest())))
            self.assertEqual(len(read_complete_state_files(folder)),1)
            meta.write_text(json.dumps(dict(status="invalid")))
            self.assertEqual(len(read_complete_state_files(folder)),0)

    def test_cleanup_only_destroys_owned_actors(self):
        env = CarlaExperimentWorld(ExperimentConfig())
        owned, foreign = Mock(), Mock()
        env.world = Mock()
        env._owned_actors = [owned]
        env.cleanup_fixture()
        owned.destroy.assert_called_once()
        foreign.destroy.assert_not_called()
        env.world.tick.assert_called_once()


class CliTests(unittest.TestCase):
    def test_audit_checks_actor_tick_completeness_and_excludes_raw_analysis(self):
        from scripts.run_ego_intent_response import _write_audit_summary
        with TemporaryDirectory() as folder:
            for repeat in (1,2):
                root = Path(folder)/"audits"/"tm_default"/"s"/"a"/f"rep_{repeat:02d}"
                root.mkdir(parents=True)
                rows = [dict(actor_key="npc",relative_time_s=t*.05,x=float(t),y=0.,vx=1.,vy=0.) for t in range(3)]
                if repeat == 2:
                    rows.pop()
                state = root/"states.csv"
                pd.DataFrame(rows).to_csv(state,index=False)
                (root/"metadata.json").write_text(json.dumps(dict(status="complete",seed=1,config_hash="c",catalog_hash="s",states_sha256=hashlib.sha256(state.read_bytes()).hexdigest())))
            _write_audit_summary(Path(folder))
            summary = pd.read_csv(Path(folder)/"reproducibility_audit.csv")
            self.assertEqual(summary.iloc[0].status,"missing_actor_or_ticks")
            self.assertTrue(read_complete_state_files(folder).empty)

    def test_retry_preserves_cell_and_resume_skips_complete_runs(self):
        from scripts import run_ego_intent_response as cli
        catalog = load_catalog("configs/ego_intent_response_town03_scenes.yaml")
        with TemporaryDirectory() as folder:
            fake = Mock()
            fake.config = replace(ExperimentConfig(),output_dir=folder,repetitions=1)
            fake.output_dir = Path(folder)
            fake.environment.provenance.return_value = {"opendrive_sha256":catalog.opendrive_sha256}
            fake.preflight.return_value = {"merge_01":[]}
            fake.is_complete.return_value = False
            fake.run_single.side_effect = [dict(status="invalid",error="spawn"),dict(status="complete",error="")]
            argv = ["experiment","--scene","merge_01","--intent","merge_now","--profile","tm_default","--repetitions","1","--skip-audit","--output-dir",folder]
            with patch.object(cli,"ExperimentRunner",return_value=fake), patch.object(cli,"_write_analysis"), patch("sys.argv",argv):
                self.assertEqual(cli.main(),0)
            self.assertEqual(fake.run_single.call_count,2)
            self.assertEqual(fake.run_single.call_args_list[0],fake.run_single.call_args_list[1])
            self.assertEqual(len(pd.read_csv(Path(folder)/"invalid_runs.csv")),1)
            fake.run_single.reset_mock()
            fake.is_complete.return_value = True
            with patch.object(cli,"ExperimentRunner",return_value=fake), patch.object(cli,"_write_analysis"), patch("sys.argv",argv+["--resume"]):
                self.assertEqual(cli.main(),0)
            fake.run_single.assert_not_called()


if __name__ == "__main__":
    unittest.main()
