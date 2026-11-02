"""Finite positive-lambda Development calibration after an identified Source study."""

import argparse
import contextlib
import copy
import json
import time
from pathlib import Path

import torch

from ev_evaluation.artifacts import authenticate_matrix
from ev_evaluation.selection import score_candidates
from ev_models.checkpoint import digest, write_json
from ev_runner.replay import Replay
from ev_runner.run import execute, runtime_code
from tools.comparison_matrix import CachedInputs
from tools.development_readiness import validate_cohort
from tools.source_epoch_sweep import summarize


def selected_sources(study: dict, cohort: dict, profile: dict) -> tuple[int, dict]:
    """Recompute the finite Source choice; never accept an edited winner pointer."""
    if (
        study.get("status") != "technical_success"
        or study.get("profile_sha256") != profile["source_profile_sha256"]
        or study.get("selection_sha256") != profile["selection_sha256"]
        or study["code"]["commit"] != profile["source_study_code"]
        or study["code"]["dirty"]
    ):
        raise ValueError("Identified successful Source-duration study required")
    selection = summarize(study["runs"], cohort, [1, 3, 10])
    epoch = selection["provisional_source_epochs"]
    if epoch is None:
        raise ValueError("No scored common Source choice")
    sources = {}
    for item in study["sources"]:
        seed = item["seed"]
        if seed in sources:
            raise ValueError("Duplicate Source seed")
        candidates = [c for c in item["candidates"] if c["epochs"] == epoch]
        if len(candidates) != 1:
            raise ValueError("Exactly one identified Source checkpoint per seed required")
        sources[seed] = candidates[0]
    if set(sources) != set(cohort["seeds"]):
        raise ValueError("All paired Source seeds required")
    return epoch, sources


def validate_profile(profile: dict) -> None:
    if set(profile) != {
        "schema",
        "scope",
        "lambdas",
        "seeds",
        "selection_sha256",
        "source_profile_sha256",
        "source_study_code",
        "selection_rule",
    } or (
        profile["schema"] != "ev-fixed-retention-study-v1"
        or profile["lambdas"] != [0.001, 0.01, 0.1, 1.0]
        or profile["seeds"] != [42, 43, 44]
        or profile["selection_rule"] != "equal_budget_station_seed_mae_kwh_then_smaller_lambda"
    ):
        raise ValueError("Unexpected finite Fixed Retention profile")


def run(args: argparse.Namespace) -> None:
    if not torch.cuda.is_available():
        raise ValueError("Real calibration requires Colab/Kaggle CUDA")
    if digest(args.profile) != args.profile_sha256 or digest(args.study) != args.study_sha256:
        raise ValueError("Study/profile fingerprint mismatch")
    profile = json.loads(args.profile.read_text())
    validate_profile(profile)
    verification = json.loads(args.verification.read_text())
    if (
        verification.get("status") != "verified"
        or verification.get("matrix_sha256") != args.study_sha256
    ):
        raise ValueError("Source study must be independently verified before calibration")
    if digest(args.selection) != profile["selection_sha256"]:
        raise ValueError("Changed identified Development cohort")
    cohort = json.loads(args.selection.read_text())
    study = authenticate_matrix(args.study, args.verification)
    epoch, sources = selected_sources(study, cohort, profile)
    if runtime_code()["files"] != study["code"]["files"]:
        raise ValueError("Core algorithms changed since the Source study")
    for seed, candidate in sources.items():
        # Bind bytes, not the previous machine's absolute filesystem location.
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
    write_json(args.output / "profile.json", profile)
    start = time.perf_counter()
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
                    for weight in profile["lambdas"]:
                        config = copy.deepcopy(reference["binding"]["config"])
                        config["method"] = {"name": "fixed_retention", "fixed_lambda": weight}
                        name = f"urbanev-SZH-{entity}-{budget}d-fixed_retention-seed{seed}-lambda{str(weight).replace('.', 'p')}"
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
                        row["fixed_lambda"] = weight
                        matrix["runs"].append(row)
                        path = args.output / "progress.next.json"
                        path.write_text(json.dumps(matrix, indent=2, allow_nan=False))
                        path.replace(args.output / "progress.json")
                        print(
                            json.dumps(
                                {k: row[k] for k in ("run_id", "scored_days", "active_mae_kwh")}
                            ),
                            flush=True,
                        )
        result = score_candidates(
            matrix["runs"],
            cohort,
            profile["lambdas"],
            choice_field="fixed_lambda",
            method_name="fixed_retention",
        )
        write_json(
            args.output / "selection.json",
            {
                "scope": "Finite Fixed Retention Development selection; no Final lock or automatic controller change",
                "candidates": result["candidates"],
                "provisional_fixed_lambda": result["provisional_choice"],
                "source_epochs": epoch,
                "limits": "Small selected cohort, different budget IDs; positive-lambda baseline only. No superiority or calibration claim for adaptive/proxy controllers.",
            },
        )
        matrix["status"] = "technical_success"
    except Exception as error:
        matrix.update(status="failed", error=repr(error))
        raise
    finally:
        matrix["wall_seconds"] = time.perf_counter() - start
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
