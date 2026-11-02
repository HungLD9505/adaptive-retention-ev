"""CPU reporter receipt barriers; no training, network or historical evidence."""

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools import hung_result_worker as worker


class ResultWorkerTests(unittest.TestCase):
    def fixture(self, root):
        folder = root / "shard_0031"
        folder.mkdir()
        archive = folder / "artifacts.zip"
        with zipfile.ZipFile(archive, "x") as stream:
            stream.writestr("synthetic-only.json", "{}")
        shard = {"id": "shard_0031", "job_ids": ["synthetic-a", "synthetic-b"]}
        receipt = {
            "shard_id": shard["id"],
            "job_ids": shard["job_ids"],
            "plan_sha256": "synthetic-plan",
            "partition_sha256": "synthetic-partition",
            "artifact_sha256": worker.file_sha(archive),
            "artifact_bytes": archive.stat().st_size,
            "crc": "passed",
        }
        for name, data in (
            ("receipt.json", receipt),
            ("execute-exit.json", {"exit_code": 0}),
            ("verify-exit.json", {"exit_code": 0}),
        ):
            (folder / name).write_text(json.dumps(data), encoding="utf-8")
        return folder, shard, receipt

    def read(self, folder, shard, root):
        return worker.completed_shard(folder, shard, "synthetic-plan", "synthetic-partition", root)

    def test_complete_receipt_is_authenticated(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory)
            folder, shard, _ = self.fixture(root)
            before = (folder / "artifacts.zip").read_bytes()
            proof = self.read(folder, shard, root)
            self.assertEqual(proof["id"], shard["id"])
            self.assertEqual((folder / "artifacts.zip").read_bytes(), before)

    def test_missing_receipt_is_pending_even_after_execution(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory)
            folder, shard, _ = self.fixture(root)
            # Synthetic fixture only; no production artifact is removed.
            (folder / "receipt.json").unlink()
            self.assertIsNone(self.read(folder, shard, root))

    def test_missing_or_failed_terminal_stops(self):
        for name in ("execute-exit.json", "verify-exit.json"):
            for action in ("missing", "nonzero"):
                with self.subTest(name=name, action=action):
                    with tempfile.TemporaryDirectory(dir=".") as directory:
                        root = Path(directory)
                        folder, shard, _ = self.fixture(root)
                        if action == "missing":
                            (folder / name).unlink()
                        else:
                            (folder / name).write_text('{"exit_code":1}', encoding="utf-8")
                        with self.assertRaises(ValueError):
                            self.read(folder, shard, root)

    def test_foreign_plan_and_jobs_stop(self):
        for field in ("job_ids", "plan_sha256", "partition_sha256"):
            with self.subTest(field=field), tempfile.TemporaryDirectory(dir=".") as directory:
                root = Path(directory)
                folder, shard, receipt = self.fixture(root)
                receipt[field] = ["foreign"] if field == "job_ids" else "foreign"
                (folder / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.read(folder, shard, root)

    def test_corrupt_archive_stops(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory)
            folder, shard, _ = self.fixture(root)
            (folder / "artifacts.zip").write_bytes(b"corrupt fixture")
            with self.assertRaises(ValueError):
                self.read(folder, shard, root)

    def test_snapshot_readback_and_corruption(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            folder = root / "snapshot"
            folder.mkdir()
            result = folder / "results.json"
            result.write_text("{}", encoding="utf-8")
            receipt = {"inputs": [], "files": [worker.pin(result, root)]}
            (folder / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            self.assertEqual(worker.verify_snapshot(folder, [], root), receipt)
            result.write_text('{"forged":true}', encoding="utf-8")
            with self.assertRaises(ValueError):
                worker.verify_snapshot(folder, [], root)

    def test_partial_snapshot_and_extra_files_stop(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            with self.assertRaises(ValueError):
                worker.verify_snapshot(root, [], root)
            (root / "receipt.json").write_text('{"inputs":[],"files":[]}', encoding="utf-8")
            (root / "unexpected.txt").write_text("fixture", encoding="utf-8")
            with self.assertRaises(ValueError):
                worker.verify_snapshot(root, [], root)


if __name__ == "__main__":
    unittest.main()
