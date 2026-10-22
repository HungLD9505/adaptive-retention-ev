"""Expected event-order and trained-state checks for the fixture runner."""

from __future__ import annotations

import unittest
from itertools import count
from unittest import mock

import torch

from experiments.hung_sprint2.controller import ControllerConfig, Decision
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.retention import frozen_source_reference
from experiments.hung_sprint2.runner import LabelArrival, Origin, PrequentialRunner
from experiments.hung_sprint2.training import target_step


def binding() -> dict:
    return {
        "schema": "ev-checkpoint-input-binding-v1",
        "feature_schema": "ev-input-v1",
        "input_manifest_sha256": "a" * 64,
        "input_run_id": "fixture-target",
        "dataset_id": "urbanev",
        "city_id": "SZH",
        "stage": "target",
        "entity_id": "station-1",
        "history_days": 7,
        "scale_id": "fixture-scale",
        "source_checkpoint_sha256": "b" * 64,
    }


def runner() -> PrequentialRunner:
    torch.manual_seed(81)
    model = ForecastGRU(ModelConfig(calendar_hidden=8))
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    reference = frozen_source_reference(model)
    controller = ControllerConfig(
        levels=(0.0, 0.1, 0.3),
        initial_level=0.1,
        block_days=14,
        min_complete_days=1,
        delta=100.0,
        alpha=0.05,
        bootstrap_segment_days=1,
        bootstrap_resamples=11,
        seed=9,
        challenger_rule="bonferroni_two",
    )
    return PrequentialRunner(
        model,
        optimizer,
        reference,
        torch.ones(64),
        binding=binding(),
        controller=controller,
        epsilon=1e-6,
        energy_scale=5.0,
    )


def origin(index: int, *, skipped: bool = False) -> Origin:
    if skipped:
        return Origin(f"day-{index}", index, None, None, "skipped_all_missing_history")
    return Origin(
        f"day-{index}",
        index,
        torch.full((1, 24, 7), 0.2),
        torch.full((1, 24, 5), 0.1),
    )


