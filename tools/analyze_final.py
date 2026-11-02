"""Analyze one complete locked Final namespace; live approval precedes all values."""

import argparse
import csv
import json
from pathlib import Path

from ev_evaluation.contexts import validate_analysis_extensions
from ev_evaluation.costs import comparison_costs
from ev_evaluation.proxy_relationships import analyze_proxy_cells
from ev_evaluation.switching import analyze_switch_cells
from ev_evaluation.uncertainty import paired_station_time_interval
from ev_models.checkpoint import digest, write_json
from ev_runner.final_gate import FinalAccess, FinalInputRun, authorize
from ev_runner.run import ROOT, runtime_code
from tools.analyze_core_comparisons import audit_gap_kwh, saved_errors
from tools.analyze_matched import aggregate_cells
from tools.verify_comparison import verify_run
from tools.verify_latest_states import verify_state


def frozen_density(rows: list[dict], threshold: float | None) -> dict:
    """Assign Final allowed-prefix metadata to a Development-frozen threshold."""
    entities, undefined = {}, []
    for row in rows:
        if row["role"] != "final" or row["status"] != "ready":
            raise ValueError("Final density requires selected ready Final metadata")
        valid, zero = row["scale"]["valid_count"], row["scale"]["zero_count"]
        if type(valid) is not int or type(zero) is not int or not 0 <= zero <= valid:
            raise ValueError("Invalid prefix counts")
        entity = row["identity"][2]
        if entity in entities or entity in undefined:
            raise ValueError("Duplicate density identity")
        if not valid or threshold is None:
            undefined.append(entity)
        else:
            density = (valid - zero) / valid
            entities[entity] = {
                "density": density,
                "valid_hours": valid,
                "group": "sparse" if density < threshold else "dense",
            }
    return {"entities": entities, "undefined_entities": undefined, "threshold": threshold}


def expected_cells(access: FinalAccess, namespace: tuple[str, str]) -> set[tuple]:
    """Require all locked IDs, budgets, seeds and variants, including null cells."""
    groups = [g for g in access.lock["groups"] if tuple(g["namespace"]) == namespace]
    if {g["history_days"] for g in groups} != {7, 14, 28}:
        raise ValueError("All three locked budgets required for namespace")
    if any(g["selected_ids"] != groups[0]["selected_ids"] for g in groups):
        raise ValueError("Final identities differ across budgets")
    return {
        (g["history_days"], entity, seed, variant)
        for g in groups
        for entity in g["selected_ids"]
        for seed in access.lock["seeds"]
        for variant in access.lock["required_unique_variants"]
    }


