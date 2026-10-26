"""Predeclared four-recipe Adaptive Controller Development calibration on CUDA."""

import argparse
import contextlib
import copy
import json
import time
from pathlib import Path

import torch

from ev_control.confidence import ControllerConfig
from ev_evaluation.artifacts import authenticate_matrix
from ev_evaluation.selection import score_candidates
from ev_models.checkpoint import digest, write_json
from ev_runner.replay import Replay
from ev_runner.run import execute, runtime_code
from tools.comparison_matrix import CachedInputs
from tools.development_readiness import validate_cohort
from tools.fixed_retention_sweep import selected_sources

# A finite joint recipe search, not estimates of individual hyperparameter effects.
RECIPES = (
    (0.01, 0.1, 7, 0.0, 3),
    (0.1, 1.0, 7, 0.0, 3),
    (0.01, 0.1, 10, 0.005, 5),
    (0.1, 1.0, 10, 0.005, 5),
)


def validate_profile(profile: dict) -> None:
    """Reject undeclared search extensions, seeds, cohorts and tie-breaking rules."""
    if set(profile) != {
        "schema",
        "scope",
        "seeds",
        "selection_sha256",
        "source_profile_sha256",
        "source_study_code",
        "recipes",
        "selection_rule",
    } or (
        profile["schema"] != "ev-controller-calibration-v1"
        or profile["seeds"] != [42, 43, 44]
        or profile["recipes"] != [list(r) for r in RECIPES]
        or profile["selection_rule"] != "equal_budget_station_seed_mae_kwh_then_recipe_index"
    ):
        raise ValueError("Unexpected finite controller calibration profile")


def recipe_config(reference: dict, recipe: int, seed: int) -> dict:
    """Create a fully paired runner config; only declared controller fields vary."""
    if type(recipe) is not int or recipe not in range(len(RECIPES)):
        raise ValueError("Unknown controller recipe")
    if seed not in (42, 43, 44) or type(seed) is not int:
        raise ValueError("Undeclared paired seed")
    low, high, minimum, margin, segment = RECIPES[recipe]
    config = copy.deepcopy(reference)
    config["method"] = {"name": "adaptive"}
    controller = config["controller"]
    controller.update(
        lambda_low=low,
        lambda_high=high,
        initial_lambda=low,
        min_valid_days=minimum,
        delta=margin,
        segment_days=segment,
        seed=seed,
    )
    if (controller["block_days"], controller["alpha"], controller["resamples"]) != (14, 0.05, 2000):
        raise ValueError("Undeclared block/alpha/bootstrap profile")
    ControllerConfig(**controller)
    if config["replay_days"] != 90 or config["state_retention"] != "latest":
        raise ValueError("Expected identified 90-day/latest profile")
    for name in ("initial_training", "online_training"):
        if config[name]["seed"] != seed:
            raise ValueError("Reference/main seed differs")
    return config


def summarize(rows: list[dict], cohort: dict) -> dict:
    """Retain every null cell and average seeds, stations and budgets in that order."""
    scores = score_candidates(
        rows, cohort, list(range(4)), choice_field="recipe", method_name="adaptive"
    )
    for row in rows:
        config = row["binding"]["config"]
        expected = recipe_config(config, row["recipe"], config["initial_training"]["seed"])
        if config != expected:
            raise ValueError("Actual controller config contradicts recipe label")
    return {
        "scope": "Finite joint controller Development calibration; no Final lock",
        **scores,
        "recipes": [list(r) for r in RECIPES],
        "limits": "Small selected cohort; joint recipes, not individual parameter effects. Alpha/R/initial-level policy not exhaustively searched. Independent review required.",
    }


