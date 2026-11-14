"""Two-expert forecast mixing with canonical Fixed-share loss updates."""

import math
from datetime import datetime, timedelta

import numpy as np


def update_stable_weight(
    weight: float, stable_loss: float, fast_loss: float, *, eta: float, share: float
) -> float:
    """Update only after both forecast losses arrive; share mass to the other expert."""
    if (
        not all(math.isfinite(x) for x in (weight, stable_loss, fast_loss, eta, share))
        or not 0 <= weight <= 1
        or min(stable_loss, fast_loss) < 0
        or eta <= 0
        or not 0 <= share <= 1
    ):
        raise ValueError("Invalid two-expert probability, loss or Fixed-share parameter")
    if weight in (0, 1):
        posterior = weight
    else:
        logit = math.log(weight) - math.log1p(-weight) - eta * (stable_loss - fast_loss)
        if logit >= 0:
            posterior = 1 / (1 + math.exp(-logit))
        else:
            value = math.exp(logit)
            posterior = value / (1 + value)
    return (1 - share) * posterior + share * (1 - posterior)


def fit_static_weight(cells: list[dict]) -> float:
    """Exact convex MAE minimizer; each station/seed cell receives equal weight."""
    if not cells:
        raise ValueError("Empty calibration cells")
    locations = []
    masses = []
    for cell in cells:
        stable, fast, labels = (
            np.asarray(cell[k], dtype=float) for k in ("stable", "fast", "labels")
        )
        if (
            stable.shape != fast.shape
            or stable.shape != labels.shape
            or stable.ndim != 2
            or stable.shape[1] != 24
            or len(stable) == 0
            or not all(np.isfinite(x).all() for x in (stable, fast, labels))
        ):
            raise ValueError("Calibration needs finite matched complete daily vectors")
        difference = stable - fast
        nonzero = difference != 0
        locations.extend(((labels - fast)[nonzero] / difference[nonzero]).tolist())
        masses.extend((np.abs(difference[nonzero]) / len(stable)).tolist())
    if not locations:
        return 1.0
    order = np.argsort(locations, kind="stable")
    ordered = np.asarray(locations)[order]
    cumulative = np.cumsum(np.asarray(masses)[order])
    median = ordered[np.searchsorted(cumulative, cumulative[-1] / 2)]
    return float(np.clip(median, 0, 1))


def forecast_mixture(
    cell: dict, initial_weight: float, *, eta: float | None = None, share: float = 0
) -> dict:
    """Predict before future labels enter weight updates; errors are scored afterward."""
    if not math.isfinite(initial_weight) or not 0 <= initial_weight <= 1:
        raise ValueError("Invalid initial mixing probability")
    if eta is not None:
        update_stable_weight(initial_weight, 0, 0, eta=eta, share=share)
    origins = cell["origins"]
    clocks = [datetime.fromisoformat(o) for o in origins]
    if not clocks or clocks != sorted(set(clocks)):
        raise ValueError("Forecast origins must be chronological and unique")
    available = cell["available_at"]
    if len(available) != len(origins):
        raise ValueError("Availability mask mismatch")
    arrival_clocks = [datetime.fromisoformat(a) for a in available]
    if any(a < o + timedelta(days=1) for o, a in zip(clocks, arrival_clocks, strict=True)):
        raise ValueError("Complete daily labels cannot arrive before the forecast day ends")
    if not math.isfinite(cell["scale"]) or cell["scale"] <= 0:
        raise ValueError("Positive fixed target scale required")
    weight = initial_weight
    consumed = set()
    weights = []
    predictions = []
    events = []
    stable, fast, labels = (np.asarray(cell[k], dtype=float) for k in ("stable", "fast", "labels"))
    if (
        stable.shape != fast.shape
        or stable.shape != labels.shape
        or stable.shape != (len(origins), 24)
    ):
        raise ValueError("Mixture requires matched full-day vectors")
    if not all(np.isfinite(x).all() and (x >= 0).all() for x in (stable, fast, labels)):
        raise ValueError("Finite nonnegative energy vectors required")
    for index, origin in enumerate(origins):
        # Complete scored origins are sufficient: unscored days cannot update weights.
        for earlier in sorted(range(index), key=lambda j: (arrival_clocks[j], clocks[j])):
            if earlier in consumed or arrival_clocks[earlier] > clocks[index]:
                continue
            if eta is not None:
                stable_loss = (
                    float(np.abs(stable[earlier] - labels[earlier]).mean()) / cell["scale"]
                )
                fast_loss = float(np.abs(fast[earlier] - labels[earlier]).mean()) / cell["scale"]
                before = weight
                weight = update_stable_weight(weight, stable_loss, fast_loss, eta=eta, share=share)
                events.append(
                    {
                        "at": origin,
                        "label_origin": origins[earlier],
                        "available_at": available[earlier],
                        "before": before,
                        "after": weight,
                    }
                )
            consumed.add(earlier)
        weights.append(weight)
        predictions.append(weight * stable[index] + (1 - weight) * fast[index])
    vectors = np.asarray(predictions)
    errors = np.abs(vectors - labels).mean(axis=1)
    return {
        "mae": float(errors.mean()),
        "daily_mae": errors.tolist(),
        "weights": weights,
        "predictions_kwh": vectors.tolist(),
        "events": events,
    }
