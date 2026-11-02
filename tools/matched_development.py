"""Complete missing matched Development comparators after verified calibration."""

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
from tools.proxy_calibration import selected_controller

CORE_VARIANTS = ("adaptive", "full_finetuning", "fixed_retention")

BASE_VARIANTS = (
    "seasonal_naive",
    "target_only",
    "frozen_source",
    "online_best",
    "without_source_initialization",
    "block7",
    "block28",
)


def variants(reference: dict, *, include_core: bool = False) -> tuple[str, ...]:
    """Alias confidence-free only if identical; add a valid block-size bridge."""
    result = BASE_VARIANTS + (CORE_VARIANTS if include_core else ())
    controller = ControllerConfig(**reference["controller"])
    if controller.delta != 0:
        result += ("without_confidence",)
    if controller.min_valid_days > 7:
        result += ("adaptive_bmin7_reference",)
    return result


def comparison_config(reference: dict, variant: str, *, fixed_lambda: float | None = None) -> dict:
    """Preserve all common settings except each declared baseline/ablation change."""
    if variant not in variants(reference, include_core=fixed_lambda is not None):
        raise ValueError("Unknown or aliased matched variant")
    config = copy.deepcopy(reference)
    config["method"] = {"name": variant}
    if variant == "fixed_retention":
        if type(fixed_lambda) not in (int, float) or fixed_lambda not in (0.001, 0.01, 0.1, 1.0):
            raise ValueError("Previously selected finite Fixed Retention lambda required")
        config["method"]["fixed_lambda"] = fixed_lambda
    elif variant == "adaptive_bmin7_reference":
        config["method"] = {"name": "adaptive"}
        config["controller"]["min_valid_days"] = 7
    elif variant == "block7":
        config["controller"].update(
            block_days=7, min_valid_days=min(7, config["controller"]["min_valid_days"])
        )
    elif variant == "block28":
        config["controller"]["block_days"] = 28
    ControllerConfig(**config["controller"])
    return config


def validate_cells(
    rows: list[dict], references: dict, *, replication_fixed_lambda: float | None = None
) -> dict:
    """Require the full paired matrix and actual configuration/coverage bindings."""
    expected = {
        (key, variant)
        for key, ref in references.items()
        for variant in variants(
            ref["binding"]["config"], include_core=replication_fixed_lambda is not None
        )
    }
    seen = set()
    for row in rows:
        b, c = row["binding"]["input"], row["binding"]["config"]
        key = b["history_days"], b["entity_id"], c["initial_training"]["seed"]
        variant = row["comparison_variant"]
        cell = key, variant
        if cell not in expected or cell in seen:
            raise ValueError("Extra/duplicate matched cell")
        seen.add(cell)
        reference = references[key]
        if c != comparison_config(
            reference["binding"]["config"], variant, fixed_lambda=replication_fixed_lambda
        ):
            raise ValueError("Matched config differs from declared ablation")
        if row["method"]["name"] != c["method"]["name"]:
            raise ValueError("Wrong executed comparator")
        if any(row[k] != reference[k] for k in ("issued_days", "scored_days")):
            raise ValueError("Matched forecast/label coverage differs")
        if b != reference["binding"]["input"]:
            raise ValueError("Matched input/Source binding differs")
        if (row["active_mae_kwh"] is None) != (row["scored_days"] == 0):
            raise ValueError("Null score/count contradiction")
    if seen != expected:
        raise ValueError("All matched cells required, including null scores")
    controller = next(iter(references.values()))["binding"]["config"]["controller"]
    return {
        "scope": "Matched Development comparators; no Final evaluation/lock",
        "cells": len(seen),
        "replication_fixed_lambda": replication_fixed_lambda,
        "aliases": {
            "without_confidence": "online_best"
            if controller["delta"] == 0
            else "without_confidence",
            "fixed_lambda": "fixed_retention",
        },
        "block7_comparator": "adaptive_bmin7_reference"
        if controller["min_valid_days"] > 7
        else "adaptive",
        "limits": "Coverage counts checked here; independently verify full issued/scored origin sets before analysis. Calibration winners are conditional Development selections, not held-out effectiveness.",
    }


