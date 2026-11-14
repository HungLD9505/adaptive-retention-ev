"""Saved-vector readback checks independent of private EV artifacts."""

import copy
import unittest

import numpy as np

from tools.fusion_evidence import read_errors


class FusionReadbackTests(unittest.TestCase):
    def cell(self):
        return {
            "scored_days": 2,
            "cell": {
                "stable": [[2.0] * 24] * 2,
                "fast": [[1.0] * 24] * 2,
                "labels": [[0.0] * 24] * 2,
                "origins": ["2026-01-01T00:00:00", "2026-01-03T00:00:00"],
            },
            "arms": {
                "old_fixed": {"mae": 2.0},
                "static_mix": {
                    "weights": [0.4, 0.4],
                    "predictions_kwh": [[1.4] * 24] * 2,
                    "mae": 1.4,
                },
                "fixed_share": {
                    "weights": [0.5, 0.5],
                    "predictions_kwh": [[1.5] * 24] * 2,
                    "mae": 1.5,
                },
            },
        }

    def test_vectors_reconstruct_errors_and_preserve_calendar_gap(self):
        result = read_errors(self.cell(), start="2026-01-01T00:00:00+08:00", days=3)
        np.testing.assert_array_equal(result["fixed"], [2, np.nan, 2])
        np.testing.assert_allclose(result["fixed_share"], [1.5, np.nan, 1.5], equal_nan=True)

    def test_modified_prediction_and_recorded_mean_fail(self):
        a = self.cell()
        a["arms"]["fixed_share"]["predictions_kwh"][0][0] = 9
        with self.assertRaises(AssertionError):
            read_errors(a, start="2026-01-01", days=3)
        a = self.cell()
        a["arms"]["old_fixed"]["mae"] = 99
        with self.assertRaisesRegex(ValueError, "recorded mean"):
            read_errors(a, start="2026-01-01", days=3)

    def test_outside_calendar_and_duplicate_origins_fail(self):
        for dates in (["2026-01-01", "2026-01-04"], ["2026-01-01", "2026-01-01"]):
            a = copy.deepcopy(self.cell())
            a["cell"]["origins"] = dates
            with self.assertRaises(ValueError):
                read_errors(a, start="2026-01-01", days=3)


if __name__ == "__main__":
    unittest.main()
