"""Independent finite-grid, pairing and station-weighting fixtures."""

import copy
import json
import unittest
from pathlib import Path

from tools.source_epoch_sweep import summarize, validate_profile


class SourceStudyTests(unittest.TestCase):
    def setUp(self):
        self.cohort = {
            "seeds": [42, 43, 44],
            "budgets": {
                str(b): {"entities": [{"entity_id": "a"}, {"entity_id": "b"}]} for b in (7, 14, 28)
            },
        }
        self.rows = []
        for epoch in (1, 3, 10):
            for budget in (7, 14, 28):
                for entity in ("a", "b"):
                    for seed in self.cohort["seeds"]:
                        self.rows.append(
                            {
                                "source_epochs": epoch,
                                "binding": {
                                    "input": {"history_days": budget, "entity_id": entity},
                                    "config": {"initial_training": {"seed": seed}},
                                },
                                "method": {"name": "full_finetuning"},
                                "issued_days": 90,
                                "scored_days": 2 if entity == "a" else 80,
                                "active_mae_kwh": (1 if epoch in (1, 3) else 4)
                                + (0 if entity == "a" else 8),
                            }
                        )

    def test_equal_station_weight_and_predeclared_tie_break(self):
        result = summarize(self.rows, self.cohort, [1, 3, 10])
        self.assertEqual(result["provisional_source_epochs"], 1)
        self.assertEqual(result["candidates"]["1"]["selection_score"], 5)
        self.assertFalse(result["best_at_grid_boundary"])

    def test_null_units_remain_null_not_zero(self):
        for row in self.rows:
            row["active_mae_kwh"] = None
            row["scored_days"] = 0
        result = summarize(self.rows, self.cohort, [1, 3, 10])
        self.assertIsNone(result["provisional_source_epochs"])
        self.assertIsNone(result["candidates"]["1"]["selection_score"])
        self.assertEqual(result["candidates"]["1"]["budgets"]["7"]["unscored_entities"], ["a", "b"])

    def test_missing_duplicate_or_different_coverage_fails(self):
        variants = [self.rows[:-1], self.rows + self.rows[:1]]
        changed = copy.deepcopy(self.rows)
        changed[0]["scored_days"] = 1
        variants.append(changed)
        for rows in variants:
            with self.assertRaises(ValueError):
                summarize(rows, self.cohort, [1, 3, 10])

    def test_mixed_seed_availability_and_nonfinite_scores_fail(self):
        for value in (None, float("nan"), -1):
            rows = copy.deepcopy(self.rows)
            rows[0]["active_mae_kwh"] = value
            with self.assertRaises(ValueError):
                summarize(rows, self.cohort, [1, 3, 10])

    def test_profile_rejects_grid_extensions_and_wrong_method(self):
        profile = json.loads(Path("configs/issue23/source-epoch-study.json").read_text())
        validate_profile(profile, self.cohort)
        for field, value in (
            ("source_epochs", [1, 3, 10, 30]),
            ("method", "adaptive"),
            ("seeds", [7, 11, 19]),
        ):
            changed = copy.deepcopy(profile)
            changed[field] = value
            with self.assertRaises(ValueError):
                validate_profile(changed, self.cohort)


if __name__ == "__main__":
    unittest.main()
