"""Audit saved Development origin errors and proxy decisions without replaying models."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

import torch


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def stage_hashes(text: str) -> dict[str, str]:
    return dict(item.split(":", 1) for item in text.split(";") if item)


def target_context(origin: str, hour: int) -> tuple[str, int]:
    timestamp = datetime.fromisoformat(origin) + timedelta(hours=hour)
    return ("weekend" if timestamp.weekday() >= 5 else "weekday", timestamp.hour)


def selected_forecast(item: dict, levels: list[float] | None) -> torch.Tensor:
    if "prediction" in item:
        return item["prediction"].reshape(-1)
    level = item["active_level"]
    if levels is None or level not in levels:
        raise ValueError("Issued active level is absent from controller levels")
    return item["forecasts"][levels.index(level)].reshape(-1)


def input_index(zip_file: ZipFile) -> tuple[dict[str, str], dict[str, set[tuple[str, str]]]]:
    manifests: dict[str, str] = {}
    origins: dict[str, set[tuple[str, str]]] = {}
    for name in zip_file.namelist():
        if not name.endswith("/manifest.json"):
            continue
        run = name.split("/")[-2]
        manifests[run] = digest(zip_file.read(name))
        forecast_name = name.removesuffix("manifest.json") + "forecasts.jsonl"
        with zip_file.open(forecast_name) as stream:
            origin_set = set()
            for line in stream:
                record = json.loads(line)
                origin_set.add((record["identity"][2], record["origin"]))
            origins[run] = origin_set
    return manifests, origins


def audited_rows(
    root: Path, ledger: list[dict], input_sha: str
) -> tuple[list[dict], list[dict], dict]:
    input_path = root / ".cache/kaggle-payload-v2/payload/inputs.zip"
    if file_digest(input_path) != input_sha:
        raise ValueError("Frozen input ZIP SHA differs")
    with ZipFile(input_path) as input_zip:
        input_manifests, input_origins = input_index(input_zip)
    archives: dict[str, list[dict]] = defaultdict(list)
    for row in ledger:
        if row["status"] not in {"VERIFIED_LOCAL_BYTES", "VERIFIED_LOCAL_ARCHIVE_STAGE_BYTES"}:
            raise ValueError(f"Unverified ledger job: {row['job_id']}")
        archives[row["archive_path"]].append(row)
    context: dict[tuple, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    decisions: list[dict] = []
    scorable_runs = zero_runs = scored_origins = issued_origins = 0
    for archive_rel, jobs in sorted(archives.items()):
        archive = root / archive_rel
        if archive.stat().st_size != int(jobs[0]["archive_bytes"]):
            raise ValueError(f"Archive byte length differs: {archive_rel}")
        actual_sha = file_digest(archive)
        if any(row["archive_sha256"] != actual_sha for row in jobs):
            raise ValueError(f"Archive SHA differs: {archive_rel}")
        with ZipFile(archive) as saved:
            for row in jobs:
                job = row["job_id"]
                receipt_bytes = saved.read(row["job_receipt_path"])
                if digest(receipt_bytes) != row["job_receipt_sha256"]:
                    raise ValueError(f"Receipt SHA differs: {job}")
                receipt = json.loads(receipt_bytes)
                if receipt["job_id"] != job:
                    raise ValueError(f"Receipt job ID differs: {job}")
                ledger_stage_hashes = stage_hashes(row["stage_receipt_sha256"])
                if ledger_stage_hashes and receipt["stages"] != ledger_stage_hashes:
                    raise ValueError(f"Receipt stages differ from ledger: {job}")
                for stage, stage_sha in receipt["stages"].items():
                    if digest(saved.read(f"receipts/{job}/{stage}.json")) != stage_sha:
                        raise ValueError(f"Stage receipt SHA differs: {job} {stage}")
                manifest_path = f"jobs/{job}/replay-90/run_manifest.json"
                manifest_bytes = saved.read(manifest_path)
                if (
                    digest(manifest_bytes)
                    != stage_hashes(row["stage_manifest_sha256"])["replay-90"]
                ):
                    raise ValueError(f"Manifest SHA differs: {job}")
                manifest = json.loads(manifest_bytes)
                binding = manifest["input_binding"]
                run = binding["input_run_id"]
                if (
                    binding["input_manifest_sha256"] != row["input_manifest_sha256"]
                    or input_manifests[run] != row["input_manifest_sha256"]
                    or binding["entity_id"] != row["entity_id"]
                ):
                    raise ValueError(f"Input binding differs: {job}")
                checkpoint_name = (
                    "runner.pt"
                    if row["method"] in {"target_only", "frozen_source", "seasonal_naive"}
                    else "runner_checkpoint.pt"
                )
                checkpoint_bytes = saved.read(f"jobs/{job}/replay-90/{checkpoint_name}")
                if digest(checkpoint_bytes) != manifest["final_runner_checkpoint_sha256"]:
                    raise ValueError(f"Checkpoint SHA differs: {job}")
                state = torch.load(
                    io.BytesIO(checkpoint_bytes), map_location="cpu", weights_only=True
                )
                if state["binding"] != binding:
                    raise ValueError(f"Checkpoint binding differs: {job}")
                issued = state["issued"]
                scored = sum(item.get("y_scaled") is not None for item in issued)
                if (
                    scored != manifest["coverage"]["scored"]
                    or len(issued) != manifest["coverage"]["created"]
                ):
                    raise ValueError(f"Checkpoint coverage differs: {job}")
                issued_origins += len(issued)
                scored_origins += scored
                scorable_runs += scored > 0
                zero_runs += scored == 0
                levels = state.get("controller", {}).get("levels")
                job_absolute = 0.0
                job_squared = 0.0
                for item in issued:
                    origin = item["day_id"]
                    if (row["entity_id"], origin) not in input_origins[run]:
                        raise ValueError(
                            f"Origin absent from frozen Development input: {job} {origin}"
                        )
                    labels = item.get("y_scaled")
                    if labels is None:
                        continue
                    forecast = selected_forecast(item, levels)
                    if forecast.numel() != 24 or labels.numel() != 24:
                        raise ValueError(f"Invalid forecast horizon: {job} {origin}")
                    errors = (forecast.to(torch.float64) - labels.to(torch.float64)) * state[
                        "energy_scale"
                    ]
                    for hour, error in enumerate(errors.tolist()):
                        job_absolute += abs(error)
                        job_squared += error * error
                        day_type, local_hour = target_context(origin, hour)
                        totals = context[
                            (row["method"], int(row["budget_days"]), day_type, local_hour)
                        ]
                        totals[0] += abs(error)
                        totals[1] += error * error
                        totals[2] += 1
                saved_metrics = manifest["metrics_kwh"]
                live = None if saved_metrics is None else saved_metrics.get("live", saved_metrics)
                if scored:
                    hours = scored * 24
                    if (
                        live is None
                        or live["hours"] != hours
                        or abs(job_absolute / hours - live["mae_kwh"]) > 1e-4
                        or abs((job_squared / hours) ** 0.5 - live["rmse_kwh"]) > 1e-4
                    ):
                        raise ValueError(f"Origin errors differ from saved live metrics: {job}")
                elif live is not None:
                    raise ValueError(f"Zero-scored job has live metrics: {job}")
                if row["method"] in {"source_error", "uncertainty", "drift"}:
                    for block, decision in enumerate(manifest["event_evidence"]["decisions"]):
                        decisions.append(
                            {
                                "job_id": job,
                                "archive_sha256": actual_sha,
                                "receipt_sha256": row["job_receipt_sha256"],
                                "manifest_sha256": digest(manifest_bytes),
                                "checkpoint_sha256": digest(checkpoint_bytes),
                                "input_manifest_sha256": row["input_manifest_sha256"],
                                "method": row["method"],
                                "budget_days": row["budget_days"],
                                "seed": row["seed"],
                                "entity_id": row["entity_id"],
                                "block_id": block,
                                "proxy_value": decision["proxy_value"],
                                "proxy_samples": decision["proxy_samples"],
                                "selected_level": decision["selected_level"],
                                "reason": decision["reason"],
                            }
                        )
    context_rows = []
    for (method, budget, day_type, hour), (absolute, squared, count) in sorted(context.items()):
        context_rows.append(
            {
                "method": method,
                "budget_days": budget,
                "day_type": day_type,
                "local_hour": hour,
                "scored_hours": int(count),
                "mae_kwh": absolute / count,
                "rmse_kwh": (squared / count) ** 0.5,
            }
        )
    return (
        context_rows,
        decisions,
        {
            "jobs": len(ledger),
            "archives": len(archives),
            "scorable_runs": scorable_runs,
            "zero_scored_runs": zero_runs,
            "issued_origins": issued_origins,
            "scored_origins": scored_origins,
            "scored_hours": scored_origins * 24,
            "proxy_decisions": len(decisions),
        },
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--ledger-sha256", required=True)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output_dir.resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError("Output must be a new directory within repository")
    ledger_path = root / "docs/reports/hung-development-782-job-ledger-20261028-v5.csv"
    if file_digest(ledger_path) != args.ledger_sha256:
        raise ValueError("Ledger SHA differs")
    with ledger_path.open(encoding="utf-8", newline="") as stream:
        ledger = list(csv.DictReader(stream))
    if len(ledger) != 782 or len({row["job_id"] for row in ledger}) != 782:
        raise ValueError("Ledger is not the exact 782-job set")
    context, decisions, counts = audited_rows(root, ledger, args.input_sha256)
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / "context_error.csv", context)
    write_csv(output / "proxy_decisions.csv", decisions)
    summary = {
        "scope": "782 new Development jobs; excludes 69 historical Main runs",
        "ledger_sha256": args.ledger_sha256,
        "input_zip_sha256": args.input_sha256,
        **counts,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
