"""Regression checks for the bounded-Final manuscript numeric audit."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.hung_report_numeric_audit_v1 import audit

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/hung-e2e-research-report-draft-20261029-v15.md"
PREVIOUS_REPORT = ROOT / "docs/reports/hung-e2e-research-report-draft-20261029-v14.md"
STATIONS = ROOT / "docs/reports/hung-final-analysis-20261029-v1/station_first.csv"
WAPE = ROOT / "docs/reports/hung-final-wape-20261029-v1/wape_summary.json"


class ReportNumericAuditTests(unittest.TestCase):
    def test_tracked_report_matches_published_tables(self) -> None:
        for report in (PREVIOUS_REPORT, REPORT):
            with self.subTest(report=report.name):
                result = audit(report, STATIONS, WAPE)
                self.assertEqual(result["checked_numeric_cells"], 90)
                self.assertEqual(result["schema"], "hung-report-numeric-audit-v1")

    def test_changed_main_gain_is_rejected(self) -> None:
        original = REPORT.read_text(encoding="utf-8")
        old = "5.540 [1.197, 11.227]"
        self.assertEqual(original.count(old), 1)
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "changed-report.md"
            changed.write_text(original.replace(old, "9.540 [1.197, 11.227]"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mae_gain_kwh"):
                audit(changed, STATIONS, WAPE)

    def test_duplicate_station_source_row_is_rejected(self) -> None:
        original = STATIONS.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "duplicate-station-first.csv"
            changed.write_text(original + original.splitlines()[1] + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate station-first"):
                audit(REPORT, changed, WAPE)


if __name__ == "__main__":
    unittest.main()
