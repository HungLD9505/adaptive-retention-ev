"""Aggregate station-raw records without filling labels or inferring charger histories."""

from __future__ import annotations

import csv
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Iterable, TextIO
from zoneinfo import ZoneInfo

RAW_FIELDS = (
    "time",
    "busy",
    "idle",
    "s_price",
    "e_price",
    "fast_busy",
    "fast_idle",
    "slow_busy",
    "slow_idle",
    "duration",
    "volume",
)
HOURLY_FIELDS = (
    "dataset_id",
    "city_id",
    "entity_id",
    "timestamp",
    "energy_kwh",
    "file_valid_mask",
    "valid_sample_count",
    "expected_sample_count",
    "qc_flags",
)


@dataclass(frozen=True)
class HourlyConfig:
    """Explicit interval assumptions and fixed, unlearned completeness policy."""

    start: datetime
    end: datetime
    timezone_name: str
    interval_label: str

    def __post_init__(self) -> None:
        if self.start.tzinfo or self.end.tzinfo:
            raise ValueError("Window boundaries must be naive local clock values")
        if self.start >= self.end or any(
            (t.minute, t.second, t.microsecond) != (0, 0, 0) for t in (self.start, self.end)
        ):
            raise ValueError("Window must be positive and aligned to whole hours")
        if self.interval_label not in {"start", "end"}:
            raise ValueError("interval_label must be start or end")
        offsets = {
            (self.start + timedelta(hours=i)).replace(tzinfo=self.zone).utcoffset()
            for i in range(self.hours + 1)
        }
        if len(offsets) != 1:
            raise ValueError("DST/offset transitions require a separate reviewed binning rule")

    @property
    def zone(self) -> tzinfo:
        return timezone.utc if self.timezone_name == "UTC" else ZoneInfo(self.timezone_name)

    @property
    def hours(self) -> int:
        return int((self.end - self.start).total_seconds() // 3600)

    def slots(self) -> dict[str, int]:
        shift = 5 if self.interval_label == "end" else 0
        return {
            (self.start + timedelta(minutes=5 * i + shift)).isoformat(sep=" "): i
            for i in range(self.hours * 12)
        }


def numeric(value: str) -> float | None:
    """Return only finite numbers; blank/NaN/infinity remain invalid observations."""
    try:
        result = float(value)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def aggregate_station(
    stream: TextIO,
    writer: csv.writer,
    entity_id: str,
    config: HourlyConfig,
    slots: dict[str, int],
    charger_counts: tuple[int, int],
    rated_power_kw: float | None,
) -> dict:
    """Write every requested hour, leaving invalid target values empty.

    Occupancy/pricing/capacity anomalies are diagnostics, not data-derived filters.
    Complete hours require 12 unique on-grid finite nonnegative energy AND duration
    observations. Duplicates/off-grid rows invalidate the touched bin without repair.
    """
    reader = csv.reader(stream)
    if tuple(next(reader, ())) != RAW_FIELDS:
        raise ValueError(f"{entity_id}: unexpected station-raw header")
    sums = [0.0] * config.hours
    count = [0] * config.hours
    flags: dict[int, set[str]] = {}
    seen: set[int] = set()
    diagnostics: Counter = Counter()
    previous = -1
    slow_count, fast_count = charger_counts
    indices = {name: RAW_FIELDS.index(name) for name in RAW_FIELDS}
    for line, row in enumerate(reader, 2):
        diagnostics["rows_read"] += 1
        if len(row) != len(RAW_FIELDS):
            raise ValueError(f"{entity_id}:{line}: expected {len(RAW_FIELDS)} fields")
        slot = slots.get(row[0])
        if slot is None:
            try:
                stamp = datetime.fromisoformat(row[0])
            except ValueError as error:
                raise ValueError(f"{entity_id}:{line}: invalid timestamp {row[0]!r}") from error
            if stamp.tzinfo is not None:
                raise ValueError(f"{entity_id}:{line}: source clock unexpectedly timezone-aware")
            effective = stamp - timedelta(minutes=5 if config.interval_label == "end" else 0)
            if not config.start <= effective < config.end:
                diagnostics["rows_outside_window"] += 1
                continue
            hour = int((effective - config.start).total_seconds() // 3600)
            flags.setdefault(hour, set()).add("off_grid_timestamp")
            diagnostics["off_grid_rows"] += 1
            continue
        hour = slot // 12
        if slot in seen:
            flags.setdefault(hour, set()).add("duplicate_timestamp")
            diagnostics["duplicate_rows"] += 1
            continue
        seen.add(slot)
        if slot < previous:
            diagnostics["out_of_order_rows"] += 1
        previous = slot
        values = {name: numeric(row[index]) for name, index in indices.items() if name != "time"}
        for name, value in values.items():
            if value is None:
                diagnostics[f"invalid_{name}"] += 1
            elif value < 0:
                diagnostics[f"negative_{name}"] += 1
        volume, duration = values["volume"], values["duration"]
        valid = volume is not None and duration is not None and volume >= 0 and duration >= 0
        if valid:
            count[hour] += 1
            sums[hour] += volume
            diagnostics["valid_target_samples"] += 1
            diagnostics["zero_volume_samples"] += volume == 0
            if rated_power_kw is not None and volume > rated_power_kw / 12 + 1e-8:
                diagnostics["volume_above_static_rated_capacity"] += 1
            if duration > (slow_count + fast_count) / 12 + 1e-8:
                diagnostics["duration_above_static_charger_capacity"] += 1
            if (volume == 0) != (duration == 0):
                diagnostics["energy_duration_zero_disagreement"] += 1
        else:
            flags.setdefault(hour, set()).add("invalid_target_sample")
        counts = [
            values[n] for n in ("busy", "idle", "fast_busy", "fast_idle", "slow_busy", "slow_idle")
        ]
        if all(v is not None and v >= 0 and v.is_integer() for v in counts):
            busy, idle, fast_busy, fast_idle, slow_busy, slow_idle = counts
            if (
                busy + idle != slow_count + fast_count
                or fast_busy + fast_idle != fast_count
                or slow_busy + slow_idle != slow_count
                or busy != fast_busy + slow_busy
                or idle != fast_idle + slow_idle
            ):
                diagnostics["occupancy_count_inconsistency"] += 1
        else:
            diagnostics["invalid_occupancy_counts"] += 1
    diagnostics["unique_grid_samples"] = len(seen)
    diagnostics["missing_grid_samples"] = config.hours * 12 - len(seen)
    diagnostics["expected_hours"] = config.hours
    total = 0.0
    zone = config.zone
    for hour in range(config.hours):
        reasons = flags.get(hour, set()).copy()
        if count[hour] != 12:
            reasons.add("incomplete_hour")
        if not math.isfinite(sums[hour]):
            reasons.add("nonfinite_sum")
        valid = not reasons
        energy = format(sums[hour], ".17g") if valid else ""
        diagnostics["valid_hours" if valid else "invalid_hours"] += 1
        if valid:
            total += sums[hour]
            diagnostics["zero_energy_hours"] += sums[hour] == 0
        else:
            for reason in reasons:
                diagnostics[f"hours_{reason}"] += 1
        stamp = (config.start + timedelta(hours=hour)).replace(tzinfo=zone).isoformat()
        writer.writerow(
            (
                "urbanev",
                "SZH",
                entity_id,
                stamp,
                energy,
                int(valid),
                count[hour],
                12,
                ";".join(sorted(reasons)),
            )
        )
    return {
        "entity_id": entity_id,
        "diagnostics": dict(sorted(diagnostics.items())),
        "valid_energy_sum_kwh": total,
        "structural_qc_pass": not any(
            diagnostics[k] for k in ("duplicate_rows", "off_grid_rows", "out_of_order_rows")
        ),
    }


def summarize(stations: Iterable[dict]) -> dict:
    """Combine QC counts without selecting experimental cohorts or thresholds."""
    totals: Counter = Counter()
    count = 0
    usable = 0
    structural = 0
    for station in stations:
        count += 1
        totals.update(station["diagnostics"])
        usable += station["diagnostics"].get("valid_hours", 0) > 0
        structural += not station["structural_qc_pass"]
    return {
        "station_count": count,
        "stations_with_valid_hours": usable,
        "stations_with_structural_failures": structural,
        "counts": dict(sorted(totals.items())),
    }
