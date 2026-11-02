"""Explain zero-scored Development cells from the pinned input ZIP, without Final data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

from ev_inputs.windows import LabelRecord, ready_labels

ROOT = Path(__file__).resolve().parents[1]
ZIP_SHA256 = "2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7"
ZERO_CSV_SHA256 = "653f4a2ba1e3217e3a775c36849093f6be9b03d28550f333519d6c093b423ff1"
MERGED_SHA256 = "82d9342c62baef0da9e6f70baf548fb9e97e653792305adbb0fb85c872a1173d"
LEDGER_SHA256 = "bf1117c1d5fc0a902411cb6d850dca51e77802997c32880295ede20d8ac83004"
EXPECTED_CELLS = {
    7: {"1050", "1200", "2447"},
    14: {"1025", "1987", "2613", "2644"},
    28: {"1188", "1251", "1408", "1987"},
}
ZIP_PREFIX = "data/inputs/issue18-input-handoff-v1-20261019"


def sha256_file(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def sha256_member(archive: ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with archive.open(name) as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_repo_path(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"Path outside repository: {path}")
    return resolved


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def label_record(row: dict, identity: list[str]) -> LabelRecord:
    expected = {
        "identity",
        "origin",
        "clock_mode",
        "timestamps",
        "energy_kwh",
        "file_valid",
        "available_at",
    }
    if set(row) != expected or row["identity"] != identity:
        raise ValueError("Selected label identity/schema differs")
    return LabelRecord(
        tuple(identity),
        datetime.fromisoformat(row["origin"]),
        row["clock_mode"],
        tuple(datetime.fromisoformat(value) for value in row["timestamps"]),
        tuple(row["energy_kwh"]),
        tuple(row["file_valid"]),
        tuple(
            None if value is None else datetime.fromisoformat(value)
            for value in row["available_at"]
        ),
    )


def classify_label(record: LabelRecord, replay_end: datetime) -> dict[str, int | str]:
    """Separate frozen-input incompleteness from complete but late labels."""
    if any(
        len(values) != 24 for values in (record.file_valid, record.energy_kwh, record.available_at)
    ):
        raise ValueError("Label horizon is not 24 aligned bins")
    invalid = sum(not value for value in record.file_valid)
    missing_energy = sum(value is None for value in record.energy_kwh)
    missing_availability = sum(value is None for value in record.available_at)
    after_end = sum(value is not None and value > replay_end for value in record.available_at)
    ready = ready_labels(record, as_of=replay_end) is not None
    if ready:
        kind = "complete_by_replay_end"
    elif invalid or missing_energy or missing_availability:
        kind = "incomplete_frozen_input"
    elif after_end:
        kind = "complete_but_late"
    else:
        raise ValueError("Unexplained unready label record")
    return {
        "classification": kind,
        "invalid_file_bins": invalid,
        "missing_energy_bins": missing_energy,
        "missing_availability_bins": missing_availability,
        "available_after_replay_end_bins": after_end,
    }


def selected_rows(
    archive: ZipFile, name: str, entity_ids: set[str]
) -> dict[str, list[tuple[dict, str]]]:
    rows: dict[str, list[tuple[dict, str]]] = defaultdict(list)
    with archive.open(name) as source:
        for line in source:
            row = json.loads(line)
            identity = row.get("identity")
            if (
                not isinstance(identity, list)
                or len(identity) != 3
                or identity[2] not in entity_ids
            ):
                continue
            if identity[:2] != ["urbanev", "SZH"]:
                raise ValueError("Selected row has unexpected dataset/city")
            rows[identity[2]].append((row, hashlib.sha256(line).hexdigest()))
    if set(rows) != entity_ids:
        raise ValueError(f"Selected entity set differs in {name}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-zip", required=True, type=Path)
    parser.add_argument("--zero-csv", required=True, type=Path)
    parser.add_argument("--merged", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    paths = {
        name: require_repo_path(getattr(args, name))
        for name in ("input_zip", "zero_csv", "merged", "ledger", "output_dir")
    }
    if paths["output_dir"].exists():
        raise FileExistsError(paths["output_dir"])
    for name, expected in (
        ("input_zip", ZIP_SHA256),
        ("zero_csv", ZERO_CSV_SHA256),
        ("merged", MERGED_SHA256),
        ("ledger", LEDGER_SHA256),
    ):
        actual = sha256_file(paths[name])
        if actual != expected:
            raise ValueError(f"{name} SHA-256 differs: {actual}")

    zero_rows = read_csv(paths["zero_csv"])
    ledger_rows = read_csv(paths["ledger"])
    merged_runs = json.loads(paths["merged"].read_text(encoding="utf-8"))["runs"]
    if len(zero_rows) != 407 or len(ledger_rows) != 782 or len(merged_runs) != 851:
        raise ValueError("Development row count differs")
    zero_by_id = {row["job_id"]: row for row in zero_rows}
    merged_by_id = {row["job_id"]: row for row in merged_runs}
    ledger_by_id = {row["job_id"]: row for row in ledger_rows}
    if len(zero_by_id) != 407 or len(merged_by_id) != 851 or len(ledger_by_id) != 782:
        raise ValueError("Duplicate Development job ID")
    groups: dict[tuple[int, str], list[dict[str, str]]] = defaultdict(list)
    for row in zero_rows:
        if int(row["scored"]) != 0 or int(row["unscored_created"]) != int(row["created"]):
            raise ValueError("Zero-scored row semantics differ")
        groups[(int(row["budget_days"]), row["entity_id"])].append(row)
    if {
        budget: {entity for b, entity in groups if b == budget} for budget in EXPECTED_CELLS
    } != EXPECTED_CELLS:
        raise ValueError("Zero-scored station/budget cells differ")
    if any(len(rows) != 37 for rows in groups.values()):
        raise ValueError("Zero-scored run count per cell differs")

    origin_rows: list[dict[str, str | int]] = []
    cell_rows: list[dict[str, str | int]] = []
    member_hashes: dict[str, str] = {}
    with ZipFile(paths["input_zip"]) as archive:
        for budget, entity_ids in EXPECTED_CELLS.items():
            base = f"{ZIP_PREFIX}/urbanev-SZH-{budget}d/"
            members = {kind: base + f"{kind}.jsonl" for kind in ("entities", "schedule", "labels")}
            manifest_name = base + "manifest.json"
            for name in (*members.values(), manifest_name):
                member_hashes[name] = sha256_member(archive, name)
            input_manifest_sha = member_hashes[manifest_name]
            manifest = json.loads(archive.read(manifest_name))
            if (
                manifest.get("run_id") != f"urbanev-SZH-{budget}d"
                or manifest.get("config", {}).get("availability_delay_hours") != 0
            ):
                raise ValueError("Input run/availability policy differs")
            ledger_budget = [row for row in ledger_rows if int(row["budget_days"]) == budget]
            if not ledger_budget or {row["input_manifest_sha256"] for row in ledger_budget} != {
                input_manifest_sha
            }:
                raise ValueError("ZIP input manifest does not match v5 ledger")
            entities = selected_rows(archive, members["entities"], entity_ids)
            schedules = selected_rows(archive, members["schedule"], entity_ids)
            labels = selected_rows(archive, members["labels"], entity_ids)
            for entity_id in sorted(entity_ids):
                identity = ["urbanev", "SZH", entity_id]
                if len(entities[entity_id]) != 1:
                    raise ValueError("Duplicate entity coverage row")
                entity = entities[entity_id][0][0]
                if len(schedules[entity_id]) != 90 or len(labels[entity_id]) != 90:
                    raise ValueError("Expected exactly 90 schedule and label source rows")
                schedule = {row["origin"]: row for row, _ in schedules[entity_id]}
                label_map = {row["origin"]: (row, line_sha) for row, line_sha in labels[entity_id]}
                if len(schedule) != 90 or len(label_map) != 90 or set(schedule) != set(label_map):
                    raise ValueError("Expected 90 distinct aligned origins")
                if {row["status"] for row in schedule.values()} - {
                    "created",
                    "skipped_all_missing_history",
                }:
                    raise ValueError("Unexpected schedule status")
                replay_end = max(datetime.fromisoformat(origin) for origin in schedule) + timedelta(
                    days=1
                )
                created = [origin for origin, row in schedule.items() if row["status"] == "created"]
                if len(created) != int(entity["scheduled_forecasts"]):
                    raise ValueError("Entity schedule count differs")
                if len(schedule) - len(created) != int(entity["skipped_all_missing_history"]):
                    raise ValueError("Entity skipped-history count differs")
                runs = groups[(budget, entity_id)]
                if any(int(row["created"]) != len(created) for row in runs):
                    raise ValueError("Saved 407-run forecast count differs from input schedule")
                for run in runs:
                    merged = merged_by_id[run["job_id"]]
                    if merged["input_manifest_sha256"] != input_manifest_sha or merged["coverage"][
                        "created"
                    ] != len(created):
                        raise ValueError("Merged zero-scored run input/count binding differs")
                    if (
                        run["job_id"] in ledger_by_id
                        and ledger_by_id[run["job_id"]]["input_manifest_sha256"]
                        != input_manifest_sha
                    ):
                        raise ValueError("New job ledger input binding differs")
                new_runs = sum(run["job_id"] in ledger_by_id for run in runs)
                if new_runs != 34:
                    raise ValueError("Expected 34 new jobs and 3 historical Main anchors per cell")
                reasons: Counter[str] = Counter()
                bins: Counter[str] = Counter()
                for origin in sorted(created):
                    label, line_sha = label_map[origin]
                    classified = classify_label(label_record(label, identity), replay_end)
                    if any(
                        (not valid) != (energy is None)
                        for valid, energy in zip(
                            label["file_valid"], label["energy_kwh"], strict=True
                        )
                    ):
                        raise ValueError("Invalid-file and missing-energy bin positions differ")
                    reasons[str(classified["classification"])] += 1
                    for key in (
                        "invalid_file_bins",
                        "missing_energy_bins",
                        "missing_availability_bins",
                        "available_after_replay_end_bins",
                    ):
                        bins[key] += int(classified[key])
                    origin_rows.append(
                        {
                            "budget_days": budget,
                            "entity_id": entity_id,
                            "origin": origin,
                            "input_manifest_sha256": input_manifest_sha,
                            "label_line_sha256": line_sha,
                            **classified,
                        }
                    )
                cell_rows.append(
                    {
                        "budget_days": budget,
                        "entity_id": entity_id,
                        "new_jobs": new_runs,
                        "historical_main_runs": len(runs) - new_runs,
                        "requested_origins": len(schedule),
                        "created_origins": len(created),
                        "skipped_origins": len(schedule) - len(created),
                        "incomplete_frozen_input_origins": reasons["incomplete_frozen_input"],
                        "complete_but_late_origins": reasons["complete_but_late"],
                        "complete_by_replay_end_origins": reasons["complete_by_replay_end"],
                        "invalid_file_bins": bins["invalid_file_bins"],
                        "missing_energy_bins": bins["missing_energy_bins"],
                        "missing_availability_bins": bins["missing_availability_bins"],
                        "available_after_replay_end_bins": bins["available_after_replay_end_bins"],
                        "initialization": entity["initialization"],
                        "initial_trainable": entity["initial_trainable"],
                        "input_manifest_sha256": input_manifest_sha,
                    }
                )

    if (
        len(origin_rows) != 550
        or sum(int(row["complete_by_replay_end_origins"]) for row in cell_rows) != 0
    ):
        raise ValueError("Expected zero-score origin accounting differs")
    if sum(int(row["incomplete_frozen_input_origins"]) for row in cell_rows) != 550:
        raise ValueError("Some created origins lack incomplete frozen-input evidence")
    if sum(int(row["created_origins"]) * 37 for row in cell_rows) != 20_350:
        raise ValueError("Repeated forecast accounting differs")

    output = paths["output_dir"]
    output.mkdir(parents=True)
    for name, rows in (("origin_labels.csv", origin_rows), ("cells.csv", cell_rows)):
        with (output / name).open("w", encoding="utf-8", newline="") as sink:
            writer = csv.DictWriter(sink, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    summary = {
        "schema": "hung-zero-score-label-audit-v1",
        "scope": "development_only",
        "input_zip_sha256": ZIP_SHA256,
        "zero_scored_csv_sha256": ZERO_CSV_SHA256,
        "merged_851_sha256": MERGED_SHA256,
        "ledger_v5_sha256": LEDGER_SHA256,
        "input_member_sha256": member_hashes,
        "zero_scored_runs": 407,
        "new_jobs": 374,
        "historical_main_runs": 33,
        "station_budget_cells": 11,
        "created_unique_origins": 550,
        "repeated_unscored_forecasts": 20_350,
        "incomplete_frozen_input_origins": 550,
        "complete_but_late_origins": 0,
        "complete_by_replay_end_origins": 0,
        "invalid_file_bins": sum(int(row["invalid_file_bins"]) for row in cell_rows),
        "missing_energy_bins": sum(int(row["missing_energy_bins"]) for row in cell_rows),
        "limits": [
            "This establishes incompleteness in the pinned Development input snapshot, not why upstream raw measurements are missing.",
            "An invalid/missing hourly bin prevents a 24-hour scored day under the frozen protocol; future data repair would need a new version, not retroactive filling.",
        ],
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "zero_scored_runs",
                    "created_unique_origins",
                    "incomplete_frozen_input_origins",
                    "complete_but_late_origins",
                    "invalid_file_bins",
                )
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
