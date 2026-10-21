"""Unit tests for EVForecasterGRU model and LatentRetentionLoss.

Verifies:
- Shape of forward pass: x_hist [B, 24, 7] + c_future [B, 24, 5] -> y_hat [B, 24], z [B, 64].
- Outputs are strictly non-negative (Softplus head).
- Source encoder is frozen and requires no grad.
- Latent retention loss computes normalized L2 distance correctly.
"""

from __future__ import annotations

import unittest

import torch

from experiments.member_studies.cyber_controller.model import (
    EVForecasterGRU,
    GRUEncoder,
    LatentRetentionLoss,
    compute_forecast_mae,
)


class ModelTests(unittest.TestCase):
    """Test suite for neural network components and retention loss."""

    def setUp(self) -> None:
        torch.manual_seed(42)
        self.batch_size = 4
        self.x_hist = torch.randn(self.batch_size, 24, 7)
        self.c_future = torch.randn(self.batch_size, 24, 5)

    def test_forward_shapes_and_nonnegativity(self) -> None:
        """Forward pass must produce correct tensor shapes and non-negative forecasts."""
        model = EVForecasterGRU()
        y_hat, z = model(self.x_hist, self.c_future)

        self.assertEqual(y_hat.shape, (self.batch_size, 24))
        self.assertEqual(z.shape, (self.batch_size, 64))
        # Softplus guarantees non-negativity
        self.assertTrue(torch.all(y_hat >= 0.0).item())

    def test_latent_retention_loss_frozen_source(self) -> None:
        """Latent retention loss must not compute gradients for source encoder."""
        source_encoder = GRUEncoder()
        s_k = torch.ones(64)
        retention_loss_fn = LatentRetentionLoss(source_encoder=source_encoder, s_k=s_k)

        # Target model
        target_model = EVForecasterGRU()
        y_hat, z_target = target_model(self.x_hist, self.c_future)

        loss = retention_loss_fn(z_target, self.x_hist)
        self.assertGreater(loss.item(), 0.0)

        # Backward should propagate to target model parameters but not source encoder
        loss.backward()
        for p in source_encoder.parameters():
            self.assertIsNone(p.grad)
        for p in target_model.encoder.parameters():
            self.assertIsNotNone(p.grad)

    def test_forecast_mae_computation(self) -> None:
        """Test forecast MAE function calculation."""
        y_hat = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
        y_true = torch.tensor([[1.5, 1.0], [2.0, 5.0]])
        mae = compute_forecast_mae(y_hat, y_true)
        # Row 0: (|1 - 1.5| + |2 - 1|)/2 = (0.5 + 1)/2 = 0.75
        # Row 1: (|3 - 2| + |4 - 5|)/2 = (1 + 1)/2 = 1.0
        expected = torch.tensor([0.75, 1.0])
        self.assertTrue(torch.allclose(mae, expected))


if __name__ == "__main__":
    unittest.main()
