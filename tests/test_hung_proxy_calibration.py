"""Finite-grid, Development isolation, and station-first selection checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from ev_inputs.hourly_reader import sha256_file
from tests.test_hung_replay_inputs import input_run
from tools.hung_proxy_calibration import (
    METHODS,
    ROOT,
    _development_entity,
    _summarize_seen,
    _validate_plan,
    build_plan,
    recipe,
    validate_profile,
)

PROFILE = ROOT / "configs" / "hung-proxy-calibration-v1.json"


class CalibrationTests(unittest.TestCase):
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
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
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
                final = deepcopy(forecasts[0])
                final["role"] = "final"
                final["origin"] = "2020-01-01T00:00:00+08:00"
                final["x_hist"] = [[999.0, 0, 0, 0, 0, 0, 1.0]] * 24
                forecasts_path.write_text(
                    "".join(json.dumps(row) + "\n" for row in [final, *forecasts]),
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
