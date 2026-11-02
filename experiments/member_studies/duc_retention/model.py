"""Independent Report 1 backbone and fixed latent-retention objective."""

import copy
import math

import torch
from torch import Tensor, nn


class Forecaster(nn.Module):
    """24x7 history -> 64 latent; 24x5 future calendar -> 24 positive outputs."""

    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.GRU(7, 64, num_layers=2, batch_first=True)
        self.head = nn.Sequential(nn.Linear(184, 64), nn.ReLU(), nn.Linear(64, 24), nn.Softplus())

    def latent(self, history: Tensor) -> Tensor:
        if history.ndim != 3 or history.shape[1:] != (24, 7):
            raise ValueError("Expected history [batch,24,7]")
        return self.encoder(history)[1][-1]

    def forward(self, history: Tensor, calendar: Tensor) -> Tensor:
        if calendar.shape != (history.shape[0], 24, 5):
            raise ValueError("Expected calendar [batch,24,5]")
        return self.head(torch.cat((self.latent(history), calendar.flatten(1)), dim=1))


def frozen_reference(model: Forecaster) -> Forecaster:
    reference = copy.deepcopy(model).eval()
    reference.requires_grad_(False)
    return reference


def retention(target_latent: Tensor, source_latent: Tensor, std: Tensor, epsilon: float) -> Tensor:
    if target_latent.ndim != 2 or target_latent.shape[1] != 64:
        raise ValueError("Expected [batch,64] latent")
    if source_latent.shape != target_latent.shape or std.shape != (64,):
        raise ValueError("Incompatible latent statistics")
    if not math.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("epsilon must be finite and positive")
    if not torch.isfinite(std).all() or (std < 0).any():
        raise ValueError("Invalid source standard deviations")
    return ((target_latent - source_latent.detach()) / (std.detach() + epsilon)).square().mean()


def objective(
    model: Forecaster,
    reference: Forecaster,
    x: Tensor,
    c: Tensor,
    y: Tensor,
    std: Tensor,
    weight: float,
    epsilon: float,
) -> tuple[Tensor, Tensor, Tensor]:
    if not math.isfinite(weight) or weight < 0:
        raise ValueError("lambda must be finite and nonnegative")
    if y.shape != (x.shape[0], 24) or not torch.isfinite(y).all():
        raise ValueError("Expected complete finite labels [batch,24]")
    reference.eval()
    with torch.no_grad():
        source_z = reference.latent(x)
    z = model.latent(x)
    prediction = model.head(torch.cat((z, c.flatten(1)), dim=1))
    forecast = (prediction - y).abs().mean()
    retain = retention(z, source_z, std, epsilon)
    return forecast + weight * retain, forecast, retain
