"""Paper arithmetic and delayed-feedback invariants for the bounded follow-up."""

import copy
import math
import unittest

import numpy as np

from ev_control.weighting_followup import METHODS, adahedge_step, probabilities, replay_weighting


def fixture():
    return dict(
        origins=["2026-01-01T00:00:00", "2026-01-02T00:00:00", "2026-01-03T00:00:00"],
        available_at=["2026-01-02T00:00:00", "2026-01-03T00:00:00", "2026-01-04T00:00:00"],
        stable=[[0.0] * 24] * 3,
        fast=[[2.0] * 24] * 3,
        labels=[[0.0] * 24] * 3,
        scale=1.0,
    )


class WeightingFollowupTests(unittest.TestCase):
    def test_adahedge_first_gap_and_next_weights_are_exact(self):
        total, gap = adahedge_step(np.zeros(2), 0, np.array([0.0, 2.0]))
        self.assertEqual(gap, 1.0)
        np.testing.assert_allclose(probabilities(total, math.log(2) / gap), [0.8, 0.2])

    def test_infinite_mix_loss_handles_leader_change(self):
        total, gap = adahedge_step(np.array([0.0, 1.0]), 0, np.array([3.0, 0.0]))
        # Previous leader loses 3; cumulative minimum increases by only 1.
        self.assertEqual(gap, 2.0)
        np.testing.assert_array_equal(total, [2, 0])

    def test_all_methods_leave_unarrived_labels_out_of_earlier_forecasts(self):
        cell = fixture()
        cell["available_at"][0] = "2026-01-03T00:00:00"
        changed = copy.deepcopy(cell)
        changed["labels"][0] = [10.0] * 24
        for method in METHODS:
            a, b = (replay_weighting(c, method, 0.43) for c in [cell, changed])
            np.testing.assert_array_equal(a["predictions_kwh"][:2], b["predictions_kwh"][:2])
            self.assertTrue(
                all(
                    e["available_at"] <= e["at"] and e["label_origin"] < e["at"]
                    for e in a["events"]
                )
            )

    def test_adahedge_weights_are_scale_invariant(self):
        a = fixture()
        b = copy.deepcopy(a)
        for key in ["stable", "fast", "labels"]:
            b[key] = (np.asarray(b[key]) * 100).tolist()
        np.testing.assert_allclose(
            replay_weighting(a, "adahedge", 0.43)["weights"],
            replay_weighting(b, "adahedge", 0.43)["weights"],
        )

    def test_ftl_can_use_endpoint_without_forced_share(self):
        r = replay_weighting(fixture(), "ftl", 0.43)
        self.assertEqual(r["weights"], [0.5, 1.0, 1.0])
        self.assertEqual(r["daily_mae"], [1.0, 0.0, 0.0])

    def test_pre_day_end_arrivals_are_rejected(self):
        cell = fixture()
        cell["available_at"][0] = cell["origins"][0]
        with self.assertRaises(ValueError):
            replay_weighting(cell, "ftl", 0.43)
