"""Single-hour feature encoding against a pinned proposal, without reading data."""

from __future__ import annotations

import math
import struct
from datetime import datetime
from numbers import Real
from typing import Literal

SCHEMA_ID = "ev-input-v1"
CONTRACT_COMMIT = "c406ae07606ca48859cf93f8b24dfffab79c7803"
CONTRACT_SHA256 = "b10178d106713670e7ba7f884dd640559ce1788b3c792447843300457df63adf"
CONTRACT_URL = (
    "https://github.com/HungLD9505/adaptive-retention-ev/blob/"
    f"{CONTRACT_COMMIT}/docs/data/INPUT_CONTRACT.md"
)
CALENDAR_FEATURE_NAMES = ("hour_sin", "hour_cos", "weekday_sin", "weekday_cos", "is_weekend")
HISTORICAL_FEATURE_NAMES = ("energy_scaled", *CALENDAR_FEATURE_NAMES, "energy_present_mask")

ClockMode = Literal["offset-aware-local", "publisher-local-naive"]
CalendarFeatures = tuple[float, float, float, float, float]
HistoricalFeatures = tuple[float, float, float, float, float, float, float]


def _float32(value: float) -> float:
    """Return a Python float holding an IEEE-754 float32 value; never clip overflow."""
    try:
        return struct.unpack("!f", struct.pack("!f", value))[0]
    except OverflowError as error:
        raise ValueError("Feature value is outside finite float32 range") from error


def _finite_number(value: Real, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number, not a boolean or text")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} must be finite") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _validate_clock(timestamp: datetime, clock_mode: ClockMode) -> None:
    if not isinstance(timestamp, datetime):
        raise TypeError("timestamp must be a datetime already parsed under its producer profile")
    if clock_mode == "offset-aware-local":
        if timestamp.utcoffset() is None:
            raise ValueError("offset-aware-local requires an offset-bearing timestamp")
    elif clock_mode == "publisher-local-naive":
        if timestamp.tzinfo is not None:
            raise ValueError("publisher-local-naive requires an offset-free timestamp")
    else:
        raise ValueError(f"Unknown clock mode: {clock_mode!r}")
    if timestamp.minute or timestamp.second or timestamp.microsecond:
        raise ValueError("timestamp must label a whole local hour; no rounding is performed")


def calendar_features(timestamp: datetime, *, clock_mode: ClockMode) -> CalendarFeatures:
    """Encode five local calendar fields; do not infer timezone, arrival time or DST.

    Clock mode checks the timestamp representation only. A future loader must validate
    the actual producer zone/profile. No UTC conversion or temporal window is created.
    """
    _validate_clock(timestamp, clock_mode)
    hour_angle = math.tau * timestamp.hour / 24
    weekday_angle = math.tau * timestamp.weekday() / 7
    return (
        _float32(math.sin(hour_angle)),
        _float32(math.cos(hour_angle)),
        _float32(math.sin(weekday_angle)),
        _float32(math.cos(weekday_angle)),
        float(timestamp.weekday() >= 5),
    )


def historical_features(
    timestamp: datetime,
    *,
    energy_kwh: Real | None,
    file_valid: bool,
    energy_available: bool,
    energy_scale: Real,
    clock_mode: ClockMode,
) -> HistoricalFeatures:
    """Encode one seven-column historical row, preserving real zero versus missing.

    The caller supplies availability and a positive, previously identified scale.
    This function fits no scaler and cannot establish either upstream causality or
    availability. A masked/unavailable value is ignored. If both flags are true,
    missing/invalid energy is an input inconsistency and fails rather than being repaired.
    """
    calendar = calendar_features(timestamp, clock_mode=clock_mode)
    if not isinstance(file_valid, bool) or not isinstance(energy_available, bool):
        raise TypeError("file_valid and energy_available must be booleans")
    scale = _finite_number(energy_scale, "energy_scale")
    if scale <= 0:
        raise ValueError("energy_scale must be positive; no fallback is inferred")
    if not file_valid or not energy_available:
        return (0.0, *calendar, 0.0)
    if energy_kwh is None:
        raise ValueError("Energy marked valid and available cannot be missing")
    energy = _finite_number(energy_kwh, "energy_kwh")
    if energy < 0:
        raise ValueError("Energy marked valid and available cannot be negative")
    scaled = energy / scale
    if not math.isfinite(scaled):
        raise ValueError("Scaled energy must be finite")
    return (_float32(scaled), *calendar, 1.0)
