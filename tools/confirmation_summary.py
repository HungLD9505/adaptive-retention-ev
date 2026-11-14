"""Locked equal-namespace confirmation contrasts and paired calendar uncertainty."""

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from ev_models.checkpoint import digest
from tools.fusion_evidence import write_csv


def stratified_contrasts(
    data: dict, *, resamples: int, seed: int, segment_days: int, alpha: float
) -> dict:
    """Equal namespace percentage gains; paired entities, seeds already averaged.

    Reference/candidate arrays share [entity, 90 scheduled dates] masks. Draw
    entities within namespace and common circular calendar blocks within each
    namespace. Both comparisons use the same draws. No invalid draw is discarded.
    """
    if not data or resamples < 2 or segment_days < 1 or not 0 < alpha < 1:
        raise ValueError("Nonempty stratified data and valid declared profile required")
    rng = np.random.default_rng(seed)
    points = {name: [] for name in ("fixed", "static")}
    estimates = {name: np.zeros(resamples) for name in points}
    valid = {name: np.ones(resamples, dtype=bool) for name in points}
    for namespace in sorted(data):
        arrays = {name: np.asarray(value, dtype=float) for name, value in data[namespace].items()}
        base = arrays["adaptive"]
        if base.ndim != 2 or not base.size or np.any(np.isnan(base).all(1)):
            raise ValueError("Every scored entity needs nonempty paired daily errors")
        if any(
            value.shape != base.shape
            or not np.array_equal(np.isnan(value), np.isnan(base))
            or np.isinf(value).any()
            or np.any(value < 0)
            for value in arrays.values()
        ):
            raise ValueError("Method masks or error domains differ")
        for name in points:
            a, b = (
                float(np.nanmean(arrays[name], axis=1).mean()),
                float(np.nanmean(base, axis=1).mean()),
            )
            points[name].append(100 * (a - b) / a if a > 0 else None)
        count, days = base.shape
        for offset in range(0, resamples, 128):
            size = min(128, resamples - offset)
            entities = rng.integers(count, size=(size, count))
            starts = rng.integers(days, size=(size, int(np.ceil(days / segment_days))))
            indices = ((starts[..., None] + np.arange(segment_days)) % days).reshape(size, -1)[
                :, :days
            ]
            sample = {
                name: value[entities[:, :, None], indices[:, None, :]]
                for name, value in arrays.items()
            }
            totals = np.isfinite(sample["adaptive"]).sum(2)
            good = (totals > 0).all(1)
            mean = {
                name: (np.nansum(value, axis=2) / np.maximum(totals, 1)).mean(1)
                for name, value in sample.items()
            }
            for name in points:
                positive = good & (mean[name] > 0)
                valid[name][offset : offset + size] &= positive
                contribution = np.zeros(size)
                contribution[positive] = (
                    100 * (mean[name][positive] - mean["adaptive"][positive]) / mean[name][positive]
                )
                estimates[name][offset : offset + size] += contribution / len(data)
    result = {}
    for name in points:
        point = float(np.mean(points[name])) if all(v is not None for v in points[name]) else None
        invalid = int((~valid[name]).sum())
        result[name] = {
            "equal_namespace_reduction_percent": point,
            "interval_percent": None
            if invalid or point is None
            else np.quantile(estimates[name], [alpha / 2, 1 - alpha / 2]).tolist(),
            "invalid_replicates": invalid,
        }
    return {
        "comparisons": result,
        "namespace_count": len(data),
        "resamples": resamples,
        "seed": seed,
        "segment_days": segment_days,
        "alpha_per_comparison": alpha,
        "interpretation": "Prespecified two-comparator family: nominal alpha=.025 per comparison from family alpha=.05; percentile calibration is approximate; conditional on selected namespaces, Source10 and fixed paired seeds. Circular seams and small entity samples limit inference.",
    }


