"""Audit pinned Development coverage, paired uncertainty, decisions and cost.

This reads completed Development artifacts only. Missing scores and unavailable
runtime fields remain null; it neither trains nor selects a Final setting.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import statistics
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pinned(path: Path, digest: str) -> Path:
    path = path.resolve()
    require(path.is_relative_to(ROOT), "Input outside repository")
    require(sha256(path) == digest, f"Input SHA mismatch: {path.name}")
    return path


def percentile(values: list[float], fraction: float) -> float:
    require(bool(values) and 0 <= fraction <= 1, "Invalid percentile input")
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    left = math.floor(index)
    right = math.ceil(index)
    return ordered[left] + (ordered[right] - ordered[left]) * (index - left)


def exact_station_bootstrap(values: list[float]) -> tuple[float, float]:
    """Exact n^n station bootstrap, preserving each station's seed mean."""
    require(1 <= len(values) <= 5, "Expected 1–5 scorable stations")
    replicates = [
        statistics.fmean(values[index] for index in draw)
        for draw in itertools.product(range(len(values)), repeat=len(values))
    ]
    return percentile(replicates, 0.025), percentile(replicates, 0.975)


def paired_uncertainty(merged: dict) -> list[dict]:
    groups: dict[tuple[int, str, str], list[dict]] = defaultdict(list)
    for cell in merged["paired_cells"]:
        groups[(cell["budget"], cell["method"], cell["reference"])].append(cell)
    station_first = {
        (row["budget"], row["method"], row["reference"]): row for row in merged["station_first"]
    }
    require(set(groups) == set(station_first), "Station-first pair set differs")
    results = []
    for key, cells in sorted(groups.items()):
        budget, method, reference = key
        by_station: dict[str, list[dict]] = defaultdict(list)
        for cell in cells:
            by_station[cell["entity_id"]].append(cell)
        mae_gains = []
        rmse_gains = []
        seed_counts = []
        for station in sorted(by_station):
            station_cells = by_station[station]
            seed_counts.append(len(station_cells))
            mae_gains.append(
                statistics.fmean(
                    c["reference_metrics"]["mae_kwh"] - c["method_metrics"]["mae_kwh"]
                    for c in station_cells
                )
            )
            rmse_gains.append(
                statistics.fmean(
                    c["reference_metrics"]["rmse_kwh"] - c["method_metrics"]["rmse_kwh"]
                    for c in station_cells
                )
            )
        published = station_first[key]
        mae_gain = statistics.fmean(mae_gains)
        require(
            math.isclose(mae_gain, published["absolute_mae_gain_kwh"], abs_tol=1e-8),
            f"Published station MAE differs: {key}",
        )
        mae_low, mae_high = exact_station_bootstrap(mae_gains)
        rmse_low, rmse_high = exact_station_bootstrap(rmse_gains)
        ntr_count = None
        ntr_fraction = published["negative_transfer_station_fraction"]
        if reference == "target_only" and ntr_fraction is not None:
            ntr_count = sum(gain < 0 for gain in mae_gains)
            require(
                math.isclose(ntr_count / len(mae_gains), ntr_fraction, abs_tol=1e-8),
                f"Published NTR differs: {key}",
            )
        results.append(
            {
                "budget_days": budget,
                "method": method,
                "reference": reference,
                "stations": len(mae_gains),
                "paired_cells": len(cells),
                "minimum_seeds_per_station": min(seed_counts),
                "mae_gain_kwh": mae_gain,
                "mae_gain_ci95_low_kwh": mae_low,
                "mae_gain_ci95_high_kwh": mae_high,
                "rmse_gain_kwh": statistics.fmean(rmse_gains),
                "rmse_gain_ci95_low_kwh": rmse_low,
                "rmse_gain_ci95_high_kwh": rmse_high,
                "negative_transfer_stations": ntr_count,
                "negative_transfer_denominator": len(mae_gains) if ntr_count is not None else None,
                "negative_transfer_fraction": ntr_fraction,
            }
        )
    return results


