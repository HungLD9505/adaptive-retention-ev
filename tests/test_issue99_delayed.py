"""Pilot-only delayed controller, virtual-real and resume checks."""

import json
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import torch

from ev_control.continuous import WindowRule
from ev_control.delayed import DelayedRule, choose_lambda, observe_delayed_gradient
from ev_models.model import ForecastGRU
from ev_models.training import TrainingConfig, adapt_model, frozen_reference
from ev_runner.continuous import ContinuousRunner
from ev_runner.continuous_run import validate_study
from ev_runner.replay import Labels
from ev_runner.state import Branch, rng_state, state_digest
from ev_runner.store import Store
from tests.test_issue99_study_config import pilot_config


def example(day: int, *, label: bool = True) -> dict:
    row = {
        "x_hist": [[0.2 + day * 0.01] + [0.0] * 5 + [1.0] for _ in range(24)],
        "c_future": [[0.0] * 5 for _ in range(24)],
    }
    if label:
        row["y_scaled"] = [0.5 + day * 0.01] * 24
    return row


class LateReplay:
    def __init__(self) -> None:
        self.start = datetime(2022, 12, 1, tzinfo=timezone.utc)
        self.stop = self.start + timedelta(days=7)
        self.scale = 2.0

    def forecast(self, origin: datetime) -> dict | None:
        day = (origin - self.start).days
        return example(day, label=False) if 0 <= day < 7 else None

    def labels(self, origin: datetime, as_of: datetime) -> Labels:
        arrival = origin + timedelta(days=2)
        if as_of < arrival:
            return Labels("pending", None, arrival)
        day = (origin - self.start).days
        return Labels("complete", tuple([1.0 + day * 0.02] * 24), arrival)


