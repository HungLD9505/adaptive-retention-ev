"""Run the locked issue #99 paired Development comparison on Kaggle T4.

This orchestrator is separate from the scorer code at commit 2798384.
Its SHA-256 is checked by the notebook before execution.
"""

import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# INPUTS: set mounted, read-only paths and exact hashes before saving the notebook.
# C transport auto-extracts manifest.json/preflight.py directly at this root.
OUTER_EXTRACTED = Path("/kaggle/input/datasets/hungluongduc/issue99-source10-2798384-scored-inputs-v1")
PROTOCOL_FILE = Path("/kaggle/input/datasets/hungluongduc/issue99-comparison-lock-2798384-v2/issue99-protocol-locked-v2.json")
LOCK_FILE = Path("/kaggle/input/datasets/hungluongduc/issue99-comparison-lock-2798384-v2/issue99-comparison-lock-v2.json")
# The Fixed audit E saved notebook output is attached read-only as a Kaggle input.
FIXED_AUDIT_FILE = Path("/kaggle/input/notebooks/hungluongduc/issue99-fixed-protocol-v2-independent-audit-e-v1/issue99-fixed-independent-audit-protocol-v2-E.json")
# E manifest is at the dataset root; its ZIP contents are under the child folder.
E_DATASET_ROOT = Path("/kaggle/input/datasets/hungluongduc/issue99-fixed-verifier-19812d66-e-v1")
E_EXTRACTED_ROOT = E_DATASET_ROOT / "issue99-fixed-verifier-E-19812d66-v1"
E_MANIFEST_FILE = E_DATASET_ROOT / "issue99-fixed-verifier-E-19812d66-v1.manifest.json"
HARDENED_VERIFIER_FILE = E_EXTRACTED_ROOT / "ev_search" / "comparison_verify.py"
LOCK_SHA256 = "209102126ca696c5da2e959b053cc413d0e8d59fda3f92b30168a7a483577269"
FIXED_AUDIT_SHA256 = "233f893338b41e1ac39da9cd0b79b56ad70fa4c86f024900de4ad6dc8fde991e"
E_MANIFEST_SHA256 = "87cbdbf5ff5b7356a114d7771b1ecc94cfbad779869b7c778e10adcfb03f2f0c"
HARDENED_VERIFIER_SHA256 = "84a4993dcdb7f2e116bb6c3987a9e0fd8375f945f9b9c66c4e538caf302764f7"
PRIOR_GPU_SECONDS = 1800.0  # Conservative debit for pilot, v1/v2 Fixed, and cancelled duplicate.
PRIOR_OUTPUT_ROOT = None  # Or Path('/kaggle/input/PRIOR_SAVED_OUTPUT/issue99-comparison-v2').

# Fixed literal paths across all saved versions; each version has a fresh filesystem.
STAGE = Path("/kaggle/working/issue99-stage-v2")
BUNDLE_COPY = Path("/kaggle/working/issue99-bundle-v2")
OUTPUT_ROOT = Path("/kaggle/working/issue99-comparison-v2")
OUTER_MANIFEST_SHA256 = "a09f6a03ae5911717fd5afd070e93b52e0a3a066398278dac7b598bfd89ae088"
PROTOCOL_SHA256 = "f104d8809e04d0cde7d8982efd8146788f32c3c9a1c561ee9309891e6b040eb0"
CODE_COMMIT = "27983845b5d446e3915b0b4353570466f1da23ef"
GLOBAL_GPU_SECONDS = 8 * 3600
RESERVE_SECONDS = 10 * 60
MIN_NEXT_JOB_SECONDS = 5 * 60
MAX_OUTPUT_BYTES = 18_000_000_000  # Leave space below Kaggle's 20 GB output cap.
MIN_FREE_BYTES = 2_000_000_000


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require_hash(path, expected):
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError(f"Unpinned SHA-256 for {path}")
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: {actual}")