def summarize(protocol_path: Path, run: Path, output: Path) -> dict:
    """Verify the full locked matrix before presenting its fixed objectives."""
    protocol = json.loads(protocol_path.read_text())
    complete = json.loads((run / "completion.json").read_text())
    if not complete["complete"] or complete["failures"]:
        raise ValueError(
            "Incomplete confirmation matrix; preserve partial outputs without a final claim"
        )
    output.mkdir(parents=True, exist_ok=False)
    records, cells, groups, data = [], [], [], {}
    null_targets = []
    for group in protocol["groups"]:
        namespace = group["namespace"]
        manifest_path = run / namespace / "manifest.json"
        expected_summary = next(
            r for r in complete["complete_groups"] if r["namespace"] == namespace
        )
        if digest(manifest_path) != expected_summary["manifest_sha256"]:
            raise ValueError("Group manifest mismatch")
        entries = json.loads(manifest_path.read_text())
        lookup = {(r["target"], r["seed"]): r for r in entries}
        if set(lookup) != {(t, s) for t in group["selected_ids"] for s in protocol["seeds"]}:
            raise ValueError("Locked target/seed matrix mismatch")
        means = {name: [] for name in ["fixed", "fast_only", "static", "adaptive"]}
        arrays = {name: [] for name in ["fixed", "static", "adaptive"]}
        for target in group["selected_ids"]:
            per_seed = []
            for seed in protocol["seeds"]:
                entry = lookup[target, seed]
                path = Path(entry["path"])
                if digest(path) != entry["sha256"]:
                    raise ValueError("Cell fingerprint mismatch")
                cell = json.loads(path.read_text())
                if cell["protocol_sha256"] != digest(protocol_path) or (
                    cell["namespace"],
                    cell["target"],
                    cell["seed"],
                ) != (namespace, target, seed):
                    raise ValueError("Cell protocol/identity mismatch")
                cells.append(
                    {
                        "namespace": namespace,
                        "target": target,
                        "seed": seed,
                        "path": str(path),
                        "sha256": entry["sha256"],
                    }
                )
                per_seed.append(cell)
            nulls = [r["cell"] is None for r in per_seed]
            if any(nulls):
                if not all(nulls):
                    raise ValueError("Seed coverage mismatch")
                null_targets.append({"namespace": namespace, "target": target})
                continue
            origins = per_seed[0]["cell"]["origins"]
            if any(r["cell"]["origins"] != origins for r in per_seed):
                raise ValueError("Seed origin masks differ")
            start = datetime.fromisoformat(group["deployment"]).date()
            indices = [(datetime.fromisoformat(o).date() - start).days for o in origins]
            for name in means:
                value = float(np.mean([r["arms"][name]["mae"] for r in per_seed]))
                means[name].append(value)
                if name in arrays:
                    row = np.full(90, np.nan)
                    row[indices] = np.mean([r["arms"][name]["daily_mae"] for r in per_seed], axis=0)
                    arrays[name].append(row)
            row = {"namespace": namespace, "target": target, "scored_days_per_seed": len(origins)}
            row.update(
                {name: float(np.mean([r["arms"][name]["mae"] for r in per_seed])) for name in means}
            )
            for name in ["fixed", "static"]:
                row["adaptive_vs_" + name + "_reduction_percent"] = (
                    100 * (row[name] - row["adaptive"]) / row[name] if row[name] > 0 else None
                )
            records.append(row)
        if not means["fixed"]:
            raise ValueError(
                "A locked namespace has no scored target; primary aggregate unavailable"
            )
        row = {
            "namespace": namespace,
            "selected_entities": len(group["selected_ids"]),
            "scored_entities": len(means["fixed"]),
        }
        row.update({name: float(np.mean(value)) for name, value in means.items()})
        for name in ["fixed", "static"]:
            row["adaptive_vs_" + name + "_reduction_percent"] = (
                100 * (row[name] - row["adaptive"]) / row[name] if row[name] > 0 else None
            )
            row["entities_lower_than_" + name] = sum(
                r["adaptive"] < r[name] for r in records if r["namespace"] == namespace
            )
        groups.append(row)
        data[namespace] = {name: np.asarray(value) for name, value in arrays.items()}
    statistics = {}
    for length in protocol["evaluation"]["block_days"]:
        statistics[str(length)] = stratified_contrasts(
            data,
            resamples=protocol["evaluation"]["resamples"],
            seed=protocol["evaluation"]["seed"],
            segment_days=length,
            alpha=protocol["evaluation"]["alpha_per_comparison"],
        )
    primary = statistics[str(protocol["evaluation"]["primary_block_days"])]
    both = not null_targets and all(
        r["interval_percent"] is not None and r["interval_percent"][0] > 0
        for r in primary["comparisons"].values()
    )
    result = {
        "schema": "new-entity-confirmation-result-v1",
        "protocol_sha256": digest(protocol_path),
        "group_results": groups,
        "primary": primary,
        "sensitivity": statistics,
        "null_targets": null_targets,
        "dual_comparator_interval_criterion_met": both,
        "history_scope": protocol["history_scope"],
        "limits": protocol["limits"],
    }
    save_path = output / "results.json"
    save_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    write_csv(output / "group-results.csv", groups)
    write_csv(output / "entity-results.csv", records)
    write_csv(output / "authenticated-cells.csv", cells)
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summarize(args.protocol, args.run, args.output)


if __name__ == "__main__":
    main()
