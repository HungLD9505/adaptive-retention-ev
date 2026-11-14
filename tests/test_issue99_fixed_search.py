"""Bounded BO/EI and score-independent sensitivity fixtures."""

import math
import unittest

import torch

from ev_search.fixed import (
    FixedSearchConfig,
    expanded_upper,
    expected_improvement,
    propose_lambda,
    sensitivity_design,
)


def config():
    return FixedSearchConfig(
        positive_lower=0.001,
        positive_upper=1.0,
        maximum_upper=8.0,
        expansion_factor=2.0,
        boundary_fraction=0.1,
        maximum_expansions=2,
        bo_trials=6,
        initial_lambdas=(0.001, 0.1, 1.0),
        sensitivity_points=5,
        acquisition_grid_points=64,
        kernel_length=1.0,
        signal_std=0.2,
        noise_std=0.01,
        expected_improvement_jitter=0.001,
    )


class FixedSearchTests(unittest.TestCase):
    def test_initial_then_ei_in_bounds_without_duplicate(self):
        settings = config()
        observations = []
        for expected in settings.initial_lambdas:
            actual, role = propose_lambda(settings, 1.0, observations)
            self.assertEqual((actual, role), (expected, "initial"))
            observations.append((actual, (math.log(actual) + 1.0) ** 2))
        proposed, role = propose_lambda(settings, 1.0, observations)
        self.assertEqual(role, "bo_ei")
        self.assertTrue(settings.positive_lower <= proposed <= 1.0)
        self.assertNotIn(proposed, settings.initial_lambdas)
        scores = expected_improvement(
            torch.linspace(math.log(0.001), 0, 10, dtype=torch.float64), observations, settings
        )
        self.assertTrue(torch.isfinite(scores).all())
        self.assertTrue((scores >= 0).all())

    def test_expansion_and_sensitivity_are_bounded(self):
        settings = config()
        self.assertEqual(expanded_upper(settings, 1.0, 0, [(1.0, 0.1), (0.1, 0.2)]), 2.0)
        self.assertEqual(expanded_upper(settings, 1.0, 2, [(1.0, 0.1)]), 1.0)
        self.assertEqual(expanded_upper(settings, 1.0, 0, [(0.1, 0.1), (1.0, 0.2)]), 1.0)
        design = sensitivity_design(settings, 2.0)
        self.assertEqual(len(design), 5)
        self.assertAlmostEqual(design[0], 0.001)
        self.assertAlmostEqual(design[-1], 2.0)

    def test_zero_and_null_do_not_enter_positive_gp(self):
        with self.assertRaises(ValueError):
            expected_improvement(torch.tensor([0.0], dtype=torch.float64), [(0.0, 0.1)], config())
        with self.assertRaises(ValueError):
            expected_improvement(
                torch.tensor([0.0], dtype=torch.float64), [(0.1, float("nan"))], config()
            )
        settings = config()
        proposed, role = propose_lambda(settings, 1.0, [(settings.initial_lambdas[0], None)])
        self.assertEqual((proposed, role), (settings.initial_lambdas[1], "initial"))


if __name__ == "__main__":
    unittest.main()
