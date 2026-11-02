"""Corrupt, missing and duplicate log chunks cannot produce a verified readback."""

import base64
import hashlib
import json
import tempfile
import unittest
import zlib
from pathlib import Path

from tools import hung_ingest_export as ingest
from tools.hung_kaggle_export_batches import digest
from tools.hung_portable_results import PLAN_SHA, SCORER_SHA
from tools.hung_results import file_sha


class IngestTests(unittest.TestCase):
    def fixture(self, root, *, wrong_jobs=False):
        rows = [
            {
                "job_id": f"fixture_{i}",
                "method": "target_only",
                "budget": 7,
                "seed": 7,
                "entity_id": str(i),
                "status": "DISPATCH_VERIFIED",
                "input_manifest_sha256": "a" * 64,
                "source_sha256": None,
                "target_sha256": "b" * 64,
                "days": {},
                "metrics": None,
                "coverage": {"requested": 90, "created": 1, "scored": 0},
            }
            for i in range(80)
        ]
        batch = {"id": "batch_00", "job_ids": [r["job_id"] for r in rows]}
        value = {
            "schema": "hung-portable-daily-errors-v1",
            "scope": "development_only",
            "canonical_plan_sha256": PLAN_SHA,
            "scorer_sha256": SCORER_SHA,
            "provenance": {"batch_sha256": digest(batch)},
            "records": rows,
        }
        if wrong_jobs:
            value["records"][0]["job_id"] = "foreign"
        body = json.dumps(value, sort_keys=True).encode()
        encoded = base64.b64encode(zlib.compress(body)).decode()
        chunks = [encoded[i : i + 600] for i in range(0, len(encoded), 600)]
        summary = {
            "scope": "development_only",
            "batch": "batch_00",
            "batch_sha256": digest(batch),
            "executed": False,
            "gpu": False,
            "bytes": len(body),
            "chunks": len(chunks),
            "sha256": hashlib.sha256(body).hexdigest(),
            "counts": {"runs": 80, "scorable_runs": 0, "zero_scored_runs": 80},
        }
        records = [{"portable_export": summary}] + [
            {"portable_chunk": i, "data": data} for i, data in enumerate(chunks)
        ]
        lines = [f"1.0s\t{i}\t{json.dumps(r)}" for i, r in enumerate(records)]
        log = root / "log.txt"
        log.write_text("\n".join(lines), encoding="utf-8")
        manifest = {
            "schema": "hung-kaggle-export-batches-v1",
            "scope": "development_only",
            "canonical_plan_sha256": PLAN_SHA,
            "batches": [batch],
            "allocation_sha256": digest([batch]),
        }
        path = root / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return log, path, lines, body

    def run_ingest(self, log, manifest, root):
        return ingest.ingest(
            {"path": str(log), "sha256": file_sha(log)},
            {"path": str(manifest), "sha256": file_sha(manifest)},
            "batch_00",
            root / "readback",
            root,
        )

    def test_native_ax_duplicates_and_dom_logs_decode_same_bytes(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            log, _, lines, body = self.fixture(Path(directory).resolve())
            original = ingest.decode_log(log.read_text(encoding="utf-8"))[1]
            native = "\n".join("  text " + line for line in lines + lines)
            self.assertEqual(ingest.decode_log(native)[1], original)
            self.assertEqual(original, body)

    def test_missing_or_conflicting_chunks_fail(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            _, _, lines, _ = self.fixture(Path(directory).resolve())
            with self.assertRaisesRegex(ValueError, "chunks"):
                ingest.decode_log("\n".join(lines[:-1]))
            changed = json.loads(lines[1][lines[1].index('{"portable_') :])
            changed["data"] = "AAAA"
            with self.assertRaisesRegex(ValueError, "duplicate"):
                ingest.decode_log("\n".join(lines + [json.dumps(changed)]))

    def test_summary_hash_size_or_scope_change_fail(self):
        for damage in ("sha256", "bytes", "gpu"):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory(dir=".") as directory:
                root = Path(directory).resolve()
                log, manifest, lines, _ = self.fixture(root)
                first = json.loads(lines[0][lines[0].index('{"portable_') :])
                first["portable_export"][damage] = (
                    "0" * 64 if damage == "sha256" else 1 if damage == "bytes" else True
                )
                lines[0] = json.dumps(first)
                log.write_text("\n".join(lines), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.run_ingest(log, manifest, root)
                self.assertFalse((root / "readback/receipt.json").exists())

    def test_exact_batch_receipt_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            log, manifest, _, _ = self.fixture(root)
            receipt = self.run_ingest(log, manifest, root)
            self.assertTrue(receipt["passed"])
            self.assertEqual(receipt["counts"]["zero_scored_runs"], 80)
            for pin in receipt["files"]:
                self.assertEqual(file_sha(Path(pin["path"])), pin["sha256"])
            before = (root / "readback/receipt.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "Output exists"):
                self.run_ingest(log, manifest, root)
            self.assertEqual((root / "readback/receipt.json").read_bytes(), before)

    def test_wrong_jobs_leave_partial_evidence_without_receipt(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            log, manifest, _, _ = self.fixture(root, wrong_jobs=True)
            with self.assertRaisesRegex(ValueError, "Jobs differ"):
                self.run_ingest(log, manifest, root)
            self.assertTrue((root / "readback/portable-batch.json").exists())
            self.assertFalse((root / "readback/receipt.json").exists())
            with self.assertRaisesRegex(ValueError, "Output exists"):
                self.run_ingest(log, manifest, root)

    def test_changed_allocation_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            log, manifest, _, _ = self.fixture(root)
            value = json.loads(manifest.read_bytes())
            value["batches"][0]["job_ids"][0] = "different"
            manifest.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Allocation"):
                self.run_ingest(log, manifest, root)
            self.assertFalse((root / "readback").exists())


if __name__ == "__main__":
    unittest.main()
