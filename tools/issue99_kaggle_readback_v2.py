"""Read back saved issue #99 protocol-v2 comparison inside Kaggle, without training."""

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

NOTEBOOK_ROOT = Path(
    "/kaggle/input/notebooks/hungluongduc/issue99-source10-2798384-paired-comparison-v2"
)
COMPARISON = NOTEBOOK_ROOT / "issue99-comparison-v2"
STAGE = NOTEBOOK_ROOT / "issue99-stage-v2"
OUTPUT = Path("/kaggle/working/issue99-comparison-v2-readback.json")
PROTOCOL_SHA = "f104d8809e04d0cde7d8982efd8146788f32c3c9a1c561ee9309891e6b040eb0"
LOCK_SHA = "209102126ca696c5da2e959b053cc413d0e8d59fda3f92b30168a7a483577269"
VERIFICATION_SHA = "c3038079cd65f575851dfd53be139017c6ad95aad087d7a3817dcd34a3d6bfed"
CODE_COMMIT = "27983845b5d446e3915b0b4353570466f1da23ef"
INPUT_MANIFEST_SHA = "66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9"
SOURCES = {
    "42": "a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b",
    "43": "2ad6ed33fb7e692eae5f8db6be075ce43564851f70390d19edb4314052a17f5f",
    "44": "6f475e54768322c5b51f5837d6ce7e863cb9ef6d33aec05b4a1c2468cd0285a5",
}
FIXED_LAMBDA = 0.5634538227695682
CONTROLLER_INITIAL_LAMBDA = 0.1
METHODS = ("lambda0", "fixed", "discrete", "continuous", "frozen_lambda")
TARGETS = ("1405", "2152", "1153", "1693")
SEEDS = (42, 43, 44)


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require_sha(path: Path, expected: str) -> None:
    if sha256(path) != expected:
        raise ValueError(f"SHA-256 differs: {path}")


def finite_cost(report: dict, family: str) -> tuple[float, dict, int, int]:
    wall_key, cost_key = (
        ("elapsed_seconds", "cost")
        if family == "discrete"
        else ("invocation_wall_seconds", "cost_seconds")
    )
    wall = report[wall_key]
    components = report[cost_key]
    if (
        isinstance(wall, bool)
        or not isinstance(wall, (int, float))
        or not math.isfinite(wall)
        or wall < 0
        or not isinstance(components, dict)
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
            for value in components.values()
        )
    ):
        raise ValueError("Invalid measured run cost")
    peak = report["gpu_peak_allocated_bytes"]
    reserved = report["gpu_peak_reserved_bytes"]
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (peak, reserved)
    ):
        raise ValueError("Invalid measured GPU memory")
    return float(wall), components, peak, reserved


def check_dispatch(root: Path, jobs: list[dict]) -> dict:
    path = root / "dispatch.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    completed = [event["job_id"] for event in events if event.get("event") == "job_completed"]
    failures = {"job_failed", "stopped_budget", "matrix_incomplete", "matrix_verification_failed"}
    matrix = [event for event in events if event.get("event") == "matrix_verified"]
    finished = [event for event in events if event.get("event") == "version_finished"]
    if (
        len(completed) != 60
        or set(completed) != {job["job_id"] for job in jobs}
        or any(event.get("event") in failures for event in events)
        or len(matrix) != 1
        or matrix[0]["verification_sha256"] != VERIFICATION_SHA
        or len(finished) != 1
    ):
        raise ValueError("Saved dispatch does not attest 60 completed and verified jobs")
    return {
        "dispatch_sha256": sha256(path),
        "gpu_seconds_this_version": finished[0]["gpu_seconds_this_version"],
        "gpu_seconds_cumulative_budget_debit": finished[0]["gpu_seconds_cumulative"],
    }


def validate_jobs(jobs: list[dict]) -> None:
    expected = {
        f"{method}-{target}-seed{seed}"
        for method in METHODS
        for target in TARGETS
        for seed in SEEDS
    }
    if len(jobs) != 60 or {job["job_id"] for job in jobs} != expected:
        raise ValueError("Incomplete or duplicate 60-cell job matrix")
    for job in jobs:
        method, target, seed = job["method"], job["target"], job["seed"]
        if (
            job["job_id"] != f"{method}-{target}-seed{seed}"
            or job["protocol_sha256"] != PROTOCOL_SHA
            or job["lock_sha256"] != LOCK_SHA
            or job["source_sha256"] != SOURCES[str(seed)]
            or job["evaluation_origins"] != sorted(job["evaluation_origins"])
            or len(set(job["evaluation_origins"])) != 28
        ):
            raise ValueError("Job identity, source or locked evaluation origin differs")
        config = job["config"]
        if method == "discrete":
            if job["family"] != "discrete" or config["method"]["name"] != "adaptive":
                raise ValueError("Historical discrete job differs")
        else:
            expected_lambda = (
                0.0
                if method == "lambda0"
                else FIXED_LAMBDA
                if method == "fixed"
                else CONTROLLER_INITIAL_LAMBDA
            )
            if (
                job["family"] != "continuous"
                or config["initial_lambda"] != expected_lambda
                or config["frozen_lambda"] != (method != "continuous")
                or config["phase"] != "evaluation"
                or config["protocol_sha256"] != PROTOCOL_SHA
                or config["objective_origins"] != job["evaluation_origins"]
            ):
                raise ValueError("Method configuration differs from locked comparison")


