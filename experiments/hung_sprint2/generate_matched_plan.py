"""Create a pinned representative Development matrix plan from reviewed inputs.

This command never starts a model process. Reused runs require exact manifest
and checkpoint identities; missing dependencies stop plan generation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2 import dispatch_matched as dispatch
from experiments.hung_sprint2.matched_plan_provenance import (
    BASELINE_METHODS,
    CONFIG_NAMES,
    TARGET_NAMES,
    cell_id,
    comparable_configs,
    pinned_file,
    pinned_json,
    require,
    verify_checkpoint_grid,
    verify_lambda,
    verify_reuse,
)


def generate(recipe_path: Path, recipe_sha256: str, output: Path, coverage_output: Path) -> dict:
    recipe = dispatch.read_verified_json(recipe_path, recipe_sha256)
    require(
        recipe.get("schema") == "hung-matched-plan-generator-v1"
        and recipe.get("scope") == "development_only",
        "Bad generator recipe",
    )
    require(
        set(recipe)
        == {
            "schema",
            "scope",
            "code_commit",
            "selection",
            "input_base",
            "lambda",
            "configs",
            "sources",
            "targets",
            "existing_runs",
            "output_root",
        },
        "Recipe fields mismatch",
    )
    code = dispatch._code_identity()
    require(
        recipe["code_commit"] == code["commit"] and code["worktree_status"] == [],
        "Code identity differs or tracked worktree dirty",
    )
    require(
        not output.exists() and not coverage_output.exists(), "Create-only output already exists"
    )
    require(output != coverage_output, "Plan and coverage outputs must differ")
    for path in (output, coverage_output):
        require(path.is_relative_to(dispatch.ROOT.resolve()), "Output outside worktree")
        require(
            dispatch.subprocess.run(
                ["git", "check-ignore", "-q", "--no-index", str(path)],
                cwd=dispatch.ROOT,
                check=False,
            ).returncode
            == 0,
            "Plan output must be Git-ignored",
        )
    selection = pinned_json(recipe["selection"])
    input_base = dispatch.project_path(recipe["input_base"])
    require(input_base.is_dir(), "Accepted Development input base missing")
    output_root = dispatch.project_path(recipe["output_root"])
    require(
        output_root.is_relative_to(dispatch.ROOT.resolve()) and not output_root.exists(),
        "Output root must be new inside worktree",
    )
    require(
        dispatch.subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", str(output_root)],
            cwd=dispatch.ROOT,
            check=False,
        ).returncode
        == 0,
        "Run output root must be Git-ignored",
    )
    require(set(selection["budgets"]) == {"7", "14", "28"}, "Selection budget grid differs")
    config_specs = recipe["configs"]
    require(
        isinstance(config_specs, dict) and set(config_specs) == set(CONFIG_NAMES),
        "All reviewed configs required",
    )
    require(
        all(
            dispatch.project_path(spec["path"]).is_relative_to(dispatch.ROOT.resolve())
            for spec in config_specs.values()
        ),
        "All configs must be inside worktree",
    )
    configs = {name: pinned_json(spec) for name, spec in config_specs.items()}
    comparable_configs(configs)
    chosen = verify_lambda(
        recipe["lambda"], configs["parameter_retention"], recipe["selection"]["sha256"]
    )
    seeds = [7, 11, 19]
    require(configs["main"]["seeds"] == seeds, "Seed grid must be 7/11/19")
    cells = []
    for budget in (7, 14, 28):
        selected = selection["budgets"][str(budget)]
        for seed in seeds:
            for entity in selected["representative_entities"]:
                cells.append(
                    {
                        "id": cell_id(budget, seed, entity["entity_id"]),
                        "budget": budget,
                        "seed": seed,
                        "entity_id": entity["entity_id"],
                        "input_manifest_sha256": selected["manifest_sha256"],
                    }
                )
    require(
        len(cells) == 69 and len({x["id"] for x in cells}) == 69,
        "Expected 69 unique representative cells",
    )
    source_specs = recipe["sources"]
    require(isinstance(source_specs, list) and len(source_specs) == 9, "Nine Source pins required")
    sources = {}
    for row in source_specs:
        require(set(row) == {"budget", "seed", "checkpoint"}, "Source pin fields mismatch")
        key = (row["budget"], row["seed"])
        require(key not in sources, "Duplicate Source pin")
        sources[key] = pinned_file(row["checkpoint"])
    require(set(sources) == {(b, s) for b in (7, 14, 28) for s in seeds}, "Source grid incomplete")
    target_specs = recipe["targets"]
    require(
        isinstance(target_specs, list) and len(target_specs) == 69 * len(TARGET_NAMES),
        "Every target variant/cell needs an explicit pin or create declaration",
    )
    targets = {}
    for row in target_specs:
        require(
            set(row) == {"cell", "variant", "mode", "checkpoint"},
            "Target declaration fields mismatch",
        )
        key = (row["cell"], row["variant"])
        require(
            key not in targets and row["variant"] in TARGET_NAMES,
            "Duplicate/unknown target declaration",
        )
        require(row["mode"] in {"reuse", "create"}, "Target mode must be explicit")
        require(
            (row["mode"] == "create") == (row["checkpoint"] is None),
            "Target checkpoint/mode mismatch",
        )
        targets[key] = None if row["mode"] == "create" else pinned_file(row["checkpoint"])
    require(
        set(targets) == {(c["id"], v) for c in cells for v in TARGET_NAMES},
        "Target grid incomplete",
    )
    verify_checkpoint_grid(cells, sources, targets, configs, selection, input_base, code)
    jobs = []
    cell_by_id = {c["id"]: c for c in cells}

    def add(
        name: str,
        cell: dict,
        config: str,
        method: str,
        target: str | None,
        *,
        source: bool = True,
        device: str = "cuda",
    ) -> None:
        jobs.append(
            {
                "id": f"{name}_{cell['id']}",
                "cell": cell["id"],
                "config": config,
                "method": method,
                "device": device,
                "source": sources[(cell["budget"], cell["seed"])] if source else None,
                "target": targets[(cell["id"], target)] if target else None,
            }
        )

    for cell in cells:
        add("main", cell, "main", "confidence", "main")
        add("target_only", cell, "main", "target_only", None, source=False)
        add("frozen_source", cell, "main", "frozen_source", None)
        for name, method in BASELINE_METHODS:
            target = name if name in TARGET_NAMES else "main"
            add(name, cell, name, method, target)
        if configs["without_confidence"]["replay"]["delta"] > 0:
            add("without_confidence", cell, "without_confidence", "without_confidence", "main")
        add("parameter_retention", cell, "parameter_retention", "confidence", "parameter_retention")
        add("block7", cell, "block7", "confidence", "main")
        add("block28", cell, "block28", "confidence", "main")
        add("no_source", cell, "no_source", "confidence", "no_source")
        if cell["seed"] == seeds[0]:
            add("seasonal_naive", cell, "main", "seasonal_naive", None, source=False, device="cpu")
    job_by_id = {job["id"]: job for job in jobs}
    require(len(job_by_id) == len(jobs), "Duplicate job ID")
    reused = {}
    rerun_existing = {}
    decisions = recipe["existing_runs"]
    require(isinstance(decisions, list), "Explicit existing-run decisions required")
    expected_existing = {job_id for job_id in job_by_id if job_id.startswith(("main_", "block7_"))}
    seen_decisions = set()
    for row in decisions:
        require(
            isinstance(row, dict) and set(row) == {"job_id", "action", "run_manifest", "reason"},
            "Existing-run decision fields mismatch",
        )
        job_id = row["job_id"]
        require(
            job_id in expected_existing and job_id not in seen_decisions,
            "Unknown/duplicate existing-run decision",
        )
        seen_decisions.add(job_id)
        require(
            isinstance(row["reason"], str) and row["reason"].strip(),
            "Existing-run decision needs reason",
        )
        job = job_by_id[job_id]
        if row["action"] == "reuse":
            require(row["run_manifest"] is not None, "Reused run needs manifest pin")
            verify_reuse(
                {"job_id": job_id, "run_manifest": row["run_manifest"]},
                job,
                cell_by_id[job["cell"]],
                configs[job["config"]],
                code,
            )
            reused[job_id] = row["run_manifest"]
        else:
            require(
                row["action"] == "rerun" and row["run_manifest"] is None,
                "Invalid existing-run decision",
            )
            rerun_existing[job_id] = row["reason"]
    require(
        seen_decisions == expected_existing,
        "Every main/block7 job requires an explicit reuse or rerun decision",
    )
    plan = {
        "schema": "hung-matched-development-dispatch-v1",
        "scope": "development_only",
        "code_commit": code["commit"],
        "selection": recipe["selection"],
        "input_base": recipe["input_base"],
        "budgets": [7, 14, 28],
        "seeds": seeds,
        "configs": [{"id": name, **config_specs[name]} for name in CONFIG_NAMES],
        "cells": cells,
        "jobs": [job for job in jobs if job["id"] not in reused],
        "output_root": recipe["output_root"],
    }
    require(plan["jobs"], "All jobs were marked reused")
    coverage = {
        "schema": "hung-matched-plan-coverage-v1",
        "scope": "development_only",
        "recipe_sha256": recipe_sha256,
        "code_commit": code["commit"],
        "chosen_lambda_low": chosen,
        "declared_cells": len(cells),
        "declared_jobs": len(jobs),
        "scheduled_jobs": len(plan["jobs"]),
        "reused_jobs": reused,
        "rerun_existing_jobs": rerun_existing,
        "aliases": {
            "fixed_lambda": "fixed_retention",
            "without_confidence": "online_best"
            if configs["without_confidence"]["replay"]["delta"] == 0
            else None,
        },
        "plan_sha256": None,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    coverage_output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(plan, stream, indent=2, sort_keys=True)
        stream.write("\n")
    coverage["plan_sha256"] = sha256_file(output)
    with coverage_output.open("x", encoding="utf-8") as stream:
        json.dump(coverage, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return coverage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--recipe-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--coverage-output", type=Path, required=True)
    args = parser.parse_args(argv)
    recipe = dispatch.project_path(args.recipe)
    output = dispatch.project_path(args.output)
    coverage = dispatch.project_path(args.coverage_output)
    print(json.dumps(generate(recipe, args.recipe_sha256, output, coverage)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
