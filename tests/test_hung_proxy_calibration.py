"""Finite-grid, Development isolation, and station-first selection checks."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.supporting_pipeline.checkpoint import load_runner, save_runner
from experiments.supporting_pipeline.cli import _replay
from tests.test_hung_replay_inputs import input_run
from tools.hung_proxy_calibration import (
    METHODS,
    ROOT,
    _development_entity,
    _ignored_output,
    _require_verified_initial_lambda,
    _run_args,
    _same_state,
    _stable_support_file,
    _summarize_seen,
    _validate_plan,
    _verify_replay_proof,
    build_plan,
    recipe,
    select,
    validate_profile,
)

PROFILE = ROOT / "configs" / "hung-proxy-calibration-v1.json"


class CalibrationTests(unittest.TestCase):
    def _authentic_select_fixture(self, device: str) -> None:
        from tests.test_hung_replay_cli import ReplayCliTests

        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            root = Path(directory)
            helper = ReplayCliTests()
            run, digest, source, target, _ = helper._inputs(root, trained_weight=0.1)
            profile = json.loads(PROFILE.read_text(encoding="utf-8"))
            profile["device"] = device
            profile["max_origins"] = 2
            profile["controller"].update(
                block_days=2, min_complete_days=1, bootstrap_segment_days=1
            )
            cell = {
                "dataset_id": "urbanev",
                "city_id": "SZH",
                "history_days": 7,
                "entity_id": "dev-1",
                "seed": 7,
                "initialization": "target_initial_adaptation",
                "input_run": str(run),
                "input_manifest_sha256": digest,
                "source_input_run": str(run),
                "source_manifest_sha256": digest,
                "source_checkpoint": str(source),
                "source_checkpoint_sha256": sha256_file(source),
                "target_checkpoint": str(target),
                "target_checkpoint_sha256": sha256_file(target),
                "drift_reference_mean": 0.0,
                "drift_reference_scale": 1.0,
            }
            code_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip()
            plan = {
                "schema": "hung-proxy-plan-v1",
                "scope": "development_only",
                "profile": profile,
                "cells": [cell],
                "code_commit": code_commit,
            }
            rows = []
            for method in METHODS:
                for index in range(4):
                    output = root / f"{method}-{index}"
                    _replay(_run_args(profile, cell, method, index, output))
                    rows.append(
                        {
                            "cell_index": 0,
                            "method": method,
                            "recipe": index,
                            "run_path": str(output),
                            "manifest_sha256": sha256_file(output / "run_manifest.json"),
                        }
                    )
            # Aggregation's full-cohort invariant has its own tests; this
            # fixture exercises all twelve authenticated artifact paths.
            with mock.patch("tools.hung_proxy_calibration._validate_plan"):
                result = select(plan, rows)
            self.assertEqual(result["matrix_runs"], 12)
            self.assertEqual(result["cells"], 1)

    def test_selector_authenticates_cpu_fixture(self) -> None:
        self._authentic_select_fixture("cpu")

    @unittest.skipUnless(torch.cuda.is_available(), "CUDA unavailable")
    def test_selector_authenticates_cuda_fixture(self) -> None:
        self._authentic_select_fixture("cuda")

    def test_state_comparison_preserves_values_across_devices(self) -> None:
        _same_state(torch.tensor([1.0]), torch.tensor([1.0]))
        if torch.cuda.is_available():
            _same_state(torch.tensor([1.0]), torch.tensor([1.0], device="cuda"))
            with self.assertRaisesRegex(ValueError, "Authenticated Development replay differs"):
                _same_state(torch.tensor([1.0]), torch.tensor([2.0], device="cuda"))

    def test_calibration_excludes_legacy_and_relabelled_target_lambda(self) -> None:
        from tests.test_hung_replay_cli import ReplayCliTests

        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            root = Path(directory)
            helper = ReplayCliTests()
            (root / "legacy").mkdir()
            (root / "trained").mkdir()
            _, _, _, legacy, _ = helper._inputs(root / "legacy")
            with self.assertRaisesRegex(ValueError, "unverified initial lambda"):
                _require_verified_initial_lambda({"target_checkpoint": str(legacy)})
            _, _, _, trained, _ = helper._inputs(root / "trained", trained_weight=0.1)
            self.assertEqual(
                _require_verified_initial_lambda({"target_checkpoint": str(trained)}), 0.1
            )
            manifest_path = trained.parent / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["retention_weight"] = 0.0
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differs from run manifest"):
                _require_verified_initial_lambda({"target_checkpoint": str(trained)})

    def test_outputs_must_be_ignored_and_inputs_stable(self) -> None:
        self.assertEqual(_ignored_output(ROOT / ".cache" / "new-run"), ROOT / ".cache" / "new-run")
        with self.assertRaisesRegex(ValueError, "Git-ignored"):
            _ignored_output(ROOT / "new-untracked-run")
        self.assertEqual(_stable_support_file(PROFILE), PROFILE)
        with self.assertRaisesRegex(ValueError, "tracked or Git-ignored"):
            _stable_support_file(ROOT / "new-untracked-cells.json")

    def test_finite_equal_grid_and_explicit_direction(self) -> None:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        validate_profile(profile)
        cell = {"drift_reference_mean": 0.3, "drift_reference_scale": 0.1}
        for method in METHODS:
            self.assertEqual(
                len({json.dumps(recipe(profile, method, i, cell)) for i in range(4)}), 4
            )
            self.assertEqual(recipe(profile, method, 0, cell)["levels_by_bin"], [0.0, 0.1, 0.2])
            self.assertEqual(recipe(profile, method, 1, cell)["levels_by_bin"], [0.2, 0.1, 0.0])
        self.assertEqual(recipe(profile, "drift", 0, cell)["drift_reference_mean"], 0.3)
        malformed = deepcopy(profile)
        malformed["seeds"] = [7, 11]
        with self.assertRaisesRegex(ValueError, "three distinct"):
            validate_profile(malformed)
        malformed = deepcopy(profile)
        malformed["thresholds"]["drift"].append([2.0, 4.0])
        with self.assertRaisesRegex(ValueError, "Exactly two"):
            validate_profile(malformed)

    def test_plan_uses_only_masked_first_development_history(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            root = Path(directory)
            cells = []
            for budget in (7, 14, 28):
                (root / f"budget-{budget}").mkdir()
                run, _ = input_run(root / f"budget-{budget}", days=3)
                forecasts_path = run / "forecasts.jsonl"
                forecasts = [json.loads(line) for line in forecasts_path.read_text().splitlines()]
                for hour, row in enumerate(forecasts[0]["x_hist"]):
                    row[0] = 0.0 if hour < 12 else 0.4
                    row[6] = 0.0 if hour < 12 else 1.0
                # Earlier Final record is an exclusion bait, never a reference.
                forecasts_path.write_text(
                    '{"role": "final", MALFORMED PRIVATE FINAL ROW\n'
                    + "".join(json.dumps(row) + "\n" for row in forecasts),
                    encoding="utf-8",
                )
                manifest_path = run / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["config"]["history_days"] = budget
                manifest["files"]["forecasts.jsonl"]["sha256"] = sha256_file(forecasts_path)
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                digest = sha256_file(manifest_path)
                for seed in (7, 11, 19):
                    source = root / f"source-{budget}-{seed}.pt"
                    target = root / f"target-{budget}-{seed}.pt"
                    source.write_bytes(f"source-{budget}-{seed}".encode())
                    target.write_bytes(f"target-{budget}-{seed}".encode())
                    cells.append(
                        {
                            "dataset_id": "urbanev",
                            "city_id": "SZH",
                            "history_days": budget,
                            "entity_id": "dev-1",
                            "seed": seed,
                            "input_run": str(run),
                            "input_manifest_sha256": digest,
                            "source_input_run": str(run),
                            "source_manifest_sha256": digest,
                            "source_checkpoint": str(source),
                            "target_checkpoint": str(target),
                        }
                    )
            cell_file = root / "cells.json"
            cell_file.write_text(
                json.dumps({"schema": "hung-proxy-cells-v1", "cells": cells}), encoding="utf-8"
            )
            plan = build_plan(PROFILE, cell_file)
            self.assertEqual(len(plan["cells"]), 9)
            self.assertAlmostEqual(plan["cells"][0]["drift_reference_mean"], 0.4)
            self.assertEqual(plan["cells"][0]["drift_reference_scale"], 0.1)
            self.assertNotEqual(plan["cells"][0]["drift_reference_mean"], 999.0)
            bad = deepcopy(cells[0])
            entities = Path(bad["input_run"]) / "entities.jsonl"
            rows = [json.loads(line) for line in entities.read_text().splitlines()]
            rows[0]["role"] = "final"
            entities.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Development entity"):
                _development_entity(Path(bad["input_run"]), manifest, bad)

    def test_replay_proof_rejects_rewritten_checkpoint_and_manifest_hash(self) -> None:
        from tests.test_hung_replay_cli import ReplayCliTests

        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            root = Path(directory)
            helper = ReplayCliTests()
            run, digest, source, target, binding = helper._inputs(root)
            args = helper._args(root, run, digest, source, target, "original", 3)
            args.selection_rule = "source_error"
            args.proxy_low, args.proxy_high = 0.1, 0.5
            args.proxy_level_low, args.proxy_level_mid, args.proxy_level_high = 0.0, 0.1, 0.2
            _replay(args)
            manifest = json.loads((args.output / "run_manifest.json").read_text(encoding="utf-8"))
            runner = load_runner(args.output / "runner_checkpoint.pt", expected_binding=binding)
            cell = {
                "dataset_id": "urbanev",
                "city_id": "SZH",
                "history_days": 7,
                "entity_id": "dev-1",
                "seed": 7,
                "input_run": str(run),
                "input_manifest_sha256": digest,
                "source_input_run": str(run),
                "source_manifest_sha256": digest,
                "source_checkpoint": str(source),
                "target_checkpoint": str(target),
                "source_checkpoint_sha256": sha256_file(source),
                "target_checkpoint_sha256": sha256_file(target),
            }
            plan = {"profile": {"max_origins": 3}}
            original_checkpoint = args.output / "runner_checkpoint.pt"
            _verify_replay_proof(plan, cell, manifest, runner, args.output, original_checkpoint)
            runner.issued[0]["forecasts"][0].add_(0.5)
            forged = root / "forged"
            forged.mkdir()
            save_runner(forged / "runner_checkpoint.pt", runner)
            shutil.copyfile(args.output / "events.jsonl", forged / "events.jsonl")
            altered = deepcopy(manifest)
            altered["final_runner_checkpoint_sha256"] = sha256_file(forged / "runner_checkpoint.pt")
            (forged / "run_manifest.json").write_text(json.dumps(altered), encoding="utf-8")
            self.assertEqual(
                altered["final_runner_checkpoint_sha256"],
                sha256_file(forged / "runner_checkpoint.pt"),
            )
            forged_runner = load_runner(forged / "runner_checkpoint.pt", expected_binding=binding)
            with self.assertRaisesRegex(ValueError, "Authenticated Development replay differs"):
                _verify_replay_proof(
                    plan, cell, altered, forged_runner, forged, forged / "runner_checkpoint.pt"
                )
            for variant in ("rng", "cost", "label"):
                forged_path = root / f"forged-{variant}"
                forged_path.mkdir()
                payload = torch.load(original_checkpoint, map_location="cpu", weights_only=True)
                altered = deepcopy(manifest)
                if variant == "rng":
                    torch.manual_seed(999)
                    payload["torch_rng"] = torch.get_rng_state().clone()
                elif variant == "cost":
                    payload["runtime_costs"]["candidate"][0]["inference_calls"] += 1
                    altered["runtime_costs"]["candidate"][0]["inference_calls"] += 1
                else:
                    scored = next(row for row in payload["issued"] if row["y_scaled"] is not None)
                    scored["y_scaled"].add_(0.5)
                checkpoint = forged_path / "runner_checkpoint.pt"
                torch.save(payload, checkpoint)
                altered["final_runner_checkpoint_sha256"] = sha256_file(checkpoint)
                (forged_path / "run_manifest.json").write_text(
                    json.dumps(altered), encoding="utf-8"
                )
                shutil.copyfile(args.output / "events.jsonl", forged_path / "events.jsonl")
                forged_runner = load_runner(checkpoint, expected_binding=binding)
                with self.assertRaisesRegex(
                    ValueError,
                    {"rng": "torch_rng", "cost": "runtime_costs", "label": "issued"}[variant],
                ):
                    _verify_replay_proof(
                        plan, cell, altered, forged_runner, forged_path, checkpoint
                    )
            forged_events = root / "forged-events"
            forged_events.mkdir()
            journal_rows = [
                json.loads(line) for line in (args.output / "events.jsonl").read_text().splitlines()
            ]
            journal_rows[1]["value"] = "forecast:forged-day"
            (forged_events / "events.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in journal_rows), encoding="utf-8"
            )
            event_manifest = deepcopy(manifest)
            event_manifest["event_journal"]["sha256"] = sha256_file(forged_events / "events.jsonl")
            authentic_runner = load_runner(
                args.output / "runner_checkpoint.pt", expected_binding=binding
            )
            with self.assertRaisesRegex(ValueError, "Event journal does not prove"):
                _verify_replay_proof(
                    plan, cell, event_manifest, authentic_runner, forged_events, original_checkpoint
                )

    def test_station_first_equal_budget_nulls_ties_and_pairing(self) -> None:
        cells = [
            {
                "dataset_id": "urbanev",
                "city_id": "SZH",
                "history_days": budget,
                "entity_id": "dev-1",
                "seed": seed,
                "initialization": "target_initial_adaptation",
            }
            for budget in (7, 14, 28)
            for seed in (7, 11, 19)
        ]
        plan = {"cells": cells, "profile": {"seeds": [7, 11, 19]}, "code_commit": "a" * 40}
        seen = {}
        for cell_index, cell in enumerate(cells):
            for method in METHODS:
                for index in range(4):
                    seen[cell_index, method, index] = {
                        "mae": float(cell["history_days"] / 7 + (index == 3)),
                        "scored": ("day-1",),
                        "coverage": {"created": 1, "scored": 1},
                        "updates": (1, 1, 1),
                        "proxy_calls": 1,
                        "runtime_costs": {
                            "candidate": [
                                {
                                    "inference_calls": 1,
                                    "inference_ns": 2,
                                    "update_steps": 1,
                                    "update_ns": 3,
                                }
                                for _ in range(3)
                            ],
                            "audit": {
                                "inference_calls": 0,
                                "inference_ns": 0,
                                "update_steps": 0,
                                "update_ns": 0,
                            },
                        },
                        "proxy_costs": {"inference_calls": 1, "inference_ns": 4},
                        "duration_seconds": 0.5,
                        "peak_rss_bytes": None,
                    }
        result = _summarize_seen(plan, seen)
        self.assertEqual(result["selection"]["drift"]["provisional_recipe"], 0)
        self.assertEqual(
            result["selection"]["drift"]["recipes"][0]["budgets"]["7"]["scored_stations"], 1
        )
        self.assertEqual(result["null_run_cells"], 0)
        self.assertEqual(
            result["selection"]["drift"]["recipes"][0]["cost_totals"]["candidate"][0][
                "update_steps"
            ],
            9,
        )
        self.assertEqual(
            result["selection"]["drift"]["recipes"][0]["cost_totals"]["proxy"]["inference_calls"], 9
        )
        self.assertEqual(
            result["selection"]["drift"]["recipes"][0]["cost_totals"]["peak_rss_missing_runs"], 9
        )
        for key in seen:
            if cells[key[0]]["history_days"] == 28:
                seen[key]["mae"] = None
        result = _summarize_seen(plan, seen)
        self.assertIsNone(result["selection"]["source_error"]["provisional_recipe"])
        self.assertEqual(result["null_run_cells"], 36)
        seen[6, "source_error", 0]["mae"] = 1.0
        with self.assertRaisesRegex(ValueError, "Partial-null"):
            _summarize_seen(plan, seen)
        seen[6, "source_error", 0]["mae"] = None
        seen[0, "source_error", 0]["updates"] = (2, 2, 2)
        with self.assertRaisesRegex(ValueError, "paired origins/update budgets"):
            _summarize_seen(plan, seen)

    def test_plan_rejects_mixed_initialization_strata(self) -> None:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        cells = [
            {
                "dataset_id": "urbanev",
                "city_id": "SZH",
                "history_days": budget,
                "entity_id": "dev-1",
                "seed": seed,
                "initialization": "target_initial_adaptation",
            }
            for budget in (7, 14, 28)
            for seed in (7, 11, 19)
        ]
        plan = {
            "schema": "hung-proxy-plan-v1",
            "scope": "development_only",
            "profile": profile,
            "cells": cells,
        }
        _validate_plan(plan)
        cells[0]["initialization"] = "source_checkpoint_only"
        with self.assertRaisesRegex(ValueError, "separate calibration plans"):
            _validate_plan(plan)
