"""Offline coverage and failure gates for the explicit representative plan generator."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2 import generate_matched_plan as generator


class PlanGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_root = generator.dispatch.ROOT / ".cache"
        temp_root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input_base = self.root / "inputs"
        self.input_base.mkdir()
        base = json.loads(
            (
                generator.dispatch.ROOT / "experiments/hung_sprint2/development_config_v1.json"
            ).read_text(encoding="utf-8")
        )
        self.configs = {}
        self.config_paths = {}
        for name in generator.CONFIG_NAMES:
            config = copy.deepcopy(base)
            replay = config["replay"]
            if name == "online_best":
                replay["selection_rule"] = "online_best_lambda"
            elif name == "without_confidence":
                replay["selection_rule"] = "without_confidence"
            elif name in {
                "fixed_retention",
                "full_finetuning",
                "source_error",
                "uncertainty",
                "drift",
            }:
                replay["selection_rule"] = name
            if name == "fixed_retention":
                replay["initial_level"] = 0.1
            if name == "full_finetuning":
                replay["initial_level"] = 0.0
                config["target"]["retention_weight"] = 0.0
            if name == "parameter_retention":
                config["target"].update(retention_kind="parameter", retention_weight=0.01)
                replay.update(
                    retention_kind="parameter", initial_level=0.01, level_one=0.01, level_two=0.02
                )
            if name == "block7":
                replay["block_days"] = 7
            if name == "block28":
                replay["block_days"] = 28
            if name == "no_source":
                config["target"]["initialization_kind"] = "random_target"
                replay["initialization_kind"] = "random_target"
            config["status"] = (
                base["status"]
                if name in {"main", "online_best", "without_confidence"}
                else f"{name} proposal"
            )
            path = self.root / f"{name}.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            self.config_paths[name] = path
            self.configs[name] = config
        self.selection_path = self.root / "selection.json"
        selection = {
            "budgets": {
                str(b): {
                    "manifest_sha256": "a" * 64,
                    "representative_entities": [
                        {
                            "entity_id": f"{b}{index:02d}",
                            "initialization": "target_initial_adaptation",
                        }
                        for index in range(count)
                    ],
                }
                for b, count in ((7, 6), (14, 8), (28, 9))
            }
        }
        self.selection_path.write_text(json.dumps(selection), encoding="utf-8")
        for budget in (7, 14, 28):
            input_run = self.input_base / f"urbanev-SZH-{budget}d"
            input_run.mkdir()
            with (input_run / "entities.jsonl").open("x", encoding="utf-8") as stream:
                for entity in selection["budgets"][str(budget)]["representative_entities"]:
                    stream.write(
                        json.dumps(
                            {
                                "identity": ["urbanev", "SZH", entity["entity_id"]],
                                "role": "development",
                                "initialization": entity["initialization"],
                                "initial_trainable": 6,
                                "scale": {"fit_sha256": "d" * 64},
                            }
                        )
                        + "\n"
                    )
        self.lambda_path = self.root / "lambda.json"
        self.lambda_path.write_text(
            json.dumps(
                {
                    "schema": "hung-parameter-lambda-development-selection-v1",
                    "scope": "development_only",
                    "rule": "station_first_mean",
                    "preflight_sha256": "b" * 64,
                    "selection_sha256": sha256_file(self.selection_path),
                    "chosen_index": 0,
                    "chosen_lambda_low": 0.01,
                    "ranking": [{} for _ in range(4)],
                    "cells": [{} for _ in range(36)],
                }
            ),
            encoding="utf-8",
        )
        self.recipe_path = self.root / "recipe.json"
        self.plan_path = self.root / "plan.json"
        self.coverage_path = self.root / "coverage.json"
        self.recipe = {
            "schema": "hung-matched-plan-generator-v1",
            "scope": "development_only",
            "code_commit": "test-commit",
            "selection": self.pin(self.selection_path),
            "input_base": str(self.input_base),
            "lambda": {"selection": self.pin(self.lambda_path), "chosen_lambda_low": 0.01},
            "configs": {name: self.pin(path) for name, path in self.config_paths.items()},
            "sources": [],
            "targets": [],
            "existing_runs": [],
            "output_root": str(self.root / "run-output"),
        }
        for budget in (7, 14, 28):
            for seed in (7, 11, 19):
                source = self.root / f"source-{budget}-{seed}.pt"
                source.write_bytes(f"{budget}-{seed}".encode())
                self.recipe["sources"].append(
                    {"budget": budget, "seed": seed, "checkpoint": self.pin(source)}
                )
                for entity in selection["budgets"][str(budget)]["representative_entities"]:
                    cell = generator.cell_id(budget, seed, entity["entity_id"])
                    for variant in generator.TARGET_NAMES:
                        self.recipe["targets"].append(
                            {"cell": cell, "variant": variant, "mode": "create", "checkpoint": None}
                        )
                    for prefix in ("main", "block7"):
                        self.recipe["existing_runs"].append(
                            {
                                "job_id": f"{prefix}_{cell}",
                                "action": "rerun",
                                "run_manifest": None,
                                "reason": "Fixture requests a new complete matrix",
                            }
                        )
        self.code_patch = patch.object(
            generator.dispatch,
            "_code_identity",
            return_value={"commit": "test-commit", "worktree_status": [], "executed_sources": {}},
        )
        self.grid_patch = patch.object(generator, "verify_checkpoint_grid")
        self.code_patch.start()
        self.grid_patch.start()
        self.addCleanup(self.code_patch.stop)
        self.addCleanup(self.grid_patch.stop)

    @staticmethod
    def pin(path: Path) -> dict:
        return {"path": str(path), "sha256": sha256_file(path)}

    def save(self) -> str:
        self.recipe_path.write_text(json.dumps(self.recipe), encoding="utf-8")
        return sha256_file(self.recipe_path)

    def test_complete_matrix_and_zero_delta_aliases(self) -> None:
        digest = self.save()
        coverage = generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        plan = json.loads(self.plan_path.read_text(encoding="utf-8"))
        self.assertEqual(coverage["declared_cells"], 69)
        self.assertEqual(coverage["declared_jobs"], 920)
        self.assertEqual(coverage["scheduled_jobs"], 920)
        self.assertEqual(coverage["aliases"]["fixed_lambda"], "fixed_retention")
        self.assertEqual(coverage["aliases"]["without_confidence"], "online_best")
        self.assertEqual(len([j for j in plan["jobs"] if j["method"] == "seasonal_naive"]), 23)
        self.assertFalse(any(j["id"].startswith("without_confidence_") for j in plan["jobs"]))
        self.assertEqual(coverage["plan_sha256"], sha256_file(self.plan_path))

        def fake_load_run(path, digest):
            budget = int(path.name.removeprefix("urbanev-SZH-").removesuffix("d"))
            return {
                "config": {
                    "dataset_id": "urbanev",
                    "city_id": "SZH",
                    "history_days": budget,
                }
            }

        with patch.object(generator.dispatch, "_load_run", side_effect=fake_load_run):
            parsed, _, _, jobs = generator.dispatch.parse_plan(self.plan_path)
        self.assertEqual(parsed["code_commit"], "test-commit")
        self.assertEqual(len(jobs), 920)

    def test_positive_delta_runs_distinct_ablation(self) -> None:
        config = self.configs["without_confidence"]
        config["replay"]["delta"] = 0.01
        path = self.config_paths["without_confidence"]
        path.write_text(json.dumps(config), encoding="utf-8")
        self.recipe["configs"]["without_confidence"] = self.pin(path)
        digest = self.save()
        coverage = generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertEqual(coverage["declared_jobs"], 989)
        self.assertIsNone(coverage["aliases"]["without_confidence"])

    def test_missing_target_or_wrong_lambda_fails_before_write(self) -> None:
        self.recipe["targets"].pop()
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "Every target variant"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())
        self.recipe["targets"].append(
            {"cell": "b28s19e2808", "variant": "no_source", "mode": "create", "checkpoint": None}
        )
        self.recipe["lambda"]["chosen_lambda_low"] = 0.02
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "lambda selection differs"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())

    def test_existing_main_block7_jobs_need_explicit_decisions(self) -> None:
        self.recipe["existing_runs"].pop()
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "explicit reuse or rerun decision"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())

    def test_reused_run_needs_matching_bound_manifest_and_checkpoint(self) -> None:
        cell = {
            "id": "b7s7e700",
            "seed": 7,
            "entity_id": "700",
            "input_manifest_sha256": "a" * 64,
        }
        job = {
            "id": "main_b7s7e700",
            "method": "confidence",
            "source": {"sha256": "b" * 64},
            "target": {"sha256": "c" * 64},
        }
        output = self.root / "prior" / "replay-90"
        output.mkdir(parents=True)
        checkpoint = output / "runner_checkpoint.pt"
        checkpoint.write_bytes(b"fixture checkpoint")
        journal = output / "events.jsonl"
        journal.write_text("fixture event\n", encoding="utf-8")
        manifest = output / "run_manifest.json"
        settings = self.configs["main"]["replay"]
        record = {
            "schema": "hung-sprint2-development-replay-v1",
            "status": "completed",
            "run_id": "replay-90",
            "code": {"executed_sources": {}},
            "runner_cursor": 90,
            "config": {
                "selection_rule": "confidence",
                "controller": {
                    "levels": [0.0, settings["level_one"], settings["level_two"]],
                    "initial_level": settings["initial_level"],
                    "block_days": settings["block_days"],
                    "min_complete_days": settings["min_complete_days"],
                    "delta": settings["delta"],
                    "alpha": settings["alpha"],
                    "bootstrap_segment_days": settings["bootstrap_segment_days"],
                    "bootstrap_resamples": settings["bootstrap_resamples"],
                    "seed": 7,
                    "challenger_rule": settings["challenger_rule"],
                },
                "retention_kind": "latent",
                "initialization_kind": "source",
                "epsilon": self.configs["main"]["target"]["epsilon"],
                "seed": 7,
                "max_origins": 90,
            },
            "input_binding": {"input_manifest_sha256": "a" * 64, "entity_id": "700"},
            "source_checkpoint_sha256": "b" * 64,
            "target_checkpoint_sha256": "c" * 64,
            "final_runner_checkpoint_sha256": sha256_file(checkpoint),
            "event_journal": {"file": journal.name, "sha256": sha256_file(journal)},
        }
        manifest.write_text(json.dumps(record), encoding="utf-8")
        spec = {"job_id": job["id"], "run_manifest": self.pin(manifest)}
        code = {"executed_sources": {}}
        generator.verify_reuse(spec, job, cell, self.configs["main"], code)
        record["config"]["seed"] = 11
        manifest.write_text(json.dumps(record), encoding="utf-8")
        spec["run_manifest"] = self.pin(manifest)
        with self.assertRaisesRegex(ValueError, "provenance differs"):
            generator.verify_reuse(spec, job, cell, self.configs["main"], code)


if __name__ == "__main__":
    unittest.main()
