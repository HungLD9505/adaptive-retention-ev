"""Retrospective proxy associations with same-block paired candidate performance."""

import math
from datetime import datetime
from statistics import mean

PROXIES = ("source_error", "uncertainty", "drift")


def correlation(pairs: list[tuple[float, float]]) -> float | None:
    """Descriptive Pearson r; constant/short populations have no defined correlation."""
    if any(not math.isfinite(v) for pair in pairs for v in pair):
        raise ValueError("Finite paired signals and benefits required")
    if len(pairs) < 2:
        return None
    x, y = zip(*pairs, strict=True)
    a, b = mean(x), mean(y)
    xx = sum((v - a) ** 2 for v in x)
    yy = sum((v - b) ** 2 for v in y)
    if not xx or not yy:
        return None
    return sum((v - a) * (w - b) for v, w in pairs) / math.sqrt(xx * yy)


def proxy_blocks(
    report: dict, trace: dict, frozen_errors: dict[str, float], scale: float | None
) -> list[dict]:
    """Pair the policy's available block signal with zero-minus-low/high candidate MAE."""
    name, levels = report["method"]["name"], report["candidate_levels"]
    if name not in PROXIES or len(levels) != 3 or levels[0] != 0 or not 0 < levels[1] < levels[2]:
        raise ValueError("Identified three-level proxy trajectory required")
    if scale is None and (trace["forecasts"] or trace["scores"]):
        raise ValueError("Issued/scored proxy trajectory cannot have an undefined scale")
    if scale is not None and (not math.isfinite(scale) or scale <= 0):
        raise ValueError("Positive fixed target scale required")
    scores = {e["origin"]: e for e in trace["scores"]}
    signals = {e["origin"]: e for e in report["policy_state"]["signals"]}
    if len(scores) != len(trace["scores"]) or len(signals) != len(
        report["policy_state"]["signals"]
    ):
        raise ValueError("Duplicate score/signal origins")
    for origin, signal in signals.items():
        value = signal["value"]
        if not math.isfinite(value) or value < 0 or origin not in trace["forecasts"]:
            raise ValueError("Invalid or unissued proxy signal")
        if name == "source_error":
            if origin not in scores or origin not in frozen_errors:
                raise ValueError("Source error requires the paired verified Frozen Source score")
            expected, available = frozen_errors[origin] / scale, scores[origin]["as_of"]
        else:
            expected, available = trace["forecasts"][origin]["signal"], origin
        if (
            not math.isclose(value, expected, rel_tol=1e-9, abs_tol=1e-10)
            or signal["available_at"] != available
        ):
            raise ValueError(
                "Recorded proxy disagrees with authenticated forecast/score availability"
            )
    output = []
    for decision in report["decisions"]:
        start, end = (
            datetime.fromisoformat(decision[k]) for k in ("block_start", "effective_from")
        )
        origins = decision["used_origins"]
        if len(set(origins)) != len(origins) or len(origins) != decision["valid_days"]:
            raise ValueError("Changed paired decision population")
        for origin in origins:
            if (
                origin not in scores
                or not start <= datetime.fromisoformat(origin) < end
                or datetime.fromisoformat(scores[origin]["as_of"]) > end
                or len(scores[origin]["mae_scaled"]) != 3
            ):
                raise ValueError("Decision uses an unpaired/out-of-block/unavailable score")
        available = [
            signals[o]["value"]
            for o in origins
            if o in signals and datetime.fromisoformat(signals[o]["available_at"]) <= end
        ]
        statistics = decision["config"]["method_statistics"]
        signal_mean = statistics.get("mean_available_signal")
        if (signal_mean is None) != (len(available) < decision["config"]["min_valid_days"]):
            raise ValueError("Missing/unexpected policy block signal")
        if signal_mean is not None and (
            len(available) < decision["config"]["min_valid_days"]
            or len(available) != statistics["signal_days"]
            or not math.isclose(signal_mean, mean(available), rel_tol=1e-9, abs_tol=1e-10)
        ):
            raise ValueError("Recorded block signal contradicts available paired signals")
        output.append(
            {
                "block_start": decision["block_start"],
                "effective_from": decision["effective_from"],
                "reason": decision["reason"],
                "policy_signal_mean": signal_mean,
                "available_signal_days": len(available),
                "paired_days": len(origins),
                "zero_minus_low_mae_kwh": mean(
                    scores[o]["mae_scaled"][0] - scores[o]["mae_scaled"][1] for o in origins
                )
                * scale
                if origins
                else None,
                "zero_minus_high_mae_kwh": mean(
                    scores[o]["mae_scaled"][0] - scores[o]["mae_scaled"][2] for o in origins
                )
                * scale
                if origins
                else None,
            }
        )
    return output


