"""Data loading utilities for Cyber UrbanEV Baseline Benchmark (Issue #95)."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import TensorDataset

from experiments.member_studies.cyber_baselines.config import (
    INPUT_ROOT,
    RAW_ZIP_PATH,
    TARGET_IDS,
    TARGET_METADATA,
)


@dataclass
class TargetReplayData:
    """Replay trajectory data for one target station."""

    entity_id: str
    p95_scale: float
    initial_trainable_count: int
    initial_records: list[dict[str, Any]]
    schedule: list[dict[str, Any]]
    forecasts: dict[str, dict[str, Any]]  # origin_iso -> forecast_record
    labels: dict[str, dict[str, Any]]  # origin_iso -> label_record


def load_source_dataset(
    input_root: Path = INPUT_ROOT,
) -> tuple[TensorDataset, int]:
    """Load all 65,888 Source pretraining examples into a TensorDataset.

    Returns:
        (dataset, count): TensorDataset containing (x_hist, c_future, y_scaled)
        and the verified count of source records.
    """
    path = input_root / "training.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"Missing training.jsonl at {path}")

    x_list: list[list[list[float]]] = []
    c_list: list[list[list[float]]] = []
    y_list: list[list[float]] = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            if record.get("role") == "source":
                fc = record["forecast"]
                x_list.append(fc["x_hist"])
                c_list.append(fc["c_future"])
                y_list.append(record["y_scaled"])

    count = len(x_list)
    if count != 65888:
        raise ValueError(
            f"Expected exactly 65,888 Source records per Issue #95 invariant, found {count}"
        )

    x_tensor = torch.tensor(x_list, dtype=torch.float32)
    c_tensor = torch.tensor(c_list, dtype=torch.float32)
    y_tensor = torch.tensor(y_list, dtype=torch.float32)

    return TensorDataset(x_tensor, c_tensor, y_tensor), count


def load_target_initial_prefix(
    input_root: Path = INPUT_ROOT,
    target_id: str = "1405",
) -> list[dict[str, Any]]:
    """Load initial trainable records for a target from training.jsonl."""
    path = input_root / "training.jsonl"
    records: list[dict[str, Any]] = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("role") == "development":
                fc = rec["forecast"]
                if fc["identity"][2] == target_id:
                    records.append(rec)

    expected = TARGET_METADATA[target_id]["initial_trainable"]
    if len(records) != expected:
        raise ValueError(
            f"Target {target_id} expected {expected} initial records, found {len(records)}"
        )
    return records


def load_target_replay_data(
    input_root: Path = INPUT_ROOT,
    target_id: str = "1405",
) -> TargetReplayData:
    """Load full replay inputs and gated labels for a target station."""
    initial_records = load_target_initial_prefix(input_root, target_id)
    p95_scale = TARGET_METADATA[target_id]["p95_scale"]
    initial_count = TARGET_METADATA[target_id]["initial_trainable"]

    # 1. Schedule
    schedule: list[dict[str, Any]] = []
    with open(input_root / "schedule.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            s = json.loads(line)
            if s["identity"][2] == target_id:
                schedule.append(s)

    schedule.sort(key=lambda s: s["origin"])
    if len(schedule) != 90:
        raise ValueError(f"Expected 90 scheduled days for {target_id}, got {len(schedule)}")

    # 2. Forecasts
    forecasts: dict[str, dict[str, Any]] = {}
    with open(input_root / "forecasts.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["identity"][2] == target_id:
                forecasts[r["origin"]] = r

    # 3. Labels
    labels: dict[str, dict[str, Any]] = {}
    with open(input_root / "labels.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["identity"][2] == target_id:
                labels[r["origin"]] = r

    return TargetReplayData(
        entity_id=target_id,
        p95_scale=p95_scale,
        initial_trainable_count=initial_count,
        initial_records=initial_records,
        schedule=schedule,
        forecasts=forecasts,
        labels=labels,
    )


def load_distance_matrix(
    raw_zip_path: Path = RAW_ZIP_PATH,
    target_ids: tuple[str, ...] = TARGET_IDS,
    sigma: float | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Extract station_distance.csv and compute normalized adjacency matrix.

    Constructs normalized spatial adjacency matrix A_hat = D^{-1/2} A D^{-1/2}
    where A_ij = exp(-d_ij^2 / sigma^2) with self-loops.
    """
    with zipfile.ZipFile(raw_zip_path) as z:
        inner_path = "UrbanEVDataset/20220901-20230228_station-raw/station_distance.csv"
        with z.open(inner_path) as f:
            df = pd.read_csv(f)

    # Filter for target nodes
    sub_df = df[df["ID"].astype(str).isin(target_ids)].copy()
    sub_df["ID"] = sub_df["ID"].astype(str)
    sub_df = sub_df.sort_values("ID")
    node_ids = list(sub_df["ID"])

    # Extract distances between these nodes
    dist_matrix = sub_df[node_ids].to_numpy(dtype=float)

    if sigma is None:
        # Standard deviation of nonzero off-diagonal distances
        off_diag = dist_matrix[dist_matrix > 0]
        sigma = float(np.std(off_diag)) if len(off_diag) > 0 else 10000.0

    # Gaussian kernel
    adj = np.exp(-((dist_matrix / sigma) ** 2))
    # Add self loops
    np.fill_diagonal(adj, 1.0)

    # Degree normalization D^{-1/2} A D^{-1/2}
    deg = np.sum(adj, axis=1)
    deg_inv_sqrt = np.zeros_like(deg)
    mask = deg > 0
    deg_inv_sqrt[mask] = np.power(deg[mask], -0.5)
    d_mat = np.diag(deg_inv_sqrt)
    normalized_adj = d_mat @ adj @ d_mat

    return normalized_adj, node_ids
