"""Read-only release-period and exact-coordinate evidence for Issue 17 Steps 3/4."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterator
from zipfile import BadZipFile, ZipFile

from tools.sources import ROOT, load_catalog, verify_archive

URBAN_PREFIX = "UrbanEVDataset/20220901-20230228_station-raw/"


def csv_rows(archive: ZipFile, member: str) -> Iterator[list[str]]:
    with archive.open(member) as stream:
        yield from csv.reader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""))


def metadata(archive: ZipFile, member: str) -> list[dict[str, str]]:
    reader = csv_rows(archive, member)
    header = next(reader)
    result = []
    for row in reader:
        if len(row) != len(header):
            raise ValueError(f"Ragged metadata: {member}")
        result.append(dict(zip(header, row)))
    return result


def coordinate_overlap(left: list[dict], right: list[dict], left_id: str, right_id: str) -> dict:
    """Exact numeric coordinates only; no physical identity or CRS conversion claim."""

    def group(records: list[dict], key: str) -> dict:
        groups: dict = {}
        for row in records:
            lon, lat = Decimal(row["longitude"]), Decimal(row["latitude"])
            if (
                not lon.is_finite()
                or not lat.is_finite()
                or not (-180 <= lon <= 180 and -90 <= lat <= 90)
            ):
                raise ValueError("Invalid coordinate")
            groups.setdefault((lon, lat), []).append(row[key])
        return groups

    a, b = group(left, left_id), group(right, right_id)
    shared = a.keys() & b.keys()
    return {
        "left_rows": len(left),
        "right_rows": len(right),
        "left_unique_coordinate_pairs": len(a),
        "right_unique_coordinate_pairs": len(b),
        "shared_coordinate_pairs": len(shared),
        "left_rows_at_shared_coordinates": sum(len(a[k]) for k in shared),
        "right_rows_at_shared_coordinates": sum(len(b[k]) for k in shared),
        "examples": [
            {
                "longitude": str(k[0]),
                "latitude": str(k[1]),
                "left_ids": a[k][:5],
                "right_ids": b[k][:5],
                "left_count": len(a[k]),
                "right_count": len(b[k]),
            }
            for k in sorted(shared)[:3]
        ],
        "interpretation": "Coordinate overlap only; not a one-to-one physical-entity mapping",
    }


def clock_span(archive: ZipFile, member: str) -> dict:
    reader = csv_rows(archive, member)
    next(reader)
    stamps = []
    for row in reader:
        stamps.append(datetime.fromisoformat(row[0]))
    if not stamps:
        raise ValueError(f"Empty sampled timeline: {member}")
    return {
        "archive_member": member,
        "rows": len(stamps),
        "minimum_literal_clock": min(stamps).isoformat(),
        "maximum_literal_clock": max(stamps).isoformat(),
        "unique_clocks": len(set(stamps)),
        "sample_scope": "This member only; not a scan of every entity",
    }


def inspect_releases(urban: ZipFile, charged: ZipFile) -> dict:
    stations = metadata(urban, URBAN_PREFIX + "station_information.csv")
    chargers = metadata(charged, "SZH/chargers.csv")
    sites = metadata(charged, "SZH/sites.csv")
    periods = {
        "urbanev_station_1001": clock_span(urban, URBAN_PREFIX + "charge_5min/1001.csv"),
        "charged_szh_volume": clock_span(charged, "SZH/volume.csv"),
    }
    return {
        "comparison": "UrbanEV station-raw vs CHARGED standard SZH; exact Decimal coordinates",
        "station_vs_charger": coordinate_overlap(stations, chargers, "station_id", "charger_id"),
        "station_vs_site": coordinate_overlap(stations, sites, "station_id", "site_id"),
        "sampled_periods": periods,
        "claims": {
            "physical_entity_mapping": "not_established",
            "record_level_duplication": "not_tested",
            "independent_external_validation": "not_established",
            "strict_online_ready": "not_established",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    storage, output = args.storage_root.resolve(), args.output.resolve()
    if output.is_relative_to(storage / "data/raw"):
        parser.error("Evidence must be outside raw storage")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            start = time.perf_counter()
            result = {
                "run_id": output.stem,
                "scope": "Issue 17 Steps 3/4; no windows, cohorts or data changes",
                "started_at_utc": datetime.now(timezone.utc).isoformat(),
                "code_commit": subprocess.check_output(
                    ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
                ).strip(),
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "python": platform.python_version(),
                "platform": platform.platform(),
                "archives": [],
                "status": "running",
            }
            try:
                specs = {a.source_id: a for a in load_catalog()}
                for name in ("urbanev-main", "charged-hourly"):
                    spec = specs[name]
                    passed, message = verify_archive(spec, storage)
                    if not passed:
                        raise ValueError(f"Archive verification failed: {name}: {message}")
                    result["archives"].append(
                        {
                            "source_id": name,
                            "sha256": spec.sha256,
                            "size_bytes": spec.size_bytes,
                            "verification": message,
                        }
                    )
                with (
                    ZipFile(storage / specs["urbanev-main"].relative_path) as urban,
                    ZipFile(storage / specs["charged-hourly"].relative_path) as charged,
                ):
                    result["release_comparison"] = inspect_releases(urban, charged)
                result["status"] = "evidence_complete; no dataset acceptance or method change"
            except (OSError, ValueError, KeyError, BadZipFile, csv.Error, ArithmeticError) as error:
                result.update(status="failed", error=str(error))
                raise
            finally:
                result["elapsed_seconds"] = time.perf_counter() - start
                json.dump(result, stream, indent=2)
                stream.write("\n")
        return 0
    except (OSError, ValueError, KeyError, BadZipFile, csv.Error, ArithmeticError) as error:
        print(f"CHARGED suitability evidence failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
