"""Independent verification arithmetic and delayed-feedback regression checks."""

import unittest

import numpy as np

from tools.confirmation_verify import equal, independent_arms, independent_intervals


class ConfirmationVerificationTests(unittest.TestCase):
    def test_only_arrived_past_labels_affect_next_forecast(self):
        cell = {
            "origins": ["2026-01-01T00:00:00", "2026-01-02T00:00:00", "2026-01-03T00:00:00"],
            "available_at": ["2026-01-03T00:00:00", "2026-01-03T00:00:00", "2026-01-04T00:00:00"],
            "stable": [[0.0] * 24] * 3,
            "fast": [[2.0] * 24] * 3,
            "labels": [[0.0] * 24] * 3,
            "scale": 1.0,
        }
        arms = independent_arms(cell, {"initial_weight": 0.5, "eta": 1.0, "share": 0.1})
        equal(arms["adaptive"]["weights"][:2], [0.5, 0.5])
        first = 0.1 + 0.8 / (1 + np.exp(-2))
        second = 0.1 + 0.8 * first / (first + (1 - first) * np.exp(-2))
        equal(arms["adaptive"]["weights"][2], second)
        equal(arms["static"]["mae"], 1.0)

    def test_constant_errors_have_exact_intervals(self):
        data = {
            "a": {
                "adaptive": np.ones((2, 90)),
                "fixed": np.full((2, 90), 2.0),
                "static": np.full((2, 90), 4.0),
            }
        }
        profile = {"seed": 9, "resamples": 151, "segment_days": 7, "alpha_per_comparison": 0.025}
        result = independent_intervals(data, profile)
        equal(result["fixed"]["interval_percent"], [50, 50])
        equal(result["static"]["interval_percent"], [75, 75])
        self.assertEqual(result["fixed"]["invalid_replicates"], 0)

    def test_zero_reference_invalidates_interval(self):
        data = {"a": {name: np.zeros((1, 90)) for name in ("fixed", "static", "adaptive")}}
        profile = {"seed": 9, "resamples": 129, "segment_days": 14, "alpha_per_comparison": 0.025}
        result = independent_intervals(data, profile)
        self.assertIsNone(result["fixed"]["interval_percent"])
        self.assertEqual(result["fixed"]["invalid_replicates"], 129)
