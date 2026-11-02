"""Compute optional WAPE denominators from authenticated Final checkpoints on Kaggle CPU."""

from __future__ import annotations

import hashlib
import io
import json
import math
import runpy
from pathlib import Path
from zipfile import ZipFile

import torch

SOURCE = "hungluongduc/hung-final-e5e8fe1c-360-20261029-v1/1"
LOCK_SHA = "e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e"
ARCHIVE_SHA = "531bff0d24ddf7eb0a08d4ed9d97976e55140b81025db0d91c28c557684e1114"
LOCK_DIR = ".cache/hung-final-lock-20261029T014357Z"
PINS = {
    "lock.json": LOCK_SHA,
    "jobset.json": "7d09583446d9437cec63956f1673c6d1927428ff80ba59a8a876b9391a7c68a2",
    "execution-plan.json": "429fdca711382161c45b338521897f945b70471f9b7b72b1fba7ef78e4cba0cb",
    "experiments/hung_sprint2/final_archive.py": "8d099276a130227cb5d70d7b3caaf61e9eec9a8460d0f0d08b78b650470e3453",
    "tools/hung_results.py": "68fccbed056734d9b4842f7bda088880d7812d12417d64878d1aa018fc010456",
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
    checker = runpy.run_path(str(paths["experiments/hung_sprint2/final_archive.py"]))[
        "readback_archive"
    ]
    scorer = runpy.run_path(str(paths["tools/hung_results.py"]))["score_saved"]
    archive_path = mount / "hung-final-artifacts/archive.zip"
    checked = checker(archive_path, ARCHIVE_SHA, LOCK_SHA, jobs, plan)
    assert checked["status"] == "local_archive_readback_verified"
    rows = []
    with ZipFile(archive_path) as archive:
        for index, job in enumerate(jobs, 1):
            job_id = job["job_id"]
            prefix = f"stages/{job_id}/replay/"
            manifest = json.loads(archive.read(prefix + "run_manifest.json"))
            checkpoints = [
                name
                for name in checked["jobs"][job_id]["replay"]["artifacts"]
                if name.endswith(("/runner.pt", "/runner_checkpoint.pt"))
            ]
            assert len(checkpoints) == 1
            state = torch.load(
                io.BytesIO(archive.read(checkpoints[0])), map_location="cpu", weights_only=True
            )
            scored = scorer(state, manifest)
            labels = [
                issued["y_scaled"]
                for issued in state["issued"]
                if issued.get("y_scaled") is not None
            ]
            assert len(labels) == len(scored["days"]) == scored["coverage"]["scored"]
            scale = state["energy_scale"]
            assert math.isfinite(scale) and scale > 0
            label_total = math.fsum(
                float(label.reshape(-1).double().sum()) * scale for label in labels
            )
            error_total = math.fsum(day["absolute"] for day in scored["days"].values())
            assert label_total >= 0 and error_total >= 0
            rows.append(
                {
                    "job_id": job_id,
                    "scored_days": len(labels),
                    "label_total_kwh": label_total,
                    "absolute_error_kwh": error_total,
                    "wape": error_total / label_total if label_total > 0 else None,
                }
            )
            if index % 60 == 0:
                print(f"WAPE denominator {index}/360", flush=True)
    assert len(rows) == 360
    output = Path("/kaggle/working/final-wape-rows.json")
    with output.open("x", encoding="utf-8") as stream:
        json.dump(
            {
                "schema": "hung-final-wape-rows-v1",
                "source_kernel": SOURCE,
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
        "schema": "hung-final-wape-receipt-v1",
        "status": "FINAL_WAPE_DENOMINATORS_READ_FROM_CHECKPOINTS",
        "jobs": len(rows),
        "undefined_jobs": sum(row["wape"] is None for row in rows),
        "source_kernel": SOURCE,
        "lock_sha256": LOCK_SHA,
        "archive_sha256": ARCHIVE_SHA,
        "output_bytes": output.stat().st_size,
        "output_sha256": sha256(output),
    }
    with Path("/kaggle/working/final-wape-receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, sort_keys=True, separators=(",", ":"))
    print(json.dumps(receipt, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
