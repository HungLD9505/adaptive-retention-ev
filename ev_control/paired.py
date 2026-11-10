"""Pilot-only paired counterfactual acceptance for a retention coefficient."""

import math
import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class PairedRule:
    anchor: float
    eta: float
    max_abs_lambda_step: float
    anchor_trust_radius: float
    valid_complete_pairs: int
    max_wait_issued_days: int
    median_candidate_minus_incumbent_mae_kwh_below: float
    minimum_candidate_wins: int

    def __post_init__(self) -> None:
        floats = (
            self.anchor,
            self.eta,
            self.max_abs_lambda_step,
            self.anchor_trust_radius,
            self.median_candidate_minus_incumbent_mae_kwh_below,
        )
        if any(isinstance(value, bool) or not math.isfinite(value) for value in floats):
            raise ValueError("Finite numeric paired-controller settings required")
        if (
            self.anchor < 0
            or self.eta <= 0
            or self.max_abs_lambda_step <= 0
            or self.anchor_trust_radius <= 0
            or self.median_candidate_minus_incumbent_mae_kwh_below >= 0
        ):
            raise ValueError("Invalid paired-controller coefficient or threshold")
        integers = (
            self.valid_complete_pairs,
            self.max_wait_issued_days,
            self.minimum_candidate_wins,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) for value in integers):
            raise ValueError("Integer paired-controller counts required")
        if not (
            1 <= self.minimum_candidate_wins <= self.valid_complete_pairs
            <= self.max_wait_issued_days
        ):
            raise ValueError("Invalid paired-controller acceptance counts")


def propose(current: float, hypergradient: float, rule: PairedRule, upper_bound: float) -> dict:
    """Use A→V only to nominate a bounded alternative; it cannot authorize adoption."""
    if not all(math.isfinite(value) for value in (current, hypergradient, upper_bound)):
        raise ValueError("Nonfinite paired-controller proposal")
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


def accept(differences_kwh: list[float], rule: PairedRule) -> dict:
    """A negative difference means the candidate's forecast had lower MAE."""
    if len(differences_kwh) != rule.valid_complete_pairs or any(
        not math.isfinite(value) for value in differences_kwh
    ):
        raise ValueError("Exactly K finite paired complete-label outcomes required")
    median = statistics.median(differences_kwh)
    wins = sum(value < 0 for value in differences_kwh)
    selected = (
        median < rule.median_candidate_minus_incumbent_mae_kwh_below
        and wins >= rule.minimum_candidate_wins
    )
    return {
        "accepted": selected,
        "median_candidate_minus_incumbent_mae_kwh": median,
        "candidate_wins": wins,
        "paired_differences_kwh": differences_kwh.copy(),
    }
