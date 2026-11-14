"""Paired exploratory intervals for entity means and common-calendar sensitivity."""

import math

import numpy as np


def paired_mean_interval(
    reference: np.ndarray,
    candidate: np.ndarray,
    *,
    resamples: int,
    seed: int,
    segment_days: int | None = None,
    alpha: float = 0.05,
) -> dict:
    """Average complete daily errors within entity, then entities equally.

    Inputs are seed-averaged daily MAEs [entity, scheduled calendar day]. NaN marks
    a missing scored day in BOTH arms. Seeds must already be paired/averaged by
    the caller; they are never resampled as independent entities. With segments,
    the SAME circular calendar draws are used by all sampled entities and arms.
    An undefined resample invalidates the interval, rather than being discarded.
    These posthoc percentile intervals are conditional on the recorded models.
    """
    a, b = np.asarray(reference, dtype=float), np.asarray(candidate, dtype=float)
    if (
        a.ndim != 2
        or a.shape != b.shape
        or not a.size
        or not np.array_equal(np.isnan(a), np.isnan(b))
        or np.isinf(a).any()
        or np.isinf(b).any()
        or np.any(a < 0)
        or np.any(b < 0)
        or np.any(np.isnan(a).all(axis=1))
        or type(resamples) is not int
        or resamples < 2
        or type(seed) is not int
        or seed < 0
        or not math.isfinite(alpha)
        or not 0 < alpha < 1
        or (
            segment_days is not None
            and (type(segment_days) is not int or not 1 <= segment_days <= a.shape[1])
        )
    ):
        raise ValueError(
            "Paired finite nonnegative errors, nonempty entities and valid profile required"
        )
    entity_a, entity_b = np.nanmean(a, axis=1), np.nanmean(b, axis=1)
    point_a, point_b = float(entity_a.mean()), float(entity_b.mean())
    rng = np.random.default_rng(seed)
    gaps, reductions = [], []
    undefined = undefined_reduction = 0
    count, days = a.shape
    # Bound temporary [resample, entity, calendar] memory for real cohorts.
    for offset in range(0, resamples, 128):
        size = min(128, resamples - offset)
        entities = rng.integers(count, size=(size, count))
        if segment_days is None:
            aa, bb = entity_a[entities].mean(1), entity_b[entities].mean(1)
            valid = np.ones(size, dtype=bool)
        else:
            starts = rng.integers(days, size=(size, math.ceil(days / segment_days)))
            indices = ((starts[..., None] + np.arange(segment_days)) % days).reshape(size, -1)
            indices = indices[:, :days]
            sampled_a = a[entities[:, :, None], indices[:, None, :]]
            sampled_b = b[entities[:, :, None], indices[:, None, :]]
            observed = np.isfinite(sampled_a)
            totals = observed.sum(2)
            valid = (totals > 0).all(1)
            # Denominator clamp affects invalid replicates only, which are counted.
            aa = (np.nansum(sampled_a, axis=2) / np.maximum(totals, 1)).mean(1)
            bb = (np.nansum(sampled_b, axis=2) / np.maximum(totals, 1)).mean(1)
        undefined += int((~valid).sum())
        gaps.extend((bb[valid] - aa[valid]).tolist())
        positive = valid & (aa > 0)
        undefined_reduction += int((valid & ~positive).sum())
        reductions.extend((100 * (aa[positive] - bb[positive]) / aa[positive]).tolist())
    probabilities = [alpha / 2, 1 - alpha / 2]
    return {
        "reference_mae_kwh": point_a,
        "candidate_mae_kwh": point_b,
        "gap_kwh": point_b - point_a,
        "reduction_percent": 100 * (point_a - point_b) / point_a if point_a > 0 else None,
        "gap_interval_kwh": None if undefined else np.quantile(gaps, probabilities).tolist(),
        "reduction_interval_percent": None
        if undefined or undefined_reduction
        else np.quantile(reductions, probabilities).tolist(),
        "undefined_replicates": undefined,
        "undefined_percentage_replicates": undefined_reduction,
        "entity_count": count,
        "scheduled_days": days,
        "entity_lower": int((entity_b < entity_a).sum()),
        "entity_equal": int((entity_b == entity_a).sum()),
        "entity_higher": int((entity_b > entity_a).sum()),
        "resamples": resamples,
        "seed": seed,
        "alpha": alpha,
        "segment_days": segment_days,
        "profile": "paired-entity"
        if segment_days is None
        else "paired-entity-shared-circular-calendar",
        "limits": "Posthoc, selected cohort, fixed paired seeds/models; marginal intervals, no multiplicity correction or independent-test guarantee",
    }
