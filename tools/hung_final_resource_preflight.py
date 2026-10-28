"""Estimate candidate Final resources from authenticated Development stage receipts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

LEDGER_SHA256 = "bf1117c1d5fc0a902411cb6d850dca51e77802997c32880295ede20d8ac83004"
SCOPE_COUNTS = (3, 10, 30)
BUDGETS = (7, 14, 28)
SEEDED_METHODS = (
    "drift",
    "fixed_retention",
    "frozen_source",
    "full_finetuning",
    "online_best_lambda",
    "source_error",
    "target_only",
    "uncertainty",
)
CONFIDENCE_CONFIGS = ("block28", "no_source", "parameter_retention")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def split_hashes(text: str) -> dict[str, str]:
    return dict(item.split(":", 1) for item in text.split(";") if item)


def percentile(values: list[float], fraction: float) -> float:
    """Use nearest-rank p95; at n 6–9 it equals the observed maximum."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def measure(root: Path, ledger: list[dict]) -> list[dict]:
    archives: dict[str, list[dict]] = defaultdict(list)
    for row in ledger:
        if row["status"] not in {"VERIFIED_LOCAL_BYTES", "VERIFIED_LOCAL_ARCHIVE_STAGE_BYTES"}:
            raise ValueError(f"Ledger job not locally verified: {row['job_id']}")
        archives[row["archive_path"]].append(row)
    records = []
    for archive_rel, jobs in sorted(archives.items()):
        archive = root / archive_rel
        if archive.stat().st_size != int(jobs[0]["archive_bytes"]):
            raise ValueError(f"Archive byte size differs: {archive_rel}")
        archive_sha = digest(archive)
        if any(row["archive_sha256"] != archive_sha for row in jobs):
            raise ValueError(f"Archive SHA differs: {archive_rel}")
        with ZipFile(archive) as saved:
            member_sizes = {member.filename: member.compress_size for member in saved.infolist()}
            for row in jobs:
                job_id = row["job_id"]
                receipt_bytes = saved.read(row["job_receipt_path"])
                if hashlib.sha256(receipt_bytes).hexdigest() != row["job_receipt_sha256"]:
                    raise ValueError(f"Job receipt SHA differs: {job_id}")
                receipt = json.loads(receipt_bytes)
                stage_hashes = split_hashes(row["stage_manifest_sha256"])
                if receipt["job_id"] != job_id or set(receipt["stages"]) != set(stage_hashes):
                    raise ValueError(f"Stage set differs: {job_id}")
                wall_seconds = raw_bytes = 0.0
                for stage, expected_sha in stage_hashes.items():
                    prefix = f"jobs/{job_id}/{stage}/"
                    manifest_bytes = saved.read(prefix + "run_manifest.json")
                    if hashlib.sha256(manifest_bytes).hexdigest() != expected_sha:
                        raise ValueError(f"Stage manifest SHA differs: {job_id}/{stage}")
                    measurement = json.loads(saved.read(prefix + "dispatch_measurement.json"))
                    wall = measurement["wall_seconds"]
                    output_bytes = measurement["output_bytes_before_measurement"]
                    if not isinstance(wall, (int, float)) or not math.isfinite(wall) or wall < 0:
                        raise ValueError(f"Invalid stage wall time: {job_id}/{stage}")
                    if not isinstance(output_bytes, int) or output_bytes < 0:
                        raise ValueError(f"Invalid stage output bytes: {job_id}/{stage}")
                    wall_seconds += wall
                    raw_bytes += output_bytes
                prefix = f"jobs/{job_id}/"
                receipt_prefix = f"receipts/{job_id}/"
                compressed_bytes = sum(
                    size
                    for name, size in member_sizes.items()
                    if name.startswith(prefix) or name.startswith(receipt_prefix)
                )
                if compressed_bytes <= 0:
                    raise ValueError(f"No job ZIP members: {job_id}")
                records.append(
                    {
                        "job_id": job_id,
                        "budget_days": int(row["budget_days"]),
                        "seed": int(row["seed"]),
                        "entity_id": row["entity_id"],
                        "method": row["method"],
                        "config_id": row["config_id"],
                        "stage_count": len(stage_hashes),
                        "stage_wall_seconds": round(wall_seconds, 6),
                        "stage_output_bytes_before_measurement": int(raw_bytes),
                        "zip_member_compressed_bytes": compressed_bytes,
                        "archive_sha256": archive_sha,
                        "receipt_sha256": row["job_receipt_sha256"],
                    }
                )
    if len(records) != 782 or len({row["job_id"] for row in records}) != 782:
        raise ValueError("Expected exact 782-job Development set")
    return sorted(records, key=lambda row: row["job_id"])


