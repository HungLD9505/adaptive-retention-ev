"""Independent readback, metric recomputation and paired analysis for Cyber benchmark (Issue #95).

Everything here is recomputed from the saved per-origin forecast files, never from runs.csv:

1. ``verify_manifest``: byte-level SHA-256/size check of every manifest entry.
2. ``verify_predictions_and_recompute_metrics``: recompute daily MAE/RMSE, coverage counts and
   run-level MAE/RMSE from the stored forecasts and labels; compare with the ledger.
3. ``write_readback_tables``: daily error export, station-first summaries, seed variability and
   paired common-origin differences with a station-stratified moving-block bootstrap CI.

Usage (from the repository root, with the declared dependencies installed)::

    python -m experiments.member_studies.cyber_baselines.verify_results --readback
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from experiments.member_studies.cyber_baselines.config import REPO_ROOT, BenchmarkConfig

TOL = 1e-5
BOOTSTRAP_REPS = 10_000
BLOCK_DAYS = 7
REFERENCE = ("GRU", "transfer")
PAIRED_COMPARATORS = [
    ("LSTM", "transfer"),
    ("TCN", "transfer"),
    ("MLP", "transfer"),
    ("TimeXer", "transfer"),
    ("Random Forest", "target_only"),
    ("Ridge", "target_only"),
    ("XGBoost", "target_only"),
    ("Daily Naive", "target_only"),
    ("Seasonal Naive", "target_only"),
    ("SARIMA", "target_only"),
    ("Basic GCN-LSTM", "target_only"),
]
WITHIN_BACKBONE = ["MLP", "GRU", "LSTM", "TCN", "TimeXer"]


def verify_manifest(config: BenchmarkConfig) -> bool:
    """Verify SHA-256 and byte sizes of all artifacts against manifest.json."""
    manifest_path = config.output_dir / "manifest.json"
    if not manifest_path.is_file():
        print(f"[FAIL] Missing manifest.json at {manifest_path}")
        return False
    manifest: dict[str, dict[str, Any]] = json.loads(manifest_path.read_bytes().decode("utf-8"))
    print(f"=== Verifying {len(manifest)} manifest entries ===")

    ok = True
    crlf = 0
    for rel_path, meta in manifest.items():
        target = REPO_ROOT / rel_path
        if not target.is_file():
            print(f"[FAIL] Missing file: {rel_path}")
            ok = False
            continue
        data = target.read_bytes()
        if target.suffix in (".json", ".csv", ".jsonl") and b"\r\n" in data:
            crlf += 1
        if hashlib.sha256(data).hexdigest() != meta["sha256"] or len(data) != meta["bytes"]:
            print(f"[FAIL] Hash/size mismatch for {rel_path}")
            ok = False
    if crlf:
        print(f"[FAIL] CRLF newlines detected in {crlf} text artifacts (LF-only policy).")
        ok = False
    if ok:
        print(f"[PASS] All {len(manifest)} manifest entries match on-disk bytes (LF-only text).")
    return ok


def _load_ledger(config: BenchmarkConfig) -> list[dict[str, str]]:
    with open(config.runs_csv_path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_predictions(config: BenchmarkConfig, run_id: str) -> tuple[dict[str, Any], str]:
    raw = (config.output_dir / f"{run_id}_predictions.json").read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def _close(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= TOL


def verify_predictions_and_recompute_metrics(config: BenchmarkConfig) -> bool:
    """Recompute every daily and run-level metric from stored forecasts and compare to ledger."""
    if not config.runs_csv_path.is_file():
        print(f"[FAIL] Missing ledger at {config.runs_csv_path}")
        return False
    rows = _load_ledger(config)
    print(f"\n=== Recomputing metrics for {len(rows)} ledger rows from forecast files ===")

    ok = True
    for r in rows:
        run_id = r["run_id"]
        try:
            data, sha = _load_predictions(config, run_id)
        except FileNotFoundError:
            print(f"[FAIL] Missing forecast file for {run_id}")
            ok = False
            continue
        if sha != r["predictions_sha256"]:
            print(f"[FAIL] Ledger hash differs from on-disk bytes for {run_id}")
            ok = False

        daily = data["daily_results"]
        maes: list[float] = []
        sq: list[float] = []
        for d in daily:
            if not d["scored"]:
                if d["mae_kwh"] is not None or d["ground_truth_kwh"] is not None:
                    print(f"[FAIL] Unscored origin carries metrics in {run_id} {d['origin']}")
                    ok = False
                continue
            errs = [p - y for p, y in zip(d["predictions_kwh"], d["ground_truth_kwh"], strict=True)]
            d_mae = float(np.mean(np.abs(errs)))
            d_rmse = float(math.sqrt(np.mean(np.square(errs))))
            if not (_close(d_mae, d["mae_kwh"]) and _close(d_rmse, d["rmse_kwh"])):
                print(f"[FAIL] Daily metric mismatch in {run_id} {d['origin']}")
                ok = False
            maes.append(d_mae)
            sq.extend(float(e) ** 2 for e in errs)

        counts = (len(daily), sum(d["issued"] for d in daily), sum(d["scored"] for d in daily))
        ledger_counts = (int(r["scheduled_days"]), int(r["issued_days"]), int(r["scored_days"]))
        if counts != ledger_counts:
            print(f"[FAIL] Coverage mismatch for {run_id}: {counts} vs {ledger_counts}")
            ok = False

        mae = float(np.mean(maes)) if maes else None
        rmse = float(math.sqrt(np.mean(sq))) if sq else None
        led_mae = float(r["mae_kwh"]) if r["mae_kwh"] else None
        led_rmse = float(r["rmse_kwh"]) if r["rmse_kwh"] else None
        # Ledger stores 6 decimals
        if not (
            (mae is None and led_mae is None)
            or (mae is not None and led_mae is not None and abs(mae - led_mae) <= 5e-6)
        ) or not (
            (rmse is None and led_rmse is None)
            or (rmse is not None and led_rmse is not None and abs(rmse - led_rmse) <= 5e-6)
        ):
            print(f"[FAIL] Run metric mismatch for {run_id}: {mae} vs {led_mae}")
            ok = False

    if ok:
        print(f"[PASS] All {len(rows)} rows recomputed from forecast bytes match the ledger.")
    return ok


def _collect_daily(config: BenchmarkConfig) -> list[dict[str, Any]]:
    out = []
    for r in _load_ledger(config):
        data, _ = _load_predictions(config, r["run_id"])
        for d in data["daily_results"]:
            out.append(
                {
                    "run_id": r["run_id"],
                    "model": data["model"],
                    "mode": data["mode"],
                    "station_id": data["station_id"],
                    "seed": data["seed"],
                    "origin": d["origin"],
                    "issued": d["issued"],
                    "scored": d["scored"],
                    "mae_kwh": d["mae_kwh"],
                    "rmse_kwh": d["rmse_kwh"],
                }
            )
    return out


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: ("" if v is None else v) for k, v in row.items()})


def _seed_mean_by_origin(
    daily: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, dict[str, float]]]:
    """(model, mode) -> station -> origin -> seed-averaged daily MAE (scored origins only)."""
    acc: dict[tuple[str, str], dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for d in daily:
        if d["scored"]:
            acc[(d["model"], d["mode"])][d["station_id"]][d["origin"]].append(d["mae_kwh"])
    return {
        k: {s: {o: float(np.mean(v)) for o, v in by_o.items()} for s, by_o in st.items()}
        for k, st in acc.items()
    }


def _block_bootstrap_ci(
    diffs_by_station: dict[str, np.ndarray], rng: np.random.Generator
) -> tuple[float, float]:
    """95% CI of the station-first mean difference.

    Within each station, the chronologically ordered common-origin differences are resampled
    in moving blocks of ``BLOCK_DAYS`` origins to respect serial correlation; the statistic is
    the unweighted mean of station means. Stations are fixed (not resampled): with only four
    Development targets, between-station uncertainty is not estimable and is not represented.
    """
    stats = np.empty(BOOTSTRAP_REPS)
    stations = sorted(diffs_by_station)
    for b in range(BOOTSTRAP_REPS):
        means = []
        for s in stations:
            x = diffs_by_station[s]
            n = len(x)
            block = min(BLOCK_DAYS, n)
            n_blocks = math.ceil(n / block)
            starts = rng.integers(0, n - block + 1, size=n_blocks)
            sample = np.concatenate([x[i : i + block] for i in starts])[:n]
            means.append(sample.mean())
        stats[b] = float(np.mean(means))
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def _paired_row(
    label: str,
    a: dict[str, dict[str, float]],
    b: dict[str, dict[str, float]],
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Difference b - a on origins scored by both, per station, then station-first mean."""
    diffs_by_station: dict[str, np.ndarray] = {}
    row: dict[str, Any] = {"comparison": label}
    for s in sorted(set(a) & set(b)):
        common = sorted(set(a[s]) & set(b[s]))
        diffs_by_station[s] = np.array([b[s][o] - a[s][o] for o in common])
        row[f"diff_{s}"] = round(float(diffs_by_station[s].mean()), 6)
        row[f"n_{s}"] = len(common)
    station_means = [v.mean() for v in diffs_by_station.values()]
    lo, hi = _block_bootstrap_ci(diffs_by_station, rng)
    row.update(
        {
            "station_first_mean_diff_kwh": round(float(np.mean(station_means)), 6),
            "ci95_low": round(lo, 6),
            "ci95_high": round(hi, 6),
            "stations_favoring_reference": int(sum(m > 0 for m in station_means)),
            "common_origins_total": int(sum(len(v) for v in diffs_by_station.values())),
        }
    )
    return row


