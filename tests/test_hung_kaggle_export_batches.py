"""Fixed CPU export routing, one-shot submission and failed-pilot gates."""

import copy
import hashlib
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools import hung_cloud_receiver as receiver
from tools import hung_kaggle_export_batches as exports
from tools import hung_kaggle_metric_queue as metrics
from tools import hung_kaggle_queue as queue


class ExportBatchTests(unittest.TestCase):
    def batches(self):
        readers = metrics.readers(queue.GROUPS, queue.EXPECTED_PROVIDER_PINS)
        partition = {
            "plan_sha256": exports.PLAN_SHA,
            "shards": [
                {"id": f"shard_{i:04d}", "job_ids": [f"fixture_{i}_{j}" for j in range(20)]}
                for i in range(1, 40)
            ],
        }
        return exports.fixed_batches(readers, partition)

    def run_fixture(self, root, status, *, exists=None, submitted=False, expected=None):
        batches = self.batches()[:1]
        submit, claim = Mock(), Mock()
        with (
            patch.object(exports, "Path", return_value=root / "relay"),
            patch.object(exports.time, "monotonic", side_effect=[0, 10801]),
        ):
            exports.run_exports(
                "# synthetic bundle",
                batches,
                expected or exports.digest(batches),
                0,
                0,
                submitted,
                submit=submit,
                status=status,
                claim_fn=claim,
                exists=exists or Mock(return_value=True),
                portable="pass",
                scorer="pass",
            )
        return submit, claim

    def test_seven_disjoint_cpu_batches_cover_only_560_kaggle_jobs(self):
        batches = self.batches()
        self.assertEqual(len(batches), 7)
        jobs = [j for b in batches for j in b["job_ids"]]
        self.assertEqual(len(jobs), len(set(jobs)))
        self.assertEqual(len(jobs), 560)
        ids = {int(r["shard_id"][6:]) for b in batches for r in b["records"]}
        self.assertFalse(ids & queue.LOCAL)
        self.assertEqual(batches[0]["records"][3]["reuse_export_sha256"], exports.REUSED_EXPORT)

    def test_missing_foreign_or_overlapping_route_fails(self):
        readers = metrics.readers(queue.GROUPS, queue.EXPECTED_PROVIDER_PINS)
        partition = {
            "plan_sha256": exports.PLAN_SHA,
            "shards": [
                {"id": f"shard_{i:04d}", "job_ids": [f"fixture_{i}_{j}" for j in range(20)]}
                for i in range(1, 40)
            ],
        }
        for problem in ("local", "missing", "overlap"):
            rows, spec = copy.deepcopy(readers), copy.deepcopy(partition)
            if problem == "local":
                rows[0]["shard_id"] = "shard_0004"
            elif problem == "missing":
                rows.pop()
            else:
                spec["shards"][1]["job_ids"][0] = spec["shards"][0]["job_ids"][0]
            with self.subTest(problem=problem), self.assertRaises(AssertionError):
                exports.fixed_batches(rows, spec)

    def test_private_cpu_request_has_exact_version1_mounts_and_no_gpu(self):
        request = exports.cpu_request("fixture", "pass", ["a", "b"], types.SimpleNamespace)
        self.assertFalse(request.enable_gpu)
        self.assertFalse(request.enable_internet)
        self.assertTrue(request.is_private)
        self.assertEqual(request.dataset_data_sources, [])
        self.assertEqual(request.kernel_data_sources, ["hungluongduc/a/1", "hungluongduc/b/1"])
        relay = exports.cpu_request("relay", "pass", [], types.SimpleNamespace)
        self.assertFalse(relay.enable_gpu)
        self.assertTrue(relay.enable_internet)
        for inputs in (["a", "a"], list("abcde")):
            with self.assertRaises(AssertionError):
                exports.cpu_request("bad", "pass", inputs, types.SimpleNamespace)

    def test_receiver_pin_and_all_generated_sources_compile(self):
        self.assertEqual(
            exports.RECEIVER_SHA, hashlib.sha256(Path(receiver.__file__).read_bytes()).hexdigest()
        )
        bundle = exports.source_bundle(
            Path(queue.__file__).read_text(encoding="utf-8"),
            Path(metrics.__file__).read_text(encoding="utf-8"),
            Path(exports.__file__).read_text(encoding="utf-8"),
            "pass",
            "pass",
        )
        namespace = {}
        exec(bundle, namespace)
        self.assertIs(namespace["run_exports"].__globals__["submit_cpu"], namespace["submit_cpu"])
        batches = self.batches()
        compile(
            exports.controller_source(bundle, batches, exports.digest(batches), 0, 0, False),
            "controller",
            "exec",
        )
        for batch in batches:
            source = exports.producer_source(batch, "pass", "pass")
            compile(source, "producer", "exec")
            self.assertIn("assert not torch.cuda.is_available()", source)
            self.assertIn("portable.export_receiver", source)
            self.assertIn(exports.RECEIVER_SHA, source)

    def test_changed_manifest_stops_before_provider_submission(self):
        with (
            tempfile.TemporaryDirectory(dir=".") as directory,
            self.assertRaisesRegex(AssertionError, "allocation"),
        ):
            self.run_fixture(Path(directory), Mock(), expected="0" * 64)

    def test_unknown_readers_never_get_status_or_batch_submission(self):
        status = Mock()
        with tempfile.TemporaryDirectory(dir=".") as directory:
            submit, _ = self.run_fixture(Path(directory), status, exists=Mock(return_value=False))
        status.assert_not_called()
        self.assertEqual(submit.call_count, 1)
        self.assertEqual(submit.call_args.args[2], [])  # CPU controller handoff only.

    def test_failed_receiver_blocks_all_batch_work(self):
        with (
            tempfile.TemporaryDirectory(dir=".") as directory,
            self.assertRaisesRegex(AssertionError, "Receiver failed"),
        ):
            self.run_fixture(Path(directory), Mock(return_value="ERROR"))

    def test_failed_export_blocks_later_batches(self):
        status = Mock(side_effect=["COMPLETE"] * 4 + ["ERROR"])
        with (
            tempfile.TemporaryDirectory(dir=".") as directory,
            self.assertRaisesRegex(AssertionError, "later exports blocked"),
        ):
            self.run_fixture(Path(directory), status)

    def test_waiting_submitted_export_is_not_submitted_again(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            submit, _ = self.run_fixture(
                Path(directory), Mock(return_value="RUNNING"), submitted=True
            )
        self.assertEqual(submit.call_count, 1)
        self.assertEqual(submit.call_args.args[2], [])
        self.assertIn("0,1,True", submit.call_args.args[1])

    def test_completed_export_writes_honest_cpu_receipt(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory)
            submit, _ = self.run_fixture(root, Mock(side_effect=["COMPLETE"] * 5))
            receipt = json.loads((root / "relay/batch_00.json").read_bytes())
            self.assertEqual(receipt["jobs"], 80)
            self.assertIn("readback/peer review pending", receipt["meaning"])
            self.assertTrue((root / "relay/complete.json").is_file())
        self.assertEqual(submit.call_count, 1)
        self.assertEqual(len(submit.call_args.args[2]), 4)


if __name__ == "__main__":
    unittest.main()
