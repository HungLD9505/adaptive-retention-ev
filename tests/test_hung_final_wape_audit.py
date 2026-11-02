"""Offline regressions for exact Final WAPE receipt and job accounting."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.hung_final_wape_audit_v1 import audit

IDENTITY = {
    "archive_sha256": "a" * 64,
    "lock_sha256": "b" * 64,
    "source_kernel": "owner/final/1",
}


class FinalWapeAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        jobs = []
        wape_jobs = []
        for index in range(360):
            job_id = f"job-{index:03d}"
            jobs.append(
                {
                    "job_id": job_id,
                    "dataset_id": "urbanev",
                    "city_id": "SZH",
                    "entity_id": str(index % 3),
                    "budget_days": 7,
                    "seed": index // 3,
                    "variant": "main",
                    "coverage": {"scored": 1},
                    "days": {"d1": {"absolute": 24.0}},
                    "metrics": {"mae_kwh": 1.0},
                }
            )
            wape_jobs.append(
                {
                    "job_id": job_id,
                    "scored_days": 1,
                    "absolute_error_kwh": 24.0,
                    "label_total_kwh": 48.0,
                    "wape": 0.5,
                }
            )
        self.scores = {**IDENTITY, "jobs": jobs}
        self.wape = {**IDENTITY, "jobs": wape_jobs}
        self.ledger = {**IDENTITY, "jobs": {item["job_id"]: {} for item in jobs}}
        self.receipt = {
            **IDENTITY,
            "jobs": 360,
            "undefined_jobs": 0,
            "status": "FINAL_WAPE_DENOMINATORS_READ_FROM_CHECKPOINTS",
        }
        self.paths = [
            self.root / name for name in ("scores.json", "wape.json", "receipt.json", "ledger.json")
        ]

    def write_inputs(self) -> None:
        scores_path, wape_path, receipt_path, ledger_path = self.paths
        scores_path.write_text(json.dumps(self.scores), encoding="utf-8")
        raw_wape = json.dumps(self.wape).encode("utf-8")
        wape_path.write_bytes(raw_wape)
        self.receipt["output_bytes"] = len(raw_wape)
        self.receipt["output_sha256"] = hashlib.sha256(raw_wape).hexdigest()
        receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        ledger_path.write_text(json.dumps(self.ledger), encoding="utf-8")

    def test_valid_exact_jobset_and_station_first_wape(self) -> None:
        self.write_inputs()
        runs, stations, summary = audit(*self.paths)
        self.assertEqual((len(runs), len(stations), summary["jobs"]), (360, 3, 360))
        self.assertEqual(summary["station_first"][0]["equal_station_wape"], 0.5)

    def test_duplicate_job_rejected_even_with_consistent_receipt_hash(self) -> None:
        self.wape["jobs"].append(dict(self.wape["jobs"][0]))
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "count or uniqueness"):
            audit(*self.paths)

    def test_zero_denominator_rejected_even_with_consistent_receipt_hash(self) -> None:
        self.wape["jobs"][0]["label_total_kwh"] = 0.0
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "denominator invalid"):
            audit(*self.paths)

    def test_changed_numerator_rejected_even_with_consistent_receipt_hash(self) -> None:
        self.wape["jobs"][0]["absolute_error_kwh"] = 25.0
        self.wape["jobs"][0]["wape"] = 25.0 / 48.0
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, "numerator differs"):
            audit(*self.paths)


if __name__ == "__main__":
    unittest.main()
