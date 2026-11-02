"""CPU-only, immutable result snapshots from completed fixed local shards."""

from __future__ import annotations

import argparse
import json
import time
import zipfile
from pathlib import Path

from experiments.hung_sprint2.dispatch_state import atomic_create, exclusive_lock
from tools.hung_result_report import publish_report
from tools.hung_results import aggregate_results, build_catalog, file_sha, verified_file


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def inside(path: Path, root: Path) -> Path:
    require(path.resolve().is_relative_to(root.resolve()), "Path outside project")
    require(not path.is_symlink(), "Symlink refused")
    return path


def pin(path: Path, root: Path) -> dict:
    inside(path, root)
    return {"path": str(path.resolve()), "sha256": file_sha(path)}


def authenticate(config: dict, root: Path) -> tuple[dict, dict, dict, list[str]]:
    """Bind the reporter to existing plan, routes and code; never launch training."""
    require(config["schema"] == "hung-result-worker-v1", "Unexpected reporter config")
    for source in config["sources"]:
        verified_file(source, root)
    require(
        any(Path(p["path"]).resolve() == Path(__file__).resolve() for p in config["sources"]),
        "Reporter source pin missing",
    )
    spec = json.loads(verified_file(config["collection_spec"], root).read_bytes())
    queue = json.loads(verified_file(config["queue"], root).read_bytes())
    plan = json.loads(verified_file(spec["plan"], root).read_bytes())
    partition = json.loads(verified_file(spec["partition"], root).read_bytes())
    require(plan["scope"] == "development_only", "Development only")
    require(
        queue["plan_sha256"] == partition["plan_sha256"] == spec["plan"]["sha256"]
        and queue["partition_sha256"] == spec["partition"]["sha256"],
        "Queue/plan/partition binding differs",
    )
    base = [s["id"] for s in spec["completed_shards"]]
    require(len(base) == len(set(base)), "Duplicate base shard")
    pending = [s for s in queue["pending_local_shards"] if s not in base]
    require(
        len(pending) == len(set(pending))
        and all(queue["routes"].get(s) == "local" for s in pending),
        "Duplicate or foreign report assignment",
    )
    require(30 <= config["poll_seconds"] <= 3600, "Poll interval out of bounds")
    require(0 < config["timeout_seconds"] <= 48 * 3600, "Reporter deadline out of bounds")
    inside(Path(config["executor_evidence"]), root)
    return spec, plan, partition, pending


def completed_shard(
    folder: Path, shard: dict, plan_sha: str, partition_sha: str, root: Path
) -> dict | None:
    """A receipt is adopted only with exact jobs, verification exit and SHA/CRC."""
    inside(folder, root)
    for terminal in ("execute-exit.json", "verify-exit.json"):
        path = folder / terminal
        if path.exists():
            require(json.loads(path.read_bytes())["exit_code"] == 0, f"Failed {terminal}")
    receipt_path = folder / "receipt.json"
    if not receipt_path.exists():
        return None
    receipt = json.loads(receipt_path.read_bytes())
    require((folder / "execute-exit.json").is_file(), "Missing execution terminal")
    require(
        (receipt["shard_id"], receipt["plan_sha256"], receipt["partition_sha256"])
        == (shard["id"], plan_sha, partition_sha),
        "Shard receipt provenance differs",
    )
    require(receipt["job_ids"] == shard["job_ids"], "Shard jobs differ")
    require(receipt["crc"] == "passed", "Executor CRC not passed")
    verify_path = folder / "verify-exit.json"
    require(verify_path.is_file(), "Missing verifier terminal")
    require(json.loads(verify_path.read_bytes())["exit_code"] == 0, "Verifier failed")
    archive = folder / "artifacts.zip"
    inside(archive, root)
    require(
        archive.stat().st_size == receipt["artifact_bytes"]
        and file_sha(archive) == receipt["artifact_sha256"],
        "Archive size/SHA differs",
    )
    with zipfile.ZipFile(archive) as stream:
        require(stream.testzip() is None, "Archive CRC differs")
    return {
        "id": shard["id"],
        "verify_exit": pin(verify_path, root),
        "receipt": pin(receipt_path, root),
        "archive": pin(archive, root),
    }


