"""Comparable four-recipe Development proxy/parameter calibration, CUDA only."""

import argparse
import contextlib
import copy
import json
import time
from pathlib import Path

import torch

from ev_baselines.policies import Method
from ev_evaluation.artifacts import authenticate_matrix
from ev_evaluation.selection import score_candidates
from ev_models.checkpoint import digest, write_json
from ev_runner.replay import Replay
from ev_runner.run import execute, runtime_code
from tools.comparison_matrix import CachedInputs
from tools.controller_calibration import summarize as controller_selection
from tools.development_readiness import validate_cohort

METHODS = ("source_error", "uncertainty", "drift", "parameter_retention")
THRESHOLDS = {
    "source_error": ((0.1, 0.5), (0.05, 0.25)),
    "uncertainty": ((0.01, 0.05), (0.005, 0.025)),
    "drift": ((0.5, 1.5), (1.0, 3.0)),
}
PARAMETER_PAIRS = ((0.001, 0.01), (0.01, 0.1), (0.1, 1.0), (1.0, 10.0))


def validate_profile(profile: dict) -> None:
    """Require the predeclared finite and equal-count tuning budgets."""
    expected = {
        "schema": "ev-proxy-calibration-v1",
        "methods": list(METHODS),
        "recipes_per_method": 4,
        "seeds": [42, 43, 44],
        "thresholds": {k: [list(t) for t in v] for k, v in THRESHOLDS.items()},
        "orders": [[0, 1, 2], [2, 1, 0]],
        "parameter_pairs": [list(p) for p in PARAMETER_PAIRS],
        "selection_rule": "equal_budget_station_seed_mae_kwh_then_recipe_index",
    }
    if profile != expected:
        raise ValueError("Unexpected comparable finite proxy/parameter profile")


