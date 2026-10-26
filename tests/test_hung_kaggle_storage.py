"""Offline barriers: upload alone must never mark a shard VERIFIED."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools import hung_kaggle_storage as storage


class StorageTests(unittest.TestCase):
    def fixture(self, directory):
        path = Path(directory) / "artifacts.zip"
        path.write_bytes(b"synthetic test bytes; no training result")
        record = {
            "exit_code": 0,
            "local_verify_exit_code": 0,
            "shard_id": "shard_0008",
            "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "artifact_bytes": path.stat().st_size,
        }
        return path, record

    def test_independent_completion_required(self):
        for state in ("COMPLETE", "ERROR"):
            with self.subTest(state=state), tempfile.TemporaryDirectory(dir=".") as directory:
                path, record = self.fixture(directory)
                submitted = Mock(return_value={"version": 1, "url": "test-only"})
                with patch.object(storage, "upload_private") as upload:
                    if state == "ERROR":
                        with self.assertRaises(AssertionError):
                            storage.persist_shard(
                                record,
                                path,
                                "",
                                owner="test",
                                submit=submitted,
                                status=Mock(return_value=state),
                            )
                        self.assertFalse((path.parent / "durability.json").exists())
                    else:
                        proof = storage.persist_shard(
                            record,
                            path,
                            "",
                            owner="test",
                            submit=submitted,
                            status=Mock(return_value=state),
                        )
                        self.assertEqual(proof["status"], "VERIFIED")
                        self.assertEqual(
                            (path.parent / "publish/artifacts.zip.bin").read_bytes(),
                            path.read_bytes(),
                        )
                        self.assertFalse(submitted.call_args.kwargs["gpu"])
                        self.assertTrue(submitted.call_args.kwargs["datasets"][0].endswith("/1"))
                    upload.assert_called_once()

    def test_corrupt_output_never_uploads(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            path, record = self.fixture(directory)
            path.write_bytes(b"corrupt")
            with patch.object(storage, "upload_private") as upload:
                with self.assertRaises(AssertionError):
                    storage.persist_shard(
                        record, path, "", owner="test", submit=Mock(), status=Mock()
                    )
                upload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