def read_scores(run_path: Path, job: dict, replay, report: dict) -> dict[str, float]:
    """Independently score authenticated saved vectors at their actual tick dates."""
    forecasts = {}
    errors = {}
    for index, tick in enumerate(sorted(run_path.glob("tick-*"))):
        tick_time = replay.start + index * timedelta(days=1)
        forecast_path = tick / "forecasts.json"
        forecast = json.loads(forecast_path.read_text())
        if forecast:
            origin = forecast["origin"]
            if datetime.fromisoformat(origin) != tick_time or origin in forecasts:
                raise ValueError("Forecast origin differs from tick or is duplicated")
            forecasts[origin] = (forecast, sha256(forecast_path))
        for line in (tick / "events.jsonl").read_text().splitlines():
            event = json.loads(line)
            if event.get("event") != "score":
                continue
            origin = event["origin"]
            if origin not in forecasts or origin in errors:
                raise ValueError("Unissued or duplicate score")
            issued, forecast_sha = forecasts[origin]
            as_of = datetime.fromisoformat(event["as_of"])
            if (
                event["prediction_sha256"] != forecast_sha
                or as_of != tick_time
                or datetime.fromisoformat(origin) >= as_of
            ):
                raise ValueError("Score does not match issuance hash or chronological tick")
            labels = replay.labels(datetime.fromisoformat(origin), as_of)
            if (
                labels.status != "complete"
                or labels.values is None
                or len(labels.values) != 24
                or labels.available_at is None
                or labels.available_at > as_of
            ):
                raise ValueError("Score used unavailable or incomplete labels")
            if job["family"] == "discrete":
                levels = report["candidate_levels"]
                if issued["active"] != event["issued_active"] or len(issued["predictions"]) != len(
                    levels
                ):
                    raise ValueError("Discrete active forecast differs")
                prediction = issued["predictions"][levels.index(issued["active"])]
            else:
                prediction = issued["prediction"]
            if len(prediction) != 24 or any(not math.isfinite(value) for value in prediction):
                raise ValueError("Invalid saved prediction vector")
            mae = (
                sum(
                    abs(value * replay.scale - label)
                    for value, label in zip(prediction, labels.values, strict=True)
                )
                / 24
            )
            if job["family"] == "discrete":
                index_active = levels.index(issued["active"])
                recorded = event["mae_scaled"][index_active] * replay.scale
            else:
                recorded = event["mae_kwh"]
            if not math.isclose(mae, recorded, rel_tol=1e-6, abs_tol=1e-6):
                raise ValueError("Saved score differs from prediction and arrived labels")
            errors[origin] = mae
    if len(forecasts) != report["issued_days"] or len(errors) != report["scored_days"]:
        raise ValueError("Run coverage differs from saved forecasts and scores")
    return errors


