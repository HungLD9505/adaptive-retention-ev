"""Summarize supplementary CHARGED Development proofs without selecting a model.

The input is the six proof JSON files from PR #67. This reads saved summary
metrics only; it does not independently restore daily forecasts or remote bytes.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from pathlib import Path

CITIES = ("MEL", "SZH", "AMS", "JHB", "SPO", "LOA")
BUDGETS = (7, 14, 28)
SEEDS = (42, 43, 44)
METHODS = frozenset(
    {
        "adaptive",
        "block28",
        "block7",
        "drift",
        "fixed_retention",
        "frozen_source",
        "full_finetuning",
        "online_best",
        "parameter_retention",
        "seasonal_naive",
        "source_error",
        "target_only",
        "uncertainty",
        "without_source_initialization",
    }
)


def summarize_city(city: str, proof: dict) -> list[dict]:
    """Return station-first descriptive Adaptive versus Target-only comparisons."""
    if city not in CITIES or proof.get("status") != "verified":
        raise ValueError(f"Unexpected city or proof status: {city}")
    rows = proof.get("runs")
    if not isinstance(rows, list) or len(rows) != 378:
        raise ValueError(f"Expected 378 proof rows for {city}")
    pattern = re.compile(rf"^charged-{city}-(.+?)-(7|14|28)d-(.+)-seed(42|43|44)$")
    units: dict[tuple[int, str, int], dict[str, dict]] = {}
    seen_ids: set[str] = set()
    for row in rows:
        run_id = row["run_id"]
        match = pattern.fullmatch(run_id)
        if match is None or run_id in seen_ids:
            raise ValueError(f"Invalid or duplicate run ID: {run_id}")
        seen_ids.add(run_id)
        entity, budget_text, method, seed_text = match.groups()
        if method not in METHODS or not entity:
            raise ValueError(f"Unexpected method or entity: {run_id}")
        if row["issued"] != 90 or row["scored"] != 90:
            raise ValueError(f"Incomplete issued/scored coverage: {run_id}")
        for metric in ("mae_kwh", "rmse_kwh"):
            value = row[metric]
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid {metric}: {run_id}")
        units.setdefault((int(budget_text), entity, int(seed_text)), {})[method] = row
    if len(units) != 27:
        raise ValueError(f"Expected 27 entity-budget-seed units for {city}")
    for key, methods in units.items():
        if methods.keys() != METHODS:
            raise ValueError(f"Missing method in {city} unit {key}")
        origins = {row["scored_origins_sha256"] for row in methods.values()}
        if len(origins) != 1:
            raise ValueError(f"Unpaired scored origins in {city} unit {key}")

    result = []
    for budget in BUDGETS:
        entities = sorted({entity for day, entity, _ in units if day == budget})
        if len(entities) != 3:
            raise ValueError(f"Expected three entities for {city} {budget}d")
        gains = []
        for entity in entities:
            if any((budget, entity, seed) not in units for seed in SEEDS):
                raise ValueError(f"Missing comparison seed for {city} {budget}d {entity}")
            gains.append(
                statistics.fmean(
                    units[(budget, entity, seed)]["target_only"]["mae_kwh"]
                    - units[(budget, entity, seed)]["adaptive"]["mae_kwh"]
                    for seed in SEEDS
                )
            )
        result.append(
            {
                "city": city,
                "budget_days": budget,
                "stations": len(entities),
                "seeds_per_station": len(SEEDS),
                "mean_mae_gain_kwh": statistics.fmean(gains),
                "worse_station_count": sum(gain < 0 for gain in gains),
                "worse_station_fraction": sum(gain < 0 for gain in gains) / len(gains),
                "scope": "supplementary_development_summary_only",
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof-dir", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for city in CITIES:
        path = args.proof_dir / f"issue23-charged-{city.lower()}-development-verification-v2.json"
        proof = json.loads(path.read_text(encoding="utf-8"))
        results.extend(summarize_city(city, proof))
    print(json.dumps(results, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
