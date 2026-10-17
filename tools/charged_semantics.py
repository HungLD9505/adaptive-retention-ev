"""Read-only AMS paired-zero and metadata evidence for Issue 17 Step 2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from itertools import zip_longest
from pathlib import Path
from typing import Iterator
from zipfile import BadZipFile, ZipFile

from tools.sources import ROOT, load_catalog, verify_archive


def rows(archive: ZipFile, member: str) -> Iterator[list[str]]:
    """Stream original archive CSV bytes; never extract or write raw inputs."""
    with archive.open(member) as stream:
        yield from csv.reader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""))


def finite_nonnegative(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Nonfinite/negative audit input: {value!r}")
    return number


def audit_ams(archive: ZipFile) -> dict:
    """Describe paired release values and static metadata; make no QC decisions."""
    volume, duration = rows(archive, "AMS/volume.csv"), rows(archive, "AMS/duration.csv")
    header = next(volume)
    if header != next(duration) or len(set(header[1:])) != len(header) - 1:
        raise ValueError("AMS volume/duration headers differ or repeat IDs")
    ids = header[1:]
    zero_v, zero_d = set(ids), set(ids)
    total_v = dict.fromkeys(ids, 0.0)
    total_d = dict.fromkeys(ids, 0.0)
    paired: Counter = Counter()
    examples: dict[str, list] = {}
    count = 0
    for v, d in zip_longest(volume, duration):
        if v is None or d is None or len(v) != len(header) or len(d) != len(header) or v[0] != d[0]:
            raise ValueError("AMS paired rows differ in length, width or clock")
        count += 1
        for site, vs, ds in zip(ids, v[1:], d[1:]):
            energy, hours = finite_nonnegative(vs), finite_nonnegative(ds)
            total_v[site] += energy
            total_d[site] += hours
            if energy > 0:
                zero_v.discard(site)
            if hours > 0:
                zero_d.discard(site)
            category = f"volume_{'positive' if energy else 'zero'}_duration_{'positive' if hours else 'zero'}"
            paired[category] += 1
            if (energy == 0) != (hours == 0):
                sample = examples.setdefault(category, [])
                if len(sample) < 3:
                    sample.append(
                        {"site_id": site, "timestamp": v[0], "volume": vs, "duration": ds}
                    )
    if not count:
        raise ValueError("No AMS paired rows")
    site_rows = rows(archive, "AMS/sites.csv")
    site_header = next(site_rows)
    sites = {}
    for row in site_rows:
        if len(row) != len(site_header):
            raise ValueError("Ragged AMS site metadata")
        item = dict(zip(site_header, row))
        if item["site_id"] in sites:
            raise ValueError("Duplicate AMS site metadata ID")
        sites[item["site_id"]] = item
    if set(sites) != set(ids):
        raise ValueError("AMS site metadata does not match matrix IDs")
    charger_rows = rows(archive, "AMS/chargers.csv")
    charger_header = next(charger_rows)
    members: dict[str, list] = {s: [] for s in ids}
    for row in charger_rows:
        if len(row) != len(charger_header):
            raise ValueError("Ragged AMS charger metadata")
        item = dict(zip(charger_header, row))
        members[item["site_id"]].append(item)
    static_v = {s: finite_nonnegative(m["total_volume"]) for s, m in sites.items()}
    static_d = {s: finite_nonnegative(m["total_duration"]) for s, m in sites.items()}
    return {
        "city": "AMS",
        "rows": count,
        "sites": len(ids),
        "paired_cells": dict(paired),
        "mismatch_examples": examples,
        "all_zero_volume_sites": len(zero_v),
        "all_zero_duration_sites": len(zero_d),
        "both_all_zero_sites": len(zero_v & zero_d),
        "all_zero_volume_but_positive_static_volume": sum(static_v[s] > 0 for s in zero_v),
        "all_zero_volume_but_positive_static_duration": sum(static_d[s] > 0 for s in zero_v),
        "all_zero_volume_but_positive_member_metadata": sum(
            any(
                finite_nonnegative(m["total_volume"]) > 0
                or finite_nonnegative(m["total_duration"]) > 0
                for m in members[s]
            )
            for s in zero_v
        ),
        "all_zero_volume_member_chargers": sum(len(members[s]) for s in zero_v),
        "member_count_mismatches": sum(
            len(members[s]) != int(sites[s]["charger_num"]) for s in ids
        ),
        "static_site_vs_member_volume_mismatches": sum(
            not math.isclose(
                static_v[s],
                math.fsum(finite_nonnegative(m["total_volume"]) for m in members[s]),
                rel_tol=1e-9,
                abs_tol=1e-6,
            )
            for s in ids
        ),
        "hourly_vs_static_volume_mismatches": sum(
            not math.isclose(total_v[s], static_v[s], rel_tol=1e-9, abs_tol=1e-6) for s in ids
        ),
        "hourly_vs_static_duration_mismatches": sum(
            not math.isclose(total_d[s], static_d[s], rel_tol=1e-9, abs_tol=1e-6) for s in ids
        ),
        "hourly_volume_sum": math.fsum(total_v.values()),
        "static_volume_sum": math.fsum(static_v.values()),
        "hourly_duration_sum": math.fsum(total_d.values()),
        "static_duration_sum": math.fsum(static_d.values()),
        "comparison_tolerance": {"relative": 1e-9, "absolute": 1e-6},
        "acceptance": "Descriptive evidence only; no exclusions or validity masks",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    spec = next(a for a in load_catalog() if a.source_id == "charged-hourly")
    output, storage = args.output.resolve(), args.storage_root.resolve()
    archive_path = storage / spec.relative_path
    if output.is_relative_to(storage / "data/raw"):
        parser.error("Output must not be inside raw storage")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Reserve a new evidence file before expensive work; never overwrite a run.
        with output.open("x", encoding="utf-8") as stream:
            start = time.perf_counter()
            result = {
                "run_id": output.stem,
                "scope": "Issue 17 Step 2 AMS semantics; read-only",
                "started_at_utc": datetime.now(timezone.utc).isoformat(),
                "code_commit": subprocess.check_output(
                    ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
                ).strip(),
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "python": platform.python_version(),
                "platform": platform.platform(),
                "status": "running",
                "archive": {"sha256": spec.sha256, "size_bytes": spec.size_bytes},
            }
            try:
                passed, message = verify_archive(spec, storage)
                if not passed:
                    raise ValueError(f"Archive verification failed: {message}")
                with ZipFile(archive_path) as archive:
                    result["ams"] = audit_ams(archive)
                result["status"] = "analysis_complete; QC not adjudicated"
            except (OSError, ValueError, KeyError, BadZipFile, csv.Error) as error:
                result.update(status="failed", error=str(error))
                raise
            finally:
                result["elapsed_seconds"] = time.perf_counter() - start
                json.dump(result, stream, indent=2, allow_nan=False)
                stream.write("\n")
        return 0
    except (OSError, ValueError, KeyError, BadZipFile, csv.Error) as error:
        print(f"CHARGED semantics audit failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
