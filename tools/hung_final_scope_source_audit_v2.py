"""Audit reusable Source checkpoints for the omitted frozen Final input IDs.

This is an input and checkpoint inventory. It never reads Final labels or scores.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import torch

from tools.hung_final_scope_gap import (
    INPUTS,
    LOCK,
    LOCK_SHA256,
    read_frozen_inputs,
)
from tools.hung_final_scope_gap import (
    JOBSET as FROZEN_JOBSET,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV_SHA = "05035160f3fef3cf58ebdb9f70deec0475ddd8e0d1f2dd55ee6ec6c87b29302f"
GAP_CSV_SHA = "c4c7a067bb45c048c4ec2da58b321d72033e23e3a4467e5378069a6ce68bd681"
JOBSET_SHA = "7d09583446d9437cec63956f1673c6d1927428ff80ba59a8a876b9391a7c68a2"
SOURCE_CSV = (
    ROOT
    / "docs/reports/hung-final-metadata-preflight-20261029-v1/development_source_candidates.csv"
)
GAP_CSV = ROOT / "docs/reports/hung-final-scope-gap-20261029-v1/scope_gap.csv"
JOBSET = ROOT / "docs/reports/hung-final-candidate-jobset-20261029-v1/candidate_jobset.json"


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _rows(path: Path, expected_sha: str) -> list[dict[str, str]]:
    if _sha(path) != expected_sha:
        raise ValueError(f"Pinned CSV changed: {path}")
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def audit() -> dict:
    sources = _rows(SOURCE_CSV, SOURCE_CSV_SHA)
    gap = _rows(GAP_CSV, GAP_CSV_SHA)
    if len(sources) != 9 or len(gap) != 370:
        raise ValueError("Source or omitted-ID inventory count changed")
    expected_pairs = {(budget, seed) for budget in (7, 14, 28) for seed in (7, 11, 19)}
    found_pairs: set[tuple[int, int]] = set()
    source_rows = []
    manifest_by_budget: dict[int, str] = {}
    for row in sources:
        budget, seed = int(row["budget_days"]), int(row["seed"])
        pair = (budget, seed)
        if pair not in expected_pairs or pair in found_pairs:
            raise ValueError(f"Unexpected or duplicate Source pair: {pair}")
        found_pairs.add(pair)
        path = (ROOT / row["source_checkpoint_path"]).resolve()
        if not path.is_relative_to(ROOT.resolve()) or path.is_symlink():
            raise ValueError(f"Unsafe Source path: {path}")
        if (
            path.stat().st_size != int(row["source_checkpoint_bytes"])
            or _sha(path) != row["source_checkpoint_sha256"]
        ):
            raise ValueError(f"Source bytes/SHA changed: {pair}")
        state = torch.load(path, map_location="cpu", weights_only=True)
        binding = state["input_binding"]
        if (
            state["schema"] != "hung-sprint2-model-v1"
            or state["seed"] != seed
            or binding["stage"] != "source"
            or binding["dataset_id"] != "urbanev"
            or binding["city_id"] != "SZH"
            or binding["entity_id"] is not None
            or binding["input_manifest_sha256"] != row["input_manifest_sha256"]
            or state["architecture"]["hidden_size"] != 64
            or state["architecture"]["gru_layers"] != 2
            or state["architecture"]["history_hours"] != 24
            or state["architecture"]["forecast_hours"] != 24
            or tuple(state["latent_scale"].shape) != (64,)
            or not state["model_state"]
            or not state["optimizer_state"]
        ):
            raise ValueError(f"Source payload identity changed: {pair}")
        record_path = path.parent / "run_manifest.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if (
            record.get("checkpoint_sha256") != row["source_checkpoint_sha256"]
            or record.get("input_binding") != binding
        ):
            raise ValueError(f"Source run manifest lineage changed: {pair}")
        prior = manifest_by_budget.setdefault(budget, row["input_manifest_sha256"])
        if prior != row["input_manifest_sha256"]:
            raise ValueError(f"Budget Source input mismatch: {budget}")
        source_rows.append(
            {
                "budget_days": budget,
                "seed": seed,
                "bytes": path.stat().st_size,
                "sha256": row["source_checkpoint_sha256"],
                "training_step": state["training_step"],
                "code_sha": state["code_sha"],
                "entity_specific": False,
                "run_manifest_bytes": record_path.stat().st_size,
                "run_manifest_sha256": _sha(record_path),
            }
        )
    if found_pairs != expected_pairs:
        raise ValueError("Missing Source pair")
    if _sha(JOBSET) != JOBSET_SHA:
        raise ValueError("Locked jobset fingerprint changed")
    jobset = json.loads(JOBSET.read_text(encoding="utf-8"))
    jobs = jobset["jobs"]
    source_by_pair = {(int(row["budget_days"]), int(row["seed"])): row for row in sources}
    if len(jobs) != 360 or len({job["job_id"] for job in jobs}) != 360:
        raise ValueError("Locked jobset count or identities changed")
    for job in jobs:
        source = source_by_pair[(job["budget_days"], job["seed"])]
        if job["input_manifest_sha256"] != source["input_manifest_sha256"]:
            raise ValueError(f"Jobset input differs from Source: {job['job_id']}")
        expected_source = (
            None
            if job["method"] in {"target_only", "seasonal_naive"}
            else source["source_checkpoint_sha256"]
        )
        if job["source_checkpoint_sha256"] != expected_source:
            raise ValueError(f"Jobset Source differs: {job['job_id']}")
    if len({row["entity_id"] for row in gap}) != 370:
        raise ValueError("Duplicate omitted entity")
    frozen_jobset, entities_by_budget, input_manifest_shas = read_frozen_inputs(
        LOCK, FROZEN_JOBSET, INPUTS
    )
    if (
        _sha(FROZEN_JOBSET) != JOBSET_SHA
        or frozen_jobset != jobset
        or input_manifest_shas != manifest_by_budget
        or _sha(LOCK) != LOCK_SHA256
    ):
        raise ValueError("Frozen ZIP, lock, jobset or Source input binding differs")
    selected = {str(job["entity_id"]) for job in jobs}
    omitted = {row["entity_id"] for row in gap}
    if any(set(entities_by_budget[budget]) - selected != omitted for budget in (7, 14, 28)):
        raise ValueError("Omitted-ID set differs from frozen ZIP")
    ready_by_budget = {}
    for budget in (7, 14, 28):
        ready_by_budget[str(budget)] = sum(
            row[f"status_{budget}d"] == "ready"
            and int(row[f"initial_trainable_{budget}d"]) > 0
            and int(row[f"scheduled_forecasts_{budget}d"]) > 0
            for row in gap
        )
    all_budget_ready = sum(
        all(
            row[f"status_{budget}d"] == "ready"
            and int(row[f"initial_trainable_{budget}d"]) > 0
            and int(row[f"scheduled_forecasts_{budget}d"]) > 0
            for budget in (7, 14, 28)
        )
        for row in gap
    )
    target_metadata_ready = {}
    for budget in (7, 14, 28):
        count = 0
        for row in gap:
            entity = entities_by_budget[budget][row["entity_id"]]
            if (
                entity["status"] != row[f"status_{budget}d"]
                or entity["initial_trainable"] != int(row[f"initial_trainable_{budget}d"])
                or entity["scheduled_forecasts"] != int(row[f"scheduled_forecasts_{budget}d"])
            ):
                raise ValueError(f"Omitted-ID inventory differs at {budget} days")
            if (
                entity["status"] == "ready"
                and entity["initial_trainable"] > 0
                and entity["scheduled_forecasts"] > 0
            ):
                if entity["initialization"] != "target_initial_adaptation" or not entity[
                    "scale"
                ].get("fit_sha256"):
                    raise ValueError(f"Target prefix metadata unavailable at {budget} days")
                count += 1
        target_metadata_ready[str(budget)] = count
    if target_metadata_ready != ready_by_budget:
        raise ValueError("Target prefix metadata counts differ")
    return {
        "schema": "hung-final-scope-source-audit-v2",
        "source_csv_sha256": SOURCE_CSV_SHA,
        "gap_csv_sha256": GAP_CSV_SHA,
        "jobset_sha256": JOBSET_SHA,
        "locked_jobset_source_bindings_verified": len(jobs),
        "frozen_lock_sha256": LOCK_SHA256,
        "frozen_input_zip_sha256": _sha(INPUTS),
        "target_prefix_metadata_ready_by_budget": target_metadata_ready,
        "omitted_ids": len(gap),
        "minimal_input_ready_by_budget": ready_by_budget,
        "minimal_input_ready_all_budgets": all_budget_ready,
        "source_checkpoints_verified": len(source_rows),
        "sources": sorted(source_rows, key=lambda x: (x["budget_days"], x["seed"])),
        "disposition": "SOURCE_AVAILABLE_INPUT_ONLY_NOT_METHOD_READY_OR_NEW_FINAL_LOCK",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT.resolve()) or output.exists() or output.is_symlink():
        raise ValueError("Output must be a new path inside this repository")
    result = audit()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "sha256": _sha(output),
                "sources": len(result["sources"]),
                "all_budget_ready": result["minimal_input_ready_all_budgets"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
