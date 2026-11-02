"""Compare saved Development Main decisions under pinned controller conventions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import torch

from experiments.supporting_pipeline.controller import ControllerConfig as HungConfig
from experiments.supporting_pipeline.controller import DailyScore as HungDay
from experiments.supporting_pipeline.controller import decide_block as hung_decide

ROOT = Path(__file__).resolve().parents[1]
TERMINAL = ROOT / ".cache/block7-terminal-checkpoint-import-v1"
IMPORT = ROOT / "docs/reports/hung-block7-terminal-checkpoint-import-20261030-v1.json"
IMPORT_SHA = "009fce2052b69bae7dde12d80b1d9e7cec28459d6f5531ce17ad76c489f535f5"
NUMERIC = ROOT / "docs/reports/hung-block7-terminal-numeric-audit-20261030-v3.json"
NUMERIC_SHA = "f9d4ff3da1a0185ad82af8bf9de5c07923d9798f119e45269e1fd67abf7f9a4b"
PAIRS = ROOT / "docs/reports/hung-block7-manifest-pairs-20261028.csv"
PAIRS_SHA = "e260de421d6c53ef3dffe5901f9e3478708b9e578791d3f370588a0a508699de"
HUNG_CONTROLLER = ROOT / "experiments/supporting_pipeline/controller.py"
HUNG_SHA = "b97f49e6895d132b5d535a05d1941dc64893f0706537d82c810ca569ced94876"
Q_ROOT = ROOT / ".cache/parity-q-20261027-v1"
Q_CONTROLLER = Q_ROOT / "ev_control/confidence.py"
Q_SHA = "27b8d7709fc07442cc4461082e4d6599108ed70591f4398c5c5cc062980c7174"
Q_RUN = Q_ROOT / "ev_runner/run.py"
Q_RUN_SHA = "1cd7ef9732419d3c18399dff140cde4034a44914b0345f57232a85f0a574bff3"
DEPLOYMENT = datetime.fromisoformat("2022-12-01T00:00:00+08:00")


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _pinned_q_controller():
    if _sha(Q_CONTROLLER) != Q_SHA or _sha(Q_RUN) != Q_RUN_SHA:
        raise ValueError("Pinned Qyroven controller or stream contract changed")
    name = "_pinned_q_controller_sensitivity_v1"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Q_CONTROLLER)
    if spec is None or spec.loader is None:
        raise ValueError("Pinned Qyroven controller cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _fixed_draw_means(
    rows: list[dict], *, active_index: int, challengers: list[int], config: dict, block_id: int
) -> tuple[list[float], list[float]]:
    """Reproduce Hùng's paired draws; leave only the final quantile convention variable."""
    n = len(rows)
    improvements = [
        [row["normalized_mae"][active_index] - row["normalized_mae"][index] for row in rows]
        for index in challengers
    ]
    seed = int.from_bytes(hashlib.sha256(f"{config['seed']}:{block_id}".encode()).digest(), "big")
    rng = random.Random(seed)
    means: tuple[list[float], list[float]] = ([], [])
    for _ in range(config["bootstrap_resamples"]):
        indices: list[int] = []
        while len(indices) < n:
            start = rng.randrange(n - config["bootstrap_segment_days"] + 1)
            indices.extend(range(start, start + config["bootstrap_segment_days"]))
        indices = indices[:n]
        for values, samples in zip(improvements, means, strict=True):
            samples.append(sum(values[index] for index in indices) / n)
    return means


def _check_saved_hung_decision(state: dict, block_id: int, rows: list[dict]) -> dict:
    config = HungConfig(**state["controller"])
    saved = state["decisions"][block_id]
    days = [HungDay(row["day_id"], True, True, tuple(row["normalized_mae"])) for row in rows]
    reproduced = hung_decide(
        config, current_level=saved["current_level"], block_id=block_id, days=days
    )
    if (
        reproduced.valid_days != saved["valid_days"]
        or reproduced.selected_level != saved["selected_level"]
        or reproduced.reason != saved["reason"]
        or any(
            (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-12)
            for a, b in zip(reproduced.lower_bounds, saved["lower_bounds"], strict=True)
        )
    ):
        raise ValueError("Saved Hùng decision does not reproduce from terminal scores")
    return saved


