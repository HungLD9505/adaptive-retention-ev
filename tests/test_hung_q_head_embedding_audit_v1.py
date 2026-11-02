"""Offline algebra and shape regressions for the diagnostic head mapping."""

from __future__ import annotations

import unittest

import torch
from torch import nn

from experiments.supporting_pipeline.model import ForecastGRU, ModelConfig
from tools.hung_q_head_embedding_audit_v1 import embed_hung_head


class MinimalQModel(nn.Module):
    def __init__(self, width: int = 64) -> None:
        super().__init__()
        self.encoder = nn.GRU(7, 64, num_layers=2, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(184, width), nn.ReLU(), nn.Linear(width, 24), nn.Softplus()
        )

    def forward(self, history: torch.Tensor, calendar: torch.Tensor) -> torch.Tensor:
        _, hidden = self.encoder(history)
        return self.head(torch.cat((hidden[-1], calendar.flatten(1)), dim=1))


class HeadEmbeddingTests(unittest.TestCase):
    def test_same_function_on_mixed_sign_latents(self) -> None:
        torch.manual_seed(17)
        hung = ForecastGRU(ModelConfig(calendar_hidden=8)).eval()
        qyroven = MinimalQModel().eval()
        embed_hung_head(hung, qyroven)
        history = torch.randn(5, 24, 7)
        calendar = torch.randn(5, 24, 5)
        with torch.no_grad():
            difference = (hung(history, calendar) - qyroven(history, calendar)).abs().max()
        self.assertLess(difference.item(), 1e-6)

    def test_unreviewed_head_width_rejected(self) -> None:
        hung = ForecastGRU(ModelConfig(calendar_hidden=8))
        with self.assertRaisesRegex(ValueError, "Forecast head shape"):
            embed_hung_head(hung, MinimalQModel(width=8))


if __name__ == "__main__":
    unittest.main()
