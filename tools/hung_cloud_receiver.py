"""Restore one completed Development shard, verify receipts and score on CPU."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def verification_command(plan: Path, partition: Path, shard_id: str, sha256) -> list[str]:
    """The receiver has no stage-execution command or execution fallback."""
    return [
        sys.executable,
        "-u",
        "-m",
        "experiments.supporting_pipeline.dispatch_matched",
        "--plan",
        str(plan),
        "--plan-sha256",
        sha256(plan),
        "--shards",
        str(partition),
        "--shards-sha256",
        sha256(partition),
        "--shard-id",
        shard_id,
        "--resume",
        "--verify-only",
    ]


def restore(
    provider,
    archive: Path,
    receipt_path: Path,
    plan_path: Path,
    partition_path: Path,
    *,
    root: Path,
    expected_code: str,
) -> dict:
    """Validate the archive and exact runtime plan before creating any output."""
    plan = json.loads(plan_path.read_bytes())
    partition = json.loads(partition_path.read_bytes())
    receipt = json.loads(receipt_path.read_bytes())
    require(
        plan["scope"] == "development_only" and plan["code_commit"] == expected_code,
        "Development code identity differs",
    )
    plan_sha, partition_sha = provider.sha256(plan_path), provider.sha256(partition_path)
    require(partition["plan_sha256"] == plan_sha == receipt["plan_sha256"], "Plan SHA differs")
    require(partition_sha == receipt["shards_sha256"], "Partition SHA differs")
    require(
        receipt["exit_code"] == receipt["local_verify_exit_code"] == 0, "Execution/verifier failed"
    )
    require(receipt["crc"] == "passed", "Original archive CRC failed")
    shard = next(s for s in partition["shards"] if s["id"] == receipt["shard_id"])
    jobs = shard["job_ids"]
    require(0 < len(jobs) <= 20 and len(jobs) == len(set(jobs)), "Not one bounded shard")
    require(receipt["job_ids"] == jobs, "Receipt job set differs")
    require(
        archive.stat().st_size == receipt["artifact_bytes"]
        and provider.sha256(archive) == receipt["artifact_sha256"],
        "Archive SHA/size differs",
    )
    output = Path(plan["output_root"])
    require(output.resolve().is_relative_to(root.resolve()), "Output outside receiver root")
    require(not output.exists(), "Restore output already exists; no overwrite")
    with zipfile.ZipFile(archive) as stream:
        names = provider.safe_members(stream)
        require(
            json.loads(stream.read("dispatch_identity.json"))["plan_sha256"] == plan_sha,
            "Archive dispatch identity differs",
        )
        require(
            all(
                n == "dispatch_identity.json"
                or (
                    len(n.split("/")) >= 3
                    and n.split("/")[0] in {"jobs", "receipts", "logs"}
                    and n.split("/")[1] in jobs
                )
                for n in names
            ),
            "Foreign archive member",
        )
        output.mkdir(parents=True, exist_ok=False)
        stream.extractall(output)
    return receipt


def receive(
    provider,
    scorer: dict,
    archive: Path,
    receipt_path: Path,
    repo: Path,
    *,
    expected_code: str,
    evidence: Path,
    scorer_sha256: str,
) -> dict:
    """Verify all official stages and dependencies before recomputing live forecasts."""
    root = repo.parent
    require(evidence.resolve().is_relative_to(root.resolve()), "Evidence outside receiver")
    require(not evidence.exists(), "Receiver evidence already exists")
    plan = repo / ".cache/provider/plan.json"
    partition = repo / ".cache/provider/shards.json"
    started = time.perf_counter()
    receipt = restore(
        provider, archive, receipt_path, plan, partition, root=root, expected_code=expected_code
    )
    evidence.mkdir(exist_ok=False)
    command = verification_command(plan, partition, receipt["shard_id"], provider.sha256)
    environment = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONPATH": os.pathsep.join((str(repo / "src"), str(repo))),
    }
    verify_started = time.perf_counter()
    with (evidence / "verify.log").open("x", encoding="utf-8") as log:
        verified = subprocess.run(
            command,
            cwd=repo,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=1800,
            check=False,
        )
    terminal = {
        "exit_code": verified.returncode,
        "command": command,
        "wall_seconds": time.perf_counter() - verify_started,
        "executed": False,
        "purpose": "Official --verify-only; no training fallback",
        "log_sha256": provider.sha256(evidence / "verify.log"),
    }
    provider.save(evidence / "verify-exit.json", terminal)
    require(verified.returncode == 0, "CPU official receipt/dependency verification failed")
    spec = {
        "plan": {"path": str(plan), "sha256": provider.sha256(plan)},
        "partition": {"path": str(partition), "sha256": provider.sha256(partition)},
        "completed_shards": [
            {
                "id": receipt["shard_id"],
                "verify_exit": {
                    "path": str(evidence / "verify-exit.json"),
                    "sha256": provider.sha256(evidence / "verify-exit.json"),
                },
            }
        ],
    }
    provider.save(evidence / "collection.json", spec)
    catalog = scorer["build_catalog"](spec, root)
    catalog["catalog_sha256"] = provider.sha256(evidence / "collection.json")
    provider.save(evidence / "catalog.json", catalog)
    result = scorer["aggregate_results"](catalog, root)
    result["catalog_sha256"] = provider.sha256(evidence / "catalog.json")
    provider.save(evidence / "results.json", result)
    summary = {
        "schema": "hung-cloud-cpu-receiver-v1",
        "scope": "development_only",
        "passed": True,
        "executed": False,
        "shard_id": receipt["shard_id"],
        "jobs": len(receipt["job_ids"]),
        "counts": result["counts"],
        "artifact_sha256": receipt["artifact_sha256"],
        "artifact_bytes": receipt["artifact_bytes"],
        "original_receipt_sha256": provider.sha256(receipt_path),
        "model_code_commit": expected_code,
        "plan_sha256": provider.sha256(plan),
        "partition_sha256": provider.sha256(partition),
        "scorer_sha256": scorer_sha256,
        "verification": terminal,
        "elapsed_seconds": time.perf_counter() - started,
        "results_sha256": provider.sha256(evidence / "results.json"),
        "catalog_sha256": provider.sha256(evidence / "catalog.json"),
        "peer_acceptance": "pending; technical restore/readback is not independent scientific review",
    }
    provider.save(evidence / "readback-summary.json", summary)
    print(json.dumps(summary), flush=True)
    return summary
