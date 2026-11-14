"""Authenticate saved expert forecasts and quantify exploratory paired uncertainty."""

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

from ev_evaluation.fusion_uncertainty import paired_mean_interval


def digest(path: Path) -> str:
    """Return a byte fingerprint without modifying the source."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write a small, uniformly shaped evidence table."""
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_errors(cell: dict, *, start: str, days: int) -> dict[str, np.ndarray]:
    """Recompute daily errors from saved predictions on the full local calendar."""
    source = cell["cell"]
    stable, fast, labels = (
        np.asarray(source[k], dtype=float) for k in ("stable", "fast", "labels")
    )
    if stable.shape != fast.shape or stable.shape != labels.shape or stable.shape[1:] != (24,):
        raise ValueError("Expert/label vector mismatch")
    if not all(np.isfinite(v).all() and (v >= 0).all() for v in (stable, fast, labels)):
        raise ValueError("Nonfinite or negative saved energy")
    predictions = {"fixed": stable}
    for name in ("static_mix", "fixed_share"):
        arm = cell["arms"][name]
        weights = np.asarray(arm["weights"], dtype=float)[:, None]
        if weights.shape != (len(stable), 1) or not np.isfinite(weights).all():
            raise ValueError("Invalid saved weights")
        value = weights * stable + (1 - weights) * fast
        np.testing.assert_allclose(value, arm["predictions_kwh"], atol=5e-12, rtol=2e-14)
        predictions[name] = value
    result = {name: np.full(days, np.nan) for name in predictions}
    origin_dates = [datetime.fromisoformat(o) for o in source["origins"]]
    if len(set(origin_dates)) != len(stable) or len(stable) != cell["scored_days"]:
        raise ValueError("Duplicate origins or scored-day mismatch")
    start_date = datetime.fromisoformat(start).date()
    for name, values in predictions.items():
        errors = np.abs(values - labels).mean(1)
        recorded = cell["arms"]["old_fixed" if name == "fixed" else name]
        if not math.isclose(float(errors.mean()), recorded["mae"], abs_tol=5e-12, rel_tol=2e-14):
            raise ValueError("Saved daily errors disagree with recorded mean")
        for origin, error in zip(origin_dates, errors, strict=True):
            index = (origin.date() - start_date).days
            if not 0 <= index < days or any((origin.hour, origin.minute, origin.second)):
                raise ValueError("Origin outside local scheduled calendar")
            result[name][index] = error
    return result


