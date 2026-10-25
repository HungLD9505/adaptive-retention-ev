"""Bounded Source-duration Development study; never a Final configuration lock."""

import argparse
import contextlib
import copy
import json
import os
import time
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch

from ev_evaluation.selection import score_candidates
from ev_models.checkpoint import digest, write_json
from ev_models.run import execute as train_source
from ev_runner.replay import Replay
from ev_runner.run import execute as replay_target
from ev_runner.run import runtime_code
from tools.comparison_matrix import CachedInputs
from tools.development_readiness import validate_cohort


def validate_profile(profile: dict, cohort: dict) -> None:
    """Reject hidden search extensions or changes to the identified study cohort."""
    if set(profile) != {
        "schema",
        "scope",
        "source_epochs",
        "seeds",
        "selection_sha256",
        "method",
        "source_training",
        "runner_config",
        "selection_rule",
    }:
        raise ValueError("Unknown/missing Source-study profile fields")
    if (
        profile["schema"] != "ev-source-epoch-study-v1"
        or profile["source_epochs"] != [1, 3, 10]
        or profile["seeds"] != [42, 43, 44]
        or profile["seeds"] != cohort["seeds"]
        or profile["method"] != "full_finetuning"
        or profile["selection_rule"] != "equal_budget_station_seed_mae_kwh_then_fewer_epochs"
    ):
        raise ValueError("Unexpected finite Source-study definition")
    config = profile["runner_config"]
    if config["replay_days"] != 90 or config["state_retention"] != "latest":
        raise ValueError("Identified 90-day/latest Development profile required")
    # Source duration is the only studied change. Architecture/optimizer remain paired.
    source = profile["source_training"]
    if source["epochs"] != 10:
        raise ValueError("One ten-epoch Source trajectory supplies all candidates")
    for key in ("head_width", "learning_rate", "epsilon", "batch_size"):
        if source[key] != config["initial_training"][key]:
            raise ValueError("Source/target training profiles differ")


def summarize(rows: list[dict], cohort: dict, epochs: list[int]) -> dict:
    """Require every candidate/seed/site cell, preserve nulls, weight stations first."""
    result = score_candidates(
        rows, cohort, epochs, choice_field="source_epochs", method_name="full_finetuning"
    )
    choice = result["provisional_choice"]
    return {
        "scope": "Development duration study; exploratory selection, no Final lock/convergence guarantee",
        "candidates": result["candidates"],
        "provisional_source_epochs": choice,
        "best_at_grid_boundary": choice == max(epochs),
        "limits": "Small selected/possibly colocated cohort; budgets have different IDs; fixed training settings. No grid extension or Final promotion is automatic.",
    }


def run(args: argparse.Namespace) -> None:
    if not torch.cuda.is_available():
        raise ValueError("Real Source-duration study requires Colab/Kaggle CUDA")
    if digest(args.profile) != args.profile_sha256:
        raise ValueError("Study profile hash mismatch")
    profile = json.loads(args.profile.read_text())
    if digest(args.selection) != profile["selection_sha256"]:
        raise ValueError("Identified cohort changed")
    cohort = json.loads(args.selection.read_text())
    validate_profile(profile, cohort)
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
        "selection_sha256": profile["selection_sha256"],
        "code": runtime_code(),
        "sources": [],
        "runs": [],
        "status": "running",
    }
    write_json(args.output / "profile.json", profile)
    start = time.perf_counter()

    def progress() -> None:
        path = args.output / "progress.next.json"
        path.write_text(json.dumps(matrix, indent=2, allow_nan=False))
        path.replace(args.output / "progress.json")

    try:
        for seed in profile["seeds"]:
            config = {
                "training": {**profile["source_training"], "seed": seed},
                "lambda": 0,
                "development_entities": ["not-used-by-source"],
                "evaluation_origins": 90,
            }
            out = args.output / f"source-seed{seed}"
            torch.cuda.reset_peak_memory_stats()
            with (
                (args.output / f"source-seed{seed}.log").open("x") as log,
                contextlib.redirect_stdout(log),
            ):
                result = train_source("source", data[7], config, out, device="cuda")
            matrix["sources"].append(
                {
                    "seed": seed,
                    "run": result,
                    "candidates": [
                        {
                            "epochs": epoch,
                            "path": str(out / f"epoch-{epoch}.pt"),
                            "sha256": digest(out / f"epoch-{epoch}.pt"),
                        }
                        for epoch in profile["source_epochs"]
                    ],
                }
            )
            progress()
            print(json.dumps({"source_seed": seed, "epochs": 10, "status": "complete"}), flush=True)
        for budget in (7, 14, 28):
            for item in cohort["budgets"][str(budget)]["entities"]:
                entity = item["entity_id"]
                replay = Replay(data[budget], entity, 90)
                replay.prepare_label_index()
                # Warm the common immutable prefix before isolated per-run counters.
                data[budget].training("development", entity)
                for source in matrix["sources"]:
                    seed = source["seed"]
                    for candidate in source["candidates"]:
                        config = copy.deepcopy(profile["runner_config"])
                        config.update(
                            development_entities=[entity], method={"name": "full_finetuning"}
                        )
                        for name in ("initial_training", "online_training", "controller"):
                            config[name]["seed"] = seed
                        run_id = f"urbanev-SZH-{entity}-{budget}d-full_finetuning-seed{seed}-source{candidate['epochs']}ep"
                        out = args.output / run_id
                        torch.cuda.reset_peak_memory_stats()
                        with (
                            (args.output / f"{run_id}.log").open("x") as log,
                            contextlib.redirect_stdout(log),
                        ):
                            row = replay_target(
                                data[budget],
                                entity,
                                Path(candidate["path"]),
                                candidate["sha256"],
                                config,
                                out,
                                device="cuda",
                                prepared_replay=replay,
                            )
                        row["source_epochs"] = candidate["epochs"]
                        matrix["runs"].append(row)
                        progress()
                        print(
                            json.dumps(
                                {k: row[k] for k in ("run_id", "scored_days", "active_mae_kwh")}
                            ),
                            flush=True,
                        )
        summary = summarize(matrix["runs"], cohort, profile["source_epochs"])
        write_json(args.output / "selection.json", summary)
        matrix["status"] = "technical_success"
    except Exception as error:
        matrix.update(status="failed", error=repr(error))
        raise
    finally:
        matrix["wall_seconds"] = time.perf_counter() - start
        write_json(args.output / "matrix.json", matrix)
        progress()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs-root", "profile", "selection", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--profile-sha256", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
