"""Dependency-specific offline tests; no downloads or real-data training."""

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import torch

from experiments.member_studies.duc_retention.data import (
    arrived,
    source_signature,
    training_rows,
    verified_manifest,
)
from experiments.member_studies.duc_retention.model import (
    Forecaster,
    frozen_reference,
    objective,
    retention,
)
from experiments.member_studies.duc_retention.run import checkpoint


class StudyTests(unittest.TestCase):
    def setUp(self) -> None:
        torch.set_num_threads(1)
        torch.manual_seed(7)

    def test_independent_nonuniform_calculation_and_gradient(self) -> None:
        # First two denominator values are 2 and 4; other differences are zero.
        # (2^2/2^2 + 4^2/4^2)/64 = 1/32.
        # dL/dz0=2*2/(64*4)=1/64; dL/dz1=2*4/(64*16)=1/128.
        target = torch.zeros(1, 64, dtype=torch.float64)
        target[0, :2] = torch.tensor([2.0, 4.0])
        target.requires_grad_()
        std = torch.ones(64, dtype=torch.float64)
        std[:2] = torch.tensor([1.5, 3.5])
        loss = retention(target, torch.zeros_like(target), std, 0.5)
        self.assertEqual(loss.item(), 1 / 32)
        loss.backward()
        self.assertEqual(target.grad[0, 0].item(), 1 / 64)
        self.assertEqual(target.grad[0, 1].item(), 1 / 128)
        self.assertTrue((target.grad[0, 2:] == 0).all())

    def test_zero_retention_and_frozen_source(self) -> None:
        model = Forecaster()
        source = frozen_reference(model)
        before = copy.deepcopy(source.state_dict())
        x, c, y = torch.randn(2, 24, 7), torch.randn(2, 24, 5), torch.rand(2, 24)
        loss, _, retain = objective(model, source, x, c, y, torch.ones(64), 0.1, 1e-6)
        # CPU train/eval GRU kernels can differ at floating-point roundoff.
        self.assertLess(retain.item(), 1e-12)
        loss.backward()
        self.assertFalse(source.training)
        self.assertTrue(all(p.grad is None and not p.requires_grad for p in source.parameters()))
        self.assertTrue(all(torch.equal(v, source.state_dict()[k]) for k, v in before.items()))
        self.assertEqual(model(x, c).shape, (2, 24))
        self.assertTrue((model(x, c) > 0).all())

    def test_lambda_zero_matches_forecast_only_and_targets_are_isolated(self) -> None:
        original = Forecaster()
        source = frozen_reference(original)
        a, b, untouched = (copy.deepcopy(original) for _ in range(3))
        oa, ob = (torch.optim.Adam(m.parameters(), lr=0.001) for m in (a, b))
        x, c, y = torch.randn(2, 24, 7), torch.randn(2, 24, 5), torch.rand(2, 24)
        for _ in range(3):
            oa.zero_grad()
            ob.zero_grad()
            objective(a, source, x, c, y, torch.ones(64), 0, 1e-6)[0].backward()
            (b(x, c) - y).abs().mean().backward()
            oa.step()
            ob.step()
        for name, value in a.state_dict().items():
            self.assertTrue(torch.equal(value, b.state_dict()[name]))
            self.assertTrue(torch.equal(original.state_dict()[name], untouched.state_dict()[name]))
        self.assertFalse(torch.equal(a.head[0].weight, untouched.head[0].weight))
        for index, state in oa.state_dict()["state"].items():
            for name, value in state.items():
                self.assertTrue(torch.equal(value, ob.state_dict()["state"][index][name]))

    def test_checkpoint_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model = Forecaster()
            path = Path(directory) / "model.pt"
            checkpoint(path, model, {}, torch.ones(64), {"stage": "source"}, {}, {})
            restored = Forecaster()
            restored.load_state_dict(torch.load(path, weights_only=False)["model"])
            x, c = torch.randn(1, 24, 7), torch.randn(1, 24, 5)
            self.assertTrue(torch.equal(model(x, c), restored(x, c)))
            with self.assertRaises(FileExistsError):
                checkpoint(path, model, {}, torch.ones(64), {}, {}, {})

    def test_label_availability_and_missing_not_zero(self) -> None:
        origin = datetime.fromisoformat("2022-12-01T00:00:00+08:00")
        row = {
            "identity": ["urbanev", "SZH", "test"],
            "origin": origin.isoformat(),
            "clock_mode": "offset-aware-local",
            "timestamps": [(origin + timedelta(hours=i)).isoformat() for i in range(24)],
            "energy_kwh": [0.0] * 24,
            "file_valid": [True] * 24,
            "available_at": [(origin + timedelta(hours=i + 1)).isoformat() for i in range(24)],
        }
        self.assertIsNone(arrived(row, origin + timedelta(hours=23)))
        self.assertEqual(arrived(row, origin + timedelta(days=1)), (0.0,) * 24)
        row["file_valid"][0] = False
        row["energy_kwh"][0] = None
        self.assertIsNone(arrived(row, origin + timedelta(days=2)))

    def test_invalid_loss_parameters(self) -> None:
        for epsilon in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                retention(torch.zeros(1, 64), torch.zeros(1, 64), torch.ones(64), epsilon)

    def test_source_container_id_is_not_training_content(self) -> None:
        a = [
            {
                "role": "source",
                "forecast": {"input_run_id": "7d", "scale_id": "fixed", "x_hist": [1]},
                "y_scaled": [2],
            }
        ]
        b = copy.deepcopy(a)
        b[0]["forecast"]["input_run_id"] = "14d"
        self.assertEqual(source_signature(a), source_signature(b))
        b[0]["forecast"]["scale_id"] = "different"
        self.assertNotEqual(source_signature(a), source_signature(b))
        b[0]["role"] = "development"
        with self.assertRaises(ValueError):
            source_signature(b)

    def test_training_role_prefix_and_scaler_guards(self) -> None:
        entity = {
            "identity": ["urbanev", "SZH", "test"],
            "role": "development",
            "fit_start": "2022-11-24T00:00:00+08:00",
            "cutoff": "2022-12-01T00:00:00+08:00",
            "initial_trainable": 1,
            "scale": {"fit_sha256": "scale"},
        }
        example = {
            "role": "development",
            "forecast": {
                "identity": entity["identity"],
                "history_labels": ["2022-11-29T00:00:00+08:00"],
                "origin": "2022-11-30T00:00:00+08:00",
                "scale_id": "scale",
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            file = path / "training.jsonl"
            file.write_text(json.dumps(example) + "\n")
            self.assertEqual(training_rows(path, [entity]), [example])
            for changed in (
                dict(example, role="final"),
                dict(
                    example, forecast=dict(example["forecast"], origin="2022-12-01T00:00:00+08:00")
                ),
                dict(example, forecast=dict(example["forecast"], scale_id="wrong")),
            ):
                file.write_text(json.dumps(changed) + "\n")
                with self.assertRaises(ValueError):
                    training_rows(path, [entity])

    def test_unpinned_manifest_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "manifest.json").write_text('{"config": {"history_days": 7}}')
            with self.assertRaisesRegex(ValueError, "pinned"):
                verified_manifest(path)


if __name__ == "__main__":
    unittest.main()
