"""Check 69 Block7/Main origin tags against the frozen Development input ZIP."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta
from zipfile import ZipFile

from tools import hung_block7_manifest_pairs as pairs
from tools import hung_block7_origin_events as origins

INPUT_ZIP = pairs.ROOT / ".cache/kaggle-payload-v2/payload/inputs.zip"
INPUT_SHA256 = "2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7"
OUTPUT = pairs.ROOT / "docs/reports/evidence/hung-block7-input-eligibility-20261030-v1.json"


def label_is_available(row: dict) -> bool:
    """Require a complete finite horizon available by the next daily tick."""
    if not (len(row["file_valid"]) == len(row["energy_kwh"]) == len(row["available_at"]) == 24):
        raise ValueError("Label horizon is not 24 hours")
    if not all(row["file_valid"]):
        return False
    if not all(
        isinstance(value, (int, float)) and math.isfinite(value) for value in row["energy_kwh"]
    ):
        raise ValueError("Complete label has a nonfinite value")
    cutoff = datetime.fromisoformat(row["origin"]) + timedelta(days=1)
    return all(datetime.fromisoformat(value) <= cutoff for value in row["available_at"])


def read_selected_member(
    archive: ZipFile, name: str, spec: dict, entities: set[str]
) -> dict[str, list[dict]]:
    """Hash the entire ZIP member while retaining only the selected entities."""
    digest = hashlib.sha256()
    size = 0
    selected: dict[str, list[dict]] = {entity: [] for entity in entities}
    with archive.open(name) as stream:
        for line in stream:
            digest.update(line)
            size += len(line)
            row = json.loads(line)
            entity = row["identity"][2]
            if entity in selected:
                selected[entity].append(row)
    if size != spec["size_bytes"] or digest.hexdigest() != spec["sha256"]:
        raise ValueError(f"Changed input member: {name}")
    return selected


def origin_hash(values: list[str]) -> str:
    return hashlib.sha256((json.dumps(values, separators=(",", ":")) + "\n").encode()).hexdigest()


def audit() -> dict:
    if pairs.sha_file(INPUT_ZIP) != INPUT_SHA256:
        raise ValueError("Frozen Development input ZIP SHA mismatch")
    coverage_proof = json.loads(pairs.EVIDENCE.read_text(encoding="utf-8"))
    expected_coverage_sha = coverage_proof["audit"]["provenance"]["inputs"]["coverage"]["sha256"]
    if pairs.sha_file(pairs.DEFAULT_COVERAGE) != expected_coverage_sha:
        raise ValueError("Pinned Block7 coverage SHA mismatch")
    coverage = json.loads(pairs.DEFAULT_COVERAGE.read_text(encoding="utf-8"))
    paired = origins.compare(coverage, pairs.DEFAULT_MANIFEST_DIR)
    if len(paired) != 69 or any(not row["origin_event_tags_equal"] for row in paired):
        raise ValueError("The 69-pair manifest origin audit is incomplete")
    results = []
    member_pins = {}
    with ZipFile(INPUT_ZIP) as archive:
        for budget in (7, 14, 28):
            group = [row for row in paired if row["budget_days"] == budget]
            entities = {row["cell_id"].split("e", 1)[1] for row in group}
            prefix = f"data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-{budget}d"
            manifest_bytes = archive.read(f"{prefix}/manifest.json")
            manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
            input_manifest = json.loads(manifest_bytes)
            if input_manifest["run_id"] != f"urbanev-SZH-{budget}d":
                raise ValueError("Unexpected input run ID")
            by_kind = {}
            for kind in ("schedule", "forecasts", "labels"):
                filename = f"{kind}.jsonl"
                by_kind[kind] = read_selected_member(
                    archive, f"{prefix}/{filename}", input_manifest["files"][filename], entities
                )
            member_pins[str(budget)] = {
                "manifest_sha256": manifest_sha,
                "schedule_sha256": input_manifest["files"]["schedule.jsonl"]["sha256"],
                "forecasts_sha256": input_manifest["files"]["forecasts.jsonl"]["sha256"],
                "labels_sha256": input_manifest["files"]["labels.jsonl"]["sha256"],
            }
            for pair in group:
                entity = pair["cell_id"].split("e", 1)[1]
                schedule = by_kind["schedule"][entity]
                forecasts = by_kind["forecasts"][entity]
                labels = by_kind["labels"][entity]
                if len(schedule) != 90 or len(labels) != 90:
                    raise ValueError(f"Incomplete 90-origin input rows for {pair['cell_id']}")
                schedule_origins = [row["origin"] for row in schedule]
                if (
                    len(set(schedule_origins)) != 90
                    or [row["origin"] for row in labels] != schedule_origins
                ):
                    raise ValueError("Schedule and label origin order differs")
                created = [row["origin"] for row in schedule if row["status"] == "created"]
                skipped = [row["origin"] for row in schedule if row["status"] != "created"]
                if [row["origin"] for row in forecasts] != created:
                    raise ValueError("Created schedule lacks exact forecast input rows")
                available = {row["origin"] for row in labels if label_is_available(row)}
                scored = [origin for origin in created if origin in available]
                for role in ("historical", "main"):
                    run_id = pair[f"{role}_run_id"]
                    manifest_spec = (
                        coverage["external_complete_jobs"][run_id]["run_manifest"]
                        if role == "historical"
                        else coverage["reused_jobs"][run_id]
                    )
                    run = pairs.checked_manifest(
                        manifest_spec, pairs.DEFAULT_MANIFEST_DIR / f"{run_id}.json"
                    )
                    binding = run["input_binding"]
                    if (
                        binding["input_manifest_sha256"] != manifest_sha
                        or binding["input_run_id"] != input_manifest["run_id"]
                        or binding["entity_id"] != entity
                        or binding["history_days"] != budget
                    ):
                        raise ValueError(f"Input binding mismatch: {run_id}")
                    events = origins.event_schedule(run)
                    for kind, expected in (
                        ("forecast", created),
                        ("skip", skipped),
                        ("score", scored),
                        ("update", scored),
                    ):
                        if events[kind] != expected:
                            raise ValueError(f"{run_id} {kind} origins differ from frozen input")
                results.append(
                    {
                        "cell_id": pair["cell_id"],
                        "budget_days": budget,
                        "seed": pair["seed"],
                        "entity_id": entity,
                        "input_manifest_sha256": manifest_sha,
                        "requested_origins": 90,
                        "created_origins": len(created),
                        "skipped_origins": len(skipped),
                        "scored_origins": len(scored),
                        "created_origin_sha256": origin_hash(created),
                        "skipped_origin_sha256": origin_hash(skipped),
                        "scored_origin_sha256": origin_hash(scored),
                        "both_manifest_schedules_match_input": True,
                        "review_status": "PENDING_PEER",
                    }
                )
    return {
        "schema": "hung-block7-input-eligibility-v1",
        "scope": "input-derived origin eligibility vs authenticated manifest tags; not journal byte or numeric readback",
        "input_zip_sha256": INPUT_SHA256,
        "coverage_sha256": expected_coverage_sha,
        "member_pins": member_pins,
        "counts": {
            "pairs": len(results),
            "origins": sum(row["requested_origins"] for row in results),
            "created": sum(row["created_origins"] for row in results),
            "skipped": sum(row["skipped_origins"] for row in results),
            "scored": sum(row["scored_origins"] for row in results),
        },
        "pairs": results,
    }


def main() -> None:
    result = audit()
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if OUTPUT.exists():
        if OUTPUT.read_bytes() != payload:
            raise ValueError("Existing input eligibility evidence differs")
    else:
        with OUTPUT.open("xb") as stream:
            stream.write(payload)
    print(json.dumps({"counts": result["counts"], "sha256": hashlib.sha256(payload).hexdigest()}))


if __name__ == "__main__":
    main()
