"""Read-only Development coverage audit; no lock approval or Final execution."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

BASELINES = (
    "seasonal_naive",
    "target_only",
    "frozen_source",
    "full_finetuning",
    "fixed_retention",
    "online_best",
    "source_error",
    "uncertainty",
    "drift",
)
ABLATIONS = {
    "without_confidence": ("without_confidence",),
    "fixed_lambda": ("fixed_lambda",),
    "parameter_retention": ("parameter_retention",),
    "different_block_size": ("block7", "block28"),
    "without_source_initialization": ("no_source",),
}


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def audit(plan: dict, coverage: dict, records: list[dict]) -> dict:
    """Count logical seed views separately from unique authenticated artifacts."""
    require(plan["scope"] == coverage["scope"] == "development_only", "Development only")
    seeds = plan["seeds"]
    require(len(seeds) >= 3 and len(seeds) == len(set(seeds)), "Three distinct seeds required")
    require(
        len(plan["budgets"]) == 3 and set(plan["budgets"]) == {7, 14, 28},
        "7/14/28 budgets required",
    )
    cells = plan["cells"]
    grid = {(c["budget"], c["seed"], c["entity_id"]): c for c in cells}
    require(len(grid) == len(cells), "Duplicate logical cell")
    require(len({c["id"] for c in cells}) == len(cells), "Duplicate cell ID")
    require(all(c["seed"] in seeds and c["budget"] in {7, 14, 28} for c in cells), "Foreign cell")
    for budget in (7, 14, 28):
        entities = {c["entity_id"] for c in cells if c["budget"] == budget}
        require(bool(entities), "Missing budget cohort")
        require(
            all((budget, seed, entity) in grid for seed in seeds for entity in entities),
            "Incomplete station/seed cohort",
        )
    scheduled = {j["id"] for j in plan["jobs"]}
    require(len(scheduled) == len(plan["jobs"]), "Duplicate scheduled job")
    reused = set(coverage["reused_jobs"])
    external = set(coverage["external_complete_jobs"])
    require(
        not (scheduled & reused or scheduled & external or reused & external), "Job class overlap"
    )
    declared = scheduled | reused | external
    aliases = coverage["aliases"]
    require(set(aliases) == {"fixed_lambda", "without_confidence"}, "Unexpected comparison alias")
    require(aliases.get("fixed_lambda") == "fixed_retention", "Fixed lambda alias differs")
    require(aliases.get("without_confidence") in {None, "online_best"}, "Confidence alias differs")
    available = {}
    for row in records:
        job_id = row["job_id"]
        require(job_id in declared and job_id not in available, "Foreign/duplicate artifact")
        require(row["status"] in {"VERIFIED_REUSE", "DISPATCH_VERIFIED"}, "Unverified artifact")
        # A new metric catalog must not silently promote historical unmatched evidence.
        require(
            job_id not in external, "External unmatched evidence requires a reviewed disposition"
        )
        available[job_id] = row
    families = ("main", *BASELINES, *(v for variants in ABLATIONS.values() for v in variants))
    rows = []
    for family in families:
        physical = aliases.get(family) or family
        matched, scorable, missing, unmatched, artifacts = [], [], [], [], set()
        for cell in cells:
            original = (
                grid[(cell["budget"], seeds[0], cell["entity_id"])]
                if physical == "seasonal_naive"
                else cell
            )
            job_id = physical + "_" + original["id"]
            require(job_id in declared, f"Undeclared mandatory comparison: {job_id}")
            if job_id in external:
                unmatched.append(cell["id"])
                continue
            record = available.get(job_id)
            if record is None:
                missing.append(cell["id"])
                continue
            require(
                (record["method"], record["budget"], record["seed"], record["entity_id"])
                == (physical, original["budget"], original["seed"], original["entity_id"]),
                "Artifact family/cell differs",
            )
            require(
                record["input_manifest_sha256"] == cell["input_manifest_sha256"],
                "Aliased input identity differs",
            )
            if physical == "seasonal_naive":
                require(
                    record.get("source_sha256") is None and record.get("target_sha256") is None,
                    "Seasonal Naive cannot alias model initialization",
                )
            matched.append(cell["id"])
            artifacts.add(job_id)
            if record["metrics"] is not None:
                scorable.append(cell["id"])
        rows.append(
            {
                "family": family,
                "physical_family": physical,
                "required_logical_cells": len(cells),
                "matched_logical_cells": len(matched),
                "scorable_logical_cells": len(scorable),
                "unique_authenticated_artifacts": len(artifacts),
                "seed_views_are_independent": physical != "seasonal_naive",
                "by_budget": {
                    str(budget): {
                        "required": sum(c["budget"] == budget for c in cells),
                        "matched": sum(c["budget"] == budget and c["id"] in matched for c in cells),
                        "scorable": sum(
                            c["budget"] == budget and c["id"] in scorable for c in cells
                        ),
                    }
                    for budget in (7, 14, 28)
                },
                "unmatched_cells": unmatched,
                "no_authenticated_metric_cells": missing,
                "zero_scored_cells": sorted(set(matched) - set(scorable)),
            }
        )
    return {
        "schema": "hung-development-coverage-audit-v1",
        "scope": "development_only",
        "baseline_families": list(BASELINES),
        "ablation_categories": ABLATIONS,
        "seeds": seeds,
        "cells": len(cells),
        "scheduled_physical_jobs": len(scheduled),
        "historical_reuse_jobs": len(reused),
        "historical_unmatched_jobs": len(external),
        "unique_authenticated_metric_artifacts": len(available),
        "matched_family_cell_coverage_complete": all(
            r["matched_logical_cells"] == len(cells) for r in rows
        ),
        "rows": rows,
        "observed_physical_methods": dict(Counter(r["method"] for r in records)),
        "interpretation": "Absent metric evidence does not prove a job was not executed. Aliases reuse artifacts, not independent observations. Zero scored labels do not become zero errors.",
        "final_authorization": "Not evaluated; this tool cannot approve a lock or execute Final",
        "other_required_gates": [
            "Independent Block-7 fairness disposition and scientific review",
            "Reviewed label coverage, exclusions and eligible evaluation cohorts",
            "Station/time uncertainty, context/seed stability, switching and isolated audit analysis",
            "Accepted data/provider scope and immutable configuration/cohort/code lock",
            "Measured capacity and storage readback for the locked Final matrix",
        ],
    }


def main() -> None:
    from experiments.supporting_pipeline.dispatch_state import atomic_create
    from tools.hung_results import verified_file, verify_artifacts

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(
        verified_file(
            {"path": str(args.spec), "sha256": args.spec_sha256}, args.project_root
        ).read_bytes()
    )
    values = {
        k: json.loads(verified_file(p, args.project_root).read_bytes()) for k, p in spec.items()
    }
    plan, derivation, coverage, catalog = (
        values[k] for k in ("plan", "derivation", "coverage", "catalog")
    )
    parent = json.loads(verified_file(derivation["parent_plan"], args.project_root).read_bytes())
    require(
        derivation["derived_plan"]["sha256"] == spec["plan"]["sha256"]
        and derivation["parent_plan"]["sha256"] == coverage["plan_sha256"]
        and plan["jobs"] == parent["jobs"]
        and plan["cells"] == parent["cells"],
        "Coverage derivation changed job/cell identities",
    )
    require(
        all(plan[k] == parent[k] for k in ("budgets", "seeds", "selection", "input_base"))
        and {c["id"]: c["sha256"] for c in plan["configs"]}
        == {c["id"]: c["sha256"] for c in parent["configs"]},
        "Coverage derivation changed configuration/data contract",
    )
    require(catalog["spec"]["plan"]["sha256"] == spec["plan"]["sha256"], "Catalog plan differs")
    configs = {c["id"]: c for c in plan["configs"]}
    if coverage["aliases"].get("without_confidence") == "online_best":
        config = json.loads(
            verified_file(configs["without_confidence"], args.project_root).read_bytes()
        )
        require(config["replay"]["delta"] == 0, "Positive margin cannot alias Online Best")
        online = json.loads(verified_file(configs["online_best"], args.project_root).read_bytes())
        require(
            config["replay"].pop("selection_rule") == "without_confidence"
            and online["replay"].pop("selection_rule") == "online_best_lambda"
            and config == online,
            "Aliased comparison configuration differs",
        )
    records = verify_artifacts(catalog, args.project_root)
    result = audit(plan, coverage, records)
    result["provenance"] = {"spec_sha256": args.spec_sha256, "inputs": spec}
    require(
        args.output.resolve().is_relative_to(args.project_root.resolve()), "Output outside project"
    )
    atomic_create(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k not in {"rows", "provenance"}}))


if __name__ == "__main__":
    main()