def analyze(
    access: FinalAccess,
    namespace: tuple[str, str],
    collection: Path,
    inputs_root: Path,
    output: Path,
) -> None:
    """Freshly verify every raw cell before the frozen station-first analysis."""
    access.check()
    groups = [g for g in access.lock["groups"] if tuple(g["namespace"]) == namespace]
    expected = expected_cells(access, namespace)
    declarations = json.loads(collection.read_text())
    declared = {(r["budget"], r["entity_id"], r["seed"], r["variant"]) for r in declarations}
    if len(declared) != len(declarations) or declared != expected:
        raise ValueError("Complete unique locked Final collection required; retain nulls")
    data = {
        g["history_days"]: FinalInputRun(
            inputs_root / f"{'-'.join(namespace)}-{g['history_days']}d",
            g["input_manifest_sha256"],
            access,
        )
        for g in groups
    }
    profile = json.loads((access.root / access.lock["analysis_profile_path"]).read_text())
    validate_analysis_extensions(profile)
    density, cohort = {}, {"seeds": access.lock["seeds"], "budgets": {}}
    for g in groups:
        b = g["history_days"]
        rows = [data[b].entities[(*namespace, entity)] for entity in g["selected_ids"]]
        threshold = next(
            r["threshold"]
            for r in profile["development_density_thresholds"]
            if tuple(r["namespace"]) == namespace and r["history_days"] == b
        )
        density[*namespace, b] = frozen_density(rows, threshold)
        cohort["budgets"][str(b)] = {
            "entities": [
                {"entity_id": r["identity"][2], "initial_trainable": r["initial_trainable"]}
                for r in rows
            ]
        }
    cells, proofs, csv_rows, audits = {}, [], [], []
    for item in declarations:
        path = Path(item["path"])
        if digest(path / "run.json") != item["report_sha256"]:
            raise ValueError("Declared Final report bytes changed")
        report = json.loads((path / "run.json").read_text())
        b, entity, seed, variant = item["budget"], item["entity_id"], item["seed"], item["variant"]
        cfg = json.loads(json.dumps(access.lock["method_configs"][str(seed)][variant]))
        cfg["development_entities"] = [entity]
        binding = report["binding"]
        if (
            binding["config"] != cfg
            or binding["input"]["entity_id"] != entity
            or binding["environment"] != access.lock["runtime_profile"]
        ):
            raise ValueError("Final report differs from declared cell/config/runtime")
        proofs.append(
            {
                "daily": verify_run(path, data[b].root, final_access=access, final_inputs=data[b]),
                "latest_state": verify_state(path, report),
            }
        )
        errors, coverage = saved_errors(path, report)
        issued = [
            json.loads(p.read_text()).get("origin")
            for p in sorted(path.glob("tick-*/forecasts.json"))
        ]
        cells[b, entity, seed, variant] = {
            "errors": errors,
            "coverage": coverage,
            "issued": tuple(x for x in issued if x),
            "report": report,
        }
        csv_rows.append(
            {
                "budget": b,
                "entity_id": entity,
                "seed": seed,
                "method": variant,
                "issued_days": report["issued_days"],
                "scored_days": report["scored_days"],
                "mae_kwh": report["active_mae_kwh"],
                "rmse_kwh": report["active_rmse_kwh"],
            }
        )
        audits.extend(
            {
                "run_id": path.name,
                "method": variant,
                "paired_days": a["paired_days"],
                "new_minus_old_mae_kwh": audit_gap_kwh(a, coverage["scale"]),
            }
            for a in report["audits"]
        )
    start = data[7].deployment
    summary = aggregate_cells(cells, cohort, density=density, deployment=start, namespace=namespace)
    differences = summary.pop("daily_adaptive_minus_comparator")
    source_reports = [
        json.loads((access.root / s["producer_report_path"]).read_text())
        for s in groups[0]["sources"].values()
    ]
    summary.update(comparison_costs(cells, source_reports))
    summary["resume_cost_scope"] = {
        "resumed_selected_cells": sum(bool(c["report"].get("resume_from")) for c in cells.values()),
        "limits": "Selected elapsed_seconds sums current invocations. Component counters and initial logs may be carried across resume; retain predecessor process spans separately and do not double count cumulative counters. Missing predecessor costs remain unknown.",
    }
    summary.update(
        {
            "scope": "Conditional bounded locked Final cohort; no city pooling or population superiority inference",
            "namespace": list(namespace),
            "final_authorization": access.provenance(),
            "collection_sha256": digest(collection),
            "analysis_code": runtime_code(),
            "adaptive_minus_comparator_intervals": {
                k: paired_station_time_interval(
                    v, seeds=tuple(cohort["seeds"]), start=start, days=90, **profile["bootstrap"]
                )
                for k, v in differences.items()
            },
            "proxy_relationships": analyze_proxy_cells(cells, cohort["seeds"]),
            "switching": analyze_switch_cells(cells, cohort["seeds"], start=start),
            "isolated_audits": audits,
            "limitations": profile["population_inference"] + " " + profile["budget_pairing"],
        }
    )
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "summary.json", summary)
    write_json(
        output / "independent-daily.json", {"collection_sha256": digest(collection), "runs": proofs}
    )
    with (output / "runs.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("lock", "collection", "inputs-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("dataset", "city"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    access = authorize(args.lock, ROOT)
    analyze(access, (args.dataset, args.city), args.collection, args.inputs_root, args.output)


if __name__ == "__main__":
    main()
