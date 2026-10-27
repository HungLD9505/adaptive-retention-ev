"""Prepare outcome-blind whole-unit replay partitions; never fit or dispatch models."""

import argparse
import copy
import json
from pathlib import Path

from ev_models.checkpoint import digest, write_json
from tools.export_development import safe_name


def prepare(
    ledger_path: Path,
    ledger_sha256: str,
    template_path: Path,
    template_sha256: str,
    output: Path,
) -> dict:
    """Select the first pending UrbanEV identity, preserving exact reference configs.

    The ledger and an accepted Colab reference template must be externally pinned.
    Template environment describes the required new execution, not old outcomes.
    This prepares both partitions; publication verification still gates dispatch.
    """
    if digest(ledger_path) != ledger_sha256 or digest(template_path) != template_sha256:
        raise ValueError("Changed ledger or runtime reference")
    ledger = json.loads(ledger_path.read_text())
    template = json.loads(template_path.read_text())
    if ledger["schema"] != "ev-current-whole-unit-remaining-ledger-v1":
        raise ValueError("Expected current whole-unit ledger")
    unit = ledger["remaining_units"][0]
    dataset, city, budget, entity, seed = unit["unit"]
    if (dataset, city) != ("urbanev", "SZH") or budget not in (7, 14, 28):
        raise ValueError("Primary Development only; city migration needs its own context")
    if seed not in (42, 43, 44) or any(
        row["unit"] == unit["unit"] for row in ledger["retained_complete_units_excluding_JHB"]
    ):
        raise ValueError("Unexpected seed or already complete unit")
    required = set(ledger["required_variants"])
    if len(required) != 14 or set(unit["methods"]) != required:
        raise ValueError("All fourteen unique methods required")
    matrices = []
    pins = ledger["pins"]
    for pin in pins:
        if Path(pin["path"]).name in (
            "proxy-selected-original-matrix.json",
            "matched-selected-original-matrix.json",
        ):
            path = Path(pin["path"])
            if digest(path) != pin["sha256"]:
                raise ValueError("Changed original reference matrix")
            value = json.loads(path.read_text())
            if value["status"] != "technical_success":
                raise ValueError("Incomplete original reference")
            matrices.append(value)
    if len(matrices) != 2:
        raise ValueError("Both original reference matrices required")
    if template["code"]["dirty"] or set(template["sources"]) != {"42", "43", "44"}:
        raise ValueError("Clean reference and all three original Sources required")
    for matrix in matrices:
        for source_seed in ("42", "43", "44"):
            if (
                matrix["sources"][source_seed]["sha256"]
                != template["sources"][source_seed]["sha256"]
                or template["sources"][source_seed]["epochs"] != 10
            ):
                raise ValueError("Source duration or ensemble identity changed")
    rows = []
    for matrix in matrices:
        for original in matrix["runs"]:
            binding, config = original["binding"]["input"], original["binding"]["config"]
            if (
                binding["history_days"],
                binding["entity_id"],
                config["initial_training"]["seed"],
            ) != (
                budget,
                entity,
                seed,
            ):
                continue
            row = copy.deepcopy(original)
            variant = row.setdefault("comparison_variant", config["method"]["name"])
            expected = unit["methods"][variant]
            safe_name(row["run_id"])
            if (
                (binding["dataset_id"], binding["city_id"], binding["stage"])
                != (dataset, city, "target")
                or config != expected["config"]
                or row["run_id"] != expected["run_id"]
                or config["replay_days"] != 90
                or binding["input_manifest_sha256"] != expected["input_manifest_sha256"]
                or binding["source_checkpoint_sha256"] != expected["source_checkpoint_sha256"]
                or row["code"]["dirty"]
                or row["code"]["files"] != template["code"]["files"]
                or matrix["sources"][str(seed)]["sha256"]
                != template["sources"][str(seed)]["sha256"]
            ):
                raise ValueError("Changed original input/config/Source/core identity")
            rows.append(row)
    rows.sort(key=lambda row: row["comparison_variant"])
    if len(rows) != 14 or {r["comparison_variant"] for r in rows} != required:
        raise ValueError("Missing or duplicate original method")
    output.mkdir(parents=True, exist_ok=False)
    declaration = {
        "schema": "ev-colab-whole-unit-migration-v1",
        "scope": "Development migration preparation only; no dispatch, new outcomes or Final",
        "remaining_ledger_sha256": ledger_sha256,
        "runtime_template_sha256": template_sha256,
        "chosen_unit": unit["unit"],
        "declared_repeat_cells": unit["old_accepted_cells_to_repeat_if_migrating"],
        "required_variants": sorted(required),
        "rows": rows,
    }
    write_json(output / "whole-unit.json", declaration)
    for start, stop in ((0, 12), (12, 14)):
        part = output / f"{start:04d}-{stop:04d}"
        part.mkdir()
        reference = {**copy.deepcopy(template), "runs": rows[start:stop]}
        reference["scope"] = "Historical rows are references; runtime profile is migration-only"
        write_json(part / "reference.json", reference)
        sources = {
            str(s): {
                "path": f"source-seed{s}/epoch-10.pt",
                "sha256": template["sources"][str(s)]["sha256"],
            }
            for s in (42, 43, 44)
        }
        ids = [row["run_id"] for row in rows[start:stop]]
        write_json(
            part / "plan.json",
            {
                "schema": "exact-missing-development-recovery-v1",
                "scope": "Whole-unit migration partition; externally verify first12 before last2",
                "sources": sources,
                "families": {
                    "matched": {
                        "original_matrix": "reference.json",
                        "original_matrix_sha256": digest(part / "reference.json"),
                        "original_total": len(ids),
                        "preserved_ids": [],
                        "replay_ids": ids,
                    }
                },
                "whole_unit_sha256": digest(output / "whole-unit.json"),
            },
        )
    return declaration


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ledger", "template", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("ledger-sha256", "template-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    value = prepare(
        args.ledger, args.ledger_sha256, args.template, args.template_sha256, args.output
    )
    print(json.dumps({"prepared_unit": value["chosen_unit"], "dispatch": False}))


if __name__ == "__main__":
    main()
