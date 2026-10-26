"""Offline coverage and failure gates for the explicit representative plan generator."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

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
        self.proxy_profile_path = generator.dispatch.ROOT / "configs/hung-proxy-calibration-v1.json"
        profile = json.loads(self.proxy_profile_path.read_text(encoding="utf-8"))
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
            if name in {"source_error", "uncertainty", "drift"}:
                low, high = profile["thresholds"][name][0]
                replay.update(
                    proxy_low=low,
                    proxy_high=high,
                    proxy_level_low=0.0,
                    proxy_level_mid=0.1,
                    proxy_level_high=0.2,
                )
                if name == "drift":
                    replay.update(drift_reference_mean=0.0, drift_reference_scale=1.0)
            if name == "fixed_retention":
                replay["initial_level"] = 0.1
            if name == "full_finetuning":
                replay["initial_level"] = 0.0
                config["target"]["retention_weight"] = 0.0
            if name == "parameter_retention":
                config["target"].update(retention_kind="parameter", retention_weight=0.1)
                replay.update(
                    retention_kind="parameter", initial_level=0.1, level_one=0.1, level_two=0.2
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
                    "verification_entity_ids": [f"{b}00"],
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
        self.drift_configs = []
        for budget in (7, 14, 28):
            for seed in (7, 11, 19):
                for entity in selection["budgets"][str(budget)]["representative_entities"]:
                    cell = generator.cell_id(budget, seed, entity["entity_id"])
                    drift = copy.deepcopy(base)
                    low, high = profile["thresholds"]["drift"][0]
                    drift["replay"].update(
                        selection_rule="drift",
                        proxy_low=low,
                        proxy_high=high,
                        proxy_level_low=0.0,
                        proxy_level_mid=0.1,
                        proxy_level_high=0.2,
                        drift_reference_mean=0.0,
                        drift_reference_scale=1.0,
                    )
                    drift_path = self.root / f"drift-{cell}.json"
                    drift_path.write_text(json.dumps(drift), encoding="utf-8")
                    self.drift_configs.append({"cell": cell, "config": self.pin(drift_path)})
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
            entity = selection["budgets"][str(budget)]["representative_entities"][0]["entity_id"]
            with (input_run / "schedule.jsonl").open("x", encoding="utf-8") as stream:
                for day in range(90):
                    stream.write(
                        json.dumps(
                            {
                                "identity": ["urbanev", "SZH", entity],
                                "origin": f"day-{day}",
                                "status": "created",
                            }
                        )
                        + "\n"
                    )
            with (input_run / "labels.jsonl").open("x", encoding="utf-8") as stream:
                for day in range(80):
                    stream.write(
                        json.dumps(
                            {
                                "identity": ["urbanev", "SZH", entity],
                                "origin": f"day-{day}",
                                "file_valid": [True] * 24,
                                "energy_kwh": [10.0] * 24,
                            }
                        )
                        + "\n"
                    )
        chosen_entities = {
            budget: selection["budgets"][str(budget)]["representative_entities"][0]["entity_id"]
            for budget in (7, 14, 28)
        }
        self.preflight_path = self.root / "preflight.json"
        self.preflight_path.write_text(
            json.dumps(
                {
                    "seeds": [7, 11, 19],
                    "code_commit": "calibration-code",
                    "budgets": {
                        str(b): {
                            "chosen_entity_id": chosen_entities[b],
                            "input_manifest_sha256": "a" * 64,
                        }
                        for b in (7, 14, 28)
                    },
                }
            ),
            encoding="utf-8",
        )
        levels = (0.1, 10.0, 1000.0, 10000.0)
        lambda_roots, proof, scores = [], [], {}
        for index, level in enumerate(levels):
            candidate = copy.deepcopy(self.configs["parameter_retention"])
            candidate["target"]["retention_weight"] = level
            candidate["replay"].update(initial_level=level, level_one=level, level_two=2 * level)
            candidate_path = self.root / f"lambda-{index}-config.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            matrix_root = self.root / f"lambda-{index}-run"
            matrix_root.mkdir()
            marker = {
                "schema": "hung-sprint2-development-matrix-v1",
                "phase": "verification",
                "budgets": [7, 14, 28],
                "seeds": [7, 11, 19],
                "selection_sha256": sha256_file(self.selection_path),
                "config_sha256": sha256_file(candidate_path),
                "code": {
                    "commit": "calibration-code",
                    "worktree_status": [],
                    "executed_sources": {},
                },
            }
            marker_path = matrix_root / "matrix_identity.json"
            marker_path.write_text(json.dumps(marker), encoding="utf-8")
            lambda_roots.append(
                {
                    "index": index,
                    "path": str(matrix_root),
                    "matrix_sha256": sha256_file(marker_path),
                    "config": self.pin(candidate_path),
                }
            )
            scores[index] = {}
            for budget in (7, 14, 28):
                scores[index][budget] = {}
                for seed in (7, 11, 19):
                    entity = chosen_entities[budget]
                    run = (
                        matrix_root
                        / f"{budget}d"
                        / f"seed-{seed}"
                        / f"entity-{entity}"
                        / "replay-90"
                    )
                    run.mkdir(parents=True)
                    base_dir = matrix_root / f"{budget}d" / f"seed-{seed}"
                    source = base_dir / "source" / "source_checkpoint.pt"
                    source.parent.mkdir(exist_ok=True)
                    source.write_bytes(f"source-{index}-{budget}-{seed}".encode())
                    target = base_dir / f"entity-{entity}" / "target" / "target_checkpoint.pt"
                    target.parent.mkdir(exist_ok=True)
                    target.write_bytes(f"target-{index}-{budget}-{seed}".encode())
                    checkpoint = run / "runner_checkpoint.pt"
                    mae = float(index + 1)
                    issued = [
                        {
                            "index": day,
                            "day_id": f"day-{day}",
                            "y_scaled": torch.full((24,), 10.0) if day < 80 else None,
                            "normalized_mae": mae if day < 80 else None,
                            "forecasts": [torch.full((1, 24), 10.0 - mae) for _ in range(3)],
                            "active_level": 0.0,
                        }
                        for day in range(90)
                    ]
                    binding = {"entity_id": entity, "input_manifest_sha256": "a" * 64}
                    torch.save(
                        {
                            "issued": issued,
                            "pending": None,
                            "next_index": 90,
                            "binding": binding,
                            "energy_scale": 1.0,
                            "controller": {"levels": [0.0, level, 2 * level]},
                        },
                        checkpoint,
                    )
                    journal = run / "events.jsonl"
                    journal.write_text("fixture event\n", encoding="utf-8")
                    scores[index][budget][seed] = mae
                    manifest = {
                        "schema": "hung-sprint2-development-replay-v1",
                        "status": "completed",
                        "code": marker["code"],
                        "runner_cursor": 90,
                        "final_runner_checkpoint_sha256": sha256_file(checkpoint),
                        "source_checkpoint_sha256": sha256_file(source),
                        "target_checkpoint_sha256": sha256_file(target),
                        "input_binding": binding,
                        "event_journal": {"file": journal.name, "sha256": sha256_file(journal)},
                        "coverage": {"requested": 90, "created": 90, "scored": 80},
                        "config": {
                            "selection_rule": "confidence",
                            "retention_kind": "parameter",
                            "seed": seed,
                            "max_origins": 90,
                            "controller": {"levels": [0.0, level, 2 * level]},
                        },
                        "metrics_kwh": {"live": {"mae_kwh": mae, "hours": 80 * 24}},
                    }
                    manifest_path = run / "run_manifest.json"
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    proof.append(
                        {
                            "lambda_index": index,
                            "budget": budget,
                            "seed": seed,
                            "entity_id": entity,
                            "mae_kwh": mae,
                            "scored_origins": 80,
                            "issued_origins_sha256": hashlib.sha256(
                                json.dumps(tuple(item["day_id"] for item in issued)).encode()
                            ).hexdigest(),
                            "scored_origins_sha256": hashlib.sha256(
                                json.dumps(tuple(item["day_id"] for item in issued[:80])).encode()
                            ).hexdigest(),
                            "source_checkpoint_sha256": sha256_file(source),
                            "target_checkpoint_sha256": sha256_file(target),
                            "runner_checkpoint_sha256": sha256_file(checkpoint),
                            "run_manifest_sha256": sha256_file(manifest_path),
                        }
                    )
        ranking = []
        for index, level in enumerate(levels):
            means = {
                str(b): math.fsum(scores[index][b][s] for s in (7, 11, 19)) / 3 for b in (7, 14, 28)
            }
            ranking.append(
                {
                    "index": index,
                    "lambda_low": level,
                    "budget_seed_mean_mae_kwh": means,
                    "equal_budget_mae_kwh": math.fsum(means.values()) / 3,
                }
            )
        self.lambda_path = self.root / "lambda.json"
        self.lambda_path.write_text(
            json.dumps(
                {
                    "schema": "hung-parameter-lambda-development-selection-v1",
                    "scope": "UrbanEV SZH Development target_initial_adaptation only; no Final lock",
                    "rule": "station-first seed mean within budget, equal budget mean, tie smaller lambda",
                    "preflight_sha256": sha256_file(self.preflight_path),
                    "selection_sha256": sha256_file(self.selection_path),
                    "chosen_index": 0,
                    "chosen_lambda_low": 0.1,
                    "ranking": ranking,
                    "cells": proof,
                }
            ),
            encoding="utf-8",
        )
        self.lambda_roots = lambda_roots
        self.proxy_plan_path = self.root / "proxy-plan.json"
        self.proxy_plan_path.write_text(
            json.dumps(
                {
                    "profile_sha256": sha256_file(self.proxy_profile_path),
                    "profile": profile,
                    "cells": [{} for _ in range(9)],
                }
            ),
            encoding="utf-8",
        )
        self.proxy_runs_path = self.root / "proxy-runs.jsonl"
        with self.proxy_runs_path.open("x", encoding="utf-8") as stream:
            for cell_index in range(9):
                for method in ("source_error", "uncertainty", "drift"):
                    for recipe in range(4):
                        run = self.root / f"proxy-{cell_index}-{method}-{recipe}"
                        run.mkdir()
                        manifest = run / "run_manifest.json"
                        manifest.write_text("{}", encoding="utf-8")
                        stream.write(
                            json.dumps(
                                {
                                    "cell_index": cell_index,
                                    "method": method,
                                    "recipe": recipe,
                                    "run_path": str(run),
                                    "manifest_sha256": sha256_file(manifest),
                                }
                            )
                            + "\n"
                        )
        self.proxy_verified = {
            "schema": "hung-proxy-development-selection-v1",
            "scope": "conditional_development_selection_only; no Final lock",
            "cells": 9,
            "matrix_runs": 108,
            "null_run_cells": 0,
            "seeds": [7, 11, 19],
            "selection": {
                name: {"provisional_recipe": 0} for name in ("source_error", "uncertainty", "drift")
            },
        }
        self.proxy_selection_path = self.root / "proxy-selection.json"
        self.proxy_selection_path.write_text(
            json.dumps(
                {
                    **self.proxy_verified,
                    "plan_sha256": sha256_file(self.proxy_plan_path),
                    "runs_sha256": sha256_file(self.proxy_runs_path),
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
            "lambda": {
                "selection": self.pin(self.lambda_path),
                "preflight": self.pin(self.preflight_path),
                "roots": self.lambda_roots,
                "chosen_lambda_low": 0.1,
            },
            "proxy_profile": self.pin(self.proxy_profile_path),
            "proxy_selection": self.pin(self.proxy_selection_path),
            "proxy_plan": self.pin(self.proxy_plan_path),
            "proxy_runs": self.pin(self.proxy_runs_path),
            "configs": {name: self.pin(path) for name, path in self.config_paths.items()},
            "drift_configs": self.drift_configs,
            "sources": [],
            "targets": [],
            "existing_runs": [],
            "output_root": str(self.root / "run-output"),
        }
        for budget in (7, 14, 28):
            for seed in (7, 11, 19):
                source_dir = self.root / f"source-{budget}-{seed}"
                source_dir.mkdir()
                source = source_dir / "source.pt"
                source.write_bytes(f"{budget}-{seed}".encode())
                source_manifest = source_dir / "run_manifest.json"
                source_manifest.write_text(json.dumps({"seed": seed}), encoding="utf-8")
                self.recipe["sources"].append(
                    {
                        "budget": budget,
                        "seed": seed,
                        "checkpoint": {
                            **self.pin(source),
                            "run_manifest_sha256": sha256_file(source_manifest),
                        },
                    }
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
        self.input_patch = patch.object(generator.dispatch, "_load_run", return_value={})
        self.drift_patch = patch.object(
            generator, "drift_reference", return_value=(0.0, 1.0, "first-origin")
        )
        self.code_patch.start()
        self.grid_patch.start()
        self.input_patch.start()
        self.drift_patch.start()
        self.proxy_select_patch = patch(
            "experiments.hung_sprint2.matched_proxy_provenance.proxy_select",
            return_value=self.proxy_verified,
        )
        self.proxy_select_patch.start()
        self.addCleanup(self.code_patch.stop)
        self.addCleanup(self.grid_patch.stop)
        self.addCleanup(self.input_patch.stop)
        self.addCleanup(self.drift_patch.stop)
        self.addCleanup(self.proxy_select_patch.stop)

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
        self.assertEqual(len(coverage["drift_reference_origins"]), 23)
        self.assertEqual(len([c for c in plan["configs"] if c["id"].startswith("drift_")]), 69)

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
        with self.assertRaisesRegex(ValueError, "Lambda ranking/winner differs"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())

    def test_source_manifest_sha_is_required(self) -> None:
        self.recipe["sources"][0]["checkpoint"].pop("run_manifest_sha256")
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "Checkpoint and run-manifest pins required"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())

    def test_fabricated_lambda_ranking_and_cells_are_rejected(self) -> None:
        original = json.loads(self.lambda_path.read_text(encoding="utf-8"))
        changes = (
            (
                "ranking",
                lambda x: x["ranking"][0].update(equal_budget_mae_kwh=0.0),
                "ranking/winner",
            ),
            ("empty_cell", lambda x: x["cells"].__setitem__(0, {}), "proof cell fields"),
            (
                "false_mae",
                lambda x: x["cells"][0].update(mae_kwh=0.0),
                "manifest/checkpoint evidence",
            ),
        )
        for name, mutate, message in changes:
            with self.subTest(name=name):
                changed = copy.deepcopy(original)
                mutate(changed)
                self.lambda_path.write_text(json.dumps(changed), encoding="utf-8")
                self.recipe["lambda"]["selection"] = self.pin(self.lambda_path)
                digest = self.save()
                with self.assertRaisesRegex(ValueError, message):
                    generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
                self.assertFalse(self.plan_path.exists())

    def test_manifest_metric_and_winner_forgery_fails_against_runner_forecasts(self) -> None:
        selected = json.loads(self.lambda_path.read_text(encoding="utf-8"))
        root = Path(self.lambda_roots[0]["path"])
        for cell in selected["cells"]:
            if cell["lambda_index"] != 0:
                continue
            cell["mae_kwh"] = 10.0
            run = (
                root
                / f"{cell['budget']}d"
                / f"seed-{cell['seed']}"
                / f"entity-{cell['entity_id']}"
                / "replay-90"
            )
            manifest_path = run / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["metrics_kwh"]["live"]["mae_kwh"] = 10.0
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            cell["run_manifest_sha256"] = sha256_file(manifest_path)
        selected["ranking"][0]["budget_seed_mean_mae_kwh"] = {
            "7": 10.0,
            "14": 10.0,
            "28": 10.0,
        }
        selected["ranking"][0]["equal_budget_mae_kwh"] = 10.0
        selected["chosen_index"] = 1
        selected["chosen_lambda_low"] = 10.0
        self.lambda_path.write_text(json.dumps(selected), encoding="utf-8")
        spec = copy.deepcopy(self.recipe["lambda"])
        spec["selection"] = self.pin(self.lambda_path)
        spec["chosen_lambda_low"] = 10.0
        config = copy.deepcopy(self.configs["parameter_retention"])
        config["target"]["retention_weight"] = 10.0
        config["replay"].update(initial_level=10.0, level_one=10.0, level_two=20.0)
        accepted = json.loads(self.selection_path.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "run manifest/checkpoint evidence differs"):
            generator.verify_lambda(
                spec,
                config,
                sha256_file(self.selection_path),
                accepted,
                self.input_base,
            )

    def test_existing_main_block7_jobs_need_explicit_decisions(self) -> None:
        self.recipe["existing_runs"].pop()
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "explicit reuse or rerun decision"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())

    def test_missing_or_inconsistent_cell_drift_config_fails_closed(self) -> None:
        removed = self.recipe["drift_configs"].pop()
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "69 cell-specific Drift"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())
        self.recipe["drift_configs"].append(removed)
        drift_path = Path(removed["config"]["path"])
        drift = json.loads(drift_path.read_text(encoding="utf-8"))
        drift["replay"]["proxy_low"] = 0.12
        drift_path.write_text(json.dumps(drift), encoding="utf-8")
        removed["config"] = self.pin(drift_path)
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "threshold/mapping differs"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())

    def test_proxy_config_must_match_selected_provisional_recipe(self) -> None:
        path = self.config_paths["source_error"]
        config = json.loads(path.read_text(encoding="utf-8"))
        config["replay"]["proxy_high"] = 0.6
        path.write_text(json.dumps(config), encoding="utf-8")
        self.recipe["configs"]["source_error"] = self.pin(path)
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "selected recipe: source_error"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())

    def test_proxy_method_cannot_change_shared_controller_schedule(self) -> None:
        for method in ("source_error", "uncertainty", "fixed_retention", "full_finetuning"):
            for field, value in (
                ("delta", 0.01),
                ("level_one", 0.15),
                ("level_two", 0.25),
                ("block_days", 7),
            ):
                with self.subTest(method=method, field=field):
                    configs = copy.deepcopy(self.configs)
                    configs[method]["replay"][field] = value
                    with self.assertRaisesRegex(ValueError, "Matched schedule differs"):
                        generator.comparable_configs(configs)
        for method in ("source_error", "uncertainty"):
            configs = copy.deepcopy(self.configs)
            configs[method]["replay"]["initial_level"] = 0.1
            with self.assertRaisesRegex(ValueError, "Matched schedule differs"):
                generator.comparable_configs(configs)
        configs = copy.deepcopy(self.configs)
        configs["fixed_retention"]["replay"]["initial_level"] = 0.2
        with self.assertRaisesRegex(ValueError, "Fixed/Full target adaptation lambda"):
            generator.comparable_configs(configs)

    def test_fabricated_proxy_selection_or_missing_run_proof_is_rejected(self) -> None:
        selection = json.loads(self.proxy_selection_path.read_text(encoding="utf-8"))
        selection["selection"]["drift"]["provisional_recipe"] = 1
        self.proxy_selection_path.write_text(json.dumps(selection), encoding="utf-8")
        self.recipe["proxy_selection"] = self.pin(self.proxy_selection_path)
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "differs from authenticated plan/run evidence"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())
        rows = self.proxy_runs_path.read_text(encoding="utf-8").splitlines()
        self.proxy_runs_path.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
        self.recipe["proxy_runs"] = self.pin(self.proxy_runs_path)
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "grid incomplete"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())

    def test_proxy_run_manifest_bytes_must_match_runs_proof(self) -> None:
        row = json.loads(self.proxy_runs_path.read_text(encoding="utf-8").splitlines()[0])
        manifest = Path(row["run_path"]) / "run_manifest.json"
        manifest.write_text('{"tampered": true}', encoding="utf-8")
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            generator.generate(self.recipe_path, digest, self.plan_path, self.coverage_path)
        self.assertFalse(self.plan_path.exists())

    def test_drift_reference_must_match_first_accepted_history(self) -> None:
        row = self.recipe["drift_configs"][0]
        path = Path(row["config"]["path"])
        drift = json.loads(path.read_text(encoding="utf-8"))
        drift["replay"]["drift_reference_mean"] = 0.5
        path.write_text(json.dumps(drift), encoding="utf-8")
        row["config"] = self.pin(path)
        digest = self.save()
        with self.assertRaisesRegex(ValueError, "not the first accepted Development history"):
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
