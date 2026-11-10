"""Persistent candidate controller: causal labels, decisions, binding, and resume."""

import json
import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import torch

from ev_control.continuous import WindowRule
from ev_control.persistent import PersistentRule, accept, propose
from ev_models.checkpoint import digest
from ev_models.model import ForecastGRU
from ev_models.training import TrainingConfig, adapt_model, frozen_reference
from ev_runner.continuous import ContinuousRunner
from ev_runner.continuous_run import validate_controller_protocol, validate_study
from ev_runner.persistent import PersistentCandidate, branch_digests
from ev_runner.replay import Labels
from ev_runner.state import Branch, identity, rng_state, state_digest
from ev_runner.store import Store
from tests.test_issue99_study_config import pilot_config


class LateReplay:
    def __init__(self, *, changed_day: int | None = None, stall_after: int | None = None) -> None:
        self.start = datetime(2022, 12, 1, tzinfo=timezone.utc)
        self.stop = self.start + timedelta(days=15)
        self.scale = 2.0
        self.changed_day, self.stall_after = changed_day, stall_after

    def forecast(self, origin: datetime) -> dict | None:
        day = (origin - self.start).days
        if not 0 <= day < 15:
            return None
        return {
            "x_hist": [[0.2 + day * 0.01] + [0.0] * 5 + [1.0] for _ in range(24)],
            "c_future": [[0.0] * 5 for _ in range(24)],
        }

    def labels(self, origin: datetime, as_of: datetime) -> Labels:
        day = (origin - self.start).days
        delay = 3 if day == 3 else 2
        if self.stall_after is not None and day >= self.stall_after:
            delay = 20
        arrival = origin + timedelta(days=delay)
        if as_of < arrival:
            return Labels("pending", None, arrival)
        value = 1.0 + day * 0.02 + (1.0 if day == self.changed_day else 0.0)
        return Labels("complete", tuple([value] * 24), arrival)


