"""Execute the finite owner-authorized issue99 Development study, never Final."""

import argparse
import copy
import json
import math
import statistics
import time
from pathlib import Path

import torch

from ev_models.checkpoint import digest
from ev_runner.continuous_run import code_identity, execute
from ev_runner.replay import Replay
from ev_search.comparison import execute_job, plan_jobs
from ev_search.comparison_verify import _scores, _verify_commit_chain, verify_matrix
from ev_search.execute import FixedMatrixEvaluator, aggregate_matrix
from ev_search.fixed import FixedSearchConfig
from ev_search.ledger import FixedLedger, run_bounded_search
from tools.issue99_study_support import PreparedInputs

TARGETS = ("1405", "2152", "1153", "1693")
SEEDS = (42, 43, 44)


def save(path: Path, value: object) -> None:
    """Create a new, JSON-safe evidence record; never overwrite a previous phase."""
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def emit(phase: str, **fields: object) -> None:
    print(json.dumps({"phase": phase, **fields}, allow_nan=False), flush=True)


def template(protocol: dict, protocol_sha: str) -> dict:
    training = {
        "seed": 42,
        "epochs": 3,
        "batch_size": 64,
        "learning_rate": 0.001,
        "epsilon": 0.001,
        "head_width": 64,
    }
    return {
        "schema": "issue99-study-v1",
        "phase": "calibration",
        "targets": list(TARGETS),
        "initial_training": training,
        "online_training": {**training, "epochs": 1},
        "window_rule": {
            "older_count": 2,
            "newer_count": 1,
            "upper_bound": protocol["fixed_search"]["maximum_upper"],
            "meta_step_size": 0.01,
            "epsilon": 0.001,
        },
        "initial_lambda": 0.0,
        "cadence": 1,
        "frozen_lambda": True,
        "replay_days": 90,
        "protocol_sha256": protocol_sha,
        "objective_origins": [],
        "state_retention": "latest",
        "diagnostic_every": 7,
    }


def verify_run(path: Path, report: dict, replay: Replay) -> dict:
    """Recompute saved-prediction errors and authenticate every tick commitment."""
    _verify_commit_chain(path, report)
    issued, scores = _scores(path, {"family": "continuous"}, replay)
    if len(issued) != report["issued_days"] or len(scores) != report["scored_days"]:
        raise ValueError("Independent coverage differs from run")
    requested = set(report["binding"]["config"]["objective_origins"])
    selected = requested & scores.keys()
    if report["mae_kwh"] is not None:
        value = sum(scores[o][0] for o in selected) / len(selected)
        if not math.isclose(value, report["mae_kwh"], rel_tol=1e-6, abs_tol=1e-6):
            raise ValueError("Independent objective differs from run")
    return {"issued": len(issued), "scores_recomputed": len(scores), "status": "PASS"}


def matrix(
    inputs: PreparedInputs,
    replays: dict[str, Replay],
    sources: dict,
    protocol_path: Path,
    study: dict,
    root: Path,
    *,
    device: str,
    pilot: bool = False,
) -> dict:
    root.mkdir(exist_ok=False)
    rows, gradients = [], []
    for target in TARGETS:
        for seed in SEEDS:
            config = copy.deepcopy(study)
            for name in ("initial_training", "online_training"):
                config[name]["seed"] = seed
            config["objective_origins"] = (
                []
                if pilot
                else json.loads(protocol_path.read_text())["calibration_origins"][target]
            )
            config["phase"] = "pilot" if pilot else "calibration"
            path = root / f"target-{target}-seed-{seed}"
            source = sources[str(seed)]
            report = execute(
                inputs,
                target,
                Path(source["path"]),
                source["sha256"],
                config,
                path,
                device=device,
                protocol_path=protocol_path,
                prepared_replay=replays[target],
                stop_after_ticks=10 if pilot else None,
            )
            checked = verify_run(path, report, replays[target])
            for tick in sorted(path.glob("tick-*")):
                for line in (tick / "events.jsonl").read_text().splitlines():
                    event = json.loads(line)
                    if event["event"] == "meta_decision":
                        gradients.append(abs(event["hypergradient"]))
            rows.append(
                {
                    "target": target,
                    "seed": seed,
                    "mae_kwh": report["mae_kwh"],
                    "objective_missing_origins": report["objective_missing_origins"],
                    "run_path": str(path),
                    "run_sha256": digest(path / "run.json"),
                    "verification": checked,
                    "cost_seconds": report["cost_seconds"],
                    "invocation_wall_seconds": report["invocation_wall_seconds"],
                }
            )
    result = {"runs": rows, "absolute_hypergradients": gradients}
    if not pilot:
        result.update(aggregate_matrix(rows))
    save(root / "matrix.json", result)
    return result


