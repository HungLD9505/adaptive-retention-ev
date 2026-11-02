"""Causal proxy selectors; thresholds and level mapping are Development choices."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence

from experiments.supporting_pipeline.controller import ControllerConfig, Decision

ProxyRule = Literal["source_error", "uncertainty", "drift"]


@dataclass(frozen=True)
class ProxyConfig:
    """A locked, explicit two-threshold mapping; no direction is implied."""

    low: float
    high: float
    levels_by_bin: tuple[float, float, float]
    drift_reference_mean: float | None = None
    drift_reference_scale: float | None = None

    def validate(self, controller: ControllerConfig, rule: ProxyRule) -> None:
        if (
            not all(math.isfinite(x) for x in (self.low, self.high))
            or not 0 <= self.low < self.high
        ):
            raise ValueError("Proxy thresholds must be finite, nonnegative, and ordered")
        if sorted(self.levels_by_bin) != sorted(controller.levels):
            raise ValueError("Proxy mapping must use each candidate level exactly once")
        reference = (self.drift_reference_mean, self.drift_reference_scale)
        if rule == "drift":
            if reference[0] is None or reference[1] is None:
                raise ValueError("Drift requires a fixed Development reference")
            if (
                not math.isfinite(reference[0])
                or not math.isfinite(reference[1])
                or reference[1] <= 0
            ):
                raise ValueError("Drift reference mean/scale must be finite with positive scale")
        elif any(value is not None for value in reference):
            raise ValueError("Only drift uses a descriptor reference")


def decide_proxy_block(
    controller: ControllerConfig,
    *,
    current_level: float,
    scheduled_days: int,
    values: Sequence[float],
    config: ProxyConfig,
    rule: ProxyRule,
) -> Decision:
    """Choose the next block from currently observable proxy values only."""
    config.validate(controller, rule)
    if current_level not in controller.levels or scheduled_days != controller.block_days:
        raise ValueError("Invalid active level or block schedule")
    if len(values) > scheduled_days or any(not math.isfinite(x) or x < 0 for x in values):
        raise ValueError("Proxy observations must be finite nonnegative values")
    valid = len(values)
    if valid < controller.min_complete_days:
        selected, reason, statistic = current_level, "insufficient_days", None
    else:
        statistic = math.fsum(values) / valid
        bin_index = 0 if statistic < config.low else 1 if statistic < config.high else 2
        selected = config.levels_by_bin[bin_index]
        reason = "switch" if selected != current_level else "no_qualifying_challenger"
    return Decision(
        current_level,
        selected,
        valid,
        scheduled_days - valid,
        (None, None, None),
        0.0,
        reason,
        selection_statistic="proxy_mean",
        proxy_value=statistic,
        proxy_samples=valid,
    )