class PersistentTests(unittest.TestCase):
    def setUp(self) -> None:
        torch.manual_seed(42)
        source = ForecastGRU()
        self.reference = frozen_reference(source)
        self.initial = adapt_model(source)
        self.training = TrainingConfig(seed=42, epochs=1, batch_size=1)
        self.window_rule = WindowRule(2, 1, 2.0, 0.01, 0.001)
        self.rule = PersistentRule(
            anchor=0.8,
            eta=10.0,
            max_abs_lambda_step=0.1,
            anchor_trust_radius=0.25,
            valid_complete_pairs=5,
            max_wait_issued_days=9,
            mean_candidate_minus_incumbent_mae_kwh_below=-0.01,
            minimum_candidate_wins=4,
            max_candidate_harm_kwh=0.05,
        )

    def branch(self) -> Branch:
        torch.manual_seed(42)
        model = ForecastGRU()
        model.load_state_dict(self.initial.state_dict())
        return Branch(model, torch.optim.Adam(model.parameters(), lr=0.001), rng_state())

    def execute_replay(self, replay: LateReplay, store: Store, stop: datetime) -> ContinuousRunner:
        runner = ContinuousRunner(
            replay,
            self.branch(),
            self.reference,
            torch.ones(64),
            self.window_rule,
            self.training,
            store,
            initial_lambda=0.8,
            device="cpu",
            cadence=1,
            persistent_rule=self.rule,
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

    def test_proposal_and_acceptance_require_mean_wins_and_harm(self) -> None:
        offered = propose(0.8, -0.1, self.rule, 2.0)
        self.assertAlmostEqual(offered["candidate"], 0.9)
        self.assertAlmostEqual(offered["raw_step"], -0.1)
        self.assertTrue(accept([-0.04, -0.03, -0.02, -0.01, 0.04], self.rule)["accepted"])
        self.assertFalse(accept([-0.06] * 4 + [0.06], self.rule)["accepted"])
        self.assertFalse(accept([-0.08] * 3 + [0.01] * 2, self.rule)["accepted"])
        self.assertFalse(accept([-0.01] * 4 + [0.01], self.rule)["accepted"])
        with self.assertRaises(ValueError):
            accept([-0.02], self.rule)

    def test_candidate_clone_is_independent_and_accept_discards_only_shadow(self) -> None:
        real = self.branch()
        manager = PersistentCandidate(
            self.rule, self.training, self.reference, torch.ones(64), device="cpu"
        )
        started = manager.start(
            real, 0.8, -0.01, 2.0, datetime(2022, 12, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(started["event"], "persistent_proposal")
        self.assertEqual(branch_digests(real), branch_digests(manager.branch))
        real_before = branch_digests(real)
        self.assertEqual(branch_digests(real), real_before)
        # Force the decision mechanism after five causally available synthetic pairs;
        # the numerical acceptance rule is tested separately above.
        now = datetime(2022, 12, 10, tzinfo=timezone.utc)
        malformed = {
            "origin": now.isoformat(),
            "lambda": 0.8,
            "prediction": [0.2] * 24,
            "prediction_sha256": "forecast",
            "paired": {
                "block_id": started["block_id"],
                "candidate_lambda": started["candidate"],
                "candidate_prediction": [0.1] * 24,
                "candidate_prediction_id": "wrong-hash",
            },
        }
        with self.assertRaisesRegex(ValueError, "malformed persistent forecast"):
            manager.observe(
                malformed, [0.1] * 24, now + timedelta(days=1),
                now + timedelta(days=1), 2.0,
            )
        with patch("ev_runner.persistent.accept", return_value={
            "accepted": True,
            "mean_candidate_minus_incumbent_mae_kwh": -0.02,
            "candidate_wins": 5,
            "max_candidate_harm_kwh": -0.01,
            "paired_differences_kwh": [-0.02] * 5,
        }):
            for index in range(5):
                origin = now + timedelta(days=index)
                manager.issued(True)
                issued = {
                    "origin": origin.isoformat(),
                    "lambda": 0.8,
                    "prediction": [0.2] * 24,
                    "prediction_sha256": str(index),
                    "paired": {
                        "block_id": started["block_id"],
                        "candidate_lambda": started["candidate"],
                        "candidate_prediction": [0.1] * 24,
                        "candidate_prediction_id": identity(
                            {"origin": origin.isoformat(), "prediction": [0.1] * 24}
                        ),
                    },
                }
                _, decision = manager.observe(
                    issued, [0.1] * 24, origin + timedelta(days=1),
                    origin + timedelta(days=1), 2.0,
                )
        self.assertTrue(decision["accepted"])
        self.assertIsNone(manager.branch)
        self.assertEqual(branch_digests(real), real_before)

    def test_late_labels_multiple_arrivals_and_resume_identity(self) -> None:
        replay = LateReplay()
        binding = {"schema": "issue99-persistent-test", "input": "synthetic"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            full_store = Store(root / "full", binding)
            full = self.execute_replay(replay, full_store, replay.stop + timedelta(days=2))
            partial_store = Store(root / "partial", binding)
            partial = self.execute_replay(
                replay, partial_store, replay.start + timedelta(days=7)
            )
            self.assertIsNotNone(partial.persistent.block)
            self.assertIsNotNone(partial.persistent.branch)
            resumed_store = Store(root / "resumed", binding, resume_from=root / "partial")
            resumed = self.execute_replay(replay, resumed_store, replay.stop + timedelta(days=2))
            first, second = full.snapshot(), resumed.snapshot()
            first.pop("cost")
            second.pop("cost")
            first["persistent"].pop("shadow_seconds")
            second["persistent"].pop("shadow_seconds")
            self.assertEqual(state_digest(first), state_digest(second))
            for index in range(full_store.count):
                folder = f"tick-{index:04d}"
                for name in ("forecasts.json", "events.jsonl"):
                    self.assertEqual(
                        (root / "full" / folder / name).read_bytes(),
                        (root / "resumed" / folder / name).read_bytes(),
                    )
                tick = root / "full" / folder
                manifest = json.loads((tick / "commit.json").read_text())
                self.assertEqual(digest(tick / "forecasts.json"), manifest["files"]["forecasts.json"])
                issued = json.loads((tick / "forecasts.json").read_text())
                if "paired" in issued:
                    self.assertEqual(
                        issued["paired"]["candidate_prediction_id"],
                        identity({
                            "origin": issued["origin"],
                            "prediction": issued["paired"]["candidate_prediction"],
                        }),
                    )
            events = self.events(root / "full")
            shadows = [event for event in events if event["event"] == "persistent_shadow_update"]
            actual = [event for event in events if event["event"] == "actual_update"]
            self.assertGreaterEqual(len(shadows), 5)
            self.assertTrue(all(row["real_steps"] == row["shadow_steps"] for row in shadows))
            self.assertTrue(all(row["origin"] in {event["origin"] for event in actual} for row in shadows))
            observations = [event for event in events if event["event"] == "persistent_observation"]
            self.assertGreaterEqual(len(observations), 5)
            for row in observations:
                self.assertLessEqual(row["available_at"], row["as_of"])
                self.assertLess(row["origin"], row["as_of"])
            self.assertTrue(any(
                sum(row["as_of"] == other["as_of"] for other in shadows) > 1
                for row in shadows
            ))

    def test_accepted_proposal_changes_lambda_without_branch_transplant(self) -> None:
        replay = LateReplay()
        binding = {"schema": "issue99-persistent-adoption-test", "input": "synthetic"}
        forced = {
            "accepted": True,
            "mean_candidate_minus_incumbent_mae_kwh": -0.02,
            "candidate_wins": 5,
            "max_candidate_harm_kwh": -0.01,
            "paired_differences_kwh": [-0.02] * 5,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch("ev_runner.persistent.accept", return_value=forced):
                runner = self.execute_replay(
                    replay, Store(root / "run", binding), replay.start + timedelta(days=12)
                )
            decisions = [
                row for row in self.events(root / "run")
                if row["event"] == "meta_decision"
            ]
            self.assertTrue(decisions)
            self.assertTrue(all(row["accepted"] for row in decisions))
            self.assertTrue(all(
                row["real_state_before"] == row["real_state_after"] for row in decisions
            ))
            self.assertTrue(all("candidate_state" in row for row in decisions))
            self.assertNotEqual(runner.current_lambda, self.rule.anchor)

    def test_future_label_cannot_change_earlier_forecast_or_decision(self) -> None:
        binding = {"schema": "issue99-persistent-future-test", "input": "synthetic"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            normal = LateReplay()
            changed = LateReplay(changed_day=7)
            self.execute_replay(normal, Store(root / "normal", binding), normal.start + timedelta(days=8))
            self.execute_replay(changed, Store(root / "changed", binding), changed.start + timedelta(days=8))
            for index in range(9):
                folder = f"tick-{index:04d}"
                for name in ("forecasts.json", "events.jsonl"):
                    self.assertEqual(
                        (root / "normal" / folder / name).read_bytes(),
                        (root / "changed" / folder / name).read_bytes(),
                    )

    def test_timeout_disposes_candidate_without_lambda_change(self) -> None:
        replay = LateReplay(stall_after=4)
        binding = {"schema": "issue99-persistent-timeout-test", "input": "synthetic"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = self.execute_replay(
                replay, Store(root / "run", binding), replay.stop
            )
            events = self.events(root / "run")
            self.assertTrue(any(
                row["event"] == "persistent_timeout"
                and row["status"] == "expired"
                and row["issued_days"] == self.rule.max_wait_issued_days
                for row in events
            ))
            self.assertFalse(any(row["event"] == "meta_decision" for row in events))
            self.assertEqual(runner.current_lambda, self.rule.anchor)

    def test_scored_protocol_binds_variant_and_rule(self) -> None:
        config = pilot_config()
        config["frozen_lambda"] = False
        config["initial_lambda"] = self.rule.anchor
        config["controller_variant"] = "persistent_v1"
        config["persistent_rule"] = vars(self.rule).copy()
        validate_study(config)
        protocol = {
            "controller_variant": "persistent_v1",
            "persistent_rule": config["persistent_rule"].copy(),
        }
        validate_controller_protocol(config, protocol)
        protocol["persistent_rule"]["max_abs_lambda_step"] = 0.2
        with self.assertRaisesRegex(ValueError, "locked protocol"):
            validate_controller_protocol(config, protocol)
        protocol["persistent_rule"] = config["persistent_rule"].copy()
        common = {
            "cadence": 1,
            "meta_step_size": config["window_rule"]["meta_step_size"],
            "upper_bound": config["window_rule"]["upper_bound"],
        }
        protocol["persistent_experiment"] = {"method_configs": {
            "lambda0": {**common, "initial_lambda": 0.0, "frozen_lambda": True,
                        "controller_variant": "immediate"},
            "fixed": {**common, "initial_lambda": self.rule.anchor, "frozen_lambda": True,
                      "controller_variant": "immediate"},
            "immediate": {**common, "initial_lambda": self.rule.anchor, "frozen_lambda": False,
                          "controller_variant": "immediate"},
            "persistent": {**common, "initial_lambda": self.rule.anchor,
                           "frozen_lambda": False, "controller_variant": "persistent_v1"},
        }}
        for method, locked in protocol["persistent_experiment"]["method_configs"].items():
            arm = copy.deepcopy(config)
            arm["initial_lambda"] = locked["initial_lambda"]
            arm["frozen_lambda"] = locked["frozen_lambda"]
            arm["controller_variant"] = locked["controller_variant"]
            if method != "persistent":
                del arm["persistent_rule"]
            validate_study(arm)
            validate_controller_protocol(arm, protocol)
        mismatched = copy.deepcopy(config)
        mismatched["persistent_rule"]["max_abs_lambda_step"] = 0.2
        with self.assertRaisesRegex(ValueError, "locked protocol"):
            validate_controller_protocol(mismatched, protocol)
        config["phase"] = "evaluation"
        config["protocol_sha256"] = "a" * 64
        config["objective_origins"] = ["2022-12-01T00:00:00+00:00"]
        validate_study(config)


if __name__ == "__main__":
    unittest.main()
