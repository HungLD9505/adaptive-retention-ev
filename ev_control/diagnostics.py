"""Read-only forecast/retention gradient diagnostics for issue #99."""

import math
from dataclasses import dataclass
from typing import Sequence

import torch

from ev_models.model import ForecastGRU, forecast_loss, retention_loss
from ev_runner.state import restore_rng, rng_state


@dataclass(frozen=True)
class DiagnosticConfig:
    cadence: int
    epsilon_g: float

    def __post_init__(self) -> None:
        if isinstance(self.cadence, bool) or not isinstance(self.cadence, int) or self.cadence < 1:
            raise ValueError("Diagnostic cadence must be a positive integer")
        if (
            isinstance(self.epsilon_g, bool)
            or not isinstance(self.epsilon_g, (int, float))
            or not math.isfinite(self.epsilon_g)
            or self.epsilon_g <= 0
        ):
            raise ValueError("Diagnostic epsilon_g must be finite positive")


def _norm(parts: Sequence[torch.Tensor]) -> torch.Tensor:
    return torch.stack([part.square().sum() for part in parts]).sum().sqrt()


def measure(
    model: ForecastGRU,
    reference: ForecastGRU,
    latent_scale: torch.Tensor,
    records: Sequence[dict],
    *,
    weight: float,
    retention_epsilon: float,
    epsilon_g: float,
    device: str,
) -> dict:
    """Measure current arrived examples without stepping model/Adam or consuming RNG."""
    if not records or not math.isfinite(weight) or weight < 0:
        raise ValueError("Nonempty arrived records and finite nonnegative lambda required")
    if (
        not math.isfinite(epsilon_g)
        or epsilon_g <= 0
        or reference.training
        or any(parameter.requires_grad for parameter in reference.parameters())
    ):
        raise ValueError("Invalid diagnostic epsilon or unfrozen reference")
    saved_rng = rng_state()
    training_mode = model.training
    try:
        # cuDNN GRU backward requires training mode. Restore mode and RNG below.
        model.train()
        x, calendar, labels = (
            torch.tensor([record[key] for record in records], dtype=torch.float32, device=device)
            for key in ("x_hist", "c_future", "y_scaled")
        )
        forecast = forecast_loss(model(x, calendar), labels)
        target_latent = model.encode(x)
        with torch.no_grad():
            source_latent = reference.encode(x)
        retain = retention_loss(
            target_latent, source_latent, latent_scale.to(device), retention_epsilon
        )
        encoder = tuple(model.encoder.parameters())
        forecast_grad = torch.autograd.grad(forecast, encoder, retain_graph=True)
        retain_grad = torch.autograd.grad(retain, encoder)
        forecast_norm = _norm(forecast_grad)
        retain_norm = _norm(retain_grad)
        weighted_norm = weight * retain_norm
        dot = sum((a * b).sum() for a, b in zip(forecast_grad, retain_grad, strict=True))
        alignment = (
            (dot / (forecast_norm * retain_norm)).item()
            if forecast_norm.item() > 0 and retain_norm.item() > 0
            else None
        )
        displacement = (target_latent - source_latent).square().sum(dim=1).sqrt().mean()
        values = {
            "forecast_mae_scaled": forecast.item(),
            "retention_mse": retain.item(),
            "lambda_times_retention": (weight * retain).item(),
            "encoder_forecast_grad_norm": forecast_norm.item(),
            "encoder_weighted_retention_grad_norm": weighted_norm.item(),
            "encoder_grad_ratio": (weighted_norm / (forecast_norm + epsilon_g)).item(),
            "encoder_forecast_retention_alignment": alignment,
            "latent_displacement_l2_mean": displacement.item(),
            "latent_scale_min": latent_scale.min().item(),
            "latent_scale_max": latent_scale.max().item(),
            "latent_scale_zero_coordinates": int((latent_scale == 0).sum().item()),
            "epsilon_g": float(epsilon_g),
            "weight": float(weight),
            "examples": len(records),
            "clipped": False,
            "nonfinite": False,
        }
        if any(not math.isfinite(value) for value in values.values() if isinstance(value, float)):
            raise ValueError("Nonfinite diagnostic; run failed")
        return values
    finally:
        model.train(training_mode)
        restore_rng(saved_rng)
