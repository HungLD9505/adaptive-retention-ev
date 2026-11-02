"""Development-only mean-error selectors over the existing three-candidate replay."""

from __future__ import annotations

import math
from typing import Literal, Sequence

from experiments.hung_sprint2.controller import ControllerConfig, DailyScore, Decision

SelectionRule = Literal[
    "confidence",
    "online_best_lambda",
    "without_confidence",
    "fixed_retention",
    "full_finetuning",
    "source_error",
    "uncertainty",
    "drift",
]


def decide_fixed_block(
    config: ControllerConfig,
    *,
    current_level: float,
    days: Sequence[DailyScore],
    rule: Literal["fixed_retention", "full_finetuning"],
) -> Decision:
    """Keep a declared level without consulting scores for policy selection."""
    if rule not in {"fixed_retention", "full_finetuning"}:
        raise ValueError("Unsupported fixed selection rule")
    if current_level not in config.levels or current_level != config.initial_level:
        raise ValueError("Fixed policy must retain its configured initial level")
    if (rule == "full_finetuning") != (current_level == 0.0):
        raise ValueError("Full fine-tuning requires zero; fixed retention requires positive lambda")
    if len(days) > config.block_days or len({day.day_id for day in days}) != len(days):
        raise ValueError("Invalid fixed-policy day schedule")
    valid = sum(day.normalized_mae is not None for day in days)
    return Decision(
        current_level,
        current_level,
        valid,
        len(days) - valid,
        (None, None, None),
        0.0,
        "fixed_policy",
        selection_statistic="fixed_level",
        observed_mean_improvement=None,
    )


def decide_mean_block(
    config: ControllerConfig,
    *,
    current_level: float,
    days: Sequence[DailyScore],
    rule: Literal["online_best_lambda", "without_confidence"],
) -> Decision:
    """Select a *future* block using paired, already arrived daily MAEs only.

    Online Best chooses the lowest observed mean MAE. Without Confidence uses
    active-minus-challenger mean improvement and the same strict delta gate as
    the confidence controller. Both preserve Bmin and all three update budgets.
    """
    if rule not in {"online_best_lambda", "without_confidence"}:
        raise ValueError("Unsupported mean selection rule")
    if current_level not in config.levels or len(days) > config.block_days:
        raise ValueError("Invalid active level or block length")
    if len({day.day_id for day in days}) != len(days):
        raise ValueError("Duplicate day identities")
    valid = [day for day in days if day.normalized_mae is not None]
    skipped = len(days) - len(valid)
    empty = (None, None, None)
    if len(valid) < config.min_complete_days:
        return Decision(
            current_level,
            current_level,
            len(valid),
            skipped,
            empty,
            0.0,
            "insufficient_days",
            selection_statistic="observed_mean_improvement",
            observed_mean_improvement=empty,
        )
    active_index = config.levels.index(current_level)
    means = tuple(
        math.fsum(day.normalized_mae[index] for day in valid) / len(valid) for index in range(3)
    )
    improvement = tuple(means[active_index] - value for value in means)
    margin = 0.0 if rule == "online_best_lambda" else config.delta
    qualifying = [
        index for index in range(3) if index != active_index and improvement[index] > margin
    ]
    selected = (
        max(
            qualifying,
            key=lambda index: (
                improvement[index],
                -abs(config.levels[index] - current_level),
                -index,
            ),
        )
        if qualifying
        else active_index
    )
    return Decision(
        current_level,
        config.levels[selected],
        len(valid),
        skipped,
        empty,
        0.0,
        "switch" if selected != active_index else "no_qualifying_challenger",
        selection_statistic="observed_mean_improvement",
        observed_mean_improvement=improvement,
    )
