"""Immutable review capsules: historical VERIFIED_REUSE Main plus local shards.

Only stored Development forecasts are read. No training, Final access, historical
identity rewriting or cloud credentials are involved in packing/verifying.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path, PurePosixPath


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def safe_members(archive: zipfile.ZipFile) -> list[str]:
    names = archive.namelist()
    check(len(names) == len(set(names)), "Duplicate ZIP member")
    for name in names:
        path = PurePosixPath(name)
        check(
            not path.is_absolute()
            and ".." not in path.parts
            and "\\" not in name
            and ":" not in name
            and str(path) == name.rstrip("/"),
            "Unsafe ZIP member",
        )
    check(archive.testzip() is None, "ZIP CRC failed")
    return names


def read_pin(pin: dict, root: Path) -> bytes:
    path = Path(pin["path"]).resolve()
    check(path.is_relative_to(root.resolve()), "Read outside project")
    data = path.read_bytes()
    check(digest(data) == pin["sha256"], f"SHA mismatch: {path.name}")
    return data


def build(spec: dict, root: Path, destination: Path) -> dict:
    check(destination.resolve().is_relative_to(root.resolve()), "Output outside project")
    plan = json.loads(read_pin(spec["plan"], root))
    partition = json.loads(read_pin(spec["partition"], root))
    ledger = json.loads(read_pin(spec["ledger"], root))
    check(
        plan["scope"] == "development_only" and partition["plan_sha256"] == spec["plan"]["sha256"],
        "Development plan/partition binding differs",
    )
    files = {}
    mains = []
    local = []
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "x") as archive:

        def add(member: str, data: bytes, *, stored=False):
            check(member not in files, "Duplicate logical member")
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
            files[member] = {"sha256": digest(data), "bytes": len(data)}

        for key in ("plan", "partition", "ledger"):
            add(f"metadata/{key}.json", read_pin(spec[key], root))
        add("code/hung_results.py", read_pin(spec["scorer"], root))
        for row in ledger["jobs"]:
            if row["status"] != "VERIFIED_REUSE":
                continue
            check(row["job_id"].startswith("main_"), "Unsupported reuse identity")
            manifest_bytes = read_pin(row["run_manifest"], root)
            manifest = json.loads(manifest_bytes)
            check(
                manifest["status"] == "completed"
                and manifest["code"]["commit"] == row["historical_code_commit"],
                "Historical terminal/code identity differs",
            )
            for role in ("source", "target"):
                check(
                    manifest[f"{role}_checkpoint_sha256"] == row[role]["sha256"],
                    "Historical initializer differs",
                )
                read_pin(row[role], root)
            parent = Path(row["run_manifest"]["path"]).parent
            checkpoint = read_pin(
                {
                    "path": str(parent / "runner_checkpoint.pt"),
                    "sha256": manifest["final_runner_checkpoint_sha256"],
                },
                root,
            )
            journal = manifest["event_journal"]
            events = read_pin(
                {"path": str(parent / journal["file"]), "sha256": journal["sha256"]}, root
            )
            prefix = f"historical/{row['job_id']}"
            add(prefix + "/run_manifest.json", manifest_bytes)
            add(prefix + "/runner_checkpoint.pt", checkpoint)
            add(prefix + "/events.jsonl", events)
            mains.append(
                {
                    "job_id": row["job_id"],
                    "prefix": prefix,
                    "original_run_id": manifest["run_id"],
                    "ledger_status": row["status"],
                    "historical_code_commit": row["historical_code_commit"],
                }
            )
        for shard in spec["local_shards"]:
            record = json.loads(read_pin(shard["receipt"], root))
            terminal = json.loads(read_pin(shard["verify_exit"], root))
            check(
                terminal["exit_code"] == 0 and record["crc"] == "passed",
                "Local verifier/CRC failed",
            )
            expected = record.get("artifact_sha256", record.get("sha256"))
            check(expected == shard["archive"]["sha256"], "Published archive pin differs")
            data = read_pin(shard["archive"], root)
            check(
                len(data) == record.get("artifact_bytes", record.get("bytes")),
                "Archive byte count differs",
            )
            prefix = f"local/{shard['id']}"
            add(prefix + "/artifacts.zip.bin", data, stored=True)
            add(prefix + "/receipt.json", read_pin(shard["receipt"], root))
            add(prefix + "/verify-exit.json", read_pin(shard["verify_exit"], root))
            local.append({"shard_id": shard["id"], "prefix": prefix, "job_ids": record["job_ids"]})
        manifest = {
            "schema": "hung-review-capsule-v1",
            "scope": "development_only",
            "parent_plan_sha256": spec["plan"]["sha256"],
            "parent_partition_sha256": spec["partition"]["sha256"],
            "model_code_commit": plan["code_commit"],
            "files": files,
            "main_runs": mains,
            "local_shards": local,
            "acceptance": "Technical capsule only; independent scientific review pending",
        }
        archive.writestr(
            "capsule-manifest.json", json.dumps(manifest, sort_keys=True, indent=2) + "\n"
        )
    with zipfile.ZipFile(destination) as archive:
        safe_members(archive)
    with destination.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return {
        "schema": "hung-review-capsule-receipt-v1",
        "scope": "development_only",
        "sha256": sha,
        "bytes": destination.stat().st_size,
        "crc": "passed",
        "main_runs": len(mains),
        "new_local_jobs": sum(len(s["job_ids"]) for s in local),
        "parent_plan_sha256": spec["plan"]["sha256"],
        "spec": spec,
    }


def verify(archive_path: Path, expected_sha: str, *, score=False) -> dict:
    with archive_path.open("rb") as stream:
        check(
            hashlib.file_digest(stream, "sha256").hexdigest() == expected_sha,
            "Capsule SHA mismatch",
        )
    computed = []
    with zipfile.ZipFile(archive_path) as archive:
        names = safe_members(archive)
        capsule = json.loads(archive.read("capsule-manifest.json"))
        check(capsule["scope"] == "development_only", "Wrong scope")
        check(
            set(names) == set(capsule["files"]) | {"capsule-manifest.json"},
            "Capsule inventory differs",
        )
        for member, pin in capsule["files"].items():
            data = archive.read(member)
            check(
                len(data) == pin["bytes"] and digest(data) == pin["sha256"],
                "Member hash/size differs",
            )
        plan = json.loads(archive.read("metadata/plan.json"))
        partition = json.loads(archive.read("metadata/partition.json"))
        check(
            digest(archive.read("metadata/plan.json")) == capsule["parent_plan_sha256"],
            "Plan SHA differs",
        )
        check(
            digest(archive.read("metadata/partition.json")) == capsule["parent_partition_sha256"],
            "Partition SHA differs",
        )
        check(
            plan["scope"] == "development_only"
            and partition["plan_sha256"] == capsule["parent_plan_sha256"],
            "Plan scope/binding differs",
        )
        ledger = json.loads(archive.read("metadata/ledger.json"))
        allowed = {r["job_id"]: r for r in ledger["jobs"] if r["status"] == "VERIFIED_REUSE"}
        seen = set()
        scorer = {}
        if score:
            import torch

            scorer = {"__name__": "pinned_scorer"}
            exec(
                compile(
                    archive.read("code/hung_results.py"), "pinned_saved_forecast_scorer", "exec"
                ),
                scorer,
            )

        def score_one(job_id, manifest, checkpoint):
            if score:
                state = torch.load(io.BytesIO(checkpoint), map_location="cpu", weights_only=True)
                check(
                    state["binding"] == manifest["input_binding"],
                    "Checkpoint input binding differs",
                )
                result = scorer["score_saved"](state, manifest)
                computed.append(
                    {"job_id": job_id, "metrics": result["metrics"], "coverage": result["coverage"]}
                )

        for row in capsule["main_runs"]:
            check(
                row["job_id"] in allowed and row["job_id"] not in seen, "Unapproved/duplicate Main"
            )
            seen.add(row["job_id"])
            original = allowed[row["job_id"]]
            prefix = row["prefix"]
            manifest_bytes = archive.read(prefix + "/run_manifest.json")
            check(
                digest(manifest_bytes) == original["run_manifest"]["sha256"],
                "Main manifest pin differs",
            )
            manifest = json.loads(manifest_bytes)
            checkpoint = archive.read(prefix + "/runner_checkpoint.pt")
            check(
                digest(checkpoint) == manifest["final_runner_checkpoint_sha256"],
                "Main checkpoint differs",
            )
            check(
                manifest["run_id"] == row["original_run_id"]
                and manifest["code"]["commit"] == row["historical_code_commit"],
                "Historical run identity changed",
            )
            check(
                digest(archive.read(prefix + "/events.jsonl"))
                == manifest["event_journal"]["sha256"],
                "Main journal differs",
            )
            score_one(row["job_id"], manifest, checkpoint)
        check(seen == set(allowed), "Historical Main inventory incomplete")
        jobs = {j["id"]: j for j in plan["jobs"]}
        cells = {c["id"]: c for c in plan["cells"]}
        configs = {c["id"]: c for c in plan["configs"]}
        for shard in capsule["local_shards"]:
            prefix = shard["prefix"]
            declared = next(
                s["job_ids"] for s in partition["shards"] if s["id"] == shard["shard_id"]
            )
            check(shard["job_ids"] == declared, "Local canonical shard differs")
            outer = json.loads(archive.read(prefix + "/receipt.json"))
            data = archive.read(prefix + "/artifacts.zip.bin")
            check(
                digest(data) == outer.get("artifact_sha256", outer.get("sha256")),
                "Local archive pin differs",
            )
            check(
                json.loads(archive.read(prefix + "/verify-exit.json"))["exit_code"] == 0,
                "Verifier exit failed",
            )
            with zipfile.ZipFile(io.BytesIO(data)) as inner:
                members = safe_members(inner)
                actual = {
                    name.split("/")[1]
                    for name in members
                    if name.startswith("receipts/") and name.endswith("/job.json")
                }
                check(actual == set(declared), "Archive contains missing/extra terminal jobs")
                check(
                    all(
                        name == "dispatch_identity.json"
                        or (
                            len(name.split("/")) >= 3
                            and name.split("/")[0] in {"jobs", "receipts", "logs"}
                            and name.split("/")[1] in actual
                        )
                        for name in members
                    ),
                    "Unexpected shard member",
                )
                identity = json.loads(inner.read("dispatch_identity.json"))
                check(
                    identity["plan_sha256"] == capsule["parent_plan_sha256"],
                    "Local plan identity differs",
                )
                for job_id in declared:
                    check(job_id not in seen, "Duplicate logical job")
                    seen.add(job_id)
                    receipt = json.loads(inner.read(f"receipts/{job_id}/job.json"))
                    check(
                        receipt["job_id"] == job_id
                        and receipt["plan_sha256"] == capsule["parent_plan_sha256"]
                        and receipt["shards_sha256"] == capsule["parent_partition_sha256"],
                        "Job receipt differs",
                    )
                    final = None
                    for stage, sha in receipt["stages"].items():
                        stage_bytes = inner.read(f"receipts/{job_id}/{stage}.json")
                        check(digest(stage_bytes) == sha, "Stage receipt hash differs")
                        record = json.loads(stage_bytes)
                        binding = record["binding"]
                        job = jobs[job_id]
                        check(
                            binding["job"] == job
                            and binding["plan_sha256"] == capsule["parent_plan_sha256"]
                            and binding["shards_sha256"] == capsule["parent_partition_sha256"]
                            and binding["input_manifest_sha256"]
                            == cells[job["cell"]]["input_manifest_sha256"]
                            and binding["config_sha256"] == configs[job["config"]]["sha256"],
                            "Job provenance differs",
                        )
                        for name, pin in record["files"].items():
                            content = inner.read(f"jobs/{job_id}/{stage}/{name}")
                            check(
                                len(content) == pin["bytes"] and digest(content) == pin["sha256"],
                                "Stage file hash differs",
                            )
                        if stage.startswith("replay-") and (
                            final is None or int(stage[7:]) > int(final[7:])
                        ):
                            final = stage
                    check(final is not None, "No complete replay")
                    manifest = json.loads(inner.read(f"jobs/{job_id}/{final}/run_manifest.json"))
                    filename = (
                        "runner.pt"
                        if manifest["schema"] == "hung-single-baseline-replay-v1"
                        else "runner_checkpoint.pt"
                    )
                    checkpoint = inner.read(f"jobs/{job_id}/{final}/{filename}")
                    check(
                        digest(checkpoint) == manifest["final_runner_checkpoint_sha256"],
                        "Final checkpoint hash differs",
                    )
                    score_one(job_id, manifest, checkpoint)
    return {
        "schema": "hung-independent-capsule-readback-v1",
        "scope": "development_only",
        "passed": True,
        "capsule_sha256": expected_sha,
        "main_runs": len(capsule["main_runs"]),
        "new_local_jobs": sum(len(s["job_ids"]) for s in capsule["local_shards"]),
        "scored_runs": sum(r["metrics"] is not None for r in computed),
        "computed_runs": computed,
        "crc": "passed",
        "review": "Independent scientific acceptance still pending",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--spec-sha256")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--score", action="store_true")
    args = parser.parse_args()
    check(
        args.archive.resolve().is_relative_to(args.project_root.resolve())
        and args.receipt.resolve().is_relative_to(args.project_root.resolve()),
        "Output outside project",
    )
    if args.spec:
        spec = json.loads(
            read_pin({"path": str(args.spec), "sha256": args.spec_sha256}, args.project_root)
        )
        result = build(spec, args.project_root, args.archive)
    else:
        result = verify(args.archive, args.archive_sha256, score=args.score)
    with args.receipt.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"spec", "computed_runs"}}))


if __name__ == "__main__":
    main()
