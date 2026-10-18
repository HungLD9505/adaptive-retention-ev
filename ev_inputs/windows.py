"""Fixture-stage 24-to-24 windows with separate prediction and delayed-label paths."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from numbers import Real
from typing import Sequence

from ev_inputs.features import (
    SCHEMA_ID,
    CalendarFeatures,
    ClockMode,
    HistoricalFeatures,
    _finite_number,
    _float32,
    _validate_clock,
    calendar_features,
    historical_features,
)

HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
Identity = tuple[str, str, str]


@dataclass(frozen=True)
class HourlyValue:
    """One explicit bin from ONE identified producer; unknown availability is None."""

    identity: Identity
    timestamp: datetime
    energy_kwh: Real | None
    file_valid: bool
    available_at: datetime | None


@dataclass(frozen=True)
class ForecastInput:
    """Predictor-visible values only; no future energy, validity or availability."""

    identity: Identity
    origin: datetime
    clock_mode: ClockMode
    schema_id: str
    input_run_id: str
    scale_id: str
    energy_scale: float
    history_labels: tuple[datetime, ...]
    future_labels: tuple[datetime, ...]
    x_hist: tuple[HistoricalFeatures, ...]
    c_future: tuple[CalendarFeatures, ...]


@dataclass(frozen=True)
class LabelRecord:
    """Evaluation/update-only future values, separate from ForecastInput."""

    identity: Identity
    origin: datetime
    clock_mode: ClockMode
    timestamps: tuple[datetime, ...]
    energy_kwh: tuple[float | None, ...]
    file_valid: tuple[bool, ...]
    available_at: tuple[datetime | None, ...]


@dataclass(frozen=True)
class TrainingExample:
    forecast: ForecastInput
    y_kwh: tuple[float, ...]
    y_scaled: tuple[float, ...]


def _identity(identity: Identity) -> None:
    if (
        not isinstance(identity, tuple)
        or len(identity) != 3
        or any(not isinstance(value, str) or not value.strip() for value in identity)
    ):
        raise ValueError("Identity must contain three nonempty strings")


def _origin(origin: datetime, clock_mode: ClockMode) -> None:
    _validate_clock(origin, clock_mode)
    if origin.hour != 0:
        raise ValueError("Proposed daily origin must be local midnight")


def _same_clock(value: datetime, origin: datetime, clock_mode: ClockMode) -> None:
    _validate_clock(value, clock_mode)
    if value.utcoffset() != origin.utcoffset():
        raise ValueError("Offset changes are unsupported; do not infer DST bins")


def _availability(row: HourlyValue, origin: datetime) -> None:
    available = row.available_at
    if available is None:
        return
    if not isinstance(available, datetime) or available.utcoffset() != origin.utcoffset():
        raise ValueError("Availability must use the same naive/fixed-offset clock")
    if available < row.timestamp + HOUR:
        raise ValueError("Complete-bin availability cannot precede bin end")


def _rows(
    rows: Sequence[HourlyValue],
    labels: tuple[datetime, ...],
    identity: Identity,
    origin: datetime,
    clock_mode: ClockMode,
) -> None:
    _identity(identity)
    if len(rows) != 24:
        raise ValueError("Exactly 24 explicit bins are required; no sorting or filling")
    for row, expected in zip(rows, labels, strict=True):
        _same_clock(row.timestamp, origin, clock_mode)
        if row.identity != identity or row.timestamp != expected:
            raise ValueError("Wrong entity or nonconsecutive/out-of-order bin")
        if not isinstance(row.file_valid, bool):
            raise TypeError("file_valid must be boolean")
        _availability(row, origin)


def scheduled_origins(
    start: datetime,
    stop: datetime,
    *,
    clock_mode: ClockMode,
) -> tuple[datetime, ...]:
    """Daily [start, stop) origins derived ONLY from configured bounds, never Y."""
    _origin(start, clock_mode)
    _origin(stop, clock_mode)
    _same_clock(stop, start, clock_mode)
    if stop < start:
        raise ValueError("Schedule stop precedes start")
    origins = tuple(start + index * DAY for index in range((stop - start).days))
    for origin in origins:
        _same_clock(origin, start, clock_mode)
    return origins


def initial_training_origins(
    prefix_start: datetime,
    cutoff: datetime,
    *,
    clock_mode: ClockMode,
) -> tuple[datetime, ...]:
    """Contained daily 24+24 candidates; later label gates decide trainability."""
    _origin(prefix_start, clock_mode)
    _origin(cutoff, clock_mode)
    _same_clock(cutoff, prefix_start, clock_mode)
    if cutoff < prefix_start:
        raise ValueError("Prefix cutoff precedes start")
    if cutoff - prefix_start < 2 * DAY:
        return ()
    return scheduled_origins(prefix_start + DAY, cutoff, clock_mode=clock_mode)


def build_forecast_input(
    history: Sequence[HourlyValue],
    *,
    identity: Identity,
    origin: datetime,
    clock_mode: ClockMode,
    energy_scale: Real,
    scale_id: str,
    input_run_id: str,
) -> ForecastInput:
    """Build [24,7] and [24,5] tuples without accepting a future-data argument.

    Supply 24 producer bins, including explicit invalid bins where energy is missing.
    Unknown or delayed historical availability produces mask 0, never a fabricated zero.
    Producer-profile validation and fitted-scale provenance remain loader duties.
    """
    _origin(origin, clock_mode)
    scale = _finite_number(energy_scale, "energy_scale")
    if scale <= 0:
        raise ValueError("energy_scale must be positive")
    for name, value in (("scale_id", scale_id), ("input_run_id", input_run_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be identified")
    history_labels = tuple(origin - (24 - index) * HOUR for index in range(24))
    future_labels = tuple(origin + index * HOUR for index in range(24))
    _rows(history, history_labels, identity, origin, clock_mode)
    for timestamp in future_labels:
        _same_clock(timestamp, origin, clock_mode)
    x_hist = tuple(
        historical_features(
            row.timestamp,
            energy_kwh=row.energy_kwh,
            file_valid=row.file_valid,
            energy_available=row.available_at is not None and row.available_at <= origin,
            energy_scale=scale,
            clock_mode=clock_mode,
        )
        for row in history
    )
    return ForecastInput(
        identity,
        origin,
        clock_mode,
        SCHEMA_ID,
        input_run_id,
        scale_id,
        scale,
        history_labels,
        future_labels,
        x_hist,
        tuple(calendar_features(time, clock_mode=clock_mode) for time in future_labels),
    )


def build_label_record(
    future: Sequence[HourlyValue],
    *,
    identity: Identity,
    origin: datetime,
    clock_mode: ClockMode,
) -> LabelRecord:
    """Read future data ONLY in the separate label path; invalid Y remains None."""
    _origin(origin, clock_mode)
    timestamps = tuple(origin + index * HOUR for index in range(24))
    _rows(future, timestamps, identity, origin, clock_mode)
    energies: list[float | None] = []
    for row in future:
        if not row.file_valid:
            energies.append(None)
            continue
        value = _finite_number(row.energy_kwh, "valid label energy")
        if value < 0:
            raise ValueError("Valid label energy cannot be negative")
        energies.append(value)
    return LabelRecord(
        identity,
        origin,
        clock_mode,
        timestamps,
        tuple(energies),
        tuple(row.file_valid for row in future),
        tuple(row.available_at for row in future),
    )


def ready_labels(record: LabelRecord, *, as_of: datetime) -> tuple[float, ...] | None:
    """Return all 24 original-unit labels only when complete and available; else None.

    This gate does not log skipped scoring, store forecasts or implement a runner.
    Serialized loading is not implemented; structural validity is rechecked at this gate.
    """
    _origin(record.origin, record.clock_mode)
    if any(
        len(values) != 24
        for values in (record.timestamps, record.energy_kwh, record.file_valid, record.available_at)
    ):
        raise ValueError("Label record must contain exactly 24 bins and aligned fields")
    expected = tuple(record.origin + index * HOUR for index in range(24))
    rows = tuple(
        HourlyValue(record.identity, timestamp, energy, valid, arrival)
        for timestamp, energy, valid, arrival in zip(
            record.timestamps,
            record.energy_kwh,
            record.file_valid,
            record.available_at,
            strict=True,
        )
    )
    _rows(rows, expected, record.identity, record.origin, record.clock_mode)
    for row in rows:
        if row.file_valid and _finite_number(row.energy_kwh, "valid label energy") < 0:
            raise ValueError("Valid label energy cannot be negative")
    if not isinstance(as_of, datetime) or as_of.utcoffset() != record.origin.utcoffset():
        raise ValueError("as_of clock differs from label clock")
    if as_of < record.origin + DAY:
        return None
    if not all(record.file_valid) or any(
        value is None or arrival is None or arrival > as_of
        for value, arrival in zip(record.energy_kwh, record.available_at, strict=True)
    ):
        return None
    return tuple(float(value) for value in record.energy_kwh)


def build_initial_training_example(
    forecast: ForecastInput,
    labels: LabelRecord,
    *,
    prefix_start: datetime,
    cutoff: datetime,
) -> TrainingExample | None:
    """Require the full X/Y inside one allowed prefix and labels available by cutoff.

    The caller supplies source pre-deployment bounds or exact target-budget bounds.
    No scaler fitting, role selection or future replay eligibility filtering occurs.
    """
    _same_clock(prefix_start, forecast.origin, forecast.clock_mode)
    _same_clock(cutoff, forecast.origin, forecast.clock_mode)
    if (labels.identity, labels.origin, labels.clock_mode, labels.timestamps) != (
        forecast.identity,
        forecast.origin,
        forecast.clock_mode,
        forecast.future_labels,
    ):
        raise ValueError("Labels do not match the forecast identity/origin/clock/bins")
    if forecast.history_labels[0] < prefix_start or forecast.origin + DAY > cutoff:
        raise ValueError("Entire history and horizon must fit inside the permitted prefix")
    y_kwh = ready_labels(labels, as_of=cutoff)
    if y_kwh is None:
        return None
    y_scaled = tuple(
        _float32(_finite_number(value / forecast.energy_scale, "scaled label")) for value in y_kwh
    )
    return TrainingExample(forecast, y_kwh, y_scaled)
