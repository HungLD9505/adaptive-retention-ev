"""Recompute saved 24-hour scores and compare selected live forecasts."""

import unittest

import torch

from tools.hung_block7_terminal_numeric_audit_v2 import (
    compare_live_forecasts,
    recompute_candidate_scores,
)


class TerminalNumericAuditTests(unittest.TestCase):
    def test_recomputes_complete_day_mae(self):
        labels = torch.ones(24)
        forecast = torch.zeros((1, 24))
        state = {
            "energy_scale": 10.0,
            "issued": [{"y_scaled": labels, "forecasts": [forecast], "mae_kwh": (10.0,)}],
        }
        checked, error, above = recompute_candidate_scores(state)
        self.assertEqual((checked, error, above), (1, 0.0, 0))

    def test_live_forecast_uses_each_runs_active_level(self):
        historical = [
            {
                "day_id": "2023-01-01",
                "index": 0,
                "active_level": 0.0,
                "forecasts": [torch.tensor([1.0]), torch.tensor([2.0])],
            }
        ]
        main = [
            {
                "day_id": "2023-01-01",
                "index": 0,
                "active_level": 0.1,
                "forecasts": [torch.tensor([1.0]), torch.tensor([2.0])],
            }
        ]
        result = compare_live_forecasts(historical, main, [0.0, 0.1])
        self.assertEqual(result["live_different_origins"], 1)
        self.assertEqual(result["max_abs_normalized_live_difference"], 1.0)
