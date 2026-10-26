"""Execute an explicit hash-pinned local Development queue without an LLM monitor."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from experiments.hung_sprint2.dispatch_state import atomic_create, exclusive_lock, select_shard
from tools.hung_provider import check, pinned, safe_members, sha256


def validate_queue(path: Path, digest: str) -> tuple[dict, dict, dict]:
    """Authenticate the queue and complete global assignment before any subprocess."""
    queue = pinned(path, digest)
    check(queue["schema"] == "hung-local-development-queue-v1", "Unexpected queue schema")
    check(sha256(Path(__file__)) == queue["worker_source_sha256"], "Worker source changed")
    plan = pinned(Path(queue["plan"]), queue["plan_sha256"])
    check(plan["scope"] == "development_only", "Only Development execution is allowed")
    partition = pinned(Path(queue["partition"]), queue["partition_sha256"])
    job_ids = [job["id"] for job in plan["jobs"]]
    routes = queue["routes"]
    check(set(routes) == {s["id"] for s in partition["shards"]}, "Incomplete shard routes")
    for shard in partition["shards"]:
        select_shard(partition, queue["plan_sha256"], job_ids, shard["id"])
    pending = queue["pending_local_shards"]
    check(len(pending) == len(set(pending)), "Duplicate local shard")
    check(pending and all(routes.get(s) == "local" for s in pending), "Foreign local assignment")
    check(
        "pilot_0000" not in pending and queue["barrier"]["shard_id"] not in pending,
        "Completed pilot/barrier cannot be queued again",
    )
    check(
        set(pending) | {queue["barrier"]["shard_id"]}
        == {s for s, route in routes.items() if route == "local"},
        "Local routes omitted from queue",
    )
    check(set(routes.values()) <= {"local", "kaggle", "completed_local_pilot"}, "Unknown route")
    check(queue["minimum_free_bytes"] >= 8 * 1024**3, "Storage reserve below dispatcher gate")
    proof = pinned(Path(queue["provider_readback"]), queue["provider_readback_sha256"])
    check(
        proof["cross_runtime"]["passed"] and proof["storage_readback"]["crc"] == "passed",
        "Pilot portability/storage prerequisite failed",
    )
    return queue, plan, partition


def wait_for_barrier(queue: dict) -> None:
    """Wait on an actual terminal receipt; a PID or log message is insufficient."""
    barrier = queue["barrier"]
    deadline = time.monotonic() + queue["barrier_timeout_seconds"]
    root = Path(barrier["evidence"])
    while not (root / "archive.json").exists():
        for name in ("exit.json", "verify-exit.json"):
            if (root / name).exists():
                check(
                    json.loads((root / name).read_bytes())["exit_code"] == 0,
                    f"Barrier {name} failed; preserve outputs",
                )
        check(
            time.monotonic() < deadline, "Barrier terminal receipt timed out; no training started"
        )
        time.sleep(30)
    for name in ("exit.json", "verify-exit.json"):
        check(json.loads((root / name).read_bytes())["exit_code"] == 0, "Barrier failed")
    record = json.loads((root / "archive.json").read_bytes())
    check(record["job_ids"] == barrier["job_ids"], "Barrier job set differs")
    check(sha256(root / "artifacts.zip") == record["sha256"], "Barrier archive SHA differs")
    with zipfile.ZipFile(root / "artifacts.zip") as archive:
        safe_members(archive)


def run_shard(queue: dict, plan: dict, partition: dict, shard_id: str, evidence: Path) -> dict:
    evidence.mkdir(exist_ok=False)
    command = [
        sys.executable,
        "-u",
        "-m",
        "experiments.hung_sprint2.dispatch_matched",
        "--plan",
        queue["plan"],
        "--plan-sha256",
        queue["plan_sha256"],
        "--shards",
        queue["partition"],
        "--shards-sha256",
        queue["partition_sha256"],
        "--shard-id",
        shard_id,
        "--resume",
    ]
    started = time.perf_counter()
    environment = {**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": queue["canonical_repo"]}
    for name, option in (("execute", "--execute"), ("verify", "--verify-only")):
        with (evidence / f"{name}.log").open("x", encoding="utf-8") as log:
            result = subprocess.run(
                command + [option],
                cwd=queue["canonical_repo"],
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        atomic_create(
            evidence / f"{name}-exit.json",
            {"exit_code": result.returncode, "log_sha256": sha256(evidence / f"{name}.log")},
        )
        check(result.returncode == 0, f"{shard_id} {name} failed; preserve partial output")
    output = Path(plan["output_root"])
    jobs = select_shard(partition, queue["plan_sha256"], [j["id"] for j in plan["jobs"]], shard_id)
    archive_path = evidence / "artifacts.zip"
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for job in jobs:
            for kind in ("jobs", "receipts", "logs"):
                for source in sorted((output / kind / job).rglob("*")):
                    if source.is_file():
                        archive.write(source, source.relative_to(output).as_posix())
        archive.write(output / "dispatch_identity.json", "dispatch_identity.json")
    with zipfile.ZipFile(archive_path) as archive:
        safe_members(archive)
    receipt = {
        "shard_id": shard_id,
        "job_ids": jobs,
        "plan_sha256": queue["plan_sha256"],
        "partition_sha256": queue["partition_sha256"],
        "artifact_sha256": sha256(archive_path),
        "artifact_bytes": archive_path.stat().st_size,
        "crc": "passed",
        "wall_seconds": time.perf_counter() - started,
        "remote_readback": "pending; archive is on persistent local SSD",
        "peer_acceptance": "pending",
    }
    atomic_create(evidence / "receipt.json", receipt)
    return receipt


def work(path: Path, digest: str, evidence: Path, *, execute: bool) -> dict:
    queue, plan, partition = validate_queue(path, digest)
    if not execute:
        return {"executed": False, "shards": queue["pending_local_shards"]}
    check(
        evidence.resolve().is_relative_to(Path(queue["project_root"]).resolve()),
        "Evidence outside project",
    )
    evidence.mkdir(parents=True, exist_ok=False)
    with exclusive_lock(evidence):
        atomic_create(evidence / "identity.json", {"queue_sha256": digest, "queue": queue})
        try:
            wait_for_barrier(queue)
            completed = []
            for shard_id in queue["pending_local_shards"]:
                current, current_plan, current_partition = validate_queue(path, digest)
                check(
                    current == queue and current_plan == plan and current_partition == partition,
                    "Queue dependencies changed",
                )
                check(
                    shutil.disk_usage(plan["output_root"]).free >= queue["minimum_free_bytes"],
                    "Local storage reserve reached; no next shard",
                )
                receipt = run_shard(queue, plan, partition, shard_id, evidence / shard_id)
                completed.append(receipt)
                print(json.dumps(receipt), flush=True)
            result = {
                "completed_shards": len(completed),
                "completed_jobs": sum(len(r["job_ids"]) for r in completed),
                "queue_sha256": digest,
            }
            atomic_create(evidence / "complete.json", result)
            return result
        except Exception as error:
            atomic_create(evidence / "failure.json", {"error": str(error), "queue_sha256": digest})
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--queue-sha256", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(work(args.queue, args.queue_sha256, args.evidence, execute=args.execute)))


if __name__ == "__main__":
    main()
