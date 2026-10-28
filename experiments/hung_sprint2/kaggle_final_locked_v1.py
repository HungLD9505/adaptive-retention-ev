"""Prepared Kaggle script for one exact, lock-bound Hùng Final jobset.

No provider submission occurs by importing this file. The explicit --run-all
route is only for a reviewed full-jobset lock with fresh provider capacity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SCHEMA = "hung-final-provider-handoff-v1"
WORKING = Path("/kaggle/working")
MOUNT = Path("/kaggle/input")
MIN_GPU_MEMORY_BYTES = 4 * 1024**3
MAX_QUOTA_AGE_SECONDS = 600


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), f"Missing/unsafe provider file: {path}")
    with path.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": path.stat().st_size, "sha256": sha}


def _unique_json(path: Path) -> dict:
    def pairs(items: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate provider manifest key: {key}")
            result[key] = value
        return result

    result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    require(isinstance(result, dict), "Provider manifest must be an object")
    return result


def _relative(name: str) -> Path:
    posix = PurePosixPath(name)
    require(
        isinstance(name, str)
        and name
        and "\\" not in name
        and ":" not in name
        and not posix.is_absolute()
        and posix.as_posix() == name
        and all(piece not in {"", ".", ".."} for piece in name.split("/")),
        f"Unsafe provider path: {name}",
    )
    return Path(*posix.parts)


def inspect_handoff(
    mount: Path, manifest_sha256: str, dataset_version: str, wrapper_path: Path
) -> tuple[Path, dict]:
    """Read no role file; authenticate all mounted bytes before checkout."""
    require(re.fullmatch(r"[0-9a-f]{64}", manifest_sha256) is not None, "Invalid manifest SHA")
    matches = [
        path
        for path in mount.rglob("final-handoff-manifest.json")
        if digest(path)["sha256"] == manifest_sha256
    ]
    require(len(matches) == 1, "Pinned Final handoff Dataset missing or ambiguous")
    path = matches[0]
    root, manifest = path.parent, _unique_json(path)
    require(
        set(manifest)
        == {"schema", "dataset_version", "code_commit", "lock_sha256", "wrapper_sha256", "files"}
        and manifest["schema"] == SCHEMA
        and manifest["dataset_version"] == dataset_version
        and re.fullmatch(r"[0-9a-f]{40}", manifest["code_commit"]) is not None
        and re.fullmatch(r"[0-9a-f]{64}", manifest["lock_sha256"]) is not None
        and digest(wrapper_path)["sha256"] == manifest["wrapper_sha256"],
        "Final handoff identity/source differs",
    )
    files = manifest["files"]
    require(
        isinstance(files, dict) and "code.bundle" in files and "lock.json" in files,
        "Provider handoff lacks code bundle or lock",
    )
    require(
        {item.name for item in root.iterdir()}
        == {"final-handoff-manifest.json"} | {Path(name).name for name in files},
        "Provider handoff has extra or missing files",
    )
    targets = []
    for name, pin in files.items():
        _relative(name)
        require(
            isinstance(pin, dict)
            and set(pin) == {"bytes", "sha256", "target"}
            and digest(root / name) == {"bytes": pin["bytes"], "sha256": pin["sha256"]},
            f"Final handoff bytes differ: {name}",
        )
        if name == "code.bundle":
            require(pin["target"] is None, "Code bundle cannot be an overlay")
        else:
            target = _relative(pin["target"])
            require(target.parts[0] == ".cache", "Final overlay must be Git-ignored .cache")
            targets.append(target)
    require(len(targets) == len(set(targets)), "Duplicate Final overlay target")
    require(files["lock.json"]["sha256"] == manifest["lock_sha256"], "Final lock SHA differs")
    lock = _unique_json(root / "lock.json")
    require(
        lock.get("schema") == "hung-final-lock-v1"
        and lock.get("scope") == "final_only"
        and lock.get("code_commit") == manifest["code_commit"],
        "Final lock/code scope differs",
    )
    return root, manifest


def _quota_gate(args: argparse.Namespace, resources: dict, free_bytes: int) -> None:
    observed = datetime.fromisoformat(args.quota_observed_utc.replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - observed).total_seconds()
    require(0 <= age <= MAX_QUOTA_AGE_SECONDS, "Provider quota observation is stale")
    require(
        resources["provider"] == "kaggle"
        and resources["device"] == "cuda"
        and resources["estimated_gpu_seconds"] > 0
        and args.available_gpu_seconds >= resources["estimated_gpu_seconds"] + 3600
        and args.available_session_seconds >= resources["estimated_gpu_seconds"] + 3600,
        "Measured Kaggle GPU/session quota does not cover the exact jobset",
    )
    require(
        args.available_output_bytes >= resources["estimated_output_bytes"]
        and free_bytes >= resources["min_free_bytes"] + resources["estimated_output_bytes"],
        "Kaggle output/free-space quota does not cover the exact jobset",
    )
    import torch

    require(torch.cuda.is_available(), "Kaggle CUDA GPU is unavailable")
    require(
        torch.cuda.get_device_properties(0).total_memory >= MIN_GPU_MEMORY_BYTES,
        "Kaggle GPU memory is below pinned minimum",
    )


def _checkout(root: Path, manifest: dict, checkout: Path) -> tuple[Path, Path]:
    require(not checkout.exists(), "Final checkout/output already exists")
    subprocess.run(
        ["git", "clone", "--no-checkout", str(root / "code.bundle"), str(checkout)],
        check=True,
    )
    subprocess.run(
        ["git", "checkout", "--detach", manifest["code_commit"]], cwd=checkout, check=True
    )
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
    require(head == manifest["code_commit"], "Final checkout commit differs")
    for name, pin in manifest["files"].items():
        if name == "code.bundle":
            continue
        target = checkout / _relative(pin["target"])
        require(not target.exists(), "Final overlay would overwrite existing bytes")
        require(
            not any(
                parent.is_symlink() for parent in target.parents if parent.is_relative_to(checkout)
            ),
            "Final overlay path contains a symlink",
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        with (root / name).open("rb") as source, target.open("xb") as output:
            shutil.copyfileobj(source, output, 1024 * 1024)
        require(
            digest(target) == {key: pin[key] for key in ("bytes", "sha256")},
            "Final overlay copy differs",
        )
    return checkout, checkout / _relative(manifest["files"]["lock.json"]["target"])


def run_all(args: argparse.Namespace) -> dict:
    require(args.run_all, "Explicit --run-all is required; partial acceptance is unsupported")
    root, manifest = inspect_handoff(
        args.mount, args.manifest_sha256, args.dataset_version, args.wrapper_path
    )
    lock = _unique_json(root / "lock.json")
    _quota_gate(args, lock["resources"], shutil.disk_usage(args.working).free)
    checkout = args.working / f"hung-final-{manifest['lock_sha256'][:12]}"
    repo, lock_path = _checkout(root, manifest, checkout)
    os.chdir(repo)
    sys.path.insert(0, str(repo))
    from experiments.hung_sprint2.final_archive import create_archive
    from experiments.hung_sprint2.final_dispatch import dispatch
    from experiments.hung_sprint2.final_extract import materialize_locked_inputs
    from experiments.hung_sprint2.final_lock import validate_lock
    from experiments.hung_sprint2.final_transport import prepare_upload

    lock_sha = manifest["lock_sha256"]
    materialize_locked_inputs(lock_path, lock_sha)
    context = validate_lock(lock_path, lock_sha)
    require(
        len(context["jobs"]) == context["lock"]["jobset"]["count"],
        "Final exact jobset count differs",
    )
    for job in context["jobs"]:
        result = dispatch(context, run=True, job_id=job["job_id"])
        require(result["verified"] == 1, f"Final job did not verify: {job['job_id']}")
    complete = dispatch(context, run=False)
    require(complete["verified"] == len(context["jobs"]), "Final jobset remains partial")
    archive = args.working / "hung-final-artifacts" / "archive.zip"
    archived = create_archive(context, archive)
    packet = args.working / "hung-final-artifacts" / "transport-packet"
    prepared = prepare_upload(context, lock_path, archive, packet)
    receipt = {
        "schema": "hung-final-kaggle-session-v1",
        "status": "LOCAL_ARCHIVE_AND_PACKET_READY",
        "lock_sha256": lock_sha,
        "jobs": len(context["jobs"]),
        "archive": archived["archive"],
        "transport": prepared,
        "remote_readback": "pending",
    }
    with (args.working / "hung-final-artifacts" / "session-receipt.json").open("x") as stream:
        json.dump(receipt, stream, sort_keys=True)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--quota-observed-utc", required=True)
    parser.add_argument("--available-gpu-seconds", type=int, required=True)
    parser.add_argument("--available-session-seconds", type=int, required=True)
    parser.add_argument("--available-output-bytes", type=int, required=True)
    parser.add_argument("--run-all", action="store_true")
    parser.add_argument("--mount", type=Path, default=MOUNT)
    parser.add_argument("--working", type=Path, default=WORKING)
    parser.add_argument("--wrapper-path", type=Path, default=Path(__file__).resolve())
    args = parser.parse_args(argv)
    print(json.dumps(run_all(args), sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
