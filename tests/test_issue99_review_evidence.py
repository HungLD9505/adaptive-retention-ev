"""Regression fixtures for station-equal baseline readback and loss-free sharing."""

import copy
import unittest

from tools.issue99_baseline_review import ledger_summary
from tools.issue99_fusion_controls import neutral_weights


class ReviewEvidenceTests(unittest.TestCase):
    def test_station_equal_mean_with_unequal_seed_counts(self):
        rows = [
            {
                "model": "GRU",
                "mode": "transfer",
                "target": target,
                "seed": str(seed),
                "mae_kwh": str(value),
            }
            for target, seeds, value in (
                ("1405", [42], 1),
                ("2152", [42, 43, 44], 3),
                ("1153", [42], 4),
                ("1693", [42], 8),
            )
            for seed in seeds
        ]
        self.assertEqual(ledger_summary(rows, "target")[0]["mae_kwh"], 4)
        for bad in (rows + rows[:1], rows[:-1]):
            with self.assertRaises(ValueError):
                ledger_summary(bad, "target")

    def test_sharing_only_uses_availability_and_prior_probability(self):
        cell = {
            "origins": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "available_at": ["2020-01-02", "2020-01-03", "2020-01-04"],
        }
        actual = neutral_weights(cell, 0.43, 0.1)
        for a, b in zip(actual, (0.43, 0.444, 0.4552), strict=True):
            self.assertAlmostEqual(a, b)
        delayed = copy.deepcopy(cell)
        delayed["available_at"][0] = "2020-01-04"
        self.assertEqual(neutral_weights(delayed, 0.43, 0.1), [0.43, 0.43, 0.444])
        cell["labels"] = "deliberately unreadable future outcomes"
        self.assertEqual(neutral_weights(cell, 0.43, 0.1), actual)

    def test_bad_probabilities_and_duplicate_clocks_fail(self):
        for initial, share in ((float("nan"), 0.1), (-1, 0.1), (0.4, 2)):
            with self.assertRaises(ValueError):
                neutral_weights({"origins": [], "available_at": []}, initial, share)
        with self.assertRaises(ValueError):
            neutral_weights(
                {"origins": ["2020-01-01", "2020-01-01"], "available_at": ["2020-01-02"] * 2},
                0.4,
                0.1,
            )


if __name__ == "__main__":
    unittest.main()
