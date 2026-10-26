"""Regression tests for interruption, immutable receipts and disjoint shards."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2 import dispatch_matched as dispatch
from experiments.hung_sprint2.dispatch_state import (
    atomic_create,
    exclusive_lock,
    make_shards,
    select_shard,
)
from tests import test_hung_matched_dispatcher as fixtures


class ResumeTests(unittest.TestCase):
    setUp = fixtures.MatchedDispatcherTests.setUp
    save = fixtures.MatchedDispatcherTests.save

    def fake_stage(self, command, **kwargs):
        if command[0] == "git":
            return SimpleNamespace(returncode=0)
        self.executions.append(command)
        output = Path(command[command.index("--output") + 1])
        output.mkdir(parents=True)
        checkpoint = output / "runner.pt"
        checkpoint.write_bytes(b"fixture-state")
        (output / "run_manifest.json").write_text(
            json.dumps(
                {
                    "status": "completed",
                    "run_id": output.name,
                    "code": {"executed_sources": self.single_code["executed_sources"]},
                    "final_runner_checkpoint_sha256": sha256_file(checkpoint),
                }
            ),
            encoding="utf-8",
        )
        (output / "forecasts.jsonl").write_text('{"prediction": 1}\n', encoding="utf-8")
        return SimpleNamespace(returncode=0)

    def run_dispatch(self, *, resume=False, **kwargs):
        with patch.object(dispatch.subprocess, "run", side_effect=self.fake_stage):
            with patch("builtins.print"):
                return dispatch.dispatch(self.plan_path, execute=True, resume=resume, **kwargs)

    def test_complete_resume_executes_zero_stages_and_preserves_receipts(self):
        self.executions = []
        self.save()
        self.run_dispatch()
        root = Path(self.plan["output_root"])
        before = {str(p): p.read_bytes() for p in (root / "receipts").rglob("*.json")}
        self.run_dispatch(resume=True)
        self.assertEqual(len(self.executions), 2)
        self.assertEqual(
            before, {str(p): p.read_bytes() for p in (root / "receipts").rglob("*.json")}
        )

    def test_verifier_checks_receipts_without_starting_training(self):
        self.executions = []
        self.save()
        self.run_dispatch()
        with patch.object(dispatch.subprocess, "run", side_effect=self.fake_stage):
            result = dispatch.dispatch(self.plan_path, execute=False, resume=True, verify_only=True)
        self.assertTrue(result["verified"])
        self.assertEqual(len(self.executions), 2)
        receipt = Path(self.plan["output_root"]) / "receipts/seasonal7/replay-42.json"
        receipt.unlink()
        with self.assertRaisesRegex(ValueError, "Missing stage receipt"):
            dispatch.dispatch(self.plan_path, execute=False, resume=True, verify_only=True)
        self.assertEqual(len(self.executions), 2)

    def test_dry_run_rechecks_input_bytes_after_cached_preflight(self):
        self.save()
        manifest = {"config": {"dataset_id": "urbanev", "city_id": "SZH", "history_days": 7}}
        with patch.object(
            dispatch, "_load_run", side_effect=[manifest, ValueError("changed input")]
        ):
            with self.assertRaisesRegex(ValueError, "changed input"):
                dispatch.dispatch(self.plan_path, execute=False)

    def test_interruption_after_first_receipt_resumes_only_missing_stage(self):
        self.executions = []
        self.save()
        original = dispatch.atomic_create

        def stop_after_receipt(path, value):
            original(path, value)
            if path.name == "replay-42.json":
                raise KeyboardInterrupt("simulated interruption")

        with patch.object(dispatch, "atomic_create", side_effect=stop_after_receipt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_dispatch()
        self.run_dispatch(resume=True)
        self.assertEqual(len(self.executions), 2)

    def test_output_without_receipt_fails_closed_and_is_preserved(self):
        self.executions = []
        self.save()
        with patch.object(dispatch, "verify_stage_output", side_effect=ValueError("interrupted")):
            with self.assertRaisesRegex(ValueError, "interrupted"):
                self.run_dispatch()
        with self.assertRaisesRegex(ValueError, "Unreceipted partial"):
            self.run_dispatch(resume=True)
        self.assertEqual(len(self.executions), 1)
        self.assertTrue(
            (Path(self.plan["output_root"]) / "jobs/seasonal7/replay-42/runner.pt").exists()
        )

    def test_changed_output_log_receipt_or_plan_never_skips(self):
        for kind in ("forecast", "extra_file", "log", "receipt", "plan"):
            with self.subTest(kind=kind):
                self.plan["output_root"] = str(self.root / kind)
                self.save()
                self.executions = []
                self.run_dispatch()
                root = Path(self.plan["output_root"])
                if kind == "plan":
                    self.plan["seeds"].append(11)
                    self.save()
                else:
                    target = {
                        "forecast": root / "jobs/seasonal7/replay-42/forecasts.jsonl",
                        "extra_file": root / "jobs/seasonal7/replay-90/unexpected.txt",
                        "log": root / "logs/seasonal7/replay-42.log",
                        "receipt": root / "receipts/seasonal7/replay-42.json",
                    }[kind]
                    target.write_text("{}", encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.run_dispatch(resume=True)
                self.assertEqual(len(self.executions), 2)

    def test_root_lock_blocks_second_executor_and_releases_on_error(self):
        self.root.mkdir(exist_ok=True)
        with exclusive_lock(self.root):
            with self.assertRaisesRegex(ValueError, "already locked"):
                with exclusive_lock(self.root):
                    self.fail("duplicate lock acquired")
        with exclusive_lock(self.root):
            pass

    def test_atomic_receipt_never_overwrites(self):
        path = self.root / "receipt.json"
        atomic_create(path, {"first": 1})
        with self.assertRaises(FileExistsError):
            atomic_create(path, {"second": 2})
        self.assertEqual(json.loads(path.read_text()), {"first": 1})

    def test_process_termination_releases_os_lock(self):
        child = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "-c",
                "import sys,time; from pathlib import Path; "
                "from experiments.hung_sprint2.dispatch_state import exclusive_lock; "
                "lock=exclusive_lock(Path(sys.argv[1])); lock.__enter__(); "
                "print('locked', flush=True); time.sleep(30)",
                str(self.root),
            ],
            cwd=dispatch.ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(child.stdout.readline().strip(), "locked")
            with self.assertRaisesRegex(ValueError, "already locked"):
                with exclusive_lock(self.root):
                    self.fail("duplicate acquired")
        finally:
            child.terminate()
            child.communicate(timeout=10)
        with exclusive_lock(self.root):
            pass

    def test_two_shards_resume_into_one_plan_without_duplicate_execution(self):
        self.executions = []
        entity_file = self.input_run / "entities.jsonl"
        entity = json.loads(entity_file.read_text())
        entity["identity"][2] = "1050"
        with entity_file.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entity) + "\n")
        selection = json.loads(self.selection_path.read_text())
        selection["budgets"]["7"]["representative_entities"].append(
            {
                "entity_id": "1050",
                "initialization": "target_initial_adaptation",
            }
        )
        self.selection_path.write_text(json.dumps(selection), encoding="utf-8")
        self.plan["selection"]["sha256"] = sha256_file(self.selection_path)
        self.plan["cells"].append({**self.plan["cells"][0], "id": "other", "entity_id": "1050"})
        self.plan["jobs"].append({**self.plan["jobs"][0], "id": "other_job", "cell": "other"})
        self.save()
        shards = self.root / "shards.json"
        atomic_create(
            shards, make_shards(sha256_file(self.plan_path), ["seasonal7", "other_job"], 1)
        )
        kwargs = {"shards_path": shards, "shards_sha256": sha256_file(shards)}
        self.run_dispatch(shard_id="shard_0000", **kwargs)
        self.assertEqual(len(self.executions), 2)
        self.run_dispatch(resume=True, shard_id="shard_0001", **kwargs)
        self.run_dispatch(resume=True, shard_id="shard_0000", **kwargs)
        self.assertEqual(len(self.executions), 4)

    def test_shards_are_complete_disjoint_and_plan_bound(self):
        ids = ["job_c", "job_a", "job_b"]
        spec = make_shards("a" * 64, ids, 2)
        self.assertEqual(select_shard(spec, "a" * 64, ids, "shard_0000"), ["job_a", "job_b"])
        with self.assertRaisesRegex(ValueError, "identity"):
            select_shard(spec, "b" * 64, ids, "shard_0000")
        spec["shards"][1]["job_ids"].append("job_a")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            select_shard(spec, "a" * 64, ids, "shard_0000")


if __name__ == "__main__":
    unittest.main()
