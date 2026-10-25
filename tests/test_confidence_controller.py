"""Independent expected-value fixtures, no model/data downloads or efficacy claims."""

import itertools
import random
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from ev_control.confidence import (
    Comparison,
    ControllerConfig,
    DailyScore,
    choose_level,
    decide,
    linear_quantile,
    moving_block_indices,
)

DAY = timedelta(days=1)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.config = ControllerConfig(0.01, 0.1, 0.01, 14, 7, 0, 0.05, 3, 200, 42)
        self.start = datetime(2022, 12, 1, tzinfo=timezone(timedelta(hours=8)))

    def rows(self, scores=(3.0, 2.0, 1.0)):
        return [
            DailyScore(
                self.start + i * DAY,
                self.start + i * DAY,
                self.start + (i + 1) * DAY,
                24,
                scores,
                "scale",
                tuple(f"{i}/{j}" for j in range(3)),
            )
            for i in range(14)
        ]

    def decision(self, rows=None, active=0.01, config=None, **changes):
        cfg = config or self.config
        return decide(
            rows if rows is not None else self.rows(),
            config=cfg,
            active_lambda=active,
            block_start=self.start,
            as_of=self.start + cfg.block_days * DAY,
            stream_id="fixture/target/7d/seed42",
            scale_id="scale",
            **changes,
        )

    def test_positive_improvement_switches_to_high(self):
        d = self.decision()
        self.assertEqual(d.selected_lambda, 0.1)
        self.assertEqual(d.reason, "switch")
        self.assertEqual(d.valid_days, 14)
        self.assertEqual(d.comparisons[1].mean_improvement, 1)
        self.assertEqual(d.comparisons[1].lcb, 1)

    def test_zero_active_can_switch_and_high_can_switch_to_zero(self):
        self.assertEqual(self.decision(active=0).selected_lambda, 0.1)
        self.assertEqual(self.decision(self.rows((1.0, 2.0, 3.0)), active=0.1).selected_lambda, 0)

    def test_equal_zero_improvement_keeps_active(self):
        d = self.decision(self.rows((2.0, 2.0, 2.0)))
        self.assertEqual(d.selected_lambda, 0.01)
        self.assertTrue(all(c.lcb == 0 and not c.qualifies for c in d.comparisons))

    def test_exact_positive_delta_equality_keeps(self):
        d = self.decision(config=replace(self.config, delta=1))
        self.assertEqual(d.selected_lambda, 0.01)
        self.assertFalse(d.comparisons[1].qualifies)

    def test_larger_mean_is_not_sufficient_with_negative_lcb(self):
        rows = self.rows()
        # One unusually good day does not force a positive lower confidence bound.
        rows = [replace(r, mae=(3.0, 2.0, 2.1)) for r in rows]
        rows[0] = replace(rows[0], mae=(3.0, 2.0, 0.0))
        d = self.decision(rows)
        self.assertGreater(d.comparisons[1].mean_improvement, 0)
        self.assertLessEqual(d.comparisons[1].lcb, 0)
        self.assertEqual(d.selected_lambda, 0.01)

    def test_bmin_counts_complete_days_not_24_labels(self):
        d = self.decision(self.rows()[:6])
        self.assertEqual(d.valid_days, 6)
        self.assertEqual(d.reason, "insufficient_valid_days")
        self.assertEqual(d.comparisons, ())
        self.assertEqual(d.selected_lambda, 0.01)
        self.assertEqual(d.absent_days, 8)

    def test_all_missing_keeps_without_bootstrap(self):
        with patch(
            "ev_control.confidence.moving_block_indices",
            side_effect=AssertionError("must not bootstrap"),
        ):
            d = self.decision([])
        self.assertEqual(d.valid_days, 0)
        self.assertEqual(d.selected_lambda, 0.01)

    def test_availability_and_missing_coverage(self):
        rows = self.rows()
        rows[0] = replace(rows[0], valid_labels=23, mae=None)
        rows[1] = replace(rows[1], available_at=None)
        rows[2] = replace(rows[2], available_at=self.start + 20 * DAY)
        d = self.decision(rows)
        self.assertEqual(
            (d.valid_days, d.incomplete_days, d.pending_days, d.absent_days), (11, 1, 2, 0)
        )
        self.assertEqual(d.valid_day_gaps, 0)  # only a leading missing stretch
        rows[7] = replace(rows[7], valid_labels=0, mae=None)
        self.assertEqual(self.decision(rows).valid_day_gaps, 1)

    def test_unavailable_future_errors_cannot_change_decision(self):
        rows = self.rows()
        rows[-1] = replace(rows[-1], available_at=self.start + 15 * DAY)
        expected = self.decision(rows)
        rows[-1] = replace(rows[-1], mae=(float("nan"), -100000.0, float("inf")))
        self.assertEqual(self.decision(rows), expected)

    def test_outside_block_scores_do_not_affect_snapshot(self):
        extra = replace(self.rows()[0], origin=self.start - DAY, mae=(float("nan"),) * 3)
        self.assertEqual(self.decision([extra, *self.rows()]), self.decision())

    def test_score_order_input_order_and_rng_are_deterministic(self):
        random.seed(137)
        state = random.getstate()
        a = self.decision()
        self.assertEqual(state, random.getstate())
        b = self.decision(list(reversed(self.rows())))
        self.assertEqual(a, b)
        self.assertEqual(a.as_dict()["algorithm"], "ev-retention-controller-mbb-v1")

    def test_two_challenger_ties_and_fixed_order(self):
        candidates = (Comparison(0.0, 1, 1, True), Comparison(0.1, 1, 1, True))
        self.assertEqual(choose_level(0.01, self.config.levels, candidates), 0.0)
        # Equal LCB and equal lambda distance: use the declared fixed order.
        self.assertEqual(
            choose_level(
                1.0, (0.0, 1.0, 2.0), (Comparison(2.0, 1, 1, True), Comparison(0.0, 1, 1, True))
            ),
            0.0,
        )
        self.assertEqual(
            choose_level(
                0.01, self.config.levels, (Comparison(0.0, 2, 1, True), Comparison(0.1, 2, 2, True))
            ),
            0.1,
        )

    def test_quantile_is_independently_calculable(self):
        self.assertEqual(linear_quantile([4, 1, 3, 2], 0.25), 1.75)
        self.assertEqual(linear_quantile([4, 1, 3, 2], 0), 1)
        self.assertEqual(linear_quantile([4, 1, 3, 2], 1), 4)

    def test_exact_enumerated_nonconstant_block_distribution(self):
        cfg = replace(self.config, block_days=4, min_valid_days=4, segment_days=2, resamples=9)
        # Three overlapping two-day blocks; enumerate all nine pairs independently.
        blocks = ((0, 1), (1, 2), (2, 3))
        draws = tuple(a + b for a, b in itertools.product(blocks, repeat=2))
        rows = [replace(r, mae=(6.0 - 2 * i, 6.0, 6.0)) for i, r in enumerate(self.rows()[:4])]
        with patch("ev_control.confidence.moving_block_indices", return_value=draws):
            d = self.decision(rows, active=0.1, config=cfg)
        self.assertEqual(d.comparisons[0].mean_improvement, 3)
        self.assertAlmostEqual(d.comparisons[0].lcb, 1.2)
        self.assertEqual(d.selected_lambda, 0.0)

    def test_bootstrap_contiguous_segments_trim_and_seed(self):
        draws = moving_block_indices(7, 3, 10, 42)
        self.assertEqual(draws, moving_block_indices(7, 3, 10, 42))
        self.assertNotEqual(draws, moving_block_indices(7, 3, 10, 43))
        for draw in draws:
            self.assertEqual(len(draw), 7)
            for start in (0, 3):
                self.assertEqual(
                    draw[start : start + 3], tuple(range(draw[start], draw[start] + 3))
                )
            self.assertTrue(all(0 <= i < 7 for i in draw))

    def test_late_decisions_and_wrong_clocks_rejected(self):
        with self.assertRaises(ValueError):
            decide(
                self.rows(),
                config=self.config,
                active_lambda=0.01,
                block_start=self.start,
                as_of=self.start + 15 * DAY,
                stream_id="s",
                scale_id="scale",
            )
        with self.assertRaises(ValueError):
            self.decision([replace(self.rows()[0], origin=self.start.replace(tzinfo=None))])
        with self.assertRaises(ValueError):
            self.decision(active=0.03)

    def test_publisher_naive_clock_is_preserved(self):
        self.start = self.start.replace(tzinfo=None)
        d = self.decision()
        self.assertEqual(d.effective_from, "2022-12-15T00:00:00")

    def test_bad_config_rejected(self):
        for changes in (
            {"lambda_low": 0},
            {"lambda_high": 0.001},
            {"initial_lambda": 0.5},
            {"seed": True},
            {"delta": -1},
            {"alpha": 1},
            {"resamples": 1},
            {"segment_days": 7},
            {"min_valid_days": 15},
            {"lambda_high": float("nan")},
        ):
            with self.assertRaises(ValueError):
                replace(self.config, **changes)

    def test_bad_arrived_scores_predictions_or_scale_rejected(self):
        for changes in (
            {"mae": (1.0, float("nan"), 2.0)},
            {"mae": (-1.0, 1.0, 2.0)},
            {"mae": None},
            {"scale_id": "other"},
            {"valid_labels": 23},
            {"valid_labels": True},
            {"prediction_ids": ("x", "x", "x")},
            {"issued_at": self.start + DAY},
            {"available_at": self.start},
        ):
            with self.assertRaises(ValueError):
                self.decision([replace(self.rows()[0], **changes)])
        with self.assertRaises(ValueError):
            self.decision([self.rows()[0], self.rows()[0]])
