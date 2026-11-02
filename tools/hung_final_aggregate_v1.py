"""Aggregate authenticated Hùng Final CPU scores under the frozen analysis rule."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_SHA = "e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e"
JOBSET_SHA = "7d09583446d9437cec63956f1673c6d1927428ff80ba59a8a876b9391a7c68a2"
LEDGER_SHA = "0dca10975d5431ac199909ccb5bf69298040d6e4a21d3424bd15986a26cfa0a8"
ARCHIVE_SHA = "531bff0d24ddf7eb0a08d4ed9d97976e55140b81025db0d91c28c557684e1114"
SOURCE = "hungluongduc/hung-final-e5e8fe1c-360-20261029-v1/1"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pinned_json(path: Path, digest: str) -> dict:
    assert path.resolve().is_relative_to(ROOT.resolve()), "Input outside repository"
    assert path.is_file() and sha256(path) == digest, f"Input SHA mismatch: {path.name}"
    return json.loads(path.read_text(encoding="utf-8"))


def metric(days: list[dict]) -> dict | None:
    if not days:
        return None
    hours = 24 * len(days)
    return {
        "hours": hours,
        "mae_kwh": math.fsum(day["absolute"] for day in days) / hours,
        "rmse_kwh": math.sqrt(math.fsum(day["squared"] for day in days) / hours),
    }


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def station_interval(values: list[float]) -> tuple[float, float]:
    assert 1 <= len(values) <= 5, "Frozen exact bootstrap supports 1–5 stations"
    draws = [
        statistics.fmean(values[i] for i in indexes)
        for indexes in itertools.product(range(len(values)), repeat=len(values))
    ]
    return percentile(draws, 0.025), percentile(draws, 0.975)


def validate_rows(scores: dict, receipt: dict, jobs: dict, ledger: dict) -> list[dict]:
    assert scores["schema"] == "hung-final-remote-run-scores-v1"
    assert receipt["schema"] == "hung-final-remote-metrics-receipt-v1"
    assert receipt["status"] == "FINAL_RUN_SCORES_RECOMPUTED_FROM_CHECKPOINTS"
    assert scores["source_kernel"] == receipt["source_kernel"] == SOURCE
    assert scores["source_run_id"] == receipt["source_run_id"] == 363367272
    assert scores["lock_sha256"] == receipt["lock_sha256"] == LOCK_SHA
    assert scores["archive_sha256"] == receipt["archive_sha256"] == ARCHIVE_SHA
    assert ledger["schema"] == "hung-final-job-artifact-ledger-v1"
    assert ledger["source_kernel"] == SOURCE and ledger["source_run_id"] == 363367272
    rows = scores["jobs"]
    assert len(rows) == receipt["jobs"] == len(jobs) == len(ledger["jobs"]) == 360
    assert {row["job_id"] for row in rows} == set(jobs) == set(ledger["jobs"])
    assert len({row["job_id"] for row in rows}) == 360
    for row in rows:
        job_id = row["job_id"]
        job = jobs[job_id]
        for key in (
            "dataset_id",
            "city_id",
            "entity_id",
            "budget_days",
            "seed",
            "variant",
            "method",
            "input_manifest_sha256",
            "source_checkpoint_sha256",
            "target_checkpoint_sha256",
        ):
            assert row[key] == job[key], f"Job binding mismatch: {job_id}/{key}"
        replay = ledger["jobs"][job_id]["replay"]
        assert replay["manifest"] == f"stages/{job_id}/replay/run_manifest.json"
        assert len(row["manifest_sha256"]) == 64
        checkpoints = [
            name
            for name in replay["artifacts"]
            if name.endswith(("runner.pt", "runner_checkpoint.pt"))
        ]
        assert len(checkpoints) == 1
        assert checkpoints[0].startswith(f"stages/{job_id}/replay/")
        assert len(row["checkpoint_sha256"]) == 64
        coverage = row["coverage"]
        days = row["days"]
        assert coverage["created"] == coverage["scored"] + coverage["unscored_created"]
        assert coverage["scored"] == len(days)
        assert coverage["requested"] == 90
        assert coverage["created"] <= 90
        for day_id, day in days.items():
            assert day_id and set(day) == {"absolute", "squared", "label_sha256"}
            assert all(math.isfinite(day[key]) and day[key] >= 0 for key in ("absolute", "squared"))
            assert len(day["label_sha256"]) == 64
        computed = metric(list(days.values()))
        declared = row["metrics"]
        assert (computed is None) == (declared is None)
        if computed is not None:
            for key, value in computed.items():
                assert math.isclose(value, declared[key], rel_tol=1e-9, abs_tol=1e-9)
    assert receipt["scored_jobs"] == sum(row["metrics"] is not None for row in rows)
    assert receipt["null_jobs"] == sum(row["metrics"] is None for row in rows)
    return rows


def pair_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    by_cell = defaultdict(dict)
    for row in rows:
        key = (row["dataset_id"], row["city_id"], row["entity_id"], row["budget_days"], row["seed"])
        assert row["variant"] not in by_cell[key]
        by_cell[key][row["variant"]] = row
    paired, blocked = [], []
    for cell, variants in sorted(by_cell.items()):
        for reference in ("target_only", "main"):
            assert reference in variants, f"Missing reference at {cell}"
            ref = variants[reference]
            for variant, candidate in sorted(variants.items()):
                if variant == reference:
                    continue
                reason = None
                if candidate["input_manifest_sha256"] != ref["input_manifest_sha256"]:
                    reason = "input_mismatch"
                common = sorted(candidate["days"].keys() & ref["days"].keys())
                if any(
                    candidate["days"][day]["label_sha256"] != ref["days"][day]["label_sha256"]
                    for day in common
                ):
                    reason = "label_mismatch"
                if not common:
                    reason = reason or "no_paired_scored_days"
                identity = {
                    "dataset_id": cell[0],
                    "city_id": cell[1],
                    "entity_id": cell[2],
                    "budget_days": cell[3],
                    "seed": cell[4],
                    "variant": variant,
                    "reference": reference,
                }
                if reason:
                    blocked.append({**identity, "reason": reason})
                    continue
                method_metric = metric([candidate["days"][day] for day in common])
                reference_metric = metric([ref["days"][day] for day in common])
                paired.append(
                    {
                        **identity,
                        "paired_days": len(common),
                        "method_mae_kwh": method_metric["mae_kwh"],
                        "method_rmse_kwh": method_metric["rmse_kwh"],
                        "reference_mae_kwh": reference_metric["mae_kwh"],
                        "reference_rmse_kwh": reference_metric["rmse_kwh"],
                        "source_using": candidate["source_checkpoint_sha256"] is not None,
                    }
                )
    return paired, blocked


def station_results(pairs: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for pair in pairs:
        grouped[
            (
                pair["dataset_id"],
                pair["city_id"],
                pair["budget_days"],
                pair["variant"],
                pair["reference"],
                pair["entity_id"],
            )
        ].append(pair)
    by_group = defaultdict(list)
    for key, seed_rows in sorted(grouped.items()):
        mae_gains = [row["reference_mae_kwh"] - row["method_mae_kwh"] for row in seed_rows]
        rmse_gains = [row["reference_rmse_kwh"] - row["method_rmse_kwh"] for row in seed_rows]
        by_group[key[:-1]].append(
            {
                "entity_id": key[-1],
                "seeds": len(seed_rows),
                "mae_gain_kwh": statistics.fmean(mae_gains),
                "rmse_gain_kwh": statistics.fmean(rmse_gains),
                "method_mae_kwh": statistics.fmean(row["method_mae_kwh"] for row in seed_rows),
                "reference_mae_kwh": statistics.fmean(
                    row["reference_mae_kwh"] for row in seed_rows
                ),
                "method_rmse_kwh": statistics.fmean(row["method_rmse_kwh"] for row in seed_rows),
                "reference_rmse_kwh": statistics.fmean(
                    row["reference_rmse_kwh"] for row in seed_rows
                ),
                "source_using": all(row["source_using"] for row in seed_rows),
            }
        )
    result = []
    for key, stations in sorted(by_group.items()):
        mae = [station["mae_gain_kwh"] for station in stations]
        rmse = [station["rmse_gain_kwh"] for station in stations]
        reference_mae = statistics.fmean(station["reference_mae_kwh"] for station in stations)
        mae_ci = station_interval(mae)
        rmse_ci = station_interval(rmse)
        transfer = key[-1] == "target_only" and all(station["source_using"] for station in stations)
        adverse = sum(value < 0 for value in mae) if transfer else None
        result.append(
            {
                "dataset_id": key[0],
                "city_id": key[1],
                "budget_days": key[2],
                "variant": key[3],
                "reference": key[4],
                "stations": len(stations),
                "paired_cells": sum(station["seeds"] for station in stations),
                "minimum_seeds_per_station": min(station["seeds"] for station in stations),
                "method_mae_kwh": statistics.fmean(
                    station["method_mae_kwh"] for station in stations
                ),
                "reference_mae_kwh": reference_mae,
                "method_rmse_kwh": statistics.fmean(
                    station["method_rmse_kwh"] for station in stations
                ),
                "reference_rmse_kwh": statistics.fmean(
                    station["reference_rmse_kwh"] for station in stations
                ),
                "mae_gain_kwh": statistics.fmean(mae),
                "mae_ci95_low_kwh": mae_ci[0],
                "mae_ci95_high_kwh": mae_ci[1],
                "rmse_gain_kwh": statistics.fmean(rmse),
                "rmse_ci95_low_kwh": rmse_ci[0],
                "rmse_ci95_high_kwh": rmse_ci[1],
                "transfer_gain": statistics.fmean(mae) / reference_mae
                if transfer and reference_mae > 0
                else None,
                "negative_transfer_stations": adverse,
                "negative_transfer_denominator": len(stations) if transfer else None,
                "negative_transfer_rate": adverse / len(stations) if transfer else None,
            }
        )
    return result


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    assert args.scores.stat().st_size == receipt["output_bytes"]
    scores = pinned_json(args.scores, receipt["output_sha256"])
    jobs = {
        job["job_id"]: job
        for job in pinned_json(
            ROOT / ".cache/hung-final-lock-20261029T014357Z/jobset.json", JOBSET_SHA
        )["jobs"]
    }
    ledger = pinned_json(args.ledger, LEDGER_SHA)
    assert ledger["lock_sha256"] == LOCK_SHA and ledger["archive_sha256"] == ARCHIVE_SHA
    rows = validate_rows(scores, receipt, jobs, ledger)
    paired, blocked = pair_rows(rows)
    groups = station_results(paired)
    output = args.output.resolve()
    assert output.is_relative_to(ROOT.resolve()) and not output.exists()
    output.mkdir(parents=True)
    run_rows = [
        {
            **{
                key: row[key]
                for key in (
                    "job_id",
                    "dataset_id",
                    "city_id",
                    "entity_id",
                    "budget_days",
                    "seed",
                    "variant",
                    "method",
                    "manifest_sha256",
                    "checkpoint_sha256",
                )
            },
            "requested_origins": row["coverage"]["requested"],
            "issued_forecasts": row["coverage"]["created"],
            "scored_days": row["coverage"]["scored"],
            "mae_kwh": None if row["metrics"] is None else row["metrics"]["mae_kwh"],
            "rmse_kwh": None if row["metrics"] is None else row["metrics"]["rmse_kwh"],
            "replay_duration_seconds": row["duration_seconds"],
        }
        for row in rows
    ]
    write_csv(output / "runs.csv", run_rows)
    write_csv(output / "paired.csv", paired)
    write_csv(output / "blocked.csv", blocked)
    write_csv(output / "station_first.csv", groups)
    summary = {
        "schema": "hung-final-aggregate-v1",
        "source_kernel": SOURCE,
        "lock_sha256": LOCK_SHA,
        "scores_sha256": sha256(args.scores),
        "ledger_sha256": LEDGER_SHA,
        "jobs": len(rows),
        "scored_jobs": sum(row["metrics"] is not None for row in rows),
        "null_jobs": sum(row["metrics"] is None for row in rows),
        "requested_origins": sum(row["coverage"]["requested"] for row in rows),
        "issued_forecasts": sum(row["coverage"]["created"] for row in rows),
        "scored_complete_days": sum(row["coverage"]["scored"] for row in rows),
        "paired_cells": len(paired),
        "blocked_cells": len(blocked),
        "station_first_groups": len(groups),
        "replay_duration_seconds_sum": math.fsum(
            row["duration_seconds"] for row in rows if row["duration_seconds"] is not None
        ),
        "replay_duration_rows": sum(row["duration_seconds"] is not None for row in rows),
        "files": {
            name: sha256(output / name)
            for name in ("runs.csv", "paired.csv", "blocked.csv", "station_first.csv")
        },
    }
    with (output / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
