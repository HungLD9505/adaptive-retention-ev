"""Publish a row-level audit of the already verified, frozen Hùng Final."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from tools.hung_final_aggregate_v1 import (
    ARCHIVE_SHA,
    JOBSET_SHA,
    LEDGER_SHA,
    LOCK_SHA,
    ROOT,
    SOURCE,
    pinned_json,
    validate_rows,
)

READBACK_RECEIPT_SHA = "19936edd017e76254abd9481fd8b8637cbf2081df798bee56f15f1cc6b869b8f"
METRICS_RECEIPT_SHA = "657264b1330d48b77f65ea032e3a69f351c6ba8f657a3ae432a3e1060b23bc65"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def project_job(job: dict, score: dict, stages: dict, code_commit: str) -> dict:
    """Bind one locked job to its remote artifact paths and scored row."""
    job_id = job["job_id"]
    replay = stages.get("replay")
    if not isinstance(replay, dict):
        raise ValueError(f"Missing replay stage: {job_id}")
    prefix = f"stages/{job_id}/replay/"
    if replay.get("manifest") != prefix + "run_manifest.json":
        raise ValueError(f"Replay manifest path mismatch: {job_id}")
    artifacts = replay.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != len(set(artifacts)):
        raise ValueError(f"Duplicate or malformed replay artifacts: {job_id}")
    if any(not isinstance(path, str) or not path.startswith(prefix) for path in artifacts):
        raise ValueError(f"Replay artifact path mismatch: {job_id}")
    checkpoints = [
        path for path in artifacts if path.endswith(("runner.pt", "runner_checkpoint.pt"))
    ]
    if len(checkpoints) != 1 or replay["manifest"] not in artifacts:
        raise ValueError(f"Missing or duplicate replay checkpoint/manifest: {job_id}")
    for name, stage in stages.items():
        stage_prefix = f"stages/{job_id}/{name}/"
        if stage.get("manifest") != stage_prefix + "run_manifest.json":
            raise ValueError(f"Stage manifest path mismatch: {job_id}/{name}")
        if stage["manifest"] not in stage.get("artifacts", []):
            raise ValueError(f"Stage manifest absent from artifacts: {job_id}/{name}")
    coverage = score["coverage"]
    return {
        "job_id": job_id,
        "dataset_id": job["dataset_id"],
        "city_id": job["city_id"],
        "entity_id": job["entity_id"],
        "budget_days": job["budget_days"],
        "seed": job["seed"],
        "variant": job["variant"],
        "method": job["method"],
        "code_commit": code_commit,
        "lock_sha256": LOCK_SHA,
        "input_manifest_sha256": job["input_manifest_sha256"],
        "source_checkpoint_sha256": job["source_checkpoint_sha256"],
        "initial_target_checkpoint_sha256": job["target_checkpoint_sha256"] or "",
        "provider_saved_version": SOURCE,
        "provider_run_id": 363367272,
        "archive_sha256": ARCHIVE_SHA,
        "replay_manifest_path": replay["manifest"],
        "replay_manifest_sha256": score["manifest_sha256"],
        "replay_checkpoint_path": checkpoints[0],
        "replay_checkpoint_sha256": score["checkpoint_sha256"],
        "stage_names": ";".join(sorted(stages)),
        "artifact_path_count": sum(len(stage["artifacts"]) for stage in stages.values()),
        "receipt_status": "REMOTE_READBACK_RECEIPT_BOUND",
        "remote_archive_bytes_sha_crc_verified": "TRUE",
        "local_archive_bytes_verified": "FALSE",
        "local_ledger_and_score_bytes_verified": "TRUE",
        "checkpoint_reloaded_for_metrics": "TRUE",
        "requested_origins": coverage["requested"],
        "issued_forecasts": coverage["created"],
        "scored_days": coverage["scored"],
        "unscored_origins": coverage["unscored_created"],
        "metric_status": "SCORED" if score["metrics"] is not None else "NULL",
        "mae_kwh": "" if score["metrics"] is None else score["metrics"]["mae_kwh"],
        "rmse_kwh": "" if score["metrics"] is None else score["metrics"]["rmse_kwh"],
        "failure_reason": "",
    }


def build(
    lock_path: Path,
    jobset_path: Path,
    ledger_path: Path,
    readback_path: Path,
    scores_path: Path,
    metrics_receipt_path: Path,
    output_dir: Path,
) -> dict:
    """Verify pinned inputs and write a create-only CSV plus its digest."""
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(ROOT.resolve()) or output_dir.exists():
        raise ValueError("Output must be a new directory inside the repository")
    lock = pinned_json(lock_path, LOCK_SHA)
    jobset = pinned_json(jobset_path, JOBSET_SHA)
    ledger = pinned_json(ledger_path, LEDGER_SHA)
    readback = pinned_json(readback_path, READBACK_RECEIPT_SHA)
    metrics_receipt = pinned_json(metrics_receipt_path, METRICS_RECEIPT_SHA)
    if sha256(scores_path) != metrics_receipt["output_sha256"]:
        raise ValueError("Score output SHA mismatch")
    if scores_path.stat().st_size != metrics_receipt["output_bytes"]:
        raise ValueError("Score output byte count mismatch")
    scores = json.loads(scores_path.read_text(encoding="utf-8"))
    if lock["jobset"]["sha256"] != JOBSET_SHA or lock["jobset"]["count"] != 360:
        raise ValueError("Lock/jobset mismatch")
    if ledger["lock_sha256"] != LOCK_SHA or ledger["archive_sha256"] != ARCHIVE_SHA:
        raise ValueError("Remote ledger lock/archive mismatch")
    if (
        readback["status"] != "REMOTE_ARCHIVE_BYTES_SHA_CRC_AND_JOBSET_VERIFIED"
        or readback["jobs"] != 360
        or readback["ledger_sha256"] != LEDGER_SHA
        or readback["ledger_bytes"] != ledger_path.stat().st_size
        or readback["archive"]["sha256"] != ARCHIVE_SHA
        or readback["archive"]["bytes"] != 2404391526
        or readback["archive"]["crc32"] != "6a29f6e1"
        or readback["lock_sha256"] != LOCK_SHA
        or readback["source_kernel"] != SOURCE
        or readback["source_run_id"] != 363367272
    ):
        raise ValueError("Remote readback receipt mismatch")
    jobs = {job["job_id"]: job for job in jobset["jobs"]}
    if len(jobs) != 360 or len(jobset["jobs"]) != 360:
        raise ValueError("Duplicate or missing locked jobs")
    verified_scores = validate_rows(scores, metrics_receipt, jobs, ledger)
    rows = sorted(
        (
            project_job(
                jobs[score["job_id"]], score, ledger["jobs"][score["job_id"]], lock["code_commit"]
            )
            for score in verified_scores
        ),
        key=lambda row: row["job_id"],
    )
    if len(rows) != 360 or len({row["job_id"] for row in rows}) != 360:
        raise ValueError("Ledger row count mismatch")
    output_dir.mkdir(parents=True)
    csv_path = output_dir / "jobs.csv"
    with csv_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "schema": "hung-final-verification-ledger-v1",
        "jobs": len(rows),
        "scored_jobs": sum(row["metric_status"] == "SCORED" for row in rows),
        "null_jobs": sum(row["metric_status"] == "NULL" for row in rows),
        "remote_verified_jobs": len(rows),
        "local_archive_byte_verified_jobs": 0,
        "lock_sha256": LOCK_SHA,
        "jobset_sha256": JOBSET_SHA,
        "remote_ledger_sha256": LEDGER_SHA,
        "readback_receipt_sha256": READBACK_RECEIPT_SHA,
        "metrics_receipt_sha256": METRICS_RECEIPT_SHA,
        "scores_sha256": sha256(scores_path),
        "jobs_csv_sha256": sha256(csv_path),
    }
    with (output_dir / "summary.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = ROOT / ".cache"
    summary = build(
        root / "hung-final-lock-20261029T014357Z/lock.json",
        root / "hung-final-lock-20261029T014357Z/jobset.json",
        root
        / "hung-final-direct-readback-20261029-v1/saved-output-v1-complete/final-job-artifact-ledger.json",
        root
        / "hung-final-direct-readback-20261029-v1/saved-output-v1-complete/final-direct-readback.json",
        root / "hung-final-metrics-20261029-v2/saved-output-v1-complete/final-run-scores.json",
        root / "hung-final-metrics-20261029-v2/saved-output-v1-complete/final-metrics-receipt.json",
        args.output_dir,
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
