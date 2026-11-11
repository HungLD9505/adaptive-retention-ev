"""Unified CLI orchestrator for Cyber UrbanEV Baseline Benchmark (Issue #95)."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import platform
import subprocess
import sys
import time
import tracemalloc
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import torch

from experiments.member_studies.cyber_baselines.config import (
    REPO_ROOT,
    BenchmarkConfig,
)
from experiments.member_studies.cyber_baselines.data import (
    load_all_targets_history_lookup,
    load_distance_matrix,
    load_source_dataset,
    load_target_replay_data,
    select_graph_nodes,
)
from experiments.member_studies.cyber_baselines.models.base import BaseForecaster
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
    RunSummary,
    append_summary_to_csv,
)
from experiments.member_studies.cyber_baselines.training import (
    build_neural_forecaster,
    train_source_model,
)

VN_TZ = timezone(timedelta(hours=7))
NEURAL_BACKBONES = ("MLP", "GRU", "LSTM", "TCN", "TimeXer")


def _now_vn() -> str:
    return datetime.now(VN_TZ).isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _process_memory_mb() -> dict[str, float | None]:
    """Current and lifetime-peak process working set (Windows) or max RSS (POSIX), in MiB."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.K32GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PMC),
            wintypes.DWORD,
        ]
        counters = PMC()
        counters.cb = ctypes.sizeof(PMC)
        ok = kernel32.K32GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        )
        if ok:
            return {
                "working_set_mib": counters.WorkingSetSize / 2**20,
                "peak_working_set_mib": counters.PeakWorkingSetSize / 2**20,
            }
        return {"working_set_mib": None, "peak_working_set_mib": None}
    import resource

    peak_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {"working_set_mib": None, "peak_working_set_mib": peak_kib / 1024}


def _git_identity() -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty_paths": [line for line in git("status", "--porcelain").splitlines() if line],
    }


def _environment_record(config: BenchmarkConfig) -> dict[str, Any]:
    versions: dict[str, str | None] = {}
    for mod in ("numpy", "pandas", "torch", "sklearn", "xgboost", "statsmodels"):
        try:
            versions[mod] = __import__(mod).__version__
        except Exception:  # noqa: BLE001 - optional dependency
            versions[mod] = None
    input_manifest = config.input_root / "manifest.json"
    return {
        "recorded_at_vn": _now_vn(),
        "run_tag": config.run_tag,
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "torch_threads": torch.get_num_threads(),
        "packages": versions,
        "git": _git_identity(),
        # Byte identity of the executed study code (independent of commit state)
        "code_sha256": {
            p.relative_to(REPO_ROOT).as_posix(): _sha256_file(p)
            for p in sorted(
                (REPO_ROOT / "experiments" / "member_studies" / "cyber_baselines").rglob("*.py")
            )
        },
        "input_manifest": {
            "path": input_manifest.relative_to(REPO_ROOT).as_posix(),
            "sha256": _sha256_file(input_manifest) if input_manifest.is_file() else None,
        },
        "config": json.loads(json.dumps(dataclasses.asdict(config), default=str)),
        "command": sys.argv,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(payload, indent=2, default=str).encode("utf-8"))


def _append_log(path: Path, record: dict[str, Any]) -> None:
    with open(path, "ab") as f:
        f.write((json.dumps(record, default=str) + "\n").encode("utf-8"))


def _fmt(v: float | None) -> str:
    return f"{v:.4f}" if v is not None else "null"


def _graph_setup(
    config: BenchmarkConfig,
) -> tuple[list[str], Any, dict[tuple[str, str], list[list[float]]], dict[str, Any]]:
    node_ids, lock = select_graph_nodes(
        config.raw_zip_path, config.input_root, config.targets, config.graph_support_k
    )
    adj_norm, node_ids = load_distance_matrix(config.raw_zip_path, tuple(node_ids))
    hist_lookup = load_all_targets_history_lookup(config.input_root, node_ids)
    lock["adjacency"] = (
        "Gaussian kernel exp(-(d/sigma)^2), sigma=std(positive distances), +I, D^-1/2 A D^-1/2"
    )
    lock["history_records_loaded"] = len(hist_lookup)
    return node_ids, adj_norm, hist_lookup, lock


