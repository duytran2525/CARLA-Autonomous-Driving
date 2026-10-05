"""Opt-in integration smoke against an otherwise empty CARLA 0.9.16 server.

Set CARLA_EIR_INTEGRATION=1, optionally CARLA_EIR_PORT/CARLA_EIR_TM_PORT.
This loads Town03 and takes ownership only of the actors it creates.
"""
from dataclasses import replace
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.ego_intent_response.runner import ExperimentRunner, load_experiment_config
from experiments.ego_intent_response.scenario_catalog import PROFILES, load_catalog


@unittest.skipUnless(os.environ.get("CARLA_EIR_INTEGRATION") == "1", "requires explicit CARLA integration opt-in")
class CarlaIntegrationTests(unittest.TestCase):
    def test_all_fixtures_preflight_and_six_family_smoke(self):
        project = Path(__file__).resolve().parent.parent
        config, raw = load_experiment_config(project / "configs/ego_intent_response_town03.yaml")
        catalog = load_catalog(project / config.catalog_path)
        with TemporaryDirectory(prefix="carla_eir_smoke_") as folder:
            config = replace(config, output_dir=folder, repetitions=1,
                             host=os.environ.get("CARLA_EIR_HOST", config.host),
                             port=int(os.environ.get("CARLA_EIR_PORT", config.port)),
                             tm_port=int(os.environ.get("CARLA_EIR_TM_PORT", config.tm_port)))
            runner = ExperimentRunner(config, raw, catalog.source_hash)
            try:
                runner.start()
                self.assertEqual(runner.environment.provenance()["opendrive_sha256"], catalog.opendrive_sha256)
                self.assertTrue(all(not reasons for reasons in runner.preflight(catalog.scenes).values()))
                categories = set()
                for index, scene in enumerate(catalog.scenes):
                    if scene.category in categories:
                        continue
                    categories.add(scene.category)
                    for profile in PROFILES:
                        for intent in scene.intents:
                            with self.subTest(scene=scene.scene_id, profile=profile, intent=intent):
                                result = runner.run_single(scene, profile=profile, intent_id=intent, repeat=1, scene_index=index)
                                self.assertEqual(result["status"], "complete", result["error"])
                                self.assertTrue(runner.is_complete(scene, profile, intent, 1))
            finally:
                runner.close()


if __name__ == "__main__":
    unittest.main()
