"""One-shard CPU receiver barriers; synthetic archives, no GPU/network/training."""

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tools import hung_cloud_receiver as receiver
from tools import hung_provider as provider


class CloudReceiverTests(unittest.TestCase):
    def fixture(self, root):
        repo = root / "repo"
        folder = repo / ".cache/provider"
        folder.mkdir(parents=True)
        output = repo / ".cache/provider-output"
        plan = folder / "plan.json"
        provider.save(
            plan,
            {
                "scope": "development_only",
                "code_commit": "synthetic-code",
                "output_root": str(output.resolve()),
            },
        )
        partition = folder / "shards.json"
        provider.save(
            partition,
            {
                "plan_sha256": provider.sha256(plan),
                "shards": [{"id": "shard_0008", "job_ids": ["fixture"]}],
            },
        )
        archive = root / "artifacts.zip.bin"
        with zipfile.ZipFile(archive, "x") as stream:
            stream.writestr(
                "dispatch_identity.json", json.dumps({"plan_sha256": provider.sha256(plan)})
            )
            stream.writestr("receipts/fixture/job.json", "{}")
            stream.writestr("jobs/fixture/replay-90/run_manifest.json", "{}")
        receipt = root / "receipt.json"
        record = {
            "shard_id": "shard_0008",
            "job_ids": ["fixture"],
            "plan_sha256": provider.sha256(plan),
            "shards_sha256": provider.sha256(partition),
            "exit_code": 0,
            "local_verify_exit_code": 0,
            "crc": "passed",
            "artifact_bytes": archive.stat().st_size,
            "artifact_sha256": provider.sha256(archive),
        }
        provider.save(receipt, record)
        return repo, plan, partition, output, archive, receipt, record

    def restore(self, root, fixture):
        _, plan, partition, _, archive, receipt, _ = fixture
        return receiver.restore(
            provider, archive, receipt, plan, partition, root=root, expected_code="synthetic-code"
        )

    def test_complete_archive_is_restored_without_training(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            fixture = self.fixture(root)
            before = fixture[4].read_bytes()
            result = self.restore(root, fixture)
            self.assertEqual(result["job_ids"], ["fixture"])
            self.assertTrue((fixture[3] / "receipts/fixture/job.json").is_file())
            self.assertEqual(fixture[4].read_bytes(), before)

    def test_command_is_verify_only_with_no_execution_fallback(self):
        command = receiver.verification_command(
            Path("plan"), Path("shards"), "shard_0008", lambda _: "pin"
        )
        self.assertEqual(command[-2:], ["--resume", "--verify-only"])
        self.assertNotIn("--execute", command)

    def test_wrong_jobs_or_failed_receipt_stops_before_restore(self):
        for key, value in [
            ("job_ids", ["foreign"]),
            ("exit_code", 1),
            ("local_verify_exit_code", 1),
            ("plan_sha256", "foreign"),
            ("shards_sha256", "foreign"),
        ]:
            with self.subTest(key=key), tempfile.TemporaryDirectory(dir=".") as directory:
                root = Path(directory).resolve()
                fixture = self.fixture(root)
                record = fixture[-1]
                record[key] = value
                fixture[5].write_text(json.dumps(record), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.restore(root, fixture)
                self.assertFalse(fixture[3].exists())

    def test_corrupt_and_unsafe_archive_stop(self):
        for unsafe in (False, True):
            with self.subTest(unsafe=unsafe), tempfile.TemporaryDirectory(dir=".") as directory:
                root = Path(directory).resolve()
                fixture = self.fixture(root)
                if unsafe:
                    with zipfile.ZipFile(fixture[4], "a") as stream:
                        stream.writestr("../escape", "fixture")
                    record = fixture[-1]
                    record.update(
                        artifact_sha256=provider.sha256(fixture[4]),
                        artifact_bytes=fixture[4].stat().st_size,
                    )
                    fixture[5].write_text(json.dumps(record), encoding="utf-8")
                else:
                    fixture[4].write_bytes(b"corrupt fixture")
                with self.assertRaises(ValueError):
                    self.restore(root, fixture)
                self.assertFalse(fixture[3].exists())

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            fixture = self.fixture(root)
            fixture[3].mkdir()
            sentinel = fixture[3] / "original.txt"
            sentinel.write_text("preserve")
            with self.assertRaises(ValueError):
                self.restore(root, fixture)
            self.assertEqual(sentinel.read_text(), "preserve")

    def test_failed_official_verification_never_scores_or_marks_complete(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            fixture = self.fixture(root)
            scorer = {"build_catalog": Mock(), "aggregate_results": Mock()}
            evidence = root / "readback"
            with patch.object(
                receiver.subprocess, "run", return_value=SimpleNamespace(returncode=1)
            ) as run:
                with self.assertRaises(ValueError):
                    receiver.receive(
                        provider,
                        scorer,
                        fixture[4],
                        fixture[5],
                        fixture[0],
                        expected_code="synthetic-code",
                        evidence=evidence,
                        scorer_sha256="fixture",
                    )
                self.assertIn("--verify-only", run.call_args.args[0])
                self.assertNotIn("--execute", run.call_args.args[0])
            scorer["build_catalog"].assert_not_called()
            scorer["aggregate_results"].assert_not_called()
            self.assertEqual(
                json.loads((evidence / "verify-exit.json").read_bytes())["exit_code"], 1
            )
            self.assertFalse((evidence / "readback-summary.json").exists())


if __name__ == "__main__":
    unittest.main()