def run_pilot(config: BenchmarkConfig) -> None:
    """One-seed pilot on target 1405 for all 12 model families with runtime/memory records."""
    print(f"=== PILOT {config.run_tag} (Target 1405, Seed 42) ===")
    config = dataclasses.replace(
        config,
        output_dir=config.output_dir / "pilot",
        runs_csv_path=config.output_dir / "pilot" / "pilot_runs.csv",
    )
    if config.runs_csv_path.is_file():
        raise FileExistsError(f"Refusing to overwrite existing pilot ledger {config.runs_csv_path}")
    runner = BenchmarkRunner(config)
    td = load_target_replay_data(config.input_root, "1405")
    node_ids, adj_norm, hist_lookup, graph_lock = _graph_setup(config)
    source_ckpts = {
        bb: config.checkpoint_dir / f"{bb.lower()}_source_seed42.pt" for bb in NEURAL_BACKBONES
    }

    factories: list[tuple[str, str, Callable[[], tuple[BaseForecaster, float]]]] = [
        ("Daily Naive", "target_only", lambda: (DailyNaive(td.initial_records), 0.0)),
        ("Seasonal Naive", "target_only", lambda: (SeasonalNaive(td.initial_records), 0.0)),
        (
            "Ridge",
            "target_only",
            lambda: (RidgeBaseline(config.classical_hp.ridge_alpha, td.initial_records), 0.0),
        ),
        (
            "SARIMA",
            "target_only",
            lambda: (
                SARIMABaseline(
                    order=config.classical_hp.sarima_order,
                    seasonal_order=config.classical_hp.sarima_seasonal_order,
                    maxiter=config.classical_hp.sarima_maxiter,
                    initial_records=td.initial_records,
                ),
                0.0,
            ),
        ),
        (
            "Random Forest",
            "target_only",
            lambda: (
                RandomForestBaseline(
                    n_estimators=config.classical_hp.rf_n_estimators,
                    max_depth=config.classical_hp.rf_max_depth,
                    seed=42,
                    initial_records=td.initial_records,
                ),
                0.0,
            ),
        ),
        (
            "XGBoost",
            "target_only",
            lambda: (
                XGBoostBaseline(
                    n_estimators=config.classical_hp.xgb_n_estimators,
                    max_depth=config.classical_hp.xgb_max_depth,
                    learning_rate=config.classical_hp.xgb_lr,
                    seed=42,
                    initial_records=td.initial_records,
                ),
                0.0,
            ),
        ),
    ]
    for bb in NEURAL_BACKBONES:
        factories.append(
            (
                bb,
                "target_only",
                lambda bb=bb: build_neural_forecaster(
                    bb, "target_only", 42, "1405", td.initial_records, config
                ),
            )
        )
        if source_ckpts[bb].is_file():
            factories.append(
                (
                    bb,
                    "transfer",
                    lambda bb=bb: build_neural_forecaster(
                        bb,
                        "transfer",
                        42,
                        "1405",
                        td.initial_records,
                        config,
                        source_ckpt_path=source_ckpts[bb],
                    ),
                )
            )
    factories.append(
        (
            "Basic GCN-LSTM",
            "target_only",
            lambda: (
                BasicGCNLSTM(
                    node_ids,
                    adj_norm,
                    "1405",
                    seed=42,
                    initial_records=td.initial_records,
                    history_lookup=hist_lookup,
                ),
                0.0,
            ),
        )
    )

    records = []
    for name, mode, factory in factories:
        seed = None if name in ("Daily Naive", "Seasonal Naive", "Ridge", "SARIMA") else 42
        tracemalloc.start()
        t0 = time.perf_counter()
        try:
            model, adapt_s = factory()
            summary = runner.run_replay(
                model, td, mode=mode, seed=seed, target_adapt_seconds=adapt_s
            )
            status, error = "ok", None
        except Exception as e:  # noqa: BLE001 - pilot records failures instead of hiding them
            summary, status, error = None, "failed", repr(e)
        wall = time.perf_counter() - t0
        _, py_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rec = {
            "model": name,
            "mode": mode,
            "station_id": "1405",
            "seed": seed,
            "status": status,
            "error": error,
            "wall_seconds_incl_construction": wall,
            "tracemalloc_peak_mib": py_peak / 2**20,
            **_process_memory_mb(),
        }
        if summary is not None:
            rec.update(
                {
                    "run_id": summary.run_id,
                    "scored_days": summary.scored_days,
                    "mae_kwh": summary.mae_kwh,
                    "param_count": summary.param_count,
                }
            )
            append_summary_to_csv(summary, config.runs_csv_path)
        records.append(rec)
        print(f"[Pilot] {name} ({mode}): {status} MAE={_fmt(rec.get('mae_kwh'))} {wall:.2f}s")

    _write_json(
        config.output_dir / "pilot_record.json",
        {
            "environment": _environment_record(config),
            "graph_lock": graph_lock,
            "note": "tracemalloc tracks Python/NumPy heap only (not PyTorch's CPU allocator); "
            "process peak working set is cumulative over the pilot process lifetime.",
            "runs": records,
        },
    )
    print("=== PILOT COMPLETE ===")


