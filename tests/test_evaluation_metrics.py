"""Hand-calculated evaluation cases, independent of training implementation."""

import json
import math
import unittest
from datetime import datetime, timedelta

from ev_evaluation.metrics import DailyError, original_errors, paired_metrics, station_first

DAY = datetime(2023, 7, 1)
SEEDS = (42, 43, 44)


def errors(maes: list[float], *, start: datetime = DAY) -> list[DailyError]:
    return [DailyError(start + timedelta(days=i), v, v * v) for i, v in enumerate(maes)]


class MetricsTests(unittest.TestCase):
    def test_original_unit_conversion(self):
        score = original_errors(DAY, [0.5] * 24, [8.0] * 24, 10.0)
        self.assertEqual((score.mae, score.mse), (3.0, 9.0))

    def test_requires_full_labels_and_finite_scale(self):
        for labels, scale in (([0.0] * 23, 1), ([0.0] * 24, 0), ([0.0] * 24, math.inf)):
            with self.assertRaises(ValueError):
                original_errors(DAY, [0.0] * 24, labels, scale)
        with self.assertRaises(ValueError):
            original_errors(DAY, [math.nan] * 24, [0.0] * 24, 1)

    def test_rmse_pools_squared_errors_before_root(self):
        result = paired_metrics(errors([0, 4]), errors([2, 2]))
        self.assertEqual(result["method_mae_kwh"], 2)
        self.assertAlmostEqual(result["method_rmse_kwh"], math.sqrt(8))
        self.assertEqual(result["gain"], 0)

    def test_negative_gain_and_absolute_gap(self):
        result = paired_metrics(errors([3]), errors([2]))
        self.assertEqual(result["gain"], -0.5)
        self.assertEqual(result["absolute_gap_kwh"], 1)
        self.assertTrue(result["negative_transfer"])

    def test_zero_denominator_is_not_epsilon_substituted(self):
        result = paired_metrics(errors([0.01]), errors([0]))
        self.assertIsNone(result["gain"])
        self.assertIsNone(result["negative_transfer"])
        self.assertEqual(result["absolute_gap_kwh"], 0.01)

    def test_identical_scored_population_required(self):
        with self.assertRaises(ValueError):
            paired_metrics(errors([1]), errors([1, 2]))
        with self.assertRaises(ValueError):
            paired_metrics(errors([1]), errors([1], start=DAY + timedelta(days=1)))
        with self.assertRaises(ValueError):
            paired_metrics(errors([1]) * 2, errors([1]) * 2)

    def test_station_equal_weight_despite_unequal_days(self):
        rows = {
            "short": {s: paired_metrics(errors([4]), errors([2])) for s in SEEDS},
            "long": {s: paired_metrics(errors([0] * 10), errors([2] * 10)) for s in SEEDS},
        }
        result = station_first(rows, seeds=SEEDS)
        self.assertEqual(result["macro_mae_kwh"], 2)
        self.assertEqual(result["ntr"], 0.5)
        self.assertEqual(result["ntr_denominator"], 2)
        self.assertIsNone(result["population_interval"])

    def test_seed_first_then_station_gain(self):
        row = {s: paired_metrics(errors([i]), errors([2])) for s, i in zip(SEEDS, (1, 2, 6))}
        result = station_first({"a": row}, seeds=SEEDS)
        self.assertEqual(result["stations"]["a"]["gain"], -0.5)

    def test_zero_baseline_station_count_separate(self):
        row = {s: paired_metrics(errors([1]), errors([0])) for s in SEEDS}
        row = {s: json.loads(json.dumps(value)) for s, value in row.items()}
        result = station_first({"zero": row}, seeds=SEEDS)
        self.assertIsNone(result["ntr"])
        self.assertEqual(result["zero_baseline_station_count"], 1)
        self.assertEqual(result["ntr_denominator"], 0)

    def test_missing_seed_and_mismatched_dates_fail(self):
        row = {s: paired_metrics(errors([1]), errors([2])) for s in SEEDS}
        with self.assertRaises(ValueError):
            station_first({"a": {42: row[42]}}, seeds=SEEDS)
        row[44] = paired_metrics(
            errors([1], start=DAY + timedelta(days=1)), errors([2], start=DAY + timedelta(days=1))
        )
        with self.assertRaises(ValueError):
            station_first({"a": row}, seeds=SEEDS)

    def test_invalid_daily_error_rejected(self):
        for mae, mse in ((math.nan, 1), (2, 1), (-1, 2)):
            with self.assertRaises(ValueError):
                DailyError(DAY, mae, mse)


if __name__ == "__main__":
    unittest.main()
