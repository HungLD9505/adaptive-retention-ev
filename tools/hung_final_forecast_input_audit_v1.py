"""Verify frozen Final forecast inputs against their daily schedule."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

from tools.hung_final_scope_gap import (
    BUDGETS,
    INPUTS,
    JOBSET,
    LOCK,
    PREFIX,
    ROOT,
    read_frozen_inputs,
)

SCHEDULE_AUDIT = ROOT / "docs/reports/hung-final-omitted-schedule-audit-20261030-v1.json"
SCHEDULE_AUDIT_SHA = "b4211712fc9c25d4343b076c29d1489a8d7d45db54a91011c9fe310daf9bed4e"
DISPOSITION = ROOT / "docs/reports/hung-final-omitted-disposition-20261030-v1.json"
DISPOSITION_SHA = "e129bcc2601c8f7c4dd209dc302f3dd0d4c2c5c61a58863b5e5e28e227f4fd76"
FORECAST_KEYS = {
    "role",
    "identity",
    "origin",
    "input_run_id",
    "schema_id",
    "clock_mode",
    "scale_id",
    "energy_scale",
    "history_labels",
    "future_labels",
    "x_hist",
    "c_future",
}


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_forecast(row: dict, entity: dict, *, run_id: str) -> tuple[str, str]:
    """Check one Final-role forecast input without opening outcome labels."""
    identity = entity["identity"]
    if (
        set(row) != FORECAST_KEYS
        or row.get("role") != "final"
        or row.get("identity") != identity
        or row.get("input_run_id") != run_id
        or row.get("schema_id") != "ev-input-v1"
        or row.get("clock_mode") != "offset-aware-local"
        or entity["status"] != "ready"
        or row.get("scale_id") != entity["scale"]["fit_sha256"]
        or row.get("energy_scale") != entity["scale"]["energy_scale"]
        or not isinstance(row["energy_scale"], (int, float))
        or not math.isfinite(row["energy_scale"])
        or row["energy_scale"] <= 0
    ):
        raise ValueError(f"Final forecast binding differs: {identity}")
    origin = datetime.fromisoformat(row["origin"])
    if origin.utcoffset() != timedelta(hours=8) or (
        origin.hour,
        origin.minute,
        origin.second,
        origin.microsecond,
    ) != (0, 0, 0, 0):
        raise ValueError(f"Final forecast origin clock differs: {identity}")
    history = [datetime.fromisoformat(value) for value in row["history_labels"]]
    future = [datetime.fromisoformat(value) for value in row["future_labels"]]
    if (
        history != [origin - timedelta(hours=24 - index) for index in range(24)]
        or future != [origin + timedelta(hours=index) for index in range(24)]
        or len(row["x_hist"]) != 24
        or any(len(hour) != 7 for hour in row["x_hist"])
        or len(row["c_future"]) != 24
        or any(len(hour) != 5 for hour in row["c_future"])
    ):
        raise ValueError(f"Final forecast shape or hourly clock differs: {identity}")
    return str(identity[2]), row["origin"]


def _member_lines(archive: ZipFile, member: str, expected: dict):
    digest = hashlib.sha256()
    size = 0
    with archive.open(member) as stream:
        for line in stream:
            digest.update(line)
            size += len(line)
            yield line
    if size != expected["size_bytes"] or digest.hexdigest() != expected["sha256"]:
        raise ValueError(f"Frozen input member bytes/SHA differ: {member}")


def audit() -> dict:
    if _sha(SCHEDULE_AUDIT) != SCHEDULE_AUDIT_SHA or _sha(DISPOSITION) != DISPOSITION_SHA:
        raise ValueError("Pinned schedule or disposition evidence changed")
    schedule_evidence = json.loads(SCHEDULE_AUDIT.read_text(encoding="utf-8"))
    disposition = json.loads(DISPOSITION.read_text(encoding="utf-8"))
    jobset, entities_by_budget, manifest_shas = read_frozen_inputs(LOCK, JOBSET, INPUTS)
    selected = {str(job["entity_id"]) for job in jobset["jobs"]}
    omitted = {row["entity_id"] for row in disposition["records"]}
    if len(selected) != 3 or len(omitted) != 370 or selected & omitted:
        raise ValueError("Frozen Final-role cohort partition differs")
    budget_records = []
    with ZipFile(INPUTS) as archive:
        for budget in BUDGETS:
            base = f"{PREFIX}/urbanev-SZH-{budget}d/"
            manifest_bytes = archive.read(base + "manifest.json")
            if hashlib.sha256(manifest_bytes).hexdigest() != manifest_shas[budget]:
                raise ValueError("Frozen input manifest differs")
            manifest = json.loads(manifest_bytes)
            entities = entities_by_budget[budget]
            if set(entities) != selected | omitted:
                raise ValueError("Frozen Final-role ID set differs")
            created: set[tuple[str, str]] = set()
            scheduled_counts: Counter[str] = Counter()
            for line in _member_lines(
                archive,
                base + "schedule.jsonl",
                manifest["files"]["schedule.jsonl"],
            ):
                row = json.loads(line)
                if row["role"] != "final":
                    continue
                entity_id = str(row["identity"][2])
                if entity_id not in entities or row["input_run_id"] != manifest["run_id"]:
                    raise ValueError("Final scheduled identity or input run differs")
                scheduled_counts[row["status"]] += 1
                if row["status"] == "created":
                    key = entity_id, row["origin"]
                    if key in created:
                        raise ValueError("Duplicate created Final schedule origin")
                    created.add(key)
            forecast_keys: set[tuple[str, str]] = set()
            per_entity: Counter[str] = Counter()
            for line in _member_lines(
                archive,
                base + "forecasts.jsonl",
                manifest["files"]["forecasts.jsonl"],
            ):
                # The whole member is authenticated. Decode only Final-role rows.
                if b'"role": "final"' not in line:
                    continue
                row = json.loads(line)
                if row["role"] != "final":
                    raise ValueError("Final forecast role filter differs")
                entity_id = str(row["identity"][2])
                if entity_id not in entities:
                    raise ValueError("Unknown Final forecast identity")
                key = validate_forecast(row, entities[entity_id], run_id=manifest["run_id"])
                if key in forecast_keys:
                    raise ValueError("Duplicate Final forecast origin")
                forecast_keys.add(key)
                per_entity[entity_id] += 1
            if forecast_keys != created:
                raise ValueError("Final forecast inputs differ from created schedule origins")
            if any(
                per_entity[entity_id] != entity["scheduled_forecasts"]
                for entity_id, entity in entities.items()
            ):
                raise ValueError("Final forecast counts differ from entity inventory")
            previous = next(
                row for row in schedule_evidence["budgets"] if row["budget_days"] == budget
            )
            if dict(sorted(scheduled_counts.items())) != previous["all_final_status_counts"]:
                raise ValueError("Pinned schedule audit counts differ")
            key_bytes = "\n".join(
                f"{entity_id}|{origin}" for entity_id, origin in sorted(created)
            ).encode()
            budget_records.append(
                {
                    "budget_days": budget,
                    "manifest_sha256": manifest_shas[budget],
                    "schedule_member_sha256": manifest["files"]["schedule.jsonl"]["sha256"],
                    "forecast_member_bytes": manifest["files"]["forecasts.jsonl"]["size_bytes"],
                    "forecast_member_sha256": manifest["files"]["forecasts.jsonl"]["sha256"],
                    "final_created_and_forecast_inputs": len(created),
                    "omitted_forecast_inputs": sum(per_entity[entity_id] for entity_id in omitted),
                    "created_key_set_sha256": hashlib.sha256(key_bytes).hexdigest(),
                    "missing_or_extra_forecast_inputs": 0,
                    "duplicate_final_forecast_inputs": 0,
                    "invalid_final_forecast_shapes_or_bindings": 0,
                }
            )
    return {
        "schema": "hung-final-forecast-input-audit-v1",
        "scope": "frozen Final-role created schedule to forecast-input bijection; no held-out labels or scores",
        "lock_sha256": disposition["lock_sha256"],
        "input_zip_sha256": disposition["input_zip_sha256"],
        "schedule_audit_sha256": SCHEDULE_AUDIT_SHA,
        "disposition_sha256": DISPOSITION_SHA,
        "budgets": budget_records,
        "disposition": "FROZEN_FORECAST_INPUTS_VERIFIED_NOT_METHOD_EXECUTION_OR_EXTENSION_LOCK",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT.resolve()) or output.exists() or output.is_symlink():
        raise ValueError("Output must be a new repository path")
    result = audit()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"output": str(output), "sha256": _sha(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
