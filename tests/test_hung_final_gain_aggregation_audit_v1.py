"""Independent fixtures for the bounded Final gain reporting audit."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from tools.hung_final_gain_aggregation_audit_v1 import audit

PAIR_FIELDS = (
    "dataset_id",
    "city_id",
    "entity_id",
    "budget_days",
    "seed",
    "variant",
    "reference",
    "paired_days",
    "method_mae_kwh",
    "reference_mae_kwh",
    "source_using",
)
STATION_FIELDS = (
    "dataset_id",
    "city_id",
    "budget_days",
    "variant",
    "reference",
    "method_mae_kwh",
    "reference_mae_kwh",
    "mae_gain_kwh",
    "transfer_gain",
    "negative_transfer_stations",
    "negative_transfer_denominator",
    "negative_transfer_rate",
    "paired_cells",
)


def _write(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class GainAggregationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        cache = Path.cwd() / ".cache"
        cache.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temporary.cleanup)
        self.paired = Path(self.temporary.name) / "paired.csv"
        self.station_first = Path(self.temporary.name) / "station_first.csv"
        paired_rows = []
        station_rows = []
        for budget in (7, 14, 28):
            for station, method, reference in (
                ("2118", 1.0, 2.0),
                ("2534", 3.0, 4.0),
                ("2579", 30.0, 60.0),
            ):
                for seed in (7, 11, 19):
                    paired_rows.append(
                        {
                            "dataset_id": "urbanev",
                            "city_id": "SZH",
                            "entity_id": station,
                            "budget_days": budget,
                            "seed": seed,
                            "variant": "main",
                            "reference": "target_only",
                            "paired_days": 89,
                            "method_mae_kwh": method,
                            "reference_mae_kwh": reference,
                            "source_using": "True",
                        }
                    )
            station_rows.append(
                {
                    "dataset_id": "urbanev",
                    "city_id": "SZH",
                    "budget_days": budget,
                    "variant": "main",
                    "reference": "target_only",
                    "method_mae_kwh": 34 / 3,
                    "reference_mae_kwh": 66 / 3,
                    "mae_gain_kwh": 32 / 3,
                    "transfer_gain": 32 / 66,
                    "negative_transfer_stations": 0,
                    "negative_transfer_denominator": 3,
                    "negative_transfer_rate": 0,
                    "paired_cells": 9,
                }
            )
        _write(self.paired, PAIR_FIELDS, paired_rows)
        _write(self.station_first, STATION_FIELDS, station_rows)

    def test_ratio_of_means_differs_from_mean_station_ratio(self) -> None:
        result = audit(self.paired, self.station_first)
        self.assertEqual(len(result["results"]), 3)
        for row in result["results"]:
            self.assertAlmostEqual(row["published_transfer_gain_ratio_of_means"], 32 / 66)
            self.assertAlmostEqual(row["mean_of_station_transfer_gains"], 5 / 12)
            self.assertEqual(row["negative_transfer_stations"], 0)

    def test_published_ratio_mismatch_is_rejected(self) -> None:
        with self.station_first.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        rows[0]["transfer_gain"] = "0.99"
        _write(self.station_first, STATION_FIELDS, rows)
        with self.assertRaisesRegex(ValueError, "transfer_gain"):
            audit(self.paired, self.station_first)

    def test_missing_physical_seed_is_rejected(self) -> None:
        with self.paired.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        rows.pop()
        _write(self.paired, PAIR_FIELDS, rows)
        with self.assertRaisesRegex(ValueError, "jobset mismatch"):
            audit(self.paired, self.station_first)


if __name__ == "__main__":
    unittest.main()
