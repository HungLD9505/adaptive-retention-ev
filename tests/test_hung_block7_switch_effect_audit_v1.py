"""Focused offline regressions for retrospective switch-effect accounting."""

from __future__ import annotations

import unittest

import torch

from tools.hung_block7_switch_effect_audit_v1 import switch_rows


def _state(*, scored: bool = True, saved_audit: float = 2.0) -> dict:
    labels = torch.zeros(24) if scored else None
    issued = {
        "day_id": "day-1",
        "block_id": 1,
        "active_level": 0.2,
        "forecasts": [torch.zeros(1, 24), torch.ones(1, 24), torch.full((1, 24), 2.0)],
        "audit_forecast": torch.ones(1, 24),
        "y_scaled": labels,
        "mae_kwh": (0.0, 2.0, 4.0) if scored else None,
        "audit_mae_kwh": saved_audit if scored else None,
    }
    return {
        "controller": {"levels": (0.0, 0.1, 0.2), "delta": 0.0},
        "energy_scale": 2.0,
        "decisions": [{"current_level": 0.0, "selected_level": 0.2}],
        "issued": [issued],
    }


class SwitchEffectAuditTests(unittest.TestCase):
    def test_old_policy_better_on_paired_next_block(self) -> None:
        rows = switch_rows(_state(), "example", "main")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["paired_scored_days"], 1)
        self.assertEqual(rows[0]["live_minus_audit_mae_kwh"], 2.0)
        self.assertTrue(rows[0]["audit_better_beyond_delta"])

    def test_missing_label_is_not_an_adverse_switch(self) -> None:
        rows = switch_rows(_state(scored=False), "example", "main")
        self.assertEqual(rows[0]["status"], "NO_PAIRED_SCORED_DAY")
        self.assertIsNone(rows[0]["audit_better_beyond_delta"])

    def test_saved_audit_score_must_match_tensor_recalculation(self) -> None:
        with self.assertRaisesRegex(ValueError, "score mismatch"):
            switch_rows(_state(saved_audit=3.0), "example", "historical")


if __name__ == "__main__":
    unittest.main()
