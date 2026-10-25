"""Reviewable encoder-parameter ablation; primary latent retention is unchanged."""

from typing import Sequence

import torch

from ev_models.model import ForecastGRU, forecast_loss
from ev_models.training import TrainingConfig, batches
from ev_runner.state import Branch, restore_rng, rng_state


def parameter_retention(model: ForecastGRU, reference: ForecastGRU) -> torch.Tensor:
    """Mean squared difference over all encoder parameter elements; head excluded."""
    pairs = list(zip(model.encoder.parameters(), reference.encoder.parameters(), strict=True))
    count = sum(p.numel() for p, _ in pairs)
    return sum((p - q.detach()).square().sum() for p, q in pairs) / count


def parameter_epoch(
    model: ForecastGRU,
    optimizer: torch.optim.Optimizer,
    records: Sequence[dict],
    config: TrainingConfig,
    *,
    epoch: int,
    weight: float,
    reference: ForecastGRU,
    device: str,
) -> dict:
    if not records or weight < 0:
        raise ValueError("Records and nonnegative lambda required")
    if reference.training or any(p.requires_grad for p in reference.parameters()):
        raise ValueError("Parameter reference must be frozen in evaluation mode")
    model.train()
    totals = [0.0, 0.0, 0.0]
    steps = 0
    for x, c, y in batches(
        records, config.batch_size, device=device, shuffle_seed=config.seed + epoch
    ):
        optimizer.zero_grad(set_to_none=True)
        forecast = forecast_loss(model(x, c), y)
        retain = parameter_retention(model, reference) if weight else forecast.new_zeros(())
        loss = forecast + weight * retain
        if not torch.isfinite(loss):
            raise ValueError("Nonfinite parameter-ablation loss")
        loss.backward()
        if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
            raise ValueError("Nonfinite parameter-ablation gradient")
        optimizer.step()
        if any(not torch.isfinite(p).all() for p in model.parameters()):
            raise ValueError("Nonfinite parameter-ablation state")
        for i, value in enumerate((loss, forecast, retain)):
            totals[i] += value.item() * len(x)
        steps += 1
    return {
        "loss": totals[0] / len(records),
        "forecast_mae_scaled": totals[1] / len(records),
        "parameter_mse": totals[2] / len(records),
        "steps": steps,
        "examples": len(records),
        "epoch": epoch + 1,
    }


class ParameterBranch(Branch):
    def snapshot(self) -> dict:
        return {**super().snapshot(), "kind": "encoder-parameter-retention-v1"}

    @classmethod
    def from_snapshot(cls, value: dict, *, device: str, learning_rate: float) -> "ParameterBranch":
        restored = Branch.from_snapshot(value, device=device, learning_rate=learning_rate)
        obj = cls(restored.model, restored.optimizer, restored.rng)
        obj.steps = restored.steps
        return obj

    def update(
        self,
        record: dict,
        *,
        weight: float,
        config: TrainingConfig,
        device: str,
        reference: ForecastGRU,
        latent_scale: torch.Tensor,
        event_index: int,
    ) -> list[dict]:
        restore_rng(self.rng)
        logs = []
        for epoch in range(config.epochs):
            log = parameter_epoch(
                self.model,
                self.optimizer,
                [record],
                config,
                epoch=event_index * config.epochs + epoch,
                weight=weight,
                reference=reference,
                device=device,
            )
            self.steps += log["steps"]
            logs.append(log)
        self.rng = rng_state()
        return logs