def summarize_relationships(units: list[dict], seeds: list[int]) -> dict:
    """Average descriptive within-run r across all paired seeds, then equally by station."""
    if len(seeds) < 3 or len(set(seeds)) != len(seeds):
        raise ValueError("At least three declared paired seeds required")
    grouped = {}
    for unit in units:
        key = unit["budget"], unit["method"], unit["entity_id"]
        by_seed = grouped.setdefault(key, {})
        if unit["seed"] in by_seed or unit["seed"] not in seeds:
            raise ValueError("Duplicate/undeclared proxy seed")
        pairs = [b for b in unit["blocks"] if b["policy_signal_mean"] is not None]
        by_seed[unit["seed"]] = {
            "blocks": len(unit["blocks"]),
            "paired_policy_blocks": len(pairs),
            **{
                label: correlation([(b["policy_signal_mean"], b[label]) for b in pairs])
                for label in ("zero_minus_low_mae_kwh", "zero_minus_high_mae_kwh")
            },
        }
    output = {}
    for (budget, method, entity), values in grouped.items():
        if set(values) != set(seeds):
            raise ValueError("Missing paired proxy seed; do not silently average")
        target = output.setdefault(f"{budget}/{method}", {"stations": {}})
        target["stations"][entity] = {
            "seeds": values,
            **{
                label: mean(v[label] for v in values.values())
                if all(v[label] is not None for v in values.values())
                else None
                for label in ("zero_minus_low_mae_kwh", "zero_minus_high_mae_kwh")
            },
        }
    for value in output.values():
        for label in ("zero_minus_low_mae_kwh", "zero_minus_high_mae_kwh"):
            defined = [s[label] for s in value["stations"].values() if s[label] is not None]
            value[label] = {
                "mean_station_r": mean(defined) if defined else None,
                "defined_stations": len(defined),
                "undefined_stations": len(value["stations"]) - len(defined),
            }
    return output


def analyze_proxy_cells(cells: dict, seeds: list[int]) -> dict:
    """Join each selected proxy with its paired Frozen Source in a verified collection."""
    units = []
    for key, cell in cells.items():
        if key[-1] not in PROXIES:
            continue
        frozen = cells[(*key[:3], "frozen_source")]["errors"]
        units.append(
            {
                "budget": key[0],
                "entity_id": key[1],
                "seed": key[2],
                "method": key[3],
                "blocks": proxy_blocks(
                    cell["report"],
                    cell["coverage"]["proxy_trace"],
                    {e.origin.isoformat(): e.mae for e in frozen},
                    cell["coverage"]["scale"],
                ),
            }
        )
    return {
        "definition": "Same-block available policy signal versus paired zero-minus-low/high candidate MAE (kWh); positive benefit favors retention. Source-error signals cross-checked against verified Frozen Source errors; uncertainty/drift against saved forecast signals. Descriptive Pearson r, no p-values, causal effect or next-block predictive skill claim. Correlations require all three seeds defined before station averaging; unavailable/constant cases stay null.",
        "station_first": summarize_relationships(units, seeds),
        "units": units,
    }
