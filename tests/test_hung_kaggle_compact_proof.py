"""Offline regressions for the compact saved-shard verifier."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools import hung_kaggle_compact_proof as proof


def encoded(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class CompactProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, *, expected_job: str = "job_a", manifest_status: str = "completed") -> tuple:
        cell = {
            "id": "cell",
            "budget": 7,
            "seed": 11,
            "entity_id": "1405",
            "input_manifest_sha256": "a" * 64,
        }
        jobs = [
            {
                "id": jid,
                "cell": "cell",
                "config": "main",
                "method": "target_only",
                "source": None,
                "target": None,
            }
            for jid in ("job_a", "job_b")
        ]
        plan = {
            "code_commit": proof.MODEL_CODE,
            "scope": "development_only",
            "jobs": jobs,
            "cells": [cell],
            "configs": [{"id": "main", "sha256": "b" * 64}],
        }
        plan_bytes = encoded(plan)
        partition = {
            "plan_sha256": digest(plan_bytes),
            "shards": [{"id": "shard_test", "job_ids": [expected_job]}],
        }
        partition_bytes = encoded(partition)
        plan_path, partition_path = self.root / "plan.json", self.root / "shards.json"
        plan_path.write_bytes(plan_bytes)
        partition_path.write_bytes(partition_bytes)

        manifest = {
            "status": manifest_status,
            "code": {"commit": proof.MODEL_CODE},
            "input_binding": {
                "entity_id": "1405",
                "history_days": 7,
                "input_manifest_sha256": "a" * 64,
            },
        }
        manifest_bytes, log_bytes = encoded(manifest), b"small log\n"
        stage = {
            "binding": {
                "job": jobs[0],
                "stage": "replay-42",
                "input_manifest_sha256": "a" * 64,
                "config_sha256": "b" * 64,
            },
            "files": {
                "run_manifest.json": {
                    "bytes": len(manifest_bytes),
                    "sha256": digest(manifest_bytes),
                }
            },
            "log": {"bytes": len(log_bytes), "sha256": digest(log_bytes)},
        }
        stage_bytes = encoded(stage)
        receipt = {
            "job_id": "job_a",
            "plan_sha256": digest(plan_bytes),
            "shards_sha256": digest(partition_bytes),
            "stages": {"replay-42": digest(stage_bytes)},
        }
        archive_path = self.root / "artifacts.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("receipts/job_a/job.json", encoded(receipt))
            archive.writestr("receipts/job_a/replay-42.json", stage_bytes)
            archive.writestr("jobs/job_a/replay-42/run_manifest.json", manifest_bytes)
            archive.writestr("logs/job_a/replay-42.log", log_bytes)
        return (
            plan_path,
            partition_path,
            plan_path,
            partition_path,
            archive_path,
            "shard_test",
            proof.file_sha256(archive_path),
            archive_path.stat().st_size,
            1,
            2,
        )

    def run_fixture(self, args: tuple) -> dict:
        with (
            patch.object(proof, "PARENT_PLAN_SHA", proof.file_sha256(args[0])),
            patch.object(proof, "PARENT_PARTITION_SHA", proof.file_sha256(args[1])),
        ):
            return proof.verify_shard(*args)

    def test_accepts_matching_archive_and_manifest(self) -> None:
        result = self.run_fixture(self.fixture())
        self.assertEqual([row["job_id"] for row in result["rows"]], ["job_a"])
        self.assertEqual(result["rows"][0]["status"], "VERIFIED_ARCHIVE_BYTES")
        self.assertFalse(result["version_ids_independently_authenticated"])

    def test_rejects_wrong_archive_sha(self) -> None:
        args = self.fixture()
        with self.assertRaisesRegex(ValueError, "Archive SHA mismatch"):
            self.run_fixture(args[:6] + ("0" * 64,) + args[7:])

    def test_rejects_foreign_receipt_jobset(self) -> None:
        with self.assertRaisesRegex(ValueError, "Archived receipt jobset mismatch"):
            self.run_fixture(self.fixture(expected_job="job_b"))

    def test_rejects_failed_manifest_even_with_matching_receipt_sha(self) -> None:
        with self.assertRaisesRegex(ValueError, "Run manifest identity mismatch"):
            self.run_fixture(self.fixture(manifest_status="failed"))


if __name__ == "__main__":
    unittest.main()
