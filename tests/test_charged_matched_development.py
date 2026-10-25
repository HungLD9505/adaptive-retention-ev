"""Fixed recipe transfer, separate-city data and complete comparison fixtures."""

import copy
import unittest
from types import SimpleNamespace

from tools.charged_development_cohort import RULE, choose_entities
from tools.charged_matched_development import (
    method_configs,
    primary_recipe,
    validate_cohort,
    validate_matrix,
)

NAMES = [
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
]


class ChargedReplicationTests(unittest.TestCase):
    def setUp(self):
        self.summary = {
            "choices": {
                "source_epochs": 10,
                "controller_recipe": 1,
                "fixed_lambda": 1.0,
                "proxy_recipes": {
                    m: 0 for m in ("source_error", "uncertainty", "drift", "parameter_retention")
                },
                "unique_method_names": NAMES,
            }
        }
        self.cohort = {
            "namespace": "charged-AMS",
            "selection_rule": RULE,
            "seeds": [42, 43, 44],
            "days": 90,
            "state_retention": "latest",
            "source_population_sha256": "city-source",
            "deployment": "2023-07-01T00:00:00",
            "budgets": {},
        }
        self.data = {}
        for b in (7, 14, 28):
            rows = [
                {
                    "identity": ["charged", "AMS", "fixture"],
                    "role": "development",
                    "status": "ready",
                    "initial_trainable": b - 1,
                }
            ]
            self.data[b] = SimpleNamespace(
                namespace=("charged", "AMS"),
                config={"history_days": b, "deployment": self.cohort["deployment"]},
                clock="publisher-local-naive",
                source_hash="city-source",
                sha256=f"manifest-{b}",
                entities={("charged", "AMS", "fixture"): rows[0]},
            )
            self.cohort["budgets"][str(b)] = choose_entities(
                rows, ("charged", "AMS"), f"manifest-{b}", b
            )

    def test_recipe_transfer_has_all_methods_and_no_primary_weight_path(self):
        before = copy.deepcopy(self.summary)
        epochs, config, _ = primary_recipe(self.summary, 43, "local-city-target")
        configs = method_configs(self.summary, 43, "local-city-target")
        self.assertEqual(epochs, 10)
        self.assertEqual(set(configs), set(NAMES))
        self.assertEqual(config["development_entities"], ["local-city-target"])
        self.assertEqual(config["controller"]["seed"], 43)
        self.assertEqual(configs["fixed_retention"]["method"]["fixed_lambda"], 1)
        self.assertEqual(self.summary, before)
        self.assertNotIn("source", config)
        nonzero = copy.deepcopy(self.summary)
        nonzero["choices"].update(
            controller_recipe=3,
            unique_method_names=NAMES + ["without_confidence", "adaptive_bmin7_reference"],
        )
        self.assertEqual(len(method_configs(nonzero, 42, "fixture")), 16)

    def test_bad_or_incomplete_primary_choices_fail(self):
        for name, value in (
            ("source_epochs", True),
            ("source_epochs", 20),
            ("controller_recipe", 4),
            ("fixed_lambda", 0),
            ("unique_method_names", NAMES[:-1]),
            ("proxy_recipes", {}),
        ):
            bad = copy.deepcopy(self.summary)
            bad["choices"][name] = value
            with self.assertRaises(ValueError):
                primary_recipe(bad, 42, "fixture")

    def test_city_source_population_clock_and_recomputed_cohort_gate(self):
        validate_cohort(self.data, self.cohort)
        for field, value in (
            ("clock", "UTC"),
            ("source_hash", "other-city-source"),
            ("namespace", ("urbanev", "SZH")),
        ):
            bad = copy.deepcopy(self.data)
            setattr(bad[7], field, value)
            with self.assertRaises(ValueError):
                validate_cohort(bad, self.cohort)
        bad = copy.deepcopy(self.cohort)
        bad["budgets"]["7"]["entities"][0]["entity_id"] = "different"
        with self.assertRaises(ValueError):
            validate_cohort(self.data, bad)

    def test_full_cells_sources_and_null_coverage_require_exact_bindings(self):
        rows = []
        for b in (7, 14, 28):
            for seed in (42, 43, 44):
                for name, config in method_configs(self.summary, seed, "fixture").items():
                    rows.append(
                        {
                            "comparison_variant": name,
                            "method": config["method"],
                            "source_checkpoint_sha256": f"city-source-{seed}",
                            "binding": {
                                "config": config,
                                "input": {
                                    "dataset_id": "charged",
                                    "city_id": "AMS",
                                    "entity_id": "fixture",
                                    "history_days": b,
                                    "input_manifest_sha256": f"manifest-{b}",
                                    "source_checkpoint_sha256": f"city-source-{seed}",
                                    "scale_id": "fixed-target-scale",
                                },
                            },
                            "issued_days": 90,
                            "scored_days": 90,
                            "active_mae_kwh": 0.0,
                        }
                    )
        validate_matrix(rows, self.cohort, self.summary)
        for bad in (rows[:-1], rows + rows[:1]):
            with self.assertRaises(ValueError):
                validate_matrix(bad, self.cohort, self.summary)
        for field, value in (
            ("scored_days", 89),
            ("source_checkpoint_sha256", "urban-weights"),
            ("active_mae_kwh", None),
        ):
            bad = copy.deepcopy(rows)
            bad[0][field] = value
            with self.assertRaises(ValueError):
                validate_matrix(bad, self.cohort, self.summary)
        bad = copy.deepcopy(rows)
        bad[0]["binding"]["input"]["city_id"] = "JHB"
        with self.assertRaises(ValueError):
            validate_matrix(bad, self.cohort, self.summary)


if __name__ == "__main__":
    unittest.main()
