"""Recompute bounded Final gain aggregation from tracked paired rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

STATIONS = ("2118", "2534", "2579")
SEEDS = ("7", "11", "19")
BUDGETS = ("7", "14", "28")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _close(actual: float, expected: float, field: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-10):
        raise ValueError(f"{field}: computed {actual}, published {expected}")


def audit(paired_path: Path, station_first_path: Path) -> dict:
    """Check the exact locked Main/Target-only cells and both gain estimands."""
    pairs = _read_csv(paired_path)
    published = _read_csv(station_first_path)
    results = []
    for budget in BUDGETS:
        selected = [
            row
            for row in pairs
            if row["dataset_id"] == "urbanev"
            and row["city_id"] == "SZH"
            and row["budget_days"] == budget
            and row["variant"] == "main"
            and row["reference"] == "target_only"
        ]
        identities = [(row["entity_id"], row["seed"]) for row in selected]
        expected = {(station, seed) for station in STATIONS for seed in SEEDS}
        if len(identities) != 9 or set(identities) != expected:
            raise ValueError(f"Budget {budget}: Main/Target-only paired jobset mismatch")
        if any(row["source_using"] != "True" or int(row["paired_days"]) <= 0 for row in selected):
            raise ValueError(f"Budget {budget}: invalid transfer or paired-day identity")
        by_station: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in selected:
            by_station[row["entity_id"]].append(row)
        station_rows = []
        for station in STATIONS:
            rows = by_station[station]
            method = statistics.fmean(float(row["method_mae_kwh"]) for row in rows)
            reference = statistics.fmean(float(row["reference_mae_kwh"]) for row in rows)
            if reference <= 0:
                raise ValueError(f"Budget {budget}, station {station}: undefined gain denominator")
            station_rows.append(
                {
                    "station": station,
                    "method_mae_kwh": method,
                    "reference_mae_kwh": reference,
                    "mae_gain_kwh": reference - method,
                    "station_transfer_gain": (reference - method) / reference,
                }
            )
        method_mean = statistics.fmean(row["method_mae_kwh"] for row in station_rows)
        reference_mean = statistics.fmean(row["reference_mae_kwh"] for row in station_rows)
        gain_mean = reference_mean - method_mean
        ratio_of_means = gain_mean / reference_mean
        mean_station_ratios = statistics.fmean(row["station_transfer_gain"] for row in station_rows)
        negative = sum(row["mae_gain_kwh"] < 0 for row in station_rows)
        matches = [
            row
            for row in published
            if row["dataset_id"] == "urbanev"
            and row["city_id"] == "SZH"
            and row["budget_days"] == budget
            and row["variant"] == "main"
            and row["reference"] == "target_only"
        ]
        if len(matches) != 1:
            raise ValueError(f"Budget {budget}: expected one published station-first row")
        record = matches[0]
        for field, value in (
            ("method_mae_kwh", method_mean),
            ("reference_mae_kwh", reference_mean),
            ("mae_gain_kwh", gain_mean),
            ("transfer_gain", ratio_of_means),
            ("negative_transfer_stations", negative),
            ("negative_transfer_denominator", 3),
            ("negative_transfer_rate", negative / 3),
            ("paired_cells", 9),
        ):
            _close(value, float(record[field]), f"Budget {budget} {field}")
        results.append(
            {
                "budget_days": int(budget),
                "paired_cells": 9,
                "stations": station_rows,
                "published_transfer_gain_ratio_of_means": ratio_of_means,
                "mean_of_station_transfer_gains": mean_station_ratios,
                "negative_transfer_stations": negative,
            }
        )
    return {
        "schema": "hung-final-gain-aggregation-audit-v1",
        "paired_csv_sha256": _sha256(paired_path),
        "station_first_csv_sha256": _sha256(station_first_path),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired", required=True, type=Path)
    parser.add_argument("--station-first", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"refusing to overwrite {args.output}")
    result = audit(args.paired, args.station_first)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "budgets": len(result["results"])}))


if __name__ == "__main__":
    main()