def write_readback_tables(config: BenchmarkConfig, out_dir: Path) -> None:
    """Write daily errors, station-first summaries, seed variability and paired differences."""
    daily = _collect_daily(config)
    _write_csv(out_dir / "daily_errors.csv", daily)

    # Station-first summary: per (model, mode, station) mean over seeds of run MAE, then mean
    runs = _load_ledger(config)
    per_station: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    per_seed: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    rmse_station: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in runs:
        if not r["mae_kwh"]:
            continue
        key = (r["model"], r["mode"])
        per_station[key][r["station_id"]].append(float(r["mae_kwh"]))
        rmse_station[key][r["station_id"]].append(float(r["rmse_kwh"]))
        per_seed[key][r["seed"] or "det"].append(float(r["mae_kwh"]))

    summary_rows = []
    for (model, mode), st in sorted(per_station.items()):
        row: dict[str, Any] = {"model": model, "mode": mode}
        for s in sorted(st):
            row[f"mae_{s}"] = round(float(np.mean(st[s])), 6)
        row["station_first_mae_kwh"] = round(float(np.mean([np.mean(v) for v in st.values()])), 6)
        row["station_first_rmse_kwh"] = round(
            float(np.mean([np.mean(v) for v in rmse_station[(model, mode)].values()])), 6
        )
        row["rows"] = int(sum(len(v) for v in st.values()))
        summary_rows.append(row)
    _write_csv(out_dir / "station_first_summary.csv", summary_rows)

    seed_rows = []
    for (model, mode), by_seed in sorted(per_seed.items()):
        if "det" in by_seed:
            continue
        seed_means = {s: float(np.mean(v)) for s, v in sorted(by_seed.items())}
        vals = np.array(list(seed_means.values()))
        seed_rows.append(
            {
                "model": model,
                "mode": mode,
                **{f"seed{s}_mae": round(v, 6) for s, v in seed_means.items()},
                "mean": round(float(vals.mean()), 6),
                "sample_sd": round(float(vals.std(ddof=1)), 6),
            }
        )
    _write_csv(out_dir / "seed_variability.csv", seed_rows)

    rng = np.random.default_rng(20261110)
    by_origin = _seed_mean_by_origin(daily)
    paired = []
    ref = by_origin[REFERENCE]
    for comp in PAIRED_COMPARATORS:
        if comp in by_origin:
            label = f"{comp[0]} {comp[1]} minus GRU transfer"
            paired.append(_paired_row(label, ref, by_origin[comp], rng))
    for bb in WITHIN_BACKBONE:
        if (bb, "transfer") in by_origin and (bb, "target_only") in by_origin:
            label = f"{bb} target_only minus {bb} transfer"
            paired.append(
                _paired_row(label, by_origin[(bb, "transfer")], by_origin[(bb, "target_only")], rng)
            )
    _write_csv(out_dir / "paired_differences.csv", paired)

    print(f"\n=== Readback tables written to {out_dir} ===")
    for p in paired:
        print(
            f"{p['comparison']:<45} diff={p['station_first_mean_diff_kwh']:+.4f} "
            f"CI95=[{p['ci95_low']:+.4f}, {p['ci95_high']:+.4f}] "
            f"stations>0={p['stations_favoring_reference']}/4"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Cyber UrbanEV Benchmark Results")
    parser.add_argument(
        "--readback", action="store_true", help="Also write readback/analysis tables"
    )
    parser.add_argument("--skip-manifest", action="store_true", help="Skip manifest byte check")
    args = parser.parse_args()

    config = BenchmarkConfig()
    v1 = True if args.skip_manifest else verify_manifest(config)
    v2 = verify_predictions_and_recompute_metrics(config)
    if args.readback:
        write_readback_tables(config, config.output_dir / "readback")

    if v1 and v2:
        print("\nVERIFICATION PASSED")
    else:
        print("\nVERIFICATION FAILED: SEE LOGS ABOVE")
        sys.exit(1)


if __name__ == "__main__":
    main()