def zero_score_audit(merged: dict) -> tuple[list[dict], list[dict]]:
    rows = [row for row in merged["runs"] if row["coverage"]["scored"] == 0]
    by_cell: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for row in rows:
        coverage = row["coverage"]
        require(
            coverage["created"] > 0
            and coverage["unscored_created"] == coverage["created"]
            and row["metrics"] is None,
            f"Unexpected zero-score coverage: {row['job_id']}",
        )
        by_cell[(row["budget"], row["entity_id"])].append(row)
    cells = []
    for (budget, entity), members in sorted(by_cell.items()):
        cells.append(
            {
                "budget_days": budget,
                "entity_id": entity,
                "runs": len(members),
                "created_forecasts_per_run": sorted({r["coverage"]["created"] for r in members}),
                "requested_per_run": sorted({r["coverage"]["requested"] for r in members}),
                "scored_days": sum(r["coverage"]["scored"] for r in members),
                "unscored_created_forecasts": sum(
                    r["coverage"]["unscored_created"] for r in members
                ),
            }
        )
    return rows, cells


def switch_audit(merged: dict, ledger: list[dict]) -> list[dict]:
    runs = {row["job_id"]: row for row in merged["runs"]}
    kaggle = [row for row in ledger if row["provider_route"] == "kaggle"]
    require(len(kaggle) == 560, "Kaggle ledger count differs")
    archive_pins: dict[str, tuple[int, str]] = {}
    for row in kaggle:
        path = row["archive_path"]
        pin = (int(row["archive_bytes"]), row["archive_sha256"])
        require(path not in archive_pins or archive_pins[path] == pin, "Conflicting archive pin")
        archive_pins[path] = pin
    for name, (size, digest) in archive_pins.items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT / ".cache"), "Archive outside repository cache")
        require(path.stat().st_size == size and sha256(path) == digest, "Archive bytes/SHA differ")
    results = []
    for row in kaggle:
        job_id = row["job_id"]
        archive = (ROOT / row["archive_path"]).resolve()
        member = f"jobs/{job_id}/replay-90/run_manifest.json"
        with zipfile.ZipFile(archive) as bundle:
            receipt_raw = bundle.read(row["job_receipt_path"])
            raw = bundle.read(member)
        receipt_sha = hashlib.sha256(receipt_raw).hexdigest()
        require(receipt_sha == row["job_receipt_sha256"], f"Job receipt SHA differs: {job_id}")
        receipt = json.loads(receipt_raw)
        require(receipt["job_id"] == job_id, f"Receipt job ID differs: {job_id}")
        manifest_sha = hashlib.sha256(raw).hexdigest()
        stages = dict(item.split(":", 1) for item in row["stage_manifest_sha256"].split(";"))
        require(stages.get("replay-90") == manifest_sha, f"Final manifest SHA differs: {job_id}")
        manifest = json.loads(raw)
        require(manifest["run_id"] == "replay-90", f"Final stage differs: {job_id}")
        evidence = manifest.get("event_evidence", {})
        decisions = evidence.get("decisions")
        require(
            isinstance(decisions, list)
            or (decisions is None and isinstance(evidence.get("issued_count"), int)),
            f"Decision trace/issued evidence absent: {job_id}",
        )
        for decision in decisions or []:
            require(
                isinstance(decision.get("current_level"), (int, float))
                and isinstance(decision.get("selected_level"), (int, float)),
                f"Decision level absent: {job_id}",
            )
        cost = runs[job_id]["cumulative_runtime_costs"]
        audit = cost.get("audit") if cost.get("complete") is True else None
        results.append(
            {
                "job_id": job_id,
                "method": row["method"],
                "budget_days": int(row["budget_days"]),
                "entity_id": row["entity_id"],
                "seed": int(row["seed"]),
                "archive_sha256": row["archive_sha256"],
                "job_receipt_sha256": receipt_sha,
                "final_manifest_sha256": manifest_sha,
                "decisions": len(decisions) if decisions is not None else None,
                "switches": sum(d["selected_level"] != d["current_level"] for d in decisions)
                if decisions is not None
                else None,
                "audit_inference_calls": audit["inference_calls"] if audit else None,
                "audit_update_steps": audit["update_steps"] if audit else None,
            }
        )
    return results


