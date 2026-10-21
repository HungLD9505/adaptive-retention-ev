"""Expected-value tests for fixed source latent scales and retention reduction."""

from __future__ import annotations

import unittest

import torch

from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.retention import (
    frozen_source_reference,
    retention_loss,
    source_latent_scale,
)
from experiments.hung_sprint2.training import initialize_target, target_step


class RetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def test_exact_dimension_and_batch_mean(self) -> None:
        target = torch.zeros(2, 64, requires_grad=True)
        source = torch.stack((torch.ones(64), torch.full((64,), 3.0)))
        scale = torch.ones(64)
        result = retention_loss(target, source, scale, epsilon=1.0)
        self.assertEqual(float(result.detach()), 1.25)
        result.backward()
        self.assertTrue(bool(torch.isfinite(target.grad).all()))
        self.assertIsNone(source.grad)

    def test_scale_is_source_only_population_sd_and_mode_restored(self) -> None:
        model = ForecastGRU(ModelConfig(calendar_hidden=8))
        model.train()
        first = torch.zeros(1, 24, 7)
        second = torch.ones(1, 24, 7)
        with torch.no_grad():
            expected = torch.cat((model.encode(first), model.encode(second))).std(
                dim=0, correction=0
            )
        actual = source_latent_scale(model, [first, second])
        self.assertTrue(torch.allclose(actual, expected))
        self.assertTrue(model.training)
        with self.assertRaises(ValueError):
            source_latent_scale(model, [first])

    def test_frozen_source_and_positive_retention_step(self) -> None:
        torch.manual_seed(222)
        source = ForecastGRU(ModelConfig(calendar_hidden=8))
        target, reference, optimizer = initialize_target(source, learning_rate=0.001)
        before = [parameter.clone() for parameter in reference.parameters()]
        x_hist = torch.rand(2, 24, 7)
        result = target_step(
            target,
            reference,
            optimizer,
            x_hist,
            torch.rand(2, 24, 5),
            torch.rand(2, 24),
            retention_weight=0.5,
            latent_scale=torch.ones(64),
            epsilon=1e-6,
        )
        self.assertGreaterEqual(result.retention, 0)
        self.assertAlmostEqual(result.total, result.forecast + 0.5 * result.retention, places=5)
        self.assertFalse(reference.training)
        for old, parameter in zip(before, reference.parameters(), strict=True):
            self.assertTrue(torch.equal(old, parameter))
            self.assertIsNone(parameter.grad)
        self.assertTrue(all(not parameter.requires_grad for parameter in reference.parameters()))

    def test_invalid_scale_and_epsilon_rejected(self) -> None:
        target = torch.zeros(1, 64)
        source = torch.zeros(1, 64)
        for scale in (torch.ones(63), torch.full((64,), -1.0), torch.full((64,), float("nan"))):
            with self.assertRaises(ValueError):
                retention_loss(target, source, scale, epsilon=1e-6)
        with self.assertRaises(ValueError):
            retention_loss(target, source, torch.ones(64), epsilon=0)
        with self.assertRaises(ValueError):
            retention_loss(target, source, torch.ones(64), epsilon=float("nan"))
        self.assertEqual(float(retention_loss(target, source, torch.zeros(64), epsilon=1e-6)), 0)

    def test_reference_is_independent_clone(self) -> None:
        source = ForecastGRU(ModelConfig(calendar_hidden=8))
        reference = frozen_source_reference(source)
        with torch.no_grad():
            source.encoder.weight_ih_l0.add_(1)
        self.assertFalse(torch.equal(source.encoder.weight_ih_l0, reference.encoder.weight_ih_l0))


if __name__ == "__main__":
    unittest.main()
