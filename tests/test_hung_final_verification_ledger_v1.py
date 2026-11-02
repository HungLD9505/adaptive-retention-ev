"""Fail-closed checks for the published Hùng Final job ledger projection."""

from __future__ import annotations

import unittest

from tools.hung_final_verification_ledger_v1 import project_job


class FinalVerificationLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.job = {
            "job_id": "job_a",
            "dataset_id": "urbanev",
            "city_id": "SZH",
            "entity_id": "2118",
            "budget_days": 7,
            "seed": 7,
            "variant": "main",
            "method": "confidence",
            "input_manifest_sha256": "a" * 64,
            "source_checkpoint_sha256": "b" * 64,
            "target_checkpoint_sha256": None,
        }
        self.score = {
            "manifest_sha256": "c" * 64,
            "checkpoint_sha256": "d" * 64,
            "coverage": {"requested": 90, "created": 90, "scored": 89, "unscored_created": 1},
            "metrics": {"mae_kwh": 1.0, "rmse_kwh": 2.0},
        }
        self.stages = {
            "replay": {
                "manifest": "stages/job_a/replay/run_manifest.json",
                "artifacts": [
                    "stages/job_a/replay/run_manifest.json",
                    "stages/job_a/replay/runner_checkpoint.pt",
                ],
            }
        }

    def test_verified_row_distinguishes_remote_and_local_archive_bytes(self) -> None:
        row = project_job(self.job, self.score, self.stages, "f" * 40)
        self.assertEqual(row["remote_archive_bytes_sha_crc_verified"], "TRUE")
        self.assertEqual(row["local_archive_bytes_verified"], "FALSE")
        self.assertEqual(row["replay_checkpoint_sha256"], "d" * 64)
        self.assertEqual(row["metric_status"], "SCORED")

    def test_missing_checkpoint_or_stage_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing replay stage"):
            project_job(self.job, self.score, {}, "f" * 40)
        self.stages["replay"]["artifacts"].pop()
        with self.assertRaisesRegex(ValueError, "Missing or duplicate replay checkpoint"):
            project_job(self.job, self.score, self.stages, "f" * 40)


if __name__ == "__main__":
    unittest.main()
