"""Independent collection completeness, fingerprint and aggregation fixtures."""

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from ev_evaluation.metrics import DailyError
from ev_models.checkpoint import digest
from tools.analyze_matched import aggregate_cells, authenticate_matrix, select_collection
from tools.controller_calibration import recipe_config as controller_config
from tools.matched_development import comparison_config, variants
from tools.proxy_calibration import METHODS
from tools.proxy_calibration import recipe_config as proxy_config


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads(Path("configs/issue23/source-epoch-study.json").read_text())[
            "runner_config"
        ]
        self.cohort = {
            "seeds": [42, 43, 44],
            "budgets": {
                str(b): {
                    "entities": [{"entity_id": "fixture", "initial_trainable": 2}],
                    "manifest_sha256": "manifest",
                }
                for b in (7, 14, 28)
            },
        }
        self.files = {"fixture": "sha"}
        cfg = json.loads(Path("configs/issue23/fixed-retention-study.json").read_text())
        self.studies = {
            name: {
                "status": "technical_success",
                "code": {"dirty": False, "files": self.files},
                "runs": [],
            }
            for name in ("source", "fixed", "controller", "proxy", "matched")
        }
        self.studies["source"].update(
            profile_sha256=cfg["source_profile_sha256"],
            selection_sha256=cfg["selection_sha256"],
            code={"commit": cfg["source_study_code"], "dirty": False, "files": self.files},
            sources=[
                {
                    "seed": seed,
                    "candidates": [
                        {"epochs": e, "path": "fixture", "sha256": f"source-{seed}"}
                        for e in (1, 3, 10)
                    ],
                }
                for seed in self.cohort["seeds"]
            ],
        )
        for b in (7, 14, 28):
            for seed in (42, 43, 44):
                config = copy.deepcopy(self.base)
                config["development_entities"] = ["fixture"]
                for name in ("initial_training", "online_training", "controller"):
                    config[name]["seed"] = seed
                binding = {
                    "dataset_id": "urbanev",
                    "city_id": "SZH",
                    "history_days": b,
                    "entity_id": "fixture",
                    "input_manifest_sha256": "manifest",
                    "source_checkpoint_sha256": f"source-{seed}",
                }

                def row(c, score):
                    return {
                        "run_id": f"{b}-{seed}-{c['method']['name']}-{score}",
                        "method": copy.deepcopy(c["method"]),
                        "binding": {"config": copy.deepcopy(c), "input": copy.deepcopy(binding)},
                        "source_checkpoint_sha256": f"source-{seed}",
                        "issued_days": 90,
                        "scored_days": 80,
                        "active_mae_kwh": float(score),
                        "active_rmse_kwh": float(score),
                        "commit_chain": "chain",
                        "code": {"dirty": False, "files": self.files},
                    }

                for e in (1, 3, 10):
                    c = copy.deepcopy(config)
                    c["method"] = {"name": "full_finetuning"}
                    self.studies["source"]["runs"].append(
                        {**row(c, 1 if e == 10 else e + 2), "source_epochs": e}
                    )
                for weight, score in ((0.001, 4), (0.01, 3), (0.1, 2), (1.0, 1)):
                    c = copy.deepcopy(config)
                    c["method"] = {"name": "fixed_retention", "fixed_lambda": weight}
                    self.studies["fixed"]["runs"].append({**row(c, score), "fixed_lambda": weight})
                for recipe in range(4):
                    c = controller_config(config, recipe, seed)
                    self.studies["controller"]["runs"].append(
                        {**row(c, 1 if recipe == 1 else recipe + 2), "recipe": recipe}
                    )
                chosen = controller_config(config, 1, seed)
                for method in METHODS:
                    for recipe in range(4):
                        c = proxy_config(chosen, method, recipe)
                        self.studies["proxy"]["runs"].append(
                            {**row(c, recipe + 1), "recipe": recipe}
                        )
                for variant in variants(chosen):
                    c = comparison_config(chosen, variant)
                    self.studies["matched"]["runs"].append(
                        {**row(c, 2), "comparison_variant": variant}
                    )

    def test_complete_collection_recomputes_choices_and_aliases(self):
        cells, choices = select_collection(self.studies, self.cohort, self.files)
        self.assertEqual(len(cells), 126)
        self.assertEqual(choices["source_epochs"], 10)
        self.assertEqual(choices["controller_recipe"], 1)
        self.assertEqual(choices["fixed_lambda"], 1)
        self.assertEqual(choices["aliases"]["without_confidence"], "online_best")
        self.assertTrue(choices["fixed_baseline_in_controller_levels"])
        self.assertEqual(len(choices["unique_method_names"]), 14)

    def test_missing_cell_wrong_source_or_changed_training_fails(self):
        for mode in ("missing", "source", "training"):
            studies = copy.deepcopy(self.studies)
            if mode == "missing":
                studies["matched"]["runs"].pop()
            elif mode == "source":
                studies["fixed"]["runs"][-1]["source_checkpoint_sha256"] = "wrong-source"
            else:
                studies["source"]["runs"][2]["binding"]["config"]["initial_training"][
                    "learning_rate"
                ] = 0.1
            with self.assertRaises(ValueError):
                select_collection(studies, self.cohort, self.files)

    def test_verifier_requires_exact_population_nulls_scores_and_hash(self):
        matrix = {
            "runs": [
                {
                    "run_id": "fixture",
                    "issued_days": 2,
                    "scored_days": 0,
                    "commit_chain": "chain",
                    "active_mae_kwh": None,
                    "active_rmse_kwh": None,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "matrix.json"
            v = root / "verification.json"
            p.write_text(json.dumps(matrix))
            proof = {
                "status": "verified",
                "matrix_sha256": digest(p),
                "runs": [
                    {
                        "run_id": "fixture",
                        "issued": 2,
                        "scored": 0,
                        "commit_chain": "chain",
                        "mae_kwh": None,
                        "rmse_kwh": None,
                    }
                ],
            }
            v.write_text(json.dumps(proof))
            self.assertEqual(authenticate_matrix(p, v), matrix)
            for field, value in (("issued", 1), ("mae_kwh", 0), ("commit_chain", "other")):
                bad = copy.deepcopy(proof)
                bad["runs"][0][field] = value
                v.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    authenticate_matrix(p, v)
            duplicate = {"runs": matrix["runs"] * 2}
            p.write_text(json.dumps(duplicate))
            proof["matrix_sha256"] = digest(p)
            v.write_text(json.dumps(proof))
            with self.assertRaises(ValueError):
                authenticate_matrix(p, v)
            proof["matrix_sha256"] = "different"
            v.write_text(json.dumps(proof))
            with self.assertRaises(ValueError):
                authenticate_matrix(p, v)


class AggregationTests(unittest.TestCase):
    def setUp(self):
        self.cohort = {
            "seeds": [42, 43, 44],
            "budgets": {
                str(b): {
                    "entities": [
                        {"entity_id": "a", "initial_trainable": 2},
                        {"entity_id": "missing", "initial_trainable": 0},
                    ]
                }
                for b in (7, 14, 28)
            },
        }
        self.cells = {}
        origins = [datetime(2026, 10, 23), datetime(2026, 10, 24)]
        for b in (7, 14, 28):
            for entity in ("a", "missing"):
                for seed in (42, 43, 44):
                    for name in ("adaptive", "target_only"):
                        value = 1 if name == "adaptive" else 0
                        errors = (
                            [DailyError(t, value, value**2) for t in origins]
                            if entity == "a"
                            else []
                        )
                        self.cells[b, entity, seed, name] = {
                            "errors": errors,
                            "issued": tuple(t.isoformat() for t in origins),
                        }

    def test_zero_target_baseline_and_null_units_are_explicit(self):
        result = aggregate_cells(self.cells, self.cohort)
        summary = result["station_first"]["7/adaptive"]
        self.assertEqual(summary["macro_mae_kwh"], 1)
        self.assertIsNone(summary["ntr"])
        self.assertEqual(summary["zero_baseline_station_count"], 1)
        self.assertEqual(result["unscored_entities_by_budget"]["7"], ["missing"])
        self.assertIn("7/adaptive/initial_adaptation", result["initialization_strata"])
        self.assertIn("7/adaptive/weekend", result["weekday_weekend"])

    def test_same_count_different_origins_or_seed_missingness_fails(self):
        for mode in ("issued", "scored", "missing_seed"):
            cells = copy.deepcopy(self.cells)
            row = cells[7, "a", 42, "adaptive"]
            if mode == "issued":
                row["issued"] = ("wrong", "other")
            elif mode == "scored":
                row["errors"] = [
                    DailyError(e.origin + timedelta(days=7), e.mae, e.mse) for e in row["errors"]
                ]
            else:
                for name in ("adaptive", "target_only"):
                    cells[7, "a", 42, name]["errors"] = []
            with self.assertRaises(ValueError):
                aggregate_cells(cells, self.cohort)


if __name__ == "__main__":
    unittest.main()
