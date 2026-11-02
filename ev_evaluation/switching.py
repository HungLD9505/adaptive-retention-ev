"""Descriptive recorded switching paths; no harmful-switch or recovery threshold."""

import math
from collections import Counter
from datetime import datetime, timedelta
from statistics import mean

from ev_evaluation.metrics import DailyError


def switch_trajectory(
    report: dict, errors: list[DailyError], issued: tuple[str, ...], *, start: datetime
) -> dict:
    """Keep calendar blocks, missing outcomes and label-drain-only decisions explicit."""
    days, ticks = report["scheduled_days"], report["ticks"]
    controller = report["binding"]["config"]["controller"]
    block = controller["block_days"]
    levels = report["candidate_levels"]
    if (
        type(days) is not int
        or days < 1
        or type(ticks) is not int
        or ticks < days + 1
        or type(block) is not int
        or block < 1
        or len(levels) not in (1, 3)
        or len(set(levels)) != len(levels)
        or any(not math.isfinite(v) or v < 0 for v in levels)
    ):
        raise ValueError(
            "Complete scheduled replay and identified candidate/block profile required"
        )
    stop = start + timedelta(days=days)
    origins = [datetime.fromisoformat(o) for o in issued]
    if len(set(origins)) != len(origins) or any(
        o.utcoffset() != start.utcoffset() or not start <= o < stop for o in origins
    ):
        raise ValueError("Unique issued origins within the declared clock/calendar required")
    scored = {e.origin for e in errors}
    if (
        len(scored) != len(errors)
        or any(e.origin not in origins for e in errors)
        or report["scored_days"] != len(errors)
        or report["issued_days"] != len(origins)
    ):
        raise ValueError("Unique scored origins must belong to actual issued forecasts")
    decisions = report["decisions"]
    if len(decisions) != (ticks - 1) // block:
        raise ValueError("Decision population does not match the complete polling calendar")
    active = controller["initial_lambda"]
    if active not in levels:
        active = levels[0]
    result = []
    for index, decision in enumerate(decisions):
        begin = start + timedelta(days=index * block)
        at = begin + timedelta(days=block)
        selected = decision["selected_lambda"]
        counts = [
            decision[k] for k in ("valid_days", "pending_days", "incomplete_days", "absent_days")
        ]
        used = [datetime.fromisoformat(o) for o in decision["used_origins"]]
        if (
            datetime.fromisoformat(decision["block_start"]) != begin
            or datetime.fromisoformat(decision["effective_from"]) != at
            or decision["active_lambda"] != active
            or selected not in levels
            or any(type(n) is not int or n < 0 for n in counts)
            or sum(counts) != block
            or len(set(used)) != len(used)
            or len(used) != counts[0]
            or any(not begin <= o < at or o not in scored for o in used)
        ):
            raise ValueError("Broken switching continuity, calendar or paired-day accounting")
        end = min(at + timedelta(days=block), stop)
        post = [e for e in errors if at <= e.origin < end]
        post_issued = sum(at <= o < end for o in origins)
        result.append(
            {
                "effective_from": decision["effective_from"],
                "active_lambda": active,
                "selected_lambda": selected,
                "switched": selected != active,
                "reason": decision["reason"],
                "effective_in_forecast_calendar": at < stop,
                "valid_days": counts[0],
                "pending_days": counts[1],
                "incomplete_days": counts[2],
                "absent_days": counts[3],
                "valid_day_gaps": decision["valid_day_gaps"],
                "post_block_stop": max(at, end).isoformat(),
                "post_scheduled_days": max(0, (end - at).days),
                "post_issued_days": post_issued,
                "post_scored_days": len(post),
                "post_mae_kwh": mean(e.mae for e in post) if post else None,
                "post_rmse_kwh": math.sqrt(mean(e.mse for e in post)) if post else None,
            }
        )
        active = selected
    effective = [d for d in result if d["effective_in_forecast_calendar"]]
    multiple = len(levels) == 3
    switches = sum(d["switched"] for d in effective)
    insufficient = sum(d["reason"].startswith("insufficient_") for d in effective)
    return {
        "boundaries_recorded": len(result),
        "decision_opportunities": len(effective) if multiple else 0,
        "switches": switches,
        "switches_per_opportunity": switches / len(effective) if multiple and effective else None,
        "insufficient_evidence_boundaries": insufficient,
        "insufficient_fraction": insufficient / len(effective) if multiple and effective else None,
        "reason_counts": dict(sorted(Counter(d["reason"] for d in effective).items())),
        "drain_only_boundaries": len(result) - len(effective),
        "drain_only_switches": sum(
            d["switched"] for d in result if not d["effective_in_forecast_calendar"]
        ),
        "decisions": result,
        "scope": "Recorded descriptive paths and actual deployed errors in the next calendar block; gaps remain missing. Single-policy switch rate is undefined. No causal effect, harm classification, recovery time or confidence-coverage claim.",
    }


def analyze_switch_cells(cells: dict, seeds: list[int], *, start: datetime) -> dict:
    """Keep all paired seeds/sites, including unscored and fixed-policy trajectories."""
    groups = {}
    for (budget, entity, seed, method), cell in cells.items():
        by_seed = groups.setdefault((budget, method), {}).setdefault(entity, {})
        if seed not in seeds or seed in by_seed:
            raise ValueError("Duplicate or undeclared switching seed")
        by_seed[seed] = switch_trajectory(
            cell["report"], cell["errors"], cell["issued"], start=start
        )
    output = {}
    for (budget, method), stations in groups.items():
        summaries = {}
        for entity, rows in stations.items():
            if set(rows) != set(seeds):
                raise ValueError("All paired switching seeds required; do not drop null sites")
            summaries[entity] = {
                "seeds": rows,
                "mean_switches": mean(r["switches"] for r in rows.values()),
                "seed_switch_count_range": [
                    min(r["switches"] for r in rows.values()),
                    max(r["switches"] for r in rows.values()),
                ],
                "mean_switches_per_opportunity": mean(
                    r["switches_per_opportunity"] for r in rows.values()
                )
                if all(r["switches_per_opportunity"] is not None for r in rows.values())
                else None,
                "mean_insufficient_fraction": mean(
                    r["insufficient_fraction"] for r in rows.values()
                )
                if all(r["insufficient_fraction"] is not None for r in rows.values())
                else None,
            }
        output[f"{budget}/{method}"] = {
            "stations": summaries,
            "station_count": len(summaries),
            "seeds": seeds,
            "mean_station_switches": mean(s["mean_switches"] for s in summaries.values()),
            "mean_station_switches_per_opportunity": mean(
                s["mean_switches_per_opportunity"] for s in summaries.values()
            )
            if all(s["mean_switches_per_opportunity"] is not None for s in summaries.values())
            else None,
            "mean_station_insufficient_fraction": mean(
                s["mean_insufficient_fraction"] for s in summaries.values()
            )
            if all(s["mean_insufficient_fraction"] is not None for s in summaries.values())
            else None,
        }
    return output
