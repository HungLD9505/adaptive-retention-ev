"""Independent arithmetic and label-availability checks for forecast fusion."""

import copy
import math
import unittest

import numpy as np

from ev_control.expert_mix import fit_static_weight, forecast_mixture, update_stable_weight


def cell(stable=2, fast=0, labels=1, days=4):
    return {
        "origins": [f"2020-01-{i:02}T00:00:00+00:00" for i in range(1, days + 1)],
        "available_at": [f"2020-01-{i:02}T00:00:00+00:00" for i in range(2, days + 2)],
        "stable": np.full((days, 24), stable).tolist(),
        "fast": np.full((days, 24), fast).tolist(),
        "labels": np.full((days, 24), labels).tolist(),
        "scale": 1.0,
    }


class ExpertMixTests(unittest.TestCase):
    def test_matches_direct_exponential_update(self):
        a, b = 0.3 * math.exp(-0.4), 0.7 * math.exp(-1.2)
        posterior = a / (a + b)
        self.assertAlmostEqual(
            update_stable_weight(0.3, 0.2, 0.6, eta=2, share=0.1),
            0.9 * posterior + 0.1 * (1 - posterior),
        )

    def test_endpoint_recovery_and_extreme_losses(self):
        self.assertEqual(update_stable_weight(1, 0, 1, eta=1, share=0.1), 0.9)
        self.assertEqual(update_stable_weight(0, 0, 1, eta=1, share=0.1), 0.1)
        self.assertEqual(update_stable_weight(0.5, 1e200, 0, eta=1e200, share=0.1), 0.1)

    def test_invalid_parameters_rejected_even_without_updates(self):
        for kwargs in ({"eta": 0}, {"eta": float("nan")}, {"eta": 1, "share": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                forecast_mixture(cell(days=1), 0.5, **kwargs)
        for weight in (-1, 2, float("nan")):
            with self.assertRaises(ValueError):
                forecast_mixture(cell(), weight)

    def test_static_weight_interior_boundary_and_identical(self):
        self.assertEqual(fit_static_weight([cell()]), 0.5)
        self.assertEqual(fit_static_weight([cell(labels=5)]), 1)
        self.assertEqual(fit_static_weight([cell(labels=-1)]), 0)
        self.assertEqual(fit_static_weight([cell(stable=0)]), 1)

    def test_static_calibration_weights_cells_equally(self):
        # One long cell must not outweigh two independent short cells.
        self.assertEqual(
            fit_static_weight([cell(labels=0, days=20), cell(labels=2), cell(labels=2)]), 1
        )

    def test_static_optimizer_matches_dense_search(self):
        rng = np.random.default_rng(8)
        c = cell()
        for key in ("stable", "fast", "labels"):
            c[key] = rng.uniform(0, 5, (4, 24)).tolist()
        weight = fit_static_weight([c])
        actual = forecast_mixture(c, weight)["mae"]
        grid = min(forecast_mixture(c, float(w))["mae"] for w in np.linspace(0, 1, 501))
        self.assertLessEqual(actual, grid + 1e-12)

    def test_future_labels_cannot_change_earlier_forecasts(self):
        c = cell(labels=0)
        changed = copy.deepcopy(c)
        changed["labels"][1:] = np.full((3, 24), 100).tolist()
        a = forecast_mixture(c, 0.5, eta=1, share=0.1)
        b = forecast_mixture(changed, 0.5, eta=1, share=0.1)
        self.assertEqual(a["predictions_kwh"][:2], b["predictions_kwh"][:2])
        self.assertNotEqual(a["weights"][2], b["weights"][2])

    def test_delayed_losses_follow_arrival_order(self):
        c = cell()
        c["available_at"][0] = c["available_at"][2]
        result = forecast_mixture(c, 0.5, eta=1, share=0.1)
        self.assertEqual(
            [e["label_origin"] for e in result["events"]],
            [c["origins"][1], c["origins"][0], c["origins"][2]],
        )
        self.assertEqual(result["weights"][:2], [0.5, 0.5])

    def test_equivalent_timezones_have_same_causal_clock(self):
        c = cell(labels=0)
        a = forecast_mixture(c, 0.5, eta=1, share=0.1)
        c["available_at"][0] = "2020-01-02T08:00:00+08:00"
        b = forecast_mixture(c, 0.5, eta=1, share=0.1)
        self.assertEqual(a, b | {"events": a["events"]})

    def test_bad_vectors_clocks_and_early_labels_fail(self):
        for key, value in (
            ("stable", [[float("nan")] * 24] * 4),
            ("fast", [[-1] * 24] * 4),
            ("scale", 0),
            ("origins", list(reversed(cell()["origins"]))),
            ("available_at", cell()["origins"]),
        ):
            c = cell()
            c[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                forecast_mixture(c, 0.5)


if __name__ == "__main__":
    unittest.main()
