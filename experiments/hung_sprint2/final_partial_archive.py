"""Create-only partial Final checkpoint archive and exact restore under one full lock."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from experiments.hung_sprint2.dispatch_state import atomic_create
from experiments.hung_sprint2.final_archive import (
    _expected_stages,
    _inventory,
    create_archive,
    readback_archive,
    require,
)
from experiments.hung_sprint2.final_lock import _project_path

SCHEMA = "hung-final-partial-checkpoint-v1"


def _subset(context: dict, ids: list[str]) -> tuple[list[dict], list[dict]]:
    full_jobs, full_plan = context["jobs"], context["plan"]
    require(
        isinstance(ids, list) and ids and ids == sorted(set(ids)) and len(ids) < len(full_jobs),
        "Final checkpoint must be a sorted proper completed-job subset",
    )
    require(
        len(full_jobs) == len(full_plan)
        and [row["job_id"] for row in full_jobs] == [row["job_id"] for row in full_plan],
        "Full Final jobset/plan differs",
    )
    selected = set(ids)
    require(selected <= {row["job_id"] for row in full_jobs}, "Unknown Final checkpoint job")
    pairs = [
        (job, planned)
        for job, planned in zip(full_jobs, full_plan, strict=True)
        if job["job_id"] in selected
    ]
    return [job for job, _ in pairs], [planned for _, planned in pairs]


def _lock_pins(context: dict) -> tuple[str, str]:
    lock = context["lock"]
    jobset, plan = lock["jobset"], lock["execution_plan"]
    require(
        _project_path(lock["output_root"]) == context["output_root"]
        and jobset["count"] == len(context["jobs"])
        and all(
            isinstance(reference["sha256"], str) and len(reference["sha256"]) == 64
            for reference in (jobset, plan)
        ),
        "Full Final lock jobset/plan pins differ",
    )
    return jobset["sha256"], plan["sha256"]


def _checkpoint(package: Path) -> dict:
    require(package.is_dir() and not package.is_symlink(), "Final checkpoint package is absent")
    require(
        {item.name for item in package.iterdir()} == {"checkpoint.json", "completed-stages.zip"},
        "Final checkpoint package has missing/extra members",
    )
    require(
        all(
            (package / name).is_file() and not (package / name).is_symlink()
            for name in ("checkpoint.json", "completed-stages.zip")
        ),
        "Final checkpoint package contains unsafe files",
    )
    value = json.loads((package / "checkpoint.json").read_text(encoding="utf-8"))
    require(
        set(value)
        == {
            "schema",
            "status",
            "lock_sha256",
            "full_jobset_sha256",
            "full_execution_plan_sha256",
            "full_job_count",
            "completed_job_ids",
            "archive",
        }
        and value["schema"] == SCHEMA
        and value["status"] == "PARTIAL_CHECKPOINT_ONLY_NOT_FINAL_RESULT",
        "Final checkpoint schema/status differs",
    )
    return value


def verify_partial_checkpoint(context: dict, package: Path) -> dict:
    """Read archive bytes without consulting the original output stage tree."""
    require(
        context.get("input_runs_verified") is True, "Full Final lock/input preflight is required"
    )
    record = _checkpoint(package)
    jobset_sha, plan_sha = _lock_pins(context)
    require(
        record["lock_sha256"] == context["lock_sha256"]
        and record["full_jobset_sha256"] == jobset_sha
        and record["full_execution_plan_sha256"] == plan_sha
        and record["full_job_count"] == len(context["jobs"]),
        "Final checkpoint full lock/jobset/plan binding differs",
    )
    jobs, plan = _subset(context, record["completed_job_ids"])
    archive = package / "completed-stages.zip"
    pin = record["archive"]
    require(
        set(pin) == {"bytes", "sha256"} and archive.stat().st_size == pin["bytes"],
        "Final checkpoint archive bytes differ",
    )
    verified = readback_archive(archive, pin["sha256"], context["lock_sha256"], jobs, plan)
    require(set(verified["jobs"]) == set(record["completed_job_ids"]), "Checkpoint job map differs")
    return {
        "status": "PARTIAL_CHECKPOINT_VERIFIED_NOT_FINAL_RESULT",
        "lock_sha256": context["lock_sha256"],
        "completed_jobs": len(jobs),
        "full_jobs": len(context["jobs"]),
        "job_artifacts": verified["jobs"],
    }


def create_partial_checkpoint(context: dict, ids: list[str], package: Path) -> dict:
    """Publish a checkpoint only after exact subset stage and receipt readback."""
    require(
        context.get("input_runs_verified") is True, "Full Final lock/input preflight is required"
    )
    require(not package.exists() and not package.is_symlink(), "Final checkpoint package exists")
    require(
        not package.is_relative_to(context["output_root"]), "Checkpoint cannot sit in output root"
    )
    jobs, plan = _subset(context, ids)
    jobset_sha, plan_sha = _lock_pins(context)
    package.mkdir(parents=True, exist_ok=False)
    archive = package / "completed-stages.zip"
    subset_context = {**context, "jobs": jobs, "plan": plan}
    result = create_archive(subset_context, archive)
    atomic_create(
        package / "checkpoint.json",
        {
            "schema": SCHEMA,
            "status": "PARTIAL_CHECKPOINT_ONLY_NOT_FINAL_RESULT",
            "lock_sha256": context["lock_sha256"],
            "full_jobset_sha256": jobset_sha,
            "full_execution_plan_sha256": plan_sha,
            "full_job_count": len(context["jobs"]),
            "completed_job_ids": ids,
            "archive": {
                "bytes": result["archive"]["bytes"],
                "sha256": result["archive"]["sha256"],
            },
        },
    )
    return verify_partial_checkpoint(context, package)


def restore_partial_checkpoint(context: dict, package: Path, target: Path) -> dict:
    """Create only an absent immutable output root, then verify restored stages."""
    verified = verify_partial_checkpoint(context, package)
    require(target == context["output_root"], "Restore target differs from locked output root")
    require(not target.exists() and not target.is_symlink(), "Restore target must be absent")
    require(not target.is_relative_to(package), "Restore target cannot be inside checkpoint")
    target.mkdir(parents=True, exist_ok=False)
    with ZipFile(package / "completed-stages.zip") as archive:
        for name in archive.namelist():
            if name == "index.json":
                continue
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, destination.open("xb") as sink:
                while block := source.read(1024 * 1024):
                    sink.write(block)
        index = json.loads(archive.read("index.json"))
    jobs, plan = _subset(context, _checkpoint(package)["completed_job_ids"])
    require(
        _inventory(target, _expected_stages(jobs, plan), context["lock_sha256"]) == index,
        "Restored Final stage bytes differ",
    )
    return {**verified, "status": "PARTIAL_CHECKPOINT_RESTORED_NOT_FINAL_RESULT"}
