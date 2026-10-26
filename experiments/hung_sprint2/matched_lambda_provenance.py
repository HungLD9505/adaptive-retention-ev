"""Authenticate finite Parameter lambda cells and recompute the Development winner."""

from __future__ import annotations

import hashlib
import json
import math

import torch

from experiments.hung_sprint2 import dispatch_matched as dispatch
from experiments.hung_sprint2.matched_plan_provenance import pinned_json, require

LEVELS = (0.1, 10.0, 1000.0, 10000.0)
BUDGETS = (7, 14, 28)
SEEDS = (7, 11, 19)
CELL_KEYS = {
    "lambda_index",
    "budget",
    "seed",
    "entity_id",
    "mae_kwh",
    "scored_origins",
    "issued_origins_sha256",
    "scored_origins_sha256",
    "source_checkpoint_sha256",
    "target_checkpoint_sha256",
    "runner_checkpoint_sha256",
    "run_manifest_sha256",
}


def _digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def verify_lambda(
    spec: dict, config: dict, selection_sha256: str, accepted_selection: dict
) -> float:
    require(
        isinstance(spec, dict)
        and set(spec) == {"selection", "chosen_lambda_low", "preflight", "roots"},
        "Chosen lambda and four-run evidence pins required",
    )
    selected = pinned_json(spec["selection"])
    preflight = pinned_json(spec["preflight"])
    require(
        set(selected)
        == {
            "schema",
            "scope",
            "rule",
            "preflight_sha256",
            "selection_sha256",
            "chosen_index",
            "chosen_lambda_low",
            "ranking",
            "cells",
        }
        and selected["schema"] == "hung-parameter-lambda-development-selection-v1"
        and selected["scope"]
        == "UrbanEV SZH Development target_initial_adaptation only; no Final lock"
        and selected["rule"]
        == "station-first seed mean within budget, equal budget mean, tie smaller lambda"
        and selected["preflight_sha256"] == spec["preflight"]["sha256"]
        and selected["selection_sha256"] == selection_sha256
        and preflight.get("seeds") == list(SEEDS)
        and isinstance(selected["cells"], list)
        and len(selected["cells"]) == 36
        and isinstance(selected["ranking"], list)
        and len(selected["ranking"]) == 4,
        "Finite Development lambda selection/preflight differs or is incomplete",
    )
    roots = spec["roots"]
    for budget in BUDGETS:
        key = str(budget)
        require(
            preflight["budgets"][key]["chosen_entity_id"]
            == accepted_selection["budgets"][key]["verification_entity_ids"][0]
            and preflight["budgets"][key]["input_manifest_sha256"]
            == accepted_selection["budgets"][key]["manifest_sha256"],
            "Lambda preflight is not the accepted Development verification cohort",
        )
    require(isinstance(roots, list) and len(roots) == 4, "Four lambda matrix roots required")
    matrices = {}
    for row in roots:
        require(
            isinstance(row, dict)
            and set(row) == {"index", "path", "matrix_sha256", "config"}
            and type(row["index"]) is int
            and row["index"] in range(4)
            and row["index"] not in matrices,
            "Duplicate/invalid lambda root",
        )
        path = dispatch.project_path(row["path"])
        marker = dispatch.read_verified_json(path / "matrix_identity.json", row["matrix_sha256"])
        candidate = pinned_json(row["config"])
        level = LEVELS[row["index"]]
        require(
            marker.get("schema") == "hung-sprint2-development-matrix-v1"
            and marker.get("phase") == "verification"
            and marker.get("budgets") == list(BUDGETS)
            and marker.get("seeds") == list(SEEDS)
            and marker.get("selection_sha256") == selection_sha256
            and marker.get("config_sha256") == row["config"]["sha256"]
            and marker.get("code", {}).get("worktree_status") == []
            and marker.get("code", {}).get("commit") == preflight.get("code_commit")
            and candidate["target"].get("retention_kind") == "parameter"
            and candidate["replay"].get("retention_kind") == "parameter"
            and candidate["target"]["retention_weight"]
            == candidate["replay"]["initial_level"]
            == candidate["replay"]["level_one"]
            == level
            and candidate["replay"]["level_two"] == 2 * level,
            "Lambda matrix marker/config differs",
        )
        matrices[row["index"]] = (path, marker)
    require(set(matrices) == set(range(4)), "Lambda root grid incomplete")
    scores = {index: {budget: {} for budget in BUDGETS} for index in range(4)}
    paired = {}
    for cell in selected["cells"]:
        require(
            isinstance(cell, dict) and set(cell) == CELL_KEYS, "Lambda proof cell fields differ"
        )
        index, budget, seed = cell["lambda_index"], cell["budget"], cell["seed"]
        require(
            type(index) is int
            and index in range(4)
            and budget in BUDGETS
            and seed in SEEDS
            and seed not in scores[index][budget]
            and cell["entity_id"] == preflight["budgets"][str(budget)]["chosen_entity_id"]
            and type(cell["scored_origins"]) is int
            and cell["scored_origins"] > 0
            and type(cell["mae_kwh"]) in (int, float)
            and math.isfinite(cell["mae_kwh"])
            and cell["mae_kwh"] >= 0
            and all(_digest(cell[name]) for name in CELL_KEYS if name.endswith("sha256")),
            "Invalid/duplicate lambda proof cell",
        )
        pairing = (
            cell["issued_origins_sha256"],
            cell["scored_origins_sha256"],
            cell["scored_origins"],
        )
        key = (budget, seed)
        require(key not in paired or paired[key] == pairing, "Lambda origin pairing differs")
        paired[key] = pairing
        root, marker = matrices[index]
        run = root / f"{budget}d" / f"seed-{seed}" / f"entity-{cell['entity_id']}" / "replay-90"
        record = dispatch.read_verified_json(run / "run_manifest.json", cell["run_manifest_sha256"])
        dispatch.verify_file(run / "runner_checkpoint.pt", cell["runner_checkpoint_sha256"])
        base = root / f"{budget}d" / f"seed-{seed}"
        dispatch.verify_file(
            base / "source" / "source_checkpoint.pt", cell["source_checkpoint_sha256"]
        )
        dispatch.verify_file(
            base / f"entity-{cell['entity_id']}" / "target" / "target_checkpoint.pt",
            cell["target_checkpoint_sha256"],
        )
        journal = record.get("event_journal", {})
        dispatch.verify_file(run / journal.get("file", ""), journal.get("sha256"))
        state = torch.load(run / "runner_checkpoint.pt", map_location="cpu", weights_only=True)
        issued = state.get("issued")
        require(
            isinstance(issued, list)
            and state.get("pending") is None
            and state.get("next_index") == 90
            and state.get("binding") == record.get("input_binding"),
            "Lambda runner state/binding differs",
        )
        origins = tuple(item["day_id"] for item in issued)
        scored = tuple(item["day_id"] for item in issued if item.get("y_scaled") is not None)
        require(
            hashlib.sha256(json.dumps(origins).encode()).hexdigest()
            == cell["issued_origins_sha256"]
            and hashlib.sha256(json.dumps(scored).encode()).hexdigest()
            == cell["scored_origins_sha256"]
            and len(scored) == cell["scored_origins"],
            "Lambda origin proof differs from runner checkpoint",
        )
        live = record.get("metrics_kwh", {}).get("live", {})
        require(
            record.get("schema") == "hung-sprint2-development-replay-v1"
            and record.get("status") == "completed"
            and record.get("code") == marker["code"]
            and record.get("runner_cursor") == 90
            and record.get("coverage", {}).get("scored") == cell["scored_origins"]
            and record.get("config", {}).get("max_origins") == 90
            and record.get("final_runner_checkpoint_sha256") == cell["runner_checkpoint_sha256"]
            and record.get("source_checkpoint_sha256") == cell["source_checkpoint_sha256"]
            and record.get("target_checkpoint_sha256") == cell["target_checkpoint_sha256"]
            and record.get("input_binding", {}).get("entity_id") == cell["entity_id"]
            and record.get("input_binding", {}).get("input_manifest_sha256")
            == preflight["budgets"][str(budget)]["input_manifest_sha256"]
            and record.get("config", {}).get("selection_rule") == "confidence"
            and record.get("config", {}).get("retention_kind") == "parameter"
            and record.get("config", {}).get("seed") == seed
            and record.get("config", {}).get("controller", {}).get("levels")
            == [0.0, LEVELS[index], 2 * LEVELS[index]]
            and live.get("mae_kwh") is not None
            and math.isclose(live["mae_kwh"], cell["mae_kwh"], rel_tol=1e-9, abs_tol=1e-9),
            "Lambda run manifest/checkpoint evidence differs",
        )
        scores[index][budget][seed] = cell["mae_kwh"]
    require(len(paired) == 9, "Lambda paired grid incomplete")
    ranking = []
    for index in range(4):
        means = {}
        for budget in BUDGETS:
            require(set(scores[index][budget]) == set(SEEDS), "Lambda seed grid incomplete")
            means[str(budget)] = math.fsum(scores[index][budget][seed] for seed in SEEDS) / len(
                SEEDS
            )
        ranking.append(
            {
                "index": index,
                "lambda_low": LEVELS[index],
                "budget_seed_mean_mae_kwh": means,
                "equal_budget_mae_kwh": math.fsum(means.values()) / len(BUDGETS),
            }
        )
    winner = min(ranking, key=lambda row: (row["equal_budget_mae_kwh"], row["index"]))
    require(
        selected["ranking"] == ranking
        and selected["chosen_index"] == winner["index"]
        and selected["chosen_lambda_low"] == spec["chosen_lambda_low"] == winner["lambda_low"],
        "Lambda ranking/winner differs from authenticated Development cells",
    )
    target, replay = config["target"], config["replay"]
    require(
        target.get("retention_kind") == replay.get("retention_kind") == "parameter"
        and target["retention_weight"]
        == replay["initial_level"]
        == replay["level_one"]
        == winner["lambda_low"]
        and replay["level_two"] == 2 * winner["lambda_low"],
        "Parameter config does not bind chosen lambda",
    )
    return winner["lambda_low"]
