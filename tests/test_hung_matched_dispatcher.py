"""Offline failure gates and CLI construction for explicit Development jobs."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2 import dispatch_matched as dispatch


class MatchedDispatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = dispatch.ROOT / ".cache"
        temp_root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input_base = self.root / "inputs"
        self.input_run = self.input_base / "urbanev-SZH-7d"
        self.input_run.mkdir(parents=True)
        (self.input_run / "entities.jsonl").write_text(
            json.dumps(
                {
                    "identity": ["urbanev", "SZH", "2264"],
                    "role": "development",
                    "initialization": "target_initial_adaptation",
                    "initial_trainable": 6,
                    "scale": {"fit_sha256": "a" * 64},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.selection_path = self.root / "selection.json"
        self.selection_path.write_text(
            json.dumps(
                {
                    "budgets": {
                        "7": {
                            "manifest_sha256": "b" * 64,
                            "representative_entities": [
                                {"entity_id": "2264", "initialization": "target_initial_adaptation"}
                            ],
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        self.config_path = dispatch.ROOT / "experiments/hung_sprint2/development_config_v1.json"
        self.plan_path = self.root / "plan.json"
        self.plan = {
            "schema": "hung-matched-development-dispatch-v1",
            "scope": "development_only",
            "code_commit": "test-commit",
            "selection": {
                "path": str(self.selection_path),
                "sha256": sha256_file(self.selection_path),
            },
            "input_base": str(self.input_base),
            "budgets": [7],
            "seeds": [7],
            "configs": [
                {
                    "id": "base",
                    "path": str(self.config_path),
                    "sha256": sha256_file(self.config_path),
                }
            ],
            "cells": [
                {
                    "id": "cell7",
                    "budget": 7,
                    "seed": 7,
                    "entity_id": "2264",
                    "input_manifest_sha256": "b" * 64,
                }
            ],
            "jobs": [
                {
                    "id": "seasonal7",
                    "cell": "cell7",
                    "config": "base",
                    "method": "seasonal_naive",
                    "device": "cpu",
                    "source": None,
                    "target": None,
                }
            ],
            "output_root": str(self.root / "new-output"),
        }
        self.code_patch = patch.object(
            dispatch,
            "_code_identity",
            return_value={"commit": "test-commit", "worktree_status": [], "executed_sources": {}},
        )
        self.load_patch = patch.object(
            dispatch,
            "_load_run",
            return_value={"config": {"dataset_id": "urbanev", "city_id": "SZH", "history_days": 7}},
        )
        self.ignore_patch = patch.object(
            dispatch.subprocess, "run", return_value=type("Result", (), {"returncode": 0})()
        )
        self.code_patch.start()
        self.load_patch.start()
        self.ignore_patch.start()
        self.addCleanup(self.code_patch.stop)
        self.addCleanup(self.load_patch.stop)
        self.addCleanup(self.ignore_patch.stop)

    def save(self) -> None:
        self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")

    def test_dry_run_builds_allowlisted_single_cli_and_writes_nothing(self) -> None:
        self.save()
        with patch("builtins.print") as printed:
            result = dispatch.dispatch(self.plan_path, execute=False)
        self.assertEqual(result, {"jobs": 1, "stages": 2, "executed": False})
        self.assertEqual(printed.call_count, 2)
        first = json.loads(printed.call_args_list[0].args[0])
        second = json.loads(printed.call_args_list[1].args[0])
        self.assertEqual(
            first["argv"][2:4],
            ["experiments.hung_sprint2.single_baseline_cli", "replay-development"],
        )
        self.assertIn("runner.pt", second["argv"][second["argv"].index("--resume-checkpoint") + 1])
        self.assertFalse((self.root / "new-output").exists())

    def test_existing_output_refused_before_any_stage(self) -> None:
        (self.root / "new-output").mkdir()
        self.save()
        with self.assertRaisesRegex(ValueError, "already exists"):
            dispatch.parse_plan(self.plan_path)

    def test_final_role_and_bad_hash_fail_closed(self) -> None:
        (self.input_run / "entities.jsonl").write_text(
            json.dumps(
                {
                    "identity": ["urbanev", "SZH", "2264"],
                    "role": "final",
                    "initialization": "target_initial_adaptation",
                    "scale": {"fit_sha256": "a" * 64},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.save()
        with self.assertRaisesRegex(ValueError, "accepted Development"):
            dispatch.parse_plan(self.plan_path)
        self.plan["configs"][0]["sha256"] = "0" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            dispatch.parse_plan(self.plan_path)

    def test_no_arbitrary_method_or_duplicate_deterministic_seed(self) -> None:
        self.plan["jobs"][0]["method"] = "shell"
        self.save()
        with self.assertRaisesRegex(ValueError, "Unsupported method"):
            dispatch.parse_plan(self.plan_path)
        self.plan["jobs"][0]["method"] = "seasonal_naive"
        self.plan["jobs"].append({**self.plan["jobs"][0], "id": "seasonal_again"})
        self.save()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            dispatch.parse_plan(self.plan_path)

    def test_capacity_gate_is_fail_closed(self) -> None:
        with patch.object(dispatch, "free_space", return_value=dispatch.MIN_FREE_BYTES - 1):
            with self.assertRaisesRegex(ValueError, "8 GiB"):
                dispatch.require_capacity(self.root / "output")

    def test_controller_builds_fresh_target_then_bound_split_resume(self) -> None:
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        job = {
            "method": "confidence",
            "device": "cuda",
            "source": {"path": str(self.root / "source.pt"), "sha256": "c" * 64},
            "target": None,
        }
        cell = {
            "input_run": self.input_run,
            "input_manifest_sha256": "b" * 64,
            "entity_id": "2264",
            "seed": 7,
            "entity": {"initial_trainable": 6},
        }
        stages = dispatch.build_stages(job, cell, config, self.root / "job")
        self.assertEqual([stage[0] for stage in stages], ["target", "replay-42", "replay-90"])
        self.assertEqual(stages[0][1], "experiments.hung_sprint2.cli")
        self.assertIn(
            "target_checkpoint.pt", stages[1][2][stages[1][2].index("--target-checkpoint") + 1]
        )
        self.assertIn(
            "runner_checkpoint.pt", stages[2][2][stages[2][2].index("--resume-checkpoint") + 1]
        )

    def test_target_only_builds_seeded_initial_and_runner_pt_resume(self) -> None:
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        job = {"method": "target_only", "device": "cpu", "source": None, "target": None}
        cell = {
            "input_run": self.input_run,
            "input_manifest_sha256": "b" * 64,
            "entity_id": "2264",
            "seed": 7,
            "entity": {"initial_trainable": 6},
        }
        stages = dispatch.build_stages(job, cell, config, self.root / "job")
        self.assertEqual(
            [stage[0] for stage in stages], ["target-only-init", "replay-42", "replay-90"]
        )
        self.assertEqual(stages[0][2][stages[0][2].index("--steps") + 1], "3")
        self.assertIn("runner.pt", stages[2][2][stages[2][2].index("--resume-checkpoint") + 1])

    def test_duplicate_json_key_refused(self) -> None:
        bad = self.root / "duplicate.json"
        bad.write_text('{"schema": "one", "schema": "two"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            dispatch.read_json(bad)


if __name__ == "__main__":
    unittest.main()
