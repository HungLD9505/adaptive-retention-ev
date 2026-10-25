"""Read-only selected Development collection; never a Final lock or winner claim."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from ev_evaluation.artifacts import authenticate_matrix
from ev_evaluation.contexts import validate_analysis_extensions
from ev_evaluation.costs import comparison_costs
from ev_evaluation.metrics import paired_metrics, station_first
from ev_evaluation.proxy_relationships import analyze_proxy_cells
from ev_evaluation.selection import score_candidates
from ev_evaluation.uncertainty import paired_station_time_interval
from ev_models.checkpoint import digest, write_json
from ev_runner.run import runtime_code
from tools.analyze_core_comparisons import audit_gap_kwh, saved_errors
from tools.development_contexts import authenticate_contexts
from tools.fixed_retention_sweep import selected_sources
from tools.matched_development import validate_cells
from tools.proxy_calibration import selected_controller
from tools.proxy_calibration import summarize as proxy_selection

FAMILIES = ("source", "fixed", "controller", "proxy", "matched")


def unit(row: dict) -> tuple[int, str, int]:
    b, c = row["binding"]["input"], row["binding"]["config"]
    if (b["dataset_id"], b["city_id"]) != ("urbanev", "SZH"):
        raise ValueError("Collection only permits this identified UrbanEV scope")
    return b["history_days"], b["entity_id"], c["initial_training"]["seed"]


def select_collection(studies: dict, cohort: dict, code_files: dict) -> tuple[dict, dict]:
    """Recompute every selection, preserve aliases and require all actual cells."""
    source_profile = json.loads(Path("configs/issue23/fixed-retention-study.json").read_text())
    epoch, sources = selected_sources(studies["source"], cohort, source_profile)
    choice, refs = selected_controller(studies["controller"], cohort, code_files)
    fixed = score_candidates(
        studies["fixed"]["runs"],
        cohort,
        [0.001, 0.01, 0.1, 1.0],
        choice_field="fixed_lambda",
        method_name="fixed_retention",
    )
    fixed_choice = fixed["provisional_choice"]
    proxies = proxy_selection(studies["proxy"]["runs"], cohort, refs)
    replication_lambda = studies["matched"].get("replication_fixed_lambda")
    if replication_lambda is not None and replication_lambda != fixed_choice:
        raise ValueError("Replication Fixed choice differs from authenticated calibration")
    coverage = validate_cells(
        studies["matched"]["runs"], refs, replication_fixed_lambda=replication_lambda
    )
    if fixed_choice is None or any(p["provisional_choice"] is None for p in proxies.values()):
        raise ValueError("No common scored Development selection")
    selected = {
        "source_epochs": epoch,
        "controller_recipe": choice,
        "fixed_lambda": fixed_choice,
        "proxy_recipes": {k: v["provisional_choice"] for k, v in proxies.items()},
        **coverage,
    }
    cells = {}
    for family in FAMILIES:
        study = studies[family]
        if (
            study["status"] != "technical_success"
            or study["code"]["dirty"]
            or study["code"]["files"] != code_files
        ):
            raise ValueError("Successful unchanged identified studies required")
        for row in study["runs"]:
            method = row["method"]["name"]
            keep = (
                family == "source"
                and row["source_epochs"] == epoch
                or family == "fixed"
                and row["fixed_lambda"] == fixed_choice
                or family == "controller"
                and row["recipe"] == choice
                or family == "proxy"
                and row["recipe"] == proxies[method]["provisional_choice"]
                or family == "matched"
            )
            if replication_lambda is not None and family in {"source", "fixed", "controller"}:
                keep = False
            if not keep:
                continue
            name = row["comparison_variant"] if family == "matched" else method
            key = (*unit(row), name)
            if key in cells:
                raise ValueError("Duplicate selected comparison cell")
            cells[key] = family, row
    names = {key[-1] for key in cells}
    required = {
        "adaptive",
        "seasonal_naive",
        "target_only",
        "frozen_source",
        "full_finetuning",
        "fixed_retention",
        "online_best",
        "source_error",
        "uncertainty",
        "drift",
        "parameter_retention",
        "without_source_initialization",
        "block7",
        "block28",
    }
    if selected["aliases"]["without_confidence"] != "online_best":
        required.add("without_confidence")
    if selected["block7_comparator"] == "adaptive_bmin7_reference":
        required.add("adaptive_bmin7_reference")
    expected = {(*key, name) for key in refs for name in required}
    if set(cells) != expected or names != required:
        raise ValueError("Complete selected method/seed/station/budget matrix required")
    shared = (
        "initial_training",
        "online_training",
        "development_entities",
        "replay_days",
        "state_retention",
    )
    for key, (_, row) in cells.items():
        ref = refs[key[:3]]
        cfg, common = row["binding"]["config"], ref["binding"]["config"]
        if (
            any(cfg[k] != common[k] for k in shared)
            or row["binding"]["input"] != ref["binding"]["input"]
        ):
            raise ValueError("Common input/training/Source bindings differ")
        environment = row["binding"].get("environment")
        peer_environment = cells[(*key[:3], "target_only")][1]["binding"].get("environment")
        if not isinstance(environment, dict) or not environment or environment != peer_environment:
            raise ValueError(
                "Mixed/missing target execution environments; rerun matched references after migration"
            )
        if row["source_checkpoint_sha256"] != sources[key[2]]["sha256"]:
            raise ValueError("Selected methods do not use the common Source family")
        if row["code"]["dirty"] or row["code"]["files"] != code_files:
            raise ValueError("Changed selected run algorithms")
        if key[-1] == "fixed_retention" and cfg["method"] != {
            "name": "fixed_retention",
            "fixed_lambda": fixed_choice,
        }:
            raise ValueError("Executed Fixed baseline contradicts selection")
    selected["fixed_baseline_in_controller_levels"] = fixed_choice in (
        0,
        common["controller"]["lambda_low"],
        common["controller"]["lambda_high"],
    )
    selected["unique_method_names"] = sorted(names)
    return cells, selected


def aggregate_cells(
    cells: dict,
    cohort: dict,
    *,
    density: dict | None = None,
    deployment: datetime | None = None,
    namespace: tuple[str, str] = ("urbanev", "SZH"),
) -> dict:
    """Require exact issued/scored sets, retain nulls, aggregate stations first."""
    names = sorted({key[-1] for key in cells})
    seeds = tuple(cohort["seeds"])
    output, nulls, differences, contexts, strata = {}, {}, {}, {}, {}
    load_groups, phases, density_coverage = {}, {}, {}
    for budget, group in cohort["budgets"].items():
        nulls[budget] = []
        grouped = {name: {} for name in names}
        if density is not None:
            for name in names:
                for label in ("sparse", "dense", "undefined"):
                    load_groups[f"{budget}/{name}/{label}"] = {}
        for item in group["entities"]:
            entity = item["entity_id"]
            if density is not None:
                g = density[*namespace, int(budget)]
                if entity not in g["entities"] and entity not in g["undefined_entities"]:
                    raise ValueError("Selected target absent from calibrated density population")
                load_context = g["entities"].get(entity, {"group": "undefined", "valid_hours": 0})
                density_coverage[f"{budget}/{entity}"] = load_context
            flags = []
            for seed in seeds:
                base = cells[int(budget), entity, seed, "target_only"]
                flags.append(bool(base["errors"]))
                for name in names:
                    row = cells[int(budget), entity, seed, name]
                    if row["issued"] != base["issued"] or {e.origin for e in row["errors"]} != {
                        e.origin for e in base["errors"]
                    }:
                        raise ValueError("Actual issued/scored origin sets differ")
                    if not row["errors"]:
                        continue
                    pair = paired_metrics(row["errors"], base["errors"])
                    grouped[name].setdefault(entity, {})[seed] = pair
                    stratum = (
                        "initial_adaptation"
                        if item["initial_trainable"]
                        else "no_initial_trainable"
                    )
                    strata.setdefault(f"{budget}/{name}/{stratum}", {}).setdefault(entity, {})[
                        seed
                    ] = pair
                    if density is not None:
                        key = f"{budget}/{name}/{load_context['group']}"
                        load_groups.setdefault(key, {}).setdefault(entity, {})[seed] = pair
                    for context in ("weekday", "weekend"):
                        left = [
                            e
                            for e in row["errors"]
                            if (e.origin.weekday() >= 5) == (context == "weekend")
                        ]
                        right = [
                            e
                            for e in base["errors"]
                            if (e.origin.weekday() >= 5) == (context == "weekend")
                        ]
                        if left:
                            contexts.setdefault(f"{budget}/{name}/{context}", {}).setdefault(
                                entity, {}
                            )[seed] = paired_metrics(left, right)
                    if deployment is not None:
                        if any(not 0 <= (e.origin - deployment).days < 90 for e in row["errors"]):
                            raise ValueError("Scored forecast outside the declared 90-day calendar")
                        for phase in range(3):
                            left = [
                                e
                                for e in row["errors"]
                                if (e.origin - deployment).days // 30 == phase
                            ]
                            right = [
                                e
                                for e in base["errors"]
                                if (e.origin - deployment).days // 30 == phase
                            ]
                            if left:
                                key = f"{budget}/{name}/days{phase * 30 + 1}-{(phase + 1) * 30}"
                                phases.setdefault(key, {}).setdefault(entity, {})[seed] = (
                                    paired_metrics(left, right)
                                )
                    active = cells[int(budget), entity, seed, "adaptive"]["errors"]
                    other = {e.origin: e.mae for e in row["errors"]}
                    differences.setdefault(f"{budget}/{name}", {}).setdefault(entity, {})[seed] = {
                        e.origin: e.mae - other[e.origin] for e in active
                    }
            if any(flags) and not all(flags):
                raise ValueError("Mixed seed score availability")
            if not any(flags):
                nulls[budget].append(entity)
        for name in names:
            output[f"{budget}/{name}"] = (
                station_first(grouped[name], seeds=seeds) if grouped[name] else None
            )
    return {
        "station_first": output,
        "unscored_entities_by_budget": nulls,
        "weekday_weekend": {k: station_first(v, seeds=seeds) for k, v in contexts.items()},
        "daily_adaptive_minus_comparator": differences,
        "initialization_strata": {k: station_first(v, seeds=seeds) for k, v in strata.items()},
        "load_density": {
            k: station_first(v, seeds=seeds) if v else None for k, v in load_groups.items()
        },
        "density_coverage": density_coverage,
        "online_phases": {k: station_first(v, seeds=seeds) for k, v in phases.items()},
    }


def analyze(args: argparse.Namespace) -> None:
    cohort = json.loads(args.selection.read_text())
    profile = json.loads(args.analysis_profile.read_text())
    validate_analysis_extensions(profile)
    if profile["seeds"] != cohort["seeds"]:
        raise ValueError("Different paired analysis seeds")
    paths = {name: getattr(args, name + "_matrix") for name in FAMILIES}
    studies = {
        name: authenticate_matrix(paths[name], getattr(args, name + "_verification"))
        for name in FAMILIES
    }
    for name in FAMILIES:
        if studies[name]["selection_sha256"] != digest(args.selection):
            raise ValueError("Changed common Development cohort")
    for name in ("fixed", "controller"):
        if studies[name]["source_study_sha256"] != digest(paths["source"]):
            raise ValueError("Source selection dependency differs")
    for name in ("proxy", "matched"):
        if studies[name]["controller_matrix_sha256"] != digest(paths["controller"]):
            raise ValueError("Controller selection dependency differs")
    if studies["matched"].get("replication_fixed_lambda") is not None and studies["matched"].get(
        "fixed_study_sha256"
    ) != digest(paths["fixed"]):
        raise ValueError("Changed Fixed calibration dependency for migrated references")
    code = runtime_code()
    if code["dirty"]:
        raise ValueError("Clean committed analysis code required")
    selected, choices = select_collection(studies, cohort, code["files"])
    cells, rows, audits, lineage = {}, [], [], []
    for key, (family, row) in selected.items():
        name = row["run_id"]
        if Path(name).name != name:
            raise ValueError("Unsafe artifact run identifier")
        root = paths[family].parent / name
        report = json.loads((root / "run.json").read_text())
        if any(row.get(k) != v for k, v in report.items()):
            raise ValueError("Selected run report changed")
        errors, coverage = saved_errors(root, row)
        issued = []
        for path in sorted(root.glob("tick-*/forecasts.json")):
            forecast = json.loads(path.read_text())
            if forecast:
                issued.append(forecast["origin"])
        if len(set(issued)) != len(issued):
            raise ValueError("Duplicate actual issued origin")
        cells[key] = {
            "errors": errors,
            "issued": tuple(issued),
            "report": row,
            "coverage": coverage,
        }
        rows.append(
            {
                "budget": key[0],
                "entity_id": key[1],
                "seed": key[2],
                "method": key[3],
                "family": family,
                "initialization": row["initialization"],
                "issued_days": len(issued),
                "scored_days": len(errors),
                "mae_kwh": row["active_mae_kwh"],
                "rmse_kwh": row["active_rmse_kwh"],
            }
        )
        lineage.append(
            {
                "method": key[3],
                "family": family,
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
                    "method": key[3],
                    "paired_days": audit["paired_days"],
                    "new_minus_old_mae_kwh": audit_gap_kwh(audit, coverage["scale"]),
                }
            )
    starts = set()
    for b, group in cohort["budgets"].items():
        path = args.inputs_root / f"urbanev-SZH-{b}d" / "manifest.json"
        if digest(path) != group["manifest_sha256"]:
            raise ValueError("Changed authenticated clock metadata")
        starts.add(json.loads(path.read_text())["config"]["deployment"])
    if len(starts) != 1:
        raise ValueError("Common explicit deployment clock required")
    context_path = getattr(args, "density_contexts", None)
    context_sha = getattr(args, "density_sha256", None)
    if (context_path is None) != (context_sha is None):
        raise ValueError("Both identified density-context arguments required")
    density = (
        authenticate_contexts(context_path, context_sha, args.inputs_root) if context_path else None
    )
    summary = aggregate_cells(
        cells, cohort, density=density, deployment=datetime.fromisoformat(next(iter(starts)))
    )
    differences = summary.pop("daily_adaptive_minus_comparator")
    summary.update(
        scope="Conditional Development calibration/comparisons; no Final effectiveness or lock",
        choices=choices,
        collection_lineage=lineage,
        matrix_identities={
            name: {
                "sha256": digest(paths[name]),
                "verification_sha256": digest(getattr(args, name + "_verification")),
            }
            for name in FAMILIES
        },
        selection_sha256=digest(args.selection),
        analysis_profile_sha256=digest(args.analysis_profile),
        analysis_code=code,
        density_contexts_sha256=context_sha,
        adaptive_minus_comparator_intervals={
            k: paired_station_time_interval(
                v,
                seeds=tuple(cohort["seeds"]),
                start=datetime.fromisoformat(next(iter(starts))),
                days=90,
                **profile["bootstrap"],
            )
            for k, v in differences.items()
        },
        isolated_audits=audits,
        limits="Small nonrandom/possibly colocated cohort; conditional Development selection, three fixed seeds, marginal exploratory intervals. Density groups require authenticated context arguments; 30-day phases and same-block proxy relationships are descriptive. No causal effect, next-block predictive skill or calibrated predictive coverage claim. Independent downloaded-state verification remains required.",
    )
    summary.update(
        comparison_costs(cells, [source["run"] for source in studies["source"]["sources"]])
    )
    summary["calibration_wall_seconds_by_family"] = {
        family: studies[family]["wall_seconds"] for family in FAMILIES
    }
    summary["proxy_relationships"] = analyze_proxy_cells(cells, cohort["seeds"])
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "summary.json", summary)
    with (args.output / "runs.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(
        json.dumps(
            {
                "status": "analyzed",
                "selected_cells": len(rows),
                "methods": choices["unique_method_names"],
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in FAMILIES:
        for suffix in ("matrix", "verification"):
            parser.add_argument("--" + name + "-" + suffix, type=Path, required=True)
    for name in ("selection", "analysis-profile", "inputs-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--density-contexts", type=Path)
    parser.add_argument("--density-sha256")
    analyze(parser.parse_args())


if __name__ == "__main__":
    main()
