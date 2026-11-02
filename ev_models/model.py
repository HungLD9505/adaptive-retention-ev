"""Standard GRU encoder and future-calendar forecasting head; no custom GRU cell."""

import math
from dataclasses import asdict, dataclass

import torch
from torch import Tensor, nn


@dataclass(frozen=True)
class ModelConfig:
    """Report 1 backbone constants and an explicitly configurable MLP width."""

    head_width: int = 64

    def __post_init__(self) -> None:
        if (
            isinstance(self.head_width, bool)
            or not isinstance(self.head_width, int)
            or self.head_width < 1
        ):
            raise ValueError("head_width must be a positive integer")


class ForecastGRU(nn.Module):
    """Stateless per-window encoder; no hidden state is shared across entities."""

    def __init__(self, config: ModelConfig = ModelConfig()) -> None:
        super().__init__()
        self.config = config
        self.encoder = nn.GRU(7, 64, num_layers=2, batch_first=True, dropout=0)
        self.head = nn.Sequential(
            nn.Linear(64 + 24 * 5, config.head_width),
            nn.ReLU(),
            nn.Linear(config.head_width, 24),
            nn.Softplus(),
        )

    def encode(self, x_hist: Tensor) -> Tensor:
        """Return last-layer final hidden state [batch,64]."""
        validate_tensor(x_hist, (24, 7), "x_hist")
        _, hidden = self.encoder(x_hist)
        return hidden[-1]

    def forward(self, x_hist: Tensor, c_future: Tensor) -> Tensor:
        validate_tensor(c_future, (24, 5), "c_future")
        if x_hist.shape[0] != c_future.shape[0]:
            raise ValueError("Historical/future batch sizes differ")
        z = self.encode(x_hist)
        return self.head(torch.cat((z, c_future.flatten(1)), dim=1))

    def architecture(self) -> dict:
        return {
            "schema": "ev-gru-v1",
            "layers": 2,
            "latent_dim": 64,
            "history_shape": [24, 7],
            "calendar_shape": [24, 5],
            "horizon": 24,
            "dropout": 0,
            "head_activation": "ReLU",
            "output_activation": "Softplus",
            **asdict(self.config),
        }


def validate_tensor(value: Tensor, tail: tuple[int, ...], name: str) -> None:
    if (
        not isinstance(value, Tensor)
        or value.ndim != len(tail) + 1
        or tuple(value.shape[1:]) != tail
        or value.shape[0] < 1
        or not value.is_floating_point()
        or not torch.isfinite(value).all()
    ):
        raise ValueError(f"{name} must be a nonempty finite floating batch with tail {tail}")


def forecast_loss(prediction: Tensor, labels: Tensor) -> Tensor:
    """Mean of each complete day's 24 normalized absolute errors, then batch mean."""
    validate_tensor(prediction, (24,), "prediction")
    validate_tensor(labels, (24,), "labels")
    if prediction.shape != labels.shape or (labels < 0).any():
        raise ValueError("Complete, nonnegative, aligned labels required; no broadcasting")
    return (prediction - labels).abs().mean()


def retention_loss(target: Tensor, reference: Tensor, scales: Tensor, epsilon: float) -> Tensor:
    """Report 1 Eq.2: mean square AFTER dimensionwise division by s_k+epsilon."""
    validate_tensor(target, (64,), "target latent")
    validate_tensor(reference, (64,), "reference latent")
    if (
        target.shape != reference.shape
        or scales.shape != (64,)
        or not torch.isfinite(scales).all()
        or (scales < 0).any()
        or not math.isfinite(epsilon)
        or epsilon <= 0
    ):
        raise ValueError("Invalid latent normalization")
    return ((target - reference.detach()) / (scales.detach() + epsilon)).square().mean()
