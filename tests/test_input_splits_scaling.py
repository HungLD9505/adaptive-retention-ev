"""Independent fixtures for proposed identity splits and permitted-prefix scaling."""

import unittest
from datetime import datetime, timedelta, timezone

from ev_inputs.scaling import EnergySample, fit_energy_scale, target_prefix_start
from ev_inputs.splits import entity_role


class SplitTests(unittest.TestCase):
    def test_fixed_roles_and_order_independence(self):
        expected = {"1001": "final", "1002": "source", "1003": "final"}
        actual = {key: entity_role("urbanev", "SZH", key, salt="review-v1") for key in expected}
        self.assertEqual(actual, expected)
        self.assertEqual(
            actual,
            {
                key: entity_role("urbanev", "SZH", key, salt="review-v1")
                for key in reversed(expected)
            },
        )

    def test_namespace_and_leading_zeros_are_preserved(self):
        # Separate IDs may happen to share a role; their encoded identities must not alias.
        # Patch the digest boundary to inspect actual canonical inputs rather than assert
        # that unrelated identities always hash to different roles.
        import hashlib
        from unittest.mock import patch

        captured = []
        original = hashlib.sha256

        def capture(payload):
            captured.append(payload)
            return original(payload)

        with patch("ev_inputs.splits.hashlib.sha256", side_effect=capture):
            for dataset, city, entity in (
                ("charged", "AMS", "01"),
                ("charged", "AMS", "1"),
                ("charged", "SZH", "1"),
                ("urbanev", "SZH", "1"),
                ("a|b", "c", "d"),
                ("a", "b|c", "d"),
            ):
                entity_role(dataset, city, entity, salt="review-v1")
        self.assertEqual(len(set(captured)), 6)

    def test_invalid_identity(self):
        for value in ("", " ", 1, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                entity_role("charged", "AMS", value, salt="review-v1")
        with self.assertRaises(ValueError):
            entity_role("charged", "AMS", "1", salt="")


class ScalingTests(unittest.TestCase):
    start = datetime(2023, 6, 24)
    cutoff = datetime(2023, 7, 1)
    identity = ("charged", "AMS", "001")

    def row(self, hour, value, valid=True, delay=1):
        timestamp = self.start + timedelta(hours=hour)
        return EnergySample(timestamp, timestamp + timedelta(hours=delay), value, valid)

    def fit(self, rows, **kwargs):
        return fit_energy_scale(
            rows,
            identity=self.identity,
            start=kwargs.get("start", self.start),
            cutoff=kwargs.get("cutoff", self.cutoff),
        )

    def test_linear_quantile_and_inverse(self):
        fitted = self.fit([self.row(0, 0), self.row(1, 10), self.row(2, 20)])
        self.assertAlmostEqual(fitted.p95_kwh, 19)
        self.assertEqual((fitted.valid_count, fitted.zero_count), (3, 1))
        self.assertIsNone(fitted.fallback)
        self.assertAlmostEqual((40 / fitted.energy_scale) * fitted.energy_scale, 40)
        self.assertGreater(40 / fitted.energy_scale, 1)

    def test_suffix_and_pre_prefix_values_cannot_affect_fit(self):
        prefix = [self.row(0, 10), self.row(1, 20)]
        expected = self.fit(prefix)
        self.assertEqual(expected, self.fit(prefix + [self.row(168, 1e99), self.row(-1, -99)]))
        self.assertEqual(expected, self.fit(list(reversed(prefix))))

    def test_exclusive_cutoff_and_label_availability(self):
        result = self.fit(
            [
                self.row(0, 2),
                self.row(167, 2),
                self.row(168, 1000),
                self.row(1, 1000, delay=168),
                self.row(2, None, valid=False),
            ]
        )
        self.assertEqual(result.valid_count, 2)
        self.assertEqual(result.energy_scale, 2)

    def test_zero_and_sparse_p95_fallback_keep_activity(self):
        for values in ([0] * 100, [0] * 99 + [10]):
            fitted = self.fit([self.row(i, value) for i, value in enumerate(values)])
            self.assertEqual(fitted.energy_scale, 1)
            self.assertEqual(fitted.fallback, "zero-p95-unit-kwh")
            self.assertEqual(fitted.valid_count, 100)
        self.assertEqual(self.fit([self.row(0, 0.01)]).energy_scale, 0.01)

    def test_empty_and_missing_are_not_zero_prefix(self):
        for rows in ([], [self.row(0, None, valid=False)], [self.row(0, 5, delay=200)]):
            with self.assertRaisesRegex(ValueError, "No valid available"):
                self.fit(rows)

    def test_invalid_valid_values_fail(self):
        for value in (None, True, "5", -1, float("nan"), float("inf"), 10**1000):
            with self.subTest(value=str(value)[:20]), self.assertRaises(ValueError):
                self.fit([self.row(0, value)])

    def test_duplicate_grid_and_availability_fail(self):
        row = self.row(0, 1)
        cases = [
            [row, row],
            [self.row(0, 1, delay=0)],
            [EnergySample(self.start + timedelta(minutes=5), self.cutoff, 1, True)],
            [EnergySample(self.start, self.cutoff.replace(tzinfo=timezone.utc), 1, True)],
        ]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.fit(rows)

    def test_clock_and_bounds_fail_closed(self):
        with self.assertRaises(ValueError):
            self.fit([], cutoff=self.cutoff.replace(tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            self.fit([], start=self.cutoff)
        with self.assertRaises(ValueError):
            self.fit([EnergySample(self.start.replace(tzinfo=timezone.utc), self.cutoff, 1, True)])

    def test_fingerprint_identifies_population_and_scope(self):
        fitted = self.fit([self.row(0, 2)])
        self.assertNotEqual(fitted.fit_sha256, self.fit([self.row(0, 3)]).fit_sha256)
        self.assertNotEqual(
            fitted.fit_sha256,
            self.fit([self.row(0, 2)], cutoff=self.cutoff + timedelta(hours=1)).fit_sha256,
        )

    def test_exact_history_budgets(self):
        for days, expected in (
            (7, datetime(2023, 6, 24)),
            (14, datetime(2023, 6, 17)),
            (28, datetime(2023, 6, 3)),
        ):
            self.assertEqual(target_prefix_start(self.cutoff, days), expected)
        for days in (True, 1, 6, 8, 29, 7.0):
            with self.subTest(days=days), self.assertRaises((ValueError, TypeError)):
                target_prefix_start(self.cutoff, days)


if __name__ == "__main__":
    unittest.main()
