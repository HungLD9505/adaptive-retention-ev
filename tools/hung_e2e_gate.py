"""Read-only artifact ledger and deterministic shard preparation; never train."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import torch

from experiments.hung_sprint2 import dispatch_matched as dispatch
from experiments.hung_sprint2.dispatch_state import atomic_create, make_shards
from experiments.hung_sprint2.matched_plan_provenance import (
    pinned_checkpoint,
    pinned_json,
    verify_reuse,
)


def equal_state(left: object, right: object) -> bool:
    """Exact comparison of model/optimizer/RNG trees, independent of ZIP metadata."""
    if isinstance(left, torch.Tensor):
        return (
            isinstance(right, torch.Tensor)
            and left.dtype == right.dtype
            and left.shape == right.shape
            and torch.equal(left, right)
        )
    if isinstance(left, dict):
        return (
            isinstance(right, dict)
            and left.keys() == right.keys()
            and all(equal_state(value, right[key]) for key, value in left.items())
        )
    if isinstance(left, (tuple, list)):
        return (
            type(left) is type(right)
            and len(left) == len(right)
            and all(equal_state(a, b) for a, b in zip(left, right, strict=True))
        )
    return type(left) is type(right) and left == right


def checkpoint_comparison(left: dict, right: dict) -> dict:
    pinned_checkpoint(left)
    pinned_checkpoint(right)
    a = torch.load(left["path"], map_location="cpu", weights_only=True)
    b = torch.load(right["path"], map_location="cpu", weights_only=True)
    fields = [
        "architecture",
        "seed",
        "training_step",
        "model_state",
        "optimizer_type",
        "optimizer_state",
        "latent_scale",
        "rng_state",
        "initial_model_sha256",
    ]
    return {
        **{key: equal_state(a.get(key), b.get(key)) for key in fields},
        "different_payload_fields": [
            key for key in sorted(a.keys() | b.keys()) if not equal_state(a.get(key), b.get(key))
        ],
    }


def charged_evidence(handoff_pin: dict) -> dict:
    """Recheck the existing six-city evidence index, without implying a fresh full restore."""
    handoff = pinned_json(handoff_pin)
    dispatch.require(
        handoff["schema"] == "charged-six-city-development-handoff-v1", "Unknown CHARGED handoff"
    )
    cities, checked = {}, 0
    for city, record in handoff["cities"].items():
        pins = list(record.get("files", {}).values())
        if "evidence_register" in record:
            pins.append(record["evidence_register"])
        for pin in pins:
            path = dispatch.project_path(pin["path"])
            dispatch.verify_file(path, pin["sha256"])
            dispatch.require(
                path.stat().st_size == pin["bytes"], f"CHARGED evidence size differs: {path}"
            )
            checked += 1
        cities[city] = {
            "status": "VERIFIED_REUSE",
            "historical_run_count": record["runs"],
            "historical_code_commit": record["source_code_commit"],
            "evidence_pins": pins,
            "scope": "Historical verified Development collection; referenced proof/catalog/matrix bytes rechecked, full daily files and remote archives not freshly restored in this pass",
            "independent_teammate_acceptance": "pending",
        }
    return {
        "handoff": handoff_pin,
        "cities": cities,
        "evidence_files_rehashed": checked,
        "historical_run_count": handoff["run_count"],
        "pooled_metric": None,
    }


def ledger(plan_pin: dict, coverage_pin: dict, recipe_pin: dict) -> dict:
    """Authenticate the historical matrix without changing its identities or results."""
    plan, coverage, recipe = [pinned_json(pin) for pin in (plan_pin, coverage_pin, recipe_pin)]
    dispatch.require(coverage["plan_sha256"] == plan_pin["sha256"], "Coverage plan differs")
    dispatch.require(coverage["recipe_sha256"] == recipe_pin["sha256"], "Coverage recipe differs")
    dispatch.require(len(plan["jobs"]) == coverage["scheduled_jobs"], "Coverage count differs")
    cells = {row["id"]: row for row in plan["cells"]}
    sources = {(row["budget"], row["seed"]): row["checkpoint"] for row in recipe["sources"]}
    targets = {(row["cell"], row["variant"]): row["checkpoint"] for row in recipe["targets"]}
    configs = {key: pinned_json(value) for key, value in recipe["configs"].items()}
    code = dispatch._code_identity()
    inputs = {}
    for cell in cells.values():
        key = (cell["budget"], cell["input_manifest_sha256"])
        if key not in inputs:
            inputs[key] = dispatch._load_run(
                dispatch.project_path(plan["input_base"]) / f"urbanev-SZH-{key[0]}d", key[1]
            )
    rows, comparisons, source_comparisons = [], [], {}
    groups = [
        ("VERIFIED_REUSE", coverage["reused_jobs"]),
        ("EXTERNAL_COMPLETE_UNMATCHED", coverage["external_complete_jobs"]),
    ]
    for status, group in groups:
        for job_id, value in sorted(group.items()):
            variant, cell_id = job_id.split("_", 1)
            cell = cells[cell_id]
            matched_source = sources[(cell["budget"], cell["seed"])]
            matched_target = targets[(cell_id, "main")]
            pin = value if status == "VERIFIED_REUSE" else value["run_manifest"]
            row = {"job_id": job_id, "status": status, "run_manifest": pin}
            try:
                source = matched_source if status == "VERIFIED_REUSE" else value["source"]
                target = matched_target if status == "VERIFIED_REUSE" else value["target"]
                for checkpoint in (source, target):
                    pinned_checkpoint(checkpoint)
                record = pinned_json(pin)
                verify_reuse(
                    {"job_id": job_id, "run_manifest": pin},
                    {"id": job_id, "method": "confidence", "source": source, "target": target},
                    cell,
                    configs[variant],
                    code,
                )
                row.update(
                    {
                        "historical_code_commit": record["code"]["commit"],
                        "source": source,
                        "target": target,
                        "coverage": record.get("coverage"),
                        "scope": "Pinned manifest, checkpoint, event-journal bytes and declared provenance; not independent prediction reproduction",
                    }
                )
                if status == "EXTERNAL_COMPLETE_UNMATCHED":
                    source_key = f"b{cell['budget']}s{cell['seed']}"
                    if source_key not in source_comparisons:
                        source_comparisons[source_key] = checkpoint_comparison(
                            matched_source, source
                        )
                    comparisons.append(
                        {
                            "job_id": job_id,
                            "source": source_comparisons[source_key],
                            "target": checkpoint_comparison(matched_target, target),
                        }
                    )
            except (ValueError, OSError, KeyError) as error:
                row["status"] = "MISSING" if isinstance(error, FileNotFoundError) else "BLOCKED"
                row["error"] = str(error)
            rows.append(row)
    output = dispatch.project_path(plan["output_root"])
    for job in plan["jobs"]:
        exists = (output / "jobs" / job["id"]).exists()
        rows.append(
            {
                "job_id": job["id"],
                "status": "BLOCKED" if exists else "PLANNED",
                "reason": "Existing output needs receipt verification"
                if exists
                else "Not executed by this ledger",
            }
        )
    dispatch.require(len(rows) == coverage["declared_jobs"], "Logical ledger count differs")
    return {
        "schema": "hung-e2e-artifact-ledger-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "plan": plan_pin,
        "coverage": coverage_pin,
        "recipe": recipe_pin,
        "verifier_code": code,
        "jobs": rows,
        "counts": dict(Counter(r["status"] for r in rows)),
        "aliases": coverage["aliases"],
        "source_payload_comparison": source_comparisons,
        "block7_payload_comparison": comparisons,
        "requirements": [
            {
                "id": "matched_block7",
                "status": "MISSING",
                "cells": len(coverage["external_complete_jobs"]),
                "reason": "Historical Block-7 keeps original identities; independent fairness reconciliation is required",
            }
        ],
        "gpu_gate": "BLOCKED: peer review, fairness, dry-run, capacity/quota and storage gates must pass",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("ledger", "shards"):
        command = sub.add_parser(name)
        command.add_argument("--plan", type=Path, required=True)
        command.add_argument("--plan-sha256", required=True)
        command.add_argument("--output", type=Path, required=True)
        if name == "ledger":
            command.add_argument("--coverage", type=Path, required=True)
            command.add_argument("--coverage-sha256", required=True)
            command.add_argument("--recipe", type=Path, required=True)
            command.add_argument("--recipe-sha256", required=True)
            command.add_argument("--charged-handoff", type=Path)
            command.add_argument("--charged-handoff-sha256")
        else:
            command.add_argument("--jobs-per-shard", type=int, default=20)
    args = parser.parse_args(argv)
    plan_pin = {"path": str(dispatch.project_path(args.plan)), "sha256": args.plan_sha256}
    if args.command == "ledger":
        value = ledger(
            plan_pin,
            {"path": str(dispatch.project_path(args.coverage)), "sha256": args.coverage_sha256},
            {"path": str(dispatch.project_path(args.recipe)), "sha256": args.recipe_sha256},
        )
        dispatch.require(
            (args.charged_handoff is None) == (args.charged_handoff_sha256 is None),
            "CHARGED handoff path and SHA must be supplied together",
        )
        if args.charged_handoff is not None:
            value["charged_collections"] = charged_evidence(
                {
                    "path": str(dispatch.project_path(args.charged_handoff)),
                    "sha256": args.charged_handoff_sha256,
                }
            )
    else:
        plan = pinned_json(plan_pin)
        value = make_shards(
            args.plan_sha256, [job["id"] for job in plan["jobs"]], args.jobs_per_shard
        )
    output = dispatch.project_path(args.output)
    dispatch.require(output.is_relative_to(dispatch.ROOT), "Output must stay in this worktree")
    atomic_create(output, value)
    print(
        json.dumps(
            {
                "output": str(output),
                "sha256": dispatch.sha256_file(output),
                "counts": value.get("counts"),
                "training_executed": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
