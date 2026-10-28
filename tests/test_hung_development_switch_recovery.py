"""Failure gates for saved Development decision-trace recovery."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from tools.hung_development_audit import ROOT
from tools.hung_development_switch_recovery import decision_counts, local_trace


class SwitchRecoveryTests(unittest.TestCase):
    def test_local_trace_binds_receipt_and_manifest_hashes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            archive = Path(directory) / "artifacts.zip"
            job_id = "fixture_b7s7e1"
            manifest = {
                "run_id": "replay-90",
                "event_evidence": {"decisions": [{"current_level": 0.0, "selected_level": 0.1}]},
            }
            manifest_raw = json.dumps(manifest).encode()
            receipt_raw = json.dumps({"job_id": job_id}).encode()
            with ZipFile(archive, "x") as bundle:
                bundle.writestr(f"jobs/{job_id}/replay-90/run_manifest.json", manifest_raw)
                bundle.writestr(f"receipts/{job_id}/job.json", receipt_raw)
            manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
            receipt_sha = hashlib.sha256(receipt_raw).hexdigest()
            row = {
                "job_id": job_id,
                "archive_path": str(archive.relative_to(ROOT)),
                "archive_sha256": "a" * 64,
                "budget_days": "7",
                "entity_id": "1",
                "seed": "7",
                "job_receipt_path": f"receipts/{job_id}/job.json",
                "job_receipt_sha256": receipt_sha,
                "stage_manifest_sha256": f"replay-90:{manifest_sha}",
            }
            run = {
                "manifest": {"sha256": manifest_sha},
                "method": "main",
                "budget": 7,
                "entity_id": "1",
                "seed": 7,
            }
            result = local_trace(row, run)
            self.assertEqual((result["decisions"], result["switches"]), (1, 1))
            with self.assertRaisesRegex(ValueError, "Receipt SHA differs"):
                local_trace({**row, "job_receipt_sha256": "b" * 64}, run)
            with self.assertRaisesRegex(ValueError, "Merged manifest SHA differs"):
                local_trace(row, {**run, "manifest": {"sha256": "c" * 64}})

    def test_missing_decision_list_stays_null_and_invalid_levels_fail(self) -> None:
        self.assertEqual(
            decision_counts({"event_evidence": {"issued_count": 2}}, "fixed"), (None, None)
        )
        with self.assertRaisesRegex(ValueError, "Decision level absent"):
            decision_counts({"event_evidence": {"decisions": [{"current_level": 0.0}]}}, "invalid")


if __name__ == "__main__":
    unittest.main()
