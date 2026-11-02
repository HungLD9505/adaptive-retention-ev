"""Reject incompatible reference matrices before any comparator training."""

import copy
import unittest

from tools.development_comparators import reference_cells


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.cohort = {
            "seeds": [42, 43, 44],
            "budgets": {
                str(b): {"manifest_sha256": str(b), "entities": [{"entity_id": "x"}]}
                for b in (7, 14, 28)
            },
        }
        self.code = {"model.py": "fixed"}
        rows = []
        for budget in (7, 14, 28):
            for seed in self.cohort["seeds"]:
                for method in ("adaptive", "target_only"):
                    config = {
                        "replay_days": 90,
                        "state_retention": "latest",
                        "development_entities": ["x"],
                        "method": {"name": method},
                        "initial_training": {"seed": seed},
                        "online_training": {"seed": seed},
                        "controller": {"seed": seed},
                    }
                    rows.append(
                        {
                            "binding": {
                                "input": {
                                    "history_days": budget,
                                    "entity_id": "x",
                                    "dataset_id": "urbanev",
                                    "city_id": "SZH",
                                    "input_manifest_sha256": str(budget),
                                },
                                "config": config,
                            },
                            "method": {"name": method},
                            "code": {"files": self.code, "dirty": False},
                            "scored_days": 0,
                        }
                    )
        self.matrix = {"status": "technical_success", "seeds": [42, 43, 44], "runs": rows}

    def test_zero_score_cells_are_preserved(self):
        self.assertEqual(len(reference_cells(self.cohort, self.matrix, self.code)), 9)

    def test_duplicate_or_missing_pair_rejected(self):
        for rows in (self.matrix["runs"][:-1], self.matrix["runs"] + self.matrix["runs"][:1]):
            matrix = {**self.matrix, "runs": rows}
            with self.assertRaises(ValueError):
                reference_cells(self.cohort, matrix, self.code)

    def test_modified_algorithm_rejected(self):
        with self.assertRaises(ValueError):
            reference_cells(self.cohort, self.matrix, {"model.py": "changed"})

    def test_wrong_namespace_and_input_manifest_rejected(self):
        for key, value in (("dataset_id", "charged"), ("input_manifest_sha256", "new")):
            matrix = copy.deepcopy(self.matrix)
            matrix["runs"][0]["binding"]["input"][key] = value
            with self.assertRaises(ValueError):
                reference_cells(self.cohort, matrix, self.code)

    def test_pair_hyperparameter_change_and_seed_change_rejected(self):
        for field, value in (("learning_rate", 0.2), ("seed", 10)):
            matrix = copy.deepcopy(self.matrix)
            matrix["runs"][0]["binding"]["config"]["online_training"][field] = value
            with self.assertRaises(ValueError):
                reference_cells(self.cohort, matrix, self.code)

    def test_failed_reference_rejected(self):
        self.matrix["status"] = "failed"
        with self.assertRaises(ValueError):
            reference_cells(self.cohort, self.matrix, self.code)


if __name__ == "__main__":
    unittest.main()
