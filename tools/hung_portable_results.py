"""Preserve daily errors for exact, disjoint Development collection reconciliation.

Exports reverify original artifacts, never infer paired errors from summary metrics.
Mounted receiver paths are relocated explicitly without changing any content hash.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path, PurePosixPath

from tools import hung_results as scorer

SCORER_SHA = "68fccbed056734d9b4842f7bda088880d7812d12417d64878d1aa018fc010456"
PLAN_SHA = "2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee"
MODEL_CODE = "44b8532959d76fb20691881539f991ca44983727"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_pin(pin: dict, root: Path) -> dict:
    return json.loads(scorer.verified_file(pin, root).read_bytes())


def export_catalog(catalog: dict, root: Path, provenance: dict) -> dict:
    """Recheck manifests/checkpoints/proofs and retain per-day original-unit errors."""
    require(scorer.file_sha(Path(scorer.__file__)) == SCORER_SHA, "Scorer source changed")
    plan_pin = catalog["spec"]["plan"]
    plan = load_pin(plan_pin, root)
    require(plan["scope"] == "development_only", "Foreign plan scope")
    if "receiver" in provenance:
        require(plan_pin["sha256"] == provenance["receiver"]["plan_sha256"], "Runtime plan differs")
    else:
        require(plan_pin["sha256"] == PLAN_SHA, "Canonical plan differs")
    records = scorer.verify_artifacts(catalog, root)
    return {
        "schema": "hung-portable-daily-errors-v1",
        "scope": "development_only",
        "canonical_plan_sha256": PLAN_SHA,
        "scorer_sha256": SCORER_SHA,
        "provenance": provenance,
        "acceptance": "Technical export only; independent review and full coverage pending",
        "records": records,
    }


def relocate_catalog(catalog: dict, original: str, mounted: Path) -> dict:
    """Map exact original receiver paths to a read-only mount, preserving SHA pins."""
    prefix = PurePosixPath(original)
    require(prefix.is_absolute() and ".." not in prefix.parts, "Invalid original root")
    relocated = copy.deepcopy(catalog)

    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "path":
                    path = PurePosixPath(item)
                    require(".." not in path.parts and path.is_relative_to(prefix), "Foreign path")
                    value[key] = str(mounted / path.relative_to(prefix))
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(relocated)
    return relocated


def export_receiver(mounted: Path, proof_sha256: str) -> dict:
    """Reverify an already completed CPU receiver from its pinned mounted output."""
    proof = load_pin(
        {"path": str(mounted / "receiver-proof.json"), "sha256": proof_sha256}, mounted
    )
    require(
        proof["scope"] == "development_only" and proof["passed"] and proof["executed"] is False,
        "Receiver did not pass without training",
    )
    require(proof["model_code_commit"] == MODEL_CODE, "Model provenance differs")
    require(proof["scorer_sha256"] == SCORER_SHA, "Receiver scorer differs")
    require(proof["derivation"]["parent_plan_sha256"] == PLAN_SHA, "Canonical plan differs")
    terminal = proof["verification"]
    require(terminal["exit_code"] == 0 and terminal["executed"] is False, "Verifier failed")
    command = terminal["command"]
    require(
        "--verify-only" in command and "--execute" not in command, "Execution command forbidden"
    )
    evidence = mounted / "cpu-readback"
    require(scorer.file_sha(evidence / "verify.log") == terminal["log_sha256"], "Log differs")
    require(json.loads((evidence / "verify-exit.json").read_bytes()) == terminal, "Exit differs")
    catalog = load_pin(
        {"path": str(evidence / "catalog.json"), "sha256": proof["catalog_sha256"]}, mounted
    )
    original = str(PurePosixPath(command[command.index("--plan") + 1]).parents[3])
    # --plan points at <root>/repo/.cache/provider/plan.json.
    require(PurePosixPath(original).name == mounted.name, "Explicit mount root identity differs")
    catalog = relocate_catalog(catalog, original, mounted)
    require(len(catalog["runs"]) == proof["jobs"], "Receiver catalog count differs")
    return export_catalog(
        catalog,
        mounted,
        {"receiver_proof_sha256": proof_sha256, "receiver": proof, "original_root": original},
    )


def merge_collections(spec: dict, root: Path) -> dict:
    """Merge exact expected job sets; duplicate anchors and altered errors fail closed."""
    require(spec.get("scope") == "development_only", "Development-only specification required")
    records, ids, logical = [], set(), set()
    for collection in spec["collections"]:
        value = load_pin(collection["export"], root)
        require(value["schema"] == "hung-portable-daily-errors-v1", "Unsupported export")
        require(value["scope"] == "development_only", "Foreign scope")
        require(value["canonical_plan_sha256"] == PLAN_SHA, "Plan differs")
        require(value["scorer_sha256"] == SCORER_SHA, "Scorer differs")
        rows = value["records"]
        expected = collection["job_ids"]
        require(len(expected) == len(set(expected)) and bool(expected), "Invalid expected job set")
        require(
            len(rows) == len(expected) and {r["job_id"] for r in rows} == set(expected),
            "Jobs differ",
        )
        for row in rows:
            identity = (row["method"], row["budget"], row["seed"], row["entity_id"])
            require(row["job_id"] not in ids and identity not in logical, "Duplicate logical run")
            require(row["status"] in {"DISPATCH_VERIFIED", "VERIFIED_REUSE"}, "Unmatched run")
            require(row["coverage"]["scored"] == len(row["days"]), "Scored coverage differs")
            for day in row["days"].values():
                require(
                    all(math.isfinite(day[k]) and day[k] >= 0 for k in ("absolute", "squared")),
                    "Invalid daily errors",
                )
                require(len(day["label_sha256"]) == 64, "Label hash missing")
            calculated = scorer.metrics(list(row["days"].values()))
            require((calculated is None) == (row["metrics"] is None), "Metric availability differs")
            if calculated is not None:
                require(
                    all(
                        math.isclose(v, row["metrics"][k], rel_tol=1e-9, abs_tol=1e-9)
                        for k, v in calculated.items()
                    ),
                    "Daily errors and metrics differ",
                )
            ids.add(row["job_id"])
            logical.add(identity)
            records.append(row)
    require(bool(records), "No verified records")
    pairs, blocked = scorer.paired_results(records)
    return {
        "schema": "hung-development-partial-results-v2",
        "scope": "development_only",
        "acceptance": "Provisional; full coverage and independent review required",
        "catalog_sha256": spec["spec_sha256"],
        "collection_proofs": spec["collections"],
        "runs": [{k: v for k, v in r.items() if k != "days"} for r in records],
        "counts": {
            "runs": len(records),
            "scorable_runs": sum(bool(r["days"]) for r in records),
            "zero_scored_runs": sum(not r["days"] for r in records),
        },
        "paired_cells": pairs,
        "blocked_pairs": blocked,
        "station_first": scorer.station_first(pairs),
        "aggregation": "Exact daily label-hash intersection within station/seed; equal seed means within station, then equal station means within each budget. Disjoint expected job sets; no global ranking or Final selection.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("export", "receiver", "merge"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(args.root.resolve()), "Output outside project")
    if args.action == "receiver":
        require(args.input.resolve().is_relative_to(args.root.resolve()), "Mount outside project")
        result = export_receiver(args.input, args.sha256)
    else:
        value = load_pin({"path": str(args.input), "sha256": args.sha256}, args.root)
        if args.action == "export":
            result = export_catalog(value, args.root, {"catalog_sha256": args.sha256})
        else:
            result = merge_collections({**value, "spec_sha256": args.sha256}, args.root)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "sha256": scorer.file_sha(args.output)}))


if __name__ == "__main__":
    main()
