"""Scientific selection rules must keep adverse and null outcomes honest."""

import unittest

from tools.issue99_study import select_fixed


def trial(index, weight, score, status="complete"):
    return {
        "trial": index,
        "lambda": weight,
        "status": status,
        "outcome": {"objective_mae_kwh": score},
    }


class SelectionTests(unittest.TestCase):
    def test_selects_best_and_first_measured_harm_above_it(self):
        events = [
            trial(0, 0.0, 5.0),
            trial(1, 0.5, 4.0),
            trial(2, 1.0, 6.0),
            trial(3, 100.0, 7.0),
            trial(4, 10.0, None, "failed"),
        ]
        result = select_fixed(events, 0.001)
        self.assertEqual(result["selected_lambda"], 0.5)
        self.assertEqual(result["controller_upper_bound"], 1.0)
        self.assertFalse(result["upper_boundary_unresolved"])
        self.assertEqual(result["all_trials"], 5)
        self.assertEqual(result["finite_trials"], 4)

    def test_ties_prefer_zero_and_boundary_winner_is_unresolved(self):
        result = select_fixed([trial(0, 0.0, 5.0), trial(1, 1.0, 5.0)], 0.001)
        self.assertEqual(result["selected_lambda"], 0.0)
        result = select_fixed([trial(0, 0.0, 5.0), trial(1, 1.0, 4.0)], 0.001)
        self.assertTrue(result["upper_boundary_unresolved"])
        self.assertEqual(result["controller_upper_bound"], 1.0)

    def test_failed_baseline_cannot_produce_a_comparison(self):
        with self.assertRaises((ValueError, StopIteration)):
            select_fixed([trial(0, 0.0, None, "failed")], 0.001)
