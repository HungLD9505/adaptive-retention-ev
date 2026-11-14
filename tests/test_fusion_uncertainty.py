"""Independent estimands and failure cases for recorded-fusion uncertainty."""

import unittest

import numpy as np

from ev_evaluation.fusion_uncertainty import paired_mean_interval


class FusionUncertaintyTests(unittest.TestCase):
    def options(self, **updates):
        return {"resamples": 200, "seed": 117, **updates}

    def test_identical_arms_have_exact_zero_gaps_with_shared_calendar(self):
        data = np.array([[1, 9, 3, 5], [20, 2, 10, 7]])
        for segment in (None, 1, 2, 4):
            r = paired_mean_interval(data, data, **self.options(segment_days=segment))
            self.assertEqual(r["gap_kwh"], 0)
            self.assertEqual(r["gap_interval_kwh"], [0, 0])
            self.assertEqual(r["reduction_interval_percent"], [0, 0])

    def test_equal_entity_weight_does_not_become_pooled_day_weight(self):
        a = np.array([[1, np.nan, np.nan], [10, 10, 10]])
        b = np.array([[0, np.nan, np.nan], [12, 12, 12]])
        r = paired_mean_interval(a, b, **self.options())
        self.assertEqual(r["reference_mae_kwh"], 5.5)
        self.assertEqual(r["candidate_mae_kwh"], 6)
        self.assertEqual(r["gap_kwh"], 0.5)
        self.assertEqual(r["gap_interval_kwh"], [-1, 2])
        self.assertEqual(r["reduction_interval_percent"], [-20, 100])
        self.assertAlmostEqual(r["reduction_percent"], -100 / 11)
        self.assertEqual((r["entity_lower"], r["entity_higher"]), (1, 1))

    def test_missing_calendar_days_can_invalidate_all_interval_reporting(self):
        a = np.array([[1, *([np.nan] * 13)]])
        b = np.array([[2, *([np.nan] * 13)]])
        r = paired_mean_interval(a, b, **self.options(segment_days=1))
        self.assertGreater(r["undefined_replicates"], 0)
        self.assertIsNone(r["gap_interval_kwh"])
        self.assertEqual(r["gap_kwh"], 1)

    def test_seed_and_input_arrays_are_reproducible_and_not_mutated(self):
        a = np.arange(1, 19, dtype=float).reshape(3, 6)
        b = a * np.array([[0.5], [1], [2]])
        copy = a.copy()
        first = paired_mean_interval(a, b, **self.options(segment_days=2))
        self.assertEqual(first, paired_mean_interval(a, b, **self.options(segment_days=2)))
        np.testing.assert_array_equal(a, copy)

    def test_constant_relative_gain_is_not_mean_of_entity_percentages(self):
        a = np.array([[1, 1], [100, 100]], dtype=float)
        b = np.array([[0, 0], [100, 100]], dtype=float)
        r = paired_mean_interval(a, b, **self.options())
        self.assertAlmostEqual(r["reduction_percent"], 100 / 101)
        self.assertNotEqual(r["reduction_percent"], 50)

    def test_zero_reference_keeps_absolute_gap_but_no_percentage(self):
        r = paired_mean_interval(np.zeros((2, 4)), np.ones((2, 4)), **self.options())
        self.assertEqual(r["gap_interval_kwh"], [1, 1])
        self.assertIsNone(r["reduction_percent"])
        self.assertIsNone(r["reduction_interval_percent"])

    def test_invalid_pairing_nonfinite_negative_and_empty_entity_rejected(self):
        cases = [
            ([[1, np.nan]], [[1, 2]]),
            ([[np.inf]], [[2]]),
            ([[1]], [[-1]]),
            ([[np.nan]], [[np.nan]]),
            ([], []),
        ]
        for a, b in cases:
            with self.subTest(a=a), self.assertRaises(ValueError):
                paired_mean_interval(np.asarray(a), np.asarray(b), **self.options())
        for bad in ({"segment_days": 3}, {"resamples": 1}, {"seed": -1}, {"alpha": 1}):
            with self.assertRaises(ValueError):
                paired_mean_interval(np.ones((1, 2)), np.ones((1, 2)), **self.options(**bad))


if __name__ == "__main__":
    unittest.main()
