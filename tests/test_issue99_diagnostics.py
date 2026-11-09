"""Independent nonmutation and scalar checks for issue #99 diagnostics."""

import copy
import json
import math
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import torch

from ev_control.continuous import WindowRule
from ev_control.diagnostics import DiagnosticConfig, measure
from ev_models.model import ForecastGRU
from ev_models.training import TrainingConfig, frozen_reference
from ev_runner.continuous import ContinuousRunner
from ev_runner.continuous_run import validate_study
from ev_runner.state import Branch, rng_state, state_digest
from ev_runner.store import Store
from tests.test_issue99_continuous_runner import ToyReplay


def record() -> dict:
    return {
        "x_hist": [[0.2] + [0.0] * 5 + [1.0] for _ in range(24)],
        "c_future": [[0.0] * 5 for _ in range(24)],
        "y_scaled": [0.4] * 24,
    }


class DiagnosticTests(unittest.TestCase):
    def test_study_config_accepts_optional_pilot_and_requires_scored_diagnostics(self):
        from test_issue99_study_config import pilot_config

        pilot = pilot_config()
        validate_study(pilot)
        pilot["diagnostics"] = {"cadence": 7, "epsilon_g": 1e-12}
        validate_study(pilot)
        pilot["diagnostics"]["epsilon_g"] = 0
        with self.assertRaises(ValueError):
            validate_study(pilot)
        pilot["diagnostics"] = {"cadence": 7, "epsilon_g": 1e-12}
        pilot["phase"] = "calibration"
        pilot["protocol_sha256"] = "a" * 64
        pilot["objective_origins"] = ["2022-12-01T00:00:00+08:00"]
        validate_study(pilot)
        del pilot["diagnostics"]
        with self.assertRaises(ValueError):
            validate_study(pilot)

    def test_zero_at_identical_source_and_invariant_state(self):
        torch.manual_seed(42)
        model = ForecastGRU()
        reference = frozen_reference(model)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        before_model = copy.deepcopy(model.state_dict())
        before_optimizer = copy.deepcopy(optimizer.state_dict())
        before_rng = rng_state()
        model.train()
        result = measure(
            model,
            reference,
            torch.ones(64),
            [record()],
            weight=0.5,
            retention_epsilon=0.001,
            epsilon_g=1e-12,
            device="cpu",
        )
        self.assertEqual(result["retention_mse"], 0.0)
        self.assertEqual(result["encoder_weighted_retention_grad_norm"], 0.0)
        self.assertIsNone(result["encoder_forecast_retention_alignment"])
        self.assertTrue(model.training)
        self.assertEqual(state_digest(model.state_dict()), state_digest(before_model))
        self.assertEqual(state_digest(optimizer.state_dict()), state_digest(before_optimizer))
        self.assertEqual(state_digest(rng_state()), state_digest(before_rng))
        self.assertFalse(any(parameter.grad is not None for parameter in reference.parameters()))

    def test_lambda_zero_keeps_retention_diagnostic_and_ratio_zero(self):
        torch.manual_seed(11)
        model = ForecastGRU()
        reference = frozen_reference(model)
        with torch.no_grad():
            next(model.encoder.parameters()).add_(0.1)
        result = measure(
            model,
            reference,
            torch.ones(64),
            [record()],
            weight=0.0,
            retention_epsilon=0.001,
            epsilon_g=1e-10,
            device="cpu",
        )
        self.assertGreater(result["retention_mse"], 0)
        self.assertEqual(result["lambda_times_retention"], 0)
        self.assertEqual(result["encoder_grad_ratio"], 0)
        self.assertTrue(math.isfinite(result["latent_displacement_l2_mean"]))

    @unittest.skipUnless(torch.cuda.is_available(), "CUDA unavailable")
    def test_cuda_diagnostics_restore_eval_mode_model_optimizer_and_rng(self):
        torch.manual_seed(123)
        model = ForecastGRU().cuda()
        reference = frozen_reference(model)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        model.eval()
        before_model = state_digest(model.state_dict())
        before_optimizer = state_digest(optimizer.state_dict())
        before_rng = state_digest(rng_state())
        result = measure(
            model,
            reference,
            torch.ones(64, device="cuda"),
            [record()],
            weight=0.1,
            retention_epsilon=0.001,
            epsilon_g=1e-12,
            device="cuda",
        )
        self.assertTrue(math.isfinite(result["encoder_forecast_grad_norm"]))
        self.assertFalse(model.training)
        self.assertEqual(state_digest(model.state_dict()), before_model)
        self.assertEqual(state_digest(optimizer.state_dict()), before_optimizer)
        self.assertEqual(state_digest(rng_state()), before_rng)

    def test_invalid_cadence_and_scale_fail(self):
        with self.assertRaises(ValueError):
            DiagnosticConfig(cadence=0, epsilon_g=1e-12)
        with self.assertRaises(ValueError):
            DiagnosticConfig(cadence=1, epsilon_g=0)
        torch.manual_seed(2)
        model = ForecastGRU()
        reference = frozen_reference(model)
        with self.assertRaises(ValueError):
            measure(
                model,
                reference,
                torch.full((64,), float("nan")),
                [record()],
                weight=1.0,
                retention_epsilon=0.001,
                epsilon_g=1e-12,
                device="cpu",
            )

    def test_fixed_diagnostics_are_bound_and_do_not_change_forecasts_or_resume(self):
        replay = ToyReplay()
        torch.manual_seed(42)
        source = ForecastGRU()
        reference = frozen_reference(source)
        initial_state = copy.deepcopy(source.state_dict())
        training = TrainingConfig(seed=42, epochs=1, batch_size=1)
        rule = WindowRule(1, 1, 1.0, 0.01, 0.001)

        def run(path, diagnostics, resume=None, stop=None):
            torch.manual_seed(42)
            model = ForecastGRU()
            model.load_state_dict(initial_state)
            branch = Branch(
                model, torch.optim.Adam(model.parameters(), lr=training.learning_rate), rng_state()
            )
            store = Store(
                path, {"test": "diagnostics", "config": str(diagnostics)}, resume_from=resume
            )
            runner = ContinuousRunner(
                replay,
                branch,
                reference,
                torch.ones(64),
                rule,
                training,
                store,
                initial_lambda=0.3,
                device="cpu",
                cadence=1,
                frozen_lambda=True,
                diagnostics=diagnostics,
            )
            runner.run_until(stop or replay.stop)
            return runner

        with tempfile.TemporaryDirectory(dir=".cache") as temp:
            root = Path(temp)
            baseline = run(root / "baseline", None)
            config = DiagnosticConfig(cadence=1, epsilon_g=1e-12)
            full = run(root / "full", config)
            run(root / "partial", config, stop=replay.start + timedelta(days=1))
            resumed = run(root / "resumed", config, resume=root / "partial")
            self.assertEqual(
                state_digest(baseline.branch.snapshot()), state_digest(full.branch.snapshot())
            )
            self.assertEqual(
                state_digest(full.branch.snapshot()), state_digest(resumed.branch.snapshot())
            )
            for index in range(4):
                folder = f"tick-{index:04d}"
                forecast = (root / "baseline" / folder / "forecasts.json").read_bytes()
                self.assertEqual(forecast, (root / "full" / folder / "forecasts.json").read_bytes())
                self.assertEqual(
                    (root / "full" / folder / "events.jsonl").read_bytes(),
                    (root / "resumed" / folder / "events.jsonl").read_bytes(),
                )
            events = [
                json.loads(line)
                for tick in sorted((root / "full").glob("tick-*"))
                for line in (tick / "events.jsonl").read_text().splitlines()
            ]
            measured = [event for event in events if event["event"] == "retention_diagnostics"]
            self.assertEqual(len(measured), 3)
            self.assertTrue(all(event["examples"] == 1 for event in measured))


if __name__ == "__main__":
    unittest.main()
