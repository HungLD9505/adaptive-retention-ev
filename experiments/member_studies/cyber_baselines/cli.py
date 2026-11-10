"""Unified CLI orchestrator for Cyber UrbanEV Baseline Benchmark (Issue #95)."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from experiments.member_studies.cyber_baselines.config import (
    BenchmarkConfig,
)
from experiments.member_studies.cyber_baselines.data import (
    load_distance_matrix,
    load_source_dataset,
    load_target_replay_data,
)
from experiments.member_studies.cyber_baselines.models.classical import (
    RandomForestBaseline,
    RidgeBaseline,
    SARIMABaseline,
    XGBoostBaseline,
)
from experiments.member_studies.cyber_baselines.models.graph import BasicGCNLSTM
from experiments.member_studies.cyber_baselines.models.naive import DailyNaive, SeasonalNaive
from experiments.member_studies.cyber_baselines.runner import (
    BenchmarkRunner,
    append_summary_to_csv,
)
from experiments.member_studies.cyber_baselines.training import (
    build_neural_forecaster,
    train_source_model,
)


def run_pilot(config: BenchmarkConfig) -> None:
    """Run pilot on target 1405 for all 12 model families to verify execution gates."""
    print("=== STARTING PILOT RUN (Target 1405, Seed 42) ===")
    runner = BenchmarkRunner(config)
    target_data = load_target_replay_data(config.input_root, "1405")

    # 1. Daily Naive
    dn = DailyNaive(target_data.initial_records)
    res_dn = runner.run_replay(dn, target_data, mode="target_only", seed=None)
    print(
        f"[Pilot] Daily Naive: MAE={res_dn.mae_kwh:.4f} kWh, Scored={res_dn.scored_days}, Time={res_dn.total_seconds:.2f}s"
    )

    # 2. Seasonal Naive
    sn = SeasonalNaive(target_data.initial_records)
    res_sn = runner.run_replay(sn, target_data, mode="target_only", seed=None)
    print(
        f"[Pilot] Seasonal Naive: MAE={res_sn.mae_kwh:.4f} kWh, Scored={res_sn.scored_days}, Time={res_sn.total_seconds:.2f}s"
    )

    # 3. Ridge
    ridge = RidgeBaseline(alpha=1.0, initial_records=target_data.initial_records)
    res_ridge = runner.run_replay(ridge, target_data, mode="target_only", seed=None)
    print(
        f"[Pilot] Ridge: MAE={res_ridge.mae_kwh:.4f} kWh, Scored={res_ridge.scored_days}, Time={res_ridge.total_seconds:.2f}s"
    )

    # 4. SARIMA
    sarima = SARIMABaseline(initial_records=target_data.initial_records, maxiter=10)
    res_sarima = runner.run_replay(sarima, target_data, mode="target_only", seed=None)
    print(
        f"[Pilot] SARIMA: MAE={res_sarima.mae_kwh:.4f} kWh, Scored={res_sarima.scored_days}, Time={res_sarima.total_seconds:.2f}s"
    )

    # 5. Random Forest
    rf = RandomForestBaseline(seed=42, initial_records=target_data.initial_records)
    res_rf = runner.run_replay(rf, target_data, mode="target_only", seed=42)
    print(
        f"[Pilot] Random Forest: MAE={res_rf.mae_kwh:.4f} kWh, Scored={res_rf.scored_days}, Time={res_rf.total_seconds:.2f}s"
    )

    # 6. XGBoost
    xgb_m = XGBoostBaseline(seed=42, initial_records=target_data.initial_records)
    res_xgb = runner.run_replay(xgb_m, target_data, mode="target_only", seed=42)
    print(
        f"[Pilot] XGBoost: MAE={res_xgb.mae_kwh:.4f} kWh, Scored={res_xgb.scored_days}, Time={res_xgb.total_seconds:.2f}s"
    )

    # 7-11 Neural Backbones (Target-only)
    for bb in ("MLP", "GRU", "LSTM", "TCN", "TimeXer"):
        net, adapt_time = build_neural_forecaster(
            bb, "target_only", 42, "1405", target_data.initial_records, config
        )
        res_nn = runner.run_replay(
            net, target_data, mode="target_only", seed=42, target_adapt_seconds=adapt_time
        )
        print(
            f"[Pilot] {bb} (target_only): MAE={res_nn.mae_kwh:.4f} kWh, Scored={res_nn.scored_days}, Time={res_nn.total_seconds:.2f}s"
        )

    # 12. Basic GCN-LSTM
    adj_norm, node_ids = load_distance_matrix(config.raw_zip_path, config.targets)
    gcn = BasicGCNLSTM(
        node_ids, adj_norm, "1405", seed=42, initial_records=target_data.initial_records
    )
    res_gcn = runner.run_replay(gcn, target_data, mode="target_only", seed=42)
    print(
        f"[Pilot] Basic GCN-LSTM: MAE={res_gcn.mae_kwh:.4f} kWh, Scored={res_gcn.scored_days}, Time={res_gcn.total_seconds:.2f}s"
    )

    print("=== PILOT RUN COMPLETE ===")


def run_full_benchmark(config: BenchmarkConfig) -> None:
    """Run all 172 model-target-seed benchmark rows."""
    print("==========================================================")
    print("STARTING FULL CYBER URBANEV BASELINE BENCHMARK (Issue #95)")
    print("==========================================================")
    total_start = time.perf_counter()

    runner = BenchmarkRunner(config)

    # Clean runs.csv if starting fresh
    if config.runs_csv_path.is_file():
        config.runs_csv_path.unlink()

    # Preload target data for all 4 targets
    print("\n--- 1. Loading Replay Data for 4 Target Stations ---")
    targets_data = {t: load_target_replay_data(config.input_root, t) for t in config.targets}
    for t, td in targets_data.items():
        print(
            f"Target {t}: initial={td.initial_trainable_count}, scale={td.p95_scale:.2f} kWh, scheduled={len(td.schedule)}"
        )

    # Load spatial distance matrix
    adj_norm, node_ids = load_distance_matrix(config.raw_zip_path, config.targets)

    # ----------------------------------------------------
    # Phase A: Statistical Deterministic Baselines (16 rows)
    # ----------------------------------------------------
    print("\n--- Phase A: Statistical Baselines (16 rows) ---")
    for t_id in config.targets:
        td = targets_data[t_id]

        # 1. Daily Naive
        dn = DailyNaive(td.initial_records)
        s_dn = runner.run_replay(dn, td, mode="target_only", seed=None)
        append_summary_to_csv(s_dn, config.runs_csv_path)
        print(
            f"[Daily Naive] Target {t_id}: MAE={s_dn.mae_kwh:.4f} kWh, RMSE={s_dn.rmse_kwh:.4f} kWh"
        )

        # 2. Seasonal Naive
        sn = SeasonalNaive(td.initial_records)
        s_sn = runner.run_replay(sn, td, mode="target_only", seed=None)
        append_summary_to_csv(s_sn, config.runs_csv_path)
        print(
            f"[Seasonal Naive] Target {t_id}: MAE={s_sn.mae_kwh:.4f} kWh, RMSE={s_sn.rmse_kwh:.4f} kWh"
        )

        # 3. Ridge
        ridge = RidgeBaseline(
            alpha=config.classical_hp.ridge_alpha, initial_records=td.initial_records
        )
        s_ridge = runner.run_replay(ridge, td, mode="target_only", seed=None)
        append_summary_to_csv(s_ridge, config.runs_csv_path)
        print(
            f"[Ridge] Target {t_id}: MAE={s_ridge.mae_kwh:.4f} kWh, RMSE={s_ridge.rmse_kwh:.4f} kWh"
        )

        # 4. SARIMA
        sarima = SARIMABaseline(
            order=config.classical_hp.sarima_order,
            seasonal_order=config.classical_hp.sarima_seasonal_order,
            maxiter=config.classical_hp.sarima_maxiter,
            initial_records=td.initial_records,
        )
        s_sarima = runner.run_replay(sarima, td, mode="target_only", seed=None)
        append_summary_to_csv(s_sarima, config.runs_csv_path)
        print(
            f"[SARIMA] Target {t_id}: MAE={s_sarima.mae_kwh:.4f} kWh, RMSE={s_sarima.rmse_kwh:.4f} kWh"
        )

    # ----------------------------------------------------
    # Phase B: Classical ML Baselines (RF, XGBoost x 3 seeds) (24 rows)
    # ----------------------------------------------------
    print("\n--- Phase B: Classical Machine Learning Baselines (24 rows) ---")
    for seed in config.seeds:
        for t_id in config.targets:
            td = targets_data[t_id]

            # Random Forest
            rf = RandomForestBaseline(
                n_estimators=config.classical_hp.rf_n_estimators,
                max_depth=config.classical_hp.rf_max_depth,
                seed=seed,
                initial_records=td.initial_records,
            )
            s_rf = runner.run_replay(rf, td, mode="target_only", seed=seed)
            append_summary_to_csv(s_rf, config.runs_csv_path)
            print(f"[Random Forest] Target {t_id} (Seed {seed}): MAE={s_rf.mae_kwh:.4f} kWh")

            # XGBoost
            xgb_m = XGBoostBaseline(
                n_estimators=config.classical_hp.xgb_n_estimators,
                max_depth=config.classical_hp.xgb_max_depth,
                learning_rate=config.classical_hp.xgb_lr,
                seed=seed,
                initial_records=td.initial_records,
            )
            s_xgb = runner.run_replay(xgb_m, td, mode="target_only", seed=seed)
            append_summary_to_csv(s_xgb, config.runs_csv_path)
            print(f"[XGBoost] Target {t_id} (Seed {seed}): MAE={s_xgb.mae_kwh:.4f} kWh")

    # ----------------------------------------------------
    # Phase C: Pretraining Source Models for Neural Backbones (15 models)
    # ----------------------------------------------------
    print("\n--- Phase C: Pretraining Neural Backbones on 65,888 Source Examples ---")
    source_ds, source_count = load_source_dataset(config.input_root)
    print(f"Loaded {source_count} Source examples.")

    source_ckpts: dict[tuple[str, int], tuple[Path, float]] = {}
    for backbone in ("MLP", "GRU", "LSTM", "TCN", "TimeXer"):
        for seed in config.seeds:
            print(f"Pretraining {backbone} (Seed {seed}) on Source...")
            ckpt_path, elapsed = train_source_model(backbone, seed, source_ds, config)
            source_ckpts[(backbone, seed)] = (ckpt_path, elapsed)
            print(f"Finished {backbone} (Seed {seed}) in {elapsed:.2f}s -> {ckpt_path.name}")

    # ----------------------------------------------------
    # Phase D: Neural Target-Only and Transfer Runs (120 rows)
    # ----------------------------------------------------
    print("\n--- Phase D: Neural Target-Only & Transfer Replays (120 rows) ---")
    for backbone in ("MLP", "GRU", "LSTM", "TCN", "TimeXer"):
        for seed in config.seeds:
            ckpt_path, src_time = source_ckpts[(backbone, seed)]

            for t_id in config.targets:
                td = targets_data[t_id]

                # 1. Target-Only
                net_to, adapt_to = build_neural_forecaster(
                    backbone, "target_only", seed, t_id, td.initial_records, config
                )
                s_to = runner.run_replay(
                    net_to, td, mode="target_only", seed=seed, target_adapt_seconds=adapt_to
                )
                append_summary_to_csv(s_to, config.runs_csv_path)
                print(
                    f"[{backbone} Target-Only] Target {t_id} (Seed {seed}): MAE={s_to.mae_kwh:.4f} kWh"
                )

                # 2. Transfer (Source -> Target Fine-tuning)
                net_tf, adapt_tf = build_neural_forecaster(
                    backbone,
                    "transfer",
                    seed,
                    t_id,
                    td.initial_records,
                    config,
                    source_ckpt_path=ckpt_path,
                )
                s_tf = runner.run_replay(
                    net_tf,
                    td,
                    mode="transfer",
                    seed=seed,
                    source_fit_seconds=src_time / len(config.targets),  # amortized per target
                    target_adapt_seconds=adapt_tf,
                )
                append_summary_to_csv(s_tf, config.runs_csv_path)
                print(
                    f"[{backbone} Transfer] Target {t_id} (Seed {seed}): MAE={s_tf.mae_kwh:.4f} kWh"
                )

    # ----------------------------------------------------
    # Phase E: Basic GCN-LSTM Spatial Comparator (12 rows)
    # ----------------------------------------------------
    print("\n--- Phase E: Basic GCN-LSTM Spatial Comparator (12 rows) ---")
    for seed in config.seeds:
        for t_id in config.targets:
            td = targets_data[t_id]
            gcn = BasicGCNLSTM(
                node_ids=node_ids,
                adj_norm=adj_norm,
                target_id=t_id,
                seed=seed,
                initial_records=td.initial_records,
            )
            s_gcn = runner.run_replay(gcn, td, mode="target_only", seed=seed)
            append_summary_to_csv(s_gcn, config.runs_csv_path)
            print(f"[Basic GCN-LSTM] Target {t_id} (Seed {seed}): MAE={s_gcn.mae_kwh:.4f} kWh")

    total_wall = time.perf_counter() - total_start
    print("\n==========================================================")
    print(f"FULL BENCHMARK COMPLETED IN {total_wall / 60:.2f} MINUTES")
    print(f"Results recorded in: {config.runs_csv_path}")
    print("==========================================================")

    # Create SHA-256 manifest of artifacts
    create_artifact_manifest(config)


def create_artifact_manifest(config: BenchmarkConfig) -> None:
    """Generate SHA-256 checksum manifest of all predictions and models."""
    manifest_records = {}
    for p in sorted(config.output_dir.glob("*.json")):
        with open(p, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        manifest_records[p.name] = {"sha256": h, "bytes": p.stat().st_size}

    if config.runs_csv_path.is_file():
        with open(config.runs_csv_path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        manifest_records["runs.csv"] = {
            "sha256": h,
            "bytes": config.runs_csv_path.stat().st_size,
        }

    manifest_path = config.output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_records, f, indent=2)
    print(f"Wrote checksum manifest to {manifest_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cyber UrbanEV Baseline Benchmark CLI")
    parser.add_argument("--pilot", action="store_true", help="Run quick 1-target pilot")
    parser.add_argument("--all", action="store_true", help="Run full 172-row benchmark")
    args = parser.parse_args()

    config = BenchmarkConfig()
    if args.pilot:
        run_pilot(config)
    elif args.all:
        run_full_benchmark(config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
