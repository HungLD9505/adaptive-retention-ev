"""External-artifact checks; intentionally excluded from offline discovery."""

from __future__ import annotations

import unittest
from copy import deepcopy

from tools import hung_q_controller_decision_sensitivity_v1 as sensitivity


class ControllerDecisionSensitivityTests(unittest.TestCase):
    def test_real_pinned_development_decisions(self) -> None:
        result = sensitivity.audit()
        self.assertEqual(result["historical_main_runs"], 69)
        self.assertEqual(result["saved_decisions_reproduced"], 414)
        self.assertEqual(result["bootstrap_eligible_decisions"], 168)
        self.assertEqual(result["fixed_draw_quantile_only_changed"], 3)
        self.assertEqual(result["full_q_rule_changed"], 8)

    def test_saved_decision_mismatch_is_rejected(self) -> None:
        import torch

        path = sensitivity.TERMINAL / "main_b14s11e1405.pt"
        state = torch.load(path, map_location="cpu", weights_only=True)
        block_id = 3
        rows = sorted(
            (
                row
                for row in state["issued"]
                if row["block_id"] == block_id and row["normalized_mae"] is not None
            ),
            key=lambda row: row["day_id"],
        )
        altered = deepcopy(state)
        altered["decisions"][block_id]["selected_level"] = 0.2
        with self.assertRaisesRegex(ValueError, "does not reproduce"):
            sensitivity._check_saved_hung_decision(altered, block_id, rows)

    def test_quantile_source_matches_independent_example(self) -> None:
        q = sensitivity._pinned_q_controller()
        self.assertEqual(q.linear_quantile([4, 1, 3, 2], 0.25), 1.75)
