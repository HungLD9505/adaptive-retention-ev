"""Independent chronological fixtures; tiny updates are not research training."""

import copy
import json
import random
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import torch

from ev_control.confidence import ControllerConfig, decide
from ev_models.model import ForecastGRU, ModelConfig
from ev_models.training import TrainingConfig, frozen_reference, seed_everything
from ev_runner.engine import DAY, Runner
from ev_runner.replay import Labels
from ev_runner.state import Branch, rng_state, state_digest
from ev_runner.store import Store


class FixtureReplay:
    def __init__(self):
        self.start = datetime(2022, 12, 1, tzinfo=timezone(timedelta(hours=8)))
        self.stop = self.start + 5 * DAY
        self.scale_id, self.scale = "fixture-scale", 10.0
        self.missing_history = set()
        self.missing_labels = set()
        self.delay = {}
        self.accesses = []
        self.on_access = None

    def forecast(self, origin):
        if origin in self.missing_history:
            return None
        return {
            "origin": origin.isoformat(),
            "x_hist": [[0.1, 0, 1, 0, 1, 0, 1] for _ in range(24)],
            "c_future": [[0, 1, 0, 1, 0] for _ in range(24)],
        }

    def labels(self, origin, as_of):
        if self.on_access:
            self.on_access(origin, as_of)
        self.accesses.append((origin, as_of))
        if origin + DAY > as_of:
            raise AssertionError("Future read")
        if as_of < origin + self.delay.get(origin, 1) * DAY:
            return Labels("pending", None, origin + 2 * DAY)
        if origin in self.missing_labels:
            return Labels("incomplete", None, as_of)
        return Labels("complete", (3.0,) * 24, as_of)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        seed_everything(42)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.replay = FixtureReplay()
        self.controller = ControllerConfig(0.01, 0.1, 0.01, 2, 2, 100, 0.05, 1, 20, 42)
        self.training = TrainingConfig(42, 1, 64, 0.001, 0.001, 4)
        model = ForecastGRU(ModelConfig(4))
        self.reference = frozen_reference(model)
        self.initial = Branch(model, torch.optim.Adam(model.parameters(), lr=0.001), rng_state())
        self.binding = {"config": "fixture", "source": state_digest(model.state_dict())}

    def tearDown(self):
        self.tmp.cleanup()

    def runner(self, name="run", resume=None):
        store = Store(self.root / name, self.binding, resume_from=resume)
        return Runner(
            self.replay,
            self.initial,
            self.reference,
            torch.ones(64),
            self.controller,
            self.training,
            store,
            device="cpu",
            stream_id="fixture",
        )

    def events(self, name="run"):
        return [
            json.loads(line)
            for f in sorted((self.root / name).glob("tick-*/events.jsonl"))
            for line in f.read_text().splitlines()
        ]

    def test_same_candidate_states_and_no_mutable_alias(self):
        r = self.runner()
        self.assertEqual(len({state_digest(x.snapshot()) for x in r.branches.values()}), 1)
        with torch.no_grad():
            next(r.branches[0].model.parameters()).add_(1)
        self.assertNotEqual(
            state_digest(r.branches[0].snapshot()), state_digest(r.branches[0.01].snapshot())
        )
        self.assertEqual(state_digest(self.reference.state_dict()), self.binding["source"])

    def test_forecast_is_durable_before_own_label_access(self):
        r = self.runner()

        def check(origin, as_of):
            index = (origin - self.replay.start).days
            saved = self.root / f"run/tick-{index:04d}/forecasts.json"
            self.assertTrue(saved.is_file())
            self.assertEqual(json.loads(saved.read_text())["origin"], origin.isoformat())

        self.replay.on_access = check
        r.run_until(self.replay.start + 2 * DAY)
        self.assertEqual(len(self.replay.accesses), 2)
        events = self.events()
        forecast_index = next(i for i, e in enumerate(events) if e["event"] == "forecast_saved")
        score_index = next(i for i, e in enumerate(events) if e["event"] == "score")
        self.assertLess(forecast_index, score_index)

    def test_keep_carries_trained_optimizer_and_rng_before_next_forecast(self):
        r = self.runner()
        initial_sha = state_digest(self.initial.snapshot())
        r.run_until(self.replay.start + 2 * DAY)
        self.assertEqual(r.active, 0.01)
        self.assertNotEqual(state_digest(r.branches[0.01].snapshot()), initial_sha)
        self.assertTrue(all(b.steps == 2 for b in r.branches.values()))
        events = self.events()
        at_boundary = [
            e["event"]
            for e in events
            if e.get("as_of", e.get("origin")) == (self.replay.start + 2 * DAY).isoformat()
        ]
        self.assertLess(at_boundary.index("update"), at_boundary.index("decision"))
        self.assertLess(at_boundary.index("decision"), at_boundary.index("forecast_saved"))
        self.assertTrue(r.branches[0.01].optimizer.state)
        self.assertEqual(state_digest(r.branches[0].rng), state_digest(r.branches[0.1].rng))

    def test_missing_history_and_labels_preserve_schedule_and_bmin(self):
        self.replay.missing_history.add(self.replay.start)
        self.replay.missing_labels.add(self.replay.start + DAY)
        r = self.runner()
        r.run_until(self.replay.start + 2 * DAY)
        self.assertEqual(r.steps, 0)
        self.assertEqual(r.decisions[0]["valid_days"], 0)
        self.assertEqual(r.decisions[0]["incomplete_days"], 1)
        events = [e["event"] for e in self.events()]
        self.assertIn("skip_all_missing_history", events)
        self.assertIn("skip_incomplete_labels", events)
        self.assertEqual(events.count("forecast_saved"), 2)

    def test_delayed_labels_cannot_affect_earlier_decision(self):
        self.replay.delay[self.replay.start] = 3
        r = self.runner()
        r.run_until(self.replay.start + 2 * DAY)
        self.assertEqual(r.decisions[0]["valid_days"], 1)
        self.assertEqual(r.decisions[0]["pending_days"], 1)
        r.tick()
        self.assertEqual(r.steps, 9)  # Three complete days x three branches by day 3.
        self.assertEqual(r.decisions[0]["valid_days"], 1)

    def test_exact_daily_resume_preserves_forecasts_models_optimizer_rng(self):
        whole = self.runner("whole")
        whole.run_until(self.replay.start + 5 * DAY)
        partial = self.runner("partial")
        partial.run_until(self.replay.start + 2 * DAY)
        old_hashes = {
            p.relative_to(partial.store.root): p.read_bytes()
            for p in partial.store.root.glob("tick-*/forecasts.json")
        }
        random.random()
        torch.rand(20)
        resumed = self.runner("resumed", partial.store.root)
        resumed.run_until(self.replay.start + 5 * DAY)
        for level in self.controller.levels:
            self.assertEqual(
                state_digest(whole.branches[level].snapshot()),
                state_digest(resumed.branches[level].snapshot()),
            )
        self.assertEqual(whole.decisions, resumed.decisions)
        for file in whole.store.root.glob("tick-*/forecasts.json"):
            self.assertEqual(
                file.read_bytes(),
                (resumed.store.root / file.relative_to(whole.store.root)).read_bytes(),
            )
        for p, data in old_hashes.items():
            self.assertEqual((partial.store.root / p).read_bytes(), data)
            self.assertEqual((resumed.store.root / p).read_bytes(), data)

    def forced_switch(self, *args, **kwargs):
        d = decide(*args, **kwargs)
        return replace(d, selected_lambda=0.1, reason="fixture_forced_switch")

    def test_audit_runs_next_block_and_is_not_controller_input(self):
        r = self.runner()
        with patch("ev_runner.engine.decide", side_effect=self.forced_switch):
            r.run_until(self.replay.start + 2 * DAY)
        self.assertIsNotNone(r.audit)
        self.assertEqual(r.audit_origin["lambda"], 0.01)
        with patch("ev_runner.engine.decide", wraps=decide) as call:
            r.run_until(self.replay.start + 4 * DAY)
        self.assertEqual(len(call.call_args.args[0]), 2)
        self.assertTrue(all(len(row.mae) == 3 for row in call.call_args.args[0]))
        self.assertEqual(r.audit_steps, 2)
        summaries = [e for e in self.events() if e["event"] == "audit_summary"]
        self.assertEqual(summaries[0]["paired_days"], 2)
        self.assertIsNotNone(summaries[0]["mean_new_minus_old"])

    def test_audit_poisoning_cannot_change_candidate_predictions_or_decisions(self):
        one, two = self.runner("one"), self.runner("two")
        with patch("ev_runner.engine.decide", side_effect=self.forced_switch):
            one.run_until(self.replay.start + 2 * DAY)
            two.run_until(self.replay.start + 2 * DAY)
        with torch.no_grad():
            next(two.audit.model.parameters()).add_(0.1)
        one.run_until(self.replay.start + 4 * DAY)
        two.run_until(self.replay.start + 4 * DAY)
        self.assertEqual(one.decisions, two.decisions)
        for level in self.controller.levels:
            self.assertEqual(
                state_digest(one.branches[level].snapshot()),
                state_digest(two.branches[level].snapshot()),
            )

    def test_resume_rejects_tampered_prediction_and_config(self):
        r = self.runner()
        r.tick()
        self.binding["config"] = "different"
        with self.assertRaisesRegex(ValueError, "binding differs"):
            self.runner("bad-config", r.store.root)
        self.binding["config"] = "fixture"
        (r.store.root / "tick-0000/forecasts.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "Changed committed"):
            self.runner("bad-file", r.store.root)

    def test_resume_rejects_uncommitted_tick_without_rewriting(self):
        r = self.runner()
        r.tick()
        path = r.store.begin()
        r.store.save_forecasts(path, {"issued": True})
        before = (path / "forecasts.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "Uncommitted issued"):
            self.runner("bad-pending", r.store.root)
        self.assertEqual((path / "forecasts.json").read_bytes(), before)

    def test_invalid_complete_values_fail_without_committed_updates(self):
        r = self.runner()
        r.tick()
        self.replay.labels = lambda *args: Labels("complete", (float("nan"),) * 24, args[1])
        with self.assertRaisesRegex(ValueError, "invalid"):
            r.tick()
        self.assertEqual(r.store.count, 1)

    def test_source_frozen_through_retention_updates(self):
        r = self.runner()
        before = copy.deepcopy(self.reference.state_dict())
        r.run_until(self.replay.start + 3 * DAY)
        for name, value in before.items():
            self.assertTrue(torch.equal(value, self.reference.state_dict()[name]))
        self.assertTrue(all(p.grad is None for p in self.reference.parameters()))
        self.assertEqual(r.steps, 9)


if __name__ == "__main__":
    unittest.main()
