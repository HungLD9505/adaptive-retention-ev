"""Independent offline checks for the Report 1 model and #19 training state."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import torch

from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.training import (
    forecast_mae,
    initialize_target,
    load_checkpoint,
    save_checkpoint,
    source_step,
    target_step,
)


def _source_binding() -> dict:
    return {
        "schema": "ev-checkpoint-input-binding-v1",
        "feature_schema": "ev-input-v1",
        "input_manifest_sha256": "a" * 64,
        "input_run_id": "fixture-source",
        "dataset_id": "urbanev",
        "city_id": "SZH",
        "stage": "source",
        "entity_id": None,
        "history_days": None,
        "scale_id": None,
        "source_checkpoint_sha256": None,
    }


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def setUp(self) -> None:
        torch.manual_seed(101)
        self.model = ForecastGRU(ModelConfig(calendar_hidden=16))
        self.history = torch.rand(2, 24, 7)
        self.calendar = torch.rand(2, 24, 5)
        self.labels = torch.rand(2, 24)

    def test_forecast_shape_nonnegative_and_latent_gradient(self) -> None:
        forecast, latent = self.model.forecast_and_latent(self.history, self.calendar)
        self.assertEqual(tuple(forecast.shape), (2, 24))
        self.assertEqual(tuple(latent.shape), (2, 64))
        self.assertTrue(bool((forecast >= 0).all()))
        forecast_mae(forecast, self.labels).backward()
        self.assertTrue(bool(torch.isfinite(self.model.encoder.weight_ih_l0.grad).all()))
        self.assertGreater(float(self.model.encoder.weight_ih_l0.grad.abs().sum()), 0)

    def test_forecast_mae_reduces_over_horizon_and_batch(self) -> None:
        forecast = torch.zeros(2, 24)
        labels = torch.cat((torch.ones(1, 24), torch.full((1, 24), 3.0)))
        self.assertEqual(float(forecast_mae(forecast, labels)), 2.0)
        with self.assertRaises(ValueError):
            forecast_mae(forecast, labels[:, :-1])

    def test_independent_targets_and_lambda_zero(self) -> None:
        source_before = {key: value.clone() for key, value in self.model.state_dict().items()}
        first, reference, first_optimizer = initialize_target(self.model, learning_rate=0.001)
        second, _, second_optimizer = initialize_target(self.model, learning_rate=0.001)
        first_before = {key: value.clone() for key, value in first.state_dict().items()}
        result = target_step(
            first,
            reference,
            first_optimizer,
            self.history,
            self.calendar,
            self.labels,
            retention_weight=0,
            latent_scale=None,
            epsilon=1e-6,
        )
        self.assertEqual(result.retention, 0)
        self.assertAlmostEqual(result.forecast, result.total)
        self.assertTrue(
            any(not torch.equal(first.state_dict()[key], value) for key, value in first_before.items())
        )
        for key, value in source_before.items():
            self.assertTrue(torch.equal(value, self.model.state_dict()[key]))
            self.assertTrue(torch.equal(value, reference.state_dict()[key]))
            self.assertTrue(torch.equal(value, second.state_dict()[key]))
        self.assertEqual(len(second_optimizer.state), 0)
        self.assertTrue(all(parameter.grad is None for parameter in reference.parameters()))

    def test_source_step_updates_encoder_and_head(self) -> None:
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        before = {key: value.clone() for key, value in self.model.state_dict().items()}
        source_step(self.model, optimizer, self.history, self.calendar, self.labels)
        self.assertFalse(torch.equal(before["encoder.weight_ih_l0"], self.model.encoder.weight_ih_l0))
        self.assertFalse(torch.equal(before["forecast_head.0.weight"], self.model.forecast_head[0].weight))

    def test_source_checkpoint_round_trip_and_binding(self) -> None:
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        source_step(self.model, optimizer, self.history, self.calendar, self.labels)
        self.model.eval()
        before = self.model(self.history, self.calendar).detach()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.pt"
            save_checkpoint(
                path,
                self.model,
                optimizer,
                input_binding=_source_binding(),
                latent_scale=torch.ones(64),
                seed=101,
                code_sha="fixture-code-sha",
                training_step=1,
            )
            reloaded, restored_optimizer, scale, metadata = load_checkpoint(
                path, expected_binding=_source_binding()
            )
            reloaded.eval()
            self.assertTrue(torch.equal(before, reloaded(self.history, self.calendar)))
            self.assertEqual(restored_optimizer.param_groups[0]["lr"], 0.001)
            self.assertTrue(torch.equal(scale, torch.ones(64)))
            self.assertEqual(metadata["training_step"], 1)
            source_step(self.model, optimizer, self.history, self.calendar, self.labels)
            source_step(reloaded, restored_optimizer, self.history, self.calendar, self.labels)
            for name, value in self.model.state_dict().items():
                self.assertTrue(torch.equal(value, reloaded.state_dict()[name]))
            with self.assertRaises(FileExistsError):
                save_checkpoint(
                    path,
                    self.model,
                    optimizer,
                    input_binding=_source_binding(),
                    latent_scale=None,
                    seed=101,
                    code_sha="fixture-code-sha",
                    training_step=1,
                )
            mismatch = _source_binding()
            mismatch["input_run_id"] = "other-run"
            with self.assertRaises(ValueError):
                load_checkpoint(path, expected_binding=mismatch)


if __name__ == "__main__":
    unittest.main()
