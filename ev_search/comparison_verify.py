"""Read-only paired Development verification from saved issue #99 runs."""

import json
import math
from datetime import datetime
from pathlib import Path

from ev_models.checkpoint import digest
from ev_runner.replay import Replay
from ev_search.comparison import METHODS, SEEDS, TARGETS, event_hashes, verify_run_binding


def _same(actual: float, expected: float) -> bool:
    return math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6)


def _scores(
    run_path: Path, job: dict, replay: Replay
) -> tuple[set[str], dict[str, tuple[float, float]]]:
    issued = set()
    errors = {}
    forecasts = {}
    for tick in sorted(run_path.glob("tick-*")):
        forecast_path = tick / "forecasts.json"
        forecast = json.loads(forecast_path.read_text())
        if forecast:
            origin = forecast["origin"]
            if origin in issued:
                raise ValueError("Duplicate issued origin")
            issued.add(origin)
            forecasts[origin] = (forecast, digest(forecast_path))
        for line in (tick / "events.jsonl").read_text().splitlines():
            event = json.loads(line)
            if event["event"] != "score":
                continue
            origin = event["origin"]
            if origin in errors or origin not in forecasts:
                raise ValueError("Duplicate or unissued scored origin")
            forecast, prediction_sha = forecasts[origin]
            if event["prediction_sha256"] != prediction_sha:
                raise ValueError("Score prediction hash differs from issued vector")
            as_of = datetime.fromisoformat(event["as_of"])
            label = replay.labels(datetime.fromisoformat(origin), as_of)
            if label.status != "complete" or label.values is None or len(label.values) != 24:
                raise ValueError("Score lacks complete arrived authenticated labels")
            if label.available_at is None or label.available_at > as_of:
                raise ValueError("Scored label predates its availability")
            y = label.values
            if job["family"] == "discrete":
                report_levels = job["report_levels"]
                index = report_levels.index(event["issued_active"])
                if event["issued_active"] != forecast["active"] or len(
                    forecast["predictions"]
                ) != len(report_levels):
                    raise ValueError("Discrete active branch differs from issued forecast")
                for branch, prediction in enumerate(forecast["predictions"]):
                    mae, mse = _vector_error(prediction, y, replay.scale)
                    if not _same(event["mae_scaled"][branch] * replay.scale, mae) or not _same(
                        event["mse_scaled"][branch] * replay.scale**2, mse
                    ):
                        raise ValueError("Discrete score differs from forecast and labels")
                value = _vector_error(forecast["predictions"][index], y, replay.scale)
            else:
                value = _vector_error(forecast["prediction"], y, replay.scale)
                if not _same(event["mae_kwh"], value[0]) or not _same(event["mse_kwh2"], value[1]):
                    raise ValueError("Continuous score differs from forecast and labels")
            errors[origin] = value
    return issued, errors


def _vector_error(
    prediction: list[float], labels: tuple[float, ...], scale: float
) -> tuple[float, float]:
    if len(prediction) != 24 or any(not math.isfinite(x) for x in prediction):
        raise ValueError("Invalid saved 24-hour forecast")
    differences = [p * scale - y for p, y in zip(prediction, labels, strict=True)]
    return sum(abs(x) for x in differences) / 24, sum(x * x for x in differences) / 24


def _verify_commit_chain(run_path: Path, report: dict) -> None:
    if json.loads((run_path / "binding.json").read_text()) != report["binding"]:
        raise ValueError("Run binding file differs from report")
    if list(run_path.glob(".pending-*")):
        raise ValueError("Uncommitted tick in completed comparison")
    ticks = sorted(run_path.glob("tick-*"))
    if not ticks:
        raise ValueError("Comparison run has no committed ticks")
    previous = "0" * 64
    retention = report["binding"]["config"].get("state_retention", "all")
    for index, tick in enumerate(ticks):
        if tick.name != f"tick-{index:04d}":
            raise ValueError("Missing or reordered tick")
        meta = json.loads((tick / "commit.json").read_text())
        if (
            meta["index"] != index
            or meta["previous"] != previous
            or set(meta["files"]) != {"state.pt", "events.jsonl", "forecasts.json"}
        ):
            raise ValueError("Broken tick commit chain")
        for name, expected in meta["files"].items():
            path = tick / name
            if (
                name == "state.pt"
                and retention == "latest"
                and index < len(ticks) - 1
                and not path.exists()
            ):
                continue
            if digest(path) != expected:
                raise ValueError("Changed committed tick artifact")
        previous = digest(tick / "commit.json")
    if report["commit_chain"] != previous:
        raise ValueError("Report commit chain differs")


