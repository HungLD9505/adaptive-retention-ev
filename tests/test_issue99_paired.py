"""Paired counterfactual pilot fixtures with delayed labels and exact resume."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import torch

from ev_control.continuous import WindowRule
from ev_control.paired import PairedRule, accept, propose
from ev_models.model import ForecastGRU
from ev_models.training import TrainingConfig, adapt_model, frozen_reference
from ev_runner.continuous import ContinuousRunner
from ev_runner.continuous_run import validate_study
from ev_runner.replay import Labels
from ev_runner.state import Branch, rng_state, state_digest
from ev_runner.store import Store
from tests.test_issue99_study_config import pilot_config


class LateReplay:
    def __init__(self, *, changed_day: int | None = None) -> None:
        self.start = datetime(2022, 12, 1, tzinfo=timezone.utc)
        self.stop = self.start + timedelta(days=9)
        self.scale = 2.0
        self.changed_day = changed_day

    def forecast(self, origin: datetime) -> dict | None:
        day = (origin - self.start).days
        if not 0 <= day < 9:
            return None
        return {
            "x_hist": [[0.2 + day * 0.01] + [0.0] * 5 + [1.0] for _ in range(24)],
            "c_future": [[0.0] * 5 for _ in range(24)],
        }

    def labels(self, origin: datetime, as_of: datetime) -> Labels:
        arrival = origin + timedelta(days=2)
        if as_of < arrival:
            return Labels("pending", None, arrival)
        day = (origin - self.start).days
        value = 1.0 + day * 0.02 + (1.0 if day == self.changed_day else 0.0)
        return Labels("complete", tuple([value] * 24), arrival)


class PairedTests(unittest.TestCase):
    def setUp(self) -> None:
        torch.manual_seed(42)
        source = ForecastGRU()
        self.reference = frozen_reference(source)
        self.initial = adapt_model(source)
        self.training = TrainingConfig(seed=42, epochs=1, batch_size=1)
        self.rule = WindowRule(2, 1, 2.0, 0.01, 0.001)
        self.paired = PairedRule(
            anchor=0.8, eta=10.0, max_abs_lambda_step=0.05,
            anchor_trust_radius=0.25, valid_complete_pairs=3,
            max_wait_issued_days=7,
            median_candidate_minus_incumbent_mae_kwh_below=-0.01,
            minimum_candidate_wins=2,
        )

    def branch(self) -> Branch:
        torch.manual_seed(42)
        model = ForecastGRU()
        model.load_state_dict(self.initial.state_dict())
        return Branch(model, torch.optim.Adam(model.parameters(), lr=0.001), rng_state())

    def execute_replay(self, replay: LateReplay, store: Store, stop: datetime) -> ContinuousRunner:
        runner = ContinuousRunner(
            replay, self.branch(), self.reference, torch.ones(64), self.rule,
            self.training, store, initial_lambda=0.8, device="cpu", cadence=1,
            paired_rule=self.paired,
        )
        runner.run_until(stop)
        return runner

    @staticmethod
    def events(root: Path) -> list[dict]:
        return [
            json.loads(line)
            for tick in sorted(root.glob("tick-*"))
            for line in (tick / "events.jsonl").read_text().splitlines()
        ]

    def test_proposal_is_bounded_and_acceptance_needs_three_labels(self) -> None:
        proposal = propose(0.8, -0.01, self.paired, 2.0)
        self.assertAlmostEqual(proposal["candidate"], 0.85)
        self.assertAlmostEqual(proposal["raw_step"], -0.05)
        self.assertTrue(accept([-0.02, -0.03, 0.01], self.paired)["accepted"])
        self.assertFalse(accept([-0.005, -0.03, 0.01], self.paired)["accepted"])
        self.assertFalse(accept([-0.02, 0.02, 0.01], self.paired)["accepted"])
        with self.assertRaises(ValueError):
            accept([-0.02], self.paired)

    def test_causal_pairs_shadow_equivalence_and_exact_resume(self) -> None:
        replay = LateReplay()
        binding = {"schema": "issue99-paired-test", "input": "synthetic"}
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary)
            full_store = Store(root / "full", binding)
            full = self.execute_replay(replay, full_store, replay.stop + timedelta(days=2))
            partial_store = Store(root / "partial", binding)
            self.execute_replay(replay, partial_store, replay.start + timedelta(days=5))
            resumed_store = Store(root / "resumed", binding, resume_from=root / "partial")
            resumed = self.execute_replay(replay, resumed_store, replay.stop + timedelta(days=2))
            first, second = full.snapshot(), resumed.snapshot()
            first.pop("cost")
            second.pop("cost")
            self.assertEqual(state_digest(first), state_digest(second))
            self.assertEqual(full.virtual_steps, resumed.virtual_steps)
            for index in range(full_store.count):
                folder = f"tick-{index:04d}"
                for name in ("forecasts.json", "events.jsonl"):
                    self.assertEqual(
                        (root / "full" / folder / name).read_bytes(),
                        (root / "resumed" / folder / name).read_bytes(),
                    )
            events = self.events(root / "full")
            paired = [event for event in events if event["event"] == "paired_observation"]
            decisions = [event for event in events if event["event"] == "meta_decision"]
            self.assertGreaterEqual(len(paired), 3)
            self.assertGreaterEqual(len(decisions), 1)
            self.assertTrue(all(event["incumbent_shadow_max_error"] < 1e-5 for event in (
                json.loads((tick / "forecasts.json").read_text())["paired"]
                for tick in sorted((root / "full").glob("tick-*"))
                if "paired" in json.loads((tick / "forecasts.json").read_text())
            )))
            for event in paired:
                self.assertLess(event["v_origin"], event["origin"])
                self.assertLessEqual(event["available_at"], event["as_of"])
                self.assertGreaterEqual(
                    datetime.fromisoformat(event["as_of"])
                    - datetime.fromisoformat(event["origin"]),
                    timedelta(days=2),
                )
            self.assertEqual(len(decisions[0]["paired_differences_kwh"]), 3)

    def test_future_changed_label_cannot_change_earlier_forecasts(self) -> None:
        binding = {"schema": "issue99-paired-future-test", "input": "synthetic"}
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary)
            first = LateReplay()
            second = LateReplay(changed_day=5)
            self.execute_replay(first, Store(root / "first", binding), first.start + timedelta(days=6))
            self.execute_replay(second, Store(root / "second", binding), second.start + timedelta(days=6))
            for index in range(7):
                folder = f"tick-{index:04d}"
                for name in ("forecasts.json", "events.jsonl"):
                    self.assertEqual(
                        (root / "first" / folder / name).read_bytes(),
                        (root / "second" / folder / name).read_bytes(),
                    )

    def test_config_rejects_scored_paired_controller(self) -> None:
        config = pilot_config()
        config["frozen_lambda"] = False
        config["initial_lambda"] = 0.8
        config["controller_variant"] = "paired"
        config["paired_rule"] = vars(self.paired).copy()
        validate_study(config)
        config["phase"] = "evaluation"
        config["protocol_sha256"] = "a" * 64
        config["objective_origins"] = ["2022-12-01T00:00:00+00:00"]
        with self.assertRaisesRegex(ValueError, "pilot-only"):
            validate_study(config)


if __name__ == "__main__":
    unittest.main()
