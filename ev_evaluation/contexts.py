"""Outcome-blind Development prefix load-density groups for descriptive analysis."""

from datetime import datetime, timedelta
from statistics import median


def fit_density_context(
    rows: list[dict], namespace: tuple[str, str], budget: int, cutoff: str
) -> dict:
    """Fit a namespace/budget median of nonzero fractions among valid prefix hours."""
    values, undefined = {}, []
    end = datetime.fromisoformat(cutoff)
    for row in rows:
        if row["role"] != "development" or row["status"] != "ready":
            continue
        identity = row["identity"]
        if (
            tuple(identity[:2]) != namespace
            or row["history_days"] != budget
            or datetime.fromisoformat(row["cutoff"]) != end
            or datetime.fromisoformat(row["fit_start"]) != end - timedelta(days=budget)
        ):
            raise ValueError("Changed Development prefix identity or clock")
        entity = identity[2]
        if entity in values or entity in undefined:
            raise ValueError("Duplicate Development entity")
        scale = row["scale"]
        if (
            scale["identity"] != identity
            or scale["start"] != row["fit_start"]
            or scale["cutoff"] != row["cutoff"]
        ):
            raise ValueError("Density metadata is not bound to the allowed prefix")
        valid, zero = scale["valid_count"], scale["zero_count"]
        if type(valid) is not int or type(zero) is not int or not 0 <= zero <= valid <= budget * 24:
            raise ValueError("Invalid prefix hour counts")
        if not valid:
            undefined.append(entity)
            continue
        values[entity] = {"density": (valid - zero) / valid, "valid_hours": valid}
    threshold = median(v["density"] for v in values.values()) if values else None
    for value in values.values():
        value["group"] = "sparse" if value["density"] < threshold else "dense"
    return {
        "namespace": list(namespace),
        "history_days": budget,
        "cutoff": cutoff,
        "threshold": threshold,
        "eligible_development_entities": len(values),
        "undefined_entities": sorted(undefined),
        "sparse_entities": sum(v["group"] == "sparse" for v in values.values()),
        "dense_entities": sum(v["group"] == "dense" for v in values.values()),
        "at_threshold_entities": sum(v["density"] == threshold for v in values.values()),
        "entities": values,
    }
