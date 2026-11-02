"""Verify frozen Final-role prefix training inventories without outcome analysis."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

from tools.hung_final_scope_gap import INPUTS, JOBSET, LOCK, PREFIX, read_frozen_inputs

ROOT = Path(__file__).resolve().parents[1]
GAP = ROOT / "docs/reports/hung-final-scope-gap-20261029-v1/scope_gap.csv"
GAP_SHA = "c4c7a067bb45c048c4ec2da58b321d72033e23e3a4467e5378069a6ce68bd681"
SOURCE_AUDIT = ROOT / "docs/reports/hung-final-scope-source-audit-20261030-v4.json"
SOURCE_AUDIT_SHA = "11b443ea1f0ad2f3b8394d75590aba4c55a7c1138256230707f941c4c6e0e0d6"
BUDGETS = (7, 14, 28)


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _check_training_row(row: dict, entity: dict, manifest: dict, deployment: datetime) -> None:
    forecast = row["forecast"]
    entity_id = str(entity["identity"][2])
    if (
        row["role"] != "final"
        or forecast["identity"] != ["urbanev", "SZH", entity_id]
        or forecast["input_run_id"] != manifest["run_id"]
        or forecast["scale_id"] != entity["scale"]["fit_sha256"]
        or forecast["clock_mode"] != "offset-aware-local"
        or len(forecast["history_labels"]) != 24
        or len(forecast["future_labels"]) != 24
        or len(forecast["x_hist"]) != 24
        or len(forecast["c_future"]) != 24
        or any(len(hour) != 7 for hour in forecast["x_hist"])
        or any(len(hour) != 5 for hour in forecast["c_future"])
        or len(row["y_kwh"]) != 24
        or len(row["y_scaled"]) != 24
        or not math.isfinite(forecast["energy_scale"])
        or forecast["energy_scale"] <= 0
        or forecast["energy_scale"] != entity["scale"]["energy_scale"]
        or any(
            not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0
            for value in row["y_kwh"]
        )
        or any(
            not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0
            for value in row["y_scaled"]
        )
    ):
        raise ValueError(f"Invalid Final prefix training row for {entity_id}")
    origin = datetime.fromisoformat(forecast["origin"])
    history = [datetime.fromisoformat(value) for value in forecast["history_labels"]]
    future = [datetime.fromisoformat(value) for value in forecast["future_labels"]]
    last_label = datetime.fromisoformat(forecast["future_labels"][-1])
    if (
        origin >= deployment
        or last_label >= deployment
        or history != [origin - timedelta(hours=24 - hour) for hour in range(24)]
        or future != [origin + timedelta(hours=hour) for hour in range(24)]
    ):
        raise ValueError(f"Final prefix training crosses deployment for {entity_id}")


def _count_member(
    archive: ZipFile, member: str, expected: dict, entities: dict[str, dict], manifest: dict
) -> tuple[Counter, dict[str, set[str]]]:
    digest = hashlib.sha256()
    size = 0
    counts: Counter[str] = Counter()
    origins: dict[str, set[str]] = defaultdict(set)
    deployment = datetime.fromisoformat(manifest["config"]["deployment"])
    if manifest["config"]["availability_delay_hours"] != 0:
        raise ValueError("Prefix label availability delay differs")
    with archive.open(member) as stream:
        for line in stream:
            digest.update(line)
            size += len(line)
            # The member is SHA-pinned. This fast filter avoids decoding Source and
            # Development training values; all Final rows are counted below.
            if b'"role": "final"' not in line:
                continue
            row = json.loads(line)
            if row.get("role") != "final":
                raise ValueError("Final-role filter mismatch")
            entity_id = str(row["forecast"]["identity"][2])
            if entity_id not in entities:
                raise ValueError(f"Unknown Final training entity: {entity_id}")
            _check_training_row(row, entities[entity_id], manifest, deployment)
            origin = row["forecast"]["origin"]
            if origin in origins[entity_id]:
                raise ValueError(f"Duplicate Final prefix origin for {entity_id}")
            origins[entity_id].add(origin)
            counts[entity_id] += 1
    if size != expected["size_bytes"] or digest.hexdigest() != expected["sha256"]:
        raise ValueError(f"Frozen training member bytes/SHA differ: {member}")
    if counts != Counter(
        {
            entity_id: entity["initial_trainable"]
            for entity_id, entity in entities.items()
            if entity["initial_trainable"] > 0
        }
    ):
        raise ValueError("Actual Final prefix row counts differ from entity metadata")
    return counts, origins


def audit() -> dict:
    if _sha(GAP) != GAP_SHA or _sha(SOURCE_AUDIT) != SOURCE_AUDIT_SHA:
        raise ValueError("Pinned gap or Source audit changed")
    source_audit = json.loads(SOURCE_AUDIT.read_text(encoding="utf-8"))
    if (
        source_audit["source_checkpoints_verified"] != 9
        or source_audit["locked_jobset_source_bindings_verified"] != 360
    ):
        raise ValueError("Source lineage prerequisite differs")
    jobset, entities_by_budget, manifest_shas = read_frozen_inputs(LOCK, JOBSET, INPUTS)
    selected = {str(job["entity_id"]) for job in jobset["jobs"]}
    with GAP.open(newline="", encoding="utf-8") as stream:
        gap = list(csv.DictReader(stream))
    omitted = {row["entity_id"] for row in gap}
    if len(selected) != 3 or len(omitted) != 370 or selected & omitted:
        raise ValueError("Frozen cohort identity differs")
    qualifying_by_budget = {}
    budget_records = []
    with ZipFile(INPUTS) as archive:
        for budget in BUDGETS:
            base = f"{PREFIX}/urbanev-SZH-{budget}d/"
            manifest_bytes = archive.read(base + "manifest.json")
            if hashlib.sha256(manifest_bytes).hexdigest() != manifest_shas[budget]:
                raise ValueError("Budget manifest differs")
            manifest = json.loads(manifest_bytes)
            entities = entities_by_budget[budget]
            if set(entities) != selected | omitted:
                raise ValueError("Budget Final-role ID set differs")
            counts, _ = _count_member(
                archive,
                base + "training.jsonl",
                manifest["files"]["training.jsonl"],
                entities,
                manifest,
            )
            qualifying = {
                entity_id
                for entity_id in omitted
                if entities[entity_id]["status"] == "ready"
                and entities[entity_id]["initialization"] == "target_initial_adaptation"
                and entities[entity_id]["scheduled_forecasts"] > 0
                and counts[entity_id] > 0
            }
            qualifying_by_budget[budget] = qualifying
            budget_records.append(
                {
                    "budget_days": budget,
                    "input_manifest_sha256": manifest_shas[budget],
                    "training_member_bytes": manifest["files"]["training.jsonl"]["size_bytes"],
                    "training_member_sha256": manifest["files"]["training.jsonl"]["sha256"],
                    "final_prefix_rows": sum(counts.values()),
                    "final_ids_with_prefix_rows": len(counts),
                    "omitted_ids_with_prefix_rows": len(set(counts) & omitted),
                    "omitted_ids_qualifying_input_inventory": len(qualifying),
                    "metadata_count_mismatches": 0,
                    "invalid_or_late_prefix_rows": 0,
                }
            )
    all_budget = set.intersection(*(qualifying_by_budget[budget] for budget in BUDGETS))
    if len(all_budget) != 326 or [len(qualifying_by_budget[b]) for b in BUDGETS] != [326, 326, 330]:
        raise ValueError("Qualifying frozen prefix ID counts changed")
    id_bytes = ("\n".join(sorted(all_budget, key=int)) + "\n").encode("utf-8")
    return {
        "schema": "hung-final-prefix-inventory-v1",
        "scope": "frozen pre-deployment Final-role training inventory; no model selection or held-out score",
        "input_zip_sha256": source_audit["frozen_input_zip_sha256"],
        "lock_sha256": source_audit["frozen_lock_sha256"],
        "gap_csv_sha256": GAP_SHA,
        "source_audit_sha256": SOURCE_AUDIT_SHA,
        "omitted_ids": len(omitted),
        "all_budget_qualifying_omitted_ids": len(all_budget),
        "all_budget_qualifying_id_set_sha256": hashlib.sha256(id_bytes).hexdigest(),
        "budgets": budget_records,
        "disposition": "PREFIX_ROW_INVENTORY_VERIFIED_NOT_METHOD_EXECUTION_OR_EXTENSION_LOCK",
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
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "sha256": _sha(output),
                "all_budget_ids": result["all_budget_qualifying_omitted_ids"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
