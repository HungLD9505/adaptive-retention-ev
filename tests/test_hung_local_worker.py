"""Queue gates authenticate inputs and never launch training in offline tests."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.hung_local_worker import validate_queue, wait_for_barrier, work
from tools.hung_provider import save, sha256


class LocalQueueTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.plan = self.root / "plan.json"
        self.partition = self.root / "partition.json"
        self.proof = self.root / "proof.json"
        save(
            self.plan,
            {
                "scope": "development_only",
                "output_root": str(self.root),
                "jobs": [{"id": s} for s in ("p", "b", "a", "k")],
            },
        )
        save(
            self.partition,
            {
                "schema": "hung-dispatch-shards-v1",
                "plan_sha256": sha256(self.plan),
                "shards": [
                    {"id": name, "job_ids": [job]}
                    for name, job in (
                        ("pilot_0000", "p"),
                        ("barrier", "b"),
                        ("assigned", "a"),
                        ("remote", "k"),
                    )
                ],
            },
        )
        save(self.proof, {"cross_runtime": {"passed": True}, "storage_readback": {"crc": "passed"}})
        self.queue = {
            "schema": "hung-local-development-queue-v1",
            "worker_source_sha256": sha256(Path(work.__code__.co_filename)),
            "plan": str(self.plan),
            "plan_sha256": sha256(self.plan),
            "partition": str(self.partition),
            "partition_sha256": sha256(self.partition),
            "provider_readback": str(self.proof),
            "provider_readback_sha256": sha256(self.proof),
            "minimum_free_bytes": 8 * 1024**3,
            "pending_local_shards": ["assigned"],
            "canonical_repo": str(self.root),
            "project_root": str(self.root),
            "barrier_timeout_seconds": 0,
            "barrier": {
                "shard_id": "barrier",
                "evidence": str(self.root / "barrier"),
                "job_ids": ["b"],
            },
            "routes": {
                "pilot_0000": "completed_local_pilot",
                "barrier": "local",
                "assigned": "local",
                "remote": "kaggle",
            },
        }

    def write_queue(self):
        path = self.root / f"queue-{len(list(self.root.glob('queue*')))}.json"
        save(path, self.queue)
        return path, sha256(path)

    def test_dry_run_does_not_wait_or_execute(self):
        path, digest = self.write_queue()
        with patch("tools.hung_local_worker.wait_for_barrier") as wait:
            result = work(path, digest, self.root / "evidence", execute=False)
        self.assertFalse(result["executed"])
        wait.assert_not_called()
        self.assertFalse((self.root / "evidence").exists())

    def test_foreign_or_duplicate_assignment_rejected(self):
        for pending in (["remote"], ["assigned", "assigned"], ["pilot_0000"]):
            with self.subTest(pending=pending):
                self.queue["pending_local_shards"] = pending
                path, digest = self.write_queue()
                with self.assertRaises(ValueError):
                    validate_queue(path, digest)

    def test_changed_plan_fails_before_execution(self):
        path, digest = self.write_queue()
        self.plan.write_text(json.dumps({"scope": "final"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            work(path, digest, self.root / "evidence", execute=True)
        self.assertFalse((self.root / "evidence").exists())

    def test_missing_terminal_barrier_times_out(self):
        with self.assertRaisesRegex(ValueError, "timed out"):
            wait_for_barrier(self.queue)

    def test_execution_failure_stops_and_preserves_record(self):
        path, digest = self.write_queue()
        with patch("tools.hung_local_worker.wait_for_barrier", side_effect=ValueError("corrupt")):
            with self.assertRaisesRegex(ValueError, "corrupt"):
                work(path, digest, self.root / "evidence", execute=True)
        self.assertEqual(
            json.loads((self.root / "evidence/failure.json").read_bytes())["error"], "corrupt"
        )


if __name__ == "__main__":
    unittest.main()
