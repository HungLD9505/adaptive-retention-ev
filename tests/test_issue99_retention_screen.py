"""Independent numeric checks for the exploratory loss definitions."""

import unittest

import torch

from ev_models.model import ForecastGRU, retention_loss
from tools.issue99_retention_screen import importance_weights, penalty


class RetentionScreenTests(unittest.TestCase):
    def test_uniform_weights_recover_existing_loss(self):
        z = torch.full((2, 64), 2.0, requires_grad=True)
        zs = torch.ones_like(z)
        scales = torch.full((64,), 0.5)
        actual = penalty("selective", None, None, z, zs, scales, 0.001, torch.ones(64))
        self.assertEqual(actual.item(), retention_loss(z, zs, scales, 0.001).item())
        weights = torch.zeros(64)
        weights[0] = 64
        altered = z.detach().clone()
        altered[:, 0] = 3
        result = penalty("selective", None, None, altered, zs, scales, 0.001, weights)
        self.assertAlmostEqual(result.item(), 4 / 0.501**2, places=5)

    def test_l2sp_uses_encoder_and_frozen_reference(self):
        model, source = ForecastGRU(), ForecastGRU()
        source.load_state_dict(model.state_dict())
        args = (None, None, None, 0.001, None)
        self.assertEqual(penalty("l2sp", model, source, *args).item(), 0)
        with torch.no_grad():
            next(model.head.parameters()).add_(2)
        self.assertEqual(penalty("l2sp", model, source, *args).item(), 0)
        with torch.no_grad():
            next(model.encoder.parameters()).view(-1)[0].add_(2)
        value = penalty("l2sp", model, source, *args)
        self.assertEqual(value.item(), 2)
        value.backward()
        self.assertTrue(all(p.grad is None for p in source.parameters()))

    def test_importance_is_prefix_only_positive_mean_one(self):
        source = ForecastGRU().eval()
        rows = [{"x_hist": [[0.1] * 7] * 24, "c_future": [[0.2] * 5] * 24, "y_scaled": [0.4] * 24}]
        weights = importance_weights(source, rows)
        self.assertEqual(tuple(weights.shape), (64,))
        self.assertGreaterEqual(weights.min().item(), 0.1)
        self.assertAlmostEqual(weights.mean().item(), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
