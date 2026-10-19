"""Verify, audit and aggregate immutable UrbanEV station-raw files into hourly data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import platform
import re
import subprocess
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from tools.sources import ROOT, Archive, load_catalog, verify_archive
from tools.urbanev_hourly import HOURLY_FIELDS, HourlyConfig, aggregate_station, summarize

LOGGER = logging.getLogger(__name__)


def fingerprint(path: Path) -> dict:
    """Read a file once for SHA-256, ZIP CRC32 and size; never write input bytes."""
    digest = hashlib.sha256()
    crc = 0
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            crc = zlib.crc32(block, crc)
            size += len(block)
    return {"sha256": digest.hexdigest(), "crc32": crc, "size_bytes": size}


def write_json(path: Path, payload: dict | list) -> None:
    """Create a new evidence file, refusing an existing destination."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)
        stream.write("\n")


def code_identity() -> dict:
    """Record commit, worktree diff identity and the executed source bytes."""
    command = ["git", "-C", str(ROOT)]
    revision = subprocess.run(command + ["rev-parse", "HEAD"], capture_output=True, text=True)
    diff = subprocess.run(command + ["diff", "HEAD", "--binary"], capture_output=True)
    status = subprocess.run(command + ["status", "--porcelain"], capture_output=True, text=True)
    return {
        "commit": revision.stdout.strip() if revision.returncode == 0 else "unavailable",
        "worktree_status": status.stdout.splitlines(),
        "tracked_diff_sha256": hashlib.sha256(diff.stdout).hexdigest(),
        "executed_sources": {
            name: fingerprint(ROOT / name)["sha256"]
            for name in ("tools/urbanev.py", "tools/urbanev_hourly.py", "tools/sources.py")
        },
    }


def read_metadata(source: Path) -> tuple[dict[str, tuple[int, int]], dict[str, float | None], dict]:
    """Validate station membership/counts and sum published charger power."""
    stations = {}
    with (source / "station_information.csv").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            entity = row["station_id"]
            if not re.fullmatch(r"[0-9]+", entity) or entity in stations:
                raise ValueError("Station IDs must be unique digit strings")
            slow, fast, total = (int(row[n]) for n in ("slow_count", "fast_count", "charge_count"))
            if min(slow, fast) < 0 or slow + fast != total:
                raise ValueError(f"{entity}: invalid infrastructure counts")
            stations[entity] = (slow, fast)
    powers = dict.fromkeys(stations, 0.0)
    counts = dict.fromkeys(stations, 0)
    seen = set()
    unknown_power = dict.fromkeys(stations, 0)
    with (source / "pile_rated_power.csv").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            station_number = float(row["station_id"])
            if not station_number.is_integer():
                raise ValueError("Nonintegral station ID in charger metadata")
            entity = str(int(station_number))
            power = float(row["power"])
            if entity not in stations or row["pile_id"] in seen:
                raise ValueError("Invalid charger identity or membership")
            seen.add(row["pile_id"])
            if 0 < power < float("inf"):
                powers[entity] += power
            else:
                unknown_power[entity] += 1
            counts[entity] += 1
    if not stations:
        raise ValueError("No station metadata")
    mismatches = [s for s, c in stations.items() if counts[s] != sum(c)]
    unreliable = set(mismatches) | {s for s, n in unknown_power.items() if n}
    usable_power = {s: None if s in unreliable else p for s, p in powers.items()}
    return (
        stations,
        usable_power,
        {
            "charger_count_mismatch_stations": mismatches,
            "nonpositive_or_nonfinite_power_entries": sum(unknown_power.values()),
            "stations_without_reliable_rated_capacity": sorted(unreliable),
            "policy": "metadata anomalies are diagnostics, not target filters; no invented capacity",
        },
    )


def verified_member(source: Path, relative: str, archive: ZipFile, prefix: str) -> dict:
    """Bind extracted bytes to an entry in the checksum-verified archive."""
    path = source / relative
    if path.is_symlink() or not path.resolve().is_relative_to(source):
        raise ValueError(f"Unsafe source member: {relative}")
    expected = archive.getinfo(prefix + relative)
    identity = fingerprint(path)
    if identity["size_bytes"] != expected.file_size or identity["crc32"] != expected.CRC:
        raise ValueError(f"Extracted bytes do not match verified ZIP member: {relative}")
    return {"path": relative, "archive_member": expected.filename, **identity}


