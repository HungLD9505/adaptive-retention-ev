"""Independent expected-value checks for the confidence controller."""

from __future__ import annotations

import unittest

from experiments.hung_sprint2.controller import ControllerConfig, DailyScore, decide_block


def config(**changes: object) -> ControllerConfig:
    values = {
        "levels": (0.0, 0.1, 0.3),
        "initial_level": 0.1,
        "block_days": 14,
        "min_complete_days": 3,
        "delta": 0.0,
        "alpha": 0.05,
        "bootstrap_segment_days": 2,
        "bootstrap_resamples": 101,
        "seed": 73,
        "challenger_rule": "bonferroni_two",
    }
    values.update(changes)
    return ControllerConfig(**values)


def complete(day: int, errors: tuple[float, float, float]) -> DailyScore:
    return DailyScore(f"day-{day}", True, True, errors)


class ControllerTests(unittest.TestCase):
    def test_insufficient_complete_days_and_missing_days(self) -> None:
        days = [
            complete(0, (0.5, 1.0, 0.2)),
            DailyScore("day-1", True, False, None),
            DailyScore("day-2", False, False, None),
            complete(3, (0.5, 1.0, 0.2)),
        ]
        decision = decide_block(config(), current_level=0.1, block_id=0, days=days)
        self.assertEqual(decision.reason, "insufficient_days")
        self.assertEqual(decision.selected_level, 0.1)
        self.assertEqual((decision.valid_days, decision.skipped_days), (2, 2))
        self.assertEqual(decision.lower_bounds, (None, None, None))

    def test_exact_threshold_equality_keeps_active(self) -> None:
        days = [complete(day, (1.0, 1.5, 1.5)) for day in range(3)]
        decision = decide_block(config(delta=0.5), current_level=0.1, block_id=0, days=days)
        self.assertEqual(decision.lower_bounds, (0.5, None, 0.0))
        self.assertEqual(decision.reason, "no_qualifying_challenger")
        self.assertFalse(decision.switched)

    def test_largest_lcb_wins_with_two_challengers(self) -> None:
        days = [complete(day, (0.5, 1.0, 0.2)) for day in range(3)]
        decision = decide_block(config(), current_level=0.1, block_id=1, days=days)
        self.assertEqual(decision.selected_level, 0.3)
        self.assertAlmostEqual(decision.lower_bounds[0], 0.5)
        self.assertIsNone(decision.lower_bounds[1])
        self.assertAlmostEqual(decision.lower_bounds[2], 0.8)
        self.assertEqual(decision.alpha_per_challenger, 0.025)

    def test_equal_lcb_prefers_nearest_current_level(self) -> None:
        days = [complete(day, (0.5, 1.0, 0.5)) for day in range(3)]
        decision = decide_block(config(), current_level=0.1, block_id=2, days=days)
        self.assertEqual(decision.selected_level, 0.0)

    def test_equal_lcb_and_distance_uses_fixed_level_order(self) -> None:
        days = [complete(day, (0.5, 1.0, 0.5)) for day in range(3)]
        decision = decide_block(
            config(levels=(0.0, 0.1, 0.2)), current_level=0.1, block_id=3, days=days
        )
        self.assertEqual(decision.selected_level, 0.0)

    def test_zero_level_can_be_active_and_keep_trained_active(self) -> None:
        days = [complete(day, (0.2, 0.5, 0.6)) for day in range(3)]
        decision = decide_block(config(), current_level=0.0, block_id=4, days=days)
        self.assertEqual(decision.selected_level, 0.0)
        self.assertFalse(decision.switched)
        self.assertEqual(decision.reason, "no_qualifying_challenger")

    def test_bootstrap_reproducibility_and_paired_day_resampling(self) -> None:
        days = [complete(day, (0.8 + 0.01 * day, 0.9, 0.7 + 0.02 * day)) for day in range(10)]
        first = decide_block(config(), current_level=0.1, block_id=5, days=days)
        second = decide_block(config(), current_level=0.1, block_id=5, days=days)
        self.assertEqual(first, second)
        self.assertEqual(first.valid_days, 10)
        self.assertIsNone(first.lower_bounds[1])

    def test_rejects_invalid_config_and_score(self) -> None:
        with self.assertRaisesRegex(ValueError, "ordered"):
            config(levels=(0.0, 0.3, 0.1))
        with self.assertRaisesRegex(ValueError, "arrived"):
            DailyScore("day", False, True, (1.0, 1.0, 1.0))
        with self.assertRaisesRegex(ValueError, "finite"):
            DailyScore("day", True, True, (1.0, float("nan"), 1.0))

    def test_rejects_duplicate_day_and_unknown_current_level(self) -> None:
        scores = [complete(0, (1.0, 1.0, 1.0))] * 3
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            decide_block(config(), current_level=0.1, block_id=0, days=scores)
        with self.assertRaisesRegex(ValueError, "absent"):
            decide_block(config(), current_level=0.2, block_id=0, days=[])


if __name__ == "__main__":
    unittest.main()
