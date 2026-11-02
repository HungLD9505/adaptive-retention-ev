"""Score the pinned Hùng Final archive inside a separate Kaggle CPU session.

This is a read-only analysis run. It mounts one immutable GPU saved output and
exports small row-level results; it never trains or edits the frozen Final.
"""

from __future__ import annotations

import hashlib
import io
import json
import runpy
from pathlib import Path
from zipfile import ZipFile

import torch

SOURCE_VERSION = "hungluongduc/hung-final-e5e8fe1c-360-20261029-v1/1"
SOURCE_RUN_ID = 363367272
LOCK_SHA = "e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e"
ARCHIVE_SHA = "531bff0d24ddf7eb0a08d4ed9d97976e55140b81025db0d91c28c557684e1114"
PINS = {
    "lock.json": LOCK_SHA,
    "jobset.json": "7d09583446d9437cec63956f1673c6d1927428ff80ba59a8a876b9391a7c68a2",
    "execution-plan.json": "429fdca711382161c45b338521897f945b70471f9b7b72b1fba7ef78e4cba0cb",
    "analysis.json": "05c0d16ae03c92968f6c69b26f0695aa2bd1604a271c815aae2c1b2531749fa4",
    "experiments/hung_sprint2/final_archive.py": "8d099276a130227cb5d70d7b3caaf61e9eec9a8460d0f0d08b78b650470e3453",
    "tools/hung_results.py": "68fccbed056734d9b4842f7bda088880d7812d12417d64878d1aa018fc010456",
}
LOCK_DIR = ".cache/hung-final-lock-20261029T014357Z"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pinned(path: Path, expected: str) -> Path:
    assert path.is_file() and not path.is_symlink(), f"Missing pinned file: {path}"
    assert sha256(path) == expected, f"Pinned SHA differs: {path}"
    return path


def main() -> None:
    receipt_paths = list(Path("/kaggle/input").rglob("hung-final-artifacts/session-receipt.json"))
    assert len(receipt_paths) == 1, "Expected exactly one mounted GPU saved output"
    receipt = json.loads(receipt_paths[0].read_text(encoding="utf-8"))
    assert receipt["schema"] == "hung-final-kaggle-session-v1"
    assert receipt["lock_sha256"] == LOCK_SHA and receipt["jobs"] == 360
    assert receipt["archive"]["sha256"] == ARCHIVE_SHA
    assert receipt["archive"]["bytes"] == 2404391526
    assert receipt["archive"]["crc32"] == "6a29f6e1"
    mount = receipt_paths[0].parent.parent
    checkout = mount / f"hung-final-{LOCK_SHA[:12]}"
    paths = {
        name: pinned(
            checkout / (f"{LOCK_DIR}/{name}" if name.endswith(".json") else name),
            expected,
        )
        for name, expected in PINS.items()
    }
    lock = json.loads(paths["lock.json"].read_text(encoding="utf-8"))
    assert lock["code_commit"] == "929480bfb123aaecab2cb9178f0e9088fb4d6593"
    assert lock["analysis"]["sha256"] == PINS["analysis.json"]
    jobs = json.loads(paths["jobset.json"].read_text(encoding="utf-8"))["jobs"]
    plan = json.loads(paths["execution-plan.json"].read_text(encoding="utf-8"))["jobs"]
    assert len(jobs) == len(plan) == 360
    archive_path = pinned(mount / "hung-final-artifacts/archive.zip", ARCHIVE_SHA)
    archive_check = runpy.run_path(str(paths["experiments/hung_sprint2/final_archive.py"]))[
        "readback_archive"
    ]
    verified = archive_check(archive_path, ARCHIVE_SHA, LOCK_SHA, jobs, plan)
    assert verified["status"] == "local_archive_readback_verified"
    score_saved = runpy.run_path(str(paths["tools/hung_results.py"]))["score_saved"]
    rows = []
    with ZipFile(archive_path) as archive:
        files = json.loads(archive.read("index.json"))["files"]
        for index, job in enumerate(jobs, 1):
            job_id = job["job_id"]
            prefix = f"stages/{job_id}/replay/"
            manifest_name = prefix + "run_manifest.json"
            manifest = json.loads(archive.read(manifest_name))
            checkpoints = [
                name
                for name in verified["jobs"][job_id]["replay"]["artifacts"]
                if name.endswith(("/runner.pt", "/runner_checkpoint.pt"))
            ]
            assert len(checkpoints) == 1, f"Expected one Final runner checkpoint: {job_id}"
            checkpoint_name = checkpoints[0]
            state = torch.load(
                io.BytesIO(archive.read(checkpoint_name)), map_location="cpu", weights_only=True
            )
            assert manifest["final_runner_checkpoint_sha256"] == files[checkpoint_name]["sha256"]
            assert manifest["final_job_id"] == job_id
            assert manifest["final_lock_sha256"] == LOCK_SHA
            binding = manifest["input_binding"]
            assert state["binding"] == binding
            assert binding["input_manifest_sha256"] == job["input_manifest_sha256"]
            assert binding["entity_id"] == job["entity_id"]
            assert binding["history_days"] == job["budget_days"]
            scored = score_saved(state, manifest)
            rows.append(
                {
                    "job_id": job_id,
                    "dataset_id": job["dataset_id"],
                    "city_id": job["city_id"],
                    "entity_id": job["entity_id"],
                    "budget_days": job["budget_days"],
                    "seed": job["seed"],
                    "variant": job["variant"],
                    "method": job["method"],
                    "input_manifest_sha256": job["input_manifest_sha256"],
                    "source_checkpoint_sha256": job["source_checkpoint_sha256"],
                    "target_checkpoint_sha256": job["target_checkpoint_sha256"],
                    "manifest_sha256": files[manifest_name]["sha256"],
                    "checkpoint_sha256": files[checkpoint_name]["sha256"],
                    "coverage": scored["coverage"],
                    "metrics": scored["metrics"],
                    "days": scored["days"],
                    "duration_seconds": manifest.get("duration_seconds"),
                    "runtime_costs": manifest.get("runtime_costs", manifest.get("cost")),
                    "proxy_costs": manifest.get("proxy_costs"),
                }
            )
            if index % 30 == 0:
                print(f"Scored {index}/360 authenticated Final jobs", flush=True)
    assert len(rows) == 360 and len({row["job_id"] for row in rows}) == 360
    output = Path("/kaggle/working/final-run-scores.json")
    with output.open("x", encoding="utf-8") as stream:
        json.dump(
            {
                "schema": "hung-final-remote-run-scores-v1",
                "source_kernel": SOURCE_VERSION,
                "source_run_id": SOURCE_RUN_ID,
                "lock_sha256": LOCK_SHA,
                "archive_sha256": ARCHIVE_SHA,
                "jobs": rows,
            },
            stream,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    summary = {
        "schema": "hung-final-remote-metrics-receipt-v1",
        "status": "FINAL_RUN_SCORES_RECOMPUTED_FROM_CHECKPOINTS",
        "source_kernel": SOURCE_VERSION,
        "source_run_id": SOURCE_RUN_ID,
        "lock_sha256": LOCK_SHA,
        "archive_sha256": ARCHIVE_SHA,
        "jobs": len(rows),
        "scored_jobs": sum(row["metrics"] is not None for row in rows),
        "null_jobs": sum(row["metrics"] is None for row in rows),
        "output_bytes": output.stat().st_size,
        "output_sha256": sha256(output),
    }
    with Path("/kaggle/working/final-metrics-receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, sort_keys=True, separators=(", ", ": "))
    print(json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
