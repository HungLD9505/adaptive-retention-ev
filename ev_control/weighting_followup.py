"""Bounded expert-weight diagnostics; explicit delayed-feedback arrival adapter."""

import math
from datetime import datetime, timedelta

import numpy as np

METHODS = ("no_share", "decreasing_share", "adahedge", "ftl")


def probabilities(total: np.ndarray, eta: float) -> np.ndarray:
    """Exponential cumulative weights, with exact uniform leader ties at infinity."""
    excess = total - total.min()
    if math.isinf(eta):
        result = (excess == 0).astype(float)
    else:
        result = np.exp(-eta * excess)
    return result / result.sum()


def adahedge_step(total: np.ndarray, gap: float, losses: np.ndarray) -> tuple[np.ndarray, float]:
    """Equations (8)--(9): eta=ln(K)/Delta, gap=Hedge loss minus mix loss.

    This operation processes one arrived feedback event. Recomputing its virtual
    Hedge loss in arrival order is an adapter, not a delay-free regret claim.
    Center both cumulative and current losses for numerical translation stability.
    """
    eta = math.log(len(total)) / gap if gap > 0 else math.inf
    before = total - total.min()
    current = losses - losses.min()
    after = before + current
    weights = probabilities(before, eta)
    if math.isinf(eta):
        mix_loss = after.min()
    else:
        old_partition = float(np.logaddexp.reduce(-eta * before))
        next_partition = float(np.logaddexp.reduce(-eta * (after - after.min())))
        mix_loss = float(after.min() - (next_partition - old_partition) / eta)
    increment = float(weights @ current - mix_loss)
    if increment < -1e-9:
        raise ValueError("Negative mixability gap beyond numerical tolerance")
    return after - after.min(), gap + max(0.0, increment)


def replay_weighting(cell: dict, method: str, initial_weight: float) -> dict:
    """Issue before consuming current/future labels; experts themselves stay fixed."""
    if method not in METHODS or not 0 < initial_weight < 1:
        raise ValueError("Declared method and interior initial probability required")
    stable, fast, labels = (np.asarray(cell[k], dtype=float) for k in ("stable", "fast", "labels"))
    origins = [datetime.fromisoformat(o) for o in cell["origins"]]
    arrivals = [datetime.fromisoformat(o) for o in cell["available_at"]]
    if (
        stable.shape != fast.shape
        or stable.shape != labels.shape
        or stable.shape != (len(origins), 24)
    ):
        raise ValueError("Matched complete daily vectors required")
    if origins != sorted(set(origins)) or len(arrivals) != len(origins) or cell["scale"] <= 0:
        raise ValueError("Invalid origins/scale")
    if any(a < o + timedelta(days=1) for o, a in zip(origins, arrivals, strict=True)):
        raise ValueError("Labels cannot arrive before the forecast day ends")
    if not all(np.isfinite(v).all() and (v >= 0).all() for v in (stable, fast, labels)):
        raise ValueError("Finite nonnegative energy required")
    losses = np.stack([abs(stable - labels).mean(1), abs(fast - labels).mean(1)], axis=1)
    losses /= cell["scale"]
    total, gap, weight, count = np.zeros(2), 0.0, initial_weight, 0
    consumed, weights, predictions, events = set(), [], [], []
    if method in ("adahedge", "ftl"):
        weight = 0.5
    for index, origin in enumerate(origins):
        for earlier in sorted(range(index), key=lambda j: (arrivals[j], origins[j])):
            if earlier in consumed or arrivals[earlier] > origin:
                continue
            before = weight
            if method == "adahedge":
                total, gap = adahedge_step(total, gap, losses[earlier])
                eta = math.log(2) / gap if gap > 0 else math.inf
                weight = float(probabilities(total, eta)[0])
            elif method == "ftl":
                total += losses[earlier] - losses[earlier].min()
                total -= total.min()
                weight = float(probabilities(total, math.inf)[0])
            else:
                # No clipping beyond stable logistic arithmetic; fixed eta is an ablation.
                odds = (
                    math.log(weight)
                    - math.log1p(-weight)
                    - 0.1 * (losses[earlier, 0] - losses[earlier, 1])
                    if 0 < weight < 1
                    else (math.inf if weight == 1 else -math.inf)
                )
                posterior = (
                    1 / (1 + math.exp(-odds))
                    if odds >= 0
                    else math.exp(odds) / (1 + math.exp(odds))
                )
                share = 1 / (count + 2) if method == "decreasing_share" else 0.0
                weight = share + (1 - 2 * share) * posterior
            count += 1
            events.append(
                {
                    "at": origin.isoformat(),
                    "label_origin": origins[earlier].isoformat(),
                    "available_at": arrivals[earlier].isoformat(),
                    "before": before,
                    "after": weight,
                    "arrivals_consumed": count,
                }
            )
            consumed.add(earlier)
        weights.append(weight)
        predictions.append(weight * stable[index] + (1 - weight) * fast[index])
    vectors = np.asarray(predictions)
    daily = abs(vectors - labels).mean(1)
    return {
        "mae": float(daily.mean()),
        "daily_mae": daily.tolist(),
        "weights": weights,
        "predictions_kwh": vectors.tolist(),
        "events": events,
    }
