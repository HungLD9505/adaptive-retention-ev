"""Original-unit metrics and explicit coverage for complete replay days."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import TYPE_CHECKING, Iterable

import torch
from torch import Tensor

if TYPE_CHECKING:
    from experiments.hung_sprint2.replay_inputs import ReplaySummary
    from experiments.hung_sprint2.runner import PrequentialRunner


@dataclass(frozen=True)
class ErrorTotals:
    """Additive errors in original kWh units for one complete horizon."""

    hours: int
    absolute_kwh: float
    squared_kwh2: float


@dataclass(frozen=True)
class ForecastMetrics:
    hours: int
    mae_kwh: float
    rmse_kwh: float


@dataclass(frozen=True)
class Coverage:
    requested: int
    created: int
    skipped_all_missing_history: int
    skipped_undefined_scale: int
    scored: int
    unscored_created: int
    issued_fraction: float
    scored_fraction: float


@dataclass(frozen=True)
class ReplayEvaluation:
    """Metrics for issued live forecasts, paired candidates and old-policy audit."""

    coverage: Coverage
    live: ForecastMetrics | None
    candidates: tuple[ForecastMetrics | None, ForecastMetrics | None, ForecastMetrics | None]
    audit: ForecastMetrics | None
    audit_scored_days: int


def complete_day_error_totals(
    forecast_scaled: Tensor,
    labels_scaled: Tensor,
    valid: Tensor,
    *,
    energy_scale: float,
) -> ErrorTotals:
    """Score an issued 24-hour forecast only after all labels are valid."""
    if (
        forecast_scaled.shape != (24,)
        or labels_scaled.shape != (24,)
        or valid.shape != (24,)
        or valid.dtype != torch.bool
    ):
        raise ValueError("Forecast, labels and validity must have 24 hourly values")
    if not bool(valid.all()):
        raise ValueError("Incomplete horizons cannot be scored")
    if not isfinite(energy_scale) or energy_scale <= 0:
        raise ValueError("Original-unit energy scale must be finite and positive")
    if (
        not forecast_scaled.is_floating_point()
        or not labels_scaled.is_floating_point()
        or not bool(torch.isfinite(forecast_scaled).all())
        or not bool(torch.isfinite(labels_scaled).all())
        or bool(torch.any(forecast_scaled < 0))
        or bool(torch.any(labels_scaled < 0))
    ):
        raise ValueError("Forecast and labels must be finite nonnegative floats")
    error = (forecast_scaled.to(torch.float64) - labels_scaled.to(torch.float64)) * energy_scale
    return ErrorTotals(24, float(error.abs().sum()), float(error.square().sum()))


def aggregate_errors(days: Iterable[ErrorTotals]) -> ForecastMetrics:
    """Micro-average every evaluated hour; do not average daily RMSEs."""
    total_hours = 0
    total_absolute = 0.0
    total_squared = 0.0
    for day in days:
        if (
            day.hours != 24
            or not isfinite(day.absolute_kwh)
            or not isfinite(day.squared_kwh2)
            or day.absolute_kwh < 0
            or day.squared_kwh2 < 0
        ):
            raise ValueError("Invalid complete-day error totals")
        total_hours += day.hours
        total_absolute += day.absolute_kwh
        total_squared += day.squared_kwh2
    if not total_hours:
        raise ValueError("At least one scored complete day is required")
    return ForecastMetrics(
        total_hours,
        total_absolute / total_hours,
        sqrt(total_squared / total_hours),
    )


def coverage_from_replay(summary: ReplaySummary) -> Coverage:
    """Keep issued and scored denominators tied to the requested schedule."""
    counts = (
        summary.requested,
        summary.created,
        summary.skipped_all_missing_history,
        summary.skipped_undefined_scale,
        summary.scored,
        summary.delayed_or_incomplete,
    )
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts):
        raise ValueError("Coverage counts must be nonnegative integers")
    if summary.requested == 0 or (
        summary.requested
        != summary.created + summary.skipped_all_missing_history + summary.skipped_undefined_scale
    ):
        raise ValueError("Requested schedule coverage does not balance")
    if summary.created != summary.scored + summary.delayed_or_incomplete:
        raise ValueError("Created forecast coverage does not balance")
    return Coverage(
        summary.requested,
        summary.created,
        summary.skipped_all_missing_history,
        summary.skipped_undefined_scale,
        summary.scored,
        summary.delayed_or_incomplete,
        summary.created / summary.requested,
        summary.scored / summary.requested,
    )


def evaluate_replay(runner: PrequentialRunner, summary: ReplaySummary) -> ReplayEvaluation:
    """Aggregate only stored forecasts with complete labels already scored by replay."""
    coverage = coverage_from_replay(summary)
    if len(runner.issued) != coverage.created:
        raise ValueError("Issued forecast count differs from replay coverage")
    candidate_days: list[list[ErrorTotals]] = [[], [], []]
    live_days: list[ErrorTotals] = []
    audit_days: list[ErrorTotals] = []
    scored = 0
    valid = torch.ones(24, dtype=torch.bool)
    for issued in runner.issued:
        labels = issued.get("y_scaled")
        if labels is None:
            if issued["normalized_mae"] is not None:
                raise ValueError("Scored forecast is missing its arrived labels")
            continue
        if issued["normalized_mae"] is None:
            raise ValueError("Arrived labels were not scored")
        if len(issued["forecasts"]) != 3:
            raise ValueError("A scored day must have three candidate forecasts")
        active = runner.controller.levels.index(issued["active_level"])
        for index, forecast in enumerate(issued["forecasts"]):
            candidate_days[index].append(
                complete_day_error_totals(
                    forecast.squeeze(0), labels, valid, energy_scale=runner.energy_scale
                )
            )
        live_days.append(candidate_days[active][-1])
        if issued["audit_forecast"] is not None:
            audit_days.append(
                complete_day_error_totals(
                    issued["audit_forecast"].squeeze(0),
                    labels,
                    valid,
                    energy_scale=runner.energy_scale,
                )
            )
        scored += 1
    if scored != coverage.scored:
        raise ValueError("Scored forecast count differs from replay coverage")
    return ReplayEvaluation(
        coverage,
        aggregate_errors(live_days) if live_days else None,
        tuple(aggregate_errors(days) if days else None for days in candidate_days),
        aggregate_errors(audit_days) if audit_days else None,
        len(audit_days),
    )
