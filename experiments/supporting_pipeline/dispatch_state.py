"""Create-only receipts, OS locks and fixed partitions for Development dispatch.

Receipts authenticate bytes and execution identity; they are not peer approval.
Locks are released by the OS after interruption, never inferred from a PID file.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ev_inputs.hourly_reader import sha256_file


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def atomic_create(path: Path, value: dict) -> None:
    """Publish a fully fsynced JSON file atomically without replacing any file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def exclusive_lock(root: Path) -> Iterator[None]:
    """Hold a nonblocking OS lock; a surviving lock file alone is harmless."""
    path = root / ".dispatch.lock"
    require(not path.is_symlink(), f"Symlink lock refused: {path}")
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError(f"Dispatch is already locked: {root}") from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def inventory(root: Path) -> dict:
    """Hash the complete stage tree; reject symlinks and special files."""
    require(root.is_dir() and not root.is_symlink(), f"Missing/unsafe stage: {root}")
    result = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"Symlink artifact refused: {path}")
        if path.is_dir():
            continue
        require(path.is_file(), f"Non-file artifact refused: {path}")
        result[path.relative_to(root).as_posix()] = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    require(bool(result), f"Empty stage output: {root}")
    return result


def stage_receipt(binding: dict, output: Path, log: Path) -> dict:
    """Capture all bytes after the stage verifier accepted its manifest/state."""
    require(log.is_file() and not log.is_symlink(), f"Missing/unsafe log: {log}")
    return {
        "schema": "hung-dispatch-stage-receipt-v1",
        "binding": binding,
        "files": inventory(output),
        "log": {"bytes": log.stat().st_size, "sha256": sha256_file(log)},
    }


def verify_receipt(path: Path, expected: dict, read_json: Callable[[Path], dict]) -> None:
    require(path.is_file() and not path.is_symlink(), f"Missing/unsafe receipt: {path}")
    require(read_json(path) == expected, f"Receipt identity/output mismatch: {path}")


def make_shards(plan_sha256: str, job_ids: list[str], jobs_per_shard: int) -> dict:
    """Partition sorted job IDs without using forecasts, labels or scores."""
    require(type(jobs_per_shard) is int and jobs_per_shard > 0, "Invalid shard size")
    require(len(job_ids) == len(set(job_ids)) and bool(job_ids), "Invalid job IDs")
    ordered = sorted(job_ids)
    return {
        "schema": "hung-dispatch-shards-v1",
        "plan_sha256": plan_sha256,
        "shards": [
            {
                "id": f"shard_{index // jobs_per_shard:04d}",
                "job_ids": ordered[index : index + jobs_per_shard],
            }
            for index in range(0, len(ordered), jobs_per_shard)
        ],
    }


def select_shard(spec: dict, plan_sha256: str, job_ids: list[str], shard_id: str) -> list[str]:
    """Require a complete, disjoint partition bound to the exact parent plan."""
    require(
        set(spec) == {"schema", "plan_sha256", "shards"}
        and spec["schema"] == "hung-dispatch-shards-v1"
        and spec["plan_sha256"] == plan_sha256,
        "Shard plan identity differs",
    )
    all_jobs, ids, selected = [], set(), None
    for row in spec["shards"]:
        require(set(row) == {"id", "job_ids"}, "Shard fields differ")
        key, jobs = row["id"], row["job_ids"]
        require(isinstance(key, str) and key.isidentifier() and key not in ids, "Invalid shard ID")
        require(isinstance(jobs, list) and bool(jobs), "Empty/invalid shard")
        require(all(isinstance(job, str) for job in jobs), "Invalid shard job ID")
        ids.add(key)
        all_jobs.extend(jobs)
        if key == shard_id:
            selected = jobs
    require(
        len(all_jobs) == len(set(all_jobs)) and set(all_jobs) == set(job_ids),
        "Shard partition has duplicate, missing or unknown jobs",
    )
    require(selected is not None, "Unknown shard ID")
    return selected


def object_sha256(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()
