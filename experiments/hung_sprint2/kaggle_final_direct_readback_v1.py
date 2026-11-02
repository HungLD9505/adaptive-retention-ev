"""CPU readback of the immutable Hùng Final GPU saved output; no training."""

import hashlib
import json
import runpy
from pathlib import Path

GPU_VERSION = "hungluongduc/hung-final-e5e8fe1c-360-20261029-v1/1"
GPU_RUN_ID = 363367272
LOCK_SHA = "e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e"
JOBSET_SHA = "7d09583446d9437cec63956f1673c6d1927428ff80ba59a8a876b9391a7c68a2"
PLAN_SHA = "429fdca711382161c45b338521897f945b70471f9b7b72b1fba7ef78e4cba0cb"
MODULE_SHA = "8d099276a130227cb5d70d7b3caaf61e9eec9a8460d0f0d08b78b650470e3453"
ARCHIVE_SHA = "531bff0d24ddf7eb0a08d4ed9d97976e55140b81025db0d91c28c557684e1114"
ARCHIVE_BYTES = 2404391526
ARCHIVE_CRC = "6a29f6e1"
INPUT = Path("/kaggle/input")
OUTPUT = Path("/kaggle/working")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


receipts = list(INPUT.rglob("hung-final-artifacts/session-receipt.json"))
assert len(receipts) == 1, "Expected exactly one mounted Final GPU saved output"
producer_receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
mount = receipts[0].parent.parent
assert producer_receipt["schema"] == "hung-final-kaggle-session-v1"
assert producer_receipt["status"] == "LOCAL_ARCHIVE_AND_PACKET_READY"
assert producer_receipt["lock_sha256"] == LOCK_SHA
assert producer_receipt["jobs"] == 360
assert producer_receipt["remote_readback"] == "pending"
assert producer_receipt["archive"] == {
    "path": "/kaggle/working/hung-final-artifacts/archive.zip",
    "bytes": ARCHIVE_BYTES,
    "sha256": ARCHIVE_SHA,
    "crc32": ARCHIVE_CRC,
}

checkout = mount / f"hung-final-{LOCK_SHA[:12]}"
lock_path = checkout / ".cache/hung-final-lock-20261029T014357Z/lock.json"
jobset_path = checkout / ".cache/hung-final-lock-20261029T014357Z/jobset.json"
plan_path = checkout / ".cache/hung-final-lock-20261029T014357Z/execution-plan.json"
module_path = checkout / "experiments/hung_sprint2/final_archive.py"
archive_path = mount / "hung-final-artifacts/archive.zip"

for path, expected in (
    (lock_path, LOCK_SHA),
    (jobset_path, JOBSET_SHA),
    (plan_path, PLAN_SHA),
    (module_path, MODULE_SHA),
):
    assert path.is_file() and not path.is_symlink(), f"Missing pinned input: {path.name}"
    assert sha256(path) == expected, f"Pinned input SHA differs: {path.name}"
assert archive_path.is_file() and not archive_path.is_symlink()
assert archive_path.stat().st_size == ARCHIVE_BYTES

lock = json.loads(lock_path.read_text(encoding="utf-8"))
assert lock["code_commit"] == "929480bfb123aaecab2cb9178f0e9088fb4d6593"
assert lock["jobset"]["sha256"] == JOBSET_SHA
assert lock["execution_plan"]["sha256"] == PLAN_SHA
jobs = json.loads(jobset_path.read_text(encoding="utf-8"))["jobs"]
plan = json.loads(plan_path.read_text(encoding="utf-8"))["jobs"]
assert len(jobs) == len(plan) == lock["jobset"]["count"] == 360

readback_archive = runpy.run_path(str(module_path))["readback_archive"]
verified = readback_archive(archive_path, ARCHIVE_SHA, LOCK_SHA, jobs, plan)
assert verified["status"] == "local_archive_readback_verified"
assert verified["archive"] == {
    "path": str(archive_path),
    "bytes": ARCHIVE_BYTES,
    "sha256": ARCHIVE_SHA,
    "crc32": ARCHIVE_CRC,
}
assert len(verified["jobs"]) == 360
assert set(verified["jobs"]) == {job["job_id"] for job in jobs}

ledger = {
    "schema": "hung-final-job-artifact-ledger-v1",
    "source_kernel": GPU_VERSION,
    "source_run_id": GPU_RUN_ID,
    "lock_sha256": LOCK_SHA,
    "archive_sha256": ARCHIVE_SHA,
    "jobs": verified["jobs"],
}
ledger_path = OUTPUT / "final-job-artifact-ledger.json"
with ledger_path.open("x", encoding="utf-8") as stream:
    json.dump(ledger, stream, sort_keys=True, separators=(",", ":"))

receipt = {
    "schema": "hung-final-direct-remote-readback-v1",
    "status": "REMOTE_ARCHIVE_BYTES_SHA_CRC_AND_JOBSET_VERIFIED",
    "source_kernel": GPU_VERSION,
    "source_run_id": GPU_RUN_ID,
    "lock_sha256": LOCK_SHA,
    "archive": {"bytes": ARCHIVE_BYTES, "sha256": ARCHIVE_SHA, "crc32": ARCHIVE_CRC},
    "jobs": len(verified["jobs"]),
    "ledger_sha256": sha256(ledger_path),
    "ledger_bytes": ledger_path.stat().st_size,
}
with (OUTPUT / "final-direct-readback.json").open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, sort_keys=True, separators=(",", ":"))
print(json.dumps(receipt, sort_keys=True), flush=True)
