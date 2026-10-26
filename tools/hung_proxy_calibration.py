"""Finite, manifest-bound Hung proxy calibration on Development only.

``plan`` validates an explicit paired cell list; ``run`` executes every declared
recipe in a new directory; ``select`` verifies complete outputs and computes a
station-first, equal-budget conditional Development choice. Nothing reads Final.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from argparse import Namespace
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.checkpoint import load_runner
from experiments.hung_sprint2.cli import _load_run, _replay
from experiments.hung_sprint2.controller import ControllerConfig
from experiments.hung_sprint2.evaluation import evaluate_replay
from experiments.hung_sprint2.proxy_selection import ProxyConfig
from experiments.hung_sprint2.replay_inputs import ReplaySummary, _target_forecasts, replay_target
from experiments.hung_sprint2.retention import frozen_source_reference
from experiments.hung_sprint2.runner import PrequentialRunner
from experiments.hung_sprint2.training import load_checkpoint

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1] if ROOT.parent.name == ".cache" else ROOT
METHODS = ("source_error", "uncertainty", "drift")
BUDGETS = (7, 14, 28)


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def _sha(value: str) -> bool:
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def _within_project(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(PROJECT_ROOT):
        raise ValueError("Calibration paths must stay inside the project")
    return resolved


def _ignored_output(path: Path) -> Path:
    resolved = _within_project(path)
    if (
        not resolved.is_relative_to(ROOT)
        or subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", str(resolved)],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError("Calibration output must be a Git-ignored path inside this worktree")
    return resolved


def _stable_support_file(path: Path) -> Path:
    resolved = _within_project(path)
    if not resolved.is_relative_to(ROOT):
        raise ValueError("Plan/profile/cell files must stay inside this worktree")
    tracked = (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(resolved)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )
    ignored = (
        subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", str(resolved)],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0
    )
    if not (tracked or ignored):
        raise ValueError("Plan/profile/cell input must be tracked or Git-ignored")
    return resolved


def validate_profile(profile: dict) -> None:
    """Require an equal, finite four-recipe search and at least three seeds."""
    if (
        profile.get("schema") != "hung-proxy-calibration-v1"
        or profile.get("scope") != "development_only"
        or profile.get("methods") != list(METHODS)
        or profile.get("history_days") != list(BUDGETS)
        or profile.get("recipes_per_method") != 4
        or profile.get("mapping_orders") != ["ascending", "descending"]
        or profile.get("selection_rule") != "equal_budget_station_seed_mae_kwh_then_recipe_index"
    ):
        raise ValueError("Unsupported finite Development profile")
    seeds = profile.get("seeds")
    if (
        not isinstance(seeds, list)
        or len(seeds) < 3
        or len(set(seeds)) != len(seeds)
        or any(type(seed) is not int or seed < 0 for seed in seeds)
    ):
        raise ValueError("At least three distinct nonnegative seeds are required")
    if type(profile.get("max_origins")) is not int or profile["max_origins"] <= 0:
        raise ValueError("Positive bounded origin count required")
    if profile.get("device") not in {"cpu", "cuda"}:
        raise ValueError("Calibration device must be CPU or CUDA")
    floor = profile.get("drift_scale_floor")
    if type(floor) not in (int, float) or not math.isfinite(floor) or floor <= 0:
        raise ValueError("Positive finite drift scale floor required")
    thresholds = profile.get("thresholds")
    if not isinstance(thresholds, dict) or set(thresholds) != set(METHODS):
        raise ValueError("Every proxy requires exactly two threshold pairs")
    controller = profile.get("controller")
    if not isinstance(controller, dict) or set(controller) != {
        "level_one",
        "level_two",
        "initial_level",
        "block_days",
        "min_complete_days",
        "delta",
        "alpha",
        "bootstrap_segment_days",
        "bootstrap_resamples",
        "challenger_rule",
        "epsilon",
    }:
        raise ValueError("Controller template is incomplete")
    for seed in seeds:
        configured = ControllerConfig(
            levels=(0.0, controller["level_one"], controller["level_two"]),
            initial_level=controller["initial_level"],
            block_days=controller["block_days"],
            min_complete_days=controller["min_complete_days"],
            delta=controller["delta"],
            alpha=controller["alpha"],
            bootstrap_segment_days=controller["bootstrap_segment_days"],
            bootstrap_resamples=controller["bootstrap_resamples"],
            seed=seed,
            challenger_rule=controller["challenger_rule"],
        )
    if not 0 < controller["epsilon"] < float("inf"):
        raise ValueError("Positive finite epsilon required")
    for method, pairs in thresholds.items():
        if not isinstance(pairs, list) or len(pairs) != 2:
            raise ValueError("Exactly two threshold pairs per method required")
        for low, high in pairs:
            reference = (0.0, 1.0) if method == "drift" else (None, None)
            ProxyConfig(low, high, configured.levels, *reference).validate(configured, method)


def recipe(profile: dict, method: str, index: int, cell: dict) -> dict:
    """Translate recipe index to a fully explicit runner proxy configuration."""
    validate_profile(profile)
    if method not in METHODS or type(index) is not int or index not in range(4):
        raise ValueError("Unknown proxy recipe")
    low, high = profile["thresholds"][method][index // 2]
    levels = (0.0, profile["controller"]["level_one"], profile["controller"]["level_two"])
    if index % 2:
        levels = tuple(reversed(levels))
    result = {"low": low, "high": high, "levels_by_bin": list(levels)}
    if method == "drift":
        result.update(
            drift_reference_mean=cell["drift_reference_mean"],
            drift_reference_scale=cell["drift_reference_scale"],
        )
    return result


def _development_entity(input_run: Path, manifest: dict, cell: dict) -> None:
    identities = []
    with (input_run / "entities.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("identity") == [cell["dataset_id"], cell["city_id"], cell["entity_id"]]:
                identities.append(row)
    if (
        len(identities) != 1
        or identities[0].get("role") != "development"
        or identities[0].get("initialization")
        not in {"target_initial_adaptation", "source_checkpoint_only"}
        or manifest["config"]["history_days"] != cell["history_days"]
        or manifest["config"]["dataset_id"] != cell["dataset_id"]
        or manifest["config"]["city_id"] != cell["city_id"]
    ):
        raise ValueError("Cell is not a unique trainable Development entity/budget")


def _drift_reference(input_run: Path, cell: dict, floor: float) -> tuple[float, float, str]:
    """Use the first issued Development history, never a future label."""
    identity = [cell["dataset_id"], cell["city_id"], cell["entity_id"]]
    first: dict | None = None
    for row in _target_forecasts(input_run / "forecasts.jsonl", identity):
        if first is None or row["origin"] < first["origin"]:
            first = row
    if first is None:
        raise ValueError("Drift reference requires a created Development origin")
    values = [
        hour[0]
        for hour in first["x_hist"]
        if len(hour) == 7 and hour[6] == 1 and math.isfinite(hour[0])
    ]
    if not values:
        raise ValueError("First Development origin lacks available historical load")
    mean = math.fsum(values) / len(values)
    variance = math.fsum((value - mean) ** 2 for value in values) / len(values)
    return mean, max(math.sqrt(variance), floor), first["origin"]


def build_plan(profile_path: Path, cells_path: Path) -> dict:
    profile_path, cells_path = _stable_support_file(profile_path), _stable_support_file(cells_path)
    profile = _json(profile_path)
    validate_profile(profile)
    cells_document = _json(cells_path)
    if cells_document.get("schema") != "hung-proxy-cells-v1":
        raise ValueError("Unexpected cell-list schema")
    cells = cells_document.get("cells")
    if not isinstance(cells, list) or not cells:
        raise ValueError("Nonempty Development cell list required")
    enriched = []
    keys = set()
    by_group: dict[tuple, set[int]] = defaultdict(set)
    for cell in cells:
        required = {
            "dataset_id",
            "city_id",
            "history_days",
            "entity_id",
            "seed",
            "input_run",
            "input_manifest_sha256",
            "source_input_run",
            "source_manifest_sha256",
            "source_checkpoint",
            "target_checkpoint",
        }
        if not isinstance(cell, dict) or set(cell) != required:
            raise ValueError("Cell identity/path fields mismatch")
        if cell["history_days"] not in BUDGETS or cell["seed"] not in profile["seeds"]:
            raise ValueError("Cell budget/seed outside declared grid")
        key = (
            cell["dataset_id"],
            cell["city_id"],
            cell["history_days"],
            cell["entity_id"],
            cell["seed"],
        )
        if key in keys:
            raise ValueError("Duplicate Development cell")
        keys.add(key)
        by_group[key[:-1]].add(cell["seed"])
        input_run = _within_project(Path(cell["input_run"]))
        source_run = _within_project(Path(cell["source_input_run"]))
        manifest = _load_run(input_run, cell["input_manifest_sha256"])
        source_manifest = _load_run(source_run, cell["source_manifest_sha256"])
        _development_entity(input_run, manifest, cell)
        if (source_manifest["config"]["dataset_id"], source_manifest["config"]["city_id"]) != key[
            :2
        ]:
            raise ValueError("Source identity differs from Development cell")
        checkpoint_hashes = {}
        checkpoint_paths = {}
        for name in ("source_checkpoint", "target_checkpoint"):
            checkpoint_paths[name] = _within_project(Path(cell[name]))
            checkpoint_hashes[f"{name}_sha256"] = sha256_file(checkpoint_paths[name])
        mean, scale, origin = _drift_reference(input_run, cell, profile["drift_scale_floor"])
        enriched.append(
            {
                **cell,
                "input_run": str(input_run),
                "source_input_run": str(source_run),
                **{name: str(path) for name, path in checkpoint_paths.items()},
                **checkpoint_hashes,
                "drift_reference_mean": mean,
                "drift_reference_scale": scale,
                "drift_reference_origin": origin,
                "initialization": next(
                    json.loads(line)["initialization"]
                    for line in (input_run / "entities.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                    if json.loads(line).get("identity") == [*key[:2], cell["entity_id"]]
                ),
            }
        )
    if {group[2] for group in by_group} != set(BUDGETS):
        raise ValueError("All 7/14/28-day Development budgets required")
    if any(seeds != set(profile["seeds"]) for seeds in by_group.values()):
        raise ValueError("Every Development entity/budget needs the same declared seeds")
    code = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    plan = {
        "schema": "hung-proxy-plan-v1",
        "scope": "development_only",
        "profile": profile,
        "profile_sha256": sha256_file(profile_path),
        "cells_sha256": sha256_file(cells_path),
        "code_commit": code,
        "driver_sha256": sha256_file(Path(__file__)),
        "cells": enriched,
    }
    _validate_plan(plan)
    return plan


def _cell_key(cell: dict) -> tuple:
    return (
        cell["dataset_id"],
        cell["city_id"],
        cell["history_days"],
        cell["entity_id"],
        cell["seed"],
    )


def _validate_plan(plan: dict) -> None:
    if plan.get("schema") != "hung-proxy-plan-v1" or plan.get("scope") != "development_only":
        raise ValueError("Unexpected Development plan")
    validate_profile(plan["profile"])
    cells = plan["cells"]
    keys = [_cell_key(cell) for cell in cells]
    if len(keys) != len(set(keys)) or not cells:
        raise ValueError("Duplicate or empty plan cells")
    groups: dict[tuple, set[int]] = defaultdict(set)
    strata = set()
    for cell in cells:
        groups[_cell_key(cell)[:-1]].add(cell["seed"])
        strata.add((cell["dataset_id"], cell["city_id"], cell["initialization"]))
        if cell["initialization"] not in {"target_initial_adaptation", "source_checkpoint_only"}:
            raise ValueError("Plan cell is not trainable Development")
    if len(strata) != 1:
        raise ValueError(
            "Use separate calibration plans for each dataset/city/initialization stratum"
        )
    if {key[2] for key in groups} != set(BUDGETS) or any(
        seeds != set(plan["profile"]["seeds"]) for seeds in groups.values()
    ):
        raise ValueError("Plan lacks a full paired seed/budget grid")


def _run_args(profile: dict, cell: dict, method: str, index: int, output: Path) -> Namespace:
    policy = recipe(profile, method, index, cell)
    controller = profile["controller"]
    return Namespace(
        input_run=Path(cell["input_run"]),
        manifest_sha256=cell["input_manifest_sha256"],
        source_input_run=Path(cell["source_input_run"]),
        source_manifest_sha256=cell["source_manifest_sha256"],
        source_checkpoint=Path(cell["source_checkpoint"]),
        target_checkpoint=Path(cell["target_checkpoint"]),
        entity_id=cell["entity_id"],
        output=output,
        max_origins=profile["max_origins"],
        seed=cell["seed"],
        selection_rule=method,
        device=profile["device"],
        resume_checkpoint=None,
        proxy_low=policy["low"],
        proxy_high=policy["high"],
        proxy_level_low=policy["levels_by_bin"][0],
        proxy_level_mid=policy["levels_by_bin"][1],
        proxy_level_high=policy["levels_by_bin"][2],
        drift_reference_mean=policy.get("drift_reference_mean"),
        drift_reference_scale=policy.get("drift_reference_scale"),
        **controller,
    )


def execute(plan_path: Path, expected_sha256: str, output: Path) -> None:
    """Run all twelve recipes per paired cell, preserving any partial output."""
    plan_path = _stable_support_file(plan_path)
    if sha256_file(plan_path) != expected_sha256:
        raise ValueError("Plan SHA-256 mismatch")
    plan = _json(plan_path)
    _validate_plan(plan)
    output = _ignored_output(output)
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    if (
        current != plan["code_commit"]
        or dirty
        or sha256_file(Path(__file__)) != plan["driver_sha256"]
    ):
        raise ValueError("Calibration code must match a clean pinned commit")
    for cell in plan["cells"]:
        input_run = _within_project(Path(cell["input_run"]))
        source_run = _within_project(Path(cell["source_input_run"]))
        for protected in (
            input_run,
            source_run,
            *(
                _within_project(Path(cell[name])).parent
                for name in ("source_checkpoint", "target_checkpoint")
            ),
        ):
            if output.is_relative_to(protected):
                raise ValueError("Calibration output cannot be inside an input/checkpoint run")
        manifest = _load_run(input_run, cell["input_manifest_sha256"])
        _load_run(source_run, cell["source_manifest_sha256"])
        _development_entity(input_run, manifest, cell)
        for name in ("source_checkpoint", "target_checkpoint"):
            if sha256_file(_within_project(Path(cell[name]))) != cell[f"{name}_sha256"]:
                raise ValueError("Changed Source/target checkpoint")
        reference = _drift_reference(input_run, cell, plan["profile"]["drift_scale_floor"])
        if reference != (
            cell["drift_reference_mean"],
            cell["drift_reference_scale"],
            cell["drift_reference_origin"],
        ):
            raise ValueError("Changed causal drift reference")
    output.mkdir(parents=True, exist_ok=False)
    (output / "plan.json").write_bytes(plan_path.read_bytes())
    with (output / "runs.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for cell_index, cell in enumerate(plan["cells"]):
            for method in METHODS:
                for index in range(4):
                    run_path = output / f"cell-{cell_index:04d}" / f"{method}-{index}"
                    summary = _replay(_run_args(plan["profile"], cell, method, index, run_path))
                    if summary["status"] != "completed":
                        raise ValueError("Replay did not complete")
                    record = {
                        "cell_index": cell_index,
                        "method": method,
                        "recipe": index,
                        "run_path": str(run_path),
                        "manifest_sha256": sha256_file(run_path / "run_manifest.json"),
                    }
                    stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())


def _same_state(left, right, field: str = "state") -> None:
    if isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor):
        if not torch.equal(left.detach().cpu(), right.detach().cpu()):
            raise ValueError(f"Authenticated Development replay differs: {field}")
    elif isinstance(left, dict) and isinstance(right, dict):
        if left.keys() != right.keys():
            raise ValueError(f"Authenticated Development replay differs: {field}")
        for key in left:
            _same_state(left[key], right[key], f"{field}.{key}")
    elif isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        if len(left) != len(right):
            raise ValueError(f"Authenticated Development replay differs: {field}")
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            _same_state(a, b, f"{field}.{index}")
    elif left != right:
        raise ValueError(f"Authenticated Development replay differs: {field}")


def _verify_event_journal(path: Path, manifest: dict, events: list[str]) -> None:
    evidence = manifest["event_journal"]
    journal = path / evidence["file"]
    if evidence["file"] != "events.jsonl" or sha256_file(journal) != evidence["sha256"]:
        raise ValueError("Event journal SHA-256 mismatch")
    with journal.open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream]
    if (
        not rows
        or rows[0]
        != {
            "schema": "hung-sprint2-event-journal-v1",
            "kind": "header",
            "run_id": manifest["run_id"],
            "input_binding": manifest["input_binding"],
            "resumed_from": None,
            "start_event_index": 0,
        }
        or evidence["start_event_index"] != 0
        or evidence["end_event_index"] != len(events)
        or evidence["events_written"] != len(events)
        or rows[1:]
        != [
            {"kind": "event", "event_index": index, "value": event}
            for index, event in enumerate(events)
        ]
    ):
        raise ValueError("Event journal does not prove the replay event sequence")


def _verify_replay_proof(
    plan: dict,
    cell: dict,
    manifest: dict,
    saved: PrequentialRunner,
    path: Path,
    checkpoint: Path,
) -> None:
    """Re-execute authenticated Development chronology before trusting a score."""
    config = manifest["config"]
    device = config["device"]
    input_run = _within_project(Path(cell["input_run"]))
    source_run = _within_project(Path(cell["source_input_run"]))
    target_manifest = _load_run(input_run, cell["input_manifest_sha256"])
    _load_run(source_run, cell["source_manifest_sha256"])
    _development_entity(input_run, target_manifest, cell)
    source_binding = manifest["source_input_binding"]
    if (
        source_binding.get("stage") != "source"
        or source_binding.get("input_manifest_sha256") != cell["source_manifest_sha256"]
        or (source_binding.get("dataset_id"), source_binding.get("city_id"))
        != (cell["dataset_id"], cell["city_id"])
        or manifest["input_binding"].get("source_checkpoint_sha256")
        != cell["source_checkpoint_sha256"]
    ):
        raise ValueError("Development Source/target input bindings differ")
    for name in ("source_checkpoint", "target_checkpoint"):
        if sha256_file(_within_project(Path(cell[name]))) != cell[f"{name}_sha256"]:
            raise ValueError("Development replay input checkpoint changed")
    source_model, _, source_scale, _ = load_checkpoint(
        Path(cell["source_checkpoint"]),
        expected_binding=manifest["source_input_binding"],
        map_location=device,
    )
    target_model, optimizer, target_scale, _ = load_checkpoint(
        Path(cell["target_checkpoint"]),
        expected_binding=manifest["input_binding"],
        map_location=device,
    )
    if source_scale is None or target_scale is None or not torch.equal(source_scale, target_scale):
        raise ValueError("Development Source/target latent scales differ")
    controller = dict(config["controller"])
    controller["levels"] = tuple(controller["levels"])
    proxy = dict(config["proxy_config"])
    proxy["levels_by_bin"] = tuple(proxy["levels_by_bin"])
    torch.manual_seed(config["seed"])
    fresh = PrequentialRunner(
        target_model,
        optimizer,
        frozen_source_reference(source_model),
        source_scale,
        binding=manifest["input_binding"],
        controller=ControllerConfig(**controller),
        epsilon=config["epsilon"],
        energy_scale=saved.energy_scale,
        selection_rule=config["selection_rule"],
        proxy_config=ProxyConfig(**proxy),
    )
    summary = replay_target(
        input_run,
        manifest_sha256=cell["input_manifest_sha256"],
        entity_id=cell["entity_id"],
        runner=fresh,
        max_origins=plan["profile"]["max_origins"],
    )
    if asdict(evaluate_replay(fresh, summary).coverage) != manifest["coverage"]:
        raise ValueError("Authenticated Development coverage differs")
    # state_dict() samples the *current global* RNG. Read the persisted bytes
    # instead: replay_target above has already advanced that global stream.
    original = torch.load(checkpoint, map_location="cpu", weights_only=True)
    replayed = fresh.state_dict()
    for field in (
        "issued",
        "decisions",
        "events",
        "update_steps",
        "audit_steps",
        "current_level",
        "next_index",
        "block_id",
        "days",
        "pending",
        "late_pending",
        "active",
        "candidates",
        "audit",
        "torch_rng",
        "audit_rng",
        "cuda_rng",
        "audit_cuda_rng",
    ):
        _same_state(original[field], replayed[field], field)
    for category in ("candidate", "audit"):
        prior = original["runtime_costs"][category]
        actual = replayed["runtime_costs"][category]
        pairs = zip(prior, actual, strict=True) if category == "candidate" else [(prior, actual)]
        for old, new in pairs:
            for counter in ("inference_calls", "update_steps"):
                _same_state(old[counter], new[counter], f"runtime_costs.{category}.{counter}")
    for counter in ("inference_calls", "update_steps"):
        _same_state(
            original["proxy_costs"][counter],
            replayed["proxy_costs"][counter],
            f"proxy_costs.{counter}",
        )
    _verify_event_journal(path, manifest, fresh.events)


def select(plan: dict, records: list[dict]) -> dict:
    """Authenticate every run and choose each method with station-first MAE."""
    _validate_plan(plan)
    expected = {
        (cell_index, method, recipe_index)
        for cell_index in range(len(plan["cells"]))
        for method in METHODS
        for recipe_index in range(4)
    }
    seen: dict[tuple, dict] = {}
    for record in records:
        key = (record.get("cell_index"), record.get("method"), record.get("recipe"))
        if key not in expected or key in seen or not _sha(record.get("manifest_sha256")):
            raise ValueError("Missing, duplicate, or unexpected calibration run")
        path = _within_project(Path(record["run_path"]))
        if sha256_file(path / "run_manifest.json") != record["manifest_sha256"]:
            raise ValueError("Run manifest SHA-256 mismatch")
        manifest = _json(path / "run_manifest.json")
        cell = plan["cells"][key[0]]
        policy = recipe(plan["profile"], key[1], key[2], cell)
        config = manifest.get("config", {})
        expected_controller = {
            **{
                name: value
                for name, value in plan["profile"]["controller"].items()
                if name not in {"level_one", "level_two", "epsilon"}
            },
            "levels": [
                0.0,
                plan["profile"]["controller"]["level_one"],
                plan["profile"]["controller"]["level_two"],
            ],
            "seed": cell["seed"],
        }
        if (
            manifest.get("schema") != "hung-sprint2-development-replay-v1"
            or manifest.get("status") != "completed"
            or manifest.get("code", {}).get("commit") != plan["code_commit"]
            or manifest.get("code", {}).get("worktree_status")
            or manifest.get("input_binding", {}).get("stage") != "target"
            or manifest.get("input_binding", {}).get("entity_id") != cell["entity_id"]
            or manifest.get("input_binding", {}).get("history_days") != cell["history_days"]
            or manifest.get("input_binding", {}).get("input_manifest_sha256")
            != cell["input_manifest_sha256"]
            or manifest.get("source_checkpoint_sha256") != cell["source_checkpoint_sha256"]
            or manifest.get("target_checkpoint_sha256") != cell["target_checkpoint_sha256"]
            or config.get("seed") != cell["seed"]
            or config.get("controller") != expected_controller
            or config.get("epsilon") != plan["profile"]["controller"]["epsilon"]
            or config.get("device") != plan["profile"]["device"]
            or config.get("selection_rule") != key[1]
            or config.get("proxy_config")
            != {
                **policy,
                "drift_reference_mean": policy.get("drift_reference_mean"),
                "drift_reference_scale": policy.get("drift_reference_scale"),
            }
            or config.get("max_origins") != plan["profile"]["max_origins"]
            or manifest.get("runner_cursor") != plan["profile"]["max_origins"]
        ):
            raise ValueError("Calibration run identity/config mismatch")
        checkpoint = path / "runner_checkpoint.pt"
        if sha256_file(checkpoint) != manifest["final_runner_checkpoint_sha256"]:
            raise ValueError("Runner checkpoint SHA-256 mismatch")
        runner = load_runner(
            checkpoint, expected_binding=manifest["input_binding"], device=config["device"]
        )
        _verify_replay_proof(plan, cell, manifest, runner, path, checkpoint)
        scored = tuple(item["day_id"] for item in runner.issued if item["y_scaled"] is not None)
        coverage = manifest["coverage"]
        recomputed = evaluate_replay(
            runner,
            ReplaySummary(
                coverage["requested"],
                coverage["created"],
                coverage["skipped_all_missing_history"],
                coverage["skipped_undefined_scale"],
                coverage["scored"],
                coverage["unscored_created"],
            ),
        )
        recomputed_metrics = {
            "live": None if recomputed.live is None else asdict(recomputed.live),
            "candidates": [
                None if item is None else asdict(item) for item in recomputed.candidates
            ],
            "audit": None if recomputed.audit is None else asdict(recomputed.audit),
            "audit_scored_days": recomputed.audit_scored_days,
        }
        expected_proxy = ProxyConfig(
            policy["low"],
            policy["high"],
            tuple(policy["levels_by_bin"]),
            policy.get("drift_reference_mean"),
            policy.get("drift_reference_scale"),
        )
        runner_controller = asdict(runner.controller)
        runner_controller["levels"] = list(runner.controller.levels)
        if (
            asdict(recomputed.coverage) != coverage
            or recomputed_metrics != manifest["metrics_kwh"]
            or len(scored) != manifest["coverage"]["scored"]
            or runner.proxy_costs["inference_calls"] != manifest["coverage"]["created"]
            or runner.proxy_costs != manifest["proxy_costs"]
            or runner.runtime_costs != manifest["runtime_costs"]
            or runner.state_tensor_memory() != manifest["state_tensor_memory"]
            or runner.selection_rule != key[1]
            or runner.proxy_config != expected_proxy
            or runner_controller != expected_controller
            or runner.update_steps
            != [cost["update_steps"] for cost in manifest["runtime_costs"]["candidate"]]
        ):
            raise ValueError("Run metrics, coverage, or cost accounting mismatch")
        mae = None if recomputed.live is None else recomputed.live.mae_kwh
        seen[key] = {
            "mae": mae,
            "scored": scored,
            "coverage": manifest["coverage"],
            "updates": tuple(runner.update_steps),
            "proxy_calls": runner.proxy_costs["inference_calls"],
            "runtime_costs": runner.runtime_costs,
            "proxy_costs": runner.proxy_costs,
            "duration_seconds": manifest["duration_seconds"],
            "peak_rss_bytes": manifest["memory_usage"]["peak_rss_bytes"],
        }
    if set(seen) != expected:
        raise ValueError("Incomplete finite calibration matrix")
    return _summarize_seen(plan, seen)


def _summarize_seen(plan: dict, seen: dict[tuple, dict]) -> dict:
    """Apply strict pairing and station/seed/budget aggregation to verified rows."""
    expected = {
        (cell_index, method, recipe_index)
        for cell_index in range(len(plan["cells"]))
        for method in METHODS
        for recipe_index in range(4)
    }
    if set(seen) != expected:
        raise ValueError("Incomplete finite calibration matrix")
    for cell_index in range(len(plan["cells"])):
        reference = seen[cell_index, METHODS[0], 0]
        for method in METHODS:
            for index in range(4):
                actual = seen[cell_index, method, index]
                if any(
                    actual[name] != reference[name]
                    for name in ("scored", "coverage", "updates", "proxy_calls")
                ):
                    raise ValueError("Methods do not share paired origins/update budgets")
    groups: dict[tuple, list[int]] = defaultdict(list)
    for cell_index, cell in enumerate(plan["cells"]):
        groups[_cell_key(cell)[:-1] + (cell["initialization"],)].append(cell_index)
    for indices in groups.values():
        ref = seen[indices[0], METHODS[0], 0]["scored"]
        if any(seen[i, METHODS[0], 0]["scored"] != ref for i in indices):
            raise ValueError("Seed replications have different scored origins")
    selections = {}
    for method in METHODS:
        recipes = []
        for index in range(4):
            budgets = {}
            null_groups = 0
            for budget in BUDGETS:
                station_means = []
                for group, indices in groups.items():
                    if group[2] != budget:
                        continue
                    values = [seen[i, method, index]["mae"] for i in indices]
                    if all(value is None for value in values):
                        null_groups += 1
                    elif any(value is None for value in values):
                        raise ValueError("Partial-null seed group cannot be silently averaged")
                    else:
                        station_means.append(math.fsum(values) / len(values))
                budgets[str(budget)] = {
                    "mae_kwh": math.fsum(station_means) / len(station_means)
                    if station_means
                    else None,
                    "scored_stations": len(station_means),
                }
            budget_values = [item["mae_kwh"] for item in budgets.values()]
            recipes.append(
                {
                    "recipe": index,
                    "budgets": budgets,
                    "null_station_budget_groups": null_groups,
                    "equal_budget_mae_kwh": math.fsum(budget_values) / len(budget_values)
                    if all(value is not None for value in budget_values)
                    else None,
                }
            )
        scored_recipes = [item for item in recipes if item["equal_budget_mae_kwh"] is not None]
        choice = (
            min(scored_recipes, key=lambda item: (item["equal_budget_mae_kwh"], item["recipe"]))[
                "recipe"
            ]
            if len(scored_recipes) == 4
            else None
        )
        for item in recipes:
            rows = [
                seen[cell_index, method, item["recipe"]] for cell_index in range(len(plan["cells"]))
            ]
            item["cost_totals"] = {
                "candidate": [
                    {
                        name: sum(
                            row["runtime_costs"]["candidate"][candidate][name] for row in rows
                        )
                        for name in ("inference_calls", "inference_ns", "update_steps", "update_ns")
                    }
                    for candidate in range(3)
                ],
                "audit": {
                    name: sum(row["runtime_costs"]["audit"][name] for row in rows)
                    for name in ("inference_calls", "inference_ns", "update_steps", "update_ns")
                },
                "proxy": {
                    name: sum(row["proxy_costs"][name] for row in rows)
                    for name in ("inference_calls", "inference_ns")
                },
                "duration_seconds_sum": math.fsum(row["duration_seconds"] for row in rows),
                "peak_rss_bytes_max": max(
                    (row["peak_rss_bytes"] for row in rows if row["peak_rss_bytes"] is not None),
                    default=None,
                ),
                "peak_rss_missing_runs": sum(row["peak_rss_bytes"] is None for row in rows),
            }
        selections[method] = {"recipes": recipes, "provisional_recipe": choice}
    return {
        "schema": "hung-proxy-development-selection-v1",
        "scope": "conditional_development_selection_only; no Final lock",
        "matrix_runs": len(seen),
        "cells": len(plan["cells"]),
        "seeds": plan["profile"]["seeds"],
        "selection": selections,
        "null_run_cells": sum(item["mae"] is None for item in seen.values()),
        "plan_code_commit": plan["code_commit"],
        "namespace_and_initialization": [
            plan["cells"][0]["dataset_id"],
            plan["cells"][0]["city_id"],
            plan["cells"][0]["initialization"],
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("plan")
    prepare.add_argument("--profile", type=Path, required=True)
    prepare.add_argument("--cells", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--plan-sha256", required=True)
    run.add_argument("--output", type=Path, required=True)
    choose = commands.add_parser("select")
    choose.add_argument("--plan", type=Path, required=True)
    choose.add_argument("--plan-sha256", required=True)
    choose.add_argument("--runs", type=Path, required=True)
    choose.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output = _ignored_output(args.output)
    if args.command == "plan":
        result = build_plan(args.profile, args.cells)
        for cell in result["cells"]:
            for path in (
                Path(cell["input_run"]),
                Path(cell["source_input_run"]),
                Path(cell["source_checkpoint"]).parent,
                Path(cell["target_checkpoint"]).parent,
            ):
                if args.output.is_relative_to(_within_project(path)):
                    raise ValueError("Plan output cannot enter an existing input/checkpoint run")
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    elif args.command == "run":
        execute(args.plan, args.plan_sha256, args.output)
    else:
        args.plan, args.runs = _stable_support_file(args.plan), _stable_support_file(args.runs)
        if sha256_file(args.plan) != args.plan_sha256:
            raise ValueError("Plan SHA-256 mismatch")
        plan = _json(args.plan)
        rows = [json.loads(line) for line in args.runs.read_text(encoding="utf-8").splitlines()]
        if any(args.output.is_relative_to(_within_project(Path(row["run_path"]))) for row in rows):
            raise ValueError("Selection output cannot enter a replay run")
        result = select(plan, rows)
        result["plan_sha256"] = args.plan_sha256
        result["runs_sha256"] = sha256_file(args.runs)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
