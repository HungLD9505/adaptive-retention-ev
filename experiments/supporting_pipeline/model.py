"""The Report 1 24-to-24 source/target forecasting backbone."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import torch
from torch import Tensor, nn


@dataclass(frozen=True)
class ModelConfig:
    """The calendar/head width is an explicit Development configuration choice."""

    calendar_hidden: int
    history_features: int = 7
    future_features: int = 5
    history_hours: int = 24
    forecast_hours: int = 24
    hidden_size: int = 64
    gru_layers: int = 2

    def __post_init__(self) -> None:
        if self.calendar_hidden <= 0:
            raise ValueError("calendar_hidden must be positive")
        if (self.history_features, self.future_features, self.history_hours) != (7, 5, 24):
            raise ValueError("Only the accepted ev-input-v1 24-hour feature schema is supported")
        if (self.forecast_hours, self.hidden_size, self.gru_layers) != (24, 64, 2):
            raise ValueError("Report 1 backbone dimensions cannot be changed")

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


class ForecastGRU(nn.Module):
    """Encode history with a two-layer GRU and forecast from known future calendar."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.config = config
        self.encoder = nn.GRU(
            input_size=config.history_features,
            hidden_size=config.hidden_size,
            num_layers=config.gru_layers,
            batch_first=True,
        )
        self.calendar_mlp = nn.Sequential(
            nn.Linear(config.forecast_hours * config.future_features, config.calendar_hidden),
            nn.ReLU(),
        )
        self.forecast_head = nn.Sequential(
            nn.Linear(config.hidden_size + config.calendar_hidden, config.forecast_hours),
            nn.Softplus(),
        )

    def encode(self, x_hist: Tensor) -> Tensor:
        if x_hist.ndim != 3 or tuple(x_hist.shape[1:]) != (24, 7):
            raise ValueError("x_hist must have shape [B,24,7]")
        if not x_hist.is_floating_point() or not torch.isfinite(x_hist).all():
            raise ValueError("x_hist must be finite floating-point values")
        _, hidden = self.encoder(x_hist)
        return hidden[-1]

    def forecast_and_latent(self, x_hist: Tensor, c_future: Tensor) -> tuple[Tensor, Tensor]:
        if c_future.ndim != 3 or tuple(c_future.shape[1:]) != (24, 5):
            raise ValueError("c_future must have shape [B,24,5]")
        if c_future.shape[0] != x_hist.shape[0]:
            raise ValueError("History/calendar batch sizes differ")
        if not c_future.is_floating_point() or not torch.isfinite(c_future).all():
            raise ValueError("c_future must be finite floating-point values")
        latent = self.encode(x_hist)
        calendar = self.calendar_mlp(c_future.flatten(start_dim=1))
        forecast = self.forecast_head(torch.cat((latent, calendar), dim=1))
        return forecast, latent

    def forward(self, x_hist: Tensor, c_future: Tensor) -> Tensor:
        forecast, _ = self.forecast_and_latent(x_hist, c_future)
        return forecast