def cost_groups(merged: dict) -> list[dict]:
    groups: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for run in merged["runs"]:
        device = run["device"].get("name") or run["device"].get("type") or "unreported"
        groups[(run["method"], run["budget"], device)].append(run)
    results = []
    for (method, budget, device), runs in sorted(groups.items()):
        durations = [r["final_stage_duration_seconds"] for r in runs]
        split = [r for r in runs if r["cumulative_runtime_costs"].get("complete") is True]
        legacy = len(runs) - len(split)
        proxy = [
            r["cumulative_proxy_costs"] for r in runs if r["cumulative_proxy_costs"] is not None
        ]
        results.append(
            {
                "method": method,
                "budget_days": budget,
                "device": device,
                "runs": len(runs),
                "split_cost_complete_runs": len(split),
                "legacy_cost_runs": legacy,
                "final_stage_mean_seconds": statistics.fmean(durations),
                "final_stage_p95_seconds": percentile(durations, 0.95),
                "candidate_inference_calls_mean": statistics.fmean(
                    sum(c["inference_calls"] for c in r["cumulative_runtime_costs"]["candidate"])
                    for r in split
                )
                if split
                else None,
                "candidate_update_steps_mean": statistics.fmean(
                    sum(c["update_steps"] for c in r["cumulative_runtime_costs"]["candidate"])
                    for r in split
                )
                if split
                else None,
                "audit_inference_calls_mean": statistics.fmean(
                    r["cumulative_runtime_costs"]["audit"]["inference_calls"] for r in split
                )
                if split
                else None,
                "audit_update_steps_mean": statistics.fmean(
                    r["cumulative_runtime_costs"]["audit"]["update_steps"] for r in split
                )
                if split
                else None,
                "proxy_inference_calls_mean": statistics.fmean(r["inference_calls"] for r in proxy)
                if proxy
                else None,
            }
        )
    return results


