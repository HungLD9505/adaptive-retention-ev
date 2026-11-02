"""Export Final manifest decisions and stage costs from the verified Kaggle archive."""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path
from zipfile import ZipFile

SOURCE_VERSION = "hungluongduc/hung-final-e5e8fe1c-360-20261029-v1/1"
LOCK_SHA = "e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e"
ARCHIVE_SHA = "531bff0d24ddf7eb0a08d4ed9d97976e55140b81025db0d91c28c557684e1114"
LOCK_DIR = ".cache/hung-final-lock-20261029T014357Z"
PINS = {
    "lock.json": LOCK_SHA,
    "jobset.json": "7d09583446d9437cec63956f1673c6d1927428ff80ba59a8a876b9391a7c68a2",
    "execution-plan.json": "429fdca711382161c45b338521897f945b70471f9b7b72b1fba7ef78e4cba0cb",
    "experiments/hung_sprint2/final_archive.py": "8d099276a130227cb5d70d7b3caaf61e9eec9a8460d0f0d08b78b650470e3453",
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    found = list(Path("/kaggle/input").rglob("hung-final-artifacts/session-receipt.json"))
    assert len(found) == 1
    producer = json.loads(found[0].read_text(encoding="utf-8"))
    assert producer["lock_sha256"] == LOCK_SHA and producer["jobs"] == 360
    assert producer["archive"]["sha256"] == ARCHIVE_SHA
    mount = found[0].parent.parent
    checkout = mount / f"hung-final-{LOCK_SHA[:12]}"
    paths = {
        name: checkout / (f"{LOCK_DIR}/{name}" if name.endswith(".json") else name) for name in PINS
    }
    for name, path in paths.items():
        assert path.is_file() and not path.is_symlink() and sha256(path) == PINS[name]
    jobs = json.loads(paths["jobset.json"].read_text(encoding="utf-8"))["jobs"]
    plan = json.loads(paths["execution-plan.json"].read_text(encoding="utf-8"))["jobs"]
    archive_path = mount / "hung-final-artifacts/archive.zip"
    checker = runpy.run_path(str(paths["experiments/hung_sprint2/final_archive.py"]))[
        "readback_archive"
    ]
    checked = checker(archive_path, ARCHIVE_SHA, LOCK_SHA, jobs, plan)
    assert checked["status"] == "local_archive_readback_verified"
    rows = []
    with ZipFile(archive_path) as archive:
        for job in jobs:
            job_id = job["job_id"]
            stages = {}
            for stage in checked["jobs"][job_id]:
                name = f"stages/{job_id}/{stage}/run_manifest.json"
                manifest = json.loads(archive.read(name))
                assert manifest["final_job_id"] == job_id
                assert manifest["final_lock_sha256"] == LOCK_SHA
                stages[stage] = {
                    "duration_seconds": manifest.get("duration_seconds"),
                    "event_evidence": manifest.get("event_evidence"),
                    "runtime_costs": manifest.get("runtime_costs", manifest.get("cost")),
                    "proxy_costs": manifest.get("proxy_costs"),
                    "coverage": manifest.get("coverage"),
                }
            rows.append({"job_id": job_id, "variant": job["variant"], "stages": stages})
    assert len(rows) == 360
    output = Path("/kaggle/working/final-run-events.json")
    with output.open("x", encoding="utf-8") as stream:
        json.dump(
            {
                "schema": "hung-final-remote-event-audit-v1",
                "source_kernel": SOURCE_VERSION,
                "lock_sha256": LOCK_SHA,
                "archive_sha256": ARCHIVE_SHA,
                "jobs": rows,
            },
            stream,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    receipt = {
        "schema": "hung-final-remote-event-audit-receipt-v1",
        "status": "FINAL_STAGE_MANIFEST_EVENTS_EXPORTED",
        "jobs": len(rows),
        "source_kernel": SOURCE_VERSION,
        "lock_sha256": LOCK_SHA,
        "archive_sha256": ARCHIVE_SHA,
        "output_bytes": output.stat().st_size,
        "output_sha256": sha256(output),
    }
    with Path("/kaggle/working/final-events-receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, sort_keys=True, separators=(",", ":"))
    print(json.dumps(receipt, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