def _decision_row(state: dict, run_id: str, block_id: int, q_module) -> dict:
    saved = state["decisions"][block_id]
    rows = sorted(
        (
            row
            for row in state["issued"]
            if row["block_id"] == block_id and row["normalized_mae"] is not None
        ),
        key=lambda row: row["day_id"],
    )
    saved = _check_saved_hung_decision(state, block_id, rows)
    config = state["controller"]
    levels = tuple(config["levels"])
    active = saved["current_level"]
    active_index = levels.index(active)
    challengers = [index for index in range(3) if index != active_index]
    fixed_draw_selected = active
    fixed_draw_bounds: list[float | None] = [None, None, None]
    if len(rows) >= config["min_complete_days"]:
        means = _fixed_draw_means(
            rows,
            active_index=active_index,
            challengers=challengers,
            config=config,
            block_id=block_id,
        )
        comparisons = []
        for index, samples in zip(challengers, means, strict=True):
            order_position = max(0, math.ceil(config["alpha"] / 2 * len(samples)) - 1)
            if abs(sorted(samples)[order_position] - saved["lower_bounds"][index]) > 1e-12:
                raise ValueError("Pinned Hùng bootstrap draws do not match saved LCB")
            bound = q_module.linear_quantile(samples, config["alpha"] / 2)
            fixed_draw_bounds[index] = bound
            comparisons.append(
                q_module.Comparison(levels[index], 0.0, bound, bound > config["delta"])
            )
        fixed_draw_selected = q_module.choose_level(active, levels, comparisons)

    binding = state["binding"]
    stream = (
        f"{(binding['dataset_id'], binding['city_id'])}/{binding['entity_id']}/"
        f"{binding['history_days']}d/seed{config['seed']}"
    )
    q_config = q_module.ControllerConfig(
        lambda_low=levels[1],
        lambda_high=levels[2],
        initial_lambda=config["initial_level"],
        block_days=config["block_days"],
        min_valid_days=config["min_complete_days"],
        delta=config["delta"],
        alpha=config["alpha"],
        segment_days=config["bootstrap_segment_days"],
        resamples=config["bootstrap_resamples"],
        seed=config["seed"],
    )
    block_start = DEPLOYMENT + timedelta(days=block_id * config["block_days"])
    block_end = block_start + timedelta(days=config["block_days"])
    q_rows = []
    for row in rows:
        origin = datetime.fromisoformat(row["day_id"])
        if not block_start <= origin < block_end or origin + timedelta(days=1) > block_end:
            raise ValueError("Scored Development day is outside its decision boundary")
        q_rows.append(
            q_module.DailyScore(
                origin,
                origin,
                origin + timedelta(days=1),
                24,
                tuple(row["normalized_mae"]),
                binding["scale_id"],
                tuple(f"{run_id}/{row['day_id']}/{index}" for index in range(3)),
            )
        )
    q_decision = q_module.decide(
        q_rows,
        config=q_config,
        active_lambda=active,
        block_start=block_start,
        as_of=block_end,
        stream_id=stream,
        scale_id=binding["scale_id"],
    )
    if q_decision.valid_days != saved["valid_days"]:
        raise ValueError("Qyroven and Hùng valid-day sets differ")
    return {
        "run_id": run_id,
        "block_id": block_id,
        "valid_days": len(rows),
        "current_level": active,
        "saved_hung_selected": saved["selected_level"],
        "fixed_draw_q_quantile_selected": fixed_draw_selected,
        "full_q_rule_selected": q_decision.selected_lambda,
        "saved_hung_lcb": saved["lower_bounds"],
        "fixed_draw_q_quantile_lcb": fixed_draw_bounds,
        "full_q_rule_lcb": {
            str(comparison.challenger): comparison.lcb for comparison in q_decision.comparisons
        },
    }


