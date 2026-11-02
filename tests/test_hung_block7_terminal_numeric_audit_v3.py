"""Regression checks for the strict saved-score and tensor inventory audit."""

import unittest

import torch

from tools.hung_block7_terminal_numeric_audit_v3 import (
    recompute_candidate_scores,
    validate_issued_forecast_order,
)


def state(*, scored: bool = True) -> dict:
    row = {
        "forecasts": [torch.zeros((1, 24))],
        "y_scaled": torch.ones(24) if scored else None,
        "mae_kwh": (10.0,) if scored else None,
        "normalized_mae": (1.0,) if scored else None,
    }
    return {"energy_scale": 10.0, "issued": [row]}


class TerminalNumericStrictAuditTests(unittest.TestCase):
    def test_checks_both_score_units_and_unscored_inventory(self):
        saved = state()
        saved["issued"].append(state(scored=False)["issued"][0])
        result = recompute_candidate_scores(saved, 1)
        self.assertEqual(result["recomputed_candidate_scores"], 1)
        self.assertEqual(result["unscored_issued_origins"], 1)
        self.assertEqual(result["max_abs_recomputed_normalized_error"], 0.0)
        self.assertEqual(result["max_abs_recomputed_score_error_kwh"], 0.0)

    def test_rejects_nonfinite_or_wrong_shape_tensor(self):
        for field, tensor in (
            ("forecasts", torch.full((1, 24), float("nan"))),
            ("forecasts", torch.zeros((2, 24))),
            ("y_scaled", torch.full((24,), float("inf"))),
            ("y_scaled", torch.ones((1, 24))),
        ):
            with self.subTest(field=field, shape=tuple(tensor.shape)):
                saved = state()
                saved["issued"][0][field] = [tensor] if field == "forecasts" else tensor
                with self.assertRaises(ValueError):
                    recompute_candidate_scores(saved, 1)

    def test_rejects_nonfinite_score_and_unscored_score(self):
        for field, value in (
            ("mae_kwh", (float("nan"),)),
            ("normalized_mae", (float("inf"),)),
        ):
            with self.subTest(field=field):
                saved = state()
                saved["issued"][0][field] = value
                with self.assertRaises(ValueError):
                    recompute_candidate_scores(saved, 1)
        saved = state(scored=False)
        saved["issued"][0]["mae_kwh"] = (0.0,)
        with self.assertRaises(ValueError):
            recompute_candidate_scores(saved, 1)

    def test_rejects_invalid_scale_or_candidate_inventory(self):
        saved = state()
        saved["energy_scale"] = 0.0
        with self.assertRaises(ValueError):
            recompute_candidate_scores(saved, 1)
        with self.assertRaises(ValueError):
            recompute_candidate_scores(state(), 2)

    def test_rejects_missing_or_reordered_journal_forecast(self):
        issued = {"issued": [{"day_id": "day-1"}, {"day_id": "day-2"}]}
        validate_issued_forecast_order(
            issued, ["fork:0", "forecast:day-1", "score:day-1", "forecast:day-2"], "run"
        )
        for events in (
            ["forecast:day-1"],
            ["forecast:day-2", "forecast:day-1"],
        ):
            with self.subTest(events=events), self.assertRaisesRegex(ValueError, "Issued origins"):
                validate_issued_forecast_order(issued, events, "run")


if __name__ == "__main__":
    unittest.main()
