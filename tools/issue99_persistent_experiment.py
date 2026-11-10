"""Run the locked #99 persistent follow-up on staged Kaggle inputs only.

This dispatcher does not search hyperparameters or inspect Final outcomes. Each
invocation has a new directory and a durable ledger row, including failures.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
import statistics
import time
import traceback
from pathlib import Path

import torch

from ev_models.checkpoint import digest
from ev_runner.continuous_run import execute
from ev_runner.replay import Replay
from tools.issue99_study_support import PreparedInputs


TARGETS = ("1405", "2152", "1153", "1693")
SEEDS = (42, 43, 44)
METHODS = ("lambda0", "fixed", "immediate", "persistent")
SOURCE_SHA = {
    42: "a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b",
    43: "2ad6ed33fb7e692eae5f8db6be075ce43564851f70390d19edb4314052a17f5f",
    44: "6f475e54768322c5b51f5837d6ce7e863cb9ef6d33aec05b4a1c2468cd0285a5",
}
REFERENCE = Path(__file__).resolve().parents[1] / "docs" / "reports" / "issue99-study-20261110"


def write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def append_event(path: Path, value: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, allow_nan=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def lock_protocol(source: Path, output: Path) -> tuple[Path, dict, str]:
    output.mkdir(parents=True, exist_ok=True)
    locked = output / "protocol-lock.json"
    source_sha = digest(source)
    if not locked.exists():
        with source.open("rb") as incoming, locked.open("xb") as outgoing:
            while block := incoming.read(1024 * 1024):
                outgoing.write(block)
            outgoing.flush()
            os.fsync(outgoing.fileno())
    if digest(locked) != source_sha:
        raise ValueError("Existing protocol lock differs from packaged protocol")
    protocol = json.loads(locked.read_text(encoding="utf-8"))
    if protocol["schema"] != "issue99-execution-protocol-v1" or protocol["status"] != "locked_owner_approved":
        raise ValueError("Protocol is not execution-locked")
    if tuple(protocol["targets"]) != TARGETS or tuple(protocol["seeds"]) != SEEDS:
        raise ValueError("Target/seed declaration changed")
    return locked, protocol, source_sha


def source_paths(stage: Path) -> dict[int, Path]:
    found = {seed: stage / "sources" / f"seed{seed}" / "epoch-10.pt" for seed in SEEDS}
    for seed, path in found.items():
        if digest(path) != SOURCE_SHA[seed]:
            raise ValueError(f"Staged Source10 checkpoint differs: seed {seed}")
    return found


def config_for(protocol: dict, protocol_sha: str, method: str, seed: int, target: str, phase: str) -> dict:
    if method not in METHODS or phase not in {"pilot", "calibration", "evaluation"}:
        raise ValueError("Unregistered method or phase")
    arm = protocol["persistent_experiment"]["method_configs"][method]
    training = {
        "seed": seed,
        "epochs": 3,
        "batch_size": 64,
        "learning_rate": 0.001,
        "epsilon": 0.001,
        "head_width": 64,
    }
    config = {
        "schema": "issue99-study-v1",
        "phase": phase,
        "targets": list(TARGETS),
        "initial_training": training,
        "online_training": {**training, "epochs": 1},
        "window_rule": {
            "older_count": 2,
            "newer_count": 1,
            "upper_bound": arm["upper_bound"],
            "meta_step_size": arm["meta_step_size"],
            "epsilon": 0.001,
        },
        "initial_lambda": arm["initial_lambda"],
        "cadence": arm["cadence"],
        "frozen_lambda": arm["frozen_lambda"],
        "controller_variant": arm["controller_variant"],
        "replay_days": 90,
        "protocol_sha256": protocol_sha,
        "objective_origins": [] if phase == "pilot" else protocol[
            "calibration_origins" if phase == "calibration" else "evaluation_origins"
        ][target],
        "state_retention": "latest",
        "diagnostic_every": 7,
    }
    if method == "persistent":
        config["persistent_rule"] = copy.deepcopy(protocol["persistent_rule"])
    return config


def plan(phase: str) -> list[tuple[str, str, int]]:
    if phase == "pilot":
        cases = (("1405", 42), ("2152", 43), ("1693", 42))
        return [(method, target, seed) for target, seed in cases for method in ("fixed", "persistent")]
    if phase == "calibration_reference":
        return [(method, target, seed) for target in TARGETS for seed in SEEDS for method in ("fixed", "immediate")]
    if phase == "calibration_remaining":
        return [(method, target, seed) for target in TARGETS for seed in SEEDS for method in ("lambda0", "persistent")]
    return [(method, target, seed) for target in TARGETS for seed in SEEDS for method in METHODS]


def run_phase(stage: Path, protocol_path: Path, output: Path, phase: str, device: str) -> dict:
    if phase not in {"pilot", "calibration_reference", "calibration_remaining", "evaluation"}:
        raise ValueError("Unknown phase")
    locked, protocol, protocol_sha = lock_protocol(protocol_path, output)
    if phase in {"calibration_reference", "calibration_remaining"}:
        pilot = output / "pilot-independent-verification.json"
        if not pilot.exists():
            raise ValueError("Independent pilot verification missing")
        verified_pilot = json.loads(pilot.read_text(encoding="utf-8"))
        if (verified_pilot.get("status") != "PASS" or verified_pilot.get("screen_pass") is not True
                or verified_pilot.get("protocol_sha256") != protocol_sha):
            raise ValueError("Independent pilot verification failed or binding changed")
    if phase == "calibration_remaining":
        comparison = output / "reference-comparability.json"
        if not comparison.exists() or json.loads(comparison.read_text())["status"] != "PASS":
            raise ValueError("Reference comparability has not passed")
    if phase == "evaluation":
        gate_path = output / "calibration-gate.json"
        if not gate_path.exists() or json.loads(gate_path.read_text())["go_to_later"] is not True:
            raise ValueError("Registered Calibration gate has not passed")
        verification_path = output / "independent-verification.json"
        if not verification_path.exists():
            raise ValueError("Independent Calibration verification missing")
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
        if (verification.get("status") != "PASS" or verification.get("gate_pass") is not True
                or verification.get("calibration_gate_sha256") != digest(gate_path)
                or verification.get("protocol_sha256") != protocol_sha):
            raise ValueError("Independent Calibration verification failed or binding changed")
    torch.set_num_threads(1)
    sources = source_paths(stage)
    inputs = PreparedInputs(stage / "inputs", protocol["input_manifest_sha256"])
    if inputs.source_hash != protocol["source_population_sha256"]:
        raise ValueError("Source population differs")
    replays = {target: Replay(inputs, target, 90) for target in TARGETS}
    name = "later" if phase == "evaluation" else "calibration" if phase.startswith("calibration_") else phase
    phase_root = output / name
    phase_root.mkdir(exist_ok=True)
    rows = []
    jobs = plan(phase)
    for index, (method, target, seed) in enumerate(jobs):
        study_phase = "calibration" if phase.startswith("calibration_") else phase
        run_id = f"{method}-{target}-seed{seed}"
        path = phase_root / run_id
        existing = path / "run.json"
        if existing.exists():
            report = json.loads(existing.read_text(encoding="utf-8"))
            if report["binding"]["config"] != config_for(protocol, protocol_sha, method, seed, target, study_phase):
                raise ValueError(f"Existing run has different config: {run_id}")
            status = "existing_complete"
        elif path.exists():
            raise ValueError(f"Partial run preserved; resume into a new path: {path}")
        else:
            started = time.perf_counter()
            try:
                report = execute(
                    inputs,
                    target,
                    sources[seed],
                    SOURCE_SHA[seed],
                    config_for(protocol, protocol_sha, method, seed, target, study_phase),
                    path,
                    device=device,
                    protocol_path=locked,
                    prepared_replay=replays[target],
                    stop_after_ticks=22 if phase == "pilot" else None,
                )
                status = "complete"
            except Exception as error:
                failure = {
                    "phase": phase, "run_id": run_id, "status": "error",
                    "error_type": type(error).__name__, "error": str(error),
                    "traceback": traceback.format_exc(),
                    "wall_seconds": time.perf_counter() - started,
                    "partial_path": str(path) if path.exists() else None,
                }
                append_event(output / "dispatch.jsonl", failure)
                print(json.dumps({k: failure[k] for k in ("phase", "run_id", "status", "error_type", "error")}), flush=True)
                rows.append(failure)
                for skipped_method, skipped_target, skipped_seed in jobs[index + 1:]:
                    skipped = {
                        "phase": phase,
                        "run_id": f"{skipped_method}-{skipped_target}-seed{skipped_seed}",
                        "status": "not_run_after_error",
                        "mae_kwh": None,
                        "reason": run_id,
                    }
                    append_event(output / "dispatch.jsonl", skipped)
                    rows.append(skipped)
                break
        row = {
            "phase": phase, "run_id": run_id, "method": method, "target": target, "seed": seed,
            "status": status, "mae_kwh": report["mae_kwh"],
            "objective_scored_days": report["objective_scored_days"],
            "objective_coverage_pass": report["objective_coverage_pass"],
            "objective_missing_origins": report["objective_missing_origins"],
            "invocation_wall_seconds": report["invocation_wall_seconds"],
            "run_sha256": digest(existing), "run_path": str(path),
            "final_lambda": report["final_lambda"],
        }
        append_event(output / "dispatch.jsonl", row)
        print(json.dumps({k: row[k] for k in ("phase", "run_id", "status", "mae_kwh", "objective_scored_days", "final_lambda")}, allow_nan=False), flush=True)
        rows.append(row)
    inputs.reauthenticate()
    summary_path = output / f"{phase}-dispatch-summary.json"
    if summary_path.exists():
        raise FileExistsError(summary_path)
    write_new(summary_path, {"phase": phase, "protocol_sha256": protocol_sha, "jobs": len(plan(phase)), "rows": rows})
    return {"phase": phase, "jobs": len(rows), "errors": sum(row["status"] in {"error", "not_run_after_error"} for row in rows), "summary_sha256": digest(summary_path)}


def scores(path: Path) -> dict[str, float]:
    result = {}
    for tick in sorted(path.glob("tick-*")):
        for line in (tick / "events.jsonl").read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event["event"] == "score":
                origin = event["origin"]
                if origin in result:
                    raise ValueError(f"Duplicate score origin: {path} {origin}")
                result[origin] = event["mae_kwh"]
    return result


def reference_guard(output: Path, protocol_path: Path) -> dict:
    """Check historical comparability before running the two new arms.

    This cross-runtime check is an engineering sanity guard, not replication
    proof and not the scientific promotion threshold.
    """
    _, protocol, protocol_sha = lock_protocol(protocol_path, output)
    reference = {}
    with (REFERENCE / "fixed-station-seed.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if int(row["trial"]) == 11:
                reference[(row["target"], int(row["seed"]))] = float(row["mae_kwh"])
    if len(reference) != 12:
        raise ValueError("Historical selected Fixed reference lacks 12 cells")
    expected_fixed_macro = 5.331705633298364
    expected_immediate_macro = 5.318961684341266
    cell_deltas = []
    failures = []
    current = {}
    for target in TARGETS:
        for seed in SEEDS:
            for method in ("fixed", "immediate"):
                path = output / "calibration" / f"{method}-{target}-seed{seed}" / "run.json"
                if not path.exists():
                    failures.append(f"Missing reference arm: {method}-{target}-seed{seed}")
                    continue
                report = json.loads(path.read_text(encoding="utf-8"))
                if report["binding"]["config"] != config_for(protocol, protocol_sha, method, seed, target, "calibration"):
                    failures.append(f"Reference arm config mismatch: {path.parent.name}")
                    continue
                if not report["objective_coverage_pass"] or report["mae_kwh"] is None:
                    failures.append(f"Reference arm null or low coverage: {path.parent.name}")
                    continue
                current[(method, target, seed)] = report["mae_kwh"]
                if method == "fixed":
                    cell_deltas.append({"target": target, "seed": seed, "signed_delta_kwh": report["mae_kwh"] - reference[(target, seed)]})
    tolerance = protocol["persistent_experiment"]["cross_runtime_comparability"]
    if len(current) == 24:
        macro = {method: statistics.mean(current[(method, target, seed)] for target in TARGETS for seed in SEEDS) for method in ("fixed", "immediate")}
        macro_deltas = {"fixed": macro["fixed"] - expected_fixed_macro, "immediate": macro["immediate"] - expected_immediate_macro}
        if any(abs(row["signed_delta_kwh"]) > tolerance["max_abs_cell_mae_delta_kwh"] for row in cell_deltas):
            failures.append("Fixed reference per-cell engineering tolerance exceeded")
        if any(abs(value) > tolerance["max_abs_station_first_macro_mae_delta_kwh"] for value in macro_deltas.values()):
            failures.append("Historical macro engineering tolerance exceeded")
    else:
        macro, macro_deltas = {}, {}
    result = {
        "schema": "issue99-reference-comparability-v1",
        "status": "PASS" if not failures else "BLOCKED",
        "protocol_sha256": protocol_sha,
        "scope": "Historical PR102 comparability across possible runtime changes; not exact replication and not the promotion decision.",
        "cell_deltas": cell_deltas,
        "macro_mae_kwh": macro,
        "macro_signed_deltas_kwh": macro_deltas,
        "failures": failures,
    }
    write_new(output / "reference-comparability.json", result)
    print(json.dumps(result, allow_nan=False), flush=True)
    return result


def summarize(output: Path, protocol_path: Path) -> dict:
    locked, protocol, protocol_sha = lock_protocol(protocol_path, output)
    del locked
    phase_root = output / "calibration"
    cell = {}
    failures = []
    for target in TARGETS:
        for seed in SEEDS:
            common = None
            for method in METHODS:
                path = phase_root / f"{method}-{target}-seed{seed}"
                report_path = path / "run.json"
                if not report_path.exists():
                    failures.append(f"Missing run: {path.name}")
                    continue
                report = json.loads(report_path.read_text(encoding="utf-8"))
                if report["binding"]["config"] != config_for(protocol, protocol_sha, method, seed, target, "calibration"):
                    failures.append(f"Config mismatch: {path.name}")
                    continue
                actual_scores = scores(path)
                requested = set(protocol["calibration_origins"][target])
                selected = requested & actual_scores.keys()
                minimum = protocol["minimum_scored_days"]["calibration"][target]
                if len(selected) < minimum or report["mae_kwh"] is None:
                    failures.append(f"Coverage or null objective: {path.name}")
                    continue
                recomputed = statistics.mean(actual_scores[origin] for origin in selected)
                if not math.isclose(recomputed, report["mae_kwh"], rel_tol=1e-6, abs_tol=1e-6):
                    failures.append(f"Saved score mismatch: {path.name}")
                    continue
                if common is None:
                    common = selected
                elif common != selected:
                    failures.append(f"Unpaired origins: {target} seed{seed}")
                cell[(method, target, seed)] = {
                    "mae_kwh": recomputed,
                    "scored_days": len(selected),
                    "wall_seconds": report["invocation_wall_seconds"],
                    "run_sha256": digest(report_path),
                }
    gate = protocol["persistent_experiment"]["go_to_later_gate"]
    if len(cell) != 48:
        failures.append(f"Expected 48 complete cells, found {len(cell)}")
    by_method = {}
    by_target = {}
    by_seed = {}
    if not failures:
        for method in METHODS:
            by_method[method] = statistics.mean(cell[(method, target, seed)]["mae_kwh"] for target in TARGETS for seed in SEEDS)
        for target in TARGETS:
            by_target[target] = {method: statistics.mean(cell[(method, target, seed)]["mae_kwh"] for seed in SEEDS) for method in METHODS}
        for seed in SEEDS:
            by_seed[str(seed)] = {method: statistics.mean(cell[(method, target, seed)]["mae_kwh"] for target in TARGETS) for method in METHODS}
        wall_ratio = sum(cell[("persistent", target, seed)]["wall_seconds"] for target in TARGETS for seed in SEEDS) / sum(cell[("fixed", target, seed)]["wall_seconds"] for target in TARGETS for seed in SEEDS)
        checks = {
            "macro_gain": by_method["fixed"] - by_method["persistent"] >= gate["macro_mae_improvement_vs_fixed_at_least_kwh"],
            "target_harm": all(by_target[target]["persistent"] - by_target[target]["fixed"] <= gate["max_target_mean_mae_harm_vs_fixed_kwh"] for target in TARGETS),
            "seed_macro": sum(by_seed[str(seed)]["persistent"] < by_seed[str(seed)]["fixed"] for seed in SEEDS) >= gate["min_seed_macro_improvements_vs_fixed"],
            "wall_ratio": wall_ratio <= gate["persistent_wall_time_over_fixed_max"],
            "coverage": True,
        }
    else:
        wall_ratio = None
        checks = {name: False for name in ("macro_gain", "target_harm", "seed_macro", "wall_ratio", "coverage")}
    result = {
        "schema": "issue99-persistent-calibration-gate-v1",
        "protocol_sha256": protocol_sha,
        "go_to_later": all(checks.values()),
        "checks": checks,
        "failures": failures,
        "macro_mae_kwh": by_method,
        "target_mae_kwh": by_target,
        "seed_macro_mae_kwh": by_seed,
        "persistent_over_fixed_invocation_wall_ratio": wall_ratio,
        "cells": [
            {"method": method, "target": target, "seed": seed, **cell[(method, target, seed)]}
            for target in TARGETS for seed in SEEDS for method in METHODS
            if (method, target, seed) in cell
        ],
    }
    path = output / "calibration-gate.json"
    if path.exists():
        raise FileExistsError(path)
    write_new(path, result)
    print(json.dumps({key: result[key] for key in ("go_to_later", "checks", "failures", "macro_mae_kwh", "target_mae_kwh", "seed_macro_mae_kwh", "persistent_over_fixed_invocation_wall_ratio")}, allow_nan=False), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--phase", choices=("pilot", "calibration_reference", "reference_guard", "calibration_remaining", "gate", "evaluation"), required=True)
    args = parser.parse_args()
    if args.phase == "gate":
        summarize(args.output, args.protocol)
    elif args.phase == "reference_guard":
        reference_guard(args.output, args.protocol)
    else:
        result = run_phase(args.stage, args.protocol, args.output, args.phase, args.device)
        print(json.dumps(result, allow_nan=False))
        if result["errors"]:
            raise RuntimeError(f"{result['errors']} {args.phase} jobs failed; partial artifacts preserved")


if __name__ == "__main__":
    main()
