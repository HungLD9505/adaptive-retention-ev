"""Offline regressions for the independent Development matrix cross-check."""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.hung_development_matrix_crosscheck_v1 import audit

ROOT = Path(__file__).resolve().parents[1]


def _write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class DevelopmentMatrixCrosscheckTests(unittest.TestCase):
    def setUp(self) -> None:
        cache = ROOT / ".cache"
        cache.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.directory.cleanup)
        base = Path(self.directory.name)
        self.matrix = base / "matrix.json"
        self.zero = base / "zero.csv"
        self.blocked = base / "blocked.csv"
        self.station = base / "station.csv"
        self.data = {
            "counts": {"runs": 2, "scorable_runs": 2, "zero_scored_runs": 0},
            "runs": [
                {
                    "job_id": method,
                    "budget": 7,
                    "entity_id": "1",
                    "seed": 7,
                    "method": method,
                    "metrics": {"mae_kwh": mae},
                    "coverage": {"scored": 1},
                }
                for method, mae in (("main", 3.0), ("target_only", 5.0))
            ],
            "paired_cells": [
                {
                    "budget": 7,
                    "entity_id": "1",
                    "seed": 7,
                    "method": "main",
                    "reference": "target_only",
                    "paired_days": 1,
                    "method_metrics": {"hours": 24, "mae_kwh": 3.0, "rmse_kwh": 4.0},
                    "reference_metrics": {"hours": 24, "mae_kwh": 5.0, "rmse_kwh": 6.0},
                }
            ],
            "blocked_pairs": [],
            "station_first": [
                {
                    "budget": 7,
                    "method": "main",
                    "reference": "target_only",
                    "stations": 1,
                    "minimum_seeds_per_station": 1,
                    "method_metrics": {"mae_kwh": 3.0, "rmse_kwh": 4.0},
                    "reference_metrics": {"mae_kwh": 5.0, "rmse_kwh": 6.0},
                    "absolute_mae_gain_kwh": 2.0,
                    "relative_mae_gain": 0.4,
                    "worse_than_reference_station_fraction": 0.0,
                }
            ],
        }
        _write_csv(self.zero, ["job_id"], [])
        _write_csv(
            self.blocked,
            ["budget_days", "entity_id", "seed", "method", "reference", "reason"],
            [],
        )
        _write_csv(
            self.station,
            [
                "budget",
                "method",
                "reference",
                "absolute_mae_gain_kwh",
                "relative_mae_gain",
                "method_metrics_mae_kwh",
                "reference_metrics_mae_kwh",
            ],
            [
                {
                    "budget": 7,
                    "method": "main",
                    "reference": "target_only",
                    "absolute_mae_gain_kwh": 2.0,
                    "relative_mae_gain": 0.4,
                    "method_metrics_mae_kwh": 3.0,
                    "reference_metrics_mae_kwh": 5.0,
                }
            ],
        )

    def check(self) -> dict:
        self.matrix.write_text(json.dumps(self.data), encoding="utf-8")
        digest = hashlib.sha256(self.matrix.read_bytes()).hexdigest()
        return audit(self.matrix, self.zero, self.blocked, self.station, digest)

    def test_valid_fixture(self) -> None:
        result = self.check()
        self.assertEqual(result["unique_runs"], 2)
        self.assertEqual(result["valid_pairs"], 1)

    def test_duplicate_run_id_rejected(self) -> None:
        self.data["runs"][1]["job_id"] = "main"
        with self.assertRaisesRegex(ValueError, "Duplicate run ID"):
            self.check()

    def test_changed_station_value_rejected(self) -> None:
        self.data["station_first"][0]["method_metrics"]["mae_kwh"] = 9.0
        with self.assertRaisesRegex(ValueError, "method_metrics MAE"):
            self.check()

    def test_invalid_pair_hours_rejected(self) -> None:
        self.data["paired_cells"][0]["method_metrics"]["hours"] = 23
        with self.assertRaisesRegex(ValueError, "Invalid paired day/hour count"):
            self.check()

    def test_matrix_hash_mismatch_rejected(self) -> None:
        self.matrix.write_text(json.dumps(self.data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Matrix SHA-256 mismatch"):
            audit(self.matrix, self.zero, self.blocked, self.station, "0" * 64)


if __name__ == "__main__":
    unittest.main()
