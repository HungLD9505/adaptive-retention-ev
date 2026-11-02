"""Score authenticated historical Main checkpoint origins from the review capsule."""

from __future__ import annotations

import argparse
import io
import json
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

import torch

from tools.hung_development_context_proxy import (
    digest,
    file_digest,
    input_index,
    selected_forecast,
    target_context,
    write_csv,
)

CAPSULE_SHA = "2493e0c1f440f6b5ead7c81facb3901623c4a58252ca7fa656cf9bdb1e32953d"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output_dir.resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError("Output must be a new directory within repository")
    input_path = root / ".cache/kaggle-payload-v2/payload/inputs.zip"
    if file_digest(input_path) != args.input_sha256:
        raise ValueError("Frozen input ZIP SHA differs")
    with ZipFile(input_path) as source:
        manifests, origins = input_index(source)
    capsule_path = root / ".cache/review-capsule-v1/review-capsule.zip.bin"
    if file_digest(capsule_path) != CAPSULE_SHA:
        raise ValueError("Historical capsule SHA differs")
    context: dict[tuple, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    bindings = []
    scored_runs = zero_runs = issued_origins = scored_origins = 0
    with ZipFile(capsule_path) as capsule:
        ledger_bytes = capsule.read("metadata/ledger.json")
        ledger = json.loads(ledger_bytes)
        jobs = sorted(
            (row for row in ledger["jobs"] if row["job_id"].startswith("main_")),
            key=lambda row: row["job_id"],
        )
        if len(jobs) != 69 or len({row["job_id"] for row in jobs}) != 69:
            raise ValueError("Capsule does not contain exact 69 historical Main jobs")
        for row in jobs:
            job = row["job_id"]
            if row["status"] != "VERIFIED_REUSE":
                raise ValueError(f"Historical job is not pinned for reuse: {job}")
            manifest_bytes = capsule.read(f"historical/{job}/run_manifest.json")
            if digest(manifest_bytes) != row["run_manifest"]["sha256"]:
                raise ValueError(f"Historical manifest SHA differs: {job}")
            manifest = json.loads(manifest_bytes)
            checkpoint_bytes = capsule.read(f"historical/{job}/runner_checkpoint.pt")
            checkpoint_sha = digest(checkpoint_bytes)
            if checkpoint_sha != manifest["final_runner_checkpoint_sha256"]:
                raise ValueError(f"Historical checkpoint SHA differs: {job}")
            state = torch.load(io.BytesIO(checkpoint_bytes), map_location="cpu", weights_only=True)
            binding = manifest["input_binding"]
            run = binding["input_run_id"]
            if state["binding"] != binding or manifests[run] != binding["input_manifest_sha256"]:
                raise ValueError(f"Historical input binding differs: {job}")
            issued = state["issued"]
            scored = sum(item.get("y_scaled") is not None for item in issued)
            if (
                scored != manifest["coverage"]["scored"]
                or len(issued) != manifest["coverage"]["created"]
            ):
                raise ValueError(f"Historical scored-count parity differs: {job}")
            scored_runs += scored > 0
            zero_runs += scored == 0
            issued_origins += len(issued)
            scored_origins += scored
            absolute = squared = 0.0
            for item in issued:
                origin = item["day_id"]
                if (binding["entity_id"], origin) not in origins[run]:
                    raise ValueError(f"Historical origin absent from frozen input: {job} {origin}")
                labels = item.get("y_scaled")
                if labels is None:
                    continue
                forecast = selected_forecast(item, state["controller"]["levels"])
                if forecast.numel() != 24 or labels.numel() != 24:
                    raise ValueError(f"Invalid historical horizon: {job} {origin}")
                errors = (forecast.to(torch.float64) - labels.to(torch.float64)) * state[
                    "energy_scale"
                ]
                for hour, error in enumerate(errors.tolist()):
                    absolute += abs(error)
                    squared += error * error
                    day_type, local_hour = target_context(origin, hour)
                    totals = context[(int(binding["history_days"]), day_type, local_hour)]
                    totals[0] += abs(error)
                    totals[1] += error * error
                    totals[2] += 1
            live = manifest["metrics_kwh"]["live"]
            if scored:
                hours = scored * 24
                if (
                    live is None
                    or live["hours"] != hours
                    or abs(absolute / hours - live["mae_kwh"]) > 1e-4
                    or abs((squared / hours) ** 0.5 - live["rmse_kwh"]) > 1e-4
                ):
                    raise ValueError(f"Historical live metric parity differs: {job}")
            elif live is not None:
                raise ValueError(f"Zero-scored historical job has metrics: {job}")
            bindings.append(
                {
                    "job_id": job,
                    "capsule_sha256": CAPSULE_SHA,
                    "capsule_ledger_sha256": digest(ledger_bytes),
                    "manifest_sha256": digest(manifest_bytes),
                    "checkpoint_sha256": checkpoint_sha,
                    "input_manifest_sha256": binding["input_manifest_sha256"],
                    "budget_days": binding["history_days"],
                    "entity_id": binding["entity_id"],
                    "issued_origins": len(issued),
                    "scored_origins": scored,
                    "proof_class": "CAPSULE_LEDGER_MANIFEST_NO_JOB_RECEIPT",
                }
            )
    context_rows = [
        {
            "method": "main",
            "budget_days": budget,
            "day_type": day_type,
            "local_hour": hour,
            "scored_hours": int(values[2]),
            "mae_kwh": values[0] / values[2],
            "rmse_kwh": (values[1] / values[2]) ** 0.5,
        }
        for (budget, day_type, hour), values in sorted(context.items())
    ]
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / "main_context_error.csv", context_rows)
    write_csv(output / "main_job_bindings.csv", bindings)
    summary = {
        "historical_jobs": 69,
        "capsule_sha256": CAPSULE_SHA,
        "capsule_ledger_sha256": bindings[0]["capsule_ledger_sha256"],
        "input_zip_sha256": args.input_sha256,
        "scorable_runs": scored_runs,
        "zero_scored_runs": zero_runs,
        "issued_origins": issued_origins,
        "scored_origins": scored_origins,
        "scored_hours": scored_origins * 24,
        "proof_class": "CAPSULE_LEDGER_MANIFEST_NO_JOB_RECEIPT",
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