def write_csv(path: Path, rows: list[dict]) -> None:
    require(bool(rows), f"No rows for {path.name}")
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit(merged: dict, ledger: list[dict], source_sha: str, ledger_sha: str, out: Path) -> dict:
    require(merged["scope"] == "development_only", "Not Development results")
    require(
        merged["counts"] == {"runs": 851, "scorable_runs": 444, "zero_scored_runs": 407},
        "Unexpected run coverage",
    )
    ledger_ids = {row["job_id"] for row in ledger}
    dispatch_ids = {row["job_id"] for row in merged["runs"] if row["status"] == "DISPATCH_VERIFIED"}
    require(
        len(ledger) == 782 and len(ledger_ids) == 782 and dispatch_ids == ledger_ids,
        "Ledger/run set differs",
    )
    zero_rows, zero_cells = zero_score_audit(merged)
    require(len(zero_rows) == 407 and len(zero_cells) == 11, "Zero-score structure changed")
    blocked = merged["blocked_pairs"]
    require(len(blocked) == 748, "Blocked-pair count changed")
    blocked_reasons = dict(sorted(Counter(row["reason"] for row in blocked).items()))
    require(
        blocked_reasons == {"no_paired_scored_days": 748},
        "Unexpected blocked-pair reason",
    )
    blocked_cells = Counter((row["budget"], row["entity_id"]) for row in blocked)
    zero_cell_keys = {(row["budget_days"], row["entity_id"]) for row in zero_cells}
    require(
        set(blocked_cells) == zero_cell_keys and set(blocked_cells.values()) == {68},
        "Blocked pairs do not align with zero-score cells",
    )
    paired = paired_uncertainty(merged)
    switches = switch_audit(merged, ledger)
    costs = cost_groups(merged)
    out = out.resolve()
    require(
        out.is_relative_to(ROOT / "docs/reports") and not out.exists(),
        "Output must be new reports directory",
    )
    out.mkdir(parents=True, exist_ok=False)
    write_csv(
        out / "zero_scored.csv",
        [
            {
                "job_id": r["job_id"],
                "method": r["method"],
                "budget_days": r["budget"],
                "entity_id": r["entity_id"],
                "seed": r["seed"],
                **r["coverage"],
            }
            for r in zero_rows
        ],
    )
    write_csv(
        out / "blocked_pairs.csv",
        [
            {
                "budget_days": r["budget"],
                "entity_id": r["entity_id"],
                "seed": r["seed"],
                "method": r["method"],
                "reference": r["reference"],
                "reason": r["reason"],
            }
            for r in blocked
        ],
    )
    write_csv(out / "paired_uncertainty.csv", paired)
    write_csv(out / "switch_audit_kaggle.csv", switches)
    write_csv(out / "cost_by_method_device.csv", costs)
    switch_groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in switches:
        switch_groups[(row["method"], row["budget_days"])].append(row)
    switch_summary = [
        {
            "method": method,
            "budget_days": budget,
            "runs": len(rows),
            "decision_trace_runs": sum(r["decisions"] is not None for r in rows),
            "decisions": sum(r["decisions"] for r in rows if r["decisions"] is not None),
            "switches": sum(r["switches"] for r in rows if r["switches"] is not None),
            "audit_inference_calls": sum(
                r["audit_inference_calls"] for r in rows if r["audit_inference_calls"] is not None
            ),
            "audit_update_steps": sum(
                r["audit_update_steps"] for r in rows if r["audit_update_steps"] is not None
            ),
            "audit_cost_complete_runs": sum(r["audit_inference_calls"] is not None for r in rows),
        }
        for (method, budget), rows in sorted(switch_groups.items())
    ]
    summary = {
        "schema": "hung-development-audit-v1",
        "scope": "development_only",
        "source_sha256": source_sha,
        "ledger_sha256": ledger_sha,
        "counts": merged["counts"],
        "zero_scored_station_budget_cells": zero_cells,
        "blocked_pair_reasons": blocked_reasons,
        "valid_paired_cells": len(merged["paired_cells"]),
        "paired_groups": len(paired),
        "switch_coverage": {
            "kaggle_manifests_checked": len(switches),
            "decision_trace_runs": sum(r["decisions"] is not None for r in switches),
            "fixed_policy_without_decision_trace": sum(r["decisions"] is None for r in switches),
            "all_physical_runs": len(merged["runs"]),
        },
        "switch_by_method_budget": switch_summary,
        "cost_schema_coverage": {
            "split_complete": sum(
                r["cumulative_runtime_costs"].get("complete") is True for r in merged["runs"]
            ),
            "legacy_without_split": sum(
                r["cumulative_runtime_costs"].get("complete") is not True for r in merged["runs"]
            ),
        },
        "limits": [
            "No saved cause distinguishes not-yet-arrived from intrinsically absent labels for zero-scored forecasts.",
            "Exact switch trace is available for 560 Kaggle jobs; other 291 run manifests are not inside this repository.",
            "Final-stage seconds exclude upstream training, upload and readback; devices are not paired for speed.",
            "Station bootstrap uses only 3–5 scorable stations per budget and is descriptive, not a population guarantee.",
        ],
    }
    with (out / "summary.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--ledger-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    merged = json.loads(pinned(args.input, args.sha256).read_bytes())
    with pinned(args.ledger, args.ledger_sha256).open(encoding="utf-8", newline="") as stream:
        ledger = list(csv.DictReader(stream))
    summary = audit(merged, ledger, args.sha256, args.ledger_sha256, args.output_dir)
    print(
        json.dumps(
            {
                "output": str(args.output_dir),
                "counts": summary["counts"],
                "blocked": summary["blocked_pair_reasons"],
            }
        )
    )


if __name__ == "__main__":
    main()