def run_full_benchmark(config: BenchmarkConfig) -> None:
    """Run all 172 model-target-seed rows into a fresh versioned output root."""
    print("==========================================================")
    print(f"FULL CYBER URBANEV BASELINE BENCHMARK {config.run_tag} (Issue #95)")
    print("==========================================================")
    total_start = time.perf_counter()

    # Never overwrite or delete earlier evidence: a new execution needs a new run tag/root.
    existing = list(config.output_dir.glob("*_predictions.json"))
    if config.runs_csv_path.is_file() or existing:
        raise FileExistsError(
            f"Refusing to overwrite run tag {config.run_tag!r}: {config.runs_csv_path} or "
            f"{len(existing)} prediction files already exist. Use a new run tag."
        )
    config = dataclasses.replace(config, save_fitted=True)
    runner = BenchmarkRunner(config)
    log_path = config.output_dir / "execution_log.jsonl"
    _write_json(config.output_dir / "environment.json", _environment_record(config))

    def record(summary: RunSummary, phase: str) -> None:
        append_summary_to_csv(summary, config.runs_csv_path)
        _append_log(
            log_path,
            {
                "finished_at_vn": _now_vn(),
                "phase": phase,
                "run_id": summary.run_id,
                "scored_days": summary.scored_days,
                "mae_kwh": summary.mae_kwh,
                "total_seconds": summary.total_seconds,
                **_process_memory_mb(),
            },
        )
        print(
            f"[{summary.model} {summary.mode}] {summary.station_id} seed={summary.seed}: "
            f"MAE={_fmt(summary.mae_kwh)} kWh RMSE={_fmt(summary.rmse_kwh)} kWh"
        )

    print("\n--- 1. Loading Replay Data for 4 Target Stations ---")
    targets_data = {t: load_target_replay_data(config.input_root, t) for t in config.targets}
    for t, td in targets_data.items():
        print(
            f"Target {t}: initial={td.initial_trainable_count}, scale={td.p95_scale:.2f} kWh, "
            f"scheduled={len(td.schedule)}"
        )

    # Phase A: Statistical Deterministic Baselines (16 rows)
    print("\n--- Phase A: Statistical Baselines (16 rows) ---")
    for t_id in config.targets:
        td = targets_data[t_id]
        record(runner.run_replay(DailyNaive(td.initial_records), td), "A")
        record(runner.run_replay(SeasonalNaive(td.initial_records), td), "A")
        ridge = RidgeBaseline(
            alpha=config.classical_hp.ridge_alpha, initial_records=td.initial_records
        )
        record(runner.run_replay(ridge, td), "A")
        sarima = SARIMABaseline(
            order=config.classical_hp.sarima_order,
            seasonal_order=config.classical_hp.sarima_seasonal_order,
            maxiter=config.classical_hp.sarima_maxiter,
            initial_records=td.initial_records,
        )
        record(runner.run_replay(sarima, td), "A")

    # Phase B: Classical ML Baselines (RF, XGBoost x 3 seeds) (24 rows)
    print("\n--- Phase B: Classical Machine Learning Baselines (24 rows) ---")
    for seed in config.seeds:
        for t_id in config.targets:
            td = targets_data[t_id]
            rf = RandomForestBaseline(
                n_estimators=config.classical_hp.rf_n_estimators,
                max_depth=config.classical_hp.rf_max_depth,
                seed=seed,
                initial_records=td.initial_records,
            )
            record(runner.run_replay(rf, td, seed=seed), "B")
            xgb_m = XGBoostBaseline(
                n_estimators=config.classical_hp.xgb_n_estimators,
                max_depth=config.classical_hp.xgb_max_depth,
                learning_rate=config.classical_hp.xgb_lr,
                seed=seed,
                initial_records=td.initial_records,
            )
            record(runner.run_replay(xgb_m, td, seed=seed), "B")

    # Phase C: Source trajectories (15 = 5 backbones x 3 seeds), reused across targets
    print("\n--- Phase C: Source Trajectories for Neural Backbones ---")
    source_ckpts: dict[tuple[str, int], tuple[Path, float]] = {}
    source_ds = None
    for backbone in NEURAL_BACKBONES:
        for seed in config.seeds:
            ckpt_path = config.checkpoint_dir / f"{backbone.lower()}_source_seed{seed}.pt"
            if ckpt_path.is_file():
                ckpt_data = torch.load(ckpt_path, map_location="cpu", weights_only=False)
                if "wall_seconds" not in ckpt_data:
                    raise ValueError(f"{ckpt_path} lacks a recorded wall_seconds timer")
                elapsed = float(ckpt_data["wall_seconds"])
                print(f"Reusing Source checkpoint {ckpt_path.name} ({elapsed:.2f}s recorded)")
            else:
                if source_ds is None:
                    source_ds, source_count = load_source_dataset(config.input_root)
                    print(f"Loaded {source_count} Source examples.")
                ckpt_path, elapsed = train_source_model(backbone, seed, source_ds, config)
                print(f"Trained {backbone} seed {seed} in {elapsed:.2f}s -> {ckpt_path.name}")
            source_ckpts[(backbone, seed)] = (ckpt_path, elapsed)
            _append_log(
                log_path,
                {
                    "phase": "C",
                    "source_checkpoint": ckpt_path.name,
                    "sha256": _sha256_file(ckpt_path),
                    "recorded_wall_seconds": elapsed,
                },
            )

    # Phase D: Neural Target-Only and Transfer Runs (120 rows)
    print("\n--- Phase D: Neural Target-Only & Transfer Replays (120 rows) ---")
    for backbone in NEURAL_BACKBONES:
        for seed in config.seeds:
            ckpt_path, src_time = source_ckpts[(backbone, seed)]
            for t_id in config.targets:
                td = targets_data[t_id]
                net_to, adapt_to = build_neural_forecaster(
                    backbone, "target_only", seed, t_id, td.initial_records, config
                )
                record(
                    runner.run_replay(
                        net_to, td, mode="target_only", seed=seed, target_adapt_seconds=adapt_to
                    ),
                    "D",
                )
                net_tf, adapt_tf = build_neural_forecaster(
                    backbone,
                    "transfer",
                    seed,
                    t_id,
                    td.initial_records,
                    config,
                    source_ckpt_path=ckpt_path,
                )
                record(
                    runner.run_replay(
                        net_tf,
                        td,
                        mode="transfer",
                        seed=seed,
                        source_fit_seconds=src_time / len(config.targets),  # amortized
                        target_adapt_seconds=adapt_tf,
                    ),
                    "D",
                )

    # Phase E: Basic GCN-LSTM Spatial Comparator (12 rows)
    print("\n--- Phase E: Basic GCN-LSTM Spatial Comparator (12 rows) ---")
    node_ids, adj_norm, hist_lookup, graph_lock = _graph_setup(config)
    _write_json(config.output_dir / "graph_lock.json", graph_lock)
    print(f"Graph nodes ({len(node_ids)}): {node_ids}")
    for seed in config.seeds:
        for t_id in config.targets:
            td = targets_data[t_id]
            gcn = BasicGCNLSTM(
                node_ids=node_ids,
                adj_norm=adj_norm,
                target_id=t_id,
                seed=seed,
                initial_records=td.initial_records,
                history_lookup=hist_lookup,
            )
            record(runner.run_replay(gcn, td, seed=seed), "E")

    total_wall = time.perf_counter() - total_start
    _append_log(
        log_path, {"phase": "end", "total_wall_seconds": total_wall, **_process_memory_mb()}
    )
    print(f"\nFULL BENCHMARK COMPLETED IN {total_wall / 60:.2f} MINUTES -> {config.runs_csv_path}")
    create_artifact_manifest(config)


