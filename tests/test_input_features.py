"""Independent calendar/numeric fixtures; no producer data, loader or fitted scaler."""

import math
import unittest
from datetime import datetime, timedelta, timezone

from ev_inputs.features import (
    CALENDAR_FEATURE_NAMES,
    CONTRACT_COMMIT,
    CONTRACT_SHA256,
    HISTORICAL_FEATURE_NAMES,
    SCHEMA_ID,
    calendar_features,
    historical_features,
)

NAIVE = "publisher-local-naive"
AWARE = "offset-aware-local"


class CalendarFeatureTests(unittest.TestCase):
    def assert_vector(self, actual: tuple, expected: tuple) -> None:
        self.assertEqual(len(actual), len(expected))
        for a, e in zip(actual, expected):
            self.assertAlmostEqual(a, e, delta=1e-6)

    def test_contract_and_order_are_explicit(self) -> None:
        self.assertEqual(SCHEMA_ID, "ev-input-v1")
        self.assertEqual(CONTRACT_COMMIT, "c406ae07606ca48859cf93f8b24dfffab79c7803")
        self.assertEqual(
            CONTRACT_SHA256, "b10178d106713670e7ba7f884dd640559ce1788b3c792447843300457df63adf"
        )
        self.assertEqual(
            CALENDAR_FEATURE_NAMES,
            ("hour_sin", "hour_cos", "weekday_sin", "weekday_cos", "is_weekend"),
        )
        self.assertEqual(
            HISTORICAL_FEATURE_NAMES,
            (
                "energy_scaled",
                "hour_sin",
                "hour_cos",
                "weekday_sin",
                "weekday_cos",
                "is_weekend",
                "energy_present_mask",
            ),
        )

    def test_monday_midnight_and_sunday_23(self) -> None:
        self.assert_vector(
            calendar_features(datetime(2023, 1, 2), clock_mode=NAIVE), (0, 1, 0, 1, 0)
        )
        self.assert_vector(
            calendar_features(datetime(2023, 1, 1, 23), clock_mode=NAIVE),
            (-0.2588190451, 0.9659258263, -0.7818314825, 0.6234898019, 1),
        )

    def test_tuesday_six_matches_documented_example(self) -> None:
        stamp = datetime.fromisoformat("2022-11-29T06:00:00+08:00")
        self.assert_vector(
            calendar_features(stamp, clock_mode=AWARE), (1, 0, 0.7818314825, 0.6234898019, 0)
        )

    def test_midnight_week_and_year_wrap(self) -> None:
        sunday = calendar_features(datetime(2023, 1, 1, 23), clock_mode=NAIVE)
        monday = calendar_features(datetime(2023, 1, 2), clock_mode=NAIVE)
        tuesday = calendar_features(datetime(2023, 1, 3), clock_mode=NAIVE)
        hour_one = calendar_features(datetime(2023, 1, 2, 1), clock_mode=NAIVE)
        self.assertAlmostEqual(
            math.dist(sunday[:2], monday[:2]), math.dist(monday[:2], hour_one[:2]), delta=1e-6
        )
        self.assertAlmostEqual(
            math.dist(sunday[2:4], monday[2:4]), math.dist(monday[2:4], tuesday[2:4]), delta=1e-6
        )
        before = calendar_features(datetime(2022, 12, 31, 23), clock_mode=NAIVE)
        after = calendar_features(datetime(2023, 1, 1), clock_mode=NAIVE)
        self.assertEqual((before[4], after[4]), (1, 1))
        self.assert_vector(after, (0, 1, -0.7818314825, 0.6234898019, 1))

    def test_local_clock_is_not_converted_to_utc(self) -> None:
        stamp = datetime(2023, 1, 2, tzinfo=timezone(timedelta(hours=8)))
        self.assert_vector(calendar_features(stamp, clock_mode=AWARE), (0, 1, 0, 1, 0))
        self.assert_vector(
            calendar_features(stamp.replace(tzinfo=None), clock_mode=NAIVE), (0, 1, 0, 1, 0)
        )
        self.assertNotEqual(
            calendar_features(stamp.astimezone(timezone.utc), clock_mode=AWARE),
            calendar_features(stamp, clock_mode=AWARE),
        )

    def test_reject_wrong_clock_unknown_mode_and_non_hour(self) -> None:
        cases = [
            (datetime(2023, 1, 2), AWARE),
            (datetime(2023, 1, 2, tzinfo=timezone.utc), NAIVE),
            (datetime(2023, 1, 2), "UTC"),
            (datetime(2023, 1, 2, minute=1), NAIVE),
            (datetime(2023, 1, 2, microsecond=1), NAIVE),
        ]
        for stamp, mode in cases:
            with self.subTest(stamp=stamp, mode=mode), self.assertRaises(ValueError):
                calendar_features(stamp, clock_mode=mode)
        with self.assertRaises(TypeError):
            calendar_features("2023-01-02", clock_mode=NAIVE)


class HistoricalFeatureTests(unittest.TestCase):
    def row(self, energy: object, **changes: object) -> tuple:
        args = dict(
            energy_kwh=energy,
            file_valid=True,
            energy_available=True,
            energy_scale=20,
            clock_mode=NAIVE,
        )
        args.update(changes)
        return historical_features(datetime(2022, 11, 29, 6), **args)

    def test_complete_historical_example_and_no_clipping(self) -> None:
        row = self.row(10)
        self.assertEqual(len(row), 7)
        self.assertEqual((row[0], row[1], row[5], row[6]), (0.5, 1, 0, 1))
        self.assertAlmostEqual(row[3], 0.7818314825, delta=1e-6)
        self.assertAlmostEqual(row[4], 0.6234898019, delta=1e-6)
        self.assertEqual(self.row(60)[0], 3)
        self.assertTrue(all(math.isfinite(x) for x in row))

    def test_zero_missing_and_unavailable_are_distinct(self) -> None:
        zero = self.row(0)
        missing = self.row(None, file_valid=False)
        unavailable = self.row(10, energy_available=False)
        self.assertEqual((zero[0], zero[-1]), (0, 1))
        self.assertEqual((missing[0], missing[-1]), (0, 0))
        self.assertEqual((unavailable[0], unavailable[-1]), (0, 0))
        self.assertEqual(zero[1:6], missing[1:6])

    def test_masked_values_cannot_change_features(self) -> None:
        baseline = self.row(None, energy_available=False)
        for value in (0, 1e30, float("nan"), -100):
            with self.subTest(value=value):
                self.assertEqual(self.row(value, energy_available=False), baseline)
                self.assertEqual(
                    self.row(value, file_valid=False), self.row(None, file_valid=False)
                )

    def test_inconsistent_valid_energy_fails(self) -> None:
        for value in (None, -1, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.row(value)
        for value in (True, "10"):
            with self.subTest(value=value), self.assertRaises(TypeError):
                self.row(value)

    def test_invalid_scales_and_flags_fail_without_fallback(self) -> None:
        for scale in (0, -1, float("nan"), float("inf")):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                self.row(10, energy_scale=scale)
        for changes in ({"energy_scale": True}, {"file_valid": 1}, {"energy_available": "yes"}):
            with self.subTest(changes=changes), self.assertRaises(TypeError):
                self.row(10, **changes)

    def test_overflow_fails_without_clipping_or_infinity(self) -> None:
        with self.assertRaisesRegex(ValueError, "float32"):
            self.row(1e40, energy_scale=1)
        with self.assertRaisesRegex(ValueError, "finite"):
            self.row(1e308, energy_scale=1e-308)


if __name__ == "__main__":
    unittest.main()
