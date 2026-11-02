"""Independent read-only cross-check of the published Development matrix tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def _key(row: dict, budget_field: str = "budget") -> tuple[int, str, int, str, str]:
    return (
        int(row[budget_field]),
        str(row["entity_id"]),
        int(row["seed"]),
        row["method"],
        row["reference"],
    )


def _unique(items: list, label: str) -> None:
    if len(items) != len(set(items)):
        raise ValueError(f"Duplicate {label}")


def _close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError(f"{label}: {actual} != {expected}")


def _station_key(row: dict) -> tuple[int, str, str]:
    return int(row["budget"]), row["method"], row["reference"]


def audit(
    matrix_path: Path,
    zero_path: Path,
    blocked_path: Path,
    station_path: Path,
    expected_matrix_sha256: str,
) -> dict:
    """Recompute coverage, pair keys, and station-first values from a pinned matrix."""
    digest = hashlib.sha256(matrix_path.read_bytes()).hexdigest()
    if digest != expected_matrix_sha256:
        raise ValueError(f"Matrix SHA-256 mismatch: {digest}")
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    runs = matrix["runs"]
    run_ids = [run["job_id"] for run in runs]
    _unique(run_ids, "run ID")
    run_keys = [
        (int(run["budget"]), str(run["entity_id"]), int(run["seed"]), run["method"]) for run in runs
    ]
    _unique(run_keys, "run cohort key")
    run_set = set(run_keys)
    zero_ids = {run["job_id"] for run in runs if run["metrics"] is None}
    if any((run["metrics"] is None) != (run["coverage"]["scored"] == 0) for run in runs):
        raise ValueError("Null metric/scored-day mismatch")
    zero_csv = _rows(zero_path)
    _unique([row["job_id"] for row in zero_csv], "zero-score CSV job ID")
    if {row["job_id"] for row in zero_csv} != zero_ids:
        raise ValueError("Zero-score CSV does not match matrix null scores")
    if matrix["counts"] != {
        "runs": len(runs),
        "scorable_runs": len(runs) - len(zero_ids),
        "zero_scored_runs": len(zero_ids),
    }:
        raise ValueError("Matrix summary counts disagree with runs")

    pairs = matrix["paired_cells"]
    blocked = matrix["blocked_pairs"]
    pair_keys = [_key(row) for row in pairs]
    blocked_keys = [_key(row) for row in blocked]
    _unique(pair_keys, "valid pair")
    _unique(blocked_keys, "blocked pair")
    if set(pair_keys) & set(blocked_keys):
        raise ValueError("Pair appears in both valid and blocked sets")
    for row in (*pairs, *blocked):
        budget, entity, seed, method, reference = _key(row)
        if (budget, entity, seed, method) not in run_set or (
            budget,
            entity,
            seed,
            reference,
        ) not in run_set:
            raise ValueError("Pair references an absent run")
    for row in pairs:
        if row["paired_days"] <= 0 or any(
            row[side]["hours"] != 24 * row["paired_days"]
            for side in ("method_metrics", "reference_metrics")
        ):
            raise ValueError("Invalid paired day/hour count")
    blocked_csv = _rows(blocked_path)
    _unique([_key(row, "budget_days") for row in blocked_csv], "blocked CSV pair")
    if {_key(row, "budget_days"): row["reason"] for row in blocked_csv} != {
        _key(row): row["reason"] for row in blocked
    }:
        raise ValueError("Blocked-pair CSV does not match matrix")

    grouped: dict[tuple[int, str, str, str], list[dict]] = defaultdict(list)
    for row in pairs:
        grouped[
            (int(row["budget"]), row["method"], row["reference"], str(row["entity_id"]))
        ].append(row)
    station_rows = matrix["station_first"]
    csv_rows = _rows(station_path)
    _unique([_station_key(row) for row in station_rows], "matrix station-first group")
    _unique([_station_key(row) for row in csv_rows], "CSV station-first group")
    if {_station_key(row) for row in station_rows} != {_station_key(row) for row in csv_rows}:
        raise ValueError("Station-first CSV group set mismatch")
    csv_by_key = {_station_key(row): row for row in csv_rows}
    for row in station_rows:
        key = _station_key(row)
        stations = [values for group_key, values in grouped.items() if group_key[:3] == key]
        if (
            len(stations) != row["stations"]
            or min(map(len, stations)) != row["minimum_seeds_per_station"]
        ):
            raise ValueError(f"Station/seed count mismatch: {key}")
        method_mae = [
            statistics.mean(cell["method_metrics"]["mae_kwh"] for cell in values)
            for values in stations
        ]
        reference_mae = [
            statistics.mean(cell["reference_metrics"]["mae_kwh"] for cell in values)
            for values in stations
        ]
        for side, values in (("method_metrics", method_mae), ("reference_metrics", reference_mae)):
            _close(statistics.mean(values), row[side]["mae_kwh"], f"{key} {side} MAE")
            rmse = statistics.mean(
                statistics.mean(cell[side]["rmse_kwh"] for cell in station) for station in stations
            )
            _close(rmse, row[side]["rmse_kwh"], f"{key} {side} RMSE")
        gain = statistics.mean(reference_mae) - statistics.mean(method_mae)
        _close(gain, row["absolute_mae_gain_kwh"], f"{key} absolute gain")
        _close(
            gain / statistics.mean(reference_mae), row["relative_mae_gain"], f"{key} relative gain"
        )
        worse = statistics.mean(float(m > r) for m, r in zip(method_mae, reference_mae))
        _close(worse, row["worse_than_reference_station_fraction"], f"{key} worse fraction")
        csv_row = csv_by_key[key]
        for name, value in (
            ("absolute_mae_gain_kwh", gain),
            ("relative_mae_gain", row["relative_mae_gain"]),
            ("method_metrics_mae_kwh", row["method_metrics"]["mae_kwh"]),
            ("reference_metrics_mae_kwh", row["reference_metrics"]["mae_kwh"]),
        ):
            _close(float(csv_row[name]), value, f"{key} CSV {name}")
    return {
        "schema": "hung-development-matrix-crosscheck-v1",
        "matrix_sha256": digest,
        "unique_runs": len(runs),
        "scored_runs": len(runs) - len(zero_ids),
        "null_scored_runs": len(zero_ids),
        "valid_pairs": len(pairs),
        "blocked_pairs": len(blocked),
        "station_first_groups": len(station_rows),
        "station_first_numeric_mismatches": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--zero", type=Path, required=True)
    parser.add_argument("--blocked", type=Path, required=True)
    parser.add_argument("--station", type=Path, required=True)
    parser.add_argument("--matrix-sha256", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            audit(args.matrix, args.zero, args.blocked, args.station, args.matrix_sha256),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
