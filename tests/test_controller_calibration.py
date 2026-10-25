"""Independent controller calibration recipe, pairing and selection checks."""

import copy
import json
import unittest
from pathlib import Path

from tools.controller_calibration import recipe_config, summarize, validate_profile


class ControllerCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads(Path("configs/issue23/source-epoch-study.json").read_text())[
            "runner_config"
        ]
        self.base["development_entities"] = ["fixture"]
        self.cohort = {
            "seeds": [42, 43, 44],
            "budgets": {str(b): {"entities": [{"entity_id": "fixture"}]} for b in (7, 14, 28)},
        }
        self.rows = []
        for recipe in range(4):
            for budget in (7, 14, 28):
                for seed in (42, 43, 44):
                    config = copy.deepcopy(self.base)
                    for name in ("controller", "initial_training", "online_training"):
                        config[name]["seed"] = seed
                    self.rows.append(
                        {
                            "recipe": recipe,
                            "method": {"name": "adaptive"},
                            "binding": {
                                "input": {"history_days": budget, "entity_id": "fixture"},
                                "config": recipe_config(config, recipe, seed),
                            },
                            "issued_days": 90,
                            "scored_days": 10,
                            "active_mae_kwh": [4.0, 3.0, 3.0, 5.0][recipe],
                        }
                    )

    def test_selection_exact_tie_and_complete_nulls(self):
        self.assertEqual(summarize(self.rows, self.cohort)["provisional_choice"], 1)
        for row in self.rows:
            row.update(active_mae_kwh=None, scored_days=0)
        self.assertIsNone(summarize(self.rows, self.cohort)["provisional_choice"])

    def test_no_mutation_and_exact_declared_config(self):
        old = copy.deepcopy(self.base)
        config = recipe_config(self.base, 3, 42)
        self.assertEqual(self.base, old)
        self.assertEqual(config["controller"]["initial_lambda"], 0.1)
        self.assertEqual(config["controller"]["min_valid_days"], 10)
        self.assertEqual(config["controller"]["delta"], 0.005)
        self.assertEqual(config["controller"]["segment_days"], 5)
        self.assertEqual(config["initial_training"], old["initial_training"])
        self.assertEqual(config["online_training"], old["online_training"])

    def test_mislabeled_or_unpaired_results_fail(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["binding"]["config"]["controller"]["delta"] = 0.1
        for bad in (rows, self.rows[:-1], self.rows + self.rows[:1]):
            with self.assertRaises(ValueError):
                summarize(bad, self.cohort)

    def test_unexpected_profiles_and_seed_fail(self):
        for recipe, seed in ((True, 42), (4, 42), (0, 7)):
            with self.assertRaises(ValueError):
                recipe_config(self.base, recipe, seed)
        for name, value in (("alpha", 0.1), ("block_days", 7), ("resamples", 500)):
            base = copy.deepcopy(self.base)
            base["controller"][name] = value
            with self.assertRaises(ValueError):
                recipe_config(base, 0, 42)

    def test_finite_search_cannot_silently_expand(self):
        profile = json.loads(Path("configs/issue23/controller-calibration.json").read_text())
        validate_profile(profile)
        for name, value in (
            ("recipes", profile["recipes"] * 2),
            ("seeds", [42]),
            ("selection_rule", "best_seed"),
        ):
            with self.assertRaises(ValueError):
                validate_profile({**profile, name: value})


if __name__ == "__main__":
    unittest.main()