def run(args: argparse.Namespace) -> None:
    if not torch.cuda.is_available():
        raise ValueError("Real matched Development runs require CUDA")
    if digest(args.controller_matrix) != args.controller_sha256:
        raise ValueError("Changed controller matrix")
    verification = json.loads(args.controller_verification.read_text())
    if (
        verification.get("status") != "verified"
        or verification.get("matrix_sha256") != args.controller_sha256
    ):
        raise ValueError("Independent controller verification required")
    matrix = authenticate_matrix(args.controller_matrix, args.controller_verification)
    if digest(args.selection) != matrix["selection_sha256"]:
        raise ValueError("Changed identified Development cohort")
    cohort = json.loads(args.selection.read_text())
    code = runtime_code()
    if code["dirty"]:
        raise ValueError("Clean identified code required")
    choice, references = selected_controller(matrix, cohort, code["files"])
    fixed_lambda = None
    fixed_identity = None
    fixed_args = (args.fixed_study, args.fixed_verification, args.fixed_sha256)
    if any(value is not None for value in fixed_args):
        if (
            not all(value is not None for value in fixed_args)
            or digest(args.fixed_study) != args.fixed_sha256
        ):
            raise ValueError("All identified Fixed study/verification arguments required")
        fixed = authenticate_matrix(args.fixed_study, args.fixed_verification)
        if (
            fixed["source_study_sha256"] != matrix["source_study_sha256"]
            or fixed["selection_sha256"] != matrix["selection_sha256"]
        ):
            raise ValueError("Replication Fixed selection has different Source/cohort")
        fixed_lambda = score_candidates(
            fixed["runs"],
            cohort,
            [0.001, 0.01, 0.1, 1.0],
            choice_field="fixed_lambda",
            method_name="fixed_retention",
        )["provisional_choice"]
        if fixed_lambda is None:
            raise ValueError("No scored Fixed recipe for replication")
        fixed_identity = args.fixed_sha256
    sources = {}
    for key, item in matrix["sources"].items():
        seed = int(key)
        path = args.source_study / f"source-seed{seed}" / f"epoch-{matrix['source_epochs']}.pt"
        if digest(path) != item["sha256"]:
            raise ValueError("Changed Source checkpoint")
        sources[seed] = path, item["sha256"]
    if set(sources) != set(cohort["seeds"]):
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
        "scope": "Missing matched Development comparators and ablations; no Final lock",
        "controller_matrix_sha256": args.controller_sha256,
        "controller_recipe": choice,
        "selection_sha256": matrix["selection_sha256"],
        "source_epochs": matrix["source_epochs"],
        "sources": matrix["sources"],
        "replication_fixed_lambda": fixed_lambda,
        "fixed_study_sha256": fixed_identity,
        "code": code,
        "runs": [],
        "status": "running",
    }
    started = time.perf_counter()
    try:
        for budget in (7, 14, 28):
            for item in cohort["budgets"][str(budget)]["entities"]:
                entity = item["entity_id"]
                replay = Replay(data[budget], entity, 90)
                replay.prepare_label_index()
                data[budget].training("development", entity)
                for seed in cohort["seeds"]:
                    reference = references[budget, entity, seed]["binding"]["config"]
                    for variant in variants(reference, include_core=fixed_lambda is not None):
                        config = comparison_config(reference, variant, fixed_lambda=fixed_lambda)
                        name = f"urbanev-SZH-{entity}-{budget}d-{variant}-seed{seed}"
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
                            )
                        row["comparison_variant"] = variant
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
        write_json(
            args.output / "coverage.json",
            validate_cells(output["runs"], references, replication_fixed_lambda=fixed_lambda),
        )
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
        "controller-matrix",
        "controller-verification",
        "source-study",
        "selection",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--controller-sha256", required=True)
    parser.add_argument("--fixed-study", type=Path)
    parser.add_argument("--fixed-verification", type=Path)
    parser.add_argument("--fixed-sha256")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