def audit() -> dict:
    pins = {IMPORT: IMPORT_SHA, NUMERIC: NUMERIC_SHA, PAIRS: PAIRS_SHA, HUNG_CONTROLLER: HUNG_SHA}
    if any(_sha(path) != expected for path, expected in pins.items()):
        raise ValueError("Pinned Development decision evidence or controller changed")
    q_module = _pinned_q_controller()
    imported = json.loads(IMPORT.read_text(encoding="utf-8"))
    numeric = json.loads(NUMERIC.read_text(encoding="utf-8"))
    if imported["checked"] != 138 or numeric["pair_count"] != 69:
        raise ValueError("Pinned terminal evidence is incomplete")
    by_id = {row["run_id"]: row for row in imported["details"]}
    if len(by_id) != 138:
        raise ValueError("Duplicate terminal run identity")
    with PAIRS.open(newline="", encoding="utf-8") as stream:
        pairs = list(csv.DictReader(stream))
    run_ids = [row["main_run_id"] for row in pairs]
    if (
        len(pairs) != 69
        or len(set(run_ids)) != 69
        or set(run_ids) != {run_id for run_id in by_id if run_id.startswith("main_")}
    ):
        raise ValueError("Historical Main jobset differs")
    decision_rows = []
    for run_id in sorted(run_ids):
        meta = by_id[run_id]
        checkpoint = TERMINAL / f"{run_id}.pt"
        manifest_path = ROOT / ".cache/block7-review-v1/manifests" / f"{run_id}.json"
        if (
            checkpoint.is_symlink()
            or manifest_path.is_symlink()
            or _sha(checkpoint) != meta["sha256"]
            or _sha(manifest_path) != meta["saved_manifest_sha256"]
        ):
            raise ValueError(f"Main checkpoint or manifest SHA differs: {run_id}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if (
            state["binding"] != manifest["input_binding"]
            or json.loads(json.dumps(state["controller"])) != manifest["config"]["controller"]
            or state["selection_rule"] != "confidence"
            or state["next_index"] != 90
            or len(state["decisions"]) != 6
        ):
            raise ValueError(f"Main state/config differs: {run_id}")
        decision_rows.extend(
            _decision_row(state, run_id, block_id, q_module)
            for block_id in range(len(state["decisions"]))
        )
    if len(decision_rows) != 414:
        raise ValueError("Historical Main decision inventory differs")
    bootstrap_rows = [row for row in decision_rows if row["valid_days"] >= 5]
    fixed_changed = [
        row
        for row in bootstrap_rows
        if row["fixed_draw_q_quantile_selected"] != row["saved_hung_selected"]
    ]
    full_changed = [
        row for row in bootstrap_rows if row["full_q_rule_selected"] != row["saved_hung_selected"]
    ]
    return {
        "schema": "hung-q-controller-decision-sensitivity-v1",
        "scope": "historical Main Development decisions; one-boundary score-conditional sensitivity, no policy replay or Final outcome",
        "terminal_import_sha256": IMPORT_SHA,
        "numeric_audit_sha256": NUMERIC_SHA,
        "pair_csv_sha256": PAIRS_SHA,
        "hung_controller_sha256": HUNG_SHA,
        "qyroven_controller_sha256": Q_SHA,
        "qyroven_stream_source_sha256": Q_RUN_SHA,
        "historical_main_runs": len(run_ids),
        "saved_decisions_reproduced": len(decision_rows),
        "bootstrap_eligible_decisions": len(bootstrap_rows),
        "fixed_draw_quantile_only_changed": len(fixed_changed),
        "full_q_rule_changed": len(full_changed),
        "fixed_draw_changed_cells": [
            {
                key: row[key]
                for key in (
                    "run_id",
                    "block_id",
                    "saved_hung_selected",
                    "fixed_draw_q_quantile_selected",
                )
            }
            for row in fixed_changed
        ],
        "full_q_changed_cells": [
            {
                key: row[key]
                for key in ("run_id", "block_id", "saved_hung_selected", "full_q_rule_selected")
            }
            for row in full_changed
        ],
        "decisions": decision_rows,
        "disposition": "COUNTERFACTUAL_RULE_SENSITIVITY_NOT_EXECUTED_POLICY_OR_PARITY_ACCEPTANCE",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT.resolve()) or output.exists() or output.is_symlink():
        raise ValueError("Output must be a new repository path")
    result = audit()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"output": str(output), "sha256": _sha(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
