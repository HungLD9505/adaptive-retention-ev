"""Compare pinned Block7/Main manifest event eligibility without accepting fairness."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib

from tools import hung_block7_manifest_pairs as pairs

EVENT_KINDS = ("forecast", "skip", "unscored", "score", "update")
OUTPUT = pairs.ROOT / "docs/reports/hung-block7-origin-eligibility-20261028-v3.csv"


def event_schedule(manifest: dict) -> dict[str, list[str]]:
    """Validate recorded per-origin event tags against manifest coverage."""
    events = manifest["event_evidence"]["events"]
    if not isinstance(events, list) or not all(isinstance(event, str) for event in events):
        raise ValueError("Invalid manifest event list")
    schedule: dict[str, list[str]] = {kind: [] for kind in EVENT_KINDS}
    for event in events:
        kind, separator, origin = event.partition(":")
        if kind in schedule:
            if not separator or not origin:
                raise ValueError(f"Invalid {kind} event")
            schedule[kind].append(origin)
    coverage = manifest["coverage"]
    issued = schedule["forecast"]
    skipped = schedule["skip"]
    outcomes = schedule["unscored"]
    scored = schedule["score"]
    updated = schedule["update"]
    requested = coverage["requested"]
    if not (
        requested == 90
        and len(issued) == coverage["created"]
        and len(issued) + len(skipped) == requested
        and len(skipped)
        == coverage["skipped_all_missing_history"] + coverage["skipped_undefined_scale"]
        and len(outcomes) == requested
        and len(scored) == coverage["scored"]
        and len(issued) - len(scored) == coverage["unscored_created"]
        and scored == updated
        and len(set(issued + skipped)) == requested
        and set(outcomes) == set(issued + skipped)
        and len(set(outcomes)) == requested
        and set(scored).issubset(issued)
        and len(set(scored)) == len(scored)
    ):
        raise ValueError("Manifest event/coverage disagreement")
    return schedule


def schedule_sha256(schedule: dict[str, list[str]]) -> str:
    data = json.dumps(schedule, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compare(coverage: dict, manifest_dir: pathlib.Path) -> list[dict]:
    """Return one row per pinned pair, preserving the historical review status."""
    rows = pairs.compare(coverage, manifest_dir)
    if len(rows) != 69 or any(row["review_status"] != "PENDING_PEER" for row in rows):
        raise ValueError("Underlying 69-pair manifest audit is incomplete")
    result = []
    external = coverage["external_complete_jobs"]
    main = coverage["reused_jobs"]
    for row in rows:
        old_id, main_id = row["historical_run_id"], row["main_run_id"]
        old = pairs.checked_manifest(
            external[old_id]["run_manifest"], manifest_dir / f"{old_id}.json"
        )
        current = pairs.checked_manifest(main[main_id], manifest_dir / f"{main_id}.json")
        old_schedule, main_schedule = event_schedule(old), event_schedule(current)
        result.append(
            {
                "cell_id": row["cell_id"],
                "budget_days": row["budget_days"],
                "seed": row["seed"],
                "historical_run_id": old_id,
                "main_run_id": main_id,
                "historical_manifest_sha256": row["historical_manifest_sha256"],
                "main_manifest_sha256": row["main_manifest_sha256"],
                "historical_event_journal_sha256": old["event_journal"]["sha256"],
                "main_event_journal_sha256": current["event_journal"]["sha256"],
                "historical_event_sha256": schedule_sha256(old_schedule),
                "main_event_sha256": schedule_sha256(main_schedule),
                "forecast_origin_count": len(old_schedule["forecast"]),
                "skipped_origin_count": len(old_schedule["skip"]),
                "scored_origin_count": len(old_schedule["score"]),
                "origin_event_tags_equal": old_schedule == main_schedule,
                "review_status": "PENDING_PEER",
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=pathlib.Path, default=pairs.DEFAULT_COVERAGE)
    parser.add_argument("--manifest-dir", type=pathlib.Path, default=pairs.DEFAULT_MANIFEST_DIR)
    parser.add_argument("--output", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args()
    evidence = json.loads(pairs.EVIDENCE.read_text(encoding="utf-8"))
    expected_sha = evidence["audit"]["provenance"]["inputs"]["coverage"]["sha256"]
    if pairs.sha_file(args.coverage) != expected_sha:
        raise SystemExit("Coverage SHA mismatch")
    rows = compare(json.loads(args.coverage.read_text(encoding="utf-8")), args.manifest_dir)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    data = stream.getvalue().encode("utf-8")
    if args.output.exists():
        if args.output.read_bytes() != data:
            raise SystemExit("Existing origin table differs")
    else:
        args.output.write_bytes(data)
    print(
        json.dumps(
            {
                "pairs": len(rows),
                "equal_origin_event_tags": sum(row["origin_event_tags_equal"] for row in rows),
                "peer_accepted": 0,
                "output_sha256": pairs.sha_file(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
