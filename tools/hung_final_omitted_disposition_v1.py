"""Classify every omitted frozen Final-role ID before any extension decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

from tools.hung_final_scope_gap import BUDGETS, INPUTS, JOBSET, LOCK, ROOT, read_frozen_inputs

GAP = ROOT / "docs/reports/hung-final-scope-gap-20261029-v1/scope_gap.csv"
GAP_SHA = "c4c7a067bb45c048c4ec2da58b321d72033e23e3a4467e5378069a6ce68bd681"
PREFIX = ROOT / "docs/reports/hung-final-prefix-inventory-20261030-v2.json"
PREFIX_SHA = "e2474fb22a16e2d877a7ed43db760e1b96dbf0c9ad29446c08d34ce2dcc01cf2"
SOURCE = ROOT / "docs/reports/hung-final-scope-source-audit-20261030-v4.json"
SOURCE_SHA = "11b443ea1f0ad2f3b8394d75590aba4c55a7c1138256230707f941c4c6e0e0d6"
CONTRACT_FILES = {
    "experiments/hung_sprint2/cli.py": "3ac9bfd8997148f363dc793c7b92c31fd28bdc51a94ec0bc57a1c1f4ae578f1d",
    "experiments/hung_sprint2/single_baseline_cli.py": "8f29bf141fc7d19aadbb8c75cd0667d11ddcf6de5d70ee72b8ac972e0965d1a8",
    "experiments/hung_sprint2/replay_inputs.py": "5f609180d94382f1db48bfd3cc9d5b473f923c50894087d28c447e40092f3c03",
    "experiments/hung_sprint2/dispatch_matched.py": "31fc6c384f5a84a6672b5b9acf798c4f950b15e6fd6996cce3f552f7581a7c97",
}


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def classify_entity(entity_by_budget: dict[int, dict]) -> tuple[str, list[dict]]:
    """Check the frozen input contract and retain the per-budget distinction."""
    budgets = []
    for budget in BUDGETS:
        entity = entity_by_budget[budget]
        status = entity["status"]
        mode = entity["initialization"]
        count = entity["initial_trainable"]
        forecasts = entity["scheduled_forecasts"]
        if type(count) is not int or count < 0 or type(forecasts) is not int or forecasts < 0:
            raise ValueError("Invalid frozen input counts")
        scale = entity.get("scale")
        if status == "ready":
            expected = "target_initial_adaptation" if count else "source_checkpoint_only"
            if (
                mode != expected
                or forecasts == 0
                or not isinstance(scale, dict)
                or not re.fullmatch(r"[0-9a-f]{64}", str(scale.get("fit_sha256")))
                or not isinstance(scale.get("energy_scale"), (float, int))
                or not math.isfinite(scale["energy_scale"])
                or scale["energy_scale"] <= 0
            ):
                raise ValueError("Ready entity violates the frozen initialization contract")
        elif status == "undefined_scale":
            if (
                mode != "blocked_undefined_scale"
                or count != 0
                or forecasts != 0
                or scale is not None
            ):
                raise ValueError("Undefined-scale entity violates blocked coverage contract")
        else:
            raise ValueError(f"Unexpected frozen input status: {status}")
        budgets.append(
            {
                "budget_days": budget,
                "status": status,
                "initialization": mode,
                "initial_trainable": count,
                "scheduled_forecasts": forecasts,
                "scale_fit_sha256": scale["fit_sha256"] if scale is not None else None,
            }
        )
    if any(row["status"] == "undefined_scale" for row in budgets):
        disposition = "UNDEFINED_SCALE_ANY_BUDGET"
    elif any(row["initial_trainable"] == 0 for row in budgets):
        disposition = "ZERO_PREFIX_ANY_BUDGET_READY"
    else:
        disposition = "POSITIVE_PREFIX_ALL_BUDGETS"
    return disposition, budgets


def audit() -> dict:
    if _sha(GAP) != GAP_SHA or _sha(PREFIX) != PREFIX_SHA or _sha(SOURCE) != SOURCE_SHA:
        raise ValueError("Pinned scope or prefix evidence changed")
    prefix = json.loads(PREFIX.read_text(encoding="utf-8"))
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    if (
        prefix["all_budget_qualifying_omitted_ids"] != 326
        or source["source_checkpoints_verified"] != 9
        or source["locked_jobset_source_bindings_verified"] != 360
    ):
        raise ValueError("Pinned input/Source prerequisites differ")
    for relative, expected in CONTRACT_FILES.items():
        if _sha(ROOT / relative) != expected:
            raise ValueError(f"Method contract source changed: {relative}")
    jobset, entities_by_budget, manifest_shas = read_frozen_inputs(LOCK, JOBSET, INPUTS)
    selected = {str(job["entity_id"]) for job in jobset["jobs"]}
    all_ids = set(entities_by_budget[BUDGETS[0]])
    if (
        len(selected) != 3
        or len(all_ids) != 373
        or any(set(entities_by_budget[budget]) != all_ids for budget in BUDGETS)
    ):
        raise ValueError("Frozen Final-role identity set differs")
    omitted = sorted(all_ids - selected, key=int)
    if len(omitted) != 370:
        raise ValueError("Omitted Final-role identity count differs")
    records = []
    for entity_id in omitted:
        by_budget = {budget: entities_by_budget[budget][entity_id] for budget in BUDGETS}
        if any(
            row["identity"] != ["urbanev", "SZH", entity_id] or row["role"] != "final"
            for row in by_budget.values()
        ):
            raise ValueError(f"Frozen Final-role identity differs: {entity_id}")
        disposition, budgets = classify_entity(by_budget)
        records.append({"entity_id": entity_id, "disposition": disposition, "budgets": budgets})
    counts = Counter(row["disposition"] for row in records)
    expected_counts = {
        "POSITIVE_PREFIX_ALL_BUDGETS": 326,
        "ZERO_PREFIX_ANY_BUDGET_READY": 11,
        "UNDEFINED_SCALE_ANY_BUDGET": 33,
    }
    if counts != expected_counts:
        raise ValueError(f"Frozen disposition counts differ: {counts}")
    positive = [
        row["entity_id"] for row in records if row["disposition"] == "POSITIVE_PREFIX_ALL_BUDGETS"
    ]
    positive_sha = hashlib.sha256(("\n".join(positive) + "\n").encode()).hexdigest()
    if positive_sha != prefix["all_budget_qualifying_id_set_sha256"]:
        raise ValueError("Positive-prefix ID set differs from streamed-row inventory")
    return {
        "schema": "hung-final-omitted-disposition-v1",
        "scope": "all omitted frozen Final-role UrbanEV/SZH input identities; no extension authorization or outcome selection",
        "lock_sha256": prefix["lock_sha256"],
        "input_zip_sha256": prefix["input_zip_sha256"],
        "gap_csv_sha256": GAP_SHA,
        "prefix_inventory_sha256": PREFIX_SHA,
        "source_audit_sha256": SOURCE_SHA,
        "input_manifest_sha256_by_budget": {str(k): v for k, v in manifest_shas.items()},
        "contract_file_sha256": CONTRACT_FILES,
        "selected_locked_ids": sorted(selected, key=int),
        "omitted_count": len(records),
        "disposition_counts": dict(sorted(counts.items())),
        "positive_prefix_id_set_sha256": positive_sha,
        "records": records,
        "decision": "INPUT_DISPOSITION_ONLY_REVIEWED_EXTENSION_PROTOCOL_REQUIRED",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT.resolve()) or output.exists() or output.is_symlink():
        raise ValueError("Output must be a new repository path")
    result = audit()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(
        json.dumps(
            {"output": str(output), "sha256": _sha(output), "counts": result["disposition_counts"]},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