def run_pipeline(
    source: Path,
    storage_root: Path,
    archive_spec: Archive,
    output_root: Path,
    config: HourlyConfig,
    run_id: str,
) -> tuple[Path, dict]:
    """Produce a new run, with explicit failed/incomplete evidence on errors."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", run_id):
        raise ValueError("Unsafe run ID")
    source = source.resolve()
    storage_root = storage_root.resolve()
    archive_path = (storage_root / archive_spec.relative_path).resolve()
    output = (output_root / run_id).resolve()
    if (
        output.is_relative_to(source)
        or source.is_relative_to(output)
        or output.is_relative_to(archive_path.parent)
        or output.is_relative_to((ROOT / "data/raw").resolve())
    ):
        raise ValueError("Output must be separate from raw inputs")
    output.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter()
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "research_acceptance": "pending_peer_review",
        "code": code_identity(),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "config": {
            "start_local": config.start.isoformat(),
            "end_local_exclusive": config.end.isoformat(),
            "timezone": config.timezone_name,
            "source_interval_label": config.interval_label,
            "output_interval": "[timestamp, timestamp + 1 hour)",
            "completeness": "12 unique on-grid finite nonnegative volume AND duration samples",
            "ancillary_anomalies": "diagnostics only; not target exclusions",
            "imputation": "none",
            "source_interval_minutes": 5,
        },
        "assumptions": {
            "time_alignment": "explicit provisional assumption; upstream generator unavailable",
            "label_arrival": "not established; output availability is not an arrival-time claim",
            "energy": "publisher-derived estimate, not independent meter readings",
            "observation_status": "unknown upstream history; file validity is not an observed mask",
        },
        "source_root": str(source),
        "archive": {
            "source_id": archive_spec.source_id,
            "sha256": archive_spec.sha256,
            "size_bytes": archive_spec.size_bytes,
            "path": str(archive_path),
        },
    }
    records = []
    try:
        passed, message = verify_archive(archive_spec, storage_root)
        if not passed:
            raise ValueError(f"Raw archive verification failed: {message}")
        manifest["archive"]["verification"] = message
        with ZipFile(archive_path) as archive:
            prefixes = [
                n.removesuffix("station_information.csv")
                for n in archive.namelist()
                if n.endswith("_station-raw/station_information.csv")
            ]
            if len(prefixes) != 1:
                raise ValueError("Expected exactly one station-raw subtree in archive")
            prefix = prefixes[0]
            manifest["metadata"] = [
                verified_member(source, n, archive, prefix)
                for n in ("station_information.csv", "pile_rated_power.csv", "station_distance.csv")
            ]
            stations, powers, metadata_qc = read_metadata(source)
            manifest["metadata_qc"] = metadata_qc
            files = {p.name for p in (source / "charge_5min").iterdir() if p.is_file()}
            if files != {s + ".csv" for s in stations}:
                raise ValueError("Station-series inventory differs from metadata")
            archive_files = {
                n.removeprefix(prefix + "charge_5min/")
                for n in archive.namelist()
                if n.startswith(prefix + "charge_5min/") and not n.endswith("/")
            }
            if archive_files != files:
                raise ValueError("Archive station inventory differs from extraction")
            slots = config.slots()
            with (output / "hourly.csv").open("x", newline="", encoding="utf-8") as target:
                writer = csv.writer(target)
                writer.writerow(HOURLY_FIELDS)
                for index, entity in enumerate(sorted(stations, key=int), 1):
                    relative = f"charge_5min/{entity}.csv"
                    identity = verified_member(source, relative, archive, prefix)
                    path = source / relative
                    before = path.stat()
                    with path.open(newline="", encoding="utf-8-sig") as stream:
                        result = aggregate_station(
                            stream, writer, entity, config, slots, stations[entity], powers[entity]
                        )
                    after = path.stat()
                    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                        raise ValueError(f"Source changed during processing: {relative}")
                    records.append({**result, "input": identity})
                    if index % 50 == 0 or index == len(stations):
                        LOGGER.info("Processed %s/%s stations", index, len(stations))
        summary = summarize(records)
        manifest["summary"] = summary
        manifest["status"] = (
            "technical_qc_pass"
            if not summary["stations_with_structural_failures"]
            else "structural_qc_failed"
        )
        manifest["output"] = {"path": "hourly.csv", **fingerprint(output / "hourly.csv")}
        write_json(output / "station_qc.json", records)
    except (OSError, ValueError, KeyError, BadZipFile, csv.Error, OverflowError) as error:
        manifest["status"] = "failed"
        manifest["error"] = str(error)
        manifest["completed_station_count"] = len(records)
        write_json(output / "completed_station_qc.json", records)
        raise
    finally:
        manifest["elapsed_seconds"] = time.perf_counter() - began
        manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(output / "manifest.json", manifest)
    return output, manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage-root", type=Path, default=ROOT, help="Root containing catalog data/raw paths"
    )
    parser.add_argument(
        "--source-root", type=Path, required=True, help="Extracted station-raw directory"
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--start", required=True, help="Local inclusive hour, ISO format")
    parser.add_argument("--end", required=True, help="Local exclusive hour, ISO format")
    parser.add_argument("--timezone", required=True, help="Explicit IANA zone, or UTC")
    parser.add_argument(
        "--interval-label",
        choices=("start", "end"),
        required=True,
        help="Provisional source five-minute interval timestamp convention",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        config = HourlyConfig(
            datetime.fromisoformat(args.start),
            datetime.fromisoformat(args.end),
            args.timezone,
            args.interval_label,
        )
        source = next(a for a in load_catalog() if a.source_id == "urbanev-main")
        output, manifest = run_pipeline(
            args.source_root, args.storage_root, source, args.output_root, config, args.run_id
        )
        print(f"{manifest['status']}: {output}")
        return 0 if manifest["status"] == "technical_qc_pass" else 1
    except (OSError, ValueError, KeyError, BadZipFile, csv.Error, OverflowError) as error:
        LOGGER.error("UrbanEV processing failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
