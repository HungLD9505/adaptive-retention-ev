"""Finite Development selection with explicit pairing, missingness and weighting."""

import math
import re


def score_candidates(
    rows: list[dict],
    cohort: dict,
    choices: list[int | float],
    *,
    choice_field: str,
    method_name: str,
) -> dict:
    """Average seeds within stations, stations within budgets, then budgets equally."""
    expected = {
        (candidate, int(budget), item["entity_id"], seed)
        for candidate in choices
        for budget, group in cohort["budgets"].items()
        for item in group["entities"]
        for seed in cohort["seeds"]
    }
    strict_origins = any(
        row.get("binding", {}).get("schema") == "ev-prequential-run-v1" for row in rows
    )
    cells = {}
    for row in rows:
        binding = row["binding"]["input"]
        seed = row["binding"]["config"]["initial_training"]["seed"]
        key = (row[choice_field], binding["history_days"], binding["entity_id"], seed)
        if key not in expected or key in cells:
            raise ValueError("Extra/duplicate study cell")
        if row["method"]["name"] != method_name:
            raise ValueError("Wrong study comparator")
        if strict_origins and (
            row["binding"].get("schema") != "ev-prequential-run-v1"
            or any(
                not isinstance(row.get(name), str)
                or re.fullmatch(r"[0-9a-f]{64}", row[name]) is None
                for name in ("issued_origins_sha256", "scored_origins_sha256")
            )
            or not isinstance(binding.get("input_manifest_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", binding["input_manifest_sha256"]) is None
        ):
            raise ValueError("Full study row lacks authenticated origin identities")
        if (row["active_mae_kwh"] is None) != (row["scored_days"] == 0):
            raise ValueError("Score availability contradicts scored-day count")
        cells[key] = row
    if set(cells) != expected:
        raise ValueError("All study cells required, including null scores")
    coverage = {}
    for (_, budget, entity, seed), row in cells.items():
        unit = (budget, entity, seed)
        signature = (row["issued_days"], row["scored_days"])
        if strict_origins:
            signature += (
                row["binding"]["input"]["input_manifest_sha256"],
                row["issued_origins_sha256"],
                row["scored_origins_sha256"],
            )
        if unit in coverage and coverage[unit] != signature:
            raise ValueError("Candidate forecast/score origin coverage differs")
        coverage[unit] = signature
    values = {}
    for candidate in choices:
        budgets = {}
        for budget, group in cohort["budgets"].items():
            stations = {}
            unscored = []
            for item in group["entities"]:
                entity = item["entity_id"]
                scores = [
                    cells[candidate, int(budget), entity, seed]["active_mae_kwh"]
                    for seed in cohort["seeds"]
                ]
                if any(v is None for v in scores):
                    if not all(v is None for v in scores):
                        raise ValueError("Mixed seed score availability")
                    unscored.append(entity)
                else:
                    if any(
                        isinstance(v, bool)
                        or not isinstance(v, (int, float))
                        or not math.isfinite(v)
                        or v < 0
                        for v in scores
                    ):
                        raise ValueError("Invalid score")
                    stations[entity] = sum(scores) / len(scores)
            budgets[budget] = {
                "station_mae_kwh": stations,
                "unscored_entities": unscored,
                "mae_kwh": sum(stations.values()) / len(stations) if stations else None,
            }
        available = [b["mae_kwh"] for b in budgets.values()]
        values[str(candidate)] = {
            "budgets": budgets,
            "selection_score": sum(available) / len(available)
            if all(v is not None for v in available)
            else None,
        }
    ranked = [e for e in choices if values[str(e)]["selection_score"] is not None]
    choice = min(ranked, key=lambda e: (values[str(e)]["selection_score"], e)) if ranked else None
    return {"candidates": values, "provisional_choice": choice}
