"""Original-unit paired metrics with explicit station-first aggregation."""

import math
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Mapping, Sequence


@dataclass(frozen=True)
class DailyError:
    """Errors of one complete 24-hour forecast, already converted to kWh units."""

    origin: datetime
    mae: float
    mse: float

    def __post_init__(self) -> None:
        if not isinstance(self.origin, datetime):
            raise ValueError("Origin must be a datetime")
        if any(not math.isfinite(v) or v < 0 for v in (self.mae, self.mse)):
            raise ValueError("Errors must be finite and nonnegative")
        if self.mae**2 > self.mse + 1e-10 * max(1, self.mse):
            raise ValueError("MSE cannot be smaller than squared MAE")


def original_errors(
    origin: datetime, prediction_scaled: Sequence[float], labels_kwh: Sequence[float], scale: float
) -> DailyError:
    """Convert a stored normalized forecast, never fill or partially score labels."""
    if len(prediction_scaled) != 24 or len(labels_kwh) != 24:
        raise ValueError("Exactly 24 predictions and complete labels required")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("Scale must be finite and positive")
    if any(not math.isfinite(v) or v < 0 for v in (*prediction_scaled, *labels_kwh)):
        raise ValueError("Nonnegative finite forecasts and labels required")
    differences = [a * scale - b for a, b in zip(prediction_scaled, labels_kwh, strict=True)]
    return DailyError(origin, mean(abs(v) for v in differences), mean(v * v for v in differences))


def indexed(errors: Sequence[DailyError]) -> dict[datetime, DailyError]:
    result = {error.origin: error for error in errors}
    if len(result) != len(errors) or not errors:
        raise ValueError("Daily errors must be nonempty with unique origins")
    clocks = {v.utcoffset() for v in result}
    if len(clocks) != 1:
        raise ValueError("One declared clock profile required per evaluation unit")
    return result


def paired_metrics(method: Sequence[DailyError], target_only: Sequence[DailyError]) -> dict:
    """Require the identical predeclared valid-day set; no silent intersection."""
    left, right = indexed(method), indexed(target_only)
    if left.keys() != right.keys():
        raise ValueError("Paired methods must have identical scored origins")
    method_mae, target_mae = mean(v.mae for v in left.values()), mean(v.mae for v in right.values())
    return {
        "days": len(left),
        "origins": tuple(v.isoformat() for v in sorted(left)),
        "method_mae_kwh": method_mae,
        "target_only_mae_kwh": target_mae,
        "method_rmse_kwh": math.sqrt(mean(v.mse for v in left.values())),
        "target_only_rmse_kwh": math.sqrt(mean(v.mse for v in right.values())),
        "absolute_gap_kwh": method_mae - target_mae,
        "gain": (target_mae - method_mae) / target_mae if target_mae > 0 else None,
        "negative_transfer": method_mae > target_mae if target_mae > 0 else None,
        "zero_target_only_mae": target_mae == 0,
    }


def station_first(
    station_seed_metrics: Mapping[str, Mapping[int, dict]], *, seeds: tuple[int, ...]
) -> dict:
    """Average paired seeds within a station, then give each station equal weight.

    NTR unit is station, after averaging MAE across the declared paired seeds.
    Different namespaces, budgets, periods and initialization strata must be passed
    separately; callers retain those identities in their output manifest.
    """
    if len(set(seeds)) != len(seeds) or len(seeds) < 3 or not station_seed_metrics:
        raise ValueError("At least three unique declared seeds and one station required")
    stations = {}
    for identity, rows in station_seed_metrics.items():
        if set(rows) != set(seeds):
            raise ValueError("Missing/extra seed cells must be reported, not silently averaged")
        if len({r["origins"] for r in rows.values()}) != 1:
            raise ValueError("Seed replications must use identical scored origins")
        for row in rows.values():
            for metric in (
                "method_mae_kwh",
                "target_only_mae_kwh",
                "method_rmse_kwh",
                "target_only_rmse_kwh",
            ):
                if not math.isfinite(row[metric]) or row[metric] < 0:
                    raise ValueError("Aggregated errors must be finite and nonnegative")
        method = mean(r["method_mae_kwh"] for r in rows.values())
        target = mean(r["target_only_mae_kwh"] for r in rows.values())
        stations[identity] = {
            "method_mae_kwh": method,
            "target_only_mae_kwh": target,
            "method_rmse_kwh": mean(r["method_rmse_kwh"] for r in rows.values()),
            "target_only_rmse_kwh": mean(r["target_only_rmse_kwh"] for r in rows.values()),
            "gain": (target - method) / target if target > 0 else None,
            "absolute_gap_kwh": method - target,
            "negative_transfer": method > target if target > 0 else None,
        }
    gains = [v["gain"] for v in stations.values() if v["gain"] is not None]
    return {
        "stations": stations,
        "station_count": len(stations),
        "seeds": list(seeds),
        "macro_mae_kwh": mean(v["method_mae_kwh"] for v in stations.values()),
        "macro_rmse_kwh": mean(v["method_rmse_kwh"] for v in stations.values()),
        "gain_distribution": gains,
        "ntr": sum(v < 0 for v in gains) / len(gains) if gains else None,
        "ntr_denominator": len(gains),
        "zero_baseline_station_count": len(stations) - len(gains),
        "population_interval": None,
        "uncertainty_status": "Not estimated; paired station/time resampling still required",
    }
