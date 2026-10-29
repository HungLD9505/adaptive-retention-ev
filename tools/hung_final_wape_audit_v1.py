"""Validate Kaggle Final WAPE numerators/denominators and summarize locked jobs.

This CPU-only tool consumes the small saved Kaggle outputs; it never reads or
downloads the multi-gigabyte Final archive. Output directories are create-only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    """Fail closed even when Python assertions are disabled."""
    if not condition:
        raise ValueError(message)


def audit(
    scores_path: Path, wape_path: Path, receipt_path: Path, ledger_path: Path
) -> tuple[list[dict], list[dict], dict]:
    """Return independently checked job and station-first WAPE rows."""
    scores = _load(scores_path)
    wape = _load(wape_path)
    receipt = _load(receipt_path)
    ledger = _load(ledger_path)
    raw_wape = wape_path.read_bytes()
    require(len(raw_wape) == receipt["output_bytes"], "WAPE output byte count differs")
    require(
        hashlib.sha256(raw_wape).hexdigest() == receipt["output_sha256"],
        "WAPE output SHA differs",
    )
    require(
        receipt["status"] == "FINAL_WAPE_DENOMINATORS_READ_FROM_CHECKPOINTS",
        "WAPE receipt is not terminal",
    )
    require(receipt["undefined_jobs"] == 0, "WAPE has undefined denominators")
    for field in ("archive_sha256", "lock_sha256", "source_kernel"):
        require(
            scores[field] == wape[field] == receipt[field] == ledger[field],
            f"WAPE source identity differs: {field}",
        )

    score_by_id = {row["job_id"]: row for row in scores["jobs"]}
    wape_by_id = {row["job_id"]: row for row in wape["jobs"]}
    require(
        len(scores["jobs"])
        == len(wape["jobs"])
        == len(score_by_id)
        == len(wape_by_id)
        == len(ledger["jobs"])
        == receipt["jobs"]
        == 360,
        "Final WAPE job count or uniqueness differs",
    )
    require(set(score_by_id) == set(wape_by_id) == set(ledger["jobs"]), "Final job IDs differ")
    run_rows: list[dict] = []
    station_seeds: dict[tuple, list[float]] = defaultdict(list)
    for job_id in sorted(score_by_id):
        score, row = score_by_id[job_id], wape_by_id[job_id]
        days = score["days"]
        require(
            row["scored_days"] == score["coverage"]["scored"] == len(days),
            f"Scored-day count differs: {job_id}",
        )
        require(
            row["label_total_kwh"] > 0 and math.isfinite(row["label_total_kwh"]),
            f"WAPE denominator invalid: {job_id}",
        )
        require(
            row["absolute_error_kwh"] >= 0
            and math.isfinite(row["absolute_error_kwh"])
            and all(
                math.isfinite(day["absolute"]) and day["absolute"] >= 0 for day in days.values()
            )
            and math.isclose(
                row["absolute_error_kwh"],
                sum(day["absolute"] for day in days.values()),
                rel_tol=1e-9,
                abs_tol=1e-6,
            ),
            f"WAPE numerator differs: {job_id}",
        )
        require(
            row["wape"] is not None
            and math.isfinite(row["wape"])
            and math.isclose(
                row["wape"], row["absolute_error_kwh"] / row["label_total_kwh"], rel_tol=1e-12
            ),
            f"WAPE ratio differs: {job_id}",
        )
        require(
            math.isfinite(score["metrics"]["mae_kwh"])
            and math.isclose(
                row["absolute_error_kwh"],
                score["metrics"]["mae_kwh"] * 24 * len(days),
                rel_tol=1e-9,
                abs_tol=1e-6,
            ),
            f"WAPE/MAE identity differs: {job_id}",
        )
        run_rows.append(
            {
                "job_id": job_id,
                "dataset_id": score["dataset_id"],
                "city_id": score["city_id"],
                "entity_id": score["entity_id"],
                "budget_days": score["budget_days"],
                "seed": score["seed"],
                "variant": score["variant"],
                "scored_days": row["scored_days"],
                "absolute_error_kwh": row["absolute_error_kwh"],
                "label_total_kwh": row["label_total_kwh"],
                "wape": row["wape"],
            }
        )
        station_seeds[
            (
                score["dataset_id"],
                score["city_id"],
                score["entity_id"],
                score["budget_days"],
                score["variant"],
            )
        ].append(row["wape"])

    station_rows = [
        {
            "dataset_id": dataset,
            "city_id": city,
            "entity_id": entity,
            "budget_days": budget,
            "variant": variant,
            "physical_seeds": len(values),
            "seed_mean_wape": sum(values) / len(values),
        }
        for (dataset, city, entity, budget, variant), values in sorted(station_seeds.items())
    ]
    grouped: dict[tuple, list[float]] = defaultdict(list)
    for row in station_rows:
        grouped[(row["budget_days"], row["variant"])].append(row["seed_mean_wape"])
    summary = {
        "schema": "hung-final-wape-audit-v1",
        "lock_sha256": receipt["lock_sha256"],
        "archive_sha256": receipt["archive_sha256"],
        "source_output_sha256": receipt["output_sha256"],
        "jobs": len(run_rows),
        "undefined_jobs": 0,
        "station_first": [
            {
                "budget_days": budget,
                "variant": variant,
                "stations": len(values),
                "equal_station_wape": sum(values) / len(values),
            }
            for (budget, variant), values in sorted(grouped.items())
        ],
    }
    return run_rows, station_rows, summary


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("scores", "wape", "receipt", "ledger", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    run_rows, station_rows, summary = audit(args.scores, args.wape, args.receipt, args.ledger)
    args.output.mkdir(parents=True, exist_ok=False)
    _write_csv(args.output / "wape_runs.csv", run_rows)
    _write_csv(args.output / "wape_stations.csv", station_rows)
    (args.output / "wape_summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps({"jobs": summary["jobs"], "station_first_groups": len(summary["station_first"])})
    )


if __name__ == "__main__":
    main()
