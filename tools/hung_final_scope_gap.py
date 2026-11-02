"""Inventory Final-role UrbanEV IDs omitted by Hùng's frozen 360-job Final."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / ".cache/hung-final-lock-20261029T014357Z/lock.json"
JOBSET = ROOT / ".cache/hung-final-lock-20261029T014357Z/jobset.json"
INPUTS = ROOT / ".cache/kaggle-payload-v2/payload/inputs.zip"
OUTPUT = ROOT / "docs/reports/hung-final-scope-gap-20261029-v1"
LOCK_SHA256 = "e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e"
BUDGETS = (7, 14, 28)
PREFIX = "data/inputs/issue18-input-handoff-v1-20261019"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_frozen_inputs(
    lock_path: Path, jobset_path: Path, zip_path: Path
) -> tuple[dict, dict, dict]:
    if sha256_file(lock_path) != LOCK_SHA256:
        raise ValueError("Final lock SHA-256 mismatch")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if (
        jobset_path.stat().st_size != lock["jobset"]["bytes"]
        or sha256_file(jobset_path) != lock["jobset"]["sha256"]
    ):
        raise ValueError("Frozen jobset SHA-256 mismatch")
    if (
        zip_path.stat().st_size != lock["input"]["bytes"]
        or sha256_file(zip_path) != lock["input"]["sha256"]
    ):
        raise ValueError("Frozen input ZIP SHA-256 mismatch")
    jobset = json.loads(jobset_path.read_text(encoding="utf-8"))
    if len(jobset["jobs"]) != lock["jobset"]["count"]:
        raise ValueError("Frozen job count mismatch")
    entities_by_budget = {}
    manifest_shas = {}
    with ZipFile(zip_path) as archive:
        for budget in BUDGETS:
            base = f"{PREFIX}/urbanev-SZH-{budget}d"
            manifest_bytes = archive.read(f"{base}/manifest.json")
            manifest = json.loads(manifest_bytes)
            entities_bytes = archive.read(f"{base}/entities.jsonl")
            expected = manifest["files"]["entities.jsonl"]
            if (
                len(entities_bytes) != expected["size_bytes"]
                or hashlib.sha256(entities_bytes).hexdigest() != expected["sha256"]
            ):
                raise ValueError(f"Entities file binding mismatch at {budget} days")
            rows = [json.loads(line) for line in io.BytesIO(entities_bytes) if line.strip()]
            final = [row for row in rows if row["role"] == "final"]
            keyed = {str(row["identity"][2]): row for row in final}
            if len(keyed) != len(final) or len(keyed) != manifest["counts"]["final"]:
                raise ValueError(f"Final-role identity mismatch at {budget} days")
            entities_by_budget[budget] = keyed
            manifest_shas[budget] = hashlib.sha256(manifest_bytes).hexdigest()
    if any(
        job["budget_days"] not in manifest_shas
        or job["input_manifest_sha256"] != manifest_shas[job["budget_days"]]
        for job in jobset["jobs"]
    ):
        raise ValueError("Frozen job input manifest binding mismatch")
    return jobset, entities_by_budget, manifest_shas


def scope_gap(jobset: dict, entities_by_budget: dict[int, dict]) -> tuple[list[dict], dict]:
    frozen_jobs = jobset["jobs"]
    if len(frozen_jobs) != 360 or len({job["job_id"] for job in frozen_jobs}) != 360:
        raise ValueError("Expected 360 distinct frozen jobs")
    chosen = {str(job["entity_id"]) for job in frozen_jobs}
    if len(chosen) != 3 or any(
        job["dataset_id"] != "urbanev" or job["city_id"] != "SZH" for job in frozen_jobs
    ):
        raise ValueError("Frozen jobset has unexpected cohort")
    sets = [set(entities_by_budget[budget]) for budget in BUDGETS]
    if not (sets[0] == sets[1] == sets[2]) or len(sets[0]) != 373 or not chosen <= sets[0]:
        raise ValueError("Final-role cohort does not match the frozen scope")
    omitted = sorted(sets[0] - chosen, key=int)
    rows = []
    for entity_id in omitted:
        row: dict[str, str | int] = {"entity_id": entity_id}
        for budget in BUDGETS:
            source = entities_by_budget[budget][entity_id]
            if source["identity"] != ["urbanev", "SZH", entity_id]:
                raise ValueError(f"Wrong identity for {entity_id} at {budget} days")
            row[f"status_{budget}d"] = source["status"]
            row[f"initial_trainable_{budget}d"] = source["initial_trainable"]
            row[f"scheduled_forecasts_{budget}d"] = source["scheduled_forecasts"]
        rows.append(row)
    patterns = Counter(tuple(row[f"status_{budget}d"] for budget in BUDGETS) for row in rows)
    summary = {
        "schema": "hung-final-scope-gap-v1",
        "scope": "frozen input Final-role identity accounting; no new evaluation authorization",
        "locked_entity_ids": sorted(chosen, key=int),
        "final_role_ids_per_budget": 373,
        "omitted_final_role_ids": len(rows),
        "ready_all_budgets": sum(
            all(row[f"status_{budget}d"] == "ready" for budget in BUDGETS) for row in rows
        ),
        "undefined_scale_any_budget": sum(
            any(row[f"status_{budget}d"] == "undefined_scale" for budget in BUDGETS) for row in rows
        ),
        "zero_initial_trainable_by_budget": {
            str(budget): sum(row[f"initial_trainable_{budget}d"] == 0 for row in rows)
            for budget in BUDGETS
        },
        "status_patterns": {
            "|".join(pattern): count for pattern, count in sorted(patterns.items())
        },
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=LOCK)
    parser.add_argument("--jobset", type=Path, default=JOBSET)
    parser.add_argument("--inputs", type=Path, default=INPUTS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    jobset, entities, manifest_shas = read_frozen_inputs(args.lock, args.jobset, args.inputs)
    rows, summary = scope_gap(jobset, entities)
    summary["lock_sha256"] = LOCK_SHA256
    summary["jobset_sha256"] = sha256_file(args.jobset)
    summary["input_zip_sha256"] = sha256_file(args.inputs)
    summary["input_manifest_sha256_by_budget"] = {str(k): v for k, v in manifest_shas.items()}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    fieldnames = ["entity_id"] + [
        field
        for budget in BUDGETS
        for field in (
            f"status_{budget}d",
            f"initial_trainable_{budget}d",
            f"scheduled_forecasts_{budget}d",
        )
    ]
    with (args.output_dir / "scope_gap.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
