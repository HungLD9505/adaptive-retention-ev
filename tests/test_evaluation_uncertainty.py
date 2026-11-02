"""Independent pairing, missing-calendar and equal-station interval checks."""

import unittest
from datetime import datetime, timedelta, timezone

from ev_evaluation.uncertainty import paired_station_time_interval


class IntervalTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2022, 12, 1, tzinfo=timezone.utc)
        self.options = dict(
            seeds=(1, 2, 3),
            start=self.start,
            days=14,
            segment_days=7,
            resamples=100,
            alpha=0.05,
            seed=50,
        )

    def rows(self, value, count=14):
        return {s: {self.start + timedelta(days=d): value for d in range(count)} for s in (1, 2, 3)}

    def test_constant_paired_gap_is_exact_and_deterministic(self):
        data = {"a": self.rows(-2), "b": self.rows(-2)}
        result = paired_station_time_interval(data, **self.options)
        self.assertEqual(result["gap_kwh"], -2)
        self.assertEqual(result["interval"], [-2, -2])
        self.assertEqual(result, paired_station_time_interval(data, **self.options))

    def test_station_weight_is_not_day_count_or_seed_count(self):
        data = {"a": self.rows(0, 7), "b": self.rows(10)}
        result = paired_station_time_interval(data, **self.options)
        self.assertEqual(result["gap_kwh"], 5)
        self.assertEqual(result["station_count"], 2)

    def test_calendar_gaps_can_make_interval_undefined_without_zero_fill(self):
        data = {"a": self.rows(4, 1)}
        result = paired_station_time_interval(data, **self.options)
        self.assertEqual(result["gap_kwh"], 4)
        self.assertGreater(result["undefined_replicates"], 0)
        self.assertIsNone(result["interval"])

    def test_missing_seed_or_shifted_scored_origin_rejected(self):
        for rows in ({1: self.rows(1)[1]}, self.rows(1)):
            if len(rows) == 3:
                rows[2].pop(self.start)
            with self.assertRaises(ValueError):
                paired_station_time_interval({"a": rows}, **self.options)

    def test_out_of_calendar_and_nonfinite_values_rejected(self):
        for origin, value in ((self.start - timedelta(days=1), 1), (self.start, float("nan"))):
            rows = {s: {origin: value} for s in (1, 2, 3)}
            with self.assertRaises(ValueError):
                paired_station_time_interval({"a": rows}, **self.options)


if __name__ == "__main__":
    unittest.main()
