"""Prespecified macro weights and calendar pairing, independent of EV results."""

import unittest

import numpy as np

from tools.confirmation_summary import stratified_contrasts


class ConfirmationSummaryTests(unittest.TestCase):
    def options(self):
        return {"resamples": 200, "seed": 119, "segment_days": 3, "alpha": 0.025}

    def test_equal_namespace_gain_is_not_pooled_kwh_or_entity_percentage(self):
        data = {
            "small": {"fixed": [[1] * 14], "static": [[0.9] * 14], "adaptive": [[0.9] * 14]},
            "large": {
                "fixed": [[100] * 14] * 3,
                "static": [[200] * 14] * 3,
                "adaptive": [[100] * 14] * 3,
            },
        }
        r = stratified_contrasts(data, **self.options())["comparisons"]
        self.assertAlmostEqual(r["fixed"]["equal_namespace_reduction_percent"], 5)
        self.assertAlmostEqual(r["static"]["equal_namespace_reduction_percent"], 25)
        np.testing.assert_allclose(r["fixed"]["interval_percent"], [5, 5], atol=1e-12)

    def test_identical_arms_share_draws_and_have_exact_zero_gain(self):
        a = np.arange(1, 29, dtype=float).reshape(2, 14)
        result = stratified_contrasts(
            {"x": {"fixed": a, "static": a, "adaptive": a}}, **self.options()
        )
        for r in result["comparisons"].values():
            self.assertEqual(r["interval_percent"], [0, 0])

    def test_zero_reference_and_missing_calendar_invalidate_instead_of_impute(self):
        data = {
            "x": {
                "fixed": np.zeros((1, 14)),
                "static": np.ones((1, 14)),
                "adaptive": np.ones((1, 14)),
            }
        }
        r = stratified_contrasts(data, **self.options())["comparisons"]["fixed"]
        self.assertIsNone(r["equal_namespace_reduction_percent"])
        self.assertIsNone(r["interval_percent"])
        a = np.array([[1, *([np.nan] * 13)]])
        r = stratified_contrasts({"x": {"fixed": a, "static": a, "adaptive": a}}, **self.options())
        self.assertGreater(r["comparisons"]["fixed"]["invalid_replicates"], 0)
        self.assertIsNone(r["comparisons"]["fixed"]["interval_percent"])

    def test_unmatched_method_mask_is_rejected(self):
        data = {"x": {"fixed": [[1, np.nan]], "static": [[1, 1]], "adaptive": [[1, 1]]}}
        with self.assertRaises(ValueError):
            stratified_contrasts(data, **self.options())


if __name__ == "__main__":
    unittest.main()
