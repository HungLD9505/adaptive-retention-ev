"""Development-only evaluation of the proposed seasonal-naive baseline."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from math import isfinite
from pathlib import Path

import torch

from ev_inputs.hourly_reader import sha256_file
from ev_inputs.loader import iter_forecasts
from ev_inputs.windows import ready_labels
from experiments.hung_sprint2.cli import _load_run
from experiments.hung_sprint2.evaluation import (
    Coverage,
    ForecastMetrics,
    aggregate_errors,
    complete_day_error_totals,
    coverage_from_replay,
)
from experiments.hung_sprint2.replay_inputs import (
    ReplaySummary,
    _label_record,
    _target_rows,
)
from experiments.hung_sprint2.seasonal_naive import forecast_previous_day


@dataclass(frozen=True)
class IssuedSeasonalForecast:
    origin: str
    scaled_kwh: tuple[float, ...]
    fallback_hours: int


@dataclass(frozen=True)
class SeasonalNaiveEvaluation:
    coverage: Coverage
    metrics: ForecastMetrics | None
    issued_fallback_hours: int
    scored_fallback_hours: int
    scored_origins: tuple[str, ...]
    issued_forecasts: tuple[IssuedSeasonalForecast, ...]


def evaluate_development(
    input_run: Path,
    *,
    manifest_sha256: str,
    entity_id: str,
    max_origins: int | None = None,
) -> SeasonalNaiveEvaluation:
    """Score accepted Development origins at the runner's same replay cutoff.

    Predictions are constructed before their matching label record is parsed.
    The labels are used only for scoring after the last replay event's cutoff;
    they never alter this stateless predictor.
    """
    input_run = Path(input_run).resolve()
    manifest = _load_run(input_run, manifest_sha256)
    identity = [manifest["config"]["dataset_id"], manifest["config"]["city_id"], entity_id]
    entities = list(_target_rows(input_run / "entities.jsonl", identity))
    if len(entities) != 1:
        raise ValueError("Development target identity is not unique")
    schedule = list(_target_rows(input_run / "schedule.jsonl", identity))
    if not schedule:
        raise ValueError("Target has no requested origins")
    if max_origins is not None and (
        isinstance(max_origins, bool) or max_origins <= 0 or max_origins > len(schedule)
    ):
        raise ValueError("Origin limit must fit the requested schedule")
    if any(row.get("input_run_id") != manifest["run_id"] for row in schedule):
        raise ValueError("Schedule input-run identity mismatch")
    origins = [datetime.fromisoformat(row["origin"]) for row in schedule]
    if any(
        later - earlier != timedelta(days=1)
        for earlier, later in zip(origins, origins[1:], strict=False)
    ):
        raise ValueError("Target schedule is not consecutive daily origins")
    limit = len(schedule) if max_origins is None else max_origins
    all_statuses = [row["status"] for row in schedule]
    if any(
        status not in {"created", "skipped_all_missing_history", "skipped_undefined_scale"}
        for status in all_statuses
    ):
        raise ValueError("Unknown schedule status")
    statuses = all_statuses[:limit]
    if "skipped_undefined_scale" in all_statuses:
        if (
            all_statuses.count("skipped_undefined_scale") != len(schedule)
            or entities[0].get("initialization") != "blocked_undefined_scale"
        ):
            raise ValueError("Mixed undefined-scale schedule")
        if any(_target_rows(input_run / "labels.jsonl", identity)) or any(
            row
            for row in iter_forecasts(input_run, expected_manifest_sha256=manifest_sha256)
            if row["role"] == "development" and row["identity"] == identity
        ):
            raise ValueError("Undefined-scale target has unexpected records")
        summary = ReplaySummary(limit, 0, 0, limit, 0, 0)
        return SeasonalNaiveEvaluation(coverage_from_replay(summary), None, 0, 0, (), ())
    if entities[0].get("initialization") not in {
        "target_initial_adaptation",
        "source_checkpoint_only",
    }:
        raise ValueError("Unsupported target initialization")
    scale = entities[0].get("scale", {})
    energy_scale = scale.get("energy_scale")
    if (
        not isinstance(energy_scale, (int, float))
        or not isfinite(energy_scale)
        or energy_scale <= 0
    ):
        raise ValueError("Target energy scale must be finite and positive")
    forecasts = (
        row
        for row in iter_forecasts(input_run, expected_manifest_sha256=manifest_sha256)
        if row["role"] == "development" and row["identity"] == identity
    )
    labels = _target_rows(input_run / "labels.jsonl", identity)
    pending = []
    issued_forecasts = []
    issued_fallback_hours = 0
    for scheduled in schedule[:limit]:
        origin = scheduled["origin"]
        prediction = None
        if scheduled["status"] == "created":
            row = next(forecasts, None)
            if row is None or (
                row["origin"] != origin
                or row["input_run_id"] != manifest["run_id"]
                or row["scale_id"] != scale.get("fit_sha256")
                or row["energy_scale"] != energy_scale
            ):
                raise ValueError("Forecast identity/origin/scale mismatch")
            prediction = forecast_previous_day(torch.tensor(row["x_hist"], dtype=torch.float32))
            issued_fallback_hours += prediction.fallback_hours
            issued_forecasts.append(
                IssuedSeasonalForecast(
                    origin,
                    tuple(float(value) for value in prediction.scaled_kwh),
                    prediction.fallback_hours,
                )
            )
        label_row = next(labels, None)
        if label_row is None:
            raise ValueError("Scheduled origin has no label record")
        record = _label_record(label_row, identity, origin)
        if prediction is not None and record.clock_mode != row["clock_mode"]:
            raise ValueError("Forecast/label clock profile mismatch")
        if prediction is not None:
            pending.append((origin, prediction, record))
    if limit == len(schedule) and (
        next(forecasts, None) is not None or next(labels, None) is not None
    ):
        raise ValueError("Forecast/label artifacts have unmatched target records")
    cutoff = origins[-1] + timedelta(days=1) if limit == len(schedule) else origins[limit - 1]
    errors = []
    scored_origins = []
    scored_fallback_hours = 0
    for origin, prediction, record in pending:
        values = ready_labels(record, as_of=cutoff)
        if values is None:
            continue
        errors.append(
            complete_day_error_totals(
                prediction.scaled_kwh,
                torch.tensor(values, dtype=torch.float32) / energy_scale,
                torch.ones(24, dtype=torch.bool),
                energy_scale=energy_scale,
            )
        )
        scored_origins.append(origin)
        scored_fallback_hours += prediction.fallback_hours
    created = statuses.count("created")
    summary = ReplaySummary(
        limit,
        created,
        statuses.count("skipped_all_missing_history"),
        0,
        len(errors),
        created - len(errors),
    )
    return SeasonalNaiveEvaluation(
        coverage_from_replay(summary),
        aggregate_errors(errors) if errors else None,
        issued_fallback_hours,
        scored_fallback_hours,
        tuple(scored_origins),
        tuple(issued_forecasts),
    )


def main() -> None:
    """Write a create-only Development diagnostic with its issued forecasts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-run", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--max-origins", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    result = evaluate_development(
        args.input_run,
        manifest_sha256=args.manifest_sha256,
        entity_id=args.entity_id,
        max_origins=args.max_origins,
    )
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    forecasts_path = output / "issued_forecasts.jsonl"
    with forecasts_path.open("x", encoding="utf-8") as stream:
        for issued in result.issued_forecasts:
            stream.write(json.dumps(asdict(issued), allow_nan=False) + "\n")
    root = Path(__file__).resolve().parents[2]
    sources = (
        root / "experiments/hung_sprint2/seasonal_naive.py",
        root / "experiments/hung_sprint2/seasonal_naive_replay.py",
        root / "experiments/hung_sprint2/evaluation.py",
        root / "experiments/hung_sprint2/replay_inputs.py",
    )
    manifest = {
        "status": "completed",
        "scope": "proposed_seasonal_naive_development_diagnostic; not accepted #22 baseline",
        "method": "previous_day_24h_last_observed_fallback",
        "input_run": str(args.input_run.resolve()),
        "input_manifest_sha256": args.manifest_sha256,
        "entity_id": args.entity_id,
        "max_origins": args.max_origins,
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "executed_sources": {
            path.relative_to(root).as_posix(): sha256_file(path) for path in sources
        },
        "duration_seconds": time.perf_counter() - started,
        "coverage": asdict(result.coverage),
        "metrics_kwh": asdict(result.metrics) if result.metrics is not None else None,
        "issued_fallback_hours": result.issued_fallback_hours,
        "scored_fallback_hours": result.scored_fallback_hours,
        "scored_origins": result.scored_origins,
        "issued_forecasts_sha256": sha256_file(forecasts_path),
    }
    with (output / "run_manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "completed", "output": str(output), "scope": manifest["scope"]}))


if __name__ == "__main__":
    main()