def analyze(
    manifest_path: Path, lock_path: Path, output: Path, *, resamples: int, seed: int
) -> None:
    """Read authenticated cells, preserving pairing, nulls and scheduled gaps."""
    output.mkdir(parents=True, exist_ok=False)
    lock = json.loads(lock_path.read_text())
    groups = {
        (
            "-".join(g["namespace"]) if isinstance(g["namespace"], list) else g["namespace"],
            g["history_days"],
        ): g
        for g in lock["groups"]
    }
    manifest = json.loads(manifest_path.read_text())
    config = {
        "schema": "fusion-evidence-profile-v1",
        "scope": "Posthoc uncertainty on inspected historical cohort; no new training or confirmation",
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "script_sha256": digest(Path(__file__)),
        "analysis_sha256": digest(
            Path(__file__).resolve().parents[1] / "ev_evaluation/fusion_uncertainty.py"
        ),
        "input_manifest_sha256": digest(manifest_path),
        "execution_lock_sha256": digest(lock_path),
        "resamples": resamples,
        "seed": seed,
        "alpha": 0.05,
        "block_sensitivity_days": [3, 7, 14],
        "seeds_averaged_not_resampled": lock["seeds"],
        "estimand": "Mean seed-averaged daily MAE within entity, then equal entities within namespace/history",
        "percentage": "100*(mean reference MAE - mean adaptive MAE)/mean reference MAE; not mean entity percentages",
        "calendar": "90 scheduled local dates; missing dates stay NaN; common circular draws across entities and arms",
        "runtime": {"python": platform.python_version(), "numpy": np.__version__},
    }
    (output / "analysis-profile.json").write_text(json.dumps(config, indent=2) + "\n")
    started = time.perf_counter()
    collected = defaultdict(dict)
    identities, nulls = [], []
    unique = set()
    for entry in manifest:
        path = Path(entry["path"])
        if digest(path) != entry["sha256"]:
            raise ValueError(f"Saved-cell authentication failed: {path}")
        cell = json.loads(path.read_text())
        identity = (cell["namespace"], cell["history_days"], cell["target"], cell["seed"])
        if identity in unique:
            raise ValueError("Duplicate entity/history/seed cell")
        unique.add(identity)
        key = identity[:2]
        if key not in groups or cell["target"] not in groups[key]["selected_ids"]:
            raise ValueError("Cell not in execution lock")
        identities.append(
            {
                "namespace": identity[0],
                "history_days": identity[1],
                "target": identity[2],
                "seed": identity[3],
                "sha256": entry["sha256"],
            }
        )
        if cell["cell"] is None:
            if cell["scored_days"] != 0:
                raise ValueError("Null unit has nonzero scoring coverage")
            nulls.append(identity)
            continue
        arrays = read_errors(cell, start=groups[key]["deployment"], days=lock["replay_days"])
        collected[key].setdefault(cell["target"], {})[cell["seed"]] = arrays
    expected = {
        (
            "-".join(g["namespace"]) if isinstance(g["namespace"], list) else g["namespace"],
            g["history_days"],
            target,
            s,
        )
        for g in lock["groups"]
        for target in g["selected_ids"]
        for s in lock["seeds"]
    }
    if unique != expected:
        raise ValueError("Missing or extra execution-lock units")
    primary, sensitivity, effects = [], [], []
    for namespace, history in sorted(groups):
        targets = collected[namespace, history]
        pooled = {name: [] for name in ("fixed", "static_mix", "fixed_share")}
        for target, cells in sorted(targets.items()):
            if set(cells) != set(lock["seeds"]):
                raise ValueError("Incomplete paired seed matrix")
            masks = [np.isnan(cells[s]["fixed"]) for s in lock["seeds"]]
            if any(not np.array_equal(masks[0], v) for v in masks[1:]):
                raise ValueError("Scored origins differ between paired seeds")
            for name in pooled:
                values = np.stack([cells[s][name] for s in lock["seeds"]])
                if any(not np.array_equal(masks[0], np.isnan(v)) for v in values):
                    raise ValueError("Scored origins differ between methods")
                pooled[name].append(values.mean(0))
        pooled = {name: np.asarray(rows) for name, rows in pooled.items()}
        for reference in ("fixed", "static_mix"):
            context = {"namespace": namespace, "history_days": history, "reference": reference}
            for segment in (None, 3, 7, 14):
                result = paired_mean_interval(
                    pooled[reference],
                    pooled["fixed_share"],
                    resamples=resamples,
                    seed=seed,
                    segment_days=segment,
                )
                row = {**context, **result}
                (primary if segment is None else sensitivity).append(row)
            for index, target in enumerate(sorted(targets)):
                a = float(np.nanmean(pooled[reference][index]))
                b = float(np.nanmean(pooled["fixed_share"][index]))
                effects.append(
                    {
                        **context,
                        "target": target,
                        "reference_mae_kwh": a,
                        "adaptive_mae_kwh": b,
                        "gap_kwh": b - a,
                        "reduction_percent": 100 * (a - b) / a if a > 0 else None,
                        "scored_days_per_seed": int(np.isfinite(pooled[reference][index]).sum()),
                        "seeds": len(lock["seeds"]),
                    }
                )
    for name, rows in (("entity-intervals", primary), ("calendar-sensitivity", sensitivity)):
        (output / f"{name}.json").write_text(json.dumps(rows, indent=2) + "\n")
        flat = [
            {k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in r.items()}
            for r in rows
        ]
        write_csv(output / f"{name}.csv", flat)
    write_csv(output / "entity-effects.csv", effects)
    summary = {
        "cells_rehashed": len(identities),
        "null_units": nulls,
        "groups": len(groups),
        "primary_comparisons": len(primary),
        "calendar_sensitivity_comparisons": len(sensitivity),
        "elapsed_seconds": time.perf_counter() - started,
        "primary_interval_excludes_zero": {
            ref: sum(
                r["gap_interval_kwh"][1] < 0 or r["gap_interval_kwh"][0] > 0
                for r in primary
                if r["reference"] == ref
            )
            for ref in ("fixed", "static_mix")
        },
        "limits": "Exploratory marginal intervals on selected entities; no test-set novelty or simultaneous significance. All source pretraining, expert training and model-selection compute are not jointly measured.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_csv(output / "authenticated-cells.csv", identities)
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20261113)
    args = parser.parse_args()
    analyze(args.manifest, args.lock, args.output, resamples=args.resamples, seed=args.seed)


if __name__ == "__main__":
    main()
