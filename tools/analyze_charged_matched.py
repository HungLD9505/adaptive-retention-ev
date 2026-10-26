"""Read-only, separate-city CHARGED Development comparison; never a Final lock."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from ev_evaluation.artifacts import authenticate_matrix
from ev_evaluation.contexts import validate_analysis_extensions
from ev_evaluation.costs import comparison_costs
from ev_evaluation.proxy_relationships import analyze_proxy_cells
from ev_evaluation.switching import analyze_switch_cells
from ev_evaluation.uncertainty import paired_station_time_interval
from ev_models.checkpoint import digest, load_checkpoint, write_json
from ev_models.data import InputRun
from ev_runner.run import runtime_code
from tools.analyze_core_comparisons import audit_gap_kwh, saved_errors
from tools.analyze_matched import aggregate_cells
from tools.charged_matched_development import primary_recipe, validate_cohort, validate_matrix
from tools.development_contexts import authenticate_contexts
from tools.export_development import safe_name


def canonical_code_files(files: dict[str, str]) -> dict[str, str]:
    """Compare recorded code hashes across OS separators without changing artifact bytes."""
    if not isinstance(files, dict):
        raise ValueError("Code file fingerprints must be a mapping")
    canonical = {}
    for path, sha256 in files.items():
        if not isinstance(path, str) or not isinstance(sha256, str):
            raise ValueError("Malformed code file fingerprint")
        key = path.replace("\\", "/")
        parts = key.split("/")
        if any(part in {"", ".", ".."} for part in parts) or ":" in parts[0]:
            raise ValueError("Unsafe code file path")
        if key in canonical:
            raise ValueError("Duplicate code file path after separator normalization")
        canonical[key] = sha256
    return canonical


def canonical_code(code: dict) -> dict:
    """Retain commit/dirty provenance while canonicalizing only file path keys."""
    return {**code, "files": canonical_code_files(code["files"])}


def validate_collection(matrix: dict, cohort: dict, primary: dict, code_files: dict) -> dict:
    """Bind every city method to its own Source, unchanged recipe and common runtime."""
    validate_matrix(matrix["runs"], cohort, primary)
    epoch, _, source_config = primary_recipe(primary, 42, "not-used-by-source")
    if (
        matrix["namespace"] != cohort["namespace"]
        or matrix["source_epochs"] != epoch
        or matrix["code"]["dirty"]
        or canonical_code_files(matrix["code"]["files"]) != canonical_code_files(code_files)
    ):
        raise ValueError("Changed city/Source duration/executed algorithms")
    sources = {s["seed"]: s for s in matrix["sources"]}
    if len(sources) != len(matrix["sources"]) or set(sources) != set(cohort["seeds"]):
        raise ValueError("Complete unique city Source seeds required")
    city = cohort["namespace"].removeprefix("charged-")
    model_files = {
        k: v for k, v in canonical_code_files(code_files).items() if k.startswith("ev_models/")
    }
    for seed, source in sources.items():
        report = source["run"]
        b = report["input_binding"]
        if (
            b["stage"] != "source"
            or (b["dataset_id"], b["city_id"]) != ("charged", city)
            or b["input_manifest_sha256"] != cohort["budgets"]["7"]["manifest_sha256"]
            or report["source_population_sha256"] != cohort["source_population_sha256"]
            or report["training_config"] != {**source_config, "seed": seed, "epochs": epoch}
            or report["checkpoint_sha256"] != source["sha256"]
            or report["code"]["dirty"]
            or canonical_code_files(report["code"]["files"]) != model_files
        ):
            raise ValueError(
                "Source must be independently trained on the identified city's Source population"
            )
    references = {}
    for row in matrix["runs"]:
        b, c = row["binding"]["input"], row["binding"]["config"]
        key = b["history_days"], b["entity_id"], c["initial_training"]["seed"]
        if row["comparison_variant"] == "target_only":
            references[key] = row
    for row in matrix["runs"]:
        b, c = row["binding"]["input"], row["binding"]["config"]
        seed = c["initial_training"]["seed"]
        ref = references[b["history_days"], b["entity_id"], seed]
        env = row["binding"].get("environment")
        if (
            not isinstance(env, dict)
            or not env
            or env != ref["binding"].get("environment")
            or row["source_checkpoint_sha256"] != sources[seed]["sha256"]
            or row["binding"]["source_population_sha256"] != cohort["source_population_sha256"]
            or row["code"]["dirty"]
            or canonical_code_files(row["code"]["files"]) != canonical_code_files(code_files)
        ):
            raise ValueError(
                "Cross-runtime/Source population/algorithm contamination in city comparisons"
            )
    return sources


def analyze(args: argparse.Namespace) -> None:
    code = runtime_code()
    if code["dirty"]:
        raise ValueError("Clean committed analysis code required")
    for path, expected in (
        (args.cohort, args.cohort_sha256),
        (args.primary_analysis, args.primary_sha256),
    ):
        if digest(path) != expected:
            raise ValueError("Changed identified primary summary or city cohort")
    cohort, primary, profile = [
        json.loads(p.read_text())
        for p in (args.cohort, args.primary_analysis, args.analysis_profile)
    ]
    validate_analysis_extensions(profile)
    if (
        profile["seeds"] != cohort["seeds"]
        or not primary.get("collection_lineage")
        or not primary.get("matrix_identities")
    ):
        raise ValueError("Identified complete primary collection and same paired seeds required")
    matrix = authenticate_matrix(args.matrix, args.verification)
    if (
        matrix["cohort_sha256"] != args.cohort_sha256
        or matrix["primary_analysis_sha256"] != args.primary_sha256
    ):
        raise ValueError("Matrix was not executed with this cohort/primary recipe")
    data = {
        b: InputRun(
            args.inputs_root / f"{cohort['namespace']}-{b}d",
            cohort["budgets"][str(b)]["manifest_sha256"],
        )
        for b in (7, 14, 28)
    }
    validate_cohort(data, cohort)
    sources = validate_collection(matrix, cohort, primary, code["files"])
    for seed, source in sources.items():
        path = args.matrix.parent / f"source-seed{seed}" / f"epoch-{matrix['source_epochs']}.pt"
        _, _, value = load_checkpoint(path, sha256=source["sha256"], device="cpu")
        if value["completed_epochs"] != matrix["source_epochs"] or any(
            (
                canonical_code(value["metadata"][k]) != canonical_code(source["run"][k])
                if k == "code"
                else value["metadata"][k] != source["run"][k]
            )
            for k in ("input_binding", "source_population_sha256", "training_config", "code")
        ):
            raise ValueError("Actual Source checkpoint contradicts city training provenance")
    ns = ("charged", cohort["namespace"].removeprefix("charged-"))
    cells, rows, lineage, audits = {}, [], [], []
    for row in matrix["runs"]:
        name = safe_name(row["run_id"])
        root = args.matrix.parent / name
        report = json.loads((root / "run.json").read_text())
        if any(
            (canonical_code(row.get(k)) != canonical_code(v) if k == "code" else row.get(k) != v)
            for k, v in report.items()
        ):
            raise ValueError("Changed city run report")
        b, c = row["binding"]["input"], row["binding"]["config"]
        seed, method = c["initial_training"]["seed"], row["comparison_variant"]
        key = b["history_days"], b["entity_id"], seed, method
        if data[key[0]].entities[(*ns, key[1])]["role"] != "development":
            raise ValueError("City analysis only permits declared Development targets")
        errors, coverage = saved_errors(root, row)
        issued = []
        for path in sorted(root.glob("tick-*/forecasts.json")):
            f = json.loads(path.read_text())
            if f:
                issued.append(f["origin"])
        cells[key] = {
            "errors": errors,
            "issued": tuple(issued),
            "report": row,
            "coverage": coverage,
        }
        rows.append(
            {
                "namespace": cohort["namespace"],
                "budget": key[0],
                "entity_id": key[1],
                "seed": seed,
                "method": method,
                "initialization": row["initialization"],
                "issued_days": len(issued),
                "scored_days": len(errors),
                "mae_kwh": row["active_mae_kwh"],
                "rmse_kwh": row["active_rmse_kwh"],
            }
        )
        lineage.append(
            {
                "method": method,
                "run_id": name,
                "report_sha256": digest(root / "run.json"),
                "commit_chain": row["commit_chain"],
                "source_sha256": row["source_checkpoint_sha256"],
            }
        )
        for audit in row["audits"]:
            audits.append(
                {
                    "run_id": name,
                    "method": method,
                    "paired_days": audit["paired_days"],
                    "new_minus_old_mae_kwh": audit_gap_kwh(audit, coverage["scale"]),
                }
            )
    density = authenticate_contexts(args.density_contexts, args.density_sha256, args.inputs_root)
    start = datetime.fromisoformat(cohort["deployment"])
    if start.utcoffset() is not None:
        raise ValueError("Preserve publisher-local-naive city clock; never silently assume UTC")
    summary = aggregate_cells(cells, cohort, density=density, deployment=start, namespace=ns)
    differences = summary.pop("daily_adaptive_minus_comparator")
    summary.update(comparison_costs(cells, [s["run"] for s in sources.values()]))
    summary.update(
        scope="Separate-city supplementary Development configuration replication; no Final or strict-online effectiveness claim",
        namespace=cohort["namespace"],
        analysis_group="SZH separate temporal/possible-overlap analysis"
        if ns[1] == "SZH"
        else "Five-city geographic supplement; publisher preprocessing limitations retained",
        cohort_sha256=args.cohort_sha256,
        primary_analysis_sha256=args.primary_sha256,
        matrix_sha256=digest(args.matrix),
        verification_sha256=digest(args.verification),
        analysis_profile_sha256=digest(args.analysis_profile),
        density_contexts_sha256=args.density_sha256,
        analysis_code=code,
        collection_lineage=lineage,
        primary_choices=primary["choices"],
        matrix_wall_seconds=matrix["wall_seconds"],
        adaptive_minus_comparator_intervals={
            k: paired_station_time_interval(
                v, seeds=tuple(cohort["seeds"]), start=start, days=90, **profile["bootstrap"]
            )
            for k, v in differences.items()
        },
        proxy_relationships=analyze_proxy_cells(cells, cohort["seeds"]),
        switching=analyze_switch_cells(cells, cohort["seeds"], start=start),
        isolated_audits=audits,
        limits="No city pooling, UrbanEV weight reuse, city-specific retuning or independent-external/strict-online certification. Small prefix-selected cohort, fixed three seeds, possible co-location, publisher imputation/clock uncertainty, conditional primary configuration. Intervals are exploratory/marginal; density and same-block proxy associations are descriptive. Off-runtime state verification and capacity/peer acceptance remain required.",
    )
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "summary.json", summary)
    with (args.output / "runs.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"status": "analyzed", "namespace": cohort["namespace"], "cells": len(rows)}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "matrix",
        "verification",
        "cohort",
        "primary-analysis",
        "analysis-profile",
        "inputs-root",
        "density-contexts",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("cohort-sha256", "primary-sha256", "density-sha256"):
        parser.add_argument("--" + name, required=True)
    analyze(parser.parse_args())


if __name__ == "__main__":
    main()
