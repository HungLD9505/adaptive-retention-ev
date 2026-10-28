"""Offline regressions for binding saved compact proofs to the frozen ledger."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import hung_import_compact_proof_ledger as importer


class CompactLedgerImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base, cls.jobsets, cls.allocation = importer.read_base_and_jobsets()
        cls.by_id = {row["job_id"]: row for row in cls.base}

    def setUp(self) -> None:
        test_cache = importer.ROOT / ".cache"
        test_cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="ledger-import-test-", dir=test_cache)
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)

    def test_tracked_text_hash_accepts_crlf_and_rejects_bare_cr(self) -> None:
        git_blob = b"header,field\nfirst,value\n"
        expected = importer.sha256_bytes(git_blob)
        self.assertEqual(importer.git_lf_sha256(git_blob, "fixture"), expected)
        self.assertEqual(
            importer.git_lf_sha256(git_blob.replace(b"\n", b"\r\n"), "fixture"), expected
        )
        with self.assertRaisesRegex(importer.ProofImportError, "Bare carriage return"):
            importer.git_lf_sha256(b"header,field\rfirst,value\n", "fixture")

    def save(self, name: str, value: dict) -> tuple[str, int, str]:
        path = self.cache / name
        raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
        path.write_bytes(raw)
        return str(path), len(raw), importer.sha256_bytes(raw)

    def proof(self, shard_id: str) -> tuple[dict, dict]:
        ids, jobset_sha = self.jobsets[shard_id]
        rows = []
        for jid in ids:
            source = self.by_id[jid]
            rows.append(
                {
                    **{
                        field: source[field]
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
                    "job_receipt_sha256": "a" * 64,
                    "stage_manifest_sha256": {"replay-42": "b" * 64},
                    "stage_receipt_sha256": {"replay-42": "c" * 64},
                    "verified_member_count": 5,
                    "status": "VERIFIED_ARCHIVE_BYTES",
                }
            )
        proof = {
            "schema": "hung-kaggle-compact-shard-proof-v1",
            "scope": "development_only",
            "parent_plan_sha256": self.allocation["plan_sha256"],
            "parent_partition_sha256": self.allocation["partition_sha256"],
            "provider_plan_sha256": "d" * 64,
            "provider_partition_sha256": "e" * 64,
            "model_code_commit": self.allocation["canonical_code_sha"],
            "verifier_sha256": importer.VERIFIER_SHA256,
            "shard_id": shard_id,
            "archive_sha256": "f" * 64,
            "archive_bytes": 12345,
            "claimed_saved_version_id": 100,
            "claimed_readback_version_id": 101,
            "version_ids_independently_authenticated": False,
            "rows": rows,
        }
        path, size, digest = self.save(f"{shard_id}-proof.json", proof)
        entry = {
            "shard_id": shard_id,
            "provider_plan_sha256": proof["provider_plan_sha256"],
            "provider_partition_sha256": proof["provider_partition_sha256"],
            "archive_sha256": proof["archive_sha256"],
            "archive_bytes": proof["archive_bytes"],
            "archive_carrier_version_id": 100,
            "archive_readback_version_id": 101,
            "proof_version_id": 102,
            "proof_readback_version_id": 103,
            "proof_source_notebook": "fixture/proof",
            "proof_path": path,
            "proof_bytes": size,
            "proof_sha256": digest,
        }
        return entry, {
            "shard_id": shard_id,
            "proof_bytes": size,
            "proof_sha256": digest,
            "jobset_sha256": jobset_sha,
            "job_ids": ids,
            "jobs": 20,
            "status": "REMOTE_PROOF_READBACK_VERIFIED",
        }

    def entries(self, *shards: str) -> list[dict]:
        pairs = [self.proof(shard) for shard in shards]
        if len(pairs) == 1:
            readback = {
                "schema": "hung-kaggle-compact-proof-readback-v1",
                "scope": "development_only",
                "source_notebook": "fixture/proof",
                "claimed_source_version_id": 102,
                **pairs[0][1],
            }
        else:
            readback = {
                "schema": "hung-kaggle-compact-proof-group-readback-v1",
                "scope": "development_only",
                "source_notebook": "fixture/proof",
                "claimed_source_version_id": 102,
                "readbacks": [pair[1] for pair in pairs],
                "jobs": 20 * len(pairs),
                "status": "REMOTE_PROOF_READBACK_VERIFIED",
            }
        path, size, digest = self.save("readback.json", readback)
        for entry, _ in pairs:
            entry.update(
                {
                    "proof_readback_path": path,
                    "proof_readback_bytes": size,
                    "proof_readback_sha256": digest,
                }
            )
        return [entry for entry, _ in pairs]

    def merge(self, entries: list[dict]) -> list[dict[str, str]]:
        return importer.merge_rows(self.base, entries, self.jobsets, self.allocation, self.cache)

    def test_valid_single_shard_preserves_pending_and_local(self) -> None:
        rows = self.merge(self.entries("shard_0001"))
        self.assertEqual(len(rows), 782)
        self.assertEqual(sum(row["status"] == importer.REMOTE_STATUS for row in rows), 20)
        self.assertEqual(sum(row["status"] == "MISSING_REVIEWABLE_ARCHIVE" for row in rows), 540)
        self.assertEqual(sum(row["status"] == "VERIFIED_LOCAL_BYTES" for row in rows), 222)
        self.assertTrue(
            all(row["proof_sha256"] for row in rows if row["status"] == importer.REMOTE_STATUS)
        )
        self.assertTrue(
            all(not row["proof_sha256"] for row in rows if row["status"] != importer.REMOTE_STATUS)
        )

    def test_valid_two_shard_group_requires_both(self) -> None:
        entries = self.entries("shard_0002", "shard_0003")
        with self.assertRaisesRegex(importer.ProofImportError, "Incomplete group"):
            self.merge(entries[:1])
        rows = self.merge(entries)
        self.assertEqual(sum(row["status"] == importer.REMOTE_STATUS for row in rows), 40)

    def test_rejects_missing_or_modified_readback(self) -> None:
        entries = self.entries("shard_0001")
        Path(entries[0]["proof_readback_path"]).write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(importer.ProofImportError, "Readback bytes/SHA mismatch"):
            self.merge(entries)
        Path(entries[0]["proof_readback_path"]).unlink()
        with self.assertRaisesRegex(importer.ProofImportError, "Missing readback"):
            self.merge(entries)

    def test_rejects_wrong_jobset_even_if_proof_hash_is_rebound(self) -> None:
        entries = self.entries("shard_0001")
        path = Path(entries[0]["proof_path"])
        proof = json.loads(path.read_text(encoding="utf-8"))
        proof["rows"][0], proof["rows"][1] = proof["rows"][1], proof["rows"][0]
        _, size, digest = self.save(path.name, proof)
        entries[0].update({"proof_bytes": size, "proof_sha256": digest})
        readback_path = Path(entries[0]["proof_readback_path"])
        readback = json.loads(readback_path.read_text(encoding="utf-8"))
        readback["proof_bytes"] = size
        readback["proof_sha256"] = digest
        readback["job_ids"] = [row["job_id"] for row in proof["rows"]]
        readback["jobset_sha256"] = importer.ordered_jobset_sha(readback["job_ids"])
        _, size, digest = self.save(readback_path.name, readback)
        entries[0].update({"proof_readback_bytes": size, "proof_readback_sha256": digest})
        with self.assertRaisesRegex(importer.ProofImportError, "Readback jobset_sha256 mismatch"):
            self.merge(entries)

    def test_rejects_cross_shard_provenance_and_duplicate(self) -> None:
        entries = self.entries("shard_0002", "shard_0003")
        entries[1]["provider_partition_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            importer.ProofImportError, "provider_partition_sha256 mismatch"
        ):
            self.merge(entries)
        with self.assertRaisesRegex(importer.ProofImportError, "Duplicate proof shard"):
            self.merge([entries[0], entries[0]])

    def test_create_only_writer_preserves_existing_snapshot(self) -> None:
        rows = self.merge(self.entries("shard_0001"))
        output = self.cache / "ledger.csv"
        digest = importer.write_ledger(output, rows)
        self.assertEqual(digest, importer.sha256_bytes(output.read_bytes()))
        with self.assertRaises(FileExistsError):
            importer.write_ledger(output, rows)


if __name__ == "__main__":
    unittest.main()