def select_fixed(events: list[dict], positive_lower: float) -> dict:
    """Select by calibration fitness and predeclared measured-harm bracket rule."""
    finite = [e for e in events if e["status"] == "complete"]
    if not finite:
        raise ValueError("No complete fixed trial; inspect preserved ledger")
    best = min(finite, key=lambda e: (e["outcome"]["objective_mae_kwh"], e["lambda"]))
    zero = next((e for e in finite if e["lambda"] == 0), None)
    if zero is None:
        raise ValueError("No complete lambda0 baseline")
    upper = max(e["lambda"] for e in finite)
    harmful = [
        e["lambda"]
        for e in finite
        if e["lambda"] > best["lambda"]
        and e["outcome"]["objective_mae_kwh"] > zero["outcome"]["objective_mae_kwh"]
    ]
    cap = min(harmful) if harmful else upper
    cap = max(cap, best["lambda"], positive_lower)
    return {
        "selected_lambda": best["lambda"],
        "mae_kwh": best["outcome"]["objective_mae_kwh"],
        "lambda0_mae_kwh": zero["outcome"]["objective_mae_kwh"],
        "controller_upper_bound": cap,
        "upper_boundary_unresolved": best["lambda"] >= upper * 0.9,
        "finite_trials": len(finite),
        "all_trials": len(events),
        "selected_trial": best["trial"],
    }


