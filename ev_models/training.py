"""Small training primitives shared by source and isolated target adaptations."""

import copy
import math
import random
from dataclasses import asdict, dataclass
from typing import Sequence

import torch
from torch import Tensor

from ev_models.model import ForecastGRU, forecast_loss, retention_loss


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 42
    epochs: int = 1
    batch_size: int = 64
    learning_rate: float = 0.001
    epsilon: float = 0.001
    head_width: int = 64

    def __post_init__(self) -> None:
        for name in ("seed", "epochs", "batch_size", "head_width"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < (0 if name == "seed" else 1)
            ):
                raise ValueError(f"Invalid {name}")
        for name in ("learning_rate", "epsilon"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"Invalid {name}")

    def as_dict(self) -> dict:
        return asdict(self)


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)


def frozen_reference(source: ForecastGRU) -> ForecastGRU:
    reference = copy.deepcopy(source).eval()
    reference.requires_grad_(False)
    return reference


def adapt_model(source: ForecastGRU) -> ForecastGRU:
    """Independent weights, including head; source optimizer is NOT transferred initially."""
    return copy.deepcopy(source).train()


def batches(
    records: Sequence[dict], batch_size: int, *, device: str, shuffle_seed: int | None = None
):
    indices = list(range(len(records)))
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(indices)
    for offset in range(0, len(indices), batch_size):
        selected = [records[i] for i in indices[offset : offset + batch_size]]
        yield tuple(
            torch.tensor([r[key] for r in selected], dtype=torch.float32, device=device)
            for key in ("x_hist", "c_future", "y_scaled")
        )


def train_epoch(
    model: ForecastGRU,
    optimizer: torch.optim.Optimizer,
    records: Sequence[dict],
    config: TrainingConfig,
    *,
    epoch: int,
    device: str,
    reference: ForecastGRU | None = None,
    latent_scale: Tensor | None = None,
    retention_weight: float = 0,
) -> dict:
    if not records or not math.isfinite(retention_weight) or retention_weight < 0:
        raise ValueError("Nonempty training records and finite nonnegative lambda required")
    if retention_weight and (reference is None or latent_scale is None):
        raise ValueError("Positive retention needs a frozen reference and source latent scales")
    if reference is not None:
        if reference.training or any(p.requires_grad for p in reference.parameters()):
            raise ValueError("Reference must be frozen and in eval mode")
    model.train()
    totals = [0.0, 0.0, 0.0]
    steps = 0
    for x, calendar, y in batches(
        records, config.batch_size, device=device, shuffle_seed=config.seed + epoch
    ):
        optimizer.zero_grad(set_to_none=True)
        prediction = model(x, calendar)
        forecast = forecast_loss(prediction, y)
        retain = forecast.new_zeros(())
        if retention_weight:
            with torch.no_grad():
                z_source = reference.encode(x)
            retain = retention_loss(
                model.encode(x), z_source, latent_scale.to(device), config.epsilon
            )
        total = forecast + retention_weight * retain
        if not torch.isfinite(total):
            raise ValueError("Nonfinite loss; optimizer not stepped")
        total.backward()
        if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
            optimizer.zero_grad(set_to_none=True)
            raise ValueError("Nonfinite gradient; optimizer not stepped")
        optimizer.step()
        if any(not torch.isfinite(p).all() for p in model.parameters()):
            raise ValueError("Nonfinite parameter after optimizer step; run failed")
        for i, loss in enumerate((total, forecast, retain)):
            totals[i] += loss.item() * len(x)
        steps += 1
    return dict(
        zip(
            ("loss", "forecast_mae_scaled", "retention_mse"),
            (v / len(records) for v in totals),
            strict=True,
        ),
        examples=len(records),
        steps=steps,
        epoch=epoch + 1,
    )


def source_latent_scale(
    source: ForecastGRU, records: Sequence[dict], *, batch_size: int, device: str
) -> Tensor:
    """Population std (ddof=0), float64 streaming moments, frozen source inputs only."""
    if not records:
        raise ValueError("Empty latent scale population")
    reference = frozen_reference(source)
    count = 0
    mean = torch.zeros(64, dtype=torch.float64, device=device)
    m2 = torch.zeros_like(mean)
    with torch.no_grad():
        for x, _, _ in batches(records, batch_size, device=device):
            z = reference.encode(x).double()
            n = len(z)
            delta = z.mean(0) - mean
            m2 += ((z - z.mean(0)).square()).sum(0) + delta.square() * count * n / (count + n)
            mean += delta * n / (count + n)
            count += n
    result = (m2 / count).clamp_min(0).sqrt().float().cpu()
    if not torch.isfinite(result).all():
        raise ValueError("Nonfinite source latent scales")
    return result
