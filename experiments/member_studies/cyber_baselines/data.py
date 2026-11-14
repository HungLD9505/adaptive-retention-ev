"""Data loading utilities for Cyber UrbanEV Baseline Benchmark (Issue #95)."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
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


STATION_DISTANCE_CSV = "UrbanEVDataset/20220901-20230228_station-raw/station_distance.csv"


def _read_distance_rows(raw_zip_path: Path) -> tuple[list[str], dict[str, list[str]]]:
    with zipfile.ZipFile(raw_zip_path) as z:
        with z.open(STATION_DISTANCE_CSV) as f:
            reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8"))
            header = next(reader)
            id_idx = header.index("ID")
            rows = {str(row[id_idx]): row for row in reader}
    return header, rows


def select_graph_nodes(
    raw_zip_path: Path = RAW_ZIP_PATH,
    input_root: Path = INPUT_ROOT,
    target_ids: tuple[str, ...] = TARGET_IDS,
    support_k: int = 3,
) -> tuple[list[str], dict[str, Any]]:
    """Lock the GCN-LSTM node set: scored targets plus their K nearest Development supports.

    Locked rule (run tag v3):
    - Candidate support nodes are other ``development``-role entities in ``entities.jsonl``
      that appear in ``station_distance.csv``. Final-role and Source-role stations are excluded
      (no Final data is touched; Source stations have no replay-window histories).
    - For each scored target, the ``support_k`` nearest candidates by geographic distance
      (ties broken by station ID) are added. Node order is sorted station ID.
    - Support nodes contribute only their predictor-visible 24h ``x_hist`` at the same origin;
      their labels are never decoded or trained on.
    """
    roles: dict[str, str] = {}
    with open(input_root / "entities.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            roles[str(e["identity"][2])] = e["role"]

    header, rows = _read_distance_rows(raw_zip_path)
    col = {c: i for i, c in enumerate(header)}
    targets = [str(t) for t in target_ids]
    candidates = sorted(
        s for s, r in roles.items() if r == "development" and s in col and s not in targets
    )

    lock: dict[str, Any] = {
        "rule": f"targets + {support_k} nearest development-role stations per target",
        "distance_source": STATION_DISTANCE_CSV,
        "excluded_roles": ["final", "source"],
        "support_k": support_k,
        "neighbors": {},
    }
    nodes = set(targets)
    for t in targets:
        row = rows[t]
        ranked = sorted((float(row[col[c]]), c) for c in candidates)[:support_k]
        lock["neighbors"][t] = [{"station_id": c, "distance_m": d} for d, c in ranked]
        nodes.update(c for _, c in ranked)

    node_ids = sorted(nodes)
    lock["node_ids"] = node_ids
    return node_ids, lock


def load_all_targets_history_lookup(
    input_root: Path = INPUT_ROOT,
    station_ids: tuple[str, ...] | list[str] = TARGET_IDS,
) -> dict[tuple[str, str], list[list[float]]]:
    """Load time-aligned predictor-visible 24h histories for graph nodes.

    Returns mapping: (station_id, origin_iso) -> x_hist [24, 7]
    Populated from development-role records in training.jsonl (initial prefixes) and
    forecasts.jsonl (replay origins). Final-role records are never read into the lookup.
    """
    lookup: dict[tuple[str, str], list[list[float]]] = {}
    station_set = {str(s) for s in station_ids}

    # 1. From training.jsonl (development records)
    with open(input_root / "training.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("role") == "development":
                fc = rec["forecast"]
                tid = str(fc["identity"][2])
                if tid in station_set:
                    lookup[(tid, fc["origin"])] = fc["x_hist"]

    # 2. From forecasts.jsonl
    with open(input_root / "forecasts.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("role") != "development":
                continue
            tid = str(r["identity"][2])
            if tid in station_set:
                lookup[(tid, r["origin"])] = r["x_hist"]

    return lookup


def load_distance_matrix(
    raw_zip_path: Path = RAW_ZIP_PATH,
    target_ids: tuple[str, ...] = TARGET_IDS,
    sigma: float | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Extract station_distance.csv and compute normalized adjacency matrix.

    Constructs normalized spatial adjacency matrix A_hat = D^{-1/2} A D^{-1/2}
    where A_ij = exp(-d_ij^2 / sigma^2) with self-loops.
    Uses Python standard csv module to ensure zero external dependency.
    """
    node_ids = sorted({str(t) for t in target_ids})
    header, rows = _read_distance_rows(raw_zip_path)
    col = {c: i for i, c in enumerate(header)}
    dist_matrix = np.array(
        [[float(rows[a][col[b]]) for b in node_ids] for a in node_ids], dtype=float
    )

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