def run(args: argparse.Namespace) -> None:
    started = time.perf_counter()
    torch.set_num_threads(1)
    protocol = json.loads(args.protocol.read_text())
    if protocol["status"] != "locked_owner_approved" or not protocol["owner_authorization"]:
        raise ValueError("Owner execution authorization required")
    args.output.mkdir(exist_ok=False)
    save(args.output / "protocol-lock.json", protocol)
    protocol_path = args.output / "protocol-lock.json"
    protocol_sha = digest(protocol_path)
    sources = json.loads(args.sources.read_text())
    save(args.output / "source-bindings.json", sources)
    for source in sources.values():
        if digest(Path(source["path"])) != source["sha256"]:
            raise ValueError("Source checkpoint changed")
    inputs = PreparedInputs(args.inputs, protocol["input_manifest_sha256"])
    if inputs.source_hash != protocol["source_population_sha256"]:
        raise ValueError("Source population changed")
    replays = {target: Replay(inputs, target, 90) for target in TARGETS}
    study = template(protocol, protocol_sha)
    search = FixedSearchConfig(**protocol["fixed_search"])
    fixed_root = args.output / "fixed"
    binding = {
        "protocol_sha256": protocol_sha,
        "sources": sources,
        "input_manifest_sha256": inputs.sha256,
        "code": code_identity(),
    }
    ledger = FixedLedger(fixed_root, search, binding=binding)
    evaluator = FixedMatrixEvaluator(
        inputs, protocol_path, study, sources, fixed_root, device=args.device
    )
    while True:
        new = run_bounded_search(ledger, evaluator, max_new_trials=1)
        if not new:
            break
        event = new[0]
        if event["status"] == "complete":
            for row in event["outcome"]["runs"]:
                path = Path(row["run_path"])
                verify_run(
                    path, json.loads((path / "run.json").read_text()), replays[row["target"]]
                )
        emit(
            "fixed",
            trial=event["trial"],
            role=event["role"],
            weight=event["lambda"],
            status=event["status"],
            mae_kwh=event["outcome"]["objective_mae_kwh"],
        )
    selection = select_fixed(ledger.completed(), search.positive_lower)
    best = next(e for e in ledger.completed() if e["trial"] == selection["selected_trial"])
    cap = selection["controller_upper_bound"]
    save(args.output / "fixed-selection.json", selection)
    emit("fixed_selected", **selection)
    controller = copy.deepcopy(study)
    controller["initial_lambda"] = best["lambda"]
    controller["frozen_lambda"] = False
    controller["window_rule"]["upper_bound"] = cap
    pilot = matrix(
        inputs,
        replays,
        sources,
        protocol_path,
        controller,
        args.output / "controller-scale-pilot",
        device=args.device,
        pilot=True,
    )
    g = statistics.median(pilot["absolute_hypergradients"])
    if not math.isfinite(g) or g <= 0:
        raise ValueError("Controller pilot has no finite nonzero median signal")
    candidates = []
    for fraction in protocol["controller_selection"]["step_fractions"]:
        eta = fraction * max(best["lambda"], search.positive_lower) / g
        for cadence in protocol["controller_selection"]["cadences"]:
            config = copy.deepcopy(controller)
            config["cadence"] = cadence
            config["window_rule"]["meta_step_size"] = eta
            index = len(candidates)
            result = matrix(
                inputs,
                replays,
                sources,
                protocol_path,
                config,
                args.output / f"controller-calibration-{index:02d}",
                device=args.device,
            )
            candidate = {
                "index": index,
                "fraction": fraction,
                "eta": eta,
                "cadence": cadence,
                "mae_kwh": result["objective_mae_kwh"],
                "config": config,
            }
            candidates.append(candidate)
            emit("controller_calibration", **{k: v for k, v in candidate.items() if k != "config"})
    valid = [c for c in candidates if c["mae_kwh"] is not None]
    if not valid:
        raise ValueError("No scoreable controller recipe")
    chosen = min(valid, key=lambda c: (c["mae_kwh"], c["eta"], -c["cadence"]))
    save(
        args.output / "controller-selection.json",
        {"candidates": candidates, "selected": chosen, "pilot_median_absolute_hypergradient": g},
    )
    config = copy.deepcopy(chosen["config"])
    config["phase"] = "evaluation"
    historical = json.loads(args.discrete.read_text())
    lock = {
        "schema": "issue99-comparison-lock-v1",
        "status": "locked_owner_approved",
        "protocol_sha256": protocol_sha,
        "selected_fixed_lambda": best["lambda"],
        "controller_initial_lambda": best["lambda"],
        "study_template": config,
        "discrete_config": historical,
        "owner_authorization": protocol["owner_authorization"],
    }
    lock_path = args.output / "controller-lock.json"
    save(lock_path, lock)
    jobs = plan_jobs(inputs, protocol_path, lock_path, sources)
    save(args.output / "comparison-jobs.json", jobs)
    comparison = args.output / "comparison"
    comparison.mkdir()
    for job in jobs:
        execute_job(
            job,
            inputs,
            protocol_path,
            lock_path,
            comparison,
            device=args.device,
            prepared_replay=replays[job["target"]],
        )
        emit("comparison", job=job["job_id"], reused=job["reuse_job_id"])
    verified = verify_matrix(jobs, comparison, inputs, protocol_path, lock_path)
    save(args.output / "comparison-verification.json", verified)
    inputs.reauthenticate()
    save(
        args.output / "completion.json",
        {
            "status": "completed",
            "scope": "exploratory Development only",
            "wall_seconds": time.perf_counter() - started,
            "protocol_sha256": protocol_sha,
            "comparison_verification_sha256": digest(args.output / "comparison-verification.json"),
        },
    )
    emit("complete", aggregate=verified.get("aggregate_mae_kwh", verified))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "protocol", "sources", "discrete", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--device", choices=("cuda",), default="cuda")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
