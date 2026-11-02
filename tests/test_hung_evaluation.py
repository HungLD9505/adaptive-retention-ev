"""Known expected values for original-unit scoring and schedule coverage."""

from __future__ import annotations

import unittest

import torch

from experiments.hung_sprint2.evaluation import (
    ErrorTotals,
    aggregate_errors,
    complete_day_error_totals,
    coverage_from_replay,
    evaluate_replay,
)
from experiments.hung_sprint2.replay_inputs import ReplaySummary
from tests.test_hung_runner import complete, origin, runner


class EvaluationTests(unittest.TestCase):
    def test_original_unit_mae_rmse_use_all_hours(self) -> None:
        first = complete_day_error_totals(
            torch.tensor([0.4, 0.6] + [0.2] * 22),
            torch.tensor([0.2] * 24),
            torch.ones(24, dtype=torch.bool),
            energy_scale=5.0,
        )
        second = complete_day_error_totals(
            torch.tensor([1.0] * 24),
            torch.tensor([0.0] * 24),
            torch.ones(24, dtype=torch.bool),
            energy_scale=2.0,
        )
        self.assertEqual(first.hours, 24)
        self.assertAlmostEqual(first.absolute_kwh, 3.0, places=5)
        self.assertAlmostEqual(first.squared_kwh2, 5.0, places=5)
        result = aggregate_errors([first, second])
        self.assertEqual(result.hours, 48)
        self.assertAlmostEqual(result.mae_kwh, 51.0 / 48, places=5)
        self.assertAlmostEqual(result.rmse_kwh, (101.0 / 48) ** 0.5, places=5)

    def test_incomplete_or_invalid_horizon_is_rejected(self) -> None:
        forecast = torch.ones(24)
        labels = torch.zeros(24)
        valid = torch.ones(24, dtype=torch.bool)
        valid[-1] = False
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            complete_day_error_totals(forecast, labels, valid, energy_scale=2.0)
        valid[-1] = True
        with self.assertRaisesRegex(ValueError, "finite and positive"):
            complete_day_error_totals(forecast, labels, valid, energy_scale=float("nan"))
        labels[0] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite nonnegative"):
            complete_day_error_totals(forecast, labels, valid, energy_scale=2.0)
        with self.assertRaisesRegex(ValueError, "At least one"):
            aggregate_errors([])
        with self.assertRaisesRegex(ValueError, "Invalid"):
            aggregate_errors([ErrorTotals(23, 0.0, 0.0)])

    def test_coverage_balances_requested_created_and_scored(self) -> None:
        result = coverage_from_replay(ReplaySummary(6, 4, 1, 1, 2, 2))
        self.assertEqual(result.unscored_created, 2)
        self.assertAlmostEqual(result.issued_fraction, 4 / 6)
        self.assertAlmostEqual(result.scored_fraction, 2 / 6)
        with self.assertRaisesRegex(ValueError, "schedule"):
            coverage_from_replay(ReplaySummary(6, 3, 1, 1, 2, 1))
        with self.assertRaisesRegex(ValueError, "forecast"):
            coverage_from_replay(ReplaySummary(6, 4, 1, 1, 2, 1))

    def test_runner_evaluation_uses_issued_forecasts_and_arrived_labels(self) -> None:
        replay = runner()
        replay.forecast(origin(0))
        replay.arrive(complete(0))
        summary = ReplaySummary(1, 1, 0, 0, 1, 0)
        result = evaluate_replay(replay, summary)
        self.assertEqual(result.coverage.scored, 1)
        self.assertEqual(result.live.hours, 24)
        self.assertAlmostEqual(result.live.mae_kwh, replay.issued[0]["mae_kwh"][0], places=5)
        self.assertGreaterEqual(result.live.rmse_kwh, result.live.mae_kwh)
        self.assertEqual(result.audit_scored_days, 0)
        self.assertIsNone(result.audit)
        with self.assertRaisesRegex(ValueError, "count differs"):
            evaluate_replay(replay, ReplaySummary(2, 2, 0, 0, 1, 1))


if __name__ == "__main__":
    unittest.main()
