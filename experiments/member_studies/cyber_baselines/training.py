"""Neural training, source pretraining and adaptation routines for Cyber baselines."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from experiments.member_studies.cyber_baselines.config import BenchmarkConfig
from experiments.member_studies.cyber_baselines.models.base import BaseForecaster
from experiments.member_studies.cyber_baselines.models.neural import (
    GRUForecaster,
    LSTMForecaster,
    MLPForecaster,
    TCNForecaster,
    TimeXerForecaster,
)

BACKBONE_REGISTRY: dict[str, type[nn.Module]] = {
    "MLP": MLPForecaster,
    "GRU": GRUForecaster,
    "LSTM": LSTMForecaster,
    "TCN": TCNForecaster,
    "TimeXer": TimeXerForecaster,
}


def set_seed(seed: int) -> None:
    """Set seeds for reproducibility."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class NeuralWrapper(BaseForecaster):
    """Wraps PyTorch neural module with optimizer and online update for replay."""

    def __init__(
        self,
        name: str,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        mode: str,
        seed: int,
    ) -> None:
        self._name = name
        self.model = model
        self.optimizer = optimizer
        self.mode = mode
        self.seed = seed

    @property
    def name(self) -> str:
        return self._name

    @property
    def param_count(self) -> int:
        return sum(p.numel() for p in self.model.parameters() if p.requires_grad)

    def predict(self, record: dict[str, Any]) -> list[float]:
        self.model.eval()
        with torch.no_grad():
            x_hist = torch.tensor(record["x_hist"], dtype=torch.float32).unsqueeze(0)
            c_future = torch.tensor(record["c_future"], dtype=torch.float32).unsqueeze(0)
            pred = self.model(x_hist, c_future)
            return pred.squeeze(0).cpu().tolist()

    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        self.model.train()
        x_hist = torch.tensor(record["x_hist"], dtype=torch.float32).unsqueeze(0)
        c_future = torch.tensor(record["c_future"], dtype=torch.float32).unsqueeze(0)
        y_label = torch.tensor(y_scaled, dtype=torch.float32).unsqueeze(0)

        self.optimizer.zero_grad()
        pred = self.model(x_hist, c_future)
        loss = (pred - y_label).abs().mean()
        loss.backward()
        self.optimizer.step()

        return {"status": "ok", "loss": float(loss.item())}


def train_source_model(
    backbone_name: str,
    seed: int,
    source_dataset: TensorDataset,
    config: BenchmarkConfig,
) -> tuple[Path, float]:
    """Train a neural backbone on the 65,888 Source examples.

    Returns:
        (checkpoint_path, elapsed_seconds)
    """
    config.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = config.checkpoint_dir / f"{backbone_name.lower()}_source_seed{seed}.pt"

    set_seed(seed)
    cls = BACKBONE_REGISTRY[backbone_name]
    model = cls()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.training_hp.source_lr)
    criterion = nn.L1Loss()

    loader = DataLoader(
        source_dataset,
        batch_size=config.training_hp.source_batch_size,
        shuffle=True,
    )

    model.train()
    start_time = time.perf_counter()

    for epoch in range(config.training_hp.source_epochs):
        epoch_loss = 0.0
        batches = 0
        for x_hist, c_future, y_scaled in loader:
            optimizer.zero_grad()
            preds = model(x_hist, c_future)
            loss = criterion(preds, y_scaled)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            batches += 1

    elapsed = time.perf_counter() - start_time

    # Save checkpoint
    torch.save(
        {
            "backbone": backbone_name,
            "seed": seed,
            "state_dict": model.state_dict(),
            "epochs": config.training_hp.source_epochs,
            "wall_seconds": elapsed,
        },
        ckpt_path,
    )

    return ckpt_path, elapsed


def build_neural_forecaster(
    backbone_name: str,
    mode: str,
    seed: int,
    target_id: str,
    initial_records: list[dict[str, Any]],
    config: BenchmarkConfig,
    source_ckpt_path: Path | None = None,
) -> tuple[NeuralWrapper, float]:
    """Build and adapt a neural forecaster for a target station.

    mode: 'target_only' or 'transfer'
    Returns:
        (wrapper, adaptation_seconds)
    """
    set_seed(seed)
    cls = BACKBONE_REGISTRY[backbone_name]
    model = cls()

    if mode == "transfer":
        if source_ckpt_path is None or not source_ckpt_path.is_file():
            raise FileNotFoundError(f"Missing Source checkpoint {source_ckpt_path} for {backbone_name}")
        state = torch.load(source_ckpt_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state["state_dict"])

    optimizer = torch.optim.Adam(model.parameters(), lr=config.training_hp.target_adapt_lr)

    # Initial adaptation on target prefix records
    adapt_start = time.perf_counter()
    model.train()

    if initial_records:
        x_list = [rec.get("forecast", rec)["x_hist"] for rec in initial_records]
        c_list = [rec.get("forecast", rec)["c_future"] for rec in initial_records]
        y_list = [rec["y_scaled"] for rec in initial_records]

        x_t = torch.tensor(x_list, dtype=torch.float32)
        c_t = torch.tensor(c_list, dtype=torch.float32)
        y_t = torch.tensor(y_list, dtype=torch.float32)
        prefix_ds = TensorDataset(x_t, c_t, y_t)
        prefix_loader = DataLoader(prefix_ds, batch_size=config.training_hp.target_batch_size, shuffle=True)

        for _ in range(config.training_hp.target_adapt_epochs):
            for xb, cb, yb in prefix_loader:
                optimizer.zero_grad()
                pred = model(xb, cb)
                loss = (pred - yb).abs().mean()
                loss.backward()
                optimizer.step()

    adapt_elapsed = time.perf_counter() - adapt_start

    wrapper = NeuralWrapper(
        name=backbone_name,
        model=model,
        optimizer=optimizer,
        mode=mode,
        seed=seed,
    )
    return wrapper, adapt_elapsed
