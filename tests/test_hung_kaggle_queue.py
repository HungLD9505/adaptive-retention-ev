"""Offline safety cases for the bounded Kaggle queue; no network/GPU calls."""

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools import hung_kaggle_queue as queue


class KaggleQueueTests(unittest.TestCase):
    def fixture(self, root):
        folder = root / "shard_0002"
        folder.mkdir()
        jobs = [f"method_b14s7e{i}" for i in range(20)]
        jobhash = hashlib.sha256(
            json.dumps(sorted(jobs), separators=(",", ":")).encode()
        ).hexdigest()
        archive = folder / "artifacts.zip"
        with zipfile.ZipFile(archive, "x") as stream:
            stream.writestr(
                "dispatch_identity.json",
                json.dumps({"plan_sha256": queue.EXPECTED_PROVIDER_PINS["shard_0002"][0]}),
            )
            for job in jobs:
                stream.writestr(f"jobs/{job}/replay/dispatch_measurement.json", "{}")
        record = {
            "shard_id": "shard_0002",
            "exit_code": 0,
            "local_verify_exit_code": 0,
            "artifact_bytes": archive.stat().st_size,
            "artifact_sha256": queue.digest(archive),
            "plan_sha256": queue.EXPECTED_PROVIDER_PINS["shard_0002"][0],
            "shards_sha256": queue.EXPECTED_PROVIDER_PINS["shard_0002"][1],
            "job_ids": jobs,
        }
        receipt = folder / "receipt.json"
        receipt.write_text(json.dumps(record))
        return receipt, archive, jobhash

    def test_fixed_allocation(self):
        queue.validate_groups()
        self.assertEqual(sum(map(len, queue.GROUPS[1:])) * 20, 500)

    def test_complete_readback(self):
        with tempfile.TemporaryDirectory(dir=".") as temporary:
            root = Path(temporary)
            _, _, jobhash = self.fixture(root)
            with patch.dict(queue.EXPECTED_JOBSET_SHA, {"shard_0002": jobhash}):
                self.assertEqual(queue.verify_predecessor(root, (2,))[0]["crc"], "passed")

    def test_corrupt_bytes_stop(self):
        with tempfile.TemporaryDirectory(dir=".") as temporary:
            root = Path(temporary)
            _, archive, jobhash = self.fixture(root)
            archive.write_bytes(archive.read_bytes() + b"unexpected")
            with patch.dict(queue.EXPECTED_JOBSET_SHA, {"shard_0002": jobhash}):
                with self.assertRaises(AssertionError):
                    queue.verify_predecessor(root, (2,))

    def test_relabelled_job_and_nonzero_exit_stop(self):
        for mutation in ("job", "exit"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(dir=".") as temporary:
                root = Path(temporary)
                receipt, _, jobhash = self.fixture(root)
                record = json.loads(receipt.read_text())
                if mutation == "job":
                    record["job_ids"][0] = "unmatched"
                else:
                    record["local_verify_exit_code"] = 1
                receipt.write_text(json.dumps(record))
                with patch.dict(queue.EXPECTED_JOBSET_SHA, {"shard_0002": jobhash}):
                    with self.assertRaises(AssertionError):
                        queue.verify_predecessor(root, (2,))

    def test_missing_predecessor_stops(self):
        with tempfile.TemporaryDirectory(dir=".") as temporary:
            with self.assertRaises(AssertionError):
                queue.verify_predecessor(Path(temporary), (2,))

    def test_generated_sources_compile_and_bound_groups(self):
        module = Path(queue.__file__).read_text()
        notebook = json.loads(
            Path("experiments/hung_sprint2/kaggle_matched_group02.ipynb").read_text()
        )
        setup, parity = ("".join(notebook["cells"][i]["source"]) for i in (1, 3))
        for index in range(1, len(queue.GROUPS)):
            source = queue.gpu_source(module, setup, parity, index)
            compile(source, "gpu", "exec")
            self.assertIn(f"selected = {[f'shard_{n:04d}' for n in queue.GROUPS[index]]!r}", source)
        compile(
            queue.relay_source(module, setup, parity, 0, 0, submit_current=False), "cpu", "exec"
        )

    def test_claim_failure_never_submits(self):
        with tempfile.TemporaryDirectory(dir=".") as temporary:
            with (
                patch.object(queue, "Path", return_value=Path(temporary)),
                patch.object(queue, "claim", side_effect=RuntimeError("existing claim")),
                patch.object(queue, "submit") as submit,
            ):
                with self.assertRaises(RuntimeError):
                    queue.relay("module", "setup", "parity", 1, 0, submit_current=True)
                submit.assert_not_called()

    def test_failed_provider_never_advances(self):
        with tempfile.TemporaryDirectory(dir=".") as temporary:
            target = Path(temporary) / "evidence"
            with (
                patch.object(queue, "Path", return_value=target),
                patch.object(queue, "claim"),
                patch.object(queue, "status", return_value="ERROR"),
                patch.object(queue, "submit") as submit,
            ):
                with self.assertRaises(AssertionError):
                    queue.relay("module", "setup", "parity", 0, 0, submit_current=False)
                submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
