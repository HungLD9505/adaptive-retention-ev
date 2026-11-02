"""Offline checks for Development seed-comparison denominators and nulls."""

from __future__ import annotations

import unittest

from tools.hung_development_seed_stability import summarize_group


def cell(seed: int, method_mae: float, *, day_hash: str = "a" * 64) -> dict:
    return {
        "budget": 7,
        "method": "drift",
        "reference": "main",
        "entity_id": "station-1",
        "seed": seed,
        "paired_days": 2,
        "paired_day_ids_sha256": day_hash,
        "method_metrics": {"mae_kwh": method_mae, "rmse_kwh": method_mae + 1},
        "reference_metrics": {"mae_kwh": 3.0, "rmse_kwh": 4.0},
    }


def station_first(method_mae: float) -> dict:
    return {
        "method_metrics": {"mae_kwh": method_mae, "rmse_kwh": method_mae + 1},
        "reference_metrics": {"mae_kwh": 3.0, "rmse_kwh": 4.0},
    }


class SeedStabilityTests(unittest.TestCase):
    def test_three_seeds_preserve_sign_crossing_and_denominator(self) -> None:
        summary, rows = summarize_group(
            [cell(7, 2.0), cell(11, 3.0), cell(19, 4.0)], station_first(3.0)
        )
        self.assertEqual(summary["stations"], 1)
        self.assertEqual(summary["seeds_per_station"], 3)
        self.assertEqual(summary["paired_cells"], 3)
        self.assertEqual(summary["mixed_sign_mae_stations"], 1)
        self.assertEqual(summary["mae_seed_span_kwh"], 2.0)
        self.assertEqual([row["mae_gain_kwh"] for row in rows], [1.0, 0.0, -1.0])

    def test_single_seed_has_null_seed_span(self) -> None:
        summary, rows = summarize_group([cell(7, 2.0)], station_first(2.0))
        self.assertIsNone(summary["mae_seed_span_kwh"])
        self.assertIsNone(summary["rmse_seed_span_kwh"])
        self.assertEqual(len(rows), 1)

    def test_seed_day_hash_mismatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "paired-day hashes differ"):
            summarize_group(
                [cell(7, 2.0), cell(11, 3.0, day_hash="b" * 64), cell(19, 4.0)],
                station_first(3.0),
            )


if __name__ == "__main__":
    unittest.main()
