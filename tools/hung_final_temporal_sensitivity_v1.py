"""Post hoc temporal-block sensitivity for the locked three-station Final gain."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
from datetime import datetime

from tools import hung_final_aggregate_v1 as aggregate

ROOT = aggregate.ROOT
SCORES = (
    ROOT / ".cache/hung-final-metrics-20261029-v2/saved-output-v1-complete/final-run-scores.json"
)
RECEIPT = (
    ROOT
    / ".cache/hung-final-metrics-20261029-v2/saved-output-v1-complete/final-metrics-receipt.json"
)
LEDGER = (
    ROOT
    / ".cache/hung-final-direct-readback-20261029-v1/saved-output-v1-complete/final-job-artifact-ledger.json"
)
JOBSET = ROOT / ".cache/hung-final-lock-20261029T014357Z/jobset.json"
STATION = ROOT / "docs/reports/hung-final-analysis-20261029-v1/station_first.csv"
STATION_SHA = "f01def5b1074cddf2bfda8fba98b9d7f5609dcea9510c3314ffe2645b0535c17"
OUTPUT = ROOT / "docs/reports/evidence/hung-final-temporal-sensitivity-20261030-v1.json"
DRAW_COUNT = 5000
BLOCK_LENGTHS = (7, 14)


def paired_series(rows: list[dict], budget: int) -> dict[str, list[float]]:
    selected = [
        row
        for row in rows
        if row["budget_days"] == budget and row["variant"] in {"main", "target_only"}
    ]
    relevant = {(row["variant"], row["entity_id"], row["seed"]): row for row in selected}
    stations = sorted({entity for _, entity, _ in relevant})
    if len(selected) != len(relevant) or len(relevant) != 18 or len(stations) != 3:
        raise ValueError("Expected exact Main/Target-only 3-station, 3-seed panel")
    result = {}
    for entity in stations:
        dates = list(relevant["main", entity, 7]["days"])
        if len(dates) not in {89, 90}:
            raise ValueError("Unexpected scored-day count")
        parsed_dates = [datetime.fromisoformat(date) for date in dates]
        if any(right <= left for left, right in zip(parsed_dates, parsed_dates[1:])):
            raise ValueError("Scored origins are not chronological")
        values = []
        for date in dates:
            daily = []
            for seed in (7, 11, 19):
                left = relevant["main", entity, seed]["days"]
                right = relevant["target_only", entity, seed]["days"]
                if list(left) != dates or list(right) != dates:
                    raise ValueError("Seed/reference dates do not match")
                if left[date]["label_sha256"] != right[date]["label_sha256"]:
                    raise ValueError("Paired label hash differs")
                daily.append((right[date]["absolute"] - left[date]["absolute"]) / 24)
            values.append(statistics.fmean(daily))
        result[entity] = values
    return result


def block_sample_mean(series: list[float], length: int, rng: random.Random) -> float:
    """Resample circular blocks of ordered scored days to the original count."""
    if not series or length < 1 or length > len(series):
        raise ValueError("Invalid temporal block length")
    indexes = []
    while len(indexes) < len(series):
        start = rng.randrange(len(series))
        indexes.extend((start + offset) % len(series) for offset in range(length))
    return statistics.fmean(series[index] for index in indexes[: len(series)])


def interval(series: dict[str, list[float]], budget: int, length: int) -> dict:
    entities = sorted(series)
    rng_seed = 20261030 + 100 * budget + length
    rng = random.Random(rng_seed)
    draws = []
    for _ in range(DRAW_COUNT):
        sampled = [
            block_sample_mean(series[entities[rng.randrange(3)]], length, rng) for _ in range(3)
        ]
        draws.append(statistics.fmean(sampled))
    return {
        "block_days": length,
        "draws": DRAW_COUNT,
        "rng_seed": rng_seed,
        "ci95_low_kwh": aggregate.percentile(draws, 0.025),
        "ci95_high_kwh": aggregate.percentile(draws, 0.975),
    }


def audit() -> dict:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if SCORES.stat().st_size != receipt["output_bytes"]:
        raise ValueError("Score source byte count differs from receipt")
    scores = aggregate.pinned_json(SCORES, receipt["output_sha256"])
    jobs = {
        row["job_id"]: row for row in aggregate.pinned_json(JOBSET, aggregate.JOBSET_SHA)["jobs"]
    }
    ledger = aggregate.pinned_json(LEDGER, aggregate.LEDGER_SHA)
    if ledger["lock_sha256"] != aggregate.LOCK_SHA:
        raise ValueError("Final lock mismatch")
    rows = aggregate.validate_rows(scores, receipt, jobs, ledger)
    if aggregate.sha256(STATION) != STATION_SHA:
        raise ValueError("Published station-first table changed")
    with STATION.open(newline="", encoding="utf-8") as stream:
        published = {
            int(row["budget_days"]): float(row["mae_gain_kwh"])
            for row in csv.DictReader(stream)
            if row["variant"] == "main" and row["reference"] == "target_only"
        }
    result = []
    for budget in (7, 14, 28):
        series = paired_series(rows, budget)
        point = statistics.fmean(statistics.fmean(days) for days in series.values())
        if not math.isclose(point, published[budget], rel_tol=0, abs_tol=1e-9):
            raise ValueError("Daily paired gain does not reproduce published point estimate")
        result.append(
            {
                "budget_days": budget,
                "stations": len(series),
                "seeds_per_station": 3,
                "scored_days_by_station": {entity: len(days) for entity, days in series.items()},
                "paired_mae_gain_kwh": point,
                "station_mae_gain_kwh": {
                    entity: statistics.fmean(days) for entity, days in series.items()
                },
                "sensitivity_intervals": [
                    interval(series, budget, length) for length in BLOCK_LENGTHS
                ],
            }
        )
    return {
        "schema": "hung-final-temporal-sensitivity-v1",
        "scope": "post hoc two-level station and temporal-block bootstrap; descriptive only",
        "scores_sha256": receipt["output_sha256"],
        "ledger_sha256": aggregate.LEDGER_SHA,
        "lock_sha256": aggregate.LOCK_SHA,
        "station_table_sha256": STATION_SHA,
        "results": result,
    }


def main() -> None:
    result = audit()
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if OUTPUT.exists():
        if OUTPUT.read_bytes() != payload:
            raise ValueError("Existing sensitivity evidence differs")
    else:
        with OUTPUT.open("xb") as stream:
            stream.write(payload)
    print(json.dumps({"sha256": hashlib.sha256(payload).hexdigest(), "budgets": 3}))


if __name__ == "__main__":
    main()
