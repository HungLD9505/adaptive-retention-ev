"""Read-only paired Development verification from saved issue #99 runs."""

import json
import math
from pathlib import Path

from ev_models.checkpoint import digest
from ev_search.comparison import METHODS, SEEDS, TARGETS, event_hashes, verify_run_binding


def _scores(run_path: Path, job: dict, scale: float) -> tuple[set[str], dict[str, float]]:
    issued = set()
    errors = {}
    for tick in sorted(run_path.glob("tick-*")):
        forecast = json.loads((tick / "forecasts.json").read_text())
        if forecast:
            origin = forecast["origin"]
            if origin in issued:
                raise ValueError("Duplicate issued origin")
            issued.add(origin)
        for line in (tick / "events.jsonl").read_text().splitlines():
            event = json.loads(line)
            if event["event"] != "score":
                continue
            origin = event["origin"]
            if origin in errors or origin not in issued:
                raise ValueError("Duplicate or unissued scored origin")
            if job["family"] == "discrete":
                report_levels = job["report_levels"]
                index = report_levels.index(event["issued_active"])
                value = event["mae_scaled"][index] * scale
            else:
                value = event["mae_kwh"]
            if not math.isfinite(value) or value < 0:
                raise ValueError("Invalid scored MAE")
            errors[origin] = value
    return issued, errors


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
        if result["reused_from"] != job["reuse_job_id"]:
            raise ValueError("Reuse identity changed")
        target = job["target"]
        if report["scheduled_days"] != 90:
            raise ValueError("Wrong comparison replay schedule")
        scale = inputs.entities[(*inputs.namespace, target)]["scale"]["energy_scale"]
        if not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
            raise ValueError("Invalid target scale")
        scored_job = {**job, "report_levels": report.get("candidate_levels")}
        issued, errors = _scores(run_path, scored_job, scale)
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
                sum(errors[origin] for origin in evaluated) / len(evaluated)
                if len(evaluated) >= minimum
                else None
            )
            if (
                report["objective_coverage_pass"] != (metric is not None)
                or (report["mae_kwh"] is None) != (metric is None)
                or (
                    metric is not None
                    and not math.isclose(report["mae_kwh"], metric, rel_tol=1e-12, abs_tol=1e-12)
                )
            ):
                raise ValueError("Continuous objective MAE differs from events")
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
    for target, rows in by_target.items():
        origin_sets = [origins for _, origins, _ in rows]
        if any(origins != origin_sets[0] for origins in origin_sets[1:]):
            raise ValueError(f"Non-common scored origins for target {target}")
        minimum = protocol["minimum_scored_days"]["evaluation"][target]
        if len(origin_sets[0]) < minimum:
            target_means[target] = {method: None for method in METHODS}
            continue
        target_means[target] = {}
        for method in METHODS:
            cells = [
                sum(errors[origin] for origin in origins) / len(origins)
                for job, origins, errors in rows
                if job["method"] == method
            ]
            if len(cells) != len(SEEDS):
                raise ValueError("Missing paired seed")
            target_means[target][method] = sum(cells) / len(cells)
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
        "aggregate_mae_kwh": aggregate,
        "coverage": details,
    }
