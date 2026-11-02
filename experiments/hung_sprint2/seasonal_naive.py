"""Proposed 24-hour seasonal-naive forecast from predictor-visible history only.

The fallback rule needs Development review before it is an accepted #22 baseline.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor


@dataclass(frozen=True)
class SeasonalNaiveForecast:
    scaled_kwh: Tensor
    fallback_hours: int


def forecast_previous_day(history: Tensor) -> SeasonalNaiveForecast:
    """Repeat each hour from the prior day, using its last observed load if masked.

    All 24 history hours precede the forecast origin. A missing energy value is
    never treated as an observed zero. An all-missing history is a scheduled
    skip and therefore cannot produce a baseline forecast.
    """
    if history.shape != (24, 7) or not history.is_floating_point():
        raise ValueError("Historical input must have floating shape [24,7]")
    if not bool(torch.isfinite(history).all()):
        raise ValueError("Historical input must be finite")
    mask = history[:, 6]
    if not bool(torch.all((mask == 0) | (mask == 1))):
        raise ValueError("Historical availability mask must be binary")
    available = mask == 1
    if not bool(available.any()):
        raise ValueError("All-missing history requires a scheduled skip")
    if bool(torch.any(history[available, 0] < 0)):
        raise ValueError("Observed scaled energy must be nonnegative")
    prediction = history[:, 0].clone()
    fallback = history[available, 0][-1]
    prediction[~available] = fallback
    return SeasonalNaiveForecast(prediction, int((~available).sum().item()))
