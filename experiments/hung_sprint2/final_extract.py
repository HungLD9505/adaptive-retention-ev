"""Materialize an authenticated Final input ZIP only after its exact lock exists."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from experiments.hung_sprint2.dispatch_matched import require
from experiments.hung_sprint2.dispatch_state import atomic_create
from experiments.hung_sprint2.final_lock import ROOT, _project_path, validate_lock

REQUIRED_FILES = {
    "manifest.json",
    "training.jsonl",
    "entities.jsonl",
    "forecasts.jsonl",
    "labels.jsonl",
    "schedule.jsonl",
}


def _receipt_path(lock_sha256: str) -> Path:
    return ROOT / ".cache" / "hung-final-input-receipts" / f"{lock_sha256}.json"


def _member_path(name: str) -> Path:
    pure = PurePosixPath(name)
    require(
        name
        and "\\" not in name
        and ":" not in name
        and not pure.is_absolute()
        and all(part not in {"", ".", ".."} for part in name.rstrip("/").split("/"))
        and pure.as_posix() == name.rstrip("/"),
        f"Unsafe Final ZIP member: {name}",
    )
    return _project_path(str(ROOT / pure))


def materialize_locked_inputs(
    lock_path: Path,
    lock_sha256: str,
    *,
    check_code: bool = True,
    provider_initial_free_bytes: int | None = None,
) -> dict:
    """Authenticate the lock first, then create each pinned input byte exactly once."""
    context = validate_lock(lock_path, lock_sha256, check_code=check_code, verify_input_runs=False)
    roots = {_project_path(row["input_run"]) for row in context["jobs"]}
    receipt = _receipt_path(lock_sha256)
    allowed_parent = (ROOT / "data" / "inputs").resolve()
    require(
        all(root.is_relative_to(allowed_parent) for root in roots),
        "Final input runs must be below data/inputs",
    )
    archive = _project_path(context["lock"]["input"]["path"])
    try:
        with ZipFile(archive) as source:
            infos = source.infolist()
            require(infos, "Final ZIP has no members")
            files: list[tuple[Path, object]] = []
            seen: set[Path] = set()
            for info in infos:
                dest = _member_path(info.filename)
                require(
                    stat.S_IFMT(info.external_attr >> 16)
                    not in {stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO, stat.S_IFSOCK},
                    "Unsafe Final ZIP member type",
                )
                require(
                    any(dest.is_relative_to(root) for root in roots)
                    or (info.is_dir() and any(root.is_relative_to(dest) for root in roots)),
                    "Unexpected Final ZIP member",
                )
                if info.is_dir():
                    continue
                require(dest not in seen, "Duplicate Final ZIP member")
                seen.add(dest)
                files.append((dest, info))
            for root in roots:
                require(
                    REQUIRED_FILES <= {dest.name for dest in seen if dest.parent == root},
                    f"Final input run has missing ZIP files: {root}",
                )
            require(
                all(not dest.exists() for dest in seen)
                and all(not root.exists() for root in roots),
                "Final input extraction would overwrite existing data",
            )
            require(not receipt.exists(), "Final input extraction receipt already exists")
            total = sum(info.file_size for _, info in files)
            resources = context["lock"]["resources"]
            current_free = shutil.disk_usage(
                allowed_parent if allowed_parent.exists() else ROOT
            ).free
            initial_free = (
                current_free if provider_initial_free_bytes is None else provider_initial_free_bytes
            )
            require(
                resources["estimated_output_bytes"] >= total
                and type(initial_free) is int
                and initial_free
                >= resources["min_free_bytes"] + resources["estimated_output_bytes"]
                and current_free >= resources["min_free_bytes"],
                "Final input extraction lacks locked capacity",
            )
            require(source.testzip() is None, "Final ZIP CRC differs")
            records = []
            for dest, info in files:
                require(
                    not any(
                        parent.is_symlink()
                        for parent in dest.parents
                        if parent.is_relative_to(ROOT)
                    ),
                    "Final input path contains a symlink",
                )
                dest.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                with source.open(info) as incoming, dest.open("xb") as outgoing:
                    while chunk := incoming.read(1024 * 1024):
                        outgoing.write(chunk)
                        digest.update(chunk)
                records.append(
                    {
                        "path": str(dest.relative_to(ROOT)),
                        "bytes": info.file_size,
                        "crc32": f"{info.CRC:08x}",
                        "sha256": digest.hexdigest(),
                    }
                )
    except BadZipFile as error:
        raise ValueError("Final ZIP CRC/structure is invalid") from error
    verified = validate_lock(lock_path, lock_sha256, check_code=check_code)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    atomic_create(
        receipt,
        {
            "schema": "hung-final-input-extraction-v1",
            "lock_sha256": lock_sha256,
            "archive_sha256": context["lock"]["input"]["sha256"],
            "files": records,
        },
    )
    return {
        "input_runs_verified": verified["input_runs_verified"],
        "files": len(records),
        "receipt": str(receipt),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--lock-sha256", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(materialize_locked_inputs(args.lock, args.lock_sha256), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
