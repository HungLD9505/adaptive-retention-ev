"""Unit tests for Adaptive Retention Controller synthetic cases.

Verifies Acceptance Criteria 4:
- Insufficient days (B < B_min) never switches.
- Equality / no-improvement retains active.
- Single qualifying challenger cleanly switches.
- Two qualifying challengers resolve via largest LCB -> nearest lambda -> fixed order.
- Transitions to and from lambda = 0 operate smoothly without singularity.
- Day-block bootstrap is fully deterministic given fixed seed.
"""

from __future__ import annotations

import unittest

import numpy as np

from experiments.confidence_controller.controller import (
    AdaptiveRetentionController,
    compute_day_block_bootstrap_lcb,
)
from experiments.confidence_controller.synthetic_cases import (
    generate_equality_keep_case,
    generate_insufficient_days_case,
    generate_single_switch_case,
    generate_two_challengers_case,
)


class ControllerSyntheticTests(unittest.TestCase):
    """Test suite verifying controller logic against deterministic synthetic benchmarks."""

    def test_insufficient_days_retains_active(self) -> None:
        """Controller must retain active when valid days B < B_min, even if challenger error is low."""
        controller = AdaptiveRetentionController(
            lambda_low=0.1,
            lambda_high=1.0,
            initial_lambda=0.1,
            block_size=14,
            b_min=10,
            delta=0.0,
        )
        # 5 valid days, 9 missing days -> B = 5 < 10
        records = generate_insufficient_days_case(active_id="cand_low", b_valid=5, b_missing=9)
        for r in records:
            controller.record_day_scores(r["day_index"], r["is_valid_day"], r["candidate_maes"])

        decision = controller.evaluate_block_decision(block_index=0)
        self.assertEqual(decision.decision_type, "keep")
        self.assertEqual(decision.selected_id, "cand_low")
        self.assertEqual(decision.valid_days_count, 5)
        self.assertIn("Insufficient complete days", decision.selection_reason)

    def test_equality_and_worse_retains_active(self) -> None:
        """Controller retains active when challengers show no improvement (diff <= 0)."""
        controller = AdaptiveRetentionController(
            lambda_low=0.1,
            lambda_high=1.0,
            initial_lambda=0.1,
            block_size=14,
            b_min=10,
            delta=0.0,
        )
        records = generate_equality_keep_case(active_id="cand_low", b_total=14)
        for r in records:
            controller.record_day_scores(r["day_index"], r["is_valid_day"], r["candidate_maes"])

        decision = controller.evaluate_block_decision(block_index=0)
        self.assertEqual(decision.decision_type, "keep")
        self.assertEqual(decision.selected_id, "cand_low")
        self.assertFalse(decision.challenger_stats["cand_0"]["qualifies"])
        self.assertFalse(decision.challenger_stats["cand_high"]["qualifies"])

    def test_single_qualifying_challenger_switches(self) -> None:
        """Controller switches when a single challenger has clear improvement (LCB > delta)."""
        controller = AdaptiveRetentionController(
            lambda_low=0.1,
            lambda_high=1.0,
            initial_lambda=0.1,
            block_size=14,
            b_min=10,
            delta=0.01,
        )
        records = generate_single_switch_case(
            active_id="cand_low", target_winner_id="cand_high", b_total=14
        )
        for r in records:
            controller.record_day_scores(r["day_index"], r["is_valid_day"], r["candidate_maes"])

        decision = controller.evaluate_block_decision(block_index=0)
        self.assertEqual(decision.decision_type, "switch")
        self.assertEqual(decision.selected_id, "cand_high")
        self.assertEqual(decision.selected_lambda, 1.0)
        self.assertTrue(decision.challenger_stats["cand_high"]["qualifies"])
        self.assertGreater(decision.challenger_stats["cand_high"]["lcb"], 0.01)

    def test_two_challengers_largest_lcb_wins(self) -> None:
        """When both challengers qualify, the one with largest LCB is selected."""
        controller = AdaptiveRetentionController(
            lambda_low=0.1,
            lambda_high=1.0,
            initial_lambda=0.1,
            block_size=14,
            b_min=10,
            delta=0.01,
        )
        records = generate_two_challengers_case(active_id="cand_low", mode="clear_lcb")
        for r in records:
            controller.record_day_scores(r["day_index"], r["is_valid_day"], r["candidate_maes"])

        decision = controller.evaluate_block_decision(block_index=0)
        self.assertEqual(decision.decision_type, "switch")
        self.assertEqual(decision.selected_id, "cand_high")
        # cand_high LCB (~0.10) > cand_0 LCB (~0.04)
        lcb_high = decision.challenger_stats["cand_high"]["lcb"]
        lcb_0 = decision.challenger_stats["cand_0"]["lcb"]
        self.assertGreater(lcb_high, lcb_0)

    def test_two_challengers_tied_lcb_selects_nearest_lambda(self) -> None:
        """When both challengers have identical LCB, select the one nearest to current lambda."""
        controller = AdaptiveRetentionController(
            lambda_low=0.1,
            lambda_high=1.0,
            initial_lambda=0.1,  # Active is 0.1
            block_size=14,
            b_min=10,
            delta=0.01,
        )
        # cand_0 (dist = 0.1) vs cand_high (dist = 0.9), identical daily improvement
        records = generate_two_challengers_case(active_id="cand_low", mode="tie_nearest_lambda")
        for r in records:
            controller.record_day_scores(r["day_index"], r["is_valid_day"], r["candidate_maes"])

        decision = controller.evaluate_block_decision(block_index=0)
        self.assertEqual(decision.decision_type, "switch")
        # cand_0 is nearest to 0.1 (dist |0 - 0.1| = 0.1 vs |1.0 - 0.1| = 0.9)
        self.assertEqual(decision.selected_id, "cand_0")
        self.assertEqual(decision.selected_lambda, 0.0)

    def test_two_challengers_tied_lcb_and_distance_selects_fixed_order(self) -> None:
        """When LCB and distance to active lambda are tied, choose by fixed order (smaller lambda)."""
        # Active is lambda = 0.5 (custom equidistant levels 0.0, 0.5, 1.0)
        controller = AdaptiveRetentionController(
            lambda_low=0.5,
            lambda_high=1.0,
            initial_lambda=0.5,
            block_size=14,
            b_min=10,
            delta=0.01,
        )
        # Both cand_0 (|0 - 0.5| = 0.5) and cand_high (|1.0 - 0.5| = 0.5) have identical error
        records = generate_two_challengers_case(active_id="cand_low", mode="tie_fixed_order")
        for r in records:
            controller.record_day_scores(r["day_index"], r["is_valid_day"], r["candidate_maes"])

        decision = controller.evaluate_block_decision(block_index=0)
        self.assertEqual(decision.decision_type, "switch")
        # Fixed order selects cand_0 (lambda=0.0 < lambda=1.0)
        self.assertEqual(decision.selected_id, "cand_0")
        self.assertEqual(decision.selected_lambda, 0.0)

    def test_lambda_zero_transitions_bidirectional(self) -> None:
        """Controller smoothly transitions from lambda=0 to lambda_high, and from lambda_high to lambda=0."""
        # 1. Start at lambda = 0.0
        controller = AdaptiveRetentionController(
            lambda_low=0.1,
            lambda_high=1.0,
            initial_lambda=0.0,
            block_size=14,
            b_min=10,
            delta=0.01,
        )
        self.assertEqual(controller.active_id, "cand_0")
        self.assertEqual(controller.active_lambda, 0.0)

        # cand_low has strong improvement over cand_0
        for day in range(14):
            controller.record_day_scores(
                day_index=day,
                is_valid_day=True,
                candidate_maes={"cand_0": 0.35, "cand_low": 0.22, "cand_high": 0.30},
            )
        dec1 = controller.evaluate_block_decision(block_index=0)
        self.assertEqual(dec1.decision_type, "switch")
        self.assertEqual(dec1.selected_id, "cand_low")
        self.assertEqual(controller.active_lambda, 0.1)

        # 2. In next block, cand_0 improves over cand_low -> transition back to lambda=0.0
        for day in range(14, 28):
            controller.record_day_scores(
                day_index=day,
                is_valid_day=True,
                candidate_maes={"cand_low": 0.30, "cand_0": 0.20, "cand_high": 0.32},
            )
        dec2 = controller.evaluate_block_decision(block_index=1)
        self.assertEqual(dec2.decision_type, "switch")
        self.assertEqual(dec2.selected_id, "cand_0")
        self.assertEqual(controller.active_lambda, 0.0)

    def test_deterministic_bootstrap_reproducibility(self) -> None:
        """Bootstrap calculation must yield identical LCB with the same random seed."""
        diffs = np.array([0.05, 0.02, 0.08, -0.01, 0.04, 0.06, 0.03, 0.07, 0.01, 0.05])
        lcb1 = compute_day_block_bootstrap_lcb(diffs, alpha=0.05, n_resamples=500, random_seed=42)
        lcb2 = compute_day_block_bootstrap_lcb(diffs, alpha=0.05, n_resamples=500, random_seed=42)
        self.assertEqual(lcb1, lcb2)

    def test_constant_differences_exact_lcb(self) -> None:
        """If all differences are exactly c, any bootstrap sample mean is c, so LCB must equal c."""
        c = 0.045
        diffs = np.full(14, fill_value=c, dtype=np.float64)
        lcb = compute_day_block_bootstrap_lcb(diffs, alpha=0.05, n_resamples=500, random_seed=123)
        self.assertAlmostEqual(lcb, c, places=6)


if __name__ == "__main__":
    unittest.main()
