"""Read-only five-method Development comparisons from authenticated saved forecasts."""

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean

from ev_evaluation.metrics import DailyError, paired_metrics, station_first
from ev_evaluation.uncertainty import paired_station_time_interval
from ev_models.checkpoint import digest, write_json
from ev_runner.run import runtime_code
from tools.development_comparators import reference_cells

METHODS = ("adaptive", "target_only", "full_finetuning", "fixed_retention", "online_best")


def saved_errors(root: Path, report: dict) -> tuple[list[DailyError], dict]:
    """Rehash daily predictions/events and follow score identities; never read labels."""
    predictions, errors, coverage = {}, [], []
    previous = "0" * 64
    scale = None
    for index, tick in enumerate(sorted(root.glob("tick-*"))):
        commit = json.loads((tick / "commit.json").read_text())
        if commit["index"] != index or commit["previous"] != previous:
            raise ValueError("Broken chronological commit chain")
        for name in ("forecasts.json", "events.jsonl"):
            if digest(tick / name) != commit["files"][name]:
                raise ValueError("Changed saved forecast/event")
        for line in (tick / "events.jsonl").read_text().splitlines():
            event = json.loads(line)
            if event["event"] != "score":
                continue
            forecast, checksum = predictions[event["origin"]]
            if (
                event["prediction_sha256"] != checksum
                or event["issued_active"] != forecast["active"]
            ):
                raise ValueError("Score does not refer to the issued prediction")
            k = report["candidate_levels"].index(forecast["active"])
            errors.append(
                DailyError(
                    datetime.fromisoformat(event["origin"]),
                    event["mae_scaled"][k] * scale,
                    event["mse_scaled"][k] * scale**2,
                )
            )
        forecast = json.loads((tick / "forecasts.json").read_text())
        if forecast:
            if forecast["origin"] in predictions or any(
                key.startswith("y_") for key in forecast["record"]
            ):
                raise ValueError("Duplicate forecast or predictor contains labels")
            current = forecast["record"]["energy_scale"]
            if scale is not None and scale != current:
                raise ValueError("Target scale changed")
            scale = current
            coverage.append(sum(bool(row[-1]) for row in forecast["record"]["x_hist"]))
            predictions[forecast["origin"]] = forecast, digest(tick / "forecasts.json")
        previous = digest(tick / "commit.json")
    if (
        previous != report["commit_chain"]
        or len(errors) != report["scored_days"]
        or len(predictions) != report["issued_days"]
        or len({e.origin for e in errors}) != len(errors)
    ):
        raise ValueError("Saved daily population differs from report")
    return errors, {
        "scale": scale,
        "valid_history_hours_min": min(coverage) if coverage else None,
        "valid_history_hours_mean": mean(coverage) if coverage else None,
    }


def load_verified(matrix_path: Path, verification_path: Path) -> list[tuple[dict, list, dict]]:
    matrix, verification = [json.loads(p.read_text()) for p in (matrix_path, verification_path)]
    if (
        matrix["status"] != "technical_success"
        or verification["status"] != "verified"
        or verification["matrix_sha256"] != digest(matrix_path)
    ):
        raise ValueError("Identified complete verified matrix required")
    verified = {r["run_id"]: r for r in verification["runs"]}
    if len(verified) != len(matrix["runs"]) or set(verified) != {
        r["run_id"] for r in matrix["runs"]
    }:
        raise ValueError("Verification population differs")
    result = []
    for row in matrix["runs"]:
        name = row["run_id"]
        if Path(name).name != name or row["commit_chain"] != verified[name]["commit_chain"]:
            raise ValueError("Unsafe identity or unverified commit chain")
        root = matrix_path.parent / name
        report = json.loads((root / "run.json").read_text())
        if any(row.get(k) != value for k, value in report.items()):
            raise ValueError("Changed run report")
        errors, coverage = saved_errors(root, row)
        result.append((row, errors, coverage))
    return result


