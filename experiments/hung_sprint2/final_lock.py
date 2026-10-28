"""Authenticate the immutable Hùng Final lock and exact jobset before execution."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2 import cli
from experiments.hung_sprint2.dispatch_matched import read_json, require
from experiments.hung_sprint2.final_coverage import _coverage_status

ROOT = Path(__file__).resolve().parents[2]
MIN_FREE_BYTES = 8 * 1024**3
CONTROLLER_METHODS = {
    "confidence",
    "online_best_lambda",
    "without_confidence",
    "fixed_retention",
    "full_finetuning",
    "source_error",
    "uncertainty",
    "drift",
}
SINGLE_METHODS = {"target_only", "frozen_source", "seasonal_naive"}
JOB_FIELDS = {
    "job_id",
    "variant",
    "entity_id",
    "dataset_id",
    "city_id",
    "budget_days",
    "seed",
    "method",
    "input_run",
    "input_manifest_sha256",
    "source_checkpoint_sha256",
    "target_checkpoint_sha256",
}
LOCK_FIELDS = {
    "schema",
    "scope",
    "code_commit",
    "authorization",
    "report1_contract",
    "drift_reference",
    "input",
    "source_checkpoints",
    "jobset",
    "execution_plan",
    "analysis",
    "coverage",
    "resources",
    "output_root",
    "created_at_utc",
    "final_label_access_after_lock",
}


def _project_path(value: str) -> Path:
    path = Path(value)
    path = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    require(path.is_relative_to(ROOT.resolve()), f"Path outside current repository: {path}")
    require(not path.is_symlink(), f"Symlink path refused: {path}")
    return path


def _pinned_json(reference: dict) -> dict:
    require(
        set(reference) in ({"path", "bytes", "sha256"}, {"path", "bytes", "sha256", "count"}),
        "Pinned reference fields differ",
    )
    path = _project_path(reference["path"])
    require(
        path.is_file() and path.stat().st_size == reference["bytes"],
        f"Pinned file bytes differ: {path}",
    )
    require(sha256_file(path) == reference["sha256"], f"Pinned file SHA differs: {path}")
    return read_json(path)


def _code_unchanged(commit: str) -> None:
    require(
        isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit), "Invalid code commit"
    )
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT, check=False
    )
    require(ancestor.returncode == 0, "Pinned code commit is not a current ancestor")
    changed = subprocess.run(
        ["git", "diff", "--quiet", commit, "HEAD", "--", "experiments/hung_sprint2", "ev_inputs"],
        cwd=ROOT,
        check=False,
    )
    require(changed.returncode == 0, "Executed code changed after pinned commit")
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    require(not status, "Execution requires a clean worktree")


def _valid_job(row: dict) -> None:
    require(set(row) == JOB_FIELDS, "Final job fields differ")
    require(
        isinstance(row["job_id"], str)
        and re.fullmatch(r"[A-Za-z0-9_-]+", row["job_id"]) is not None,
        "Unsafe Final job ID",
    )
    require(row["method"] in CONTROLLER_METHODS | SINGLE_METHODS, "Unknown Final method")
    require(isinstance(row["variant"], str) and row["variant"], "Missing Final variant")
    require(row["dataset_id"] in {"urbanev", "charged"}, "Unknown Final dataset")
    require(
        all(isinstance(row[key], str) and row[key] for key in ("city_id", "entity_id")),
        "Missing Final identity",
    )
    require(
        type(row["budget_days"]) is int and row["budget_days"] in {7, 14, 28},
        "Invalid Final budget",
    )
    require(type(row["seed"]) is int and row["seed"] >= 0, "Invalid Final seed")
    require(
        re.fullmatch(r"[0-9a-f]{64}", row["input_manifest_sha256"]) is not None,
        "Invalid Final input SHA",
    )
    for key in ("source_checkpoint_sha256", "target_checkpoint_sha256"):
        value = row[key]
        require(
            value is None or (isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)),
            f"Invalid {key}",
        )
    require(
        row["target_checkpoint_sha256"] is None,
        "Pre-existing Final Target checkpoint reuse is not supported",
    )
    if row["method"] in CONTROLLER_METHODS | {"frozen_source"}:
        require(row["source_checkpoint_sha256"] is not None, "Source checkpoint is required")
    else:
        require(row["source_checkpoint_sha256"] is None, "Source checkpoint is inapplicable")
    _project_path(row["input_run"])


def _plan_identity(
    job: dict, planned: dict, source_by_sha: dict[str, Path], replay_origins: int
) -> None:
    require(
        set(planned) == {"job_id", "variant", "method", "target_init", "replay"},
        "Final plan job fields differ",
    )
    require(
        planned["job_id"] == job["job_id"]
        and planned["variant"] == job["variant"]
        and planned["method"] == job["method"],
        "Final plan/jobset ID differs",
    )
    replay = planned["replay"]
    require(isinstance(replay, dict), "Missing Final replay arguments")
    protected = {"output", "role", "final_lock_sha256", "final_job_id"}
    require(not protected & set(replay), "Final replay overrides protected arguments")
    for name in (
        "input_run",
        "source_input_run",
        "source_checkpoint",
        "target_checkpoint",
        "initial_checkpoint",
    ):
        if replay.get(name) is not None:
            _project_path(replay[name])
    require(
        replay.get("entity_id") == job["entity_id"]
        and replay.get("seed", job["seed"]) == job["seed"]
        and replay.get("manifest_sha256") == job["input_manifest_sha256"]
        and _project_path(replay["input_run"]) == _project_path(job["input_run"])
        and replay.get("max_origins") == replay_origins
        and replay.get("device") in {"cpu", "cuda"},
        "Final replay identity/config differs from jobset",
    )
    require(
        replay.get("resume_checkpoint") is None, "Final plan cannot begin from an unpinned resume"
    )
    if job["method"] in CONTROLLER_METHODS:
        require(replay.get("selection_rule") == job["method"], "Final controller method differs")
    else:
        require(replay.get("method") == job["method"], "Final single method differs")
    if job["method"] == "drift":
        require(
            "drift_reference_mean" in replay
            and "drift_reference_scale" in replay
            and replay["drift_reference_mean"] is None
            and replay["drift_reference_scale"] is None,
            "Final Drift numeric reference must be derived after lock",
        )
    if job["source_checkpoint_sha256"] is not None:
        source = source_by_sha[job["source_checkpoint_sha256"]]
        require(_project_path(replay["source_checkpoint"]) == source, "Final Source path differs")
    else:
        require(replay.get("source_checkpoint") is None, "Unexpected Final Source path")
    init = planned["target_init"]
    if job["method"] in CONTROLLER_METHODS | {"target_only"}:
        require(isinstance(init, dict), "Final Target initialization is required")
        require(not protected & set(init), "Final initialization overrides protected arguments")
        for name in ("input_run", "source_input_run", "source_checkpoint"):
            if init.get(name) is not None:
                _project_path(init[name])
        require(
            init.get("entity_id") == job["entity_id"]
            and init.get("seed") == job["seed"]
            and init.get("manifest_sha256") == job["input_manifest_sha256"]
            and _project_path(init["input_run"]) == _project_path(job["input_run"])
            and init.get("device") == replay["device"],
            "Final target initialization differs from jobset",
        )
        if job["method"] in CONTROLLER_METHODS:
            require(
                _project_path(init["source_checkpoint"])
                == source_by_sha[job["source_checkpoint_sha256"]]
                and init["source_input_run"] == replay["source_input_run"]
                and init["source_manifest_sha256"] == replay["source_manifest_sha256"],
                "Final initialization Source lineage differs from replay",
            )
    else:
        require(init is None, "Unexpected Final Target initialization")


def validate_lock(
    path: Path, expected_sha256: str, *, check_code: bool = True, verify_input_runs: bool = True
) -> dict:
    """Authenticate all identities before opening any Final role artifact."""
    lock_path = _project_path(str(path))
    require(
        lock_path.is_file() and sha256_file(lock_path) == expected_sha256, "Final lock SHA differs"
    )
    lock = read_json(lock_path)
    require(set(lock) == LOCK_FIELDS, "Final lock fields differ")
    require(
        lock["schema"] == "hung-final-lock-v1" and lock["scope"] == "final_only",
        "Unexpected Final lock",
    )
    require(lock["final_label_access_after_lock"] is True, "Final access order is not locked")
    authorization = lock["authorization"]
    require(
        set(authorization) == {"issue_url", "comment_id", "review_state"}
        and authorization["issue_url"]
        == "https://github.com/HungLD9505/adaptive-retention-ev/issues/23"
        and authorization["comment_id"] == 6476049006
        and authorization["review_state"] == "lead_exception_not_peer_approval",
        "Hùng-specific Final execution authorization differs",
    )
    contract = lock["report1_contract"]
    require(
        isinstance(contract, dict)
        and set(contract)
        == {"head_topology", "bootstrap_rule", "controller_rule", "causal_label_rule"}
        and all(
            isinstance(value, str)
            and value.strip()
            and value.strip().lower() not in {"pending", "tbd", "unknown"}
            for value in contract.values()
        ),
        "Missing Report 1 contract decisions",
    )
    drift = lock["drift_reference"]
    require(
        isinstance(drift, dict)
        and set(drift) == {"schema", "rule", "scale_floor"}
        and drift["schema"] == "hung-final-drift-reference-v1"
        and drift["rule"] == "first_created_final_forecast_valid_load_population_sd"
        and type(drift["scale_floor"]) in {int, float}
        and drift["scale_floor"] == 0.1,
        "Final Drift derivation rule is not locked",
    )
    if check_code:
        _code_unchanged(lock["code_commit"])
    resources = lock["resources"]
    require(
        set(resources)
        == {
            "provider",
            "device",
            "min_free_bytes",
            "estimated_gpu_seconds",
            "estimated_output_bytes",
        }
        and resources["provider"] in {"local", "kaggle"}
        and resources["device"] in {"cpu", "cuda"}
        and type(resources["min_free_bytes"]) is int
        and resources["min_free_bytes"] >= MIN_FREE_BYTES
        and type(resources["estimated_output_bytes"]) is int
        and resources["estimated_output_bytes"] > 0
        and isinstance(resources["estimated_gpu_seconds"], (int, float))
        and not isinstance(resources["estimated_gpu_seconds"], bool)
        and 0 <= resources["estimated_gpu_seconds"] < float("inf"),
        "Final resource lock is invalid",
    )
    for key in ("input", "analysis"):
        reference = lock[key]
        require(set(reference) == {"path", "bytes", "sha256"}, f"{key} pin fields differ")
        pinned = _project_path(reference["path"])
        require(
            pinned.is_file() and pinned.stat().st_size == reference["bytes"], f"{key} bytes differ"
        )
        require(sha256_file(pinned) == reference["sha256"], f"{key} SHA differs")
    source_by_sha: dict[str, Path] = {}
    require(isinstance(lock["source_checkpoints"], list), "Source checkpoint list is invalid")
    for reference in lock["source_checkpoints"]:
        require(set(reference) == {"path", "bytes", "sha256"}, "Source reference fields differ")
        source = _project_path(reference["path"])
        require(
            source.is_file() and source.stat().st_size == reference["bytes"],
            "Source checkpoint bytes differ",
        )
        require(sha256_file(source) == reference["sha256"], "Source checkpoint SHA differs")
        require(reference["sha256"] not in source_by_sha, "Duplicate Source checkpoint SHA")
        source_by_sha[reference["sha256"]] = source
    jobset = _pinned_json(lock["jobset"])
    plan = _pinned_json(lock["execution_plan"])
    require(
        jobset.get("schema") == "hung-final-jobset-v1" and set(jobset) == {"schema", "jobs"},
        "Final jobset schema differs",
    )
    require(
        plan.get("schema") == "hung-final-execution-plan-v1" and set(plan) == {"schema", "jobs"},
        "Final execution plan schema differs",
    )
    jobs, planned = jobset["jobs"], plan["jobs"]
    require(
        isinstance(jobs, list) and jobs and isinstance(planned, list), "Empty/invalid Final jobset"
    )
    require(len(jobs) == lock["jobset"]["count"] == len(planned), "Final job count differs")
    require(
        [row["job_id"] for row in jobs] == sorted(row["job_id"] for row in jobs),
        "Final jobset is not sorted",
    )
    require(len({row["job_id"] for row in jobs}) == len(jobs), "Duplicate Final job ID")
    require(
        [row["job_id"] for row in planned] == [row["job_id"] for row in jobs],
        "Final plan/jobset order differs",
    )
    for job, planned_job in zip(jobs, planned, strict=True):
        _valid_job(job)
        _plan_identity(job, planned_job, source_by_sha, lock["coverage"]["replay_origins"])
    coverage_status = _coverage_status(lock["coverage"], jobs, planned)
    root = _project_path(lock["output_root"])
    require(not root.is_relative_to(lock_path.parent), "Final output cannot contain the lock")
    context = {
        "lock": lock,
        "lock_sha256": expected_sha256,
        "jobs": jobs,
        "plan": planned,
        "output_root": root,
        "coverage_status": coverage_status,
        "input_runs_verified": verify_input_runs,
    }
    if not verify_input_runs:
        return context
    authenticated_inputs = set()
    final_entities: dict[Path, dict[tuple[str, str, str], int]] = {}
    final_schedule: dict[Path, dict[tuple[str, str, str], list[dict]]] = {}
    for job in jobs:
        input_run = _project_path(job["input_run"])
        key = (input_run, job["input_manifest_sha256"])
        if key in authenticated_inputs:
            continue
        manifest = cli._load_run(input_run, job["input_manifest_sha256"])
        require(
            manifest["config"]["dataset_id"] == job["dataset_id"]
            and manifest["config"]["city_id"] == job["city_id"]
            and manifest["config"]["history_days"] == job["budget_days"],
            "Final input-run identity differs from jobset",
        )
        entities: dict[tuple[str, str, str], int] = {}
        with (input_run / "entities.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if row.get("role") == "final":
                    identity = tuple(row["identity"])
                    entities[identity] = entities.get(identity, 0) + 1
        schedules: dict[tuple[str, str, str], list[dict]] = {}
        with (input_run / "schedule.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if row.get("role") == "final":
                    schedules.setdefault(tuple(row["identity"]), []).append(row)
        final_entities[input_run] = entities
        final_schedule[input_run] = schedules
        authenticated_inputs.add(key)
    for job in jobs:
        input_run = _project_path(job["input_run"])
        identity = (job["dataset_id"], job["city_id"], job["entity_id"])
        schedule = final_schedule[input_run].get(identity, [])
        require(final_entities[input_run].get(identity) == 1, "Final entity is not unique/ready")
        require(
            len(schedule) == lock["coverage"]["replay_origins"]
            and all(
                row.get("input_run_id") == input_run.name
                and row.get("status")
                in {"created", "skipped_all_missing_history", "skipped_undefined_scale"}
                for row in schedule
            ),
            "Final locked-origin schedule differs from jobset",
        )
        origins = [datetime.fromisoformat(row["origin"]) for row in schedule]
        require(
            all(
                later - earlier == timedelta(days=1)
                for earlier, later in zip(origins, origins[1:], strict=False)
            ),
            "Final origin order is not consecutive daily",
        )
    return context
