"""24-to-24 fixtures with independent literal shapes, timing and energy expectations."""

import unittest
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone

from ev_inputs.windows import (
    HourlyValue,
    build_forecast_input,
    build_initial_training_example,
    build_label_record,
    initial_training_origins,
    ready_labels,
    scheduled_origins,
)

HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


class WindowTests(unittest.TestCase):
    identity = ("charged", "AMS", "001")
    origin = datetime(2023, 7, 1)
    mode = "publisher-local-naive"

    def rows(self, start, *, energy=10):
        return [
            HourlyValue(self.identity, start + i * HOUR, energy, True, start + (i + 1) * HOUR)
            for i in range(24)
        ]

    def forecast(self, history=None, *, origin=None, mode=None, scale=20):
        origin = origin or self.origin
        return build_forecast_input(
            self.rows(origin - DAY) if history is None else history,
            identity=self.identity,
            origin=origin,
            clock_mode=mode or self.mode,
            energy_scale=scale,
            scale_id="fixture-scale-v1",
            input_run_id="fixture-hourly-v1",
        )

    def labels(self, future=None):
        return build_label_record(
            self.rows(self.origin) if future is None else future,
            identity=self.identity,
            origin=self.origin,
            clock_mode=self.mode,
        )

    def train(self, forecast, labels, *, start=None, cutoff=None):
        return build_initial_training_example(
            forecast,
            labels,
            prefix_start=start or self.origin - DAY,
            cutoff=cutoff or self.origin + DAY,
        )

    def test_shapes_order_and_literal_rows(self):
        forecast = self.forecast()
        self.assertEqual((len(forecast.x_hist), len(forecast.x_hist[0])), (24, 7))
        self.assertEqual((len(forecast.c_future), len(forecast.c_future[0])), (24, 5))
        self.assertEqual(forecast.history_labels[0], datetime(2023, 6, 30))
        self.assertEqual(forecast.history_labels[-1], datetime(2023, 6, 30, 23))
        self.assertEqual(forecast.future_labels[-1], datetime(2023, 7, 1, 23))
        self.assertEqual(forecast.x_hist[0][0], 0.5)
        self.assertEqual(forecast.x_hist[0][-1], 1)
        # Friday history; Saturday forecast: distinct weekdays and weekend flag.
        self.assertEqual(forecast.x_hist[0][5], 0)
        self.assertEqual(forecast.c_future[0][-1], 1)
        self.assertEqual(forecast.c_future[0][:2], (0, 1))

    def test_true_zero_missing_delayed_unknown_history(self):
        history = self.rows(self.origin - DAY)
        history[0] = replace(history[0], energy_kwh=0)
        history[1] = replace(history[1], file_valid=False, energy_kwh=None)
        history[2] = replace(history[2], available_at=self.origin + HOUR, energy_kwh=999)
        history[3] = replace(history[3], available_at=None)
        forecast = self.forecast(history)
        self.assertEqual((forecast.x_hist[0][0], forecast.x_hist[0][-1]), (0, 1))
        for index in (1, 2, 3):
            self.assertEqual((forecast.x_hist[index][0], forecast.x_hist[index][-1]), (0, 0))

    def test_all_missing_history_preserved_without_future_filter(self):
        history = [
            replace(row, energy_kwh=None, file_valid=False) for row in self.rows(self.origin - DAY)
        ]
        forecast = self.forecast(history)
        self.assertTrue(all(row[0] == row[-1] == 0 for row in forecast.x_hist))

    def test_prediction_has_no_future_label_fields_or_dependency(self):
        forecast = self.forecast()
        bad_future = [
            replace(row, file_valid=False, energy_kwh=None) for row in self.rows(self.origin)
        ]
        self.assertIsNone(ready_labels(self.labels(bad_future), as_of=self.origin + DAY))
        self.assertEqual(forecast, self.forecast())
        fields = asdict(forecast)
        self.assertFalse(
            {"y_kwh", "y_scaled", "energy_kwh", "file_valid", "available_at"} & fields.keys()
        )
        with self.assertRaises(TypeError):
            build_forecast_input([], future=bad_future)

    def test_schedule_never_reads_future_completeness(self):
        expected = (self.origin, self.origin + DAY, self.origin + 2 * DAY)
        self.assertEqual(
            scheduled_origins(self.origin, self.origin + 3 * DAY, clock_mode=self.mode), expected
        )
        self.labels(
            [replace(row, file_valid=False, energy_kwh=None) for row in self.rows(self.origin)]
        )
        self.assertEqual(
            scheduled_origins(self.origin, self.origin + 3 * DAY, clock_mode=self.mode), expected
        )

    def test_complete_labels_only_at_horizon_end(self):
        labels = self.labels()
        self.assertIsNone(ready_labels(labels, as_of=self.origin + DAY - timedelta(microseconds=1)))
        self.assertEqual(ready_labels(labels, as_of=self.origin + DAY), (10.0,) * 24)

    def test_delayed_or_unknown_label_blocks_entire_day(self):
        for arrival in (None, self.origin + 2 * DAY):
            future = self.rows(self.origin)
            future[0] = replace(future[0], available_at=arrival)
            labels = self.labels(future)
            self.assertIsNone(ready_labels(labels, as_of=self.origin + DAY))
            if arrival:
                self.assertEqual(ready_labels(labels, as_of=arrival), (10.0,) * 24)

    def test_missing_y_is_none_and_never_partial_training(self):
        future = self.rows(self.origin)
        future[5] = replace(future[5], energy_kwh=999, file_valid=False)
        labels = self.labels(future)
        self.assertIsNone(labels.energy_kwh[5])
        self.assertIsNone(self.train(self.forecast(), labels))

    def test_malformed_label_records_cannot_bypass_gate(self):
        labels = self.labels()
        for malformed in (
            replace(labels, energy_kwh=labels.energy_kwh[:-1]),
            replace(labels, file_valid=labels.file_valid[:-1]),
            replace(labels, timestamps=tuple(reversed(labels.timestamps))),
            replace(labels, energy_kwh=(float("nan"),) + labels.energy_kwh[1:]),
        ):
            with self.subTest(record=malformed), self.assertRaises(ValueError):
                ready_labels(malformed, as_of=self.origin + DAY)

    def test_zero_labels_are_complete_and_trainable(self):
        labels = self.labels(self.rows(self.origin, energy=0))
        example = self.train(self.forecast(), labels)
        self.assertEqual(example.y_kwh, (0.0,) * 24)
        self.assertEqual(example.y_scaled, (0.0,) * 24)

    def test_training_units_and_prefix_boundaries(self):
        example = self.train(self.forecast(), self.labels())
        self.assertEqual(example.y_scaled, (0.5,) * 24)
        self.assertEqual(tuple(value * 20 for value in example.y_scaled), example.y_kwh)
        for start, cutoff in (
            (self.origin - DAY + HOUR, self.origin + DAY),
            (self.origin - DAY, self.origin + DAY - HOUR),
        ):
            with self.assertRaisesRegex(ValueError, "Entire history"):
                self.train(self.forecast(), self.labels(), start=start, cutoff=cutoff)

    def test_budget_candidate_counts_are_contained(self):
        for days, count in ((7, 6), (14, 13), (28, 27)):
            start = self.origin - days * DAY
            origins = initial_training_origins(start, self.origin, clock_mode=self.mode)
            self.assertEqual(len(origins), count)
            self.assertEqual(origins[0] - DAY, start)
            self.assertEqual(origins[-1] + DAY, self.origin)
        self.assertEqual(
            initial_training_origins(self.origin - DAY, self.origin, clock_mode=self.mode), ()
        )

    def test_wrong_entity_or_origin_labels_rejected(self):
        labels = self.labels()
        for record in (
            replace(labels, identity=("charged", "JHB", "001")),
            replace(labels, origin=self.origin + DAY),
        ):
            with self.assertRaisesRegex(ValueError, "do not match"):
                self.train(self.forecast(), record)

    def test_bad_bin_count_order_gap_duplicate_entity(self):
        history = self.rows(self.origin - DAY)
        cases = [
            history[:-1],
            history + history[:1],
            list(reversed(history)),
            [history[0]] + history[:-1],
            [replace(history[0], identity=("charged", "AMS", "1"))] + history[1:],
        ]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.forecast(rows)

    def test_profile_origin_and_availability_failures(self):
        with self.assertRaises(ValueError):
            self.forecast(origin=self.origin + HOUR)
        with self.assertRaises(ValueError):
            self.forecast(mode="offset-aware-local")
        history = self.rows(self.origin - DAY)
        for arrival in (history[0].timestamp, self.origin.replace(tzinfo=timezone.utc)):
            with self.assertRaises(ValueError):
                self.forecast([replace(history[0], available_at=arrival)] + history[1:])
        with self.assertRaises(ValueError):
            ready_labels(self.labels(), as_of=self.origin.replace(tzinfo=timezone.utc))

    def test_aware_local_calendar_is_not_converted_to_utc(self):
        local = datetime(2022, 12, 1, tzinfo=timezone(timedelta(hours=8)))
        forecast = self.forecast(origin=local, mode="offset-aware-local")
        self.assertEqual(forecast.c_future[0][:2], (0, 1))
        self.assertEqual(forecast.future_labels[0].utcoffset(), timedelta(hours=8))

    def test_invalid_valid_energy_and_nonfinite_scaled_y_fail(self):
        for value in (None, -1, float("nan"), float("inf"), True):
            future = self.rows(self.origin)
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                self.labels([replace(future[0], energy_kwh=value)] + future[1:])
        history = self.rows(self.origin - DAY, energy=0)
        with self.assertRaises(ValueError):
            self.train(self.forecast(history, scale=1e-300), self.labels())
        with self.assertRaises(ValueError):
            self.forecast(scale=0)


if __name__ == "__main__":
    unittest.main()
