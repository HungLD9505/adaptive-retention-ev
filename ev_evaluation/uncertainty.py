"""Exploratory paired station/calendar-block intervals, conditional on recorded seeds."""

import math
import random
from datetime import datetime, timedelta
from statistics import mean
from typing import Mapping


def quantile(values: list[float], probability: float) -> float:
    """Linear empirical quantile, fixed before inspecting comparator outcomes."""
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = int(index)
    return ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower]) * (
        index - lower
    )


def paired_station_time_interval(
    differences: Mapping[str, Mapping[int, Mapping[datetime, float]]],
    *,
    seeds: tuple[int, ...],
    start: datetime,
    days: int,
    segment_days: int,
    resamples: int,
    alpha: float,
    seed: int,
) -> dict:
    """Gap=method minus comparator; resample paired stations and calendar blocks.

    Use the same calendar indices across stations to retain common-date dependence.
    Missing scheduled dates stay missing, never compressed into adjacent observations.
    Average the fixed paired seeds within station/day; do not treat seeds as stations.
    No interval is returned when any bootstrap replicate has an undefined station mean.
    Small, nonrandom/colocated station cohorts limit the interval's interpretation.
    """
    if (
        not differences
        or len(set(seeds)) < 3
        or len(set(seeds)) != len(seeds)
        or any(type(v) is not int for v in (days, segment_days, resamples, seed))
        or not 1 <= segment_days <= days
        or resamples < 2
        or seed < 0
        or not math.isfinite(alpha)
        or not 0 < alpha < 1
        or any((start.hour, start.minute, start.second, start.microsecond))
    ):
        raise ValueError("Explicit nonempty paired cohort and valid bootstrap profile required")
    series = []
    for rows in differences.values():
        if set(rows) != set(seeds) or any(not rows[s] for s in seeds):
            raise ValueError("Every station needs all declared nonempty seed cells")
        origins = set(rows[seeds[0]])
        if any(set(rows[s]) != origins for s in seeds):
            raise ValueError("Seed cells must have identical scored origins")
        daily = {}
        for origin in origins:
            if origin.utcoffset() != start.utcoffset() or any(
                (origin.hour, origin.minute, origin.second, origin.microsecond)
            ):
                raise ValueError("One declared midnight clock required")
            delta = origin - start
            offset = delta.days
            if delta != timedelta(days=offset) or not 0 <= offset < days:
                raise ValueError("Scored origin outside scheduled calendar")
            values = [rows[s][origin] for s in seeds]
            if any(not math.isfinite(v) for v in values):
                raise ValueError("Finite paired errors required")
            daily[offset] = mean(values)
        series.append(daily)
    point = mean(mean(row.values()) for row in series)
    rng = random.Random(seed)
    replicates, undefined = [], 0
    for _ in range(resamples):
        selected = [rng.randrange(len(series)) for _ in series]
        indices = []
        while len(indices) < days:
            offset = rng.randrange(days)
            indices.extend((offset + j) % days for j in range(segment_days))
        indices = indices[:days]
        station_means = []
        for index in selected:
            values = [series[index][day] for day in indices if day in series[index]]
            if not values:
                break
            station_means.append(mean(values))
        if len(station_means) != len(selected):
            undefined += 1
        else:
            replicates.append(mean(station_means))
    return {
        "gap_kwh": point,
        "interval": None
        if undefined
        else [quantile(replicates, alpha / 2), quantile(replicates, 1 - alpha / 2)],
        "station_count": len(series),
        "seeds": list(seeds),
        "days": days,
        "segment_days": segment_days,
        "resamples": resamples,
        "alpha": alpha,
        "seed": seed,
        "undefined_replicates": undefined,
        "scope": "Exploratory selected-station/calendar bootstrap, conditional on fixed paired seeds",
        "limits": "Nonrandom small/possibly colocated cohort; circular seams/nonstationarity; no simultaneous-comparison correction or causal claim",
    }