def log(record):
    record = {"wall_time_utc": datetime.now(timezone.utc).isoformat(), **record}
    with (OUTPUT_ROOT / "dispatch.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, allow_nan=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(record, allow_nan=False, sort_keys=True), flush=True)


def output_size(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_completed(job, root, verifier, inputs, replay):
    """Authenticate a saved job before copying it into this version."""
    from ev_models.checkpoint import digest
    from ev_search.comparison import event_hashes, verify_run_binding

    folder = root / job["job_id"]
    saved = json.loads((folder / "job.json").read_text(encoding="utf-8"))
    if saved["job"] != job or saved["reused_from"] != job["reuse_job_id"]:
        raise ValueError(f"Saved job identity differs: {job['job_id']}")
    expected_run = f"{job['reuse_job_id'] or job['job_id']}/run"
    if saved["run_path"] != expected_run:
        raise ValueError(f"Saved run path differs: {job['job_id']}")
    run = root / expected_run
    report_file = run / "run.json"
    if digest(report_file) != saved["run_sha256"]:
        raise ValueError(f"Saved run hash differs: {job['job_id']}")
    if event_hashes(run) != saved["event_sha256"]:
        raise ValueError(f"Saved event hashes differ: {job['job_id']}")
    report = json.loads(report_file.read_text(encoding="utf-8"))
    verify_run_binding(job, report, inputs)
    if report["scheduled_days"] != 90:
        raise ValueError(f"Wrong replay horizon: {job['job_id']}")
    verifier._verify_commit_chain(run, report)
    verifier._verify_full_horizon(run, replay)


def main():
    if (
        PRIOR_GPU_SECONDS is None
        or isinstance(PRIOR_GPU_SECONDS, bool)
        or not isinstance(PRIOR_GPU_SECONDS, (int, float))
        or not math.isfinite(PRIOR_GPU_SECONDS)
        or PRIOR_GPU_SECONDS < 0
    ):
        raise ValueError("Set PRIOR_GPU_SECONDS from audited Fixed and previous saved versions")
    if PRIOR_GPU_SECONDS >= GLOBAL_GPU_SECONDS - RESERVE_SECONDS:
        raise ValueError("No comparison time remains inside the locked GPU budget")
    if OUTPUT_ROOT.exists() or STAGE.exists() or BUNDLE_COPY.exists():
        raise FileExistsError("A fresh Kaggle version must start with unused output/stage paths")
    require_hash(PROTOCOL_FILE, PROTOCOL_SHA256)
    require_hash(LOCK_FILE, LOCK_SHA256)
    require_hash(FIXED_AUDIT_FILE, FIXED_AUDIT_SHA256)
    require_hash(E_MANIFEST_FILE, E_MANIFEST_SHA256)
    e_manifest = json.loads(E_MANIFEST_FILE.read_text(encoding="utf-8"))
    if (
        e_manifest.get("schema") != "issue99-fixed-verifier-package-v1"
        or e_manifest.get("source_commit") != "19812d66ef62f40e3bde2c812f3c5e4f14bbbd6d"
        or e_manifest.get("members", {}).get("ev_search/comparison_verify.py", {}).get("sha256")
        != HARDENED_VERIFIER_SHA256
    ):
        raise ValueError("Mounted audit E verifier differs from authenticated package")
    require_hash(HARDENED_VERIFIER_FILE, HARDENED_VERIFIER_SHA256)
    protocol = json.loads(PROTOCOL_FILE.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    fixed_audit = json.loads(FIXED_AUDIT_FILE.read_text(encoding="utf-8"))
    if (
        fixed_audit.get("schema") != "issue99-fixed-independent-verification-v1"
        or fixed_audit.get("status") != "PASS"
        or fixed_audit.get("protocol_sha256") != PROTOCOL_SHA256
    ):
        raise ValueError("Independent Fixed v2 audit has not passed")
    if lock.get("status") != "locked_owner_approved" or lock.get("protocol_sha256") != PROTOCOL_SHA256:
        raise ValueError("Comparison selection lock is missing or bound to another protocol")
    if not isinstance(lock.get("selected_fixed_lambda"), (int, float)):
        raise ValueError("Selected Fixed lambda is missing")

    # Authenticate the exact commit-C transport before importing any runner code.
    preflight_file = OUTER_EXTRACTED / "preflight.py"
    require_hash(preflight_file, "6bede89694d6d0dfb30fd59ed8b0305d7d374eca932e723e4af690d56ab561f6")
    preflight = load_module(preflight_file, "issue99_preflight")
    preflight.rehydrate_and_stage(
        OUTER_EXTRACTED, BUNDLE_COPY, STAGE,
        expected_manifest_sha256=OUTER_MANIFEST_SHA256, require_t4=True,
    )
    if (STAGE / "code" / ".issue99-code-commit").read_text().strip() != CODE_COMMIT:
        raise ValueError("Staged runner commit differs")
    sys.path.insert(0, str(STAGE / "code"))
    verifier = load_module(HARDENED_VERIFIER_FILE, "issue99_hardened_comparison_verify")

    from ev_models.data import InputRun
    from ev_runner.replay import Replay
    from ev_search.comparison import execute_job, plan_jobs

    inputs = InputRun(STAGE / "inputs", protocol["input_manifest_sha256"])
    sources = {
        str(seed): {
            "path": str(STAGE / "sources" / f"seed{seed}" / "epoch-10.pt"),
            "sha256": protocol["source_checkpoint_sha256"][str(seed)],
        }
        for seed in (42, 43, 44)
    }
    jobs = plan_jobs(inputs, PROTOCOL_FILE, LOCK_FILE, sources)
    if len(jobs) != 60:
        raise ValueError("Comparison matrix must have 60 identities")
    replays = {target: Replay(inputs, target, 90) for target in ("1405", "2152", "1153", "1693")}

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    log({"event": "start", "code_commit": CODE_COMMIT, "protocol_sha256": PROTOCOL_SHA256,
         "lock_sha256": LOCK_SHA256, "prior_gpu_seconds": PRIOR_GPU_SECONDS})
    start = time.perf_counter()
    durations = []
    if PRIOR_OUTPUT_ROOT is not None:
        prior = Path(PRIOR_OUTPUT_ROOT)
        if not prior.is_dir():
            raise FileNotFoundError(prior)
        for job in jobs:
            source = prior / job["job_id"]
            if not (source / "job.json").is_file():
                continue
            check_completed(job, prior, verifier, inputs, replays[job["target"]])
            if output_size(OUTPUT_ROOT) + output_size(source) > MAX_OUTPUT_BYTES:
                raise RuntimeError("Output size cap would be exceeded while carrying jobs")
            shutil.copytree(source, OUTPUT_ROOT / job["job_id"])
            log({"event": "carried", "job_id": job["job_id"]})

    for job in jobs:
        job_id = job["job_id"]
        if (OUTPUT_ROOT / job_id / "job.json").is_file():
            continue
        elapsed = time.perf_counter() - start
        remaining = GLOBAL_GPU_SECONDS - PRIOR_GPU_SECONDS - elapsed
        estimate = max(MIN_NEXT_JOB_SECONDS, 1.5 * max(durations, default=MIN_NEXT_JOB_SECONDS))
        size = output_size(OUTPUT_ROOT)
        free = shutil.disk_usage(OUTPUT_ROOT).free
        if remaining < estimate + RESERVE_SECONDS or size >= MAX_OUTPUT_BYTES or free < MIN_FREE_BYTES:
            log({"event": "stopped_budget", "next_job": job_id, "remaining_seconds": remaining,
                 "output_bytes": size, "free_bytes": free})
            break
        resume_from = None
        if PRIOR_OUTPUT_ROOT is not None:
            partial = Path(PRIOR_OUTPUT_ROOT) / job_id / "run"
            if partial.is_dir() and list(partial.glob("tick-*")) and not list(partial.glob(".pending-*")):
                resume_from = partial
        log({"event": "job_started", "job_id": job_id,
             "resume_from": str(resume_from) if resume_from else None})
        job_start = time.perf_counter()
        try:
            execute_job(job, inputs, PROTOCOL_FILE, LOCK_FILE, OUTPUT_ROOT,
                        device="cuda", resume_from=resume_from)
            check_completed(job, OUTPUT_ROOT, verifier, inputs, replays[job["target"]])
        except Exception as exc:
            log({"event": "job_failed", "job_id": job_id, "error": repr(exc),
                 "traceback": traceback.format_exc(),
                 "elapsed_seconds": time.perf_counter() - job_start})
            break  # Save this version, including partial artifacts, for inspection.
        duration = time.perf_counter() - job_start
        durations.append(duration)
        log({"event": "job_completed", "job_id": job_id, "elapsed_seconds": duration,
             "output_bytes": output_size(OUTPUT_ROOT)})

    complete = all((OUTPUT_ROOT / job["job_id"] / "job.json").is_file() for job in jobs)
    if complete:
        try:
            result = verifier.verify_matrix(jobs, OUTPUT_ROOT, inputs, PROTOCOL_FILE, LOCK_FILE)
            with (OUTPUT_ROOT / "verification.json").open("x", encoding="utf-8") as stream:
                json.dump(result, stream, allow_nan=False, sort_keys=True)
            log({"event": "matrix_verified", "verification_sha256": sha256(OUTPUT_ROOT / "verification.json")})
        except Exception as exc:
            log({"event": "matrix_verification_failed", "error": repr(exc),
                 "traceback": traceback.format_exc()})
            raise
    else:
        log({"event": "matrix_incomplete", "completed_jobs": sum(
            (OUTPUT_ROOT / job["job_id"] / "job.json").is_file() for job in jobs
        )})
    log({"event": "version_finished", "gpu_seconds_this_version": time.perf_counter() - start,
         "gpu_seconds_cumulative": PRIOR_GPU_SECONDS + time.perf_counter() - start})


if __name__ == "__main__":
    main()
