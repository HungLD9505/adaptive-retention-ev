"""Recompute Development daily errors from immutable training ZIPs on local CPU.

This is an alternative readback when a saved Kaggle CPU exporter is still pending.
It never runs training and requires the original receipt, allocation and payload pins.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import zipfile
from pathlib import Path

import torch

from tools.hung_kaggle_export_batches import digest
from tools.hung_results import file_sha, score_saved

PAYLOAD_SHA = "23a6d420523d990d07ff07d814ed642a851925283a102a3ae806f3b666e1d6f4"
ALLOCATION_SHA = "05e0d8158f71fc07d58c49c30a165aadce0b333b2f7df0f09b069d0b2f510ed5"
PLAN_SHA = "2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee"
SCORER_SHA = "68fccbed056734d9b4842f7bda088880d7812d12417d64878d1aa018fc010456"
MODEL_CODE = "44b8532959d76fb20691881539f991ca44983727"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(archive: zipfile.ZipFile, name: str) -> dict:
    return json.loads(archive.read(name))


def score_shard(
    archive_path: Path,
    receipt_path: Path,
    payload_path: Path,
    allocation_path: Path,
    shard_id: str,
    root: Path,
) -> dict:
    """Verify exact archive/job/stage bindings and recompute saved forecasts."""
    root = root.resolve()
    for path in (archive_path, receipt_path, payload_path, allocation_path):
        require(path.resolve().is_relative_to(root), "Input outside repository")
    require(file_sha(Path(__file__).with_name("hung_results.py")) == SCORER_SHA, "Scorer changed")
    require(file_sha(payload_path) == PAYLOAD_SHA, "Payload changed")
    require(file_sha(allocation_path) == ALLOCATION_SHA, "Allocation file changed")
    allocation = json.loads(allocation_path.read_bytes())
    require(
        allocation["schema"] == "hung-kaggle-export-batches-v1"
        and allocation["scope"] == "development_only"
        and allocation["canonical_plan_sha256"] == PLAN_SHA,
        "Allocation scope/plan differs",
    )
    require(digest(allocation["batches"]) == allocation["allocation_sha256"], "Allocation changed")
    records = [r for b in allocation["batches"] for r in b["records"] if r["shard_id"] == shard_id]
    require(len(records) == 1, "Shard absent or duplicated in allocation")
    record = records[0]
    receipt = json.loads(receipt_path.read_bytes())
    require(receipt["shard_id"] == shard_id, "Receipt shard differs")
    require(receipt["job_ids"] == record["job_ids"], "Receipt jobset differs")
    require(receipt["plan_sha256"] == record["plan_sha256"], "Receipt plan differs")
    require(receipt["shards_sha256"] == record["partition_sha256"], "Receipt partition differs")
    require(
        receipt["exit_code"] == receipt["local_verify_exit_code"] == 0, "Training verifier failed"
    )
    require(receipt["crc"] == "passed", "Original CRC receipt failed")
    require(archive_path.stat().st_size == receipt["artifact_bytes"], "Archive byte count differs")
    require(file_sha(archive_path) == receipt["artifact_sha256"], "Archive SHA differs")

    with zipfile.ZipFile(payload_path) as payload, zipfile.ZipFile(archive_path) as archive:
        require(archive.testzip() is None, "Archive CRC differs")
        payload_manifest = read_json(payload, "payload-manifest.json")
        require(payload_manifest["parent_plan_sha256"] == PLAN_SHA, "Payload plan differs")
        plan = read_json(payload, "portable-plan.json")
        require(
            plan["scope"] == "development_only" and plan["code_commit"] == MODEL_CODE,
            "Plan differs",
        )
        identity = read_json(archive, "dispatch_identity.json")
        require(identity["code"]["commit"] == MODEL_CODE, "Execution code differs")
        require(identity["plan_sha256"] == receipt["plan_sha256"], "Dispatch plan differs")
        require(identity["shards_sha256"] == receipt["shards_sha256"], "Dispatch partition differs")
        jobs = {j["id"]: j for j in plan["jobs"]}
        cells = {c["id"]: c for c in plan["cells"]}
        configs = {c["id"]: c for c in plan["configs"]}
        result = []
        for job_id in record["job_ids"]:
            job = jobs[job_id]
            runtime_job = copy.deepcopy(job)
            for role in ("source", "target"):
                if runtime_job[role]:
                    runtime_job[role]["path"] = (
                        f"/kaggle/working/{record['base']}/repo/" + runtime_job[role]["path"]
                    )
            cell = cells[job["cell"]]
            config_pin = configs[job["config"]]
            config_bytes = payload.read(config_pin["path"])
            require(sha_bytes(config_bytes) == config_pin["sha256"], "Config SHA differs")
            config = json.loads(config_bytes)
            final_stage = f"replay-{config['replay']['max_origins']}"
            receipt_name = f"receipts/{job_id}/job.json"
            job_receipt = read_json(archive, receipt_name)
            require(job_receipt["job_id"] == job_id, "Job receipt differs")
            require(job_receipt["plan_sha256"] == receipt["plan_sha256"], "Job plan differs")
            require(
                job_receipt["shards_sha256"] == receipt["shards_sha256"], "Job partition differs"
            )
            require(final_stage in job_receipt["stages"], "Final stage absent")
            for stage, stage_sha in job_receipt["stages"].items():
                stage_bytes = archive.read(f"receipts/{job_id}/{stage}.json")
                require(sha_bytes(stage_bytes) == stage_sha, "Stage receipt SHA differs")
                stage_record = json.loads(stage_bytes)
                binding = stage_record["binding"]
                require(binding["job"] == runtime_job, "Stage job binding differs")
                require(binding["config_sha256"] == config_pin["sha256"], "Stage config differs")
                require(
                    binding["input_manifest_sha256"] == cell["input_manifest_sha256"],
                    "Stage input differs",
                )
                require(binding["plan_sha256"] == receipt["plan_sha256"], "Stage plan differs")
                require(
                    binding["shards_sha256"] == receipt["shards_sha256"], "Stage partition differs"
                )
                for name, item in stage_record["files"].items():
                    require(
                        sha_bytes(archive.read(f"jobs/{job_id}/{stage}/{name}")) == item["sha256"],
                        "Stage artifact SHA differs",
                    )
            prefix = f"jobs/{job_id}/{final_stage}/"
            manifest_name = prefix + "run_manifest.json"
            manifest_bytes = archive.read(manifest_name)
            manifest = json.loads(manifest_bytes)
            checkpoint_name = (
                "runner.pt"
                if manifest["schema"] == "hung-single-baseline-replay-v1"
                else "runner_checkpoint.pt"
            )
            checkpoint_bytes = archive.read(prefix + checkpoint_name)
            require(
                sha_bytes(checkpoint_bytes) == manifest["final_runner_checkpoint_sha256"],
                "Checkpoint SHA differs",
            )
            binding = manifest["input_binding"]
            require(
                binding["input_manifest_sha256"] == cell["input_manifest_sha256"],
                "Final input differs",
            )
            require(
                binding["entity_id"] == cell["entity_id"]
                and binding["history_days"] == cell["budget"],
                "Final cell differs",
            )
            require(manifest["code"]["commit"] == MODEL_CODE, "Final code differs")
            for role in ("source", "target"):
                expected = job[role]["sha256"] if job[role] else None
                if expected is not None:
                    require(
                        manifest[f"{role}_checkpoint_sha256"] == expected, "Initialization differs"
                    )
            state = torch.load(io.BytesIO(checkpoint_bytes), map_location="cpu", weights_only=True)
            require(state["binding"] == binding, "Checkpoint binding differs")
            scored = score_saved(state, manifest)
            result.append(
                {
                    "job_id": job_id,
                    "method": job_id[: -len("_" + job["cell"])],
                    "budget": cell["budget"],
                    "seed": cell["seed"],
                    "entity_id": cell["entity_id"],
                    "input_manifest_sha256": cell["input_manifest_sha256"],
                    "source_sha256": job["source"]["sha256"] if job["source"] else None,
                    "target_sha256": job["target"]["sha256"] if job["target"] else None,
                    "manifest": {
                        "archive_sha256": receipt["artifact_sha256"],
                        "member": manifest_name,
                        "sha256": sha_bytes(manifest_bytes),
                    },
                    "checkpoint": {
                        "archive_sha256": receipt["artifact_sha256"],
                        "member": prefix + checkpoint_name,
                        "sha256": sha_bytes(checkpoint_bytes),
                    },
                    "proofs": [
                        {"path": str(receipt_path.resolve()), "sha256": file_sha(receipt_path)}
                    ],
                    "status": "DISPATCH_VERIFIED",
                    **scored,
                    "code_commit": MODEL_CODE,
                    "device": manifest.get("device"),
                    "final_stage_duration_seconds": manifest.get("duration_seconds"),
                    "cumulative_runtime_costs": manifest.get("runtime_costs", manifest.get("cost")),
                    "cumulative_proxy_costs": manifest.get("proxy_costs"),
                }
            )
    require(len(result) == len(record["job_ids"]) == 20, "Output job count differs")
    return {
        "schema": "hung-portable-daily-errors-v1",
        "scope": "development_only",
        "canonical_plan_sha256": allocation["canonical_plan_sha256"],
        "scorer_sha256": SCORER_SHA,
        "provenance": {
            "derivation": "local CPU scoring from immutable training ZIP; no training",
            "shard_id": shard_id,
            "archive_sha256": receipt["artifact_sha256"],
            "receipt_sha256": file_sha(receipt_path),
            "allocation_sha256": file_sha(allocation_path),
            "payload_sha256": PAYLOAD_SHA,
        },
        "acceptance": "Technical archive/readback only; independent review pending",
        "records": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--allocation", required=True, type=Path)
    parser.add_argument("--shard", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(args.root.resolve()), "Output outside repository")
    require(not args.output.exists(), "Output exists; preserve it")
    result = score_shard(
        args.archive, args.receipt, args.payload, args.allocation, args.shard, args.root
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(
            (
                json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
            ).encode()
        )
    print(
        json.dumps(
            {
                "shard": args.shard,
                "jobs": len(result["records"]),
                "scorable": sum(bool(r["days"]) for r in result["records"]),
                "sha256": file_sha(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
