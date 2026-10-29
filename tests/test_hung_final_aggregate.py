"""Offline checks for the frozen Final aggregation boundary."""

import unittest

from tools.hung_final_aggregate_v1 import metric, pair_rows, station_interval, station_results


def row(variant: str, seed: int, days: dict) -> dict:
    return {
        "dataset_id": "urbanev",
        "city_id": "SZH",
        "entity_id": "2118",
        "budget_days": 7,
        "seed": seed,
        "variant": variant,
        "input_manifest_sha256": "a" * 64,
        "source_checkpoint_sha256": None if variant == "target_only" else "b" * 64,
        "days": days,
    }


def day(absolute: float, label: str = "a") -> dict:
    return {"absolute": absolute, "squared": absolute * absolute / 24, "label_sha256": label * 64}


class FinalAggregateTests(unittest.TestCase):
    def test_microaverage_and_station_bootstrap(self) -> None:
        scored = metric([day(24), day(48)])
        self.assertEqual(scored["hours"], 48)
        self.assertEqual(scored["mae_kwh"], 1.5)
        self.assertAlmostEqual(scored["rmse_kwh"], (5 / 2) ** 0.5)
        self.assertEqual(station_interval([1.0]), (1.0, 1.0))
        self.assertIsNone(metric([]))

    def test_exact_common_day_pairing_and_negative_transfer(self) -> None:
        rows = [
            row("target_only", 7, {"d1": day(24), "d2": day(48)}),
            row("main", 7, {"d1": day(48), "d3": day(1)}),
        ]
        paired, blocked = pair_rows(rows)
        self.assertFalse(blocked)
        target_pair = next(item for item in paired if item["reference"] == "target_only")
        self.assertEqual(target_pair["paired_days"], 1)
        self.assertEqual(target_pair["method_mae_kwh"], 2.0)
        self.assertEqual(target_pair["reference_mae_kwh"], 1.0)
        station = next(
            item for item in station_results(paired) if item["reference"] == "target_only"
        )
        self.assertEqual(station["negative_transfer_stations"], 1)
        self.assertEqual(station["negative_transfer_denominator"], 1)
        self.assertEqual(station["transfer_gain"], -1.0)

    def test_missing_and_mismatched_labels_block_without_zero_filling(self) -> None:
        rows = [row("target_only", 7, {"d1": day(24)}), row("main", 7, {})]
        paired, blocked = pair_rows(rows)
        self.assertFalse(paired)
        self.assertEqual({item["reason"] for item in blocked}, {"no_paired_scored_days"})
        rows[1]["days"] = {"d1": day(24, "b")}
        paired, blocked = pair_rows(rows)
        self.assertFalse(paired)
        self.assertEqual({item["reason"] for item in blocked}, {"label_mismatch"})


if __name__ == "__main__":
    unittest.main()
