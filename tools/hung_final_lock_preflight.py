"""Outcome-blind create-only Hùng Final lock gate; never reads Final role values."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from experiments.supporting_pipeline.dispatch_state import atomic_create
from experiments.supporting_pipeline.final_archive import require
from experiments.supporting_pipeline.final_lock import MIN_FREE_BYTES, validate_lock

INPUT_ZIP_SHA = "2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7"
RESOURCE_SCENARIOS_SHA = "d5eee62c42b8b21d82fe40324cb077576ca8d6725fb939caa73b75e8ab45be5c"
SOURCE_CSV_SHA = "05035160f3fef3cf58ebdb9f70deec0475ddd8e0d1f2dd55ee6ec6c87b29302f"
AUTHORIZATION = {
    "issue_url": "https://github.com/HungLD9505/adaptive-retention-ev/issues/23",
    "comment_id": 6476049006,
    "review_state": "lead_exception_not_peer_approval",
}


def _pin(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), f"Missing/unsafe lock input: {path}")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}


def _lock_ref(root: Path, path: Path) -> dict:
    pin = _pin(path)
    pin["path"] = path.resolve().relative_to(root.resolve()).as_posix()
    return pin


def _inside(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    require(resolved.is_relative_to(root.resolve()), f"Path outside repository: {path}")
    return resolved


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _code_commit(root: Path) -> str:
    require(
        not subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True),
        "Lock generation requires a clean code worktree",
    )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    require(
        len(commit) == 40 and all(char in "0123456789abcdef" for char in commit),
        "Invalid code commit",
    )
    return commit


def _attestation(
    root: Path, path: Path, now: datetime, gpu_seconds: float, output_bytes: int
) -> dict:
    attested = _read(path)
    require(
        set(attested)
        == {
            "schema",
            "provider",
            "account",
            "observed_at_utc",
            "authentication_method",
            "evidence",
            "gpu_seconds_available",
            "provider_storage_free_bytes",
            "is_pay_to_scale_enabled",
        }
        and attested["schema"] == "hung-final-provider-attestation-v1"
        and attested["provider"] == "kaggle"
        and isinstance(attested["account"], str)
        and bool(attested["account"])
        and attested["authentication_method"] == "authenticated_kaggle_api"
        and attested["is_pay_to_scale_enabled"] is False,
        "Authenticated free-tier Kaggle attestation is absent/invalid",
    )
    observed = datetime.fromisoformat(attested["observed_at_utc"].replace("Z", "+00:00"))
    require(
        observed.tzinfo is not None
        and now - timedelta(minutes=20) <= observed <= now + timedelta(minutes=2),
        "Kaggle quota/storage attestation is stale/future",
    )
    evidence = attested["evidence"]
    require(set(evidence) == {"path", "bytes", "sha256"}, "Attestation evidence pin differs")
    source = _inside(root, Path(evidence["path"]))
    require(_pin(source) == evidence, "Attestation evidence bytes/SHA differ")
    raw = _read(source)
    require(
        raw.get("provider") == "kaggle"
        and raw.get("account") == attested["account"]
        and raw.get("observed_at_utc") == attested["observed_at_utc"]
        and raw.get("gpu_seconds_available") == attested["gpu_seconds_available"]
        and raw.get("provider_storage_free_bytes") == attested["provider_storage_free_bytes"]
        and raw.get("is_pay_to_scale_enabled") is False,
        "Attestation evidence fields differ",
    )
    require(
        type(attested["gpu_seconds_available"]) in {int, float}
        and attested["gpu_seconds_available"] >= gpu_seconds + 3600
        and type(attested["provider_storage_free_bytes"]) is int
        and attested["provider_storage_free_bytes"] >= MIN_FREE_BYTES + output_bytes,
        "Kaggle quota/storage insufficient for locked estimate and reserve",
    )
    return attested


def _candidate(
    root: Path, candidate_dir: Path, analysis_path: Path, source_csv: Path
) -> tuple[dict, dict, dict, list[dict]]:
    jobset_path = candidate_dir / "candidate_jobset.json"
    plan_path = candidate_dir / "candidate_execution_plan.json"
    coverage = _read(candidate_dir / "candidate_coverage.json")
    spec = _read(analysis_path)
    require(
        spec.get("schema") == "hung-final-execution-contract-candidate-v1"
        and spec.get("status") == "candidate_only_not_an_executable_lock_or_peer_approval"
        and spec["authority"]["candidate_jobset_sha256"] == _pin(jobset_path)["sha256"]
        and spec["authority"]["candidate_execution_plan_sha256"] == _pin(plan_path)["sha256"]
        and spec["authority"]["candidate_source_config_bindings_sha256"]
        == _pin(candidate_dir / "source_config_bindings.json")["sha256"],
        "Candidate or analysis identity changed",
    )
    jobset, plan = _read(jobset_path), _read(plan_path)
    jobs, planned = jobset["jobs"], plan["jobs"]
    require(
        jobset["schema"] == "hung-final-jobset-v1"
        and plan["schema"] == "hung-final-execution-plan-v1"
        and len(jobs) == len(planned) == coverage["expected_jobs"] == 360
        and [job["job_id"] for job in jobs] == [row["job_id"] for row in planned],
        "Candidate exact 360-job matrix differs",
    )
    require(
        coverage["missing_cells"] == []
        and any("370 of 373" in item for item in coverage["declared_shortfalls"])
        and any("CHARGED" in item for item in coverage["declared_shortfalls"]),
        "Required #15 shortfalls or selected-matrix cells differ",
    )
    drift_jobs = [row for row in planned if row["method"] == "drift"]
    require(
        len(drift_jobs) == 27
        and all(
            row["replay"].get("drift_reference_mean") is None
            and row["replay"].get("drift_reference_scale") is None
            for row in drift_jobs
        ),
        "Final Drift must use the locked post-input derivation",
    )
    for group, prefix in (
        ("executed_hung_code_sha256", "experiments/supporting_pipeline"),
        ("development_analysis_code_sha256", ""),
        ("prepared_final_durability_code_sha256", ""),
    ):
        pins = spec[group]
        require(isinstance(pins, dict) and pins, f"Missing code pins: {group}")
        for name, expected_sha in pins.items():
            path = root / prefix / name
            require(_pin(path)["sha256"] == expected_sha, f"Changed candidate code: {name}")
    require(_pin(source_csv)["sha256"] == SOURCE_CSV_SHA, "Source candidate table changed")
    with source_csv.open(newline="", encoding="utf-8") as stream:
        sources = list(csv.DictReader(stream))
    require(len(sources) == 9, "Nine Development Source candidates are required")
    references = []
    input_manifests = {}
    for row in sources:
        path = _inside(root, root / row["source_checkpoint_path"])
        pin = _pin(path)
        require(
            pin["sha256"] == row["source_checkpoint_sha256"]
            and pin["bytes"] == int(row["source_checkpoint_bytes"])
            and _pin(path.with_name("run_manifest.json"))["sha256"]
            == row["source_manifest_sha256"],
            "Source candidate bytes/SHA differ",
        )
        references.append(_lock_ref(root, path))
        input_manifests[int(row["budget_days"])] = row["input_manifest_sha256"]
    require(
        {ref["sha256"] for ref in references}
        == {job["source_checkpoint_sha256"] for job in jobs if job["source_checkpoint_sha256"]},
        "Candidate Source set differs",
    )
    require(
        all(job["input_manifest_sha256"] == input_manifests[job["budget_days"]] for job in jobs),
        "Candidate input manifest set differs",
    )
    return jobset, plan, coverage, sorted(references, key=lambda row: row["sha256"])


def prepare_lock(
    *,
    root: Path,
    candidate_dir: Path,
    analysis_path: Path,
    source_csv: Path,
    resource_csv: Path,
    input_zip: Path,
    attestation_path: Path,
    output_root: Path,
    packet: Path,
    estimated_gpu_seconds: float,
    estimated_output_bytes: int,
    now: datetime,
    authenticated_evidence_verifier: Callable[[dict, Path], bool] | None = None,
) -> dict:
    """Create a lock only after every external and local pre-execution gate passes."""
    root = root.resolve()
    (
        candidate_dir,
        analysis_path,
        source_csv,
        resource_csv,
        input_zip,
        attestation_path,
        output_root,
        packet,
    ) = (
        _inside(root, path)
        for path in (
            candidate_dir,
            analysis_path,
            source_csv,
            resource_csv,
            input_zip,
            attestation_path,
            output_root,
            packet,
        )
    )
    require(now.tzinfo is not None, "UTC-aware preflight time is required")
    now = now.astimezone(timezone.utc)
    require(
        type(estimated_output_bytes) is int
        and estimated_output_bytes > 0
        and type(estimated_gpu_seconds) in {int, float}
        and estimated_gpu_seconds > 0,
        "Final resource estimate is invalid",
    )
    require(
        _pin(resource_csv)["sha256"] == RESOURCE_SCENARIOS_SHA, "Measured resource scenario changed"
    )
    with resource_csv.open(newline="", encoding="utf-8") as stream:
        scenarios = list(csv.DictReader(stream))
    measured = next(
        (
            row
            for row in scenarios
            if row["candidate_urban_entities"] == "3" and row["candidate_physical_jobs"] == "360"
        ),
        None,
    )
    require(measured is not None, "Measured 360-job Development resource scenario is absent")
    require(
        estimated_output_bytes >= int(measured["raw_plus_zip_p95_with_1_5_margin_bytes"])
        and estimated_gpu_seconds
        >= float(measured["stage_wall_observed_p95_scenario_hours"]) * 3600,
        "Final resource estimate understates measured Development scenario",
    )
    require(
        not packet.exists() and not output_root.exists(), "Final packet/output root must be new"
    )
    require(
        packet.is_relative_to(root / ".cache") and output_root.is_relative_to(root / ".cache"),
        "Lock packet/output must remain ignored under repo .cache",
    )
    attested = _attestation(
        root, attestation_path, now, estimated_gpu_seconds, estimated_output_bytes
    )
    require(
        authenticated_evidence_verifier is not None
        and authenticated_evidence_verifier(attested, Path(attested["evidence"]["path"])) is True,
        "Authenticated Kaggle evidence was not independently verified",
    )
    ancestor = packet.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    staging_bytes = (
        sum(
            path.stat().st_size
            for path in (
                candidate_dir / "candidate_jobset.json",
                candidate_dir / "candidate_execution_plan.json",
                analysis_path,
            )
        )
        + 1024 * 1024
    )
    require(
        shutil.disk_usage(ancestor).free >= staging_bytes,
        "Local Final lock staging space is unavailable",
    )
    require(_pin(input_zip)["sha256"] == INPUT_ZIP_SHA, "Frozen UrbanEV input ZIP differs")
    jobset, plan, coverage, sources = _candidate(root, candidate_dir, analysis_path, source_csv)
    spec = _read(analysis_path)
    choice = spec["execution_choice"]
    require(
        choice["drift_reference"].startswith("first issued Final x_hist")
        and choice["controller"]["bootstrap_stream"]
        and choice["causal_order"]
        and choice["head_topology"],
        "Final analysis/execution contract is incomplete",
    )
    code_commit = _code_commit(root)
    packet.mkdir(parents=True, exist_ok=False)
    copied = {}
    for name, source in (
        ("jobset.json", candidate_dir / "candidate_jobset.json"),
        ("execution-plan.json", candidate_dir / "candidate_execution_plan.json"),
        ("analysis.json", analysis_path),
    ):
        target = packet / name
        with source.open("rb") as reader, target.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
        copied[name] = _lock_ref(root, target)
    lock = {
        "schema": "hung-final-lock-v1",
        "scope": "final_only",
        "code_commit": code_commit,
        "authorization": AUTHORIZATION,
        "report1_contract": {
            "head_topology": choice["head_topology"],
            "bootstrap_rule": choice["controller"]["bootstrap_stream"]
            + "; "
            + choice["controller"]["lcb_quantile"],
            "controller_rule": choice["controller"]["switch_rule"],
            "causal_label_rule": choice["causal_order"],
        },
        "drift_reference": {
            "schema": "hung-final-drift-reference-v1",
            "rule": "first_created_final_forecast_valid_load_population_sd",
            "scale_floor": 0.1,
        },
        "input": _lock_ref(root, input_zip),
        "source_checkpoints": sources,
        "jobset": {**copied["jobset.json"], "count": len(jobset["jobs"])},
        "execution_plan": copied["execution-plan.json"],
        "analysis": copied["analysis.json"],
        "coverage": coverage,
        "resources": {
            "provider": "kaggle",
            "device": "cuda",
            "min_free_bytes": MIN_FREE_BYTES,
            "estimated_gpu_seconds": estimated_gpu_seconds,
            "estimated_output_bytes": estimated_output_bytes,
        },
        "output_root": output_root.relative_to(root).as_posix(),
        "created_at_utc": now.isoformat().replace("+00:00", "Z"),
        "final_label_access_after_lock": True,
    }
    atomic_create(packet / "lock.json", lock)
    lock_sha = _pin(packet / "lock.json")["sha256"]
    validate_lock(packet / "lock.json", lock_sha, check_code=False, verify_input_runs=False)
    atomic_create(
        packet / "preflight.json",
        {
            "schema": "hung-final-lock-preflight-v1",
            "status": "LOCK_CREATED_EXECUTION_NOT_STARTED",
            "lock_sha256": lock_sha,
            "attestation_sha256": _pin(attestation_path)["sha256"],
            "candidate_jobs": len(jobset["jobs"]),
            "shortfalls": coverage["declared_shortfalls"],
        },
    )
    return {"lock": str(packet / "lock.json"), "sha256": lock_sha}
