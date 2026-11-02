"""Offline regressions for importing corrected local shard proofs."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools import hung_import_compact_proof_ledger as frozen
from tools import hung_local_stageplan_ledger as ledger


class LocalStageplanLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        base, jobsets, allocation = frozen.read_base_and_jobsets()
        cls.base = {row["job_id"]: row for row in base}
        cls.expected = jobsets["shard_0014"][0]
        cls.allocation = allocation

    def setUp(self) -> None:
        ledger.CACHE.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="stageplan-ledger-test-", dir=ledger.CACHE)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def pin(self, path: Path) -> dict[str, str | int]:
        return {
            "path": path.relative_to(ledger.ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": ledger.file_sha256(path),
        }

    def fixture(self) -> dict:
        rows = []
        archive_path = self.directory / "artifacts.zip"
        with zipfile.ZipFile(archive_path, "x") as archive:
            for job_id in self.expected:
                base = self.base[job_id]
                job_receipt = f"receipts/{job_id}/job.json"
                stage_receipt = f"receipts/{job_id}/replay-42.json"
                stage_manifest = f"jobs/{job_id}/replay-42/run_manifest.json"
                stage_sha = hashlib.sha256(f"stage:{job_id}".encode()).hexdigest()
                job_receipt_bytes = json.dumps(
                    {
                        "schema": "hung-dispatch-job-receipt-v1",
                        "job_id": job_id,
                        "plan_sha256": "a" * 64,
                        "shards_sha256": "b" * 64,
                        "stages": {"replay-42": stage_sha},
                    }
                ).encode()
                archive.writestr(job_receipt, job_receipt_bytes)
                archive.writestr(stage_receipt, f"stage:{job_id}".encode())
                archive.writestr(stage_manifest, f"manifest:{job_id}".encode())
                rows.append(
                    {
                        **{
                            field: base[field]
                            for field in (
                                "job_id",
                                "shard_id",
                                "method",
                                "cell_id",
                                "budget_days",
                                "seed",
                                "entity_id",
                                "input_manifest_sha256",
                                "config_sha256",
                            )
                        },
                        "job_receipt_sha256": hashlib.sha256(job_receipt_bytes).hexdigest(),
                        "stage_receipt_sha256": {"replay-42": stage_sha},
                        "stage_manifest_sha256": {
                            "replay-42": hashlib.sha256(f"manifest:{job_id}".encode()).hexdigest()
                        },
                        "verified_member_count": 3,
                        "status": "VERIFIED_ARCHIVE_BYTES_AND_STAGE_PLAN",
                    }
                )
        archive_pin = self.pin(archive_path)
        receipt = {
            "shard_id": "shard_0014",
            "plan_sha256": "a" * 64,
            "shards_sha256": "b" * 64,
            "artifact_bytes": archive_pin["bytes"],
            "artifact_sha256": archive_pin["sha256"],
            "job_ids": self.expected,
            "crc": "passed",
            "exit_code": 0,
            "local_verify_exit_code": 0,
        }
        proof = {
            "schema": "hung-kaggle-compact-shard-proof-v2",
            "scope": "development_only",
            "shard_id": "shard_0014",
            "parent_plan_sha256": self.allocation["plan_sha256"],
            "parent_partition_sha256": self.allocation["partition_sha256"],
            "model_code_commit": self.allocation["canonical_code_sha"],
            "provider_plan_sha256": receipt["plan_sha256"],
            "provider_partition_sha256": receipt["shards_sha256"],
            "archive_bytes": archive_pin["bytes"],
            "archive_sha256": archive_pin["sha256"],
            "claimed_saved_version_id": 100,
            "claimed_readback_version_id": 200,
            "version_ids_independently_authenticated": False,
            "rows": rows,
        }
        proof_path = self.directory / "proof.json"
        receipt_path = self.directory / "receipt.json"
        proof_path.write_text(json.dumps(proof), encoding="utf-8")
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        return {
            "shard_id": "shard_0014",
            "proof": self.pin(proof_path),
            "receipt": self.pin(receipt_path),
            "archive": archive_pin,
        }

    def validate(self, entry: dict) -> dict[str, dict[str, str]]:
        return ledger.validate_shard(entry, self.expected, self.base, self.allocation, ledger.CACHE)

    def test_accepts_bound_archive_and_preserves_job_artifact_paths(self) -> None:
        entry = self.fixture()
        rows = self.validate(entry)
        self.assertEqual(set(rows), set(self.expected))
        self.assertTrue(all(row["status"] == ledger.STATUS for row in rows.values()))
        self.assertTrue(
            all(row["archive_path"] == entry["archive"]["path"] for row in rows.values())
        )

    def test_rejects_archive_corruption_before_proof_import(self) -> None:
        entry = self.fixture()
        archive_path = ledger.ROOT / entry["archive"]["path"]
        with archive_path.open("ab") as stream:
            stream.write(b"tamper")
        with self.assertRaisesRegex(frozen.ProofImportError, "archive bytes/SHA mismatch"):
            self.validate(entry)

    def test_rejects_empty_stage_proof_even_with_pinned_json(self) -> None:
        entry = self.fixture()
        proof_path = ledger.ROOT / entry["proof"]["path"]
        proof = json.loads(proof_path.read_text())
        proof["rows"][0]["stage_manifest_sha256"] = {}
        proof["rows"][0]["stage_receipt_sha256"] = {}
        proof_path.write_text(json.dumps(proof), encoding="utf-8")
        entry["proof"] = self.pin(proof_path)
        with self.assertRaisesRegex(frozen.ProofImportError, "Missing stage manifests"):
            self.validate(entry)

    def test_rejects_wrong_exact_job_order(self) -> None:
        entry = self.fixture()
        receipt_path = ledger.ROOT / entry["receipt"]["path"]
        receipt = json.loads(receipt_path.read_text())
        receipt["job_ids"] = list(reversed(receipt["job_ids"]))
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        entry["receipt"] = self.pin(receipt_path)
        with self.assertRaisesRegex(frozen.ProofImportError, "Receipt jobset/order"):
            self.validate(entry)


if __name__ == "__main__":
    unittest.main()