def run(args: argparse.Namespace) -> None:
    if not torch.cuda.is_available():
        raise ValueError("Real controller calibration requires Colab/Kaggle CUDA")
    if digest(args.profile) != args.profile_sha256 or digest(args.study) != args.study_sha256:
        raise ValueError("Study/profile fingerprint mismatch")
    profile = json.loads(args.profile.read_text())
    validate_profile(profile)
    verification = json.loads(args.verification.read_text())
    if (
        verification.get("status") != "verified"
        or verification.get("matrix_sha256") != args.study_sha256
    ):
        raise ValueError("Source study must be independently verified")
    if digest(args.selection) != profile["selection_sha256"]:
        raise ValueError("Identified cohort changed")
    cohort = json.loads(args.selection.read_text())
    study = authenticate_matrix(args.study, args.verification)
    epoch, sources = selected_sources(study, cohort, profile)
    if runtime_code()["files"] != study["code"]["files"]:
        raise ValueError("Core algorithms changed since Source study")
    for seed, candidate in sources.items():
        path = args.study.parent / f"source-seed{seed}" / f"epoch-{epoch}.pt"
        if digest(path) != candidate["sha256"]:
            raise ValueError("Source checkpoint changed")
        sources[seed] = {**candidate, "original_path": candidate["path"], "path": str(path)}
    data = {
        b: CachedInputs(
            args.inputs_root / f"urbanev-SZH-{b}d", cohort["budgets"][str(b)]["manifest_sha256"]
        )
        for b in (7, 14, 28)
    }
    validate_cohort(data, cohort)
    args.output.mkdir(parents=True, exist_ok=False)
    matrix = {
        "scope": profile["scope"],
        "profile_sha256": args.profile_sha256,
        "source_study_sha256": args.study_sha256,
        "source_epochs": epoch,
        "selection_sha256": profile["selection_sha256"],
        "sources": sources,
        "runs": [],
        "status": "running",
        "code": runtime_code(),
    }
    if matrix["code"]["dirty"]:
        raise ValueError("Clean identified code required")
    write_json(args.output / "profile.json", profile)
    started = time.perf_counter()
    try:
        for budget in (7, 14, 28):
            for item in cohort["budgets"][str(budget)]["entities"]:
                entity = item["entity_id"]
                replay = Replay(data[budget], entity, 90)
                replay.prepare_label_index()
                data[budget].training("development", entity)
                for seed in profile["seeds"]:
                    reference = next(
                        r
                        for r in study["runs"]
                        if r["source_epochs"] == epoch
                        and r["binding"]["input"]["history_days"] == budget
                        and r["binding"]["input"]["entity_id"] == entity
                        and r["binding"]["config"]["initial_training"]["seed"] == seed
                    )
                    for recipe in range(4):
                        config = recipe_config(reference["binding"]["config"], recipe, seed)
                        name = f"urbanev-SZH-{entity}-{budget}d-adaptive-seed{seed}-recipe{recipe}"
                        torch.cuda.reset_peak_memory_stats()
                        with (
                            (args.output / f"{name}.log").open("x") as log,
                            contextlib.redirect_stdout(log),
                        ):
                            row = execute(
                                data[budget],
                                entity,
                                Path(sources[seed]["path"]),
                                sources[seed]["sha256"],
                                config,
                                args.output / name,
                                device="cuda",
                                prepared_replay=replay,
                            )
                        row["recipe"] = recipe
                        matrix["runs"].append(row)
                        progress = args.output / "progress.next.json"
                        progress.write_text(json.dumps(matrix, indent=2, allow_nan=False))
                        progress.replace(args.output / "progress.json")
                        print(
                            json.dumps(
                                {k: row[k] for k in ("run_id", "scored_days", "active_mae_kwh")}
                            ),
                            flush=True,
                        )
        write_json(args.output / "selection.json", summarize(matrix["runs"], cohort))
        matrix["status"] = "technical_success"
    except Exception as error:
        matrix.update(status="failed", error=repr(error))
        raise
    finally:
        matrix["wall_seconds"] = time.perf_counter() - started
        write_json(args.output / "matrix.json", matrix)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs-root", "profile", "study", "verification", "selection", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("profile-sha256", "study-sha256"):
        parser.add_argument("--" + name, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
