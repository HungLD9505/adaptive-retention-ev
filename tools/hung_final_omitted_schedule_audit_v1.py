"""Verify frozen Final-role daily schedule coverage without reading outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
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

DISPOSITION = ROOT / "docs/reports/hung-final-omitted-disposition-20261030-v1.json"
DISPOSITION_SHA = "e129bcc2601c8f7c4dd209dc302f3dd0d4c2c5c61a58863b5e5e28e227f4fd76"
STATUSES = {"created", "skipped_all_missing_history", "skipped_undefined_scale"}


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_entity_schedule(rows: list[dict], entity: dict, expected_origins: set[str]) -> Counter:
    """Require one causally scheduled status per declared daily origin."""
    identity = entity["identity"]
    if len(rows) != entity["requested_forecasts"] or len(rows) != len(expected_origins):
        raise ValueError(f"Requested schedule count differs: {identity}")
    origins = [row["origin"] for row in rows]
    if len(set(origins)) != len(origins) or set(origins) != expected_origins:
        raise ValueError(f"Scheduled origin set differs: {identity}")
    if any(row["identity"] != identity or row["role"] != "final" for row in rows):
        raise ValueError(f"Scheduled identity/role differs: {identity}")
    counts = Counter(row["status"] for row in rows)
    if set(counts) - STATUSES:
        raise ValueError(f"Unexpected scheduled status: {identity}")
    expected = Counter(
        {
            "created": entity["scheduled_forecasts"],
            "skipped_all_missing_history": entity["skipped_all_missing_history"],
            "skipped_undefined_scale": entity["skipped_undefined_scale"],
        }
    )
    if counts != +expected:
        raise ValueError(f"Scheduled coverage differs from entity inventory: {identity}")
    if entity["status"] == "undefined_scale" and counts != Counter(
        {"skipped_undefined_scale": len(rows)}
    ):
        raise ValueError(f"Undefined scale has a nonblocked origin: {identity}")
    if entity["status"] == "ready" and counts["skipped_undefined_scale"]:
        raise ValueError(f"Ready entity has undefined-scale skip: {identity}")
    return counts


def audit() -> dict:
    if _sha(DISPOSITION) != DISPOSITION_SHA:
        raise ValueError("Pinned omitted-ID disposition changed")
    packet = json.loads(DISPOSITION.read_text(encoding="utf-8"))
    jobset, entities_by_budget, manifest_shas = read_frozen_inputs(LOCK, JOBSET, INPUTS)
    selected = {str(job["entity_id"]) for job in jobset["jobs"]}
    records = {row["entity_id"]: row for row in packet["records"]}
    if len(records) != 370 or len(selected) != 3 or selected & records.keys():
        raise ValueError("Omitted-ID partition differs")
    budgets = []
    with ZipFile(INPUTS) as archive:
        for budget in BUDGETS:
            base = f"{PREFIX}/urbanev-SZH-{budget}d/"
            manifest_bytes = archive.read(base + "manifest.json")
            if hashlib.sha256(manifest_bytes).hexdigest() != manifest_shas[budget]:
                raise ValueError("Frozen input manifest differs")
            manifest = json.loads(manifest_bytes)
            start = datetime.fromisoformat(manifest["config"]["deployment"])
            stop = datetime.fromisoformat(manifest["config"]["replay_stop"])
            expected_origins = set()
            day = start
            while day < stop:
                expected_origins.add(day.isoformat())
                day += timedelta(days=1)
            member = base + "schedule.jsonl"
            data = archive.read(member)
            expected_file = manifest["files"]["schedule.jsonl"]
            if (
                len(data) != expected_file["size_bytes"]
                or hashlib.sha256(data).hexdigest() != expected_file["sha256"]
            ):
                raise ValueError("Frozen schedule bytes/SHA differ")
            grouped: dict[str, list[dict]] = defaultdict(list)
            for line in data.splitlines():
                row = json.loads(line)
                if row["role"] != "final":
                    continue
                entity_id = str(row["identity"][2])
                if entity_id not in entities_by_budget[budget]:
                    raise ValueError(f"Unknown Final scheduled entity: {entity_id}")
                if row["input_run_id"] != manifest["run_id"]:
                    raise ValueError(f"Scheduled input run differs: {entity_id}")
                grouped[entity_id].append(row)
            if set(grouped) != set(entities_by_budget[budget]):
                raise ValueError("Final-role scheduled ID set differs")
            totals: Counter[str] = Counter()
            strata: dict[str, Counter] = defaultdict(Counter)
            for entity_id, entity in entities_by_budget[budget].items():
                counts = validate_entity_schedule(grouped[entity_id], entity, expected_origins)
                totals.update(counts)
                if entity_id in records:
                    packet_budget = next(
                        row for row in records[entity_id]["budgets"] if row["budget_days"] == budget
                    )
                    if (
                        packet_budget["status"] != entity["status"]
                        or packet_budget["scheduled_forecasts"] != entity["scheduled_forecasts"]
                    ):
                        raise ValueError("Omitted-ID disposition differs from schedule entity")
                    strata[records[entity_id]["disposition"]].update(counts)
            budgets.append(
                {
                    "budget_days": budget,
                    "input_manifest_sha256": manifest_shas[budget],
                    "schedule_member_bytes": len(data),
                    "schedule_member_sha256": expected_file["sha256"],
                    "final_role_entities": len(grouped),
                    "daily_origins_per_entity": len(expected_origins),
                    "all_final_status_counts": dict(sorted(totals.items())),
                    "omitted_status_counts_by_disposition": {
                        key: dict(sorted(value.items())) for key, value in sorted(strata.items())
                    },
                    "invalid_or_missing_entity_schedules": 0,
                }
            )
    return {
        "schema": "hung-final-omitted-schedule-audit-v1",
        "scope": "frozen Final-role schedule coverage; no held-out label or score read",
        "lock_sha256": packet["lock_sha256"],
        "input_zip_sha256": packet["input_zip_sha256"],
        "disposition_sha256": DISPOSITION_SHA,
        "budgets": budgets,
        "decision": "SCHEDULE_COVERAGE_VERIFIED_NOT_METHOD_EXECUTION_OR_EXTENSION_LOCK",
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
