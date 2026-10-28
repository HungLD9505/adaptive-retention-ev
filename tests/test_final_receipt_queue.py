"""Independent fake producer verifies admission, finite wait and restart behavior."""

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.final_receipt_policy import ReceiptPolicy
from tools.final_receipt_queue import run_queue, sha


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo, self.ops, self.remote, self.previous, self.quota = (
            self.root / name for name in ("repo", "ops", "remote", "previous", "quota")
        )
        for path in (self.repo, self.ops, self.remote, self.previous, self.quota):
            path.mkdir()
        (self.repo / "configs/issue23").mkdir(parents=True)
        lock = self.repo / "configs/issue23/final-execution-lock-20261027-v2.json"
        lock.write_text(json.dumps({"unit_order": [{}, {}, {"fixture": "independent"}]}))
        self.lock_sha = sha(lock)
        pins = {}
        for name in ("prototype_final_unit.py", "async_export.py"):
            path = self.ops / name
            path.write_text("# independently authored fake operator; never executed\n")
            pins[name] = sha(path)
        reservation = {
            "ownership": {"A": [2], "C": []},
            "units": [{"index": 2, "unit": {"fixture": "independent"}}],
            "storage": {
                "mounted_parent": str(self.remote),
                "main_mounted_parent": str(self.previous),
            },
            "input_roots": {"A": str(self.root / "opaque-fixture-inputs")},
        }
        r = self.root / "reservation.json"
        r.write_text(json.dumps(reservation))
        self.receipt = self.previous / "root-acceptance-unit-0000.json"
        self.receipt.write_text(
            json.dumps(
                {
                    "schema": "ev-final-unit-acceptance-v1",
                    "lock_sha256": self.lock_sha,
                    "unit_index": 0,
                    "lane": 0,
                    "accepted_method_cells": 14,
                    "native_readback_verified": True,
                    "independent_content_verified": True,
                }
            )
        )
        (self.previous / "unit-0000-process.json").write_text('{"pid":777}')
        self.observation = self.quota / "quota-actual-1000.json"
        self.observation.write_text(
            json.dumps(
                {
                    "balance": 60,
                    "aggregatePerHour": 1.07,
                    "observedEpoch": time.time(),
                    "activeSessions": 1,
                    "reserve": 30,
                }
            )
        )
        self.config = {
            "receipt_policy": vars(ReceiptPolicy()),
            "repo": str(self.repo),
            "ops": str(self.ops),
            "lock_sha256": self.lock_sha,
            "commit": "fixture-commit",
            "ops_pins": pins,
            "indices": [2],
            "lane": 0,
            "reservations": [{"path": str(r), "sha256": sha(r), "indices": [2]}],
            "scratch": str(self.root),
            "queue_wall_seconds": 10800,
            "initial_previous_receipt_sha256": sha(self.receipt),
            "previous_queue_parent_pid": 555,
            "quota_folder": str(self.quota),
            "intent_folder_name": "new-intents",
            "drive_mount": str(self.root / "fixture-mount"),
            "operational_envelope_sha256": "fixture-envelope",
        }
        self.calls = 0
        self.producer_returncode = 0
        self.completed_cells = 14

    def fake_producer(self, command, **kwargs):
        self.calls += 1
        output = Path(command[command.index("--output") + 1])
        backup = Path(command[command.index("--backup-root") + 1])
        output.mkdir()
        backup.mkdir()
        for i in range(self.completed_cells):
            (output / f"progress-{i:02d}.json").write_text("{}")
            (backup / f"fixture-{i:02d}.receipt.json").write_text("{}")
        if self.producer_returncode == 0:
            (self.remote / "final-unit-0002-publication.zip").write_bytes(b"fixture-only")
        returncode = self.producer_returncode

        class Child:
            pid = 901

            def poll(self):
                return returncode

            def wait(self, timeout=None):
                return returncode

        return Child()

    def run_fixture(self, config=None):
        def git(args, **kwargs):
            return "fixture-commit\n" if "rev-parse" in args else ""

        with (
            patch("tools.final_receipt_queue.subprocess.check_output", side_effect=git),
            patch("tools.final_receipt_queue.subprocess.Popen", side_effect=self.fake_producer),
        ):
            run_queue(config or self.config)

    def test_completed_producer_is_durable_but_never_self_root_credited(self):
        self.run_fixture()
        self.assertEqual(self.calls, 1)
        record = json.loads((self.remote / "unit-0002-exit.json").read_text())
        self.assertEqual(record["completed_method_cells"], 14)
        self.assertFalse((self.remote / "root-acceptance-unit-0002.json").exists())
        process = json.loads((self.remote / "unit-0002-process.json").read_text())
        self.assertEqual(process["previous_receipt_sha256"], sha(self.receipt))
        self.assertEqual(process["receipt_policy"]["completed_inflight"], 1)

    def test_restart_does_not_refit_or_replace_any_existing_output(self):
        self.run_fixture()
        process = self.remote / "unit-0002-process.json"
        before = process.read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_fixture()
        self.assertEqual(self.calls, 1)
        self.assertEqual(process.read_bytes(), before)

    def test_failed_fit_preserves_partial_output_and_never_self_accepts(self):
        self.producer_returncode, self.completed_cells = 1, 4
        with self.assertRaisesRegex(RuntimeError, "preserve"):
            self.run_fixture()
        self.assertEqual(self.calls, 1)
        record = json.loads((self.remote / "unit-0002-exit.json").read_text())
        self.assertEqual(record["returncode"], 1)
        self.assertEqual(record["completed_method_cells"], 4)
        self.assertTrue((self.root / "final-unit-0002-v2").is_dir())
        self.assertFalse((self.remote / "root-acceptance-unit-0002.json").exists())

    def test_absent_root_receipt_has_finite_wait_without_dispatch(self):
        self.receipt.unlink()
        with (
            patch("tools.final_receipt_queue.time.monotonic", side_effect=[0, 0, 600]),
            self.assertRaises(TimeoutError),
        ):
            self.run_fixture()
        self.assertEqual(self.calls, 0)

    def test_quota_reserve_blocks_before_intent_or_producer(self):
        q = json.loads(self.observation.read_text())
        self.observation.write_text(json.dumps({**q, "balance": 30.2}))
        with self.assertRaisesRegex(ValueError, "reserve"):
            self.run_fixture()
        self.assertEqual(self.calls, 0)
        self.assertFalse((self.remote / "new-intents").exists())

    def test_corrupt_receipt_or_changed_operator_blocks_before_producer(self):
        self.receipt.write_text("corrupted{")
        with self.assertRaises(ValueError):
            self.run_fixture()
        self.assertEqual(self.calls, 0)
        (self.ops / "prototype_final_unit.py").write_text("changed operator")
        with self.assertRaises(AssertionError):
            self.run_fixture()
        self.assertEqual(self.calls, 0)