def analyze(args: argparse.Namespace) -> None:
    cohort, profile = [json.loads(p.read_text()) for p in (args.selection, args.profile)]
    old, new = [json.loads(p.read_text()) for p in (args.reference, args.matrix)]
    reference_cells(cohort, old, runtime_code()["files"])
    if new["reference_matrix_sha256"] != digest(args.reference) or any(
        m["selection_sha256"] != digest(args.selection) for m in (old, new)
    ):
        raise ValueError("Comparison reference/cohort mismatch")
    rows = load_verified(args.reference, args.reference_verification) + load_verified(
        args.matrix, args.verification
    )
    seeds = tuple(profile["seeds"])
    if list(seeds) != cohort["seeds"]:
        raise ValueError("Analysis seed profile differs")
    cells = {}
    for report, errors, coverage in rows:
        b = report["binding"]["input"]
        seed = report["binding"]["config"]["initial_training"]["seed"]
        key = b["history_days"], b["entity_id"], seed, report["method"]["name"]
        if key in cells:
            raise ValueError("Duplicate comparison cell")
        if report["code"]["files"] != runtime_code()["files"] or report["code"]["dirty"]:
            raise ValueError("Analysis algorithms differ from identified run")
        cells[key] = report, errors, coverage
    expected = {
        (int(b), item["entity_id"], seed, method)
        for b, group in cohort["budgets"].items()
        for item in group["entities"]
        for seed in seeds
        for method in METHODS
    }
    if set(cells) != expected:
        raise ValueError("All five methods and all null cells required")
    for (budget, entity, seed, _), (report, _, _) in cells.items():
        ref = cells[budget, entity, seed, "adaptive"][0]
        configs = [dict(r["binding"]["config"]) for r in (ref, report)]
        for config in configs:
            config.pop("method")
        if (
            configs[0] != configs[1]
            or report["source_checkpoint_sha256"] != ref["source_checkpoint_sha256"]
        ):
            raise ValueError("Methods have different config or Source weights")
    grouped, gaps, contexts = {}, {}, {}
    pair_rows, audit_rows = [], []
    null_units = Counter()
    for budget, group in cohort["budgets"].items():
        for item in group["entities"]:
            entity = item["entity_id"]
            stratum = "initial_adaptation" if item["initial_trainable"] else "no_initial_trainable"
            for seed in seeds:
                baseline = cells[int(budget), entity, seed, "target_only"]
                origins = {e.origin for e in baseline[1]}
                if not origins:
                    null_units[budget] += 1
                for method in METHODS:
                    report, errors, coverage = cells[int(budget), entity, seed, method]
                    if {e.origin for e in errors} != origins or report["issued_days"] != baseline[
                        0
                    ]["issued_days"]:
                        raise ValueError(
                            "Methods must have identical issued/scored origin populations"
                        )
                    pair_rows.append(
                        {
                            "budget": int(budget),
                            "entity_id": entity,
                            "seed": seed,
                            "method": method,
                            "stratum": stratum,
                            "initialization": report["initialization"],
                            "issued_days": report["issued_days"],
                            "scored_days": len(errors),
                            "mae_kwh": report["active_mae_kwh"],
                            "rmse_kwh": report["active_rmse_kwh"],
                            **coverage,
                        }
                    )
                    for audit in report["audits"]:
                        audit_rows.append(
                            {
                                "run_id": report["run_id"],
                                "method": method,
                                "paired_days": audit["paired_days"],
                                "new_minus_old_mae_kwh": audit["mean_new_minus_old"]
                                * coverage["scale"],
                                "scope": "Retrospective descriptive gap; no locked harmful-switch threshold",
                            }
                        )
                    if not origins:
                        continue
                    key = budget, stratum, method
                    grouped.setdefault(key, {}).setdefault(entity, {})[seed] = paired_metrics(
                        errors, baseline[1]
                    )
                    for context in profile["contexts"]:
                        chosen = [
                            e for e in errors if (e.origin.weekday() >= 5) == (context == "weekend")
                        ]
                        other = [
                            e
                            for e in baseline[1]
                            if (e.origin.weekday() >= 5) == (context == "weekend")
                        ]
                        if chosen:
                            contexts.setdefault((*key, context), {}).setdefault(entity, {})[
                                seed
                            ] = paired_metrics(chosen, other)
                    if method != "adaptive":
                        active = cells[int(budget), entity, seed, "adaptive"][1]
                        other_errors = {e.origin: e.mae for e in errors}
                        gaps.setdefault(key, {}).setdefault(entity, {})[seed] = {
                            e.origin: e.mae - other_errors[e.origin] for e in active
                        }
    aggregates = {
        "/".join(key): station_first(value, seeds=seeds) for key, value in grouped.items()
    }
    context_results = {
        "/".join(key): station_first(value, seeds=seeds) for key, value in contexts.items()
    }
    # Read only authenticated clock metadata, not Final forecasts or labels.
    starts = set()
    for budget, group in cohort["budgets"].items():
        path = args.inputs_root / f"urbanev-SZH-{budget}d" / "manifest.json"
        if digest(path) != group["manifest_sha256"]:
            raise ValueError("Changed analysis input manifest")
        starts.add(json.loads(path.read_text())["config"]["deployment"])
    if len(starts) != 1:
        raise ValueError("Explicit common deployment required")
    start = datetime.fromisoformat(starts.pop())
    intervals = {
        "/".join(key): paired_station_time_interval(
            value, seeds=seeds, start=start, days=90, **profile["bootstrap"]
        )
        for key, value in gaps.items()
    }
    costs = {}
    for method in METHODS:
        subset = [r for r, _, _ in rows if r["method"]["name"] == method]
        costs[method] = {
            "run_count": len(subset),
            "elapsed_seconds_sum": sum(r["elapsed_seconds"] for r in subset),
            "initial_steps": sum(sum(x["steps"] for x in r["initial_logs"]) for r in subset),
            "online_candidate_steps": sum(r["candidate_steps"] for r in subset),
            "audit_steps": sum(r["audit_steps"] for r in subset),
            "decision_reasons": dict(Counter(d["reason"] for r in subset for d in r["decisions"])),
            "switches": sum(
                d["selected_lambda"] != d["active_lambda"] for r in subset for d in r["decisions"]
            ),
            "gpu_peak_allocated_bytes_max": max(r["gpu_peak_allocated_bytes"] for r in subset),
            "cost_components_sum": {
                k: sum(r["cost"][k] for r in subset) for k in subset[0]["cost"]
            },
            "scope": "Includes initialization in elapsed; Source pretraining/reused input preparation and posthoc verification excluded",
        }
    summary = {
        "scope": "Exploratory core-transfer Development comparison; no tuning/Final or superiority claim",
        "reference_sha256": digest(args.reference),
        "matrix_sha256": digest(args.matrix),
        "analysis_profile_sha256": digest(args.profile),
        "null_paired_units_by_budget": dict(null_units),
        "station_first": aggregates,
        "adaptive_minus_comparator_intervals": intervals,
        "weekday_weekend": context_results,
        "costs": costs,
        "isolated_audits": audit_rows,
        "limits": [
            "Five diagnostic methods, not complete nine-baseline/five-ablation replication",
            "Three to five scored station IDs per budget, selected nonrandomly; IDs can share locations",
            "Marginal exploratory intervals; no simultaneous comparison correction",
            "No proxy calibration, sparse/dense threshold or harmful-switch margin locked",
        ],
    }
    args.output.mkdir(exist_ok=False)
    write_json(args.output / "summary.json", summary)
    with (args.output / "runs.csv").open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(pair_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(pair_rows)
    lines = [
        "# UrbanEV core-transfer Development comparison",
        "",
        "Diagnostic settings; three seeds;90 scheduled days. No Final or tuned-winner claim.",
        "",
        "| Budget | Scored stations | Adaptive | Target-only | Full Fine-tuning | Fixed Retention | Online Best-lambda |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for b in ("7", "14", "28"):
        values = [aggregates[f"{b}/initial_adaptation/{m}"] for m in METHODS]
        lines.append(
            "| "
            + b
            + "d | "
            + str(values[0]["station_count"])
            + " | "
            + " | ".join(f"{r['macro_mae_kwh']:.6f}" for r in values)
            + " |"
        )
    lines += [
        "",
        "MAE in kWh, equal station weight after paired seed averages. Budget cohorts differ.",
        "",
        "| Budget | Adaptive minus comparator | Gap kWh | Exploratory95% interval |",
        "|---|---|---:|---|",
    ]
    for key, row in intervals.items():
        interval = (
            "undefined"
            if row["interval"] is None
            else f"[{row['interval'][0]:.6f}, {row['interval'][1]:.6f}]"
        )
        lines.append(
            f"| {key.split('/')[0]}d | {key.split('/')[-1]} | {row['gap_kwh']:.6f} | {interval} |"
        )
    lines += [
        "",
        "Negative gaps favor Adaptive. These are marginal, selected-cohort bootstrap intervals, conditional on fixed seeds. No population or causal guarantee.",
        "",
        "All null units remain explicit; no missing labels or score cells are filled. See summary.json and runs.csv for contexts, coverage, steps, switching and isolated audit gaps.",
    ]
    (args.output / "README.md").write_text("\n".join(lines) + "\n")
    print((args.output / "README.md").read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "reference",
        "matrix",
        "reference-verification",
        "verification",
        "selection",
        "profile",
        "inputs-root",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    analyze(parser.parse_args())


if __name__ == "__main__":
    main()