def complete(index: int) -> LabelArrival:
    return LabelArrival(
        f"day-{index}", True, torch.full((24,), 0.4), torch.ones(24, dtype=torch.bool)
    )


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def test_forecast_before_label_missing_day_and_boundary(self) -> None:
        replay = runner()
        before = replay.candidates[1][0].encoder.weight_ih_l0.detach().clone()
        replay.forecast(origin(0))
        self.assertEqual(replay.events[-1], "forecast:day-0")
        self.assertEqual(len(replay.issued), 1)
        self.assertIsNone(replay.issued[0]["normalized_mae"])
        self.assertIsNone(replay.issued[0]["y_scaled"])
        self.assertTrue(torch.equal(before, replay.candidates[1][0].encoder.weight_ih_l0))
        with self.assertRaisesRegex(ValueError, "Previous day"):
            replay.forecast(origin(1))
        replay.arrive(complete(0))
        self.assertEqual(replay.events[-2:], ["score:day-0", "update:day-0"])
        self.assertEqual(replay.update_steps, [1, 1, 1])
        self.assertTrue(torch.equal(replay.issued[0]["y_scaled"], torch.full((24,), 0.4)))
        self.assertAlmostEqual(
            replay.issued[0]["mae_kwh"][0], 5 * replay.issued[0]["normalized_mae"][0]
        )
        for day in range(1, 14):
            replay.forecast(origin(day, skipped=True))
            replay.arrive(LabelArrival(f"day-{day}", False))
        with self.assertRaisesRegex(ValueError, "Finish block"):
            replay.forecast(origin(14))
        trained_active = replay.candidates[1][0].encoder.weight_ih_l0.detach().clone()
        decision = replay.finish_block()
        self.assertFalse(decision.switched)
        self.assertEqual(replay.current_level, 0.1)
        self.assertTrue(torch.equal(trained_active, replay.active_model.encoder.weight_ih_l0))
        self.assertFalse(torch.equal(before, replay.active_model.encoder.weight_ih_l0))
        replay.forecast(origin(14))
        self.assertLess(
            replay.events.index("decision:0:0.1"), replay.events.index("forecast:day-14")
        )

    def test_forced_switch_carries_trained_candidate_and_isolated_audit(self) -> None:
        replay = runner()
        replay.forecast(origin(0))
        replay.arrive(complete(0))
        for day in range(1, 14):
            replay.forecast(origin(day, skipped=True))
            replay.arrive(LabelArrival(f"day-{day}", False))
        old_active = replay.candidates[1][0].encoder.weight_ih_l0.detach().clone()
        winner = replay.candidates[2][0].encoder.weight_ih_l0.detach().clone()
        forced = Decision(0.1, 0.3, 1, 13, (None, None, 1.0), 0.025, "switch")
        with mock.patch("experiments.hung_sprint2.runner.decide_block", return_value=forced):
            replay.finish_block()
        self.assertTrue(torch.equal(winner, replay.active_model.encoder.weight_ih_l0))
        self.assertTrue(torch.equal(old_active, replay.audit[1].encoder.weight_ih_l0))
        self.assertTrue(torch.equal(winner, replay.candidates[0][0].encoder.weight_ih_l0))
        replay.forecast(origin(14))
        self.assertIsNotNone(replay.issued[-1]["audit_forecast"])
        rng_before = torch.get_rng_state().clone()

        def consume_audit_rng(model, *args, **kwargs):
            result = target_step(model, *args, **kwargs)
            if model is replay.audit[1]:
                torch.rand(1)
            return result

        with mock.patch(
            "experiments.hung_sprint2.runner.target_step", side_effect=consume_audit_rng
        ):
            replay.arrive(complete(14))
        self.assertTrue(torch.equal(rng_before, torch.get_rng_state()))
        self.assertEqual(replay.audit_steps, 1)
        self.assertEqual(replay.runtime_costs["audit"]["inference_calls"], 1)
        self.assertEqual(replay.runtime_costs["audit"]["update_steps"], 1)
        self.assertGreater(replay.state_tensor_memory()["audit"], 0)
        self.assertIsNotNone(replay.issued[-1]["audit_mae_kwh"])
        self.assertEqual(len(replay.days), 1)
        self.assertEqual(replay.update_steps, [2, 2, 2])

    def test_incomplete_labels_never_score_or_update(self) -> None:
        replay = runner()
        replay.forecast(origin(0))
        with self.assertRaisesRegex(ValueError, "Unavailable labels"):
            replay.arrive(LabelArrival("day-0", False, torch.ones(24)))
        with self.assertRaisesRegex(ValueError, "24 values"):
            replay.arrive(
                LabelArrival("day-0", True, torch.ones(23), torch.ones(23, dtype=torch.bool))
            )
        incomplete = torch.ones(24, dtype=torch.bool)
        incomplete[2] = False
        replay.arrive(LabelArrival("day-0", True, torch.ones(24), incomplete))
        self.assertEqual(replay.update_steps, [0, 0, 0])
        self.assertIsNone(replay.issued[0]["normalized_mae"])
        self.assertEqual(replay.days[0].labels_complete, False)
        self.assertEqual(replay.events[-1], "unscored:day-0")

    def test_repeated_day_identity_is_rejected(self) -> None:
        replay = runner()
        replay.forecast(origin(0))
        replay.arrive(complete(0))
        with self.assertRaisesRegex(ValueError, "Duplicate forecast day"):
            replay.forecast(Origin("day-0", 1, torch.ones(1, 24, 7), torch.ones(1, 24, 5)))

    def test_deferred_label_updates_current_block_only_once(self) -> None:
        replay = runner()
        replay.forecast(origin(0))
        replay.arrive(LabelArrival("day-0", False, deferred=True))
        self.assertIn("day-0", replay.late_pending)
        replay.forecast(origin(1))
        replay.arrive(complete(1))
        replay.arrive(complete(0))
        self.assertEqual(replay.update_steps, [2, 2, 2])
        self.assertEqual(replay.days[0].normalized_mae, replay.issued[0]["normalized_mae"])
        self.assertEqual(replay.next_index, 2)
        self.assertNotIn("day-0", replay.late_pending)
        with self.assertRaisesRegex(ValueError, "no matching"):
            replay.arrive(complete(0))

    def test_runtime_costs_measure_successful_calls_separately(self) -> None:
        replay = runner()
        initial_memory = replay.state_tensor_memory()
        self.assertIsNone(initial_memory["audit"])
        self.assertEqual(len(initial_memory["candidate"]), 3)
        label = complete(0)
        with mock.patch("experiments.hung_sprint2.runner.perf_counter_ns", side_effect=count(0, 7)):
            replay.forecast(origin(0))
            replay.arrive(label)
        updated_memory = replay.state_tensor_memory()
        for before, after in zip(initial_memory["candidate"], updated_memory["candidate"]):
            self.assertGreater(after, before)
        for cost in replay.runtime_costs["candidate"]:
            self.assertEqual(
                cost,
                {
                    "inference_calls": 1,
                    "inference_ns": 7,
                    "update_steps": 1,
                    "update_ns": 7,
                },
            )
        self.assertEqual(replay.runtime_costs["audit"]["inference_calls"], 0)
        self.assertEqual(replay.runtime_costs["audit"]["update_steps"], 0)
        label.y_scaled.fill_(2.0)
        self.assertTrue(torch.equal(replay.issued[0]["y_scaled"], torch.full((24,), 0.4)))


if __name__ == "__main__":
    unittest.main()
