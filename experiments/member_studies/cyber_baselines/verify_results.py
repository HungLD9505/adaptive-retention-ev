"""Independent audit and verification readback script for Cyber benchmark (Issue #95)."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from experiments.member_studies.cyber_baselines.config import BenchmarkConfig


def verify_manifest(config: BenchmarkConfig) -> bool:
    """Verify SHA-256 and byte sizes of all artifacts against manifest.json."""
    manifest_path = config.output_dir / "manifest.json"
    if not manifest_path.is_file():
        print(f"[FAIL] Missing manifest.json at {manifest_path}")
        return False

    with open(manifest_path, "rb") as f:
        manifest: dict[str, dict[str, Any]] = json.loads(f.read().decode("utf-8"))

    print(f"=== Verifying {len(manifest)} manifest entries ===")
    all_passed = True
    crlf_detected = 0

    base_dir = config.output_dir.parent

    for rel_path_str, meta in manifest.items():
        if rel_path_str.endswith(".json") and rel_path_str != "manifest.json":
            target_file = config.output_dir / Path(rel_path_str).name
        elif rel_path_str.endswith(".pt"):
            target_file = config.checkpoint_dir / Path(rel_path_str).name
        elif rel_path_str.endswith(".csv"):
            target_file = config.runs_csv_path
        else:
            target_file = base_dir / rel_path_str

        if not target_file.is_file():
            print(f"[FAIL] Missing file: {target_file}")
            all_passed = False
            continue

        with open(target_file, "rb") as f:
            bytes_data = f.read()

        if b"\r\n" in bytes_data and target_file.suffix in (".json", ".csv"):
            crlf_detected += 1

        actual_sha = hashlib.sha256(bytes_data).hexdigest()
        actual_size = len(bytes_data)

        if actual_sha != meta["sha256"]:
            print(
                f"[FAIL] Hash mismatch for {rel_path_str}:\n  Expected: {meta['sha256']}\n  Actual:   {actual_sha}"
            )
            all_passed = False
        elif actual_size != meta["bytes"]:
            print(
                f"[FAIL] Size mismatch for {rel_path_str}:\n  Expected: {meta['bytes']}\n  Actual:   {actual_size}"
            )
            all_passed = False

    if crlf_detected > 0:
        print(
            f"[WARN] CRLF newlines detected in {crlf_detected} files (binary policy recommends strict LF)."
        )
    else:
        print("[PASS] Strict LF newline consistency verified across all files.")

    if all_passed:
        print(f"[PASS] All {len(manifest)} manifest entries verified successfully!")
    return all_passed


def verify_predictions_and_recompute_metrics(config: BenchmarkConfig) -> bool:
    """Read back all prediction artifacts, recompute metrics, and verify agreement with runs.csv."""
    if not config.runs_csv_path.is_file():
        print(f"[FAIL] Missing runs.csv at {config.runs_csv_path}")
        return False

    with open(config.runs_csv_path, "r", encoding="utf-8") as f:
        csv_lines = [line.strip() for line in f if line.strip()]

    rows = [line.split(",") for line in csv_lines[1:]]
    print(f"\n=== Recomputing metrics across {len(rows)} runs from predictions JSON ===")

    all_agreed = True
    verified_count = 0

    for r in rows:
        run_id = r[0]
        scheduled_days = int(r[5])
        issued_days = int(r[6])
        scored_days = int(r[7])
        reported_mae = float(r[8]) if r[8] else None
        reported_rmse = float(r[9]) if r[9] else None
        ledger_sha = r[16]

        pred_file = config.output_dir / f"{run_id}_predictions.json"
        if not pred_file.is_file():
            print(f"[FAIL] Missing prediction artifact for run {run_id}")
            all_agreed = False
            continue

        with open(pred_file, "rb") as f:
            raw_bytes = f.read()

        file_sha = hashlib.sha256(raw_bytes).hexdigest()
        if file_sha != ledger_sha:
            print(
                f"[FAIL] Checksum mismatch in ledger for {run_id}:\n  Ledger: {ledger_sha}\n  Disk:   {file_sha}"
            )
            all_agreed = False

        data = json.loads(raw_bytes.decode("utf-8"))
        daily_results = data["daily_results"]

        # Recompute daily errors independently
        recomputed_maes: list[float] = []
        recomputed_sq_errors: list[float] = []
        rec_scheduled = len(daily_results)
        rec_issued = sum(1 for d in daily_results if d["issued"])
        rec_scored = sum(1 for d in daily_results if d["scored"])

        if (
            rec_scheduled != scheduled_days
            or rec_issued != issued_days
            or rec_scored != scored_days
        ):
            print(
                f"[FAIL] Coverage count mismatch for {run_id}: "
                f"Sched {rec_scheduled} vs {scheduled_days}, Issued {rec_issued} vs {issued_days}, Scored {rec_scored} vs {scored_days}"
            )
            all_agreed = False

        for d in daily_results:
            if d["scored"]:
                preds = d["predictions_kwh"]
                gt = d["ground_truth_kwh"]
                diffs = [abs(p - y) for p, y in zip(preds, gt, strict=True)]
                sq = [(p - y) ** 2 for p, y in zip(preds, gt, strict=True)]
                d_mae = float(np.mean(diffs))
                d_rmse = float(math.sqrt(np.mean(sq)))

                if abs(d_mae - d["mae_kwh"]) > 1e-5 or abs(d_rmse - d["rmse_kwh"]) > 1e-5:
                    print(f"[FAIL] Daily error mismatch in {run_id} origin {d['origin']}")
                    all_agreed = False

                recomputed_maes.append(d_mae)
                recomputed_sq_errors.extend(sq)

        if recomputed_maes:
            recomputed_overall_mae = float(np.mean(recomputed_maes))
            recomputed_overall_rmse = float(math.sqrt(np.mean(recomputed_sq_errors)))
        else:
            recomputed_overall_mae = None
            recomputed_overall_rmse = None

        if reported_mae is not None and recomputed_overall_mae is not None:
            if abs(reported_mae - recomputed_overall_mae) > 1e-5:
                print(
                    f"[FAIL] Overall MAE mismatch for {run_id}: {reported_mae} vs {recomputed_overall_mae}"
                )
                all_agreed = False
        elif reported_mae != recomputed_overall_mae:
            print(
                f"[FAIL] Null metric mismatch for {run_id}: {reported_mae} vs {recomputed_overall_mae}"
            )
            all_agreed = False

        if reported_rmse is not None and recomputed_overall_rmse is not None:
            if abs(reported_rmse - recomputed_overall_rmse) > 1e-5:
                print(
                    f"[FAIL] Overall RMSE mismatch for {run_id}: {reported_rmse} vs {recomputed_overall_rmse}"
                )
                all_agreed = False
        elif reported_rmse != recomputed_overall_rmse:
            print(
                f"[FAIL] Null RMSE mismatch for {run_id}: {reported_rmse} vs {recomputed_overall_rmse}"
            )
            all_agreed = False

        verified_count += 1

    if all_agreed:
        print(
            f"[PASS] Successfully verified all {verified_count} runs: independent recomputation matches runs.csv to < 1e-5 kWh!"
        )
    return all_agreed


def compute_paired_statistics(config: BenchmarkConfig) -> None:
    """Compute station-first summaries and common-origin paired differences."""
    from scipy import stats

    print("\n=== Paired Common-Origin Differences & Statistical Indistinguishability ===")
    # Load all predictions
    models_to_compare = [
        ("GRU", "transfer"),
        ("LSTM", "transfer"),
        ("TCN", "transfer"),
        ("TimeXer", "transfer"),
        ("MLP", "transfer"),
        ("Random Forest", "target_only"),
        ("Daily Naive", "target_only"),
        ("SARIMA", "target_only"),
        ("Basic GCN-LSTM", "target_only"),
    ]

    # Map (model, mode) -> origin -> list of absolute errors across seeds and stations
    origin_errors: dict[tuple[str, str], dict[str, list[float]]] = {
        m: {} for m in models_to_compare
    }

    for p in config.output_dir.glob("*_predictions.json"):
        with open(p, "rb") as f:
            data = json.load(f)
        key = (data["model"], data["mode"])
        if key in origin_errors:
            for d in data["daily_results"]:
                if d["scored"]:
                    orig_key = f"{data['station_id']}_{d['origin']}"
                    origin_errors[key].setdefault(orig_key, []).append(d["mae_kwh"])

    # Common scored origins present across all models
    common_origins = set.intersection(*(set(errs.keys()) for errs in origin_errors.values()))
    print(f"Total common scored station-origins: {len(common_origins)}")

    # Paired comparisons against GRU (best performing transfer model)
    gru_means = [np.mean(origin_errors[("GRU", "transfer")][o]) for o in sorted(common_origins)]

    print(
        "\n| Model Pair | Mean MAE Diff (kWh) | Paired t-stat | p-value | Significant at alpha=0.05 |"
    )
    print("| :--- | :--- | :--- | :--- | :--- |")

    for m, mode in models_to_compare:
        if (m, mode) == ("GRU", "transfer"):
            continue
        comp_means = [np.mean(origin_errors[(m, mode)][o]) for o in sorted(common_origins)]
        diffs = np.array(comp_means) - np.array(gru_means)
        mean_diff = float(np.mean(diffs))

        t_res = stats.ttest_rel(comp_means, gru_means)
        p_val = float(t_res.pvalue)
        sig = "Yes (p < 0.05)" if p_val < 0.05 else "No (Indistinguishable)"

        print(
            f"| GRU Transfer vs {m} ({mode}) | {mean_diff:+.4f} | {t_res.statistic:.3f} | {p_val:.4e} | {sig} |"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Cyber UrbanEV Benchmark Results")
    parser.add_argument("--paired", action="store_true", help="Compute paired statistical tests")
    args = parser.parse_args()

    config = BenchmarkConfig()
    v1 = verify_manifest(config)
    v2 = verify_predictions_and_recompute_metrics(config)

    if args.paired:
        try:
            compute_paired_statistics(config)
        except Exception as e:
            print(f"[NOTE] Paired statistics calculation skipped: {e}")

    if v1 and v2:
        print("\n=======================================================")
        print("ALL AUDIT AND VERIFICATION CRITERIA SATISFIED (Issue #95)")
        print("=======================================================")
    else:
        print("\n=======================================================")
        print("VERIFICATION FAILED: SEE LOGS ABOVE")
        print("=======================================================")
        exit(1)


if __name__ == "__main__":
    main()
