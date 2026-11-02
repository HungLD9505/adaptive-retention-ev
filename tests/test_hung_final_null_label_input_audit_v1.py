"""Synthetic frozen-label audit fixtures for the common unscored Final day."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

from tools.hung_final_null_label_input_audit_v1 import BUDGETS, IDENTITY, ORIGIN, PREFIX, audit


class NullLabelInputAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        cache = Path.cwd() / ".cache"
        cache.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temporary.cleanup)
        self.archive = Path(self.temporary.name) / "input.zip"
        start = datetime.fromisoformat(ORIGIN)
        self.records = {}
        for budget in BUDGETS:
            valid = [index not in (11, 12, 13) for index in range(24)]
            self.records[budget] = {
                "identity": IDENTITY,
                "origin": ORIGIN,
                "clock_mode": "offset-aware-local",
                "timestamps": [(start + timedelta(hours=index)).isoformat() for index in range(24)],
                "energy_kwh": [float(index) if flag else None for index, flag in enumerate(valid)],
                "file_valid": valid,
            }

    def _write(self) -> str:
        with ZipFile(self.archive, "w") as archive:
            for budget, record in self.records.items():
                name = f"{PREFIX}/urbanev-SZH-{budget}d/labels.jsonl"
                archive.writestr(name, json.dumps(record, sort_keys=True) + "\n")
        return hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def test_three_identical_budget_records_identify_invalid_hours(self) -> None:
        result = audit(self.archive, expected_sha=self._write())
        self.assertEqual(len(result["budget_records"]), 3)
        for row in result["budget_records"]:
            self.assertEqual(row["valid_bins"], 21)
            self.assertEqual([item["index"] for item in row["invalid_bins"]], [11, 12, 13])

    def test_budget_label_divergence_is_rejected(self) -> None:
        self.records[28]["energy_kwh"][14] = 99.0
        with self.assertRaisesRegex(ValueError, "differ across history budgets"):
            audit(self.archive, expected_sha=self._write())

    def test_null_energy_with_valid_flag_is_rejected(self) -> None:
        self.records[7]["energy_kwh"][10] = None
        with self.assertRaisesRegex(ValueError, "invalid 24-hour label record"):
            audit(self.archive, expected_sha=self._write())


if __name__ == "__main__":
    unittest.main()
