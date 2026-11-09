"""Independent numerical checks for the issue #99 virtual Adam derivative."""

import copy
import unittest

import torch
from torch import nn

from ev_control.hypergradient import (
    forecast_with_virtual,
    validation_hypergradient,
    virtual_adam_step,
)


class HypergradientTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(42)
        self.model = nn.Linear(2, 1, bias=True).double()
        self.optimizer = torch.optim.Adam(
            self.model.parameters(), lr=0.01, weight_decay=0.02, amsgrad=True
        )
        x = torch.tensor([[0.7, -0.3], [0.2, 0.9]], dtype=torch.float64)
        y = torch.tensor([[0.4], [0.8]], dtype=torch.float64)
        for _ in range(2):
            self.optimizer.zero_grad(set_to_none=True)
            ((self.model(x) - y) ** 2).mean().backward()
            self.optimizer.step()
        self.x = x
        self.y = y

    def train_loss(self, model, coefficient):
        forecast = ((model(self.x) - self.y) ** 2).mean()
        retention = (
            (model.weight - torch.tensor([[0.1, -0.2]], dtype=torch.float64)).square().mean()
        )
        return forecast + coefficient * retention

    def validation_loss(self, weights):
        return (forecast_with_virtual(self.model, weights, self.x) - self.y * 0.8).square().mean()

    def test_virtual_step_matches_real_adam_and_does_not_mutate(self):
        before_model = copy.deepcopy(self.model.state_dict())
        before_optimizer = copy.deepcopy(self.optimizer.state_dict())
        coefficient = torch.tensor(0.3, dtype=torch.float64, requires_grad=True)
        virtual = virtual_adam_step(
            self.model, self.optimizer, self.train_loss(self.model, coefficient)
        )
        for name, original in before_model.items():
            self.assertTrue(torch.equal(self.model.state_dict()[name], original))
        self.assertEqual(str(self.optimizer.state_dict()), str(before_optimizer))
        clone = copy.deepcopy(self.model)
        real = torch.optim.Adam(clone.parameters(), lr=0.01, weight_decay=0.02, amsgrad=True)
        real.load_state_dict(before_optimizer)
        real.zero_grad(set_to_none=True)
        self.train_loss(clone, coefficient.detach()).backward()
        real.step()
        for name, actual in clone.named_parameters():
            torch.testing.assert_close(virtual[name].detach(), actual, rtol=1e-13, atol=1e-13)

    def test_hypergradient_matches_symmetric_difference_at_zero_and_positive(self):
        for value in (0.0, 0.3):
            coefficient = torch.tensor(value, dtype=torch.float64, requires_grad=True)
            gradient, _ = validation_hypergradient(
                self.model, self.optimizer, coefficient, self.train_loss, self.validation_loss
            )
            for delta in (1e-3, 1e-4, 1e-5):
                plus = torch.tensor(value + delta, dtype=torch.float64)
                minus = torch.tensor(value - delta, dtype=torch.float64)
                upper = self.validation_loss(
                    virtual_adam_step(self.model, self.optimizer, self.train_loss(self.model, plus))
                )
                lower = self.validation_loss(
                    virtual_adam_step(
                        self.model, self.optimizer, self.train_loss(self.model, minus)
                    )
                )
                numerical = (upper - lower) / (2 * delta)
                torch.testing.assert_close(gradient, numerical, rtol=5e-5, atol=1e-7)


if __name__ == "__main__":
    unittest.main()
