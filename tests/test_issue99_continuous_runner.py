"""Small synthetic interrupted/resumed continuous replay identity fixture."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import torch

from ev_control.continuous import WindowRule, decide
from ev_models.model import ForecastGRU
from ev_models.training import TrainingConfig, adapt_model, frozen_reference
from ev_runner.continuous import ContinuousRunner
from ev_runner.replay import Labels
from ev_runner.state import Branch, rng_state, state_digest
from ev_runner.store import Store


class ToyReplay:
    def __init__(self):
        self.start = datetime(2022, 12, 1, tzinfo=timezone.utc)
        self.stop = self.start + timedelta(days=3)
        self.scale = 2.0
        self.records = {}
        for day in range(3):
            origin = self.start + timedelta(days=day)
            self.records[origin] = {
                "x_hist": [[0.2 + day * 0.01] + [0.0] * 5 + [1.0] for _ in range(24)],
                "c_future": [[0.0] * 5 for _ in range(24)],
            }

    def forecast(self, origin):
        return self.records.get(origin)

    def labels(self, origin, as_of):
        arrival = origin + timedelta(days=1)
        if as_of < arrival:
            return Labels("pending", None, arrival)
        return Labels("complete", tuple([0.5] * 24), arrival)


class ContinuousRunnerTests(unittest.TestCase):
    def test_virtual_decision_restores_prediction_mode(self):
        for device in ("cpu", "cuda") if torch.cuda.is_available() else ("cpu",):
            model = ForecastGRU().to(device)
            reference = frozen_reference(ForecastGRU().to(device))
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            model.eval()
            record = {
                "x_hist": [[0.2] + [0.0] * 5 + [1.0] for _ in range(24)],
                "c_future": [[0.0] * 5 for _ in range(24)],
                "y_scaled": [0.5] * 24,
            }
            a = [{"origin": "2022-12-01", "trained": True, "record": record}]
            v = [{"origin": "2022-12-02", "trained": False, "record": record}]
            rule = WindowRule(1, 1, 1.0, 0.01, 0.001)
            result = decide(
                model, optimizer, reference, torch.ones(64), a, v, 0.1, rule, device=device
            )
            self.assertFalse(model.training)
            self.assertEqual(result["virtual_adam_steps"], 1)

    def test_resume_matches_full_predictions_and_state(self):
        torch.manual_seed(42)
        source = ForecastGRU()
        reference = frozen_reference(source)
        initial = adapt_model(source)
        initial_state = initial.state_dict()
        replay = ToyReplay()
        rule = WindowRule(
            older_count=1, newer_count=1, upper_bound=2.0, meta_step_size=0.01, epsilon=0.001
        )
        training = TrainingConfig(seed=42, epochs=1, batch_size=1)
        binding = {
            "schema": "issue99-test-binding",
            "input": "synthetic",
            "source": state_digest(reference.state_dict()),
        }

        def branch():
            torch.manual_seed(42)
            model = ForecastGRU()
            model.load_state_dict(initial_state)
            return Branch(
                model, torch.optim.Adam(model.parameters(), lr=training.learning_rate), rng_state()
            )

        def run(store, stop):
            runner = ContinuousRunner(
                replay,
                branch(),
                reference,
                torch.ones(64),
                rule,
                training,
                store,
                initial_lambda=0.5,
                device="cpu",
                cadence=1,
            )
            runner.run_until(stop)
            return runner

        with tempfile.TemporaryDirectory(dir=".cache") as temp:
            root = Path(temp)
            full_store = Store(root / "full", binding)
            full = run(full_store, replay.stop)
            partial_store = Store(root / "partial", binding)
            run(partial_store, replay.start + timedelta(days=1))
            resumed_store = Store(root / "resumed", binding, resume_from=root / "partial")
            resumed = run(resumed_store, replay.stop)
            self.assertEqual(full.current_lambda, resumed.current_lambda)
            self.assertEqual(
                state_digest(full.branch.snapshot()), state_digest(resumed.branch.snapshot())
            )
            self.assertEqual(full.virtual_steps, resumed.virtual_steps)
            for index in range(full_store.count):
                folder = f"tick-{index:04d}"
                original = json.loads((root / "full" / folder / "forecasts.json").read_text())
                restored = json.loads((root / "resumed" / folder / "forecasts.json").read_text())
                self.assertEqual(original, restored)
                first_events = [
                    json.loads(line)
                    for line in (root / "full" / folder / "events.jsonl").read_text().splitlines()
                ]
                resumed_events = [
                    json.loads(line)
                    for line in (root / "resumed" / folder / "events.jsonl")
                    .read_text()
                    .splitlines()
                ]
                self.assertEqual(first_events, resumed_events)
                if index > 0:
                    previous = json.loads(
                        (root / "full" / f"tick-{index - 1:04d}" / "forecasts.json").read_text()
                    )
                    score = next(event for event in first_events if event["event"] == "score")
                    expected = (
                        sum(abs(value * replay.scale - 0.5) for value in previous["prediction"])
                        / 24
                    )
                    self.assertAlmostEqual(score["mae_kwh"], expected)


if __name__ == "__main__":
    unittest.main()
