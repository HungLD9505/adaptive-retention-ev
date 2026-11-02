"""CPU-only reader routing, failure and handoff safety; no provider calls."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools import hung_kaggle_metric_queue as metrics
from tools import hung_kaggle_queue as queue


class MetricQueueTests(unittest.TestCase):
    def records(self):
        return metrics.readers(queue.GROUPS, queue.EXPECTED_PROVIDER_PINS)

    def run_fixture(self, root, status, *, submitted=False, exists=None, clock=(0, 10801)):
        submit = Mock()
        record = self.records()[0]
        with (
            patch.object(metrics, "Path", return_value=root / "relay"),
            patch.object(metrics.time, "monotonic", side_effect=clock),
        ):
            metrics.run_queue(
                "# synthetic metadata only",
                [record],
                0,
                0,
                submitted,
                submit=submit,
                status=status,
                claim=Mock(),
                exists=exists or Mock(return_value=True),
                receiver="pass",
                scorer="pass",
            )
        return submit

    def test_fixed_kaggle_only_assignment_reuses_trial(self):
        records = self.records()
        ids = [int(r["shard_id"][6:]) for r in records]
        self.assertEqual(len(ids), 27)
        self.assertEqual(len(set(ids)), 27)
        self.assertNotIn(8, ids)
        self.assertFalse(set(ids) & queue.LOCAL)
        self.assertEqual(
            next(r for r in records if r["shard_id"] == "shard_0009")["training"],
            "hung-matched-group03-recovery-20261027-v2",
        )

    def test_future_import_boundaries_and_runtime_namespace(self):
        module = Path(queue.__file__).read_text(encoding="utf-8")
        metric_source = Path(metrics.__file__).read_text(encoding="utf-8")
        bundle = metrics.bundle_sources(module, metric_source, "pass", "pass")
        scope = {}
        exec(bundle, scope)
        self.assertIs(scope["run_queue"].__globals__["receiver_source"], scope["receiver_source"])
        source = metrics.relay_source(bundle, self.records(), 0, 0, False)
        compile(source, "relay", "exec")
        for record in self.records():
            compile(metrics.receiver_source(record, "pass", "pass"), "child", "exec")

    def test_failed_trial_stops_before_submission(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            with self.assertRaises(AssertionError):
                self.run_fixture(Path(directory), Mock(return_value="ERROR"))

    def test_failed_training_stops_before_receiver(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            with self.assertRaises(AssertionError):
                self.run_fixture(Path(directory), Mock(side_effect=["COMPLETE", "ERROR"]))

    def test_unobserved_group_never_gets_status_or_reader_submission(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            status = Mock(return_value="COMPLETE")
            submitted = self.run_fixture(Path(directory), status, exists=Mock(return_value=False))
            status.assert_called_once_with(metrics.TRIAL)
            self.assertEqual(submitted.call_count, 1)
            self.assertIn("coordinator", submitted.call_args.args[0])
            self.assertFalse(submitted.call_args.kwargs["gpu"])

    def test_new_receiver_and_handoff_are_both_cpu_only(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            submit = self.run_fixture(
                Path(directory), Mock(side_effect=["COMPLETE", "COMPLETE", "RUNNING"])
            )
            self.assertEqual(submit.call_count, 2)
            self.assertTrue(all(call.kwargs["gpu"] is False for call in submit.call_args_list))
            self.assertEqual(
                submit.call_args_list[0].kwargs["predecessor"], self.records()[0]["training"]
            )
            self.assertEqual(submit.call_args_list[1].kwargs["datasets"], [])

    def test_handoff_resumes_existing_reader_without_resubmit(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            submit = self.run_fixture(
                Path(directory), Mock(side_effect=["COMPLETE", "RUNNING"]), submitted=True
            )
            self.assertEqual(submit.call_count, 1)
            self.assertIn("coordinator", submit.call_args.args[0])
            self.assertFalse(submit.call_args.kwargs["gpu"])

    def test_completed_reader_returns_one_receipt(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory)
            submit = self.run_fixture(root, Mock(return_value="COMPLETE"), clock=(0,))
            self.assertEqual(submit.call_count, 1)
            self.assertTrue((root / "relay/complete.json").is_file())
            self.assertTrue((root / "relay/shard_0001.json").is_file())


if __name__ == "__main__":
    unittest.main()
