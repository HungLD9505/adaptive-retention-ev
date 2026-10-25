"""Independent fixture checks for Report 1, without data downloads or real training."""

import copy
import tempfile
import unittest
from pathlib import Path

import torch

from ev_models.checkpoint import load_checkpoint, save_checkpoint
from ev_models.model import ForecastGRU, ModelConfig, forecast_loss, retention_loss
from ev_models.training import (
    TrainingConfig,
    adapt_model,
    frozen_reference,
    seed_everything,
    source_latent_scale,
    train_epoch,
)


class ModelTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        seed_everything(42)
        self.model = ForecastGRU()
        self.x = torch.rand(3, 24, 7)
        self.c = torch.rand(3, 24, 5)
        self.records = [
            {"x_hist": x.tolist(), "c_future": c.tolist(), "y_scaled": [0.2] * 24}
            for x, c in zip(self.x, self.c)
        ]
        self.config = TrainingConfig(epochs=2, batch_size=2)

    def test_standard_architecture_forward_and_both_gradients(self):
        self.assertEqual(self.model.encoder.num_layers, 2)
        self.assertEqual(self.model.encoder.hidden_size, 64)
        pred = self.model(self.x, self.c)
        self.assertEqual(tuple(pred.shape), (3, 24))
        self.assertTrue(torch.isfinite(pred).all())
        self.assertTrue((pred >= 0).all())
        forecast_loss(pred, torch.ones_like(pred)).backward()
        for module in (self.model.encoder, self.model.head):
            self.assertTrue(
                any(p.grad is not None and p.grad.abs().sum() > 0 for p in module.parameters())
            )

    def test_shape_nonfinite_and_broadcast_rejected(self):
        for x in (
            torch.zeros(3, 23, 7),
            torch.zeros(0, 24, 7),
            torch.full((3, 24, 7), float("nan")),
        ):
            with self.assertRaises(ValueError):
                self.model(x, self.c)
        with self.assertRaises(ValueError):
            forecast_loss(torch.ones(3, 24), torch.ones(1, 24))
        with self.assertRaises(ValueError):
            forecast_loss(torch.ones(3, 24), torch.full((3, 24), float("nan")))

    def test_latent_matches_last_layer_final_state(self):
        _, hidden = self.model.encoder(self.x)
        torch.testing.assert_close(self.model.encode(self.x), hidden[-1], rtol=0, atol=0)

    def test_loss_hand_calculation_and_detached_reference(self):
        target = torch.arange(64, dtype=torch.float32).reshape(1, 64).requires_grad_()
        reference = torch.ones(1, 64, requires_grad=True)
        scales = torch.arange(64, dtype=torch.float32, requires_grad=True)
        epsilon = 0.5
        expected = sum(((k - 1) / (k + epsilon)) ** 2 for k in range(64)) / 64
        loss = retention_loss(target, reference, scales, epsilon)
        self.assertAlmostEqual(loss.item(), expected, places=6)
        loss.backward()
        self.assertIsNone(reference.grad)
        self.assertIsNone(scales.grad)
        self.assertIsNotNone(target.grad)
        self.assertEqual(retention_loss(target, target, scales, epsilon).item(), 0)

    def test_source_scale_population_std_independent_calculation(self):
        actual = source_latent_scale(self.model, self.records, batch_size=2, device="cpu")
        with torch.no_grad():
            expected = self.model.eval().encode(self.x).double().std(0, correction=0).float()
        torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-7)

    def test_initial_transfer_target_isolation_and_freeze(self):
        source = copy.deepcopy(self.model.state_dict())
        a, b = adapt_model(self.model), adapt_model(self.model)
        ref = frozen_reference(self.model)
        scale = source_latent_scale(self.model, self.records, batch_size=2, device="cpu")
        train_epoch(
            a,
            torch.optim.Adam(a.parameters()),
            self.records,
            self.config,
            epoch=0,
            device="cpu",
            reference=ref,
            latent_scale=scale,
            retention_weight=0.01,
        )
        self.assertTrue(any(not torch.equal(p, a.state_dict()[k]) for k, p in source.items()))
        for k, value in source.items():
            self.assertTrue(torch.equal(value, b.state_dict()[k]))
            self.assertTrue(torch.equal(value, self.model.state_dict()[k]))
            self.assertTrue(torch.equal(value, ref.state_dict()[k]))
        self.assertFalse(ref.training)
        self.assertTrue(all(p.grad is None and not p.requires_grad for p in ref.parameters()))

    def test_lambda_zero_exactly_matches_forecast_only(self):
        a, b = adapt_model(self.model), adapt_model(self.model)
        first = train_epoch(
            a, torch.optim.Adam(a.parameters()), self.records, self.config, epoch=0, device="cpu"
        )
        second = train_epoch(
            b,
            torch.optim.Adam(b.parameters()),
            self.records,
            self.config,
            epoch=0,
            device="cpu",
            reference=frozen_reference(self.model),
            latent_scale=torch.ones(64),
            retention_weight=0,
        )
        self.assertEqual(first, second)
        for k, p in a.state_dict().items():
            self.assertTrue(torch.equal(p, b.state_dict()[k]))

    def test_reproducible_fixed_seed_training(self):
        snapshots = []
        for _ in range(2):
            seed_everything(42)
            model = ForecastGRU()
            train_epoch(
                model,
                torch.optim.Adam(model.parameters()),
                self.records,
                self.config,
                epoch=0,
                device="cpu",
            )
            snapshots.append(copy.deepcopy(model.state_dict()))
        for k, p in snapshots[0].items():
            self.assertTrue(torch.equal(p, snapshots[1][k]))

    def test_checkpoint_resume_optimizer_rng_matches_uninterrupted(self):
        a, b = adapt_model(self.model), adapt_model(self.model)
        oa, ob = torch.optim.Adam(a.parameters()), torch.optim.Adam(b.parameters())
        for epoch in (0, 1):
            train_epoch(a, oa, self.records, self.config, epoch=epoch, device="cpu")
        train_epoch(b, ob, self.records, self.config, epoch=0, device="cpu")
        metadata = {
            "input_binding": {
                "schema": "ev-checkpoint-input-binding-v1",
                "feature_schema": "ev-input-v1",
                "input_manifest_sha256": "a" * 64,
                "input_run_id": "fixture",
                "dataset_id": "charged",
                "city_id": "AMS",
                "stage": "source",
                "entity_id": None,
                "history_days": None,
                "scale_id": None,
                "source_checkpoint_sha256": None,
            },
            "training_config": self.config.as_dict(),
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "epoch.pt"
            sha = save_checkpoint(
                path, b, ob, metadata=metadata, latent_scale=torch.ones(64), completed_epochs=1
            )
            b, ob, payload = load_checkpoint(path, sha256=sha, restore_rng=True)
            self.assertEqual(payload["completed_epochs"], 1)
            train_epoch(b, ob, self.records, self.config, epoch=1, device="cpu")
            for k, p in a.state_dict().items():
                self.assertTrue(torch.equal(p, b.state_dict()[k]))
            self.assertEqual(oa.state_dict()["param_groups"], ob.state_dict()["param_groups"])
            with self.assertRaises(ValueError):
                load_checkpoint(path, sha256="0" * 64)
            with self.assertRaises(FileExistsError):
                save_checkpoint(
                    path, b, ob, metadata=metadata, latent_scale=None, completed_epochs=2
                )

    def test_bad_config_and_reference_rejected(self):
        for kwargs in (
            {"epochs": 0},
            {"seed": True},
            {"learning_rate": float("nan")},
            {"epsilon": 0},
        ):
            with self.assertRaises(ValueError):
                TrainingConfig(**kwargs)
        with self.assertRaises(ValueError):
            ModelConfig(0)
        with self.assertRaises(ValueError):
            train_epoch(
                self.model,
                torch.optim.Adam(self.model.parameters()),
                self.records,
                self.config,
                epoch=0,
                device="cpu",
                reference=self.model,
                latent_scale=torch.ones(64),
                retention_weight=1,
            )

    def test_nonfinite_gradient_does_not_step(self):
        before = copy.deepcopy(self.model.state_dict())
        handle = next(self.model.parameters()).register_hook(
            lambda g: torch.full_like(g, float("inf"))
        )
        with self.assertRaises(ValueError):
            train_epoch(
                self.model,
                torch.optim.Adam(self.model.parameters()),
                self.records,
                self.config,
                epoch=0,
                device="cpu",
            )
        handle.remove()
        for k, p in before.items():
            self.assertTrue(torch.equal(p, self.model.state_dict()[k]))
