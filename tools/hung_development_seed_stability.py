"""Audit Development paired-gain stability across frozen seeds and stations."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SOURCE_SHA256 = "82d9342c62baef0da9e6f70baf548fb9e97e653792305adbb0fb85c872a1173d"
METRICS = ("mae_kwh", "rmse_kwh")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inside_repo(path: Path) -> Path:
    resolved = path.resolve()
    require(resolved.is_relative_to(ROOT), f"Path must be inside repository: {path}")
    return resolved


def gain(cell: dict, metric: str) -> float:
    reference = cell["reference_metrics"][metric]
    method = cell["method_metrics"][metric]
    require(
        isinstance(reference, (int, float)) and isinstance(method, (int, float)), "Missing metric"
    )
    return float(reference - method)


def sign(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def summarize_group(cells: list[dict], station_first: dict) -> tuple[dict, list[dict]]:
    budget = cells[0]["budget"]
    method = cells[0]["method"]
    reference = cells[0]["reference"]
    by_station: dict[str, list[dict]] = defaultdict(list)
    by_seed: dict[int, list[dict]] = defaultdict(list)
    for cell in cells:
        station = str(cell["entity_id"])
        by_station[station].append(cell)
        by_seed[cell["seed"]].append(cell)
    stations = sorted(by_station)
    seeds = sorted(by_seed)
    require(len(seeds) in (1, 3), "Unexpected seed count")
    require(set(seeds) in ({7}, {7, 11, 19}), "Unexpected seed set")
    require(
        all({str(c["entity_id"]) for c in group} == set(stations) for group in by_seed.values()),
        "Seed station sets differ",
    )
    for group in by_station.values():
        require(len(group) == len(seeds), "Incomplete station seed coverage")
        require(
            len({c["paired_day_ids_sha256"] for c in group}) == 1, "Seed paired-day hashes differ"
        )
        require(len({c["paired_days"] for c in group}) == 1, "Seed paired-day counts differ")

    seed_rows = []
    for seed in seeds:
        selected = by_seed[seed]
        station_mae = [gain(c, "mae_kwh") for c in selected]
        station_rmse = [gain(c, "rmse_kwh") for c in selected]
        seed_rows.append(
            {
                "budget_days": budget,
                "method": method,
                "reference": reference,
                "seed": seed,
                "stations": len(stations),
                "paired_cells": len(selected),
                "mae_gain_kwh": mean(station_mae),
                "rmse_gain_kwh": mean(station_rmse),
                "positive_mae_stations": sum(v > 0 for v in station_mae),
                "negative_mae_stations": sum(v < 0 for v in station_mae),
                "zero_mae_stations": sum(v == 0 for v in station_mae),
            }
        )

    station_signs = []
    for station in stations:
        values = [gain(c, "mae_kwh") for c in by_station[station]]
        unique = {sign(v) for v in values}
        station_signs.append(next(iter(unique)) if len(unique) == 1 else "mixed")
    means_mae = [row["mae_gain_kwh"] for row in seed_rows]
    means_rmse = [row["rmse_gain_kwh"] for row in seed_rows]
    saved_mae = (
        station_first["reference_metrics"]["mae_kwh"] - station_first["method_metrics"]["mae_kwh"]
    )
    saved_rmse = (
        station_first["reference_metrics"]["rmse_kwh"] - station_first["method_metrics"]["rmse_kwh"]
    )
    require(
        abs(mean(means_mae) - saved_mae) < 1e-9,
        "MAE aggregate differs from saved station-first row",
    )
    require(
        abs(mean(means_rmse) - saved_rmse) < 1e-9,
        "RMSE aggregate differs from saved station-first row",
    )
    summary = {
        "budget_days": budget,
        "method": method,
        "reference": reference,
        "stations": len(stations),
        "seeds_per_station": len(seeds),
        "paired_cells": len(cells),
        "paired_days_per_station_min": min(c["paired_days"] for c in cells),
        "paired_days_per_station_max": max(c["paired_days"] for c in cells),
        "station_first_mae_gain_kwh": mean(means_mae),
        "mae_seed_min_kwh": min(means_mae),
        "mae_seed_max_kwh": max(means_mae),
        "mae_seed_span_kwh": max(means_mae) - min(means_mae) if len(seeds) > 1 else None,
        "rmse_seed_min_kwh": min(means_rmse),
        "rmse_seed_max_kwh": max(means_rmse),
        "rmse_seed_span_kwh": max(means_rmse) - min(means_rmse) if len(seeds) > 1 else None,
        "all_positive_mae_stations": station_signs.count("positive"),
        "all_negative_mae_stations": station_signs.count("negative"),
        "all_zero_mae_stations": station_signs.count("zero"),
        "mixed_sign_mae_stations": station_signs.count("mixed"),
    }
    return summary, seed_rows


def audit(source: dict) -> tuple[list[dict], list[dict], dict]:
    require(source.get("scope") == "development_only", "Development source required")
    require(source.get("counts", {}).get("runs") == 851, "Expected 851 physical runs")
    cells = source.get("paired_cells")
    saved = source.get("station_first")
    require(isinstance(cells, list) and len(cells) == 816, "Expected 816 paired cells")
    require(isinstance(saved, list) and len(saved) == 72, "Expected 72 station-first rows")
    keys = [
        (c["budget"], c["method"], c["reference"], str(c["entity_id"]), c["seed"]) for c in cells
    ]
    require(len(keys) == len(set(keys)), "Duplicate paired cell")
    saved_by_group = {(r["budget"], r["method"], r["reference"]): r for r in saved}
    require(len(saved_by_group) == 72, "Duplicate station-first group")
    by_group: dict[tuple, list[dict]] = defaultdict(list)
    for cell in cells:
        by_group[(cell["budget"], cell["method"], cell["reference"])].append(cell)
    require(set(by_group) == set(saved_by_group), "Paired/station-first groups differ")
    summaries, seed_rows = [], []
    for key in sorted(by_group):
        summary, rows = summarize_group(by_group[key], saved_by_group[key])
        summaries.append(summary)
        seed_rows.extend(rows)
    context_fields = sorted(
        {
            k
            for row in cells + saved
            for k in row
            if any(word in k.lower() for word in ("context", "season", "weekday", "hour", "period"))
        }
    )
    proxy_values = sorted(
        {
            k
            for row in source["runs"]
            for k in row
            if any(
                word in k.lower()
                for word in ("proxy_value", "proxy_signal", "drift_value", "uncertainty_value")
            )
        }
    )
    metadata = {
        "schema": "hung-development-seed-stability-v1",
        "scope": "development_only",
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "paired_groups": len(summaries),
        "paired_cells": len(cells),
        "seed_rows": len(seed_rows),
        "three_seed_groups": sum(r["seeds_per_station"] == 3 for r in summaries),
        "single_seed_groups": sum(r["seeds_per_station"] == 1 for r in summaries),
        "mixed_sign_stations_across_three_seed_groups": sum(
            r["mixed_sign_mae_stations"] for r in summaries if r["seeds_per_station"] == 3
        ),
        "context_fields_in_paired_source": context_fields,
        "per_origin_proxy_value_fields_in_merged_runs": proxy_values,
    }
    return summaries, seed_rows, metadata


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    input_path = inside_repo(args.input)
    output = inside_repo(args.output_dir)
    require(args.sha256 == EXPECTED_SOURCE_SHA256, "Unexpected source pin")
    raw = input_path.read_bytes()
    require(sha256_bytes(raw) == args.sha256, "Source SHA-256 mismatch")
    require(not output.exists(), "Output directory already exists")
    source = json.loads(raw)
    summaries, seed_rows, metadata = audit(source)
    output.mkdir(parents=True)
    write_csv(output / "seed_stability.csv", summaries)
    write_csv(output / "seed_gains.csv", seed_rows)
    (output / "summary.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(metadata, sort_keys=True))


if __name__ == "__main__":
    main()