def verify_snapshot(folder: Path, expected_inputs: list[dict], root: Path) -> dict:
    """Never overwrite a partial snapshot or trust a receipt without readback."""
    receipt_path = folder / "receipt.json"
    require(receipt_path.is_file(), "Partial report snapshot; preserve and investigate")
    receipt = json.loads(receipt_path.read_bytes())
    require(receipt["inputs"] == expected_inputs, "Report inputs changed")
    expected = {"receipt.json"}
    for artifact in receipt["files"]:
        path = verified_file(artifact, root)
        require(path.is_relative_to(folder.resolve()), "Report member outside snapshot")
        expected.add(path.relative_to(folder.resolve()).as_posix())
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    require(actual == expected, "Snapshot inventory differs")
    return receipt


def snapshot(config: dict, root: Path, output: Path) -> tuple[bool, bool]:
    spec, _, partition, pending = authenticate(config, root)
    executor = Path(config["executor_evidence"])
    require(not (executor / "failure.json").exists(), "Executor reported failure")
    shards = {s["id"]: s for s in partition["shards"]}
    ready = []
    for shard_id in pending:
        record = completed_shard(
            executor / shard_id,
            shards[shard_id],
            spec["plan"]["sha256"],
            spec["partition"]["sha256"],
            root,
        )
        if record:
            ready.append(record)
    if not ready:
        return False, not pending
    name = "through-" + ready[-1]["id"]
    folder = output / name
    if folder.exists():
        verify_snapshot(folder, ready, root)
        return False, len(ready) == len(pending)
    folder.mkdir()
    spec["completed_shards"] += [{"id": r["id"], "verify_exit": r["verify_exit"]} for r in ready]
    atomic_create(folder / "collection.json", spec)
    catalog = build_catalog(spec, root)
    catalog["catalog_sha256"] = file_sha(folder / "collection.json")
    atomic_create(folder / "catalog.json", catalog)
    result = aggregate_results(catalog, root)
    result["catalog_sha256"] = file_sha(folder / "catalog.json")
    atomic_create(folder / "results.json", result)
    publish_report(result, folder / "report", file_sha(folder / "results.json"))
    files = [pin(p, root) for p in sorted(folder.rglob("*")) if p.is_file()]
    receipt = {
        "schema": "hung-local-result-snapshot-v1",
        "scope": "development_only",
        "inputs": ready,
        "files": files,
        "counts": result["counts"],
        "remote_readback": "Not inferred from local reporting",
        "review": "Independent scientific acceptance and Final lock still pending",
    }
    atomic_create(folder / "receipt.json", receipt)
    verify_snapshot(folder, ready, root)
    print(json.dumps({"snapshot": str(folder), "counts": result["counts"]}), flush=True)
    return True, len(ready) == len(pending)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--watch", action="store_true", help="Bounded CPU-only receipt watcher")
    args = parser.parse_args()
    config = json.loads(
        verified_file(
            {"path": str(args.config), "sha256": args.config_sha256}, args.project_root
        ).read_bytes()
    )
    inside(args.output, args.project_root)
    args.output.mkdir(exist_ok=True)
    with exclusive_lock(args.output):
        require(not (args.output / "failure.json").exists(), "Prior reporting failure preserved")
        identity = {
            "config_sha256": args.config_sha256,
            "scope": "development_only",
            "role": "CPU receipt verification and immutable reports; no training or publication",
        }
        identity_path = args.output / "identity.json"
        if identity_path.exists():
            require(json.loads(identity_path.read_bytes()) == identity, "Reporter identity changed")
        else:
            atomic_create(identity_path, identity)
        print(json.dumps({"reporter_started": identity}), flush=True)
        started = time.monotonic()
        while True:
            try:
                _, complete = snapshot(config, args.project_root, args.output)
                if complete:
                    atomic_create(
                        args.output / "complete.json",
                        {"scope": "development_only", "all_local_report_snapshots_complete": True},
                    )
                    return
                if not args.watch:
                    return
                require(time.monotonic() - started < config["timeout_seconds"], "Reporter timeout")
            except Exception as error:
                atomic_create(args.output / "failure.json", {"error": str(error)})
                raise
            time.sleep(config["poll_seconds"])


if __name__ == "__main__":
    main()
