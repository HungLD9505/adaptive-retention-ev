"""Stream one saved Development shard into a small, create-only per-job proof.

This verifier does not run training, fetch Kaggle data or authenticate caller-supplied
version IDs. The caller must mount the exact saved output and independently bind
its version and archive fingerprint to the provider's readback record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import zipfile
from typing import Any

MODEL_CODE = "44b8532959d76fb20691881539f991ca44983727"
PARENT_PLAN_SHA = "2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee"
PARENT_PARTITION_SHA = "7dd340b84a51abca9dcb2e83490d088c07178ffbdbb9d81d68225d665a279c7f"


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def member_sha256(archive: zipfile.ZipFile, name: str) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with archive.open(name) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def pinned_jobs(
    plan: dict[str, Any], partition: dict[str, Any], shard_id: str
) -> tuple[dict, dict, dict, list[str]]:
    jobs = {job["id"]: job for job in plan["jobs"]}
    cells = {cell["id"]: cell for cell in plan["cells"]}
    configs = {config["id"]: config for config in plan["configs"]}
    require(len(jobs) == len(plan["jobs"]), "Duplicate job IDs in plan")
    shards = [shard for shard in partition["shards"] if shard["id"] == shard_id]
    require(len(shards) == 1, f"Missing/duplicate shard {shard_id}")
    ids = shards[0]["job_ids"]
    require(len(ids) == len(set(ids)) and 0 < len(ids) <= 20, "Invalid shard jobset")
    require(all(jid in jobs for jid in ids), "Shard names a foreign job")
    return jobs, cells, configs, ids


def equivalent_job(parent: dict[str, Any], provider: dict[str, Any]) -> bool:
    """Allow transport path relocation while preserving every scientific job pin."""
    for key in ("id", "cell", "config", "method"):
        if parent.get(key) != provider.get(key):
            return False
    for key in ("source", "target"):
        before, after = parent.get(key) or {}, provider.get(key) or {}
        if before.get("sha256") != after.get("sha256"):
            return False
    return True


def planned_stages(job: dict, config: dict) -> list[str]:
    """Derive the mandatory stage set from the pinned dispatch plan."""
    replay = config["replay"]
    block, limit = replay["block_days"], replay["max_origins"]
    require(
        type(block) is int and type(limit) is int and block > 0 and limit >= 2 * block + 1,
        "Invalid replay limits",
    )
    split = min(3 * block, limit - 1)
    require(split != limit, "Replay stages overlap")
    method = job["method"]
    if method == "target_only":
        prefix = ["target-only-init"]
    elif method not in {"seasonal_naive", "frozen_source"} and job["target"] is None:
        prefix = ["target"]
    else:
        prefix = []
    return [*prefix, f"replay-{split}", f"replay-{limit}"]


def checked_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            require(key not in value, f"Duplicate JSON key: {label}/{key}")
            value[key] = item
        return value

    result = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(result, dict), f"Expected JSON object: {label}")
    return result


def expected_stage_files(stage: str, method: str) -> tuple[str, str | None]:
    if stage == "target-only-init":
        return "initial.pt", None
    if stage == "target":
        return "target_checkpoint.pt", None
    if method in {"seasonal_naive", "target_only", "frozen_source"}:
        return "runner.pt", "forecasts.jsonl"
    return "runner_checkpoint.pt", "events.jsonl"


def verify_argv(binding: dict, job: dict, cell: dict, stage: str, root: str) -> None:
    args = binding.get("args")
    require(isinstance(args, list) and all(isinstance(x, str) for x in args), "Invalid argv")
    expected_module = (
        "experiments.supporting_pipeline.single_baseline_cli"
        if job["method"] in {"seasonal_naive", "target_only", "frozen_source"}
        else "experiments.supporting_pipeline.cli"
    )
    require(binding.get("module") == expected_module, f"Stage module mismatch: {stage}")
    expected_command = (
        "target-only-init"
        if stage == "target-only-init"
        else "target-smoke"
        if stage == "target"
        else "replay-development"
    )
    require(args and args[0] == expected_command, f"Stage command mismatch: {stage}")

    def flag_value(flag: str) -> str | None:
        positions = [i for i, value in enumerate(args) if value == flag]
        require(len(positions) <= 1, f"Duplicate stage argv flag: {stage}/{flag}")
        if not positions or positions[0] + 1 >= len(args):
            return None
        return args[positions[0] + 1]

    for flag, value in (
        ("--manifest-sha256", cell["input_manifest_sha256"]),
        ("--entity-id", str(cell["entity_id"])),
        ("--output", f"{root}/jobs/{job['id']}/{stage}"),
    ):
        require(flag_value(flag) == value, f"Stage argv {flag} mismatch: {stage}")
    if stage.startswith("replay-"):
        require(
            flag_value("--max-origins") == stage.removeprefix("replay-"), "Replay limit mismatch"
        )
        require(flag_value("--device") == job["device"], "Replay device mismatch")
        if job["method"] in {"seasonal_naive", "target_only", "frozen_source"}:
            require(flag_value("--method") == job["method"], "Replay method mismatch")
        else:
            require(flag_value("--seed") == str(cell["seed"]), "Replay seed mismatch")


def verify_shard(
    parent_plan_path: pathlib.Path,
    parent_partition_path: pathlib.Path,
    provider_plan_path: pathlib.Path,
    provider_partition_path: pathlib.Path,
    archive_path: pathlib.Path,
    shard_id: str,
    expected_archive_sha256: str,
    expected_archive_bytes: int,
    saved_version_id: int,
    readback_version_id: int,
    config_blobs: dict[str, bytes],
) -> dict[str, Any]:
    """Verify archive, receipts, manifests and all referenced bytes without extraction."""
    require(file_sha256(parent_plan_path) == PARENT_PLAN_SHA, "Parent plan SHA mismatch")
    require(
        file_sha256(parent_partition_path) == PARENT_PARTITION_SHA, "Parent partition SHA mismatch"
    )
    parent_plan = read_json(parent_plan_path)
    parent_partition = read_json(parent_partition_path)
    provider_plan_sha = file_sha256(provider_plan_path)
    provider_partition_sha = file_sha256(provider_partition_path)
    provider_plan = read_json(provider_plan_path)
    provider_partition = read_json(provider_partition_path)
    require(parent_partition["plan_sha256"] == PARENT_PLAN_SHA, "Parent partition binding mismatch")
    require(
        provider_partition["plan_sha256"] == provider_plan_sha,
        "Provider partition binding mismatch",
    )
    require(
        parent_plan["code_commit"] == provider_plan["code_commit"] == MODEL_CODE,
        "Model code mismatch",
    )
    require(parent_plan["scope"] == provider_plan["scope"] == "development_only", "Scope mismatch")
    parent_jobs, parent_cells, parent_configs, expected_ids = pinned_jobs(
        parent_plan, parent_partition, shard_id
    )
    provider_jobs, provider_cells, provider_configs, provider_ids = pinned_jobs(
        provider_plan, provider_partition, shard_id
    )
    require(
        set(config_blobs) == set(provider_configs) == set(parent_configs),
        "Pinned config set mismatch",
    )
    config_values = {}
    for config_id, raw in config_blobs.items():
        require(
            isinstance(raw, bytes)
            and hashlib.sha256(raw).hexdigest()
            == provider_configs[config_id]["sha256"]
            == parent_configs[config_id]["sha256"],
            f"Pinned config SHA mismatch: {config_id}",
        )
        config_values[config_id] = checked_json_bytes(raw, f"config {config_id}")
    require(provider_ids == expected_ids, "Provider shard differs from parent jobset")
    for jid in expected_ids:
        pj, qj = parent_jobs[jid], provider_jobs[jid]
        require(equivalent_job(pj, qj), f"Transport changed scientific job pin: {jid}")
        pc, qc = parent_cells[pj["cell"]], provider_cells[qj["cell"]]
        for key in ("id", "budget", "seed", "entity_id", "input_manifest_sha256"):
            require(pc.get(key) == qc.get(key), f"Transport changed cell {key}: {jid}")
        require(
            parent_configs[pj["config"]]["sha256"] == provider_configs[qj["config"]]["sha256"],
            f"Transport changed config: {jid}",
        )
    require(
        expected_archive_bytes > 0 and len(expected_archive_sha256) == 64, "Invalid archive pin"
    )
    require(archive_path.stat().st_size == expected_archive_bytes, "Archive byte count mismatch")
    require(file_sha256(archive_path) == expected_archive_sha256, "Archive SHA mismatch")
    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(archive_path) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        require(len(names) == len(set(names)), "Duplicate ZIP member")
        require(
            all(
                not pathlib.PurePosixPath(name).is_absolute()
                and ".." not in pathlib.PurePosixPath(name).parts
                for name in names
            ),
            "Unsafe ZIP member",
        )
        # Verify every member, including unreferenced files, before accepting the shard.
        bad_member = archive.testzip()
        require(bad_member is None, f"ZIP CRC mismatch: {bad_member}")
        identity = checked_json_bytes(archive.read("dispatch_identity.json"), "dispatch identity")
        all_stage_count = sum(
            len(planned_stages(job, config_values[job["config"]])) for job in provider_plan["jobs"]
        )
        require(
            identity.get("schema") == "hung-resumable-dispatch-v1"
            and identity.get("plan_sha256") == provider_plan_sha
            and identity.get("shards_sha256") == provider_partition_sha
            and identity.get("jobs") == len(provider_plan["jobs"])
            and identity.get("stages") == all_stage_count
            and identity.get("code", {}).get("commit") == MODEL_CODE
            and identity.get("single_code", {}).get("commit") == MODEL_CODE,
            "Archive dispatch identity mismatch",
        )
        expected_members = {"dispatch_identity.json"}
        receipt_ids = {
            name.split("/")[1]
            for name in names
            if name.startswith("receipts/") and name.endswith("/job.json")
        }
        require(receipt_ids == set(expected_ids), "Archived receipt jobset mismatch")
        for jid in expected_ids:
            job = provider_jobs[jid]
            cell = provider_cells[job["cell"]]
            config = provider_configs[job["config"]]
            stages = planned_stages(job, config_values[job["config"]])
            receipt_path = f"receipts/{jid}/job.json"
            receipt_bytes = archive.read(receipt_path)
            receipt = checked_json_bytes(receipt_bytes, receipt_path)
            require(
                receipt["job_id"] == jid
                and receipt["plan_sha256"] == provider_plan_sha
                and receipt["shards_sha256"] == provider_partition_sha
                and set(receipt["stages"]) == set(stages)
                and len(receipt["stages"]) == len(stages),
                f"Job receipt binding mismatch: {jid}",
            )
            expected_members.add(receipt_path)
            stage_manifests: dict[str, str] = {}
            stage_receipts: dict[str, str] = {}
            member_count = 0
            for stage in stages:
                expected_stage_sha = receipt["stages"][stage]
                stage_path = f"receipts/{jid}/{stage}.json"
                stage_bytes = archive.read(stage_path)
                stage_sha = hashlib.sha256(stage_bytes).hexdigest()
                require(
                    stage_sha == expected_stage_sha, f"Stage receipt SHA mismatch: {jid}/{stage}"
                )
                stage_receipt = checked_json_bytes(stage_bytes, stage_path)
                binding = stage_receipt["binding"]
                cell_digest = hashlib.sha256(
                    json.dumps(
                        {
                            key: value
                            for key, value in cell.items()
                            if key not in {"input_run", "manifest", "entity"}
                        },
                        sort_keys=True,
                        allow_nan=False,
                    ).encode()
                ).hexdigest()
                require(
                    binding["job"] == job
                    and binding["stage"] == stage
                    and binding["plan_sha256"] == provider_plan_sha
                    and binding["shards_sha256"] == provider_partition_sha
                    and binding["input_manifest_sha256"] == cell["input_manifest_sha256"]
                    and binding["config_sha256"] == config["sha256"]
                    and binding["cell_sha256"] == cell_digest,
                    f"Stage binding mismatch: {jid}/{stage}",
                )
                verify_argv(binding, job, cell, stage, provider_plan["output_root"])
                files = stage_receipt["files"]
                checkpoint, journal = expected_stage_files(stage, job["method"])
                required_files = {"run_manifest.json", "dispatch_measurement.json", checkpoint}
                if journal:
                    required_files.add(journal)
                require(
                    required_files <= set(files), f"Missing required stage files: {jid}/{stage}"
                )
                expected_members.add(stage_path)
                for filename, expected in files.items():
                    require(
                        pathlib.PurePosixPath(filename).as_posix() == filename
                        and not pathlib.PurePosixPath(filename).is_absolute()
                        and ".." not in pathlib.PurePosixPath(filename).parts,
                        f"Unsafe stage filename: {jid}/{stage}/{filename}",
                    )
                    size, digest = member_sha256(archive, f"jobs/{jid}/{stage}/{filename}")
                    require(
                        size == expected["bytes"] and digest == expected["sha256"],
                        f"Member mismatch: {jid}/{stage}/{filename}",
                    )
                    expected_members.add(f"jobs/{jid}/{stage}/{filename}")
                    member_count += 1
                log_size, log_sha = member_sha256(archive, f"logs/{jid}/{stage}.log")
                require(
                    log_size > 0
                    and log_size == stage_receipt["log"]["bytes"]
                    and log_sha == stage_receipt["log"]["sha256"],
                    f"Log mismatch: {jid}/{stage}",
                )
                log_header = checked_json_bytes(
                    archive.read(f"logs/{jid}/{stage}.log").splitlines()[0],
                    f"log header {jid}/{stage}",
                )
                require(
                    log_header.get("command", [])[1:] == ["-m", binding["module"], *binding["args"]]
                    and log_header.get("config_sha256") == config["sha256"]
                    and log_header.get("input_manifest_sha256") == cell["input_manifest_sha256"],
                    f"Log execution binding mismatch: {jid}/{stage}",
                )
                expected_members.add(f"logs/{jid}/{stage}.log")
                member_count += 1
                manifest = checked_json_bytes(
                    archive.read(f"jobs/{jid}/{stage}/run_manifest.json"),
                    f"manifest {jid}/{stage}",
                )
                input_binding = manifest.get("input_binding", manifest.get("binding", {}))
                code_identity = (
                    identity["single_code"]
                    if job["method"] in {"seasonal_naive", "target_only", "frozen_source"}
                    else identity["code"]
                )
                digest_field = (
                    "initial_checkpoint_sha256"
                    if stage == "target-only-init"
                    else "checkpoint_sha256"
                    if stage == "target"
                    else "final_runner_checkpoint_sha256"
                )
                require(
                    manifest["status"] == "completed"
                    and manifest.get("run_id") == stage
                    and manifest["code"]["commit"] == MODEL_CODE
                    and manifest["code"].get("executed_sources")
                    == code_identity["executed_sources"]
                    and input_binding["entity_id"] == str(cell["entity_id"])
                    and input_binding["history_days"] == cell["budget"]
                    and input_binding["input_manifest_sha256"] == cell["input_manifest_sha256"]
                    and manifest.get(digest_field) == files[checkpoint]["sha256"],
                    f"Run manifest identity mismatch: {jid}/{stage}",
                )
                if journal:
                    journal_field = (
                        "forecast_journal" if journal == "forecasts.jsonl" else "event_journal"
                    )
                    require(
                        manifest.get(journal_field, {}).get("file") == journal
                        and manifest[journal_field].get("sha256") == files[journal]["sha256"],
                        f"Run journal mismatch: {jid}/{stage}",
                    )
                stage_manifests[stage] = files["run_manifest.json"]["sha256"]
                stage_receipts[stage] = stage_sha
            rows.append(
                {
                    "job_id": jid,
                    "shard_id": shard_id,
                    "method": job["method"],
                    "cell_id": job["cell"],
                    "budget_days": cell["budget"],
                    "seed": cell["seed"],
                    "entity_id": cell["entity_id"],
                    "input_manifest_sha256": cell["input_manifest_sha256"],
                    "config_sha256": provider_configs[job["config"]]["sha256"],
                    "job_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
                    "stage_receipt_sha256": stage_receipts,
                    "stage_manifest_sha256": stage_manifests,
                    "verified_member_count": member_count,
                    "status": "VERIFIED_ARCHIVE_BYTES_AND_STAGE_PLAN",
                }
            )
    require(len(rows) == len(expected_ids), "Per-job proof count mismatch")
    require(set(names) == expected_members, "Unexpected or unreceipted archive member")
    return {
        "schema": "hung-kaggle-compact-shard-proof-v2",
        "scope": "development_only",
        "parent_plan_sha256": PARENT_PLAN_SHA,
        "parent_partition_sha256": PARENT_PARTITION_SHA,
        "provider_plan_sha256": provider_plan_sha,
        "provider_partition_sha256": provider_partition_sha,
        "model_code_commit": MODEL_CODE,
        "shard_id": shard_id,
        "archive_sha256": expected_archive_sha256,
        "archive_bytes": expected_archive_bytes,
        "claimed_saved_version_id": saved_version_id,
        "claimed_readback_version_id": readback_version_id,
        "version_ids_independently_authenticated": False,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "parent_plan",
        "parent_partition",
        "provider_plan",
        "provider_partition",
        "archive",
        "out",
    ):
        parser.add_argument("--" + name.replace("_", "-"), required=True, type=pathlib.Path)
    parser.add_argument("--shard-id", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--archive-bytes", required=True, type=int)
    parser.add_argument("--saved-version-id", required=True, type=int)
    parser.add_argument("--readback-version-id", required=True, type=int)
    parser.add_argument("--config-bundle", required=True, type=pathlib.Path)
    args = parser.parse_args()
    require(args.saved_version_id >= 0 and args.readback_version_id >= 0, "Invalid version IDs")
    provider_plan = read_json(args.provider_plan)
    with zipfile.ZipFile(args.config_bundle) as config_bundle:
        config_blobs = {
            spec["id"]: config_bundle.read(
                f".cache/provider/configs/{pathlib.Path(spec['path']).name}"
            )
            for spec in provider_plan["configs"]
        }
    proof = verify_shard(
        args.parent_plan,
        args.parent_partition,
        args.provider_plan,
        args.provider_partition,
        args.archive,
        args.shard_id,
        args.archive_sha256,
        args.archive_bytes,
        args.saved_version_id,
        args.readback_version_id,
        config_blobs,
    )
    serialized = json.dumps(proof, sort_keys=True, indent=2, allow_nan=False) + "\n"
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
    print(
        json.dumps(
            {
                "shard_id": args.shard_id,
                "jobs": len(proof["rows"]),
                "proof_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()