def summarize(jobs: list[dict], root: Path, inputs, saved: dict) -> dict:
    """Recompute cell means from saved vectors/arrived labels and measured run costs."""
    from ev_models.checkpoint import digest
    from ev_runner.replay import Replay
    from ev_search.comparison import event_hashes, verify_run_binding
    from ev_search.comparison_verify import _verify_commit_chain

    replays = {target: Replay(inputs, target, 90) for target in TARGETS}
    cells = {}
    costs = defaultdict(
        lambda: {
            "logical_cells": 0,
            "executions": 0,
            "reused": 0,
            "wall_seconds": 0.0,
            "gpu_peak_allocated_bytes_max": 0,
            "gpu_peak_reserved_bytes_max": 0,
            "components_seconds": defaultdict(float),
        }
    )
    receipt_hashes = {}
    for job in jobs:
        job_id = job["job_id"]
        receipt_path = root / job_id / "job.json"
        receipt = json.loads(receipt_path.read_text())
        if receipt["job"] != job or receipt["reused_from"] != job["reuse_job_id"]:
            raise ValueError(f"Job identity differs: {job_id}")
        run_path = root / receipt["run_path"]
        if receipt["run_path"] != f"{job['reuse_job_id'] or job_id}/run":
            raise ValueError(f"Unexpected run path: {job_id}")
        if digest(run_path / "run.json") != receipt["run_sha256"]:
            raise ValueError(f"Run report hash differs: {job_id}")
        if event_hashes(run_path) != receipt["event_sha256"]:
            raise ValueError(f"Committed artifact hashes differ: {job_id}")
        receipt_hashes[job_id] = sha256(receipt_path)
        report = json.loads((run_path / "run.json").read_text())
        verify_run_binding(job, report, inputs)
        _verify_commit_chain(run_path, report)
        replay = replays[job["target"]]
        end = replay.stop + (int(replay.delay / timedelta(days=1)) + 1) * timedelta(days=1)
        expected_ticks = int((end - replay.start) / timedelta(days=1)) + 1
        if len(list(run_path.glob("tick-*"))) != expected_ticks:
            raise ValueError(f"Incomplete replay tick horizon: {job_id}")
        errors = read_scores(run_path, job, replay, report)
        origins = set(job["evaluation_origins"])
        if len(origins) != 28 or origins - errors.keys():
            raise ValueError(f"Evaluation coverage is not 28/28: {job_id}")
        mean = sum(errors[origin] for origin in origins) / 28
        cells[(job["method"], job["target"], job["seed"])] = mean
        group = costs[job["method"]]
        group["logical_cells"] += 1
        if receipt["reused_from"] is not None:
            group["reused"] += 1
        else:
            wall, components, peak, reserved = finite_cost(report, job["family"])
            group["executions"] += 1
            group["wall_seconds"] += wall
            group["gpu_peak_allocated_bytes_max"] = max(group["gpu_peak_allocated_bytes_max"], peak)
            group["gpu_peak_reserved_bytes_max"] = max(
                group["gpu_peak_reserved_bytes_max"], reserved
            )
            for name, seconds in components.items():
                group["components_seconds"][name] += seconds
    if len(cells) != 60 or len(receipt_hashes) != 60:
        raise ValueError("Comparison matrix is incomplete")
    target_means = {
        target: {
            method: sum(cells[method, target, seed] for seed in SEEDS) / len(SEEDS)
            for method in METHODS
        }
        for target in TARGETS
    }
    macro = {
        method: sum(target_means[target][method] for target in TARGETS) / len(TARGETS)
        for method in METHODS
    }
    deltas = {
        target: {
            method: {
                str(seed): cells[method, target, seed] - cells["lambda0", target, seed]
                for seed in SEEDS
            }
            for method in METHODS
        }
        for target in TARGETS
    }

    def near(actual: float, expected: float) -> bool:
        return math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6)

    if any(
        not near(macro[method], saved["aggregate_mae_kwh"][method])
        or any(
            not near(target_means[target][method], saved["targets"][target][method])
            or any(
                not near(
                    deltas[target][method][str(seed)],
                    saved["paired_mae_delta_vs_lambda0_kwh"][target][method][str(seed)],
                )
                for seed in SEEDS
            )
            for target in TARGETS
        )
        for method in METHODS
    ):
        raise ValueError("Recomputed paired metrics differ from saved verification")
    compact_costs = {
        method: {**value, "components_seconds": dict(value["components_seconds"])}
        for method, value in costs.items()
    }
    return {
        "status": "PASS",
        "verified_jobs": len(receipt_hashes),
        "evaluation_coverage_each": "28/28",
        "receipt_index_sha256": hashlib.sha256(
            json.dumps(receipt_hashes, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "aggregate_mae_kwh": macro,
        "target_mae_kwh": target_means,
        "paired_mae_delta_vs_lambda0_kwh": deltas,
        "run_costs": compact_costs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook-root", type=Path, default=NOTEBOOK_ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    comparison = args.notebook_root / "issue99-comparison-v2"
    stage = args.notebook_root / "issue99-stage-v2"
    verification = comparison / "verification.json"
    require_sha(verification, VERIFICATION_SHA)
    if (stage / "code/.issue99-code-commit").read_text().strip() != CODE_COMMIT:
        raise ValueError("Saved scorer commit differs")
    for seed in SEEDS:
        require_sha(stage / "sources" / f"seed{seed}" / "epoch-10.pt", SOURCES[str(seed)])
    sys.path.insert(0, str(stage / "code"))
    from ev_models.data import InputRun

    inputs = InputRun(stage / "inputs", INPUT_MANIFEST_SHA)
    jobs = [
        json.loads((comparison / job_id / "job.json").read_text())["job"]
        for job_id in sorted(
            f"{method}-{target}-seed{seed}"
            for method in METHODS
            for target in TARGETS
            for seed in SEEDS
        )
    ]
    validate_jobs(jobs)
    dispatch = check_dispatch(comparison, jobs)
    saved = json.loads(verification.read_text())
    if (
        saved["protocol_sha256"] != PROTOCOL_SHA
        or len(saved["coverage"]) != 60
        or {row["job_id"] for row in saved["coverage"]} != {job["job_id"] for job in jobs}
        or any(row["evaluation_scored_days"] != 28 for row in saved["coverage"])
    ):
        raise ValueError("Saved E verification identity or coverage differs")
    result = summarize(jobs, comparison, inputs, saved)
    result.update(
        {
            "schema": "issue99-comparison-v2-kaggle-readback-v1",
            "protocol_sha256": PROTOCOL_SHA,
            "lock_sha256": LOCK_SHA,
            "saved_verification_sha256": VERIFICATION_SHA,
            **dispatch,
        }
    )
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "verified_jobs": result["verified_jobs"],
                "aggregate_mae_kwh": result["aggregate_mae_kwh"],
                "readback_sha256": sha256(args.output),
            },
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
