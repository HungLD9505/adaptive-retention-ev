"""Create-only execution and byte-verified job-boundary recovery for Hùng Final."""

from __future__ import annotations

import argparse
import json
import shutil
from argparse import Namespace
from pathlib import Path

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2 import cli, single_baseline_cli
from experiments.hung_sprint2.dispatch_matched import read_json, require
from experiments.hung_sprint2.dispatch_state import (
    atomic_create,
    exclusive_lock,
    stage_receipt,
    verify_receipt,
)
from experiments.hung_sprint2.final_drift import derive_drift_reference
from experiments.hung_sprint2.final_lock import (
    CONTROLLER_METHODS,
    SINGLE_METHODS,
    _project_path,
    validate_lock,
)


def _stage_paths(root: Path, job_id: str, stage: str) -> tuple[Path, Path, Path]:
    return (
        root / "stages" / job_id / stage,
        root / "logs" / job_id / f"{stage}.json",
        root / "receipts" / job_id / f"{stage}.json",
    )


def _free_bytes(path: Path) -> int:
    ancestor = path
    while not ancestor.exists():
        ancestor = ancestor.parent
    return shutil.disk_usage(ancestor).free


def _output_tree(root: Path, expected_ids: set[str]) -> None:
    require(
        {path.name for path in root.iterdir()}
        <= {"final_lock_identity.json", ".dispatch.lock", "stages", "logs", "receipts"},
        "Unexpected Final output-root member",
    )
    for category in ("stages", "logs", "receipts"):
        directory = root / category
        if not directory.exists():
            continue
        require(directory.is_dir() and not directory.is_symlink(), "Unsafe Final output category")
        job_paths = list(directory.iterdir())
        require(
            {path.name for path in job_paths} <= expected_ids
            and all(path.is_dir() and not path.is_symlink() for path in job_paths),
            "Unexpected Final output job",
        )
        expected_members = (
            {"drift_reference", "target_init", "replay"}
            if category == "stages"
            else {"drift_reference.json", "target_init.json", "replay.json"}
        )
        for job_path in job_paths:
            require(
                {path.name for path in job_path.iterdir()} <= expected_members,
                "Unexpected Final stage/log/receipt",
            )


def _verified_stage(root: Path, job_id: str, stage: str, lock_sha: str) -> dict | None:
    output, log, receipt = _stage_paths(root, job_id, stage)
    if not any(path.exists() for path in (output, log, receipt)):
        return None
    require(
        all(path.exists() for path in (output, log, receipt)),
        "Partial Final stage requires inspection",
    )
    binding = {
        "schema": "hung-final-stage-binding-v1",
        "lock_sha256": lock_sha,
        "job_id": job_id,
        "stage": stage,
    }
    verify_receipt(receipt, stage_receipt(binding, output, log), read_json)
    manifest = read_json(output / "run_manifest.json")
    require(
        manifest.get("status") == "completed"
        and manifest.get("final_lock_sha256") == lock_sha
        and manifest.get("final_job_id") == job_id,
        "Final stage manifest/lock identity differs",
    )
    return manifest


def _namespace(values: dict, **fixed: object) -> Namespace:
    require(
        isinstance(values, dict) and not set(values) & set(fixed),
        "Final plan overrides protected arguments",
    )
    path_names = {
        "input_run",
        "source_input_run",
        "source_checkpoint",
        "target_checkpoint",
        "initial_checkpoint",
        "resume_checkpoint",
    }
    converted = {
        key: _project_path(value) if key in path_names and value is not None else value
        for key, value in values.items()
    }
    return Namespace(**converted, **fixed)


def _publish_stage(root: Path, job_id: str, stage: str, lock_sha: str, result: dict) -> None:
    output, log, receipt = _stage_paths(root, job_id, stage)
    require(result.get("status") == "completed", "Final stage did not complete")
    log.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    atomic_create(
        log,
        {
            "schema": "hung-final-stage-log-v1",
            "lock_sha256": lock_sha,
            "job_id": job_id,
            "stage": stage,
            "manifest_sha256": sha256_file(output / "run_manifest.json"),
        },
    )
    binding = {
        "schema": "hung-final-stage-binding-v1",
        "lock_sha256": lock_sha,
        "job_id": job_id,
        "stage": stage,
    }
    atomic_create(receipt, stage_receipt(binding, output, log))


def _locked_drift_reference(context: dict, job: dict) -> dict:
    reference = derive_drift_reference(job, context["lock"]["drift_reference"])
    root, lock_sha, job_id = context["output_root"], context["lock_sha256"], job["job_id"]
    prior = _verified_stage(root, job_id, "drift_reference", lock_sha)
    if prior is not None:
        require(prior.get("drift_reference") == reference, "Final Drift reference changed")
        return reference
    output, _, _ = _stage_paths(root, job_id, "drift_reference")
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "status": "completed",
        "final_lock_sha256": lock_sha,
        "final_job_id": job_id,
        "drift_reference": reference,
    }
    atomic_create(output / "run_manifest.json", result)
    _publish_stage(root, job_id, "drift_reference", lock_sha, result)
    return reference


