"""Read-only CHARGED Step-1 inventory; no QC acceptance, repairs or cohort selection."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import re
import subprocess
import sys
import time
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from tools.sources import ROOT, Archive, load_catalog, verify_archive

CITIES = ("AMS", "JHB", "LOA", "MEL", "SPO", "SZH")
MATRICES = ("volume.csv", "duration.csv", "e_price.csv", "s_price.csv")
FILES = (
    *MATRICES,
    "info.csv",
    "sites.csv",
    "chargers.csv",
    "distance.csv",
    "weather.csv",
    "poi.csv",
)


def file_identity(path: Path) -> dict:
    digest = hashlib.sha256()
    crc = size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            crc = zlib.crc32(block, crc)
            size += len(block)
    return {"sha256": digest.hexdigest(), "crc32": crc, "size_bytes": size}


def token_kind(value: str) -> tuple[str, float | None]:
    """Descriptive categories; not an acceptance rule or original-observation mask."""
    if not value.strip():
        return "blank", None
    try:
        number = float(value)
    except ValueError:
        return "nonnumeric", None
    if not math.isfinite(number):
        return "nonfinite", None
    return "finite", number


def numeric_counts(values: list[str], counts: Counter) -> None:
    for value in values:
        kind, number = token_kind(value)
        counts[kind] += 1
        if number is not None:
            counts["zero"] += number == 0
            counts["negative"] += number < 0
            counts["positive"] += number > 0


def time_inventory(tokens: list[str]) -> dict:
    """Describe literal clocks without assigning timezone or filling timestamps."""
    stamps = []
    failures = []
    for value in tokens:
        try:
            try:
                stamp = datetime.fromisoformat(value)
            except ValueError:
                stamp = datetime.strptime(value, "%Y/%m/%d %H:%M")
            stamps.append(stamp)
        except ValueError:
            if len(failures) < 3:
                failures.append(value)
    offsets = Counter(str(t.utcoffset()) if t.tzinfo else "no_offset" for t in stamps)
    # Compare like clocks only. A mixed offset/naive series is itself an inventory finding.
    comparable = len(offsets) <= 1
    steps = (
        Counter((b - a).total_seconds() for a, b in zip(stamps, stamps[1:])) if comparable else {}
    )
    return {
        "rows": len(tokens),
        "parsed": len(stamps),
        "parse_failures": len(tokens) - len(stamps),
        "parse_failure_examples": failures,
        "first_literal": tokens[0] if tokens else None,
        "last_literal": tokens[-1] if tokens else None,
        "unique_parsed": len(set(stamps)),
        "duplicates": len(stamps) - len(set(stamps)),
        "offset_tokens": dict(offsets),
        "step_seconds": {str(k): v for k, v in sorted(steps.items())},
        "non_hour_steps": sum(v for k, v in steps.items() if k != 3600) if comparable else None,
        "parsed_sequence_sha256": hashlib.sha256(
            json.dumps([t.isoformat() for t in stamps]).encode()
        ).hexdigest(),
        "within_span_missing_hour_slots": (
            int((max(stamps) - min(stamps)).total_seconds() // 3600) + 1 - len(set(stamps))
            if stamps
            and comparable
            and all(t.minute == t.second == t.microsecond == 0 for t in stamps)
            else None
        ),
        "timezone_verified": False,
        "bin_endpoint_verified": False,
    }


def inspect_csv(path: Path, role: str) -> dict:
    """Record actual headers, row shapes, IDs and values without editing sources."""
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader, [])
        if not header:
            raise ValueError(f"Empty CSV/header: {path.name}")
        report = {"header": header, "header_count": len(header), "rows": 0}
        widths: Counter = Counter()
        blanks: Counter = Counter()
        numbers: Counter = Counter()
        row_ids = []
        times = []
        malformed_examples = []
        site_columns = header[1:] if role == "matrix" else []
        per_site = [Counter() for _ in site_columns]
        site_member_counts: Counter = Counter()
        member_column = next((header.index(n) for n in ("site_id", "site") if n in header), None)
        id_column = (
            header.index("charger_id")
            if role == "chargers" and "charger_id" in header
            else member_column
            if role == "sites"
            else 0
        )
        per_column_missing = Counter()
        for line, row in enumerate(reader, 2):
            report["rows"] += 1
            widths[len(row)] += 1
            if len(row) != len(header) and len(malformed_examples) < 2:
                malformed_examples.append({"line": line, "values": row})
            blanks["blank_present_cells"] += sum(not value.strip() for value in row)
            blanks["absent_cells_in_short_rows"] += max(0, len(header) - len(row))
            blanks["extra_cells_in_long_rows"] += max(0, len(row) - len(header))
            if role in {"matrix", "weather"}:
                times.append(row[0] if row else "")
            if role in {"sites", "chargers", "distance"}:
                row_ids.append(
                    row[id_column] if id_column is not None and len(row) > id_column else ""
                )
            if role == "chargers" and member_column is not None and len(row) > member_column:
                site_member_counts[row[member_column]] += 1
            if role == "matrix":
                # Counts refer to physically present data cells, not fabricated missing values.
                for index, value in enumerate(row[1 : len(header)]):
                    kind, number = token_kind(value)
                    numbers[kind] += 1
                    per_site[index][kind] += 1
                    if number is not None:
                        numbers["zero"] += number == 0
                        numbers["negative"] += number < 0
                        numbers["positive"] += number > 0
                        per_site[index]["zero"] += number == 0
                        per_site[index]["positive"] += number > 0
                        per_site[index]["negative"] += number < 0
            elif role == "distance":
                numeric_counts(row[1 : len(header)], numbers)
            elif role == "weather":
                for name, value in zip(header, row):
                    if not value.strip():
                        per_column_missing[name] += 1
        report.update(
            {
                "row_widths": dict(sorted(widths.items())),
                "rows_with_width_mismatch": sum(n for w, n in widths.items() if w != len(header)),
                "width_mismatch_examples": malformed_examples,
                "missing_cells": dict(blanks),
            }
        )
        if role in {"matrix", "weather"}:
            report["time"] = time_inventory(times)
            report["timestamp_sequence_sha256"] = hashlib.sha256(
                json.dumps(times).encode()
            ).hexdigest()
        if role in {"matrix", "distance"}:
            report["numeric_cells"] = dict(numbers)
            report["data_columns"] = header[1:]
            report["duplicate_column_ids"] = len(header[1:]) - len(set(header[1:]))
        if role == "matrix":
            report["all_zero_sites"] = [
                s
                for s, c in zip(site_columns, per_site)
                if report["rows"] > 0 and c["zero"] == report["rows"]
            ]
            report["per_site_numeric_counts"] = dict(zip(site_columns, map(dict, per_site)))
        if role in {"sites", "chargers", "distance"}:
            report["row_ids"] = row_ids
            report["blank_ids"] = row_ids.count("")
            report["duplicate_ids"] = len(row_ids) - len(set(row_ids))
        if role == "chargers":
            report["membership_column_observed"] = (
                header[member_column] if member_column is not None else None
            )
            report["members_per_site"] = dict(site_member_counts)
        if role == "weather":
            report["blanks_by_column"] = dict(per_column_missing)
        return report


def inspect_city(directory: Path, archive: ZipFile) -> dict:
    """Inspect one standard city; no normalization or acceptance decisions."""
    city = directory.name
    present = sorted(p.name for p in directory.iterdir() if p.is_file())
    result = {
        "city": city,
        "present_files": present,
        "missing_expected_files": sorted(set(FILES) - set(present)),
        "unexpected_files": sorted(set(present) - set(FILES)),
        "files": {},
        "readiness": {
            "file_valid": "not_adjudicated; inventory diagnostics only",
            "forecasting_eligible": "not_assessed; official windows/cohorts belong to #18",
            "strict_online_ready": "not_established; upstream/availability audit deferred",
        },
    }
    for name in FILES:
        if name not in present:
            continue
        path = directory / name
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError("Unsafe source member")
        identity = file_identity(path)
        member = archive.getinfo(city + "/" + name)
        if identity["size_bytes"] != member.file_size or identity["crc32"] != member.CRC:
            raise ValueError(f"Extracted bytes differ from verified ZIP: {city}/{name}")
        role = "matrix" if name in MATRICES else Path(name).stem
        report = inspect_csv(path, role)
        report["input"] = {"archive_member": member.filename, **identity}
        result["files"][name] = report
    files = result["files"]
    sites = set(files.get("sites.csv", {}).get("row_ids", []))
    result["site_rows"] = files.get("sites.csv", {}).get("rows")
    result["unique_sites"] = len(sites)
    result["charger_rows"] = files.get("chargers.csv", {}).get("rows")
    result["site_id_header_observed"] = next(
        (n for n in ("site_id", "site") if n in files.get("sites.csv", {}).get("header", [])), None
    )
    result["matrix_site_id_matches"] = {
        n: set(files[n]["data_columns"]) == sites for n in MATRICES if n in files
    }
    result["distance_site_ids_match"] = (
        set(files.get("distance.csv", {}).get("data_columns", [])) == sites
        and set(files.get("distance.csv", {}).get("row_ids", [])) == sites
    )
    result["charger_unknown_site_ids"] = sorted(
        set(files.get("chargers.csv", {}).get("members_per_site", {})) - sites
    )
    result["hourly_timestamp_sequences_match"] = (
        len({files[n]["timestamp_sequence_sha256"] for n in MATRICES if n in files}) == 1
    )
    volume_clock = files.get("volume.csv", {}).get("timestamp_sequence_sha256")
    result["weather_timestamp_literals_match_volume"] = (
        files.get("weather.csv", {}).get("timestamp_sequence_sha256") == volume_clock
    )
    result["weather_parsed_clock_matches_volume"] = (
        all(
            n in files and files[n]["time"]["parse_failures"] == 0
            for n in ("weather.csv", "volume.csv")
        )
        and files["weather.csv"]["time"]["parsed_sequence_sha256"]
        == files["volume.csv"]["time"]["parsed_sequence_sha256"]
    )
    result["findings"] = []
    for name, report in files.items():
        if report["rows_with_width_mismatch"]:
            result["findings"].append(f"{name}: row widths differ from header")
        if report.get("duplicate_ids", 0):
            result["findings"].append(f"{name}: duplicate identifiers")
        if (
            report.get("time", {}).get("duplicates", 0)
            or report.get("time", {}).get("parse_failures", 0)
            or report.get("time", {}).get("non_hour_steps", 0)
        ):
            result["findings"].append(f"{name}: inspect clock diagnostics")
    return result


def inventory(source: Path, storage: Path, spec: Archive, output: Path) -> dict:
    """Create one immutable inventory run; return no scientific acceptance verdict."""
    source, storage, output = source.resolve(), storage.resolve(), output.resolve()
    archive_path = storage / spec.relative_path
    if (
        output.is_relative_to(archive_path.parent)
        or output.is_relative_to(source)
        or source.is_relative_to(output)
    ):
        raise ValueError("Inventory output must be separate from raw inputs")
    output.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter()
    run = {
        "run_id": output.name,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Issue 17 Step 1 only; six standard cities; no data transformations or eligibility decisions",
        "status": "running",
        "code_commit": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "script_sha256": file_identity(Path(__file__))["sha256"],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "source_archive": {
            "source_id": spec.source_id,
            "sha256": spec.sha256,
            "size_bytes": spec.size_bytes,
        },
        "cities": [],
    }
    try:
        passed, message = verify_archive(spec, storage)
        if not passed:
            raise ValueError(f"Archive verification failed: {message}")
        run["source_archive"]["verification"] = message
        run["extracted_city_directories"] = sorted(p.name for p in source.iterdir() if p.is_dir())
        with ZipFile(archive_path) as archive:
            for city in CITIES:
                if not (source / city).is_dir():
                    raise ValueError(f"Missing standard city directory: {city}")
                run["cities"].append(inspect_city(source / city, archive))
                print(f"Inventoried {city}", flush=True)
        run["status"] = "inventory_complete; QC acceptance not decided"
    except (OSError, ValueError, KeyError, BadZipFile, csv.Error) as error:
        run["status"] = "failed"
        run["error"] = str(error)
        raise
    finally:
        run["elapsed_seconds"] = time.perf_counter() - began
        with (output / "inventory.json").open("x", encoding="utf-8") as stream:
            json.dump(run, stream, indent=2, allow_nan=False)
            stream.write("\n")
    return run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, default=ROOT)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", args.run_id):
        parser.error("Unsafe run ID")
    try:
        spec = next(a for a in load_catalog() if a.source_id == "charged-hourly")
        result = inventory(
            args.source_root, args.storage_root, spec, args.output_root / args.run_id
        )
        print(result["status"])
        return 0
    except (OSError, ValueError, KeyError, BadZipFile, csv.Error) as error:
        print(f"CHARGED inventory failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