def create_artifact_manifest(config: BenchmarkConfig) -> None:
    """SHA-256 manifest over the exact on-disk bytes of every artifact in the run root.

    Keys are POSIX paths relative to the repository root, so the manifest can be checked
    from any checkout or from the extracted external bundle.
    """
    files: list[Path] = [
        p
        for p in sorted(config.output_dir.rglob("*"))
        if p.is_file() and p.name != "manifest.json" and "pilot" not in p.parts
    ]
    if config.checkpoint_dir.is_dir():
        files += sorted(config.checkpoint_dir.glob("*.pt"))
    if config.runs_csv_path.is_file():
        files.append(config.runs_csv_path)

    manifest_records = {
        p.resolve().relative_to(REPO_ROOT).as_posix(): {
            "sha256": _sha256_file(p),
            "bytes": p.stat().st_size,
        }
        for p in files
    }
    manifest_path = config.output_dir / "manifest.json"
    _write_json(manifest_path, manifest_records)
    print(f"Wrote checksum manifest with {len(manifest_records)} entries to {manifest_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cyber UrbanEV Baseline Benchmark CLI")
    parser.add_argument("--pilot", action="store_true", help="Run one-seed pilot on target 1405")
    parser.add_argument("--all", action="store_true", help="Run full 172-row benchmark")
    parser.add_argument("--manifest", action="store_true", help="Rebuild manifest only")
    args = parser.parse_args()

    config = BenchmarkConfig()
    if args.pilot:
        run_pilot(config)
    elif args.all:
        run_full_benchmark(config)
    elif args.manifest:
        create_artifact_manifest(config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