def recipe_config(reference: dict, method: str, recipe: int) -> dict:
    """Keep the selected common controller structure and change its selector only."""
    if method not in METHODS or type(recipe) is not int or recipe not in range(4):
        raise ValueError("Unknown method/recipe")
    config = copy.deepcopy(reference)
    if method == "parameter_retention":
        low, high = PARAMETER_PAIRS[recipe]
        config["controller"].update(lambda_low=low, lambda_high=high, initial_lambda=low)
        config["method"] = {"name": method}
    else:
        config["method"] = {
            "name": method,
            "proxy_thresholds": list(THRESHOLDS[method][recipe // 2]),
            "proxy_order": [0, 1, 2] if recipe % 2 == 0 else [2, 1, 0],
        }
    Method(**config["method"])
    return config


def selected_controller(matrix: dict, cohort: dict, code_files: dict) -> tuple[int, dict]:
    """Recompute the controller winner and require its whole verified pairing."""
    if (
        matrix.get("status") != "technical_success"
        or matrix["code"]["dirty"]
        or matrix["code"]["files"] != code_files
    ):
        raise ValueError("Successful unchanged controller calibration required")
    selection = controller_selection(matrix["runs"], cohort)
    choice = selection["provisional_choice"]
    if choice is None:
        raise ValueError("No scored controller recipe")
    rows = {}
    for row in matrix["runs"]:
        if row["recipe"] != choice:
            continue
        if row["code"]["dirty"] or row["code"]["files"] != code_files:
            raise ValueError("Changed controller row algorithms")
        b, c = row["binding"]["input"], row["binding"]["config"]
        key = b["history_days"], b["entity_id"], c["initial_training"]["seed"]
        if (
            b["dataset_id"] != "urbanev"
            or b["city_id"] != "SZH"
            or b["input_manifest_sha256"] != cohort["budgets"][str(key[0])]["manifest_sha256"]
        ):
            raise ValueError("Changed Development namespace/manifest")
        rows[key] = row
    return choice, rows


def summarize(rows: list[dict], cohort: dict, references: dict) -> dict:
    """Validate each actual recipe and select each method independently with nulls."""
    if any(row["method"]["name"] not in METHODS for row in rows):
        raise ValueError("Unexpected calibration method")
    result = {}
    for method in METHODS:
        group = [r for r in rows if r["method"]["name"] == method]
        for row in group:
            b, c = row["binding"]["input"], row["binding"]["config"]
            key = b["history_days"], b["entity_id"], c["initial_training"]["seed"]
            if c != recipe_config(references[key]["binding"]["config"], method, row["recipe"]):
                raise ValueError("Actual proxy/parameter config contradicts recipe")
        result[method] = score_candidates(
            group, cohort, list(range(4)), choice_field="recipe", method_name=method
        )
    return result


def run(args: argparse.Namespace) -> None:
    if not torch.cuda.is_available():
        raise ValueError("Real proxy/parameter calibration requires CUDA")
    if (
        digest(args.profile) != args.profile_sha256
        or digest(args.controller_matrix) != args.controller_sha256
    ):
        raise ValueError("Changed profile/controller matrix")
    profile = json.loads(args.profile.read_text())
    validate_profile(profile)
    verification = json.loads(args.controller_verification.read_text())
    if (
        verification.get("status") != "verified"
        or verification.get("matrix_sha256") != args.controller_sha256
    ):
        raise ValueError("Independently verified controller matrix required")
    matrix = authenticate_matrix(args.controller_matrix, args.controller_verification)
    if digest(args.selection) != matrix["selection_sha256"]:
        raise ValueError("Changed identified Development cohort")
    cohort = json.loads(args.selection.read_text())
    code = runtime_code()
    if code["dirty"]:
        raise ValueError("Clean identified code required")
    choice, refs = selected_controller(matrix, cohort, code["files"])
    sources = {}
    for key, source in matrix["sources"].items():
        seed = int(key)
        path = args.source_study / f"source-seed{seed}" / f"epoch-{matrix['source_epochs']}.pt"
        if digest(path) != source["sha256"]:
            raise ValueError("Changed selected Source checkpoint")
        sources[seed] = (path, source["sha256"])
    if set(sources) != set(cohort["seeds"]) or cohort["seeds"] != profile["seeds"]:
        raise ValueError("All paired Source seeds required")
    data = {
        b: CachedInputs(
            args.inputs_root / f"urbanev-SZH-{b}d", cohort["budgets"][str(b)]["manifest_sha256"]
        )
        for b in (7, 14, 28)
    }
    validate_cohort(data, cohort)
    args.output.mkdir(parents=True, exist_ok=False)
    output = {
        "scope": "Comparable four-recipe proxy/parameter Development calibration; no Final lock",
        "profile_sha256": args.profile_sha256,
        "controller_matrix_sha256": args.controller_sha256,
        "controller_recipe": choice,
        "selection_sha256": matrix["selection_sha256"],
        "source_epochs": matrix["source_epochs"],
        "sources": matrix["sources"],
        "code": code,
        "runs": [],
        "status": "running",
    }
    write_json(args.output / "profile.json", profile)
    started = time.perf_counter()
    try:
        for budget in (7, 14, 28):
            for item in cohort["budgets"][str(budget)]["entities"]:
                entity = item["entity_id"]
                replay = Replay(data[budget], entity, 90)
                replay.prepare_label_index()
                data[budget].training("development", entity)
                for seed in cohort["seeds"]:
                    reference = refs[budget, entity, seed]["binding"]["config"]
                    for method in METHODS:
                        for recipe in range(4):
                            config = recipe_config(reference, method, recipe)
                            name = (
                                f"urbanev-SZH-{entity}-{budget}d-{method}-seed{seed}-recipe{recipe}"
                            )
                            torch.cuda.reset_peak_memory_stats()
                            with (
                                (args.output / f"{name}.log").open("x") as log,
                                contextlib.redirect_stdout(log),
                            ):
                                row = execute(
                                    data[budget],
                                    entity,
                                    sources[seed][0],
                                    sources[seed][1],
                                    config,
                                    args.output / name,
                                    device="cuda",
                                    prepared_replay=replay,
                                    ensemble_sources=tuple(sources[s] for s in cohort["seeds"])
                                    if method == "uncertainty"
                                    else (),
                                )
                            row["recipe"] = recipe
                            output["runs"].append(row)
                            progress = args.output / "progress.next.json"
                            progress.write_text(json.dumps(output, indent=2, allow_nan=False))
                            progress.replace(args.output / "progress.json")
                            print(
                                json.dumps(
                                    {k: row[k] for k in ("run_id", "scored_days", "active_mae_kwh")}
                                ),
                                flush=True,
                            )
        write_json(args.output / "selection.json", summarize(output["runs"], cohort, refs))
        output["status"] = "technical_success"
    except Exception as error:
        output.update(status="failed", error=repr(error))
        raise
    finally:
        output["wall_seconds"] = time.perf_counter() - started
        write_json(args.output / "matrix.json", output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "inputs-root",
        "profile",
        "controller-matrix",
        "controller-verification",
        "source-study",
        "selection",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("profile-sha256", "controller-sha256"):
        parser.add_argument("--" + name, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
