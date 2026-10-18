"""Verify known producer manifests and stage hourly rows in a local disk index."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ev_inputs.features import ClockMode, _validate_clock
from ev_inputs.windows import HourlyValue

FIELDS = (
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
HOUR = timedelta(hours=1)
CITIES = ("AMS", "JHB", "LOA", "MEL", "SPO", "SZH")


@dataclass(frozen=True)
class HourlySource:
    manifest_path: Path
    manifest_sha256: str
    hourly_path: Path
    hourly_sha256: str
    run_id: str
    dataset_id: str
    city_id: str
    clock_mode: ClockMode
    start: datetime
    stop: datetime
    entity_count: int
    expected_samples: int
    upstream: dict


def sha256_file(path: Path) -> str:
    """Hash bytes in bounded blocks; never modify source files."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise ValueError("Expected a lowercase SHA-256 fingerprint")


def _member(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("Producer output must be a relative member path")
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Producer output escapes the manifest directory")
    return path.resolve()


def read_source(
    manifest_path: Path,
    *,
    expected_manifest_sha256: str,
    dataset_id: str,
    city_id: str,
) -> HourlySource:
    """Recognize pinned producer layouts, without accepting research/online claims."""
    _digest(expected_manifest_sha256)
    manifest_path = manifest_path.resolve()
    data = manifest_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_manifest_sha256:
        raise ValueError("Producer manifest fingerprint mismatch")
    manifest = json.loads(data)
    config = manifest["config"]
    if not isinstance(manifest["run_id"], str) or not manifest["run_id"].strip():
        raise ValueError("Producer run ID is missing")
    if dataset_id == "urbanev" and city_id == "SZH":
        if manifest["status"] != "technical_qc_pass":
            raise ValueError("UrbanEV producer structural QC did not pass")
        if (
            config["timezone"] != "Asia/Shanghai"
            or config["output_interval"] != "[timestamp, timestamp + 1 hour)"
        ):
            raise ValueError("Unknown UrbanEV zone or output-bin profile")
        if config["source_interval_label"] not in ("start", "end"):
            raise ValueError("Unknown source interval assumption")
        zone = timezone(timedelta(hours=8))
        start, stop = (
            datetime.fromisoformat(config[key]) for key in ("start_local", "end_local_exclusive")
        )
        if start.tzinfo is not None or stop.tzinfo is not None:
            raise ValueError("Expected naive local bounds in UrbanEV producer config")
        start, stop = start.replace(tzinfo=zone), stop.replace(tzinfo=zone)
        clock, expected = "offset-aware-local", 12
        output = manifest["output"]
        count = manifest["summary"]["station_count"]
        upstream = {
            "archive": manifest["archive"],
            "code": manifest["code"],
            "assumptions": manifest["assumptions"],
            "research_acceptance": manifest["research_acceptance"],
            "config": config,
        }
    elif dataset_id == "charged" and city_id in CITIES:
        if manifest["status"] != "technical_success; input acceptance pending peer review":
            raise ValueError("CHARGED producer technical status is not recognized")
        if (
            manifest["contract_profile"] != "charged-hourly-v1-local-naive"
            or config["clock_policy"] != "publisher-local-naive"
        ):
            raise ValueError("Unknown CHARGED clock profile")
        if config["interval_label_assumption"] not in ("start", "end"):
            raise ValueError("Unknown source interval assumption")
        matches = [city for city in manifest["cities"] if city["city"] == city_id]
        if len(matches) != 1:
            raise ValueError("Expected one selected city in producer manifest")
        output, count = matches[0]["output"], matches[0]["site_count"]
        start, stop = (
            datetime.fromisoformat(config[key]) for key in ("start_inclusive", "end_exclusive")
        )
        clock, expected = "publisher-local-naive", 1
        upstream = {
            "archive": manifest["source_archive"],
            "code_commit": manifest["code_commit"],
            "contract_profile": manifest["contract_profile"],
            "original_observation_status": manifest["original_observation_status"],
            "strict_online_ready": manifest["strict_online_ready"],
            "config": config,
        }
    else:
        raise ValueError("Unsupported dataset/city; no pooling or guessed profile")
    for stamp in (start, stop):
        _validate_clock(stamp, clock)
    if stop <= start or isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ValueError("Invalid producer bounds or entity count")
    _digest(upstream["archive"]["sha256"])
    _digest(output["sha256"])
    hourly = _member(manifest_path.parent, output["path"])
    if hourly.stat().st_size != output["size_bytes"] or sha256_file(hourly) != output["sha256"]:
        raise ValueError("Hourly output size/fingerprint mismatch")
    return HourlySource(
        manifest_path,
        expected_manifest_sha256,
        hourly,
        output["sha256"],
        manifest["run_id"],
        dataset_id,
        city_id,
        clock,
        start,
        stop,
        count,
        expected,
        upstream,
    )


def stage_hourly(source: HourlySource, index_path: Path) -> sqlite3.Connection:
    """Read once, validate per-entity complete grids and index on disk, not all in RAM."""
    with index_path.open("xb"):
        pass
    connection = sqlite3.connect(index_path)
    try:
        connection.execute(
            "CREATE TABLE hourly (entity TEXT, stamp TEXT, energy REAL, valid INTEGER, PRIMARY KEY(entity, stamp))"
        )
        previous: dict[str, datetime] = {}
        with source.hourly_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            if tuple(next(reader, ())) != FIELDS:
                raise ValueError("Unexpected hourly header")
            for line, row in enumerate(reader, 2):
                if len(row) != len(FIELDS):
                    raise ValueError(f"Ragged hourly row {line}")
                dataset, city, entity, token, energy, mask, valid_count, expected_count, flags = row
                if (dataset, city) != (source.dataset_id, source.city_id) or not entity.strip():
                    raise ValueError(f"Wrong identity at row {line}")
                stamp = datetime.fromisoformat(token)
                _validate_clock(stamp, source.clock_mode)
                expected_stamp = previous.get(entity, source.start - HOUR) + HOUR
                if (
                    stamp.utcoffset() != source.start.utcoffset()
                    or stamp != expected_stamp
                    or stamp >= source.stop
                ):
                    raise ValueError(f"Gap/duplicate/order/clock error at row {line}")
                if (
                    mask not in ("0", "1")
                    or not valid_count.isdecimal()
                    or not expected_count.isdecimal()
                ):
                    raise ValueError(f"Invalid mask/count at row {line}")
                count, expected = int(valid_count), int(expected_count)
                if expected != source.expected_samples or not 0 <= count <= expected:
                    raise ValueError(f"Wrong sample counts at row {line}")
                valid = mask == "1"
                if valid:
                    value = float(energy)
                    if not math.isfinite(value) or value < 0 or count != expected:
                        raise ValueError(f"Invalid valid energy at row {line}")
                else:
                    if energy != "":
                        raise ValueError(f"Invalid energy must remain blank at row {line}")
                    value = None
                connection.execute(
                    "INSERT INTO hourly VALUES (?, ?, ?, ?)",
                    (entity, stamp.isoformat(), value, int(valid)),
                )
                previous[entity] = stamp
        if len(previous) != source.entity_count or any(
            stamp != source.stop - HOUR for stamp in previous.values()
        ):
            raise ValueError("Producer inventory or trailing grid differs from manifest")
        if sha256_file(source.hourly_path) != source.hourly_sha256:
            raise ValueError("Hourly source changed during staging")
        connection.commit()
        return connection
    except BaseException:
        connection.close()
        raise


def read_entity(
    connection: sqlite3.Connection,
    source: HourlySource,
    entity_id: str,
    *,
    delay_hours: int,
) -> list[HourlyValue]:
    """Read one entity; bin-end plus declared delay is an assumption, not arrival evidence."""
    if isinstance(delay_hours, bool) or not isinstance(delay_hours, int) or delay_hours < 0:
        raise ValueError("Availability delay must be a nonnegative integer number of hours")
    identity = (source.dataset_id, source.city_id, entity_id)
    return [
        HourlyValue(
            identity,
            datetime.fromisoformat(stamp),
            energy,
            bool(valid),
            datetime.fromisoformat(stamp) + HOUR + timedelta(hours=delay_hours),
        )
        for stamp, energy, valid in connection.execute(
            "SELECT stamp, energy, valid FROM hourly WHERE entity=? ORDER BY stamp", (entity_id,)
        )
    ]
