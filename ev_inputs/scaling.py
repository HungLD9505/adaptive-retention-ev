"""Proposed prefix-only p95 fitting; no producer IO, windows or cohort selection."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from numbers import Real
from typing import Iterable

SCALE_POLICY = "entity-prefix-p95-linear-v1"


@dataclass(frozen=True)
class EnergySample:
    """One hourly bin with explicit replay availability, not inferred arrival time."""

    timestamp: datetime
    available_at: datetime
    energy_kwh: Real | None
    file_valid: bool


@dataclass(frozen=True)
class FittedScale:
    """Reviewable fit provenance; the input-run manifest must add code/runtime IDs."""

    policy: str
    identity: tuple[str, str, str]
    start: datetime
    cutoff: datetime
    valid_count: int
    zero_count: int
    p95_kwh: float
    energy_scale: float
    fallback: str | None
    fit_sha256: str


def _whole_hour(value: datetime, *, aware: bool) -> None:
    if not isinstance(value, datetime):
        raise TypeError("Time fields must be datetimes")
    if (value.utcoffset() is not None) != aware:
        raise ValueError("Mixed naive and aware clocks are not allowed")
    if value.minute or value.second or value.microsecond:
        raise ValueError("Bin labels and bounds must be whole hours")


def fit_energy_scale(
    samples: Iterable[EnergySample],
    *,
    identity: tuple[str, str, str],
    start: datetime,
    cutoff: datetime,
) -> FittedScale:
    """Fit per entity on valid bins wholly inside [start, cutoff), available by cutoff.

    The caller must enforce the entity role, producer profile, source pre-deployment
    bound or exact target budget. Samples belong to ONE identified entity. Outside
    bins are ignored before reading their energy/validity/availability. No latest-
    stream refit, clipping, imputation or implicit empty-prefix scale is performed.
    """
    if len(identity) != 3 or any(
        not isinstance(part, str) or not part.strip() for part in identity
    ):
        raise ValueError("identity must contain dataset, city and entity strings")
    if not isinstance(start, datetime) or not isinstance(cutoff, datetime):
        raise TypeError("Bounds must be datetimes")
    aware = start.utcoffset() is not None
    _whole_hour(start, aware=aware)
    _whole_hour(cutoff, aware=aware)
    if start >= cutoff:
        raise ValueError("start must precede cutoff")
    rows: list[tuple[str, str, float]] = []
    seen: set[datetime] = set()
    for sample in samples:
        _whole_hour(sample.timestamp, aware=aware)
        if not start <= sample.timestamp < cutoff:
            continue
        if sample.timestamp in seen:
            raise ValueError("Duplicate prefix bin")
        seen.add(sample.timestamp)
        if not isinstance(sample.file_valid, bool):
            raise TypeError("file_valid must be boolean")
        if not sample.file_valid:
            continue
        if not isinstance(sample.available_at, datetime):
            raise TypeError("available_at must be a datetime")
        if (sample.available_at.utcoffset() is not None) != aware:
            raise ValueError("Availability clock differs from prefix clock")
        if sample.available_at < sample.timestamp + timedelta(hours=1):
            raise ValueError("Availability cannot precede the exclusive bin end")
        if sample.available_at > cutoff:
            continue
        value = sample.energy_kwh
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError("Valid available energy must be numeric")
        try:
            energy = float(value)
        except OverflowError as error:
            raise ValueError("Energy must be finite") from error
        if not math.isfinite(energy) or energy < 0:
            raise ValueError("Valid available energy must be finite and nonnegative")
        rows.append((sample.timestamp.isoformat(), sample.available_at.isoformat(), energy))
    if not rows:
        raise ValueError("No valid available prefix energy; scale is undefined")
    values = sorted(row[2] for row in rows)
    position = (len(values) - 1) * 0.95
    low = math.floor(position)
    weight = position - low
    high = min(low + 1, len(values) - 1)
    p95 = values[low] * (1 - weight) + values[high] * weight
    # A declared 1 kWh unit fallback preserves zeros and sparse activity without
    # fitting any future data. This proposed policy requires development review.
    scale = p95 if p95 > 0 else 1.0
    payload = json.dumps(
        [SCALE_POLICY, identity, start.isoformat(), cutoff.isoformat(), sorted(rows)],
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return FittedScale(
        policy=SCALE_POLICY,
        identity=identity,
        start=start,
        cutoff=cutoff,
        valid_count=len(values),
        zero_count=values.count(0.0),
        p95_kwh=p95,
        energy_scale=scale,
        fallback="zero-p95-unit-kwh" if p95 == 0 else None,
        fit_sha256=hashlib.sha256(payload).hexdigest(),
    )


def target_prefix_start(deployment: datetime, history_days: int) -> datetime:
    """Return an exact nominal 7/14/28-day prefix start, without choosing eligibility.

    Use a validated producer clock: this arithmetic does not resolve DST or prove
    elapsed physical hours for offset-free CHARGED labels.
    """
    if isinstance(history_days, bool) or history_days not in (7, 14, 28):
        raise ValueError("Target history must be exactly 7, 14 or 28 days")
    if not isinstance(history_days, int):
        raise TypeError("history_days must be an integer")
    if not isinstance(deployment, datetime):
        raise TypeError("deployment must be a datetime")
    _whole_hour(deployment, aware=deployment.utcoffset() is not None)
    return deployment - timedelta(days=history_days)
