"""Separate-city provenance and shared cost accounting, without training."""

import copy
import unittest

from ev_evaluation.costs import comparison_costs
from tools.analyze_charged_matched import validate_collection
from tools.charged_matched_development import method_configs, primary_recipe


class CityCollectionTests(unittest.TestCase):
    def setUp(self):
        self.primary = {
            "choices": {
                "source_epochs": 10,
                "controller_recipe": 1,
                "fixed_lambda": 1.0,
                "proxy_recipes": dict.fromkeys(
                    ("source_error", "uncertainty", "drift", "parameter_retention"), 0
                ),
                "unique_method_names": [
                    "adaptive",
                    "seasonal_naive",
                    "target_only",
                    "frozen_source",
                    "full_finetuning",
                    "fixed_retention",
                    "online_best",
                    "source_error",
                    "uncertainty",
                    "drift",
                    "parameter_retention",
                    "without_source_initialization",
                    "block7",
                    "block28",
                ],
            }
        }
        self.cohort = {
            "namespace": "charged-JHB",
            "seeds": [42, 43, 44],
            "source_population_sha256": "JHB-source-population",
            "budgets": {
                str(b): {"manifest_sha256": f"JHB-{b}", "entities": [{"entity_id": "site"}]}
                for b in (7, 14, 28)
            },
        }
        self.files = {"ev_models/model.py": "model", "ev_runner/run.py": "runner"}
        code = {"dirty": False, "files": self.files}
        self.matrix = {
            "namespace": "charged-JHB",
            "source_epochs": 10,
            "code": code,
            "sources": [],
            "runs": [],
        }
        _, _, training = primary_recipe(self.primary, 42, "unused")
        for seed in self.cohort["seeds"]:
            self.matrix["sources"].append(
                {
                    "seed": seed,
                    "sha256": f"JHB-weights-{seed}",
                    "run": {
                        "input_binding": {
                            "stage": "source",
                            "dataset_id": "charged",
                            "city_id": "JHB",
                            "input_manifest_sha256": "JHB-7",
                        },
                        "source_population_sha256": "JHB-source-population",
                        "training_config": {**training, "seed": seed, "epochs": 10},
                        "checkpoint_sha256": f"JHB-weights-{seed}",
                        "code": {"dirty": False, "files": {"ev_models/model.py": "model"}},
                    },
                }
            )
            for budget in (7, 14, 28):
                for method, config in method_configs(self.primary, seed, "site").items():
                    self.matrix["runs"].append(
                        {
                            "comparison_variant": method,
                            "method": config["method"],
                            "source_checkpoint_sha256": f"JHB-weights-{seed}",
                            "code": code,
                            "binding": {
                                "config": config,
                                "environment": {"device": "fixture", "torch": "same-runtime"},
                                "source_population_sha256": "JHB-source-population",
                                "input": {
                                    "dataset_id": "charged",
                                    "city_id": "JHB",
                                    "entity_id": "site",
                                    "history_days": budget,
                                    "input_manifest_sha256": f"JHB-{budget}",
                                    "source_checkpoint_sha256": f"JHB-weights-{seed}",
                                },
                            },
                            "issued_days": 90,
                            "scored_days": 0,
                            "active_mae_kwh": None,
                        }
                    )

    def check(self, matrix):
        return validate_collection(matrix, self.cohort, self.primary, self.files)

    def test_complete_separate_city_keeps_null_cells_and_three_own_sources(self):
        self.assertEqual(set(self.check(self.matrix)), {42, 43, 44})
        self.assertEqual(len(self.matrix["runs"]), 126)
        self.assertTrue(all(r["active_mae_kwh"] is None for r in self.matrix["runs"]))

    def test_wrong_source_city_population_seed_training_or_code_fails(self):
        for field, value in (
            ("source_population_sha256", "UrbanEV-population"),
            ("checkpoint_sha256", "UrbanEV-weights"),
            ("training_config", {}),
            ("code", {"dirty": True, "files": {}}),
        ):
            bad = copy.deepcopy(self.matrix)
            bad["sources"][0]["run"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(bad)
        for mode in ("city", "missing", "duplicate", "epochs"):
            bad = copy.deepcopy(self.matrix)
            if mode == "city":
                bad["sources"][0]["run"]["input_binding"]["city_id"] = "AMS"
            elif mode == "missing":
                bad["sources"].pop()
            elif mode == "duplicate":
                bad["sources"].append(bad["sources"][0])
            else:
                bad["source_epochs"] = 1
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.check(bad)

    def test_cross_runtime_target_population_and_changed_algorithms_fail(self):
        for mode in ("runtime", "population", "code", "missing-cell"):
            bad = copy.deepcopy(self.matrix)
            row = bad["runs"][0]
            if mode == "runtime":
                row["binding"]["environment"]["torch"] = "other-runtime"
            elif mode == "population":
                row["binding"]["source_population_sha256"] = "other-city"
            elif mode == "code":
                row["code"] = {"dirty": False, "files": {"ev_runner/run.py": "changed"}}
            else:
                bad["runs"].pop()
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.check(bad)


class ComparisonCostTests(unittest.TestCase):
    def test_candidates_ensemble_audits_and_source_reuse_count_actual_work(self):
        costs = {
            "inference_seconds": 1,
            "update_seconds": 2,
            "audit_inference_seconds": 3,
            "audit_update_seconds": 4,
            "controller_seconds": 5,
            "proxy_seconds": 6,
        }

        def report(members, candidates, elapsed, peak):
            return {
                "elapsed_seconds": elapsed,
                "candidate_steps": 7,
                "audit_steps": 8,
                "initial_logs": [{"steps": 9}, {"steps": 10}],
                "candidate_levels": list(range(candidates)),
                "binding": {"uncertainty_members": list(range(members))},
                "cost": costs,
                "gpu_peak_allocated_bytes": peak,
                "gpu_peak_reserved_bytes": peak + 1,
            }

        cells = {
            (7, "a", 42, "adaptive"): {"report": report(0, 3, 20, 100)},
            (14, "a", 42, "adaptive"): {"report": report(0, 3, 30, 200)},
            (7, "a", 42, "uncertainty"): {"report": report(3, 1, 40, 300)},
        }
        sources = [
            {"elapsed_seconds": 11, "logs": [{"steps": 12}], "environment": {"runtime": "source"}}
        ]
        result = comparison_costs(cells, sources)
        adaptive = result["costs"]["adaptive"]
        self.assertEqual(adaptive["run_count"], 2)
        self.assertEqual(adaptive["elapsed_seconds_sum"], 50)
        self.assertEqual(adaptive["candidate_steps"], 14)
        self.assertEqual(adaptive["audit_steps"], 16)
        self.assertEqual(adaptive["initial_adaptation_steps"], 38)
        self.assertEqual(adaptive["candidate_models_per_run"], [3])
        self.assertEqual(adaptive["component_seconds_sum"]["proxy_seconds"], 12)
        self.assertEqual(adaptive["gpu_peak_allocated_bytes_max"], 200)
        self.assertEqual(result["costs"]["uncertainty"]["uncertainty_source_members_per_run"], [3])
        self.assertEqual(result["source_cost_reused_once"]["source_training_elapsed_seconds"], 11)
        self.assertEqual(result["source_cost_reused_once"]["source_training_optimizer_steps"], 12)


if __name__ == "__main__":
    unittest.main()
