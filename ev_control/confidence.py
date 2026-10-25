"""Report 1 §6: paired daily improvement, moving-block LCB and future-only choice."""

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from numbers import Real
from typing import Sequence

ALGORITHM = "ev-retention-controller-mbb-v1"
DAY = timedelta(days=1)


def finite(value: Real, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric")
    return float(value)


@dataclass(frozen=True)
class ControllerConfig:
    """All tuning values explicit; example configs are not a Final lock."""

    lambda_low: float
    lambda_high: float
    initial_lambda: float
    block_days: int
    min_valid_days: int
    delta: float
    alpha: float
    segment_days: int
    resamples: int
    seed: int

    def __post_init__(self) -> None:
        low, high = finite(self.lambda_low, "lambda_low"), finite(self.lambda_high, "lambda_high")
        if not 0 < low < high:
            raise ValueError("Require 0 < lambda_low < lambda_high")
        if finite(self.initial_lambda, "initial_lambda") not in self.levels:
            raise ValueError("Initial lambda must be a configured level")
        for name in ("block_days", "min_valid_days", "segment_days", "resamples", "seed"):
            x = getattr(self, name)
            if isinstance(x, bool) or not isinstance(x, int) or x < (0 if name == "seed" else 1):
                raise ValueError(f"Invalid {name}")
        if (
            not 1 <= self.segment_days < self.min_valid_days <= self.block_days
            or self.resamples < 2
        ):
            raise ValueError("Require segment < Bmin <= block days and at least 2 resamples")
        if finite(self.delta, "delta") < 0 or not 0 < finite(self.alpha, "alpha") < 1:
            raise ValueError("Require delta >= 0 and 0 < alpha < 1")

    @property
    def levels(self) -> tuple[float, float, float]:
        return (0.0, float(self.lambda_low), float(self.lambda_high))


@dataclass(frozen=True)
class DailyScore:
    """One target/day, three saved candidate predictions and one complete-label gate.

    MAEs are in configured-level order on the same fixed normalized scale.
    For incomplete days pass mae=None. Future/unavailable values are never read.
    The runner, not this helper, computes MAE and proves prediction-file lineage.
    """

    origin: datetime
    issued_at: datetime
    available_at: datetime | None
    valid_labels: int
    mae: tuple[float, float, float] | None
    scale_id: str
    prediction_ids: tuple[str, str, str]


@dataclass(frozen=True)
class Comparison:
    challenger: float
    mean_improvement: float
    lcb: float
    qualifies: bool


@dataclass(frozen=True)
class Decision:
    algorithm: str
    stream_id: str
    scale_id: str
    block_start: str
    effective_from: str
    active_lambda: float
    selected_lambda: float
    reason: str
    valid_days: int
    pending_days: int
    incomplete_days: int
    absent_days: int
    valid_day_gaps: int
    used_origins: tuple[str, ...]
    comparisons: tuple[Comparison, ...]
    config: dict
    bootstrap_seed: int
    paired_input_sha256: str

    def as_dict(self) -> dict:
        return asdict(self)


def linear_quantile(values: Sequence[float], probability: float) -> float:
    """Explicit linear interpolation at (N-1)*p; no library-default ambiguity."""
    if not values or not 0 <= probability <= 1:
        raise ValueError("Invalid quantile population/probability")
    ordered = sorted(finite(x, "bootstrap mean") for x in values)
    h = (len(ordered) - 1) * probability
    lo = int(h)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (h - lo)


def moving_block_indices(
    size: int, segment: int, resamples: int, seed: int
) -> tuple[tuple[int, ...], ...]:
    """Noncircular overlapping blocks on chronological valid-day ordinal indices.

    Draw starts uniformly in [0,B-L], concatenate blocks, trim each draw to B.
    Reuse these draws across both challengers, preserving paired comparisons.
    """
    if not 1 <= segment < size or resamples < 2:
        raise ValueError("Invalid moving-block dimensions")
    rng = random.Random(seed)
    output = []
    for _ in range(resamples):
        draw = []
        while len(draw) < size:
            start = rng.randrange(size - segment + 1)
            draw.extend(range(start, start + segment))
        output.append(tuple(draw[:size]))
    return tuple(output)


def choose_level(
    active: float, levels: tuple[float, float, float], comparisons: Sequence[Comparison]
) -> float:
    """Exact tie rule: largest qualifying LCB, nearest lambda, fixed level order."""
    eligible = [c for c in comparisons if c.qualifies]
    if not eligible:
        return active
    return min(
        eligible, key=lambda c: (-c.lcb, abs(c.challenger - active), levels.index(c.challenger))
    ).challenger


def _midnight(stamp: datetime, offset, name: str) -> None:
    if (
        not isinstance(stamp, datetime)
        or stamp.utcoffset() != offset
        or any((stamp.hour, stamp.minute, stamp.second, stamp.microsecond))
    ):
        raise ValueError(f"{name} must be midnight in the declared naive/fixed-offset clock")


def decide(
    rows: Sequence[DailyScore],
    *,
    config: ControllerConfig,
    active_lambda: float,
    block_start: datetime,
    as_of: datetime,
    stream_id: str,
    scale_id: str,
) -> Decision:
    """Decide at the block boundary; never select/rewrite past forecasts or weights.

    The caller retains the chosen TRAINED checkpoint/optimizer. A keep decision
    does not mean restore block-start state. This helper cannot access a model/Y.
    """
    if not isinstance(block_start, datetime):
        raise ValueError("Missing block start")
    offset = block_start.utcoffset()
    _midnight(block_start, offset, "block_start")
    stop = block_start + config.block_days * DAY
    _midnight(as_of, offset, "as_of")
    if as_of != stop:
        raise ValueError("Decision must be at this block boundary; no retrospective decisions")
    active = finite(active_lambda, "active_lambda")
    if active not in config.levels or not stream_id or not scale_id:
        raise ValueError("Unknown active level or missing stream/scale identity")
    used = []
    seen = set()
    pending = incomplete = 0
    for row in rows:
        _midnight(row.origin, offset, "daily origin")
        if not block_start <= row.origin < stop:
            continue
        if row.origin in seen:
            raise ValueError("Duplicate block day")
        seen.add(row.origin)
        if row.available_at is None:
            pending += 1
            continue
        if (
            not isinstance(row.available_at, datetime)
            or row.available_at.utcoffset() != offset
            or row.available_at < row.origin + DAY
        ):
            raise ValueError("Invalid complete-day label availability")
        if row.available_at > as_of:
            pending += 1
            continue
        if (
            isinstance(row.valid_labels, bool)
            or not isinstance(row.valid_labels, int)
            or not 0 <= row.valid_labels <= 24
        ):
            raise ValueError("valid_labels must be an integer in [0,24]")
        if row.valid_labels != 24:
            incomplete += 1
            if row.mae is not None:
                raise ValueError("Incomplete labels cannot supply partial-day MAE")
            continue
        if row.scale_id != scale_id or row.mae is None or len(row.mae) != 3:
            raise ValueError("All three normalized scores must share the fixed scale")
        if (
            not isinstance(row.issued_at, datetime)
            or row.issued_at.utcoffset() != offset
            or row.issued_at > row.origin
            or row.issued_at >= row.available_at
        ):
            raise ValueError("Predictions must be issued by origin and before label availability")
        if (
            len(row.prediction_ids) != 3
            or len(set(row.prediction_ids)) != 3
            or not all(row.prediction_ids)
        ):
            raise ValueError("Distinct identified predictions for all three candidates required")
        scores = tuple(finite(x, "normalized daily MAE") for x in row.mae)
        if any(x < 0 for x in scores):
            raise ValueError("MAE cannot be negative")
        used.append((row.origin, scores, row.prediction_ids))
    used.sort(key=lambda x: x[0])
    origins = tuple(origin.isoformat() for origin, _, _ in used)
    paired = [(origin.isoformat(), scores, ids) for origin, scores, ids in used]
    paired_sha = hashlib.sha256(json.dumps(paired, separators=(",", ":")).encode()).hexdigest()
    seed_payload = [
        ALGORITHM,
        config.seed,
        stream_id,
        scale_id,
        block_start.isoformat(),
        stop.isoformat(),
    ]
    seed = int.from_bytes(hashlib.sha256(json.dumps(seed_payload).encode()).digest(), "big")
    comparisons = []
    if len(used) >= config.min_valid_days:
        draws = moving_block_indices(len(used), config.segment_days, config.resamples, seed)
        active_index = config.levels.index(active)
        for i, candidate in enumerate(config.levels):
            if candidate == active:
                continue
            difference = [scores[active_index] - scores[i] for _, scores, _ in used]
            if any(not math.isfinite(x) for x in difference):
                raise ValueError("Overflow in paired improvement")
            means = [math.fsum(difference[j] for j in draw) / len(draw) for draw in draws]
            lcb = linear_quantile(means, config.alpha / 2)
            comparisons.append(
                Comparison(
                    candidate, math.fsum(difference) / len(difference), lcb, lcb > config.delta
                )
            )
    selected = choose_level(active, config.levels, comparisons)
    reason = (
        "insufficient_valid_days"
        if len(used) < config.min_valid_days
        else "switch"
        if selected != active
        else "no_qualifying_challenger"
    )
    return Decision(
        ALGORITHM,
        stream_id,
        scale_id,
        block_start.isoformat(),
        as_of.isoformat(),
        active,
        selected,
        reason,
        len(used),
        pending,
        incomplete,
        config.block_days - len(seen),
        sum(used[i][0] - used[i - 1][0] != DAY for i in range(1, len(used))),
        origins,
        tuple(comparisons),
        asdict(config),
        seed,
        paired_sha,
    )
