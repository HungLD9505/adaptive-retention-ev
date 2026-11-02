"""Summarize station clustering in the authenticated Development switch audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/reports/hung-block7-switch-effect-20261030-v1/switches.csv"
SOURCE_SHA256 = "0b863d2fce6d6f95b701ffd24a40999061d3158c405a482fe077b3dca9f0527b"
RUN_ID = re.compile(r"^(main|block7)_b(7|14|28)s(7|11|19)e([0-9]+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize(rows: list[dict[str, str]]) -> dict:
    """Keep switch, run, station and budget denominators distinct."""
    if len(rows) != 87:
        raise ValueError("Expected the complete 87-switch source")
    seen: set[tuple[str, str, str]] = set()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        match = RUN_ID.fullmatch(row["run_id"])
        if match is None:
            raise ValueError("Unrecognized switch run ID")
        role = "main" if match[1] == "main" else "historical"
        if row["role"] != role:
            raise ValueError("Run ID and role disagree")
        key = (role, row["run_id"], row["decision_index"])
        if key in seen:
            raise ValueError("Duplicate switch decision")
        seen.add(key)
        days = int(row["paired_scored_days"])
        if row["status"] == "PAIRED_SCORED_DAYS":
            live = float(row["mean_live_mae_kwh"])
            audit = float(row["mean_old_policy_audit_mae_kwh"])
            difference = float(row["live_minus_audit_mae_kwh"])
            delta = float(row["delta_kwh"])
            if (
                days <= 0
                or not all(math.isfinite(value) for value in (live, audit, difference, delta))
                or abs((live - audit) - difference) > 1e-9
                or row["audit_better_beyond_delta"] != str(difference > delta)
            ):
                raise ValueError("Inconsistent paired switch score")
            grouped[role].append(
                {
                    "station": match[4],
                    "budget_days": int(match[2]),
                    "run_id": row["run_id"],
                    "difference_kwh": difference,
                    "audit_better": difference > delta,
                    "paired_days": days,
                }
            )
        elif row["status"] == "NO_PAIRED_SCORED_DAY":
            if days != 0 or row["live_minus_audit_mae_kwh"] or row["audit_better_beyond_delta"]:
                raise ValueError("Unscored switch has a score")
        else:
            raise ValueError("Unexpected switch status")
    if len(grouped["main"]) != 28 or len(grouped["historical"]) != 55:
        raise ValueError("Paired switch inventory differs from source receipt")

    main = grouped["main"]
    stations = sorted({item["station"] for item in main})
    by_station = {}
    for station in stations:
        subset = [item for item in main if item["station"] == station]
        by_station[station] = {
            "evaluable_switches": len(subset),
            "audit_better_switches": sum(item["audit_better"] for item in subset),
            "mean_live_minus_audit_kwh": statistics.fmean(
                item["difference_kwh"] for item in subset
            ),
            "run_count": len({item["run_id"] for item in subset}),
        }
    by_budget = {}
    for budget in (7, 14, 28):
        subset = [item for item in main if item["budget_days"] == budget]
        by_budget[str(budget)] = {
            "evaluable_switches": len(subset),
            "audit_better_switches": sum(item["audit_better"] for item in subset),
            "station_count": len({item["station"] for item in subset}),
        }
    leave_one_out = {}
    for station in stations:
        subset = [item for item in main if item["station"] != station]
        leave_one_out[station] = {
            "evaluable_switches": len(subset),
            "audit_better_switches": sum(item["audit_better"] for item in subset),
            "mean_live_minus_audit_kwh": statistics.fmean(
                item["difference_kwh"] for item in subset
            ),
        }
    return {
        "schema": "hung-block7-switch-sensitivity-v1",
        "source_sha256": SOURCE_SHA256,
        "main": {
            "evaluable_switches": len(main),
            "audit_better_switches": sum(item["audit_better"] for item in main),
            "paired_scored_days": sum(item["paired_days"] for item in main),
            "run_count": len({item["run_id"] for item in main}),
            "station_count": len(stations),
            "switch_weighted_mean_live_minus_audit_kwh": statistics.fmean(
                item["difference_kwh"] for item in main
            ),
            "station_equal_mean_live_minus_audit_kwh": statistics.fmean(
                item["mean_live_minus_audit_kwh"] for item in by_station.values()
            ),
            "by_station": by_station,
            "by_budget": by_budget,
            "leave_one_station_out": leave_one_out,
        },
        "historical": {
            "evaluable_switches": len(grouped["historical"]),
            "audit_better_switches": sum(item["audit_better"] for item in grouped["historical"]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha256(SOURCE) != SOURCE_SHA256:
        raise ValueError("Source switch CSV SHA mismatch")
    with SOURCE.open("r", encoding="utf-8", newline="") as stream:
        summary = summarize(list(csv.DictReader(stream)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary["main"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
