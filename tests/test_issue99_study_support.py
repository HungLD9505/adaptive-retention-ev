"""Regression checks for immutable caching and non-mutating diagnostics."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import torch

from ev_models.data import InputRun
from ev_models.model import ForecastGRU
from ev_models.training import frozen_reference
from ev_runner.diagnostics import measure
from ev_runner.state import state_digest
from tools.issue99_study_support import PreparedInputs


class StudySupportTests(unittest.TestCase):
    def test_cached_rows_are_isolated_and_tampering_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "training.jsonl").write_text("original")
            inputs = PreparedInputs.__new__(PreparedInputs)
            inputs.root = root
            inputs._verified = {}
            inputs._rows = {}
            with (
                mock.patch.object(InputRun, "verify"),
                mock.patch.object(
                    InputRun, "_selected_rows", return_value=iter([{"values": [1]}])
                ) as loader,
            ):
                first = list(inputs._selected_rows("training.jsonl", "development", "1405"))
                first[0]["values"][0] = 999
                self.assertEqual(
                    list(inputs._selected_rows("training.jsonl", "development", "1405")),
                    [{"values": [1]}],
                )
                self.assertEqual(loader.call_count, 1)
                (root / "training.jsonl").write_text("tampered")
                with self.assertRaisesRegex(ValueError, "changed"):
                    list(inputs._selected_rows("training.jsonl", "development", "1405"))
            with self.assertRaisesRegex(ValueError, "restricted"):
                list(inputs._selected_rows("training.jsonl", "final", "1405"))

    def test_diagnostics_preserve_parameters_gradients_rng_and_mode(self):
        for device in ["cpu", "cuda"] if torch.cuda.is_available() else ["cpu"]:
            with self.subTest(device=device):
                self._diagnostic_invariance(device)

    def _diagnostic_invariance(self, device):
        torch.manual_seed(13)
        model = ForecastGRU().to(device).eval()
        reference = frozen_reference(model)
        for parameter in model.parameters():
            parameter.grad = torch.ones_like(parameter)
        before = state_digest(model.state_dict())
        gradients = state_digest([p.grad for p in model.parameters()])
        rng = torch.get_rng_state().clone()
        cuda_rng = torch.cuda.get_rng_state().clone() if device == "cuda" else None
        record = {
            "x_hist": [[0.2] * 7 for _ in range(24)],
            "c_future": [[0.1] * 5 for _ in range(24)],
            "y_scaled": [0.3] * 24,
        }
        result = measure(model, reference, torch.ones(64), record, 2.0, epsilon=0.001, device="cpu")
        self.assertEqual(result["retention_mse"], 0.0)
        self.assertEqual(result["weighted_gradient_ratio"], 0.0)
        self.assertGreater(result["forecast_gradient_norm"], 0.0)
        self.assertEqual(state_digest(model.state_dict()), before)
        self.assertEqual(state_digest([p.grad for p in model.parameters()]), gradients)
        self.assertTrue(torch.equal(torch.get_rng_state(), rng))
        if cuda_rng is not None:
            self.assertTrue(torch.equal(torch.cuda.get_rng_state(), cuda_rng))
        self.assertFalse(model.training)
        self.assertTrue(all(p.grad is None for p in reference.parameters()))
