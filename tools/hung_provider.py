"""Portable, hash-pinned Development packages for the existing dispatcher.

This stdlib launcher runs outside the bundled clean code checkout. Only paths
change during relocation; model code, configuration bytes and job IDs do not.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def pinned(path: Path, digest: str) -> dict:
    check(sha256(path) == digest, f"SHA mismatch: {path}")
    return json.loads(path.read_bytes())


def safe_members(archive: zipfile.ZipFile) -> list[str]:
    names = archive.namelist()
    check(len(set(names)) == len(names), "Duplicate archive members")
    for name in names:
        path = PurePosixPath(name)
        check(
            not path.is_absolute()
            and ".." not in path.parts
            and "\\" not in name
            and ":" not in name
            and str(path) == name.rstrip("/"),
            f"Unsafe archive member: {name}",
        )
    check(archive.testzip() is None, "Archive CRC mismatch")
    return names


def package(
    repo: Path,
    plan_path: Path,
    plan_sha: str,
    shards_path: Path,
    shards_sha: str,
    inputs: Path,
    inputs_sha: str,
    destination: Path,
) -> dict:
    """Copy exact pinned dependencies to a new project-local transport directory."""
    repo = repo.resolve()
    plan = pinned(plan_path, plan_sha)
    shards = pinned(shards_path, shards_sha)
    check(plan["scope"] == "development_only", "Development plan required")
    check(shards["plan_sha256"] == plan_sha, "Partition plan differs")
    expected = [job["id"] for job in plan["jobs"]]
    assigned = [job for shard in shards["shards"] for job in shard["job_ids"]]
    check(
        len(assigned) == len(set(assigned)) and set(assigned) == set(expected),
        "Partition is incomplete or overlapping",
    )
    check(sha256(inputs) == inputs_sha, "Input ZIP SHA mismatch")
    check(destination.resolve().is_relative_to(repo), "Destination outside repository")
    destination.mkdir(parents=True, exist_ok=False)
    payload = destination / "payload"
    payload.mkdir()
    refs = subprocess.check_output(
        ["git", "for-each-ref", "--points-at", plan["code_commit"], "--format=%(refname)"],
        cwd=repo,
        text=True,
    ).splitlines()
    check(bool(refs), "Pinned code must have a named Git ref for the offline bundle")
    subprocess.run(
        ["git", "bundle", "create", str((payload / "code.bundle").resolve()), refs[0]],
        cwd=repo,
        check=True,
    )
    shutil.copyfile(inputs, payload / "inputs.zip")
    shutil.copyfile(plan_path, payload / "parent-plan.json")
    shutil.copyfile(shards_path, payload / "parent-shards.json")
    relocated = copy.deepcopy(plan)
    for config in relocated["configs"]:
        source = Path(config["path"])
        check(sha256(source) == config["sha256"], f"Config SHA mismatch: {source}")
        name = f".cache/provider/configs/{config['id']}.json"
        target = payload / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        config["path"] = name
    selection = relocated["selection"]
    check(sha256(Path(selection["path"])) == selection["sha256"], "Selection SHA mismatch")
    shutil.copyfile(selection["path"], payload / ".cache/provider/selection.json")
    selection["path"] = ".cache/provider/selection.json"
    for job in relocated["jobs"]:
        for role in ("source", "target"):
            spec = job[role]
            if spec is None:
                continue
            source = Path(spec["path"])
            manifest = source.parent / "run_manifest.json"
            check(sha256(source) == spec["sha256"], "Checkpoint SHA mismatch")
            check(sha256(manifest) == spec["run_manifest_sha256"], "Manifest SHA mismatch")
            relative = f".cache/provider/checkpoints/{spec['sha256']}/{source.parent.name}"
            target = payload / relative
            target.mkdir(parents=True, exist_ok=True)
            for item in (source, manifest):
                output = target / item.name
                if output.exists():
                    check(sha256(output) == sha256(item), "Conflicting checkpoint manifest")
                else:
                    shutil.copyfile(item, output)
            spec["path"] = f"{relative}/{source.name}"
    relocated["input_base"] = "data/inputs/issue18-input-handoff-v1-20261019"
    relocated["output_root"] = ".cache/provider-output"
    save(payload / "portable-plan.json", relocated)
    inventory = {
        item.relative_to(payload).as_posix(): sha256(item)
        for item in sorted(payload.rglob("*"))
        if item.is_file()
    }
    manifest = {
        "schema": "hung-provider-payload-v1",
        "code_commit": plan["code_commit"],
        "parent_plan_sha256": plan_sha,
        "parent_shards_sha256": shards_sha,
        "input_archive_sha256": inputs_sha,
        "files": inventory,
        "relocation": "Paths only; all jobs, seeds, configs and checkpoint bytes preserved",
    }
    save(payload / "payload-manifest.json", manifest)
    archive = destination / "provider-payload.zip.bin"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as stream:
        for source in sorted(payload.rglob("*")):
            if source.is_file():
                stream.write(source, source.relative_to(payload).as_posix())
    with zipfile.ZipFile(archive) as stream:
        safe_members(stream)
    result = {
        "archive_sha256": sha256(archive),
        "archive_bytes": archive.stat().st_size,
        "payload_manifest_sha256": sha256(payload / "payload-manifest.json"),
        "parent_plan_sha256": plan_sha,
        "parent_shards_sha256": shards_sha,
    }
    save(destination / "transport.json", result)
    return result


def materialize(archive: Path, archive_sha: str, destination: Path) -> tuple[Path, Path]:
    """Create a clean pinned checkout; reject damaged/unsafe transport before extraction."""
    destination = destination.resolve()
    check(sha256(archive) == archive_sha, "Transport SHA mismatch")
    check(not destination.exists(), "Destination already exists; preserve it")
    with zipfile.ZipFile(archive) as stream:
        names = safe_members(stream)
        manifest = json.loads(stream.read("payload-manifest.json"))
        check(
            set(names) == set(manifest["files"]) | {"payload-manifest.json"},
            "Payload inventory differs",
        )
        for name, digest in manifest["files"].items():
            check(
                hashlib.sha256(stream.read(name)).hexdigest() == digest,
                f"Payload SHA mismatch: {name}",
            )
        destination.mkdir(parents=True, exist_ok=False)
        payload = destination / "payload"
        stream.extractall(payload)
    repo = destination / "repo"
    subprocess.run(
        ["git", "clone", "--no-checkout", str(payload / "code.bundle"), str(repo)], check=True
    )
    subprocess.run(["git", "checkout", "--detach", manifest["code_commit"]], cwd=repo, check=True)
    shutil.copytree(payload / ".cache", repo / ".cache")
    with zipfile.ZipFile(payload / "inputs.zip") as stream:
        safe_members(stream)
        stream.extractall(repo)
    plan = json.loads((payload / "portable-plan.json").read_bytes())
    for spec in [
        *plan["configs"],
        plan["selection"],
        *(j[r] for j in plan["jobs"] for r in ("source", "target") if j[r]),
    ]:
        spec["path"] = str(repo / spec["path"])
    plan["input_base"] = str(repo / plan["input_base"])
    plan["output_root"] = str(repo / plan["output_root"])
    plan_path = repo / ".cache/provider/plan.json"
    save(plan_path, plan)
    shards = json.loads((payload / "parent-shards.json").read_bytes())
    shards["plan_sha256"] = sha256(plan_path)
    shards_path = repo / ".cache/provider/shards.json"
    save(shards_path, shards)
    save(
        destination / "derivation.json",
        {
            "parent_plan_sha256": manifest["parent_plan_sha256"],
            "parent_shards_sha256": manifest["parent_shards_sha256"],
            "provider_plan_sha256": sha256(plan_path),
            "provider_shards_sha256": sha256(shards_path),
            "code_commit": manifest["code_commit"],
            "transport_sha256": archive_sha,
        },
    )
    return repo, plan_path


def execute_shard(repo: Path, shard_id: str, evidence: Path) -> dict:
    """Run one explicit shard, verify receipts, then CRC-check its complete output ZIP."""
    repo = repo.resolve()
    check(shard_id != "pilot_0000", "Completed local pilot must not execute again")
    plan_path = repo / ".cache/provider/plan.json"
    shards_path = repo / ".cache/provider/shards.json"
    shards = json.loads(shards_path.read_bytes())
    check(shard_id in {s["id"] for s in shards["shards"]}, "Unknown shard")
    evidence.mkdir(parents=True, exist_ok=False)
    command = [
        sys.executable,
        "-u",
        "-m",
        "experiments.supporting_pipeline.dispatch_matched",
        "--plan",
        str(plan_path),
        "--plan-sha256",
        sha256(plan_path),
        "--shards",
        str(shards_path),
        "--shards-sha256",
        sha256(shards_path),
        "--shard-id",
        shard_id,
    ]
    start = time.perf_counter()
    environment = {**os.environ, "PYTHONUTF8": "1"}
    output = repo / ".cache/provider-output"
    execute = command + ["--execute"] + (["--resume"] if output.exists() else [])
    with (evidence / "execute.log").open("x", encoding="utf-8") as log:
        result = subprocess.run(
            execute, cwd=repo, env=environment, stdout=log, stderr=subprocess.STDOUT, check=False
        )
    record = {
        "shard_id": shard_id,
        "exit_code": result.returncode,
        "wall_seconds": time.perf_counter() - start,
        "ended_at_utc": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": sha256(plan_path),
        "shards_sha256": sha256(shards_path),
    }
    save(evidence / "execution.json", record)
    check(result.returncode == 0, "Shard failed; preserve partial outputs and logs")
    with (evidence / "verify.log").open("x", encoding="utf-8") as log:
        verified = subprocess.run(
            command + ["--resume", "--verify-only"],
            cwd=repo,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    check(verified.returncode == 0, "Receipt verification failed")
    archive = evidence / "artifacts.zip"
    job_ids = next(s["job_ids"] for s in shards["shards"] if s["id"] == shard_id)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as stream:
        for job in job_ids:
            for kind in ("jobs", "receipts", "logs"):
                for source in sorted((output / kind / job).rglob("*")):
                    if source.is_file():
                        stream.write(source, source.relative_to(output).as_posix())
        stream.write(output / "dispatch_identity.json", "dispatch_identity.json")
    with zipfile.ZipFile(archive) as stream:
        safe_members(stream)
    receipt = {
        **record,
        "job_ids": job_ids,
        "local_verify_exit_code": verified.returncode,
        "artifact_bytes": archive.stat().st_size,
        "artifact_sha256": sha256(archive),
        "crc": "passed",
        "remote_readback": "pending",
        "peer_acceptance": "pending",
    }
    save(evidence / "receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    pack = sub.add_parser("package")
    for name in ("repo", "plan", "shards", "inputs", "destination"):
        pack.add_argument(f"--{name}", type=Path, required=True)
    for name in ("plan-sha", "shards-sha", "inputs-sha"):
        pack.add_argument(f"--{name}", required=True)
    unpack = sub.add_parser("materialize")
    unpack.add_argument("--archive", type=Path, required=True)
    unpack.add_argument("--archive-sha", required=True)
    unpack.add_argument("--destination", type=Path, required=True)
    run = sub.add_parser("execute-shard")
    run.add_argument("--repo", type=Path, required=True)
    run.add_argument("--shard-id", required=True)
    run.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "package":
        print(
            json.dumps(
                package(
                    args.repo,
                    args.plan,
                    args.plan_sha,
                    args.shards,
                    args.shards_sha,
                    args.inputs,
                    args.inputs_sha,
                    args.destination,
                )
            )
        )
    elif args.action == "materialize":
        repo, plan = materialize(args.archive, args.archive_sha, args.destination)
        print(json.dumps({"repo": str(repo), "plan": str(plan)}))
    else:
        print(json.dumps(execute_shard(args.repo, args.shard_id, args.evidence)))


if __name__ == "__main__":
    main()
