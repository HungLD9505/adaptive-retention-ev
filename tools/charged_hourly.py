"""Adapt standard CHARGED hourly energy without filling labels or selecting sites."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import re
import subprocess
import sys
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from itertools import zip_longest
from pathlib import Path
from typing import Iterator
from zipfile import BadZipFile, ZipFile

from tools.sources import ROOT, load_catalog, verify_archive

CITIES = ("AMS", "JHB", "LOA", "MEL", "SPO", "SZH")
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
INFO_HEADER = [
    "city",
    "country",
    "abbreviation",
    "total_chargers",
    "total_sites",
    "DBSCAN_eps",
    "total_duration",
    "total_volume",
    "avg_power",
]
BROKEN_INFO_HEADER = INFO_HEADER[:4] + ["total_siteBSCAN_eps"] + INFO_HEADER[6:]


@contextmanager
def reader(archive: ZipFile, name: str) -> Iterator:
    with archive.open(name) as binary:
        with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as stream:
            yield csv.reader(stream)


def table(archive: ZipFile, name: str) -> tuple[list[str], list[list[str]]]:
    with reader(archive, name) as data:
        header = next(data)
        values = list(data)
    return header, values


def metadata(archive: ZipFile, city: str) -> tuple[list[str], dict]:
    """Validate IDs and explicitly map the known metadata-header defect in memory."""
    sh, sr = table(archive, f"{city}/sites.csv")
    ch, cr = table(archive, f"{city}/chargers.csv")
    for header, records in ((sh, sr), (ch, cr)):
        if len(set(header)) != len(header) or any(len(r) != len(header) for r in records):
            raise ValueError(f"{city}: duplicate metadata header or ragged row")
    sid = "site_id" if "site_id" in sh else "site"
    member = "site_id" if "site_id" in ch else "site"
    sites = [r[sh.index(sid)] for r in sr]
    chargers = [r[ch.index("charger_id")] for r in cr]
    if not sites or any(not s.strip() for s in sites + chargers):
        raise ValueError(f"{city}: missing metadata identifiers")
    if len(set(sites)) != len(sites) or len(set(chargers)) != len(chargers):
        raise ValueError(f"{city}: duplicate metadata identifiers")
    counts = Counter(r[ch.index(member)] for r in cr)
    if set(counts) - set(sites):
        raise ValueError(f"{city}: unknown charger member site")
    ih, ir = table(archive, f"{city}/info.csv")
    if len(ir) != 1 or len(ir[0]) != 9 or ih not in (INFO_HEADER, BROKEN_INFO_HEADER):
        raise ValueError(f"{city}: unrecognized info.csv schema; do not guess mapping")
    info = dict(zip(INFO_HEADER, ir[0]))
    if (
        info["abbreviation"] != city
        or int(info["total_sites"]) != len(sites)
        or int(info["total_chargers"]) != len(chargers)
    ):
        raise ValueError(f"{city}: info.csv counts/code do not match actual metadata")
    eps = float(info["DBSCAN_eps"])
    if not math.isfinite(eps) or eps <= 0:
        raise ValueError(f"{city}: invalid mapped DBSCAN_eps")
    return sites, {
        "site_count": len(sites),
        "charger_count": len(chargers),
        "site_id_source_field": sid,
        "charger_membership_source_field": member,
        "info_header_original": ih,
        "info_header_effective": INFO_HEADER,
        "info_header_override": ih == BROKEN_INFO_HEADER,
        "override_validation": "Recognized exact header; 9 values; city/count/radius checks",
        "member_count_mismatches": sum(
            int(r[sh.index("charger_num")]) != counts[r[sh.index(sid)]] for r in sr
        ),
    }


def numeric(value: str) -> tuple[bool, float | None]:
    try:
        number = float(value)
    except ValueError:
        return False, None
    return math.isfinite(number) and number >= 0, number


def parse_hour(value: str) -> datetime:
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is not None or stamp.minute or stamp.second or stamp.microsecond:
        raise ValueError(f"Expected whole-hour offset-free local label: {value!r}")
    return stamp


def adapt_city(
    archive: ZipFile, city: str, output: Path, start: datetime, end: datetime, label: str
) -> dict:
    """Write all metadata sites; retain source zeros and blank invalid target values."""
    sites, qc = metadata(archive, city)
    output.mkdir()
    stats: Counter = Counter()
    examples: dict[str, list] = {}
    zeros: Counter = Counter()
    valid_by_site: Counter = Counter()
    shift = timedelta(hours=1) if label == "end" else timedelta(0)
    expected = int((end - start).total_seconds() // 3600)
    names = [f"{city}/{n}.csv" for n in ("sites", "chargers", "info", "volume", "duration")]
    qc["source_members"] = [
        {"name": n, "size_bytes": archive.getinfo(n).file_size, "crc32": archive.getinfo(n).CRC}
        for n in names
    ]
    hourly = output / "hourly.csv"
    with (
        reader(archive, f"{city}/volume.csv") as vr,
        reader(archive, f"{city}/duration.csv") as dr,
        hourly.open("x", newline="", encoding="utf-8") as stream,
    ):
        vh, dh = next(vr), next(dr)
        if (
            len(set(vh[1:])) != len(vh) - 1
            or set(vh[1:]) != set(sites)
            or len(set(dh[1:])) != len(dh) - 1
            or set(dh[1:]) != set(sites)
        ):
            raise ValueError(f"{city}: matrix site IDs do not match metadata")
        dcolumns = {s: i for i, s in enumerate(dh)}
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        cursor = start
        previous = None

        def emit(stamp: datetime, volume: list[str] | None, duration: list[str] | None) -> None:
            for index, site in enumerate(vh[1:], 1):
                token = volume[index].strip() if volume else ""
                valid, energy = numeric(token)
                flag = "" if valid else "invalid_target_value" if volume else "missing_hour"
                writer.writerow(
                    (
                        "charged",
                        city,
                        site,
                        stamp.isoformat(),
                        token if valid else "",
                        int(valid),
                        int(valid),
                        1,
                        flag,
                    )
                )
                stats["rows"] += 1
                stats["valid_energy_rows"] += valid
                stats["invalid_energy_rows"] += not valid
                stats["zero_energy_rows"] += valid and energy == 0
                if valid:
                    valid_by_site[site] += 1
                    zeros[site] += energy == 0
                if duration is not None:
                    dvalid, hours = numeric(duration[dcolumns[site]])
                    diagnostic = (
                        "invalid_duration"
                        if not dvalid
                        else (
                            "positive_volume_zero_duration"
                            if valid and energy > 0 and hours == 0
                            else "zero_volume_positive_duration"
                            if valid and energy == 0 and hours > 0
                            else ""
                        )
                    )
                    if diagnostic:
                        stats[diagnostic] += 1
                        sample = examples.setdefault(diagnostic, [])
                        if len(sample) < 3:
                            sample.append({"entity_id": site, "timestamp": stamp.isoformat()})

        for v, d in zip_longest(vr, dr):
            if v is None or d is None or len(v) != len(vh) or len(d) != len(dh) or v[0] != d[0]:
                raise ValueError(f"{city}: matrix lengths/row widths/clocks differ")
            stamp = parse_hour(v[0]) - shift
            if previous is not None and stamp <= previous:
                raise ValueError(f"{city}: duplicate or out-of-order timestamp")
            previous = stamp
            stats["source_hour_rows"] += 1
            if not start <= stamp < end:
                stats["source_hours_outside_window"] += 1
                continue
            while cursor < stamp:
                emit(cursor, None, None)
                stats["missing_hour_bins"] += 1
                cursor += timedelta(hours=1)
            emit(stamp, v, d)
            cursor = stamp + timedelta(hours=1)
        while cursor < end:
            emit(cursor, None, None)
            stats["missing_hour_bins"] += 1
            cursor += timedelta(hours=1)
    digest = hashlib.sha256()
    with hourly.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    qc.update(
        city=city,
        counts=dict(stats),
        diagnostics_examples=examples,
        expected_hours_per_site=expected,
        expected_output_rows=len(sites) * expected,
        all_zero_volume_sites=sum(
            valid_by_site[s] == expected and zeros[s] == expected for s in sites
        ),
        output={
            "path": f"{city}/hourly.csv",
            "sha256": digest.hexdigest(),
            "size_bytes": hourly.stat().st_size,
        },
        analysis_group="shenzhen_later_period" if city == "SZH" else "other_geographies",
        readiness={
            "file_valid": "Per-row energy checks only",
            "forecasting_eligible": "pending #18",
            "strict_online_ready": "not_established",
        },
    )
    if stats["rows"] != qc["expected_output_rows"]:
        raise ValueError(f"{city}: incomplete output row count")
    (output / "qc.json").write_text(json.dumps(qc, indent=2) + "\n", encoding="utf-8")
    return qc


def run(storage: Path, output: Path, start: datetime, end: datetime, label: str) -> dict:
    storage, output = storage.resolve(), output.resolve()
    if output.is_relative_to(storage / "data/raw") or (storage / "data/raw").is_relative_to(output):
        raise ValueError("Output must be separate from raw storage")
    if (
        start.tzinfo is not None
        or end.tzinfo is not None
        or start.minute
        or start.second
        or start.microsecond
        or end.minute
        or end.second
        or end.microsecond
        or end <= start
    ):
        raise ValueError("Expected positive whole-hour naive window")
    if label not in ("start", "end"):
        raise ValueError("Expected explicit start/end interval label")
    output.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter()
    manifest = {
        "run_id": output.name,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "contract_profile": "charged-hourly-v1-local-naive",
        "config": {
            "start_inclusive": start.isoformat(),
            "end_exclusive": end.isoformat(),
            "interval_label_assumption": label,
            "clock_policy": "publisher-local-naive",
            "cities": CITIES,
        },
        "code_commit": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "worktree_status": subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"], text=True
        ).strip(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "research_scope": "UrbanEV primary; all six CHARGED cities supplementary; SZH analyzed separately; no pooling or exclusions",
        "original_observation_status": "unknown",
        "strict_online_ready": False,
        "research_acceptance": "limited scope accepted by user; implementation pending peer review",
        "cities": [],
    }
    try:
        spec = next(a for a in load_catalog() if a.source_id == "charged-hourly")
        passed, message = verify_archive(spec, storage)
        if not passed:
            raise ValueError(f"Archive verification failed: {message}")
        manifest["source_archive"] = {
            "source_id": spec.source_id,
            "path": spec.relative_path,
            "sha256": spec.sha256,
            "size_bytes": spec.size_bytes,
            "publisher_checksum": spec.publisher_checksum,
            "verification": message,
        }
        with ZipFile(storage / spec.relative_path) as archive:
            for city in CITIES:
                manifest["cities"].append(
                    adapt_city(archive, city, output / city, start, end, label)
                )
                print(f"Adapted {city}", flush=True)
        manifest["status"] = "technical_success; input acceptance pending peer review"
    except (OSError, ValueError, KeyError, StopIteration, BadZipFile, csv.Error) as error:
        manifest.update(status="failed", error=str(error))
        raise
    finally:
        manifest["elapsed_seconds"] = time.perf_counter() - began
        (output / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", type=Path, default=ROOT)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--interval-label", choices=("start", "end"), required=True)
    parser.add_argument("--clock-policy", choices=("publisher-local-naive",), required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", args.run_id):
        parser.error("Unsafe run ID")
    try:
        run(
            args.storage_root,
            args.output_root / args.run_id,
            parse_hour(args.start),
            parse_hour(args.end),
            args.interval_label,
        )
        return 0
    except (OSError, ValueError, KeyError, StopIteration, BadZipFile, csv.Error) as error:
        print(f"CHARGED adapter failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