class DelayedTests(unittest.TestCase):
    def setUp(self) -> None:
        torch.manual_seed(42)
        self.reference = frozen_reference(ForecastGRU())
        self.initial = adapt_model(self.reference)
        self.training = TrainingConfig(seed=42, epochs=1, batch_size=1)
        self.delayed = DelayedRule(
            anchor=0.8, decay=0.9, meta_step=10.0, max_step=0.02,
            trust_radius=0.25, history=1, agreement=1,
        )

    def branch(self) -> Branch:
        torch.manual_seed(42)
        model = ForecastGRU()
        model.load_state_dict(self.initial.state_dict())
        return Branch(model, torch.optim.Adam(model.parameters(), lr=0.001), rng_state())

    def test_virtual_step_matches_bound_real_forecast_or_skips(self) -> None:
        branch = self.branch()
        before = branch.snapshot()
        branch.update(
            example(0), weight=0.8, config=self.training, device="cpu",
            reference=self.reference, latent_scale=torch.ones(64), event_index=0,
        )
        prediction = branch.predict(example(1, label=False), device="cpu")
        virtual = Branch.from_snapshot(before, device="cpu", learning_rate=0.001)
        digest_before = state_digest(virtual.snapshot())
        result = observe_delayed_gradient(
            virtual.model, virtual.optimizer, self.reference, torch.ones(64),
            example(0), example(1), prediction, 0.8, epsilon=0.001, device="cpu",
        )
        self.assertEqual(result["status"], "observed")
        self.assertTrue(math.isfinite(result["hypergradient"]))
        self.assertLess(result["virtual_real_max_error"], 1e-5)
        self.assertEqual(state_digest(virtual.snapshot()), digest_before)
        wrong = observe_delayed_gradient(
            virtual.model, virtual.optimizer, self.reference, torch.ones(64),
            example(0), example(1), [value + 0.1 for value in prediction], 0.8,
            epsilon=0.001, device="cpu",
        )
        self.assertEqual(wrong["reason"], "virtual_real_mismatch")

    def test_anchor_gate_and_trust_interval(self) -> None:
        rule = DelayedRule(0.8, 0.9, 10.0, 0.02, 0.25)
        history = [0.002, 0.003, 0.001, 0.002]
        result = choose_lambda(0.8, history, 0.002, rule, 2.0)
        self.assertTrue(result["gate_pass"])
        self.assertAlmostEqual(result["lambda_after"], 0.78)
        uncertain = choose_lambda(1.0, [0.002, 0.003, -0.001, -0.002], -0.003, rule, 2.0)
        self.assertFalse(uncertain["gate_pass"])
        self.assertAlmostEqual(uncertain["lambda_after"], 0.98)
        reset = choose_lambda(1.0, history, None, rule, 2.0)
        self.assertEqual(reset["gradient_history"], history)
        self.assertFalse(reset["gate_pass"])
        self.assertAlmostEqual(reset["lambda_after"], 0.98)

    def test_late_label_decisions_and_resume_match(self) -> None:
        replay = LateReplay()
        rule = WindowRule(1, 1, 2.0, 0.01, 0.001)
        binding = {"schema": "issue99-delayed-test", "input": "synthetic"}

        def run(store: Store, stop: datetime) -> ContinuousRunner:
            runner = ContinuousRunner(
                replay, self.branch(), self.reference, torch.ones(64), rule,
                self.training, store, initial_lambda=0.8, device="cpu", cadence=1,
                delayed_rule=self.delayed,
            )
            runner.run_until(stop)
            return runner

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary)
            full_store = Store(root / "full", binding)
            full = run(full_store, replay.stop + timedelta(days=2))
            partial_store = Store(root / "partial", binding)
            run(partial_store, replay.start + timedelta(days=3))
            resumed_store = Store(root / "resumed", binding, resume_from=root / "partial")
            resumed = run(resumed_store, replay.stop + timedelta(days=2))
            full_state, resumed_state = full.snapshot(), resumed.snapshot()
            full_state.pop("cost")
            resumed_state.pop("cost")
            self.assertEqual(state_digest(full_state), state_digest(resumed_state))
            self.assertEqual(full.current_lambda, resumed.current_lambda)
            self.assertGreater(full.virtual_steps, 0)
            for index in range(full_store.count):
                folder = f"tick-{index:04d}"
                for name in ("events.jsonl", "forecasts.json"):
                    self.assertEqual(
                        (root / "full" / folder / name).read_bytes(),
                        (root / "resumed" / folder / name).read_bytes(),
                    )
                events = [
                    json.loads(line)
                    for line in (root / "full" / folder / "events.jsonl").read_text().splitlines()
                ]
                for event in events:
                    if event["event"] == "meta_decision":
                        self.assertLess(event["v_origin"], event["origin"])
                        self.assertLessEqual(event["available_at"], event["as_of"])
                        self.assertGreaterEqual(
                            datetime.fromisoformat(event["as_of"])
                            - datetime.fromisoformat(event["origin"]),
                            timedelta(days=2),
                        )

    def test_config_rejects_scored_or_multistep_delayed(self) -> None:
        config = pilot_config()
        config["frozen_lambda"] = False
        config["initial_lambda"] = 0.8
        config["controller_variant"] = "delayed"
        config["delayed_rule"] = {
            "anchor": 0.8, "decay": 0.9, "meta_step": 10.0,
            "max_step": 0.02, "trust_radius": 0.25,
            "history": 5, "agreement": 4,
        }
        validate_study(config)
        config["phase"] = "evaluation"
        config["protocol_sha256"] = "a" * 64
        config["objective_origins"] = ["2022-12-01T00:00:00+00:00"]
        with self.assertRaisesRegex(ValueError, "pilot-only"):
            validate_study(config)
        config["phase"] = "pilot"
        config["protocol_sha256"] = None
        config["objective_origins"] = []
        config["online_training"]["epochs"] = 2
        with self.assertRaisesRegex(ValueError, "one online epoch"):
            validate_study(config)


if __name__ == "__main__":
    unittest.main()
