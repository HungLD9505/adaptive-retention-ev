"""Synthetic missingness and label-support checks for bounded Final coverage."""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from tools.hung_final_coverage_symmetry_audit_v1 import (
    ARCHIVE_SHA,
    BUDGETS,
    LOCK_SHA,
    SOURCE_KERNEL,
    STATIONS,
    audit,
)


class CoverageSymmetryAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        cache = Path.cwd() / ".cache"
        cache.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.scores = root / "scores.json"
        self.receipt = root / "receipt.json"
        self.runs = root / "runs.csv"
        start = datetime.fromisoformat("2022-12-01T00:00:00+08:00")
        self.days = [(start + timedelta(days=i)).isoformat() for i in range(90)]
        self.jobs = []
        self.run_rows = []
        for station in STATIONS:
            for budget in BUDGETS:
                scored = {
                    day: {"label_sha256": "a" * 64}
                    for day in self.days
                    if station != "2118" or day != self.days[8]
                }
                for index in range(40):
                    job_id = f"{station}-{budget}-{index}"
                    job = {
                        "job_id": job_id,
                        "dataset_id": "urbanev",
                        "city_id": "SZH",
                        "entity_id": station,
                        "budget_days": budget,
                        "seed": index,
                        "variant": f"variant_{index}",
                        "method": "fixture",
                        "coverage": {
                            "requested": 90,
                            "created": 90,
                            "scored": len(scored),
                            "unscored_created": 90 - len(scored),
                            "skipped_all_missing_history": 0,
                            "skipped_undefined_scale": 0,
                        },
                        "metrics": {"hours": 24 * len(scored)},
                        "days": {
                            day: {"label_sha256": label["label_sha256"]}
                            for day, label in scored.items()
                        },
                    }
                    self.jobs.append(job)
                    self.run_rows.append(
                        {
                            "job_id": job_id,
                            "dataset_id": "urbanev",
                            "city_id": "SZH",
                            "entity_id": station,
                            "budget_days": budget,
                            "seed": index,
                            "variant": f"variant_{index}",
                            "method": "fixture",
                            "requested_origins": 90,
                            "issued_forecasts": 90,
                            "scored_days": len(scored),
                        }
                    )

    def _write(self) -> str:
        source = {
            "schema": "hung-final-remote-run-scores-v1",
            "source_kernel": SOURCE_KERNEL,
            "lock_sha256": LOCK_SHA,
            "archive_sha256": ARCHIVE_SHA,
            "jobs": self.jobs,
        }
        self.scores.write_text(json.dumps(source), encoding="utf-8", newline="\n")
        digest = hashlib.sha256(self.scores.read_bytes()).hexdigest()
        receipt = {
            "schema": "hung-final-remote-metrics-receipt-v1",
            "status": "FINAL_RUN_SCORES_RECOMPUTED_FROM_CHECKPOINTS",
            "source_kernel": SOURCE_KERNEL,
            "lock_sha256": LOCK_SHA,
            "archive_sha256": ARCHIVE_SHA,
            "output_sha256": digest,
            "output_bytes": self.scores.stat().st_size,
            "jobs": 360,
            "scored_jobs": 360,
            "null_jobs": 0,
        }
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8", newline="\n")
        with self.runs.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.run_rows[0].keys())
            writer.writeheader()
            writer.writerows(self.run_rows)
        return digest

    def test_symmetric_single_missing_day(self) -> None:
        result = audit(self.scores, self.receipt, self.runs, score_sha=self._write())
        self.assertEqual(result["jobs"], 360)
        self.assertEqual(result["unscored_origins"], 120)
        missing = [row for row in result["station_budget"] if row["entity_id"] == "2118"]
        self.assertEqual([row["unscored_origins"] for row in missing], [40, 40, 40])
        self.assertEqual(missing[0]["unscored_day_ids"], [self.days[8]])

    def test_method_specific_missing_day_is_rejected(self) -> None:
        job = self.jobs[0]
        job["days"].pop(self.days[9])
        job["coverage"]["scored"] -= 1
        job["coverage"]["unscored_created"] += 1
        job["metrics"]["hours"] -= 24
        self.run_rows[0]["scored_days"] -= 1
        with self.assertRaisesRegex(ValueError, "scored-day sets differ"):
            audit(self.scores, self.receipt, self.runs, score_sha=self._write())

    def test_method_specific_label_hash_is_rejected(self) -> None:
        self.jobs[0]["days"][self.days[0]]["label_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "labels differ"):
            audit(self.scores, self.receipt, self.runs, score_sha=self._write())


if __name__ == "__main__":
    unittest.main()
