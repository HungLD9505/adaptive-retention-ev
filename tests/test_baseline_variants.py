"""Independent baseline formula, chronology, cost and restart checks."""

import copy
import unittest
from dataclasses import replace
from datetime import timedelta

import test_prequential_runner as fixtures
import torch

from ev_baselines.naive import SeasonalNaive
from ev_baselines.policies import METHODS, Method, Policy, ablation_aliases
from ev_baselines.retention import ParameterBranch, parameter_retention
from ev_control.confidence import DailyScore
from ev_models.training import frozen_reference
from ev_runner.engine import DAY, Runner
from ev_runner.state import Branch, state_digest
from ev_runner.store import Store


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RunnerTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.controller = replace(self.fixture.controller, delta=0)
        self.start = self.fixture.replay.start

    def record(self, at=None, value=0.1):
        at = at or self.start
        return {
            "origin": at.isoformat(),
            "history_labels": [(at - timedelta(hours=24 - i)).isoformat() for i in range(24)],
            "future_labels": [(at + timedelta(hours=i)).isoformat() for i in range(24)],
            "x_hist": [[value, 0, 1, 0, 1, 0, 1] for _ in range(24)],
            "c_future": [[0, 1, 0, 1, 0] for _ in range(24)],
            "y_scaled": [value] * 24,
        }

    def test_weekly_then_daily_then_mean_fallback_and_zero_are_predictions(self):
        weekly = self.record(self.start - 6 * DAY, 0.7)
        model = SeasonalNaive([weekly])
        prediction = model.predict(self.record())
        self.assertEqual(prediction, [0.7] * 24)
        self.assertEqual(model.fallbacks["weekly"], 24)
        daily = SeasonalNaive([])
        self.assertEqual(daily.predict(self.record(value=0)), [0] * 24)
        missing = self.record()
        for row in missing["x_hist"]:
            row[-1] = 0
        self.assertEqual(daily.predict(missing), [0] * 24)
        self.assertEqual(SeasonalNaive([]).predict(missing), [0] * 24)

    def test_naive_never_uses_future_and_retains_state_without_sgd(self):
        model = SeasonalNaive([])
        record = self.record()
        model.history[(self.start + DAY).isoformat()] = 100000
        self.assertEqual(model.predict(record), [0.1] * 24)
        model.update(record)
        self.assertEqual(model.steps, 0)
        clone = model.clone()
        self.assertEqual(clone.snapshot(), model.snapshot())
        clone.history.clear()
        self.assertTrue(model.history)

    def test_parameter_mse_is_elementwise_encoder_only_and_reference_frozen(self):
        target = copy.deepcopy(self.fixture.initial.model)
        reference = self.fixture.reference
        with torch.no_grad():
            for p in target.encoder.parameters():
                p.add_(2)
            for p in target.head.parameters():
                p.add_(100)
        loss = parameter_retention(target, reference)
        self.assertAlmostEqual(loss.item(), 4, places=5)
        loss.backward()
        self.assertTrue(any(p.grad is not None for p in target.encoder.parameters()))
        self.assertTrue(all(p.grad is None for p in target.head.parameters()))
        self.assertTrue(all(p.grad is None for p in reference.parameters()))

    def test_zero_parameter_weight_matches_latent_zero_update(self):
        kwargs = dict(device="cpu", learning_rate=0.001)
        latent = Branch.from_snapshot(self.fixture.initial.snapshot(), **kwargs)
        parameter = ParameterBranch.from_snapshot(self.fixture.initial.snapshot(), **kwargs)
        update = dict(
            weight=0,
            config=self.fixture.training,
            device="cpu",
            reference=self.fixture.reference,
            latent_scale=torch.ones(64),
            event_index=0,
        )
        latent.update(self.record(), **update)
        parameter.update(self.record(), **update)
        self.assertEqual(
            state_digest(latent.model.state_dict()), state_digest(parameter.model.state_dict())
        )
        self.assertEqual(
            state_digest(latent.optimizer.state_dict()),
            state_digest(parameter.optimizer.state_dict()),
        )

    def policy(self, name, **kwargs):
        return Policy(
            Method(name, **kwargs), self.fixture.reference, initial_records=[], device="cpu"
        )

    def rows(self, values=(1, 2, 3)):
        return [
            DailyScore(
                self.start + i * DAY,
                self.start + i * DAY,
                self.start + (i + 1) * DAY,
                24,
                values,
                "s",
                ("a", "b", "c"),
            )
            for i in range(2)
        ]

    def choose(self, policy, rows=None, config=None):
        return policy.choose(
            rows or self.rows(),
            config=config or self.controller,
            active_lambda=0.01,
            block_start=self.start,
            as_of=self.start + 2 * DAY,
            stream_id="x",
            scale_id="s",
        )

    def test_online_best_uses_mean_not_bootstrap_and_preserves_bmin(self):
        p = self.policy("online_best")
        d = self.choose(p)
        self.assertEqual(d.selected_lambda, 0)
        self.assertEqual(d.comparisons, ())  # Never label mean improvement as an LCB.
        self.assertEqual(self.choose(p, self.rows()[:1]).selected_lambda, 0.01)
        self.assertEqual(self.choose(p, self.rows((2, 2, 2))).selected_lambda, 0.01)

    def test_without_confidence_alias_is_conditional_on_zero_delta(self):
        self.assertEqual(
            ablation_aliases(self.controller, 0.01)["without_confidence"], "online_best"
        )
        positive = replace(self.controller, delta=2)
        self.assertEqual(
            ablation_aliases(positive, 0.01)["without_confidence"], "without_confidence"
        )
        self.assertEqual(
            self.choose(self.policy("without_confidence"), config=positive).selected_lambda, 0.01
        )
        self.assertEqual(
            self.choose(self.policy("online_best"), config=positive).selected_lambda, 0
        )

    def test_proxy_mapping_direction_explicit_and_future_signals_ignored(self):
        p = self.policy("drift", proxy_thresholds=(0.1, 0.5), proxy_order=(2, 1, 0))
        p.signals = [
            {
                "origin": (self.start + i * DAY).isoformat(),
                "available_at": (self.start + i * DAY).isoformat(),
                "value": 10,
            }
            for i in range(2)
        ]
        self.assertEqual(self.choose(p).selected_lambda, 0)
        p.signals.append(
            {
                "origin": (self.start + 2 * DAY).isoformat(),
                "available_at": (self.start + 2 * DAY).isoformat(),
                "value": 0,
            }
        )
        self.assertEqual(self.choose(p).selected_lambda, 0)
        pending = [replace(r, available_at=self.start + 3 * DAY) for r in self.rows()]
        self.assertEqual(self.choose(p, pending).selected_lambda, 0.01)

    def test_source_error_not_recorded_until_complete_label_arrival(self):
        p = self.policy("source_error")
        proxy = p.predict(self.record())
        self.assertEqual(p.signals, [])
        p.observe({"origin": self.start.isoformat(), "proxy": proxy}, [0] * 24, self.start + DAY)
        self.assertEqual(len(p.signals), 1)
        self.assertGreaterEqual(p.signals[0]["value"], 0)

    def test_uncertainty_needs_identified_ensemble_and_same_input(self):
        with self.assertRaises(ValueError):
            self.policy("uncertainty")
        models = [frozen_reference(self.fixture.initial.model) for _ in range(3)]
        p = Policy(
            Method("uncertainty"),
            models[0],
            initial_records=[],
            device="cpu",
            ensemble=tuple(models),
        )
        self.assertEqual(p.predict(self.record())["signal"], 0)
        before = state_digest(models[0].state_dict())
        p.predict(self.record())
        self.assertEqual(state_digest(models[0].state_dict()), before)

    def test_single_candidate_fixed_frozen_naive_and_restore(self):
        for name in (
            "full_finetuning",
            "fixed_retention",
            "target_only",
            "frozen_source",
            "seasonal_naive",
        ):
            with self.subTest(method=name):
                replay = fixtures.FixtureReplay()
                replay.forecast = lambda at: self.record(at)
                initial = SeasonalNaive([]) if name == "seasonal_naive" else self.fixture.initial
                p = self.policy(name)
                root = self.fixture.root / name
                runner = Runner(
                    replay,
                    initial,
                    self.fixture.reference,
                    torch.ones(64),
                    self.controller,
                    self.fixture.training,
                    Store(root, {"method": name}),
                    device="cpu",
                    stream_id=name,
                    policy=p,
                )
                runner.run_until(self.start + 2 * DAY)
                self.assertEqual(len(runner.branches), 1)
                self.assertEqual(
                    runner.steps, 0 if name in {"frozen_source", "seasonal_naive"} else 2
                )
                restored = Runner(
                    replay,
                    initial,
                    self.fixture.reference,
                    torch.ones(64),
                    self.controller,
                    self.fixture.training,
                    Store(
                        self.fixture.root / (name + "-resume"), {"method": name}, resume_from=root
                    ),
                    device="cpu",
                    stream_id=name,
                    policy=self.policy(name),
                )
                self.assertEqual(state_digest(runner.snapshot()), state_digest(restored.snapshot()))

    def test_required_methods_are_named_and_invalid_mapping_rejected(self):
        self.assertTrue(
            set(
                (
                    "seasonal_naive",
                    "target_only",
                    "frozen_source",
                    "full_finetuning",
                    "fixed_retention",
                    "online_best",
                    "source_error",
                    "uncertainty",
                    "drift",
                )
            ).issubset(METHODS)
        )
        with self.assertRaises(ValueError):
            Method("drift", proxy_order=(0, 0, 1))


if __name__ == "__main__":
    unittest.main()