def _run_job(context: dict, job: dict, plan: dict) -> None:
    root, lock_sha = context["output_root"], context["lock_sha256"]
    job_id, method = job["job_id"], job["method"]
    drift = _locked_drift_reference(context, job) if method == "drift" else None
    init = plan["target_init"]
    replay_present = _verified_stage(root, job_id, "replay", lock_sha)
    if replay_present is not None and init is not None:
        require(
            _verified_stage(root, job_id, "target_init", lock_sha) is not None,
            "Final replay exists without its bound initialization",
        )
    if replay_present is not None:
        return
    if init is not None:
        output, _, _ = _stage_paths(root, job_id, "target_init")
        existing = _verified_stage(root, job_id, "target_init", lock_sha)
        if existing is None:
            output.parent.mkdir(parents=True, exist_ok=True)
            args = _namespace(
                init, output=output, role="final", final_lock_sha256=lock_sha, final_job_id=job_id
            )
            result = (
                single_baseline_cli._initialize_target_only(args)
                if method == "target_only"
                else cli._target(args)
            )
            _publish_stage(root, job_id, "target_init", lock_sha, result)
        checkpoint = output / ("initial.pt" if method == "target_only" else "target_checkpoint.pt")
        require(checkpoint.is_file(), "Final initialization checkpoint is missing")
    replay_output, _, _ = _stage_paths(root, job_id, "replay")
    values = dict(plan["replay"])
    if drift is not None:
        values["drift_reference_mean"] = drift["mean"]
        values["drift_reference_scale"] = drift["scale"]
    if method in CONTROLLER_METHODS:
        values["target_checkpoint"] = str(checkpoint)
    elif method == "target_only":
        values["initial_checkpoint"] = str(checkpoint)
    replay_output.parent.mkdir(parents=True, exist_ok=True)
    args = _namespace(
        values, output=replay_output, role="final", final_lock_sha256=lock_sha, final_job_id=job_id
    )
    result = single_baseline_cli._replay(args) if method in SINGLE_METHODS else cli._replay(args)
    _publish_stage(root, job_id, "replay", lock_sha, result)


def dispatch(context: dict, *, run: bool, job_id: str | None = None) -> dict:
    require(context.get("input_runs_verified") is True, "Final input runs were not verified")
    root, lock_sha = context["output_root"], context["lock_sha256"]
    jobs = context["jobs"]
    if job_id is not None:
        require(job_id in {row["job_id"] for row in jobs}, "Unknown Final job ID")
    selected = [
        (job, plan)
        for job, plan in zip(jobs, context["plan"], strict=True)
        if job_id is None or job["job_id"] == job_id
    ]
    if not run and not root.exists():
        return {
            "status": "not_started",
            "jobs": len(selected),
            "total_locked_jobs": len(jobs),
            "verified": 0,
            "coverage_status": context["coverage_status"],
        }
    if run:
        require(
            _free_bytes(root)
            >= context["lock"]["resources"]["min_free_bytes"]
            + context["lock"]["resources"]["estimated_output_bytes"],
            "Final output reserve plus locked output budget is unavailable",
        )
        root.mkdir(parents=True, exist_ok=True)
    require(root.is_dir() and not root.is_symlink(), "Final output root is missing/unsafe")
    identity = root / "final_lock_identity.json"
    if run and not identity.exists():
        require(not any(root.iterdir()), "Nonempty Final output root lacks lock identity")
        atomic_create(
            identity, {"schema": "hung-final-output-identity-v1", "lock_sha256": lock_sha}
        )
    require(
        read_json(identity) == {"schema": "hung-final-output-identity-v1", "lock_sha256": lock_sha},
        "Final output root lock differs",
    )
    _output_tree(root, {row["job_id"] for row in jobs})
    verified = 0
    with exclusive_lock(root):
        # Authenticate every previously published stage before starting even
        # one missing job; a late corrupt receipt cannot hide behind order.
        for existing_job, existing_plan in zip(jobs, context["plan"], strict=True):
            drift = _verified_stage(root, existing_job["job_id"], "drift_reference", lock_sha)
            initial = _verified_stage(root, existing_job["job_id"], "target_init", lock_sha)
            replay = _verified_stage(root, existing_job["job_id"], "replay", lock_sha)
            require(
                (existing_plan["target_init"] is not None or initial is None)
                and (replay is None or existing_plan["target_init"] is None or initial is not None),
                "Final stage lineage is incomplete or unexpected",
            )
            require(
                (existing_job["method"] == "drift" or drift is None)
                and (replay is None or existing_job["method"] != "drift" or drift is not None),
                "Final Drift stage lineage is incomplete or unexpected",
            )
            if drift is not None:
                require(
                    drift.get("drift_reference")
                    == derive_drift_reference(existing_job, context["lock"]["drift_reference"]),
                    "Final Drift reference changed",
                )
        for job, plan in selected:
            if run:
                require(
                    _free_bytes(root) >= context["lock"]["resources"]["min_free_bytes"],
                    "Final output reserve fell below lock",
                )
                _run_job(context, job, plan)
            elif plan["target_init"] is not None:
                _verified_stage(root, job["job_id"], "target_init", lock_sha)
            if _verified_stage(root, job["job_id"], "replay", lock_sha) is not None:
                verified += 1
    return {
        "status": ("selected_job_complete" if job_id is not None else "jobset_complete")
        if verified == len(selected)
        else "selected_jobs_incomplete",
        "jobs": len(selected),
        "total_locked_jobs": len(jobs),
        "verified": verified,
        "coverage_status": context["coverage_status"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--lock-sha256", required=True)
    parser.add_argument("--job-id")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    context = validate_lock(args.lock, args.lock_sha256)
    print(json.dumps(dispatch(context, run=args.run, job_id=args.job_id), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
