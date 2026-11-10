"""Configuration and constants for Cyber UrbanEV Baseline Benchmark (Issue #95)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Repository root and data paths
REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT_ROOT = REPO_ROOT / "data" / "inputs" / "issue18-input-handoff-v1-20261019" / "urbanev-SZH-14d"
RAW_ZIP_PATH = REPO_ROOT / "data" / "raw" / "urbanev" / "official_2026_05_11" / "UrbanEVDataset.zip"

OUTPUT_DIR = REPO_ROOT / "experiments" / "member_studies" / "cyber_baselines" / "artifacts"
CHECKPOINT_DIR = REPO_ROOT / "experiments" / "member_studies" / "cyber_baselines" / "checkpoints"
RUNS_CSV_PATH = REPO_ROOT / "experiments" / "member_studies" / "cyber_baselines" / "runs.csv"
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "member-cyber-baselines.md"

# Development target stations and their fixed initial budgets & scalers
TARGET_IDS = ("1405", "2152", "1153", "1693")

TARGET_METADATA = {
    "1405": {
        "initial_trainable": 4,
        "scheduled_forecasts": 90,
        "p95_scale": 43.86666666666667,
    },
    "2152": {
        "initial_trainable": 12,
        "scheduled_forecasts": 59,
        "p95_scale": 42.0,
    },
    "1153": {
        "initial_trainable": 13,
        "scheduled_forecasts": 59,
        "p95_scale": 56.0,
    },
    "1693": {
        "initial_trainable": 13,
        "scheduled_forecasts": 59,
        "p95_scale": 14.0,
    },
}

# Seeds for stochastic models
BENCHMARK_SEEDS = (42, 43, 44)

# Models in non-graph benchmark
STATISTICAL_MODELS = ("Daily Naive", "Seasonal Naive", "Ridge", "SARIMA")
CLASSICAL_MODELS = ("Random Forest", "XGBoost")
NEURAL_MODELS = ("MLP", "GRU", "LSTM", "TCN", "TimeXer")
GRAPH_MODELS = ("Basic GCN-LSTM",)

ALL_MODELS = STATISTICAL_MODELS + CLASSICAL_MODELS + NEURAL_MODELS + GRAPH_MODELS


@dataclass(frozen=True)
class TrainingHyperparameters:
    """Hyperparameters for neural source pretraining and target fine-tuning."""

    source_batch_size: int = 256
    source_epochs: int = 3
    source_lr: float = 1e-3

    target_batch_size: int = 4
    target_adapt_epochs: int = 3
    target_adapt_lr: float = 5e-4

    target_update_epochs: int = 1
    target_update_lr: float = 5e-4


@dataclass(frozen=True)
class ClassicalHyperparameters:
    """Hyperparameters for classical / ML models."""

    ridge_alpha: float = 1.0
    rf_n_estimators: int = 100
    rf_max_depth: int = 10
    xgb_n_estimators: int = 100
    xgb_max_depth: int = 5
    xgb_lr: float = 0.1
    sarima_order: tuple[int, int, int] = (1, 0, 1)
    sarima_seasonal_order: tuple[int, int, int, int] = (1, 0, 0, 24)
    sarima_maxiter: int = 25


@dataclass
class BenchmarkConfig:
    """Full benchmark configuration."""

    input_root: Path = INPUT_ROOT
    raw_zip_path: Path = RAW_ZIP_PATH
    output_dir: Path = OUTPUT_DIR
    checkpoint_dir: Path = CHECKPOINT_DIR
    runs_csv_path: Path = RUNS_CSV_PATH
    targets: tuple[str, ...] = TARGET_IDS
    seeds: tuple[int, ...] = BENCHMARK_SEEDS
    training_hp: TrainingHyperparameters = field(default_factory=TrainingHyperparameters)
    classical_hp: ClassicalHyperparameters = field(default_factory=ClassicalHyperparameters)
