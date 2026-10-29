"""Audit scored-day symmetry across the frozen 360-job Final matrix."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

LOCK_SHA = "e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e"
ARCHIVE_SHA = "531bff0d24ddf7eb0a08d4ed9d97976e55140b81025db0d91c28c557684e1114"
SCORES_SHA = "9e09ae4f72b13c03ed029deb338301753ae377c15cbbfa7414433c5538cba73a"
SOURCE_KERNEL = "hungluongduc/hung-final-e5e8fe1c-360-20261029-v1/1"
STATIONS = ("2118", "2534", "2579")
BUDGETS = (7, 14, 28)
START = datetime.fromisoformat("2022-12-01T00:00:00+08:00")
SCHEDULE = {(START + timedelta(days=index)).isoformat() for index in range(90)}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(
    scores_path: Path, receipt_path: Path, runs_path: Path, *, score_sha: str = SCORES_SHA
) -> dict:
    """Verify exact job accounting, scored dates and same-label comparison support."""
    if _sha256(scores_path) != score_sha:
        raise ValueError("Pinned Final CPU score-source SHA-256 mismatch")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        receipt.get("schema") != "hung-final-remote-metrics-receipt-v1"
        or receipt.get("status") != "FINAL_RUN_SCORES_RECOMPUTED_FROM_CHECKPOINTS"
        or receipt.get("source_kernel") != SOURCE_KERNEL
        or receipt.get("lock_sha256") != LOCK_SHA
        or receipt.get("archive_sha256") != ARCHIVE_SHA
        or receipt.get("output_sha256") != score_sha
        or receipt.get("output_bytes") != scores_path.stat().st_size
        or receipt.get("jobs") != 360
        or receipt.get("scored_jobs") != 360
        or receipt.get("null_jobs") != 0
    ):
        raise ValueError("Final CPU score receipt binding mismatch")
    source = json.loads(scores_path.read_text(encoding="utf-8"))
    if (
        source.get("schema") != "hung-final-remote-run-scores-v1"
        or source.get("source_kernel") != SOURCE_KERNEL
        or source.get("lock_sha256") != LOCK_SHA
        or source.get("archive_sha256") != ARCHIVE_SHA
    ):
        raise ValueError("Final score-source identity mismatch")
    jobs = source["jobs"]
    with runs_path.open(encoding="utf-8", newline="") as stream:
        runs = list(csv.DictReader(stream))
    by_id = {row["job_id"]: row for row in runs}
    if len(jobs) != 360 or len(runs) != 360 or len(by_id) != 360:
        raise ValueError("Final score/run job count mismatch")
    if len({job["job_id"] for job in jobs}) != 360:
        raise ValueError("Duplicate Final score job ID")
    if set(by_id) != {job["job_id"] for job in jobs}:
        raise ValueError("Final score/run jobset mismatch")

    grouped = defaultdict(list)
    for job in jobs:
        row = by_id[job["job_id"]]
        identity = (str(job["entity_id"]), int(job["budget_days"]))
        if identity[0] not in STATIONS or identity[1] not in BUDGETS:
            raise ValueError("Job outside locked station/budget scope")
        for field in ("dataset_id", "city_id", "entity_id", "variant", "method"):
            if str(job[field]) != row[field]:
                raise ValueError(f"Final job {job['job_id']}: {field} mismatch")
        for field in ("budget_days", "seed"):
            if int(job[field]) != int(row[field]):
                raise ValueError(f"Final job {job['job_id']}: {field} mismatch")
        days = job["days"]
        coverage = job["coverage"]
        if (
            coverage["requested"] != 90
            or coverage["created"] != 90
            or coverage["skipped_all_missing_history"] != 0
            or coverage["skipped_undefined_scale"] != 0
            or coverage["scored"] != len(days)
            or coverage["unscored_created"] != 90 - len(days)
            or int(row["requested_origins"]) != 90
            or int(row["issued_forecasts"]) != 90
            or int(row["scored_days"]) != len(days)
            or job["metrics"]["hours"] != 24 * len(days)
            or not set(days) <= SCHEDULE
        ):
            raise ValueError(f"Final job {job['job_id']}: coverage mismatch")
        grouped[identity].append(job)

    expected_groups = {(station, budget) for station in STATIONS for budget in BUDGETS}
    if set(grouped) != expected_groups:
        raise ValueError("Final station/budget group set mismatch")
    result = []
    for station, budget in sorted(grouped):
        group = grouped[(station, budget)]
        if len(group) != 40:
            raise ValueError(f"Station {station}, budget {budget}: expected 40 jobs")
        scored_sets = {frozenset(job["days"]) for job in group}
        if len(scored_sets) != 1:
            raise ValueError(f"Station {station}, budget {budget}: scored-day sets differ")
        scored = set(next(iter(scored_sets)))
        for day in scored:
            labels = {job["days"][day]["label_sha256"] for job in group}
            if len(labels) != 1:
                raise ValueError(f"Station {station}, budget {budget}, day {day}: labels differ")
        result.append(
            {
                "entity_id": station,
                "budget_days": budget,
                "jobs": len(group),
                "requested_origins": 90 * len(group),
                "issued_forecasts": 90 * len(group),
                "scored_origins": sum(len(job["days"]) for job in group),
                "unscored_origins": sum(90 - len(job["days"]) for job in group),
                "common_scored_days": len(scored),
                "unscored_day_ids": sorted(SCHEDULE - scored),
                "same_scored_day_set_and_label_hashes": True,
            }
        )
    return {
        "schema": "hung-final-coverage-symmetry-audit-v1",
        "scores_sha256": score_sha,
        "receipt_sha256": _sha256(receipt_path),
        "runs_csv_sha256": _sha256(runs_path),
        "jobs": len(jobs),
        "scored_origins": sum(row["scored_origins"] for row in result),
        "unscored_origins": sum(row["unscored_origins"] for row in result),
        "station_budget": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--runs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"refusing to overwrite {args.output}")
    result = audit(args.scores, args.receipt, args.runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"jobs": result["jobs"], "unscored_origins": result["unscored_origins"]}))


if __name__ == "__main__":
    main()