def verify_matrix(jobs: list[dict], output_root: Path, inputs, protocol_path: Path) -> dict:
    """Require exact matrix, saved hashes and common scored origins before aggregation."""
    expected_ids = {
        f"{method}-{target}-seed{seed}"
        for method in METHODS
        for target in TARGETS
        for seed in SEEDS
    }
    if len(jobs) != len(expected_ids) or {job["job_id"] for job in jobs} != expected_ids:
        raise ValueError("Incomplete or duplicated comparison matrix")
    protocol_sha = digest(protocol_path)
    protocol = json.loads(protocol_path.read_text())
    by_target = {}
    details = []
    replay_by_target = {}
    for job in jobs:
        if job["protocol_sha256"] != protocol_sha:
            raise ValueError("Comparison protocol hash changed")
        result = json.loads((output_root / job["job_id"] / "job.json").read_text())
        if result["job"] != job:
            raise ValueError("Saved job identity changed")
        expected_run = f"{job['reuse_job_id'] or job['job_id']}/run"
        if result["run_path"] != expected_run:
            raise ValueError("Saved run path differs from pinned job")
        run_path = output_root / expected_run
        report_path = run_path / "run.json"
        if digest(report_path) != result["run_sha256"]:
            raise ValueError("Saved run report hash changed")
        if event_hashes(run_path) != result["event_sha256"]:
            raise ValueError("Saved forecast/score stream hash changed")
        report = json.loads(report_path.read_text())
        verify_run_binding(job, report, inputs)
        _verify_commit_chain(run_path, report)
        if result["reused_from"] != job["reuse_job_id"]:
            raise ValueError("Reuse identity changed")
        target = job["target"]
        if report["scheduled_days"] != 90:
            raise ValueError("Wrong comparison replay schedule")
        scale = inputs.entities[(*inputs.namespace, target)]["scale"]["energy_scale"]
        if not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
            raise ValueError("Invalid target scale")
        if target not in replay_by_target:
            replay_by_target[target] = Replay(inputs, target, 90)
        replay = replay_by_target[target]
        if not _same(replay.scale, scale):
            raise ValueError("Replay scale differs from identified target")
        scored_job = {**job, "report_levels": report.get("candidate_levels")}
        issued, errors = _scores(run_path, scored_job, replay)
        if report["issued_days"] != len(issued) or report["scored_days"] != len(errors):
            raise ValueError("Run reported coverage differs from events")
        requested = set(job["evaluation_origins"])
        if len(requested) != len(job["evaluation_origins"]):
            raise ValueError("Duplicate evaluation origin")
        evaluated = requested & errors.keys()
        minimum = protocol["minimum_scored_days"]["evaluation"][target]
        if not 1 <= minimum <= len(requested):
            raise ValueError("Invalid comparison coverage threshold")
        if job["family"] == "continuous":
            if (
                report["objective_scored_days"] != len(evaluated)
                or set(report["objective_missing_origins"]) != requested - evaluated
            ):
                raise ValueError("Continuous objective coverage differs from events")
            metric = (
                sum(errors[origin][0] for origin in evaluated) / len(evaluated)
                if len(evaluated) >= minimum
                else None
            )
            rmse = (
                math.sqrt(sum(errors[origin][1] for origin in evaluated) / len(evaluated))
                if metric is not None
                else None
            )
            if (
                report["objective_coverage_pass"] != (metric is not None)
                or (report["mae_kwh"] is None) != (metric is None)
                or (
                    metric is not None
                    and (
                        not _same(report["mae_kwh"], metric) or not _same(report["rmse_kwh"], rmse)
                    )
                )
            ):
                raise ValueError("Continuous objective metric differs from forecasts/labels")
        else:
            full_mae = sum(value[0] for value in errors.values()) / len(errors) if errors else None
            full_rmse = (
                math.sqrt(sum(value[1] for value in errors.values()) / len(errors))
                if errors
                else None
            )
            if (full_mae is None) != (report["active_mae_kwh"] is None) or (
                full_mae is not None
                and (
                    not _same(report["active_mae_kwh"], full_mae)
                    or not _same(report["active_rmse_kwh"], full_rmse)
                )
            ):
                raise ValueError("Discrete report metric differs from forecasts/labels")
        by_target.setdefault(target, []).append((job, evaluated, errors))
        details.append(
            {
                "job_id": job["job_id"],
                "issued_days": len(issued),
                "scored_days": len(errors),
                "evaluation_scored_days": len(evaluated),
            }
        )
    target_means = {}
    target_rmse = {}
    paired_deltas = {}
    for target, rows in by_target.items():
        origin_sets = [origins for _, origins, _ in rows]
        if any(origins != origin_sets[0] for origins in origin_sets[1:]):
            raise ValueError(f"Non-common scored origins for target {target}")
        minimum = protocol["minimum_scored_days"]["evaluation"][target]
        if len(origin_sets[0]) < minimum:
            target_means[target] = {method: None for method in METHODS}
            target_rmse[target] = {method: None for method in METHODS}
            paired_deltas[target] = {method: None for method in METHODS}
            continue
        target_means[target] = {}
        target_rmse[target] = {}
        paired_deltas[target] = {}
        per_cell = {}
        for job, origins, errors in rows:
            per_cell[(job["method"], job["seed"])] = (
                sum(errors[origin][0] for origin in origins) / len(origins),
                math.sqrt(sum(errors[origin][1] for origin in origins) / len(origins)),
            )
        for method in METHODS:
            if any((method, seed) not in per_cell for seed in SEEDS):
                raise ValueError("Missing paired seed")
            target_means[target][method] = sum(per_cell[(method, seed)][0] for seed in SEEDS) / len(
                SEEDS
            )
            target_rmse[target][method] = sum(per_cell[(method, seed)][1] for seed in SEEDS) / len(
                SEEDS
            )
            paired_deltas[target][method] = {
                str(seed): per_cell[(method, seed)][0] - per_cell[("lambda0", seed)][0]
                for seed in SEEDS
            }
    aggregate = {
        method: (
            sum(target_means[target][method] for target in TARGETS) / len(TARGETS)
            if all(target_means[target][method] is not None for target in TARGETS)
            else None
        )
        for method in METHODS
    }
    return {
        "schema": "issue99-paired-verification-v1",
        "protocol_sha256": protocol_sha,
        "targets": target_means,
        "target_rmse_kwh": target_rmse,
        "paired_mae_delta_vs_lambda0_kwh": paired_deltas,
        "aggregate_mae_kwh": aggregate,
        "coverage": details,
    }