def scenarios(records: list[dict]) -> tuple[list[dict], dict]:
    groups: dict[tuple[int, str], list[dict]] = defaultdict(list)
    proxies: dict[int, list[dict]] = defaultdict(list)
    for row in records:
        budget = row["budget_days"]
        groups[budget, row["entity_id"]].append(row)
        if row["method"] == "confidence" and row["config_id"] == "block28":
            proxies[budget].append(row)
    expected_groups = {7: 6, 14: 8, 28: 9}
    budget_rows = []
    for budget in BUDGETS:
        entity_groups = [rows for (b, _), rows in groups.items() if b == budget]
        if len(entity_groups) != expected_groups[budget] or any(
            len(rows) != 34 for rows in entity_groups
        ):
            raise ValueError(f"Development method coverage differs at {budget} days")
        for rows in entity_groups:
            methods = Counter(row["method"] for row in rows)
            expected = {"confidence": 9, "seasonal_naive": 1}
            expected.update({method: 3 for method in SEEDED_METHODS})
            confidence = Counter(row["config_id"] for row in rows if row["method"] == "confidence")
            if methods != expected or confidence != {name: 3 for name in CONFIDENCE_CONFIGS}:
                raise ValueError(f"Development method composition differs at {budget} days")
            if {row["seed"] for row in rows if row["method"] == "seasonal_naive"} != {7}:
                raise ValueError("Seasonal Naive seed convention differs")
            for method in SEEDED_METHODS:
                if {row["seed"] for row in rows if row["method"] == method} != {7, 11, 19}:
                    raise ValueError(f"Development seed coverage differs: {method}")
            for config in CONFIDENCE_CONFIGS:
                if {
                    row["seed"]
                    for row in rows
                    if row["method"] == "confidence" and row["config_id"] == config
                } != {7, 11, 19}:
                    raise ValueError(f"Development confidence seed coverage differs: {config}")
        if len(proxies[budget]) != 3 * expected_groups[budget]:
            raise ValueError(f"Block28 proxy count differs at {budget} days")
        wall = [sum(row["stage_wall_seconds"] for row in rows) for rows in entity_groups]
        storage = [
            sum(
                row["stage_output_bytes_before_measurement"] + row["zip_member_compressed_bytes"]
                for row in rows
            )
            for rows in entity_groups
        ]
        proxy_wall = [row["stage_wall_seconds"] for row in proxies[budget]]
        proxy_storage = [
            row["stage_output_bytes_before_measurement"] + row["zip_member_compressed_bytes"]
            for row in proxies[budget]
        ]
        budget_rows.append(
            {
                "budget_days": budget,
                "observed_entity_groups": len(entity_groups),
                "observed_jobs_per_entity_group": 34,
                "unmeasured_main_and_block7_jobs_per_group": 6,
                "group_stage_wall_median_seconds": statistics.median(wall),
                "group_stage_wall_p95_seconds": percentile(wall, 0.95),
                "group_raw_plus_zip_median_bytes": statistics.median(storage),
                "group_raw_plus_zip_p95_bytes": percentile(storage, 0.95),
                "block28_proxy_stage_wall_median_seconds": statistics.median(proxy_wall),
                "block28_proxy_stage_wall_p95_seconds": percentile(proxy_wall, 0.95),
                "block28_proxy_raw_plus_zip_median_bytes": statistics.median(proxy_storage),
                "block28_proxy_raw_plus_zip_p95_bytes": percentile(proxy_storage, 0.95),
            }
        )
    scenario_rows = []
    for entities in SCOPE_COUNTS:
        median_seconds = sum(
            entities
            * (
                row["group_stage_wall_median_seconds"]
                + 6 * row["block28_proxy_stage_wall_median_seconds"]
            )
            for row in budget_rows
        )
        p95_seconds = sum(
            entities
            * (
                row["group_stage_wall_p95_seconds"]
                + 6 * row["block28_proxy_stage_wall_p95_seconds"]
            )
            for row in budget_rows
        )
        p95_bytes = sum(
            entities
            * (
                row["group_raw_plus_zip_p95_bytes"]
                + 6 * row["block28_proxy_raw_plus_zip_p95_bytes"]
            )
            for row in budget_rows
        )
        scenario_rows.append(
            {
                "candidate_urban_entities": entities,
                "budgets": 3,
                "physical_jobs_per_entity_budget_assumed": 40,
                "candidate_physical_jobs": entities * 3 * 40,
                "stage_wall_median_scenario_hours": round(median_seconds / 3600, 3),
                "stage_wall_observed_p95_scenario_hours": round(p95_seconds / 3600, 3),
                "raw_plus_zip_observed_p95_bytes": round(p95_bytes),
                "raw_plus_zip_p95_with_1_5_margin_bytes": round(p95_bytes * 1.5),
                "scope": "UrbanEV/SZH candidate only; excludes CHARGED and Source fit/provider overhead",
            }
        )
    return scenario_rows, {"budget_strata": budget_rows}


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output_dir.resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError("Output must be a new directory inside repository")
    ledger_path = root / "docs/reports/hung-development-782-job-ledger-20261028-v5.csv"
    if digest(ledger_path) != LEDGER_SHA256:
        raise ValueError("Development ledger SHA differs")
    with ledger_path.open(newline="", encoding="utf-8") as stream:
        ledger = list(csv.DictReader(stream))
    records = measure(root, ledger)
    scenario_rows, detail = scenarios(records)
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / "measured_development_jobs.csv", records)
    write_csv(output / "candidate_scenarios.csv", scenario_rows)
    (output / "summary.json").write_text(
        json.dumps(
            {
                "schema": "hung-final-resource-preflight-v1",
                "status": "CANDIDATE_SCENARIOS_NOT_CAPACITY_APPROVAL",
                "ledger_sha256": LEDGER_SHA256,
                "measured_development_jobs": len(records),
                "measured_archives": len({row["archive_sha256"] for row in records}),
                **detail,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"jobs": len(records), "scenarios": scenario_rows}))


if __name__ == "__main__":
    main()
