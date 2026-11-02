"""Checks for the bounded Block7 manifest metric comparison."""

from __future__ import annotations

import unittest

from tools.hung_block7_manifest_metric_audit import metric_row


class MetricAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pair = {
            "cell_id": "b7s7e1",
            "budget_days": 7,
            "seed": 7,
            "historical_run_id": "block7_b7s7e1",
            "main_run_id": "main_b7s7e1",
            "historical_manifest_sha256": "old-hash",
            "main_manifest_sha256": "main-hash",
        }

    def manifest(self, score: float | None, days: int) -> dict:
        return {
            "coverage": {"scored": days},
            "metrics_kwh": {
                "live": None
                if score is None
                else {"hours": 24 * days, "mae_kwh": score, "rmse_kwh": score + 1},
                "audit_scored_days": days,
            },
        }

    def test_preserves_null_metric(self) -> None:
        row = metric_row(self.pair, self.manifest(None, 0), self.manifest(None, 0))
        self.assertIsNone(row["main_minus_historical_live_mae_kwh"])
        self.assertTrue(row["live_metric_equal"])

    def test_reports_signed_policy_difference(self) -> None:
        row = metric_row(self.pair, self.manifest(2.0, 1), self.manifest(1.5, 1))
        self.assertEqual(row["main_minus_historical_live_mae_kwh"], -0.5)
        self.assertFalse(row["live_metric_equal"])

    def test_rejects_inconsistent_scored_hours(self) -> None:
        main = self.manifest(1.5, 1)
        main["metrics_kwh"]["live"]["hours"] = 48
        with self.assertRaisesRegex(ValueError, "hours disagree"):
            metric_row(self.pair, self.manifest(2.0, 1), main)
