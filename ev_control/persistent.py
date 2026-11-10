"""Versioned paired-trajectory proposal and acceptance rules for issue #99."""

import math
import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class PersistentRule:
    anchor: float
    eta: float
    max_abs_lambda_step: float
    anchor_trust_radius: float
    valid_complete_pairs: int
    max_wait_issued_days: int
    mean_candidate_minus_incumbent_mae_kwh_below: float
    minimum_candidate_wins: int
    max_candidate_harm_kwh: float

    def __post_init__(self) -> None:
        floats = (
            self.anchor,
            self.eta,
            self.max_abs_lambda_step,
            self.anchor_trust_radius,
            self.mean_candidate_minus_incumbent_mae_kwh_below,
            self.max_candidate_harm_kwh,
        )
        if any(isinstance(value, bool) or not math.isfinite(value) for value in floats):
            raise ValueError("Finite numeric persistent-controller settings required")
        if (
            self.anchor < 0
            or self.eta <= 0
            or self.max_abs_lambda_step <= 0
            or self.anchor_trust_radius <= 0
            or self.mean_candidate_minus_incumbent_mae_kwh_below >= 0
            or self.max_candidate_harm_kwh < 0
        ):
            raise ValueError("Invalid persistent-controller coefficient or threshold")
        integers = (
            self.valid_complete_pairs,
            self.max_wait_issued_days,
            self.minimum_candidate_wins,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) for value in integers):
            raise ValueError("Integer persistent-controller counts required")
        if not (
            1 <= self.minimum_candidate_wins <= self.valid_complete_pairs
            <= self.max_wait_issued_days
        ):
            raise ValueError("Invalid persistent-controller acceptance counts")


def propose(current: float, hypergradient: float, rule: PersistentRule, upper_bound: float) -> dict:
    """A/V suggests only a candidate; future paired labels authorize adoption."""
    if not all(math.isfinite(value) for value in (current, hypergradient, upper_bound)):
        raise ValueError("Nonfinite persistent-controller proposal")
    lower = max(0.0, rule.anchor - rule.anchor_trust_radius)
    upper = min(upper_bound, rule.anchor + rule.anchor_trust_radius)
    if lower > upper or not lower <= current <= upper:
        raise ValueError("Invalid incumbent or empty trust interval")
    raw_step = max(
        -rule.max_abs_lambda_step,
        min(rule.max_abs_lambda_step, rule.eta * hypergradient),
    )
    raw = current - raw_step
    candidate = max(lower, min(upper, raw))
    return {
        "incumbent": current,
        "candidate": candidate,
        "hypergradient": hypergradient,
        "raw_step": raw_step,
        "candidate_unclipped": raw,
        "bound_hit": candidate != raw,
        "lower_bound": lower,
        "upper_bound": upper,
    }


def accept(differences_kwh: list[float], rule: PersistentRule) -> dict:
    """Require mean gain, wins, and a per-day harm ceiling on arrived labels."""
    if len(differences_kwh) != rule.valid_complete_pairs or any(
        not math.isfinite(value) for value in differences_kwh
    ):
        raise ValueError("Exactly K finite complete paired outcomes required")
    mean = statistics.mean(differences_kwh)
    wins = sum(value < 0 for value in differences_kwh)
    maximum = max(differences_kwh)
    chosen = (
        mean < rule.mean_candidate_minus_incumbent_mae_kwh_below
        and wins >= rule.minimum_candidate_wins
        and maximum <= rule.max_candidate_harm_kwh
    )
    return {
        "accepted": chosen,
        "mean_candidate_minus_incumbent_mae_kwh": mean,
        "candidate_wins": wins,
        "max_candidate_harm_kwh": maximum,
        "paired_differences_kwh": differences_kwh.copy(),
    }
