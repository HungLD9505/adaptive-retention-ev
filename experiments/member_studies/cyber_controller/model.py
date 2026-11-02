"""Backbone GRU model and latent retention loss for EV charging demand forecasting.

Follows Report 1 Section 5:
- 2-layer GRU backbone, hidden size 64 (d=64).
- Input: 24 historical hours with 7 features (scaled energy + calendar + present mask).
- Output: Last hidden representation z_t concatenated with 24h future calendar (120 dims),
  passed through an MLP with Softplus activation producing 24 non-negative predictions.
- Retention loss: normalized L2 distance on latent representations against frozen source encoder:
  L_retain = (1/d) * sum_{k=1}^d [ (z_T,k - z_S,k) / (s_k + eps) ]^2
"""

from __future__ import annotations

from typing import Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class GRUEncoder(nn.Module):
    """2-layer GRU encoder producing 64-dimensional latent representations."""

    def __init__(self, input_dim: int = 7, hidden_dim: int = 64, num_layers: int = 2) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
        )

    def forward(self, x_hist: torch.Tensor) -> torch.Tensor:
        """Encode historical sequence [batch_size, 24, input_dim] into z [batch_size, 64]."""
        out, _ = self.gru(x_hist)
        # Take the latent representation at the final step (equivalent to top-layer final hidden)
        return out[:, -1, :]


class ForecastHead(nn.Module):
    """MLP mapping latent representation + 24h future calendar to 24 non-negative outputs."""

    def __init__(
        self,
        latent_dim: int = 64,
        future_cal_dim: int = 120,
        hidden_dim: int = 128,
        horizon: int = 24,
    ) -> None:
        super().__init__()
        in_dim = latent_dim + future_cal_dim
        self.mlp = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, horizon),
        )

    def forward(self, z: torch.Tensor, c_future: torch.Tensor) -> torch.Tensor:
        """Combine z [B, 64] and c_future [B, 24, 5] -> return predictions [B, 24]."""
        b = z.size(0)
        c_flat = c_future.reshape(b, -1)
        combined = torch.cat([z, c_flat], dim=1)
        out = self.mlp(combined)
        return F.softplus(out)


class EVForecasterGRU(nn.Module):
    """Complete 24h -> 24h EV Demand Forecaster."""

    def __init__(
        self,
        input_dim: int = 7,
        latent_dim: int = 64,
        future_cal_dim: int = 120,
        head_hidden_dim: int = 128,
        horizon: int = 24,
    ) -> None:
        super().__init__()
        self.encoder = GRUEncoder(input_dim=input_dim, hidden_dim=latent_dim, num_layers=2)
        self.head = ForecastHead(
            latent_dim=latent_dim,
            future_cal_dim=future_cal_dim,
            hidden_dim=head_hidden_dim,
            horizon=horizon,
        )

    def forward(
        self, x_hist: torch.Tensor, c_future: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass returning (predictions [B, 24], latent_z [B, 64])."""
        z = self.encoder(x_hist)
        y_hat = self.head(z, c_future)
        return y_hat, z

    def predict(self, x_hist: torch.Tensor, c_future: torch.Tensor) -> torch.Tensor:
        """Inference returning only predictions [B, 24]."""
        y_hat, _ = self.forward(x_hist, c_future)
        return y_hat


class LatentRetentionLoss(nn.Module):
    """Latent retention loss against a frozen source encoder with per-dimension scaling s_k.

    L_retain = (1/d) * sum_k [ (z_T,k - z_S,k) / (s_k + eps) ]^2
    """

    def __init__(
        self,
        source_encoder: nn.Module,
        s_k: torch.Tensor,
        eps: float = 1e-5,
    ) -> None:
        super().__init__()
        self.source_encoder = source_encoder
        self.source_encoder.eval()
        for param in self.source_encoder.parameters():
            param.requires_grad = False

        # Register s_k as a persistent buffer
        self.register_buffer("s_k", s_k.detach().clone())
        self.eps = eps

    def forward(self, z_target: torch.Tensor, x_hist: torch.Tensor) -> torch.Tensor:
        """Compute latent retention loss for the given target latents and inputs."""
        with torch.no_grad():
            z_source = self.source_encoder(x_hist)

        # Scale difference by (s_k + eps)
        diff = (z_target - z_source) / (self.s_k + self.eps)
        # Mean squared difference across dimensions, then mean over batch
        dim_loss = torch.mean(diff**2, dim=-1)
        return torch.mean(dim_loss)


def compute_forecast_mae(y_hat: torch.Tensor, y_true: torch.Tensor) -> torch.Tensor:
    """Mean absolute error across 24 horizons: (1/24) * sum_h |y_hat_h - y_h|."""
    return torch.mean(torch.abs(y_hat - y_true), dim=-1)
