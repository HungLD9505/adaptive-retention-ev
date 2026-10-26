"""Development-configured confidence decisions over paired, complete forecast days.

The runner owns forecast storage and label-arrival checks. It may pass missing
days for accounting, but only days with all three paired MAEs and arrived,
complete labels enter the bootstrap. Decisions affect the following block.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Literal, Sequence


@dataclass(frozen=True)
class ControllerConfig:
    """Values must be chosen on Development and locked before Final replay."""

    levels: tuple[float, float, float]
    initial_level: float
    block_days: int
    min_complete_days: int
    delta: float
    alpha: float
    bootstrap_segment_days: int
    bootstrap_resamples: int
    seed: int
    challenger_rule: Literal["bonferroni_two"]

    def __post_init__(self) -> None:
        if len(self.levels) != 3 or self.levels[0] != 0:
            raise ValueError("Levels must contain zero and two positive values")
        if any(not math.isfinite(level) for level in self.levels):
            raise ValueError("Levels must be finite")
        if not 0 < self.levels[1] < self.levels[2]:
            raise ValueError("Positive retention levels must be ordered")
        if self.initial_level not in self.levels:
            raise ValueError("Initial level must be one of the candidate levels")
        if self.block_days <= 0 or self.min_complete_days <= 0:
            raise ValueError("Day counts must be positive")
        if self.min_complete_days > self.block_days:
            raise ValueError("Minimum complete days exceed block length")
        if not 1 <= self.bootstrap_segment_days <= self.min_complete_days:
            raise ValueError("Bootstrap segment length must fit minimum complete days")
        if self.bootstrap_resamples <= 0:
            raise ValueError("Bootstrap resamples must be positive")
        if not math.isfinite(self.delta) or self.delta < 0:
            raise ValueError("Delta must be finite and nonnegative")
        if not math.isfinite(self.alpha) or not 0 < self.alpha < 1:
            raise ValueError("Alpha must be between zero and one")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("Seed must be an integer")
        if self.challenger_rule != "bonferroni_two":
            raise ValueError("Unsupported two-challenger rule")


@dataclass(frozen=True)
class DailyScore:
    """One scheduled day; missing or unavailable labels have no paired MAEs."""

    day_id: str
    labels_arrived: bool
    labels_complete: bool
    normalized_mae: tuple[float, float, float] | None

    def __post_init__(self) -> None:
        if not self.day_id:
            raise ValueError("Day identity is required")
        if self.normalized_mae is None:
            return
        if not self.labels_arrived or not self.labels_complete:
            raise ValueError("MAEs require arrived, complete 24-hour labels")
        if len(self.normalized_mae) != 3 or any(
            not math.isfinite(error) or error < 0 for error in self.normalized_mae
        ):
            raise ValueError("All three paired normalized MAEs must be finite and nonnegative")


@dataclass(frozen=True)
class Decision:
    """A block-end choice and its diagnostics, in configured level order."""

    current_level: float
    selected_level: float
    valid_days: int
    skipped_days: int
    lower_bounds: tuple[float | None, float | None, float | None]
    alpha_per_challenger: float
    reason: Literal["insufficient_days", "no_qualifying_challenger", "switch"]
    selection_statistic: Literal["bootstrap_lcb", "observed_mean_improvement"] = "bootstrap_lcb"
    observed_mean_improvement: tuple[float | None, float | None, float | None] | None = None

    @property
    def switched(self) -> bool:
        return self.selected_level != self.current_level


def _bootstrap_lower_bounds(
    improvements: tuple[list[float], list[float]],
    *,
    alpha: float,
    segment_days: int,
    resamples: int,
    seed: int,
    block_id: int,
) -> tuple[float, float]:
    """Empirical one-sided percentile LCB from paired moving day blocks.

    Each resample draws contiguous segments with replacement and trims to B
    days. Both challengers use the same resampled day indices. The empirical
    quantile is order statistic ceil(alpha * R) - 1, with no interpolation.
    """

    days = len(improvements[0])
    digest = hashlib.sha256(f"{seed}:{block_id}".encode()).digest()
    rng = random.Random(int.from_bytes(digest, "big"))
    means: tuple[list[float], list[float]] = ([], [])
    for _ in range(resamples):
        indices: list[int] = []
        while len(indices) < days:
            start = rng.randrange(days - segment_days + 1)
            indices.extend(range(start, start + segment_days))
        indices = indices[:days]
        for values, samples in zip(improvements, means, strict=True):
            samples.append(sum(values[index] for index in indices) / days)
    position = max(0, math.ceil(alpha * resamples) - 1)
    return tuple(sorted(samples)[position] for samples in means)  # type: ignore[return-value]


def decide_block(
    config: ControllerConfig,
    *,
    current_level: float,
    block_id: int,
    days: Sequence[DailyScore],
) -> Decision:
    """Choose next block's trained candidate using only arrived complete days.

    The active candidate is fixed before this block. MAEs are aligned by day and
    configured level order. The caller must provide only forecasts stored before
    labels, and must not use this decision to revise past forecasts.
    """

    if current_level not in config.levels:
        raise ValueError("Current level is absent from candidate levels")
    if isinstance(block_id, bool) or not isinstance(block_id, int) or block_id < 0:
        raise ValueError("Block ID must be a nonnegative integer")
    if len(days) > config.block_days:
        raise ValueError("More scheduled days than the configured block length")
    if len({day.day_id for day in days}) != len(days):
        raise ValueError("Duplicate day identities")

    valid = [day for day in days if day.normalized_mae is not None]
    skipped = len(days) - len(valid)
    alpha_each = config.alpha / 2
    empty_bounds: tuple[None, None, None] = (None, None, None)
    if len(valid) < config.min_complete_days:
        return Decision(
            current_level,
            current_level,
            len(valid),
            skipped,
            empty_bounds,
            alpha_each,
            "insufficient_days",
        )

    active_index = config.levels.index(current_level)
    challengers = [index for index in range(3) if index != active_index]
    paired = tuple(
        [
            day.normalized_mae[active_index] - day.normalized_mae[index]
            for day in valid
            if day.normalized_mae is not None
        ]
        for index in challengers
    )
    challenger_bounds = _bootstrap_lower_bounds(
        paired,
        alpha=alpha_each,
        segment_days=config.bootstrap_segment_days,
        resamples=config.bootstrap_resamples,
        seed=config.seed,
        block_id=block_id,
    )
    bounds: list[float | None] = [None, None, None]
    for index, lower_bound in zip(challengers, challenger_bounds, strict=True):
        bounds[index] = lower_bound
    qualifying = [index for index in challengers if bounds[index] > config.delta]
    if not qualifying:
        return Decision(
            current_level,
            current_level,
            len(valid),
            skipped,
            tuple(bounds),
            alpha_each,
            "no_qualifying_challenger",
        )
    selected = max(
        qualifying,
        key=lambda index: (
            bounds[index],
            -abs(config.levels[index] - current_level),
            -index,
        ),
    )
    return Decision(
        current_level,
        config.levels[selected],
        len(valid),
        skipped,
        tuple(bounds),
        alpha_each,
        "switch",
    )
