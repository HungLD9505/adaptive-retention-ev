"""Checkpoint/resume must preserve issued forecasts and optimizer progress."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import torch

from experiments.hung_sprint2.checkpoint import load_runner, save_runner
from experiments.hung_sprint2.controller import Decision
from experiments.hung_sprint2.runner import LabelArrival, PrequentialRunner
from tests.test_hung_runner import binding, complete, origin, runner


def assert_same_replay(case: unittest.TestCase, left, right) -> None:
    case.assertEqual(left.events, right.events)
    case.assertEqual(left.update_steps, right.update_steps)
    case.assertEqual(left.audit_steps, right.audit_steps)
    case.assertEqual(left.current_level, right.current_level)
    case.assertEqual(left.next_index, right.next_index)
    case.assertEqual(
        [record["inference_calls"] for record in left.runtime_costs["candidate"]],
        [record["inference_calls"] for record in right.runtime_costs["candidate"]],
    )
    case.assertEqual(
        [record["update_steps"] for record in left.runtime_costs["candidate"]],
        [record["update_steps"] for record in right.runtime_costs["candidate"]],
    )
    case.assertEqual(
        left.runtime_costs["audit"]["inference_calls"],
        right.runtime_costs["audit"]["inference_calls"],
    )
    case.assertEqual(
        left.runtime_costs["audit"]["update_steps"],
        right.runtime_costs["audit"]["update_steps"],
    )
    case.assertEqual(len(left.issued), len(right.issued))
    for a, b in zip(left.issued, right.issued, strict=True):
        case.assertEqual(a["day_id"], b["day_id"])
        case.assertEqual(a["normalized_mae"], b["normalized_mae"])
        if a["y_scaled"] is None:
            case.assertIsNone(b["y_scaled"])
        else:
            case.assertTrue(torch.equal(a["y_scaled"], b["y_scaled"]))
        for forecast_a, forecast_b in zip(a["forecasts"], b["forecasts"], strict=True):
            case.assertTrue(torch.equal(forecast_a, forecast_b))
    for (model_a, opt_a), (model_b, opt_b) in zip(left.candidates, right.candidates, strict=True):
        for name, value in model_a.state_dict().items():
            case.assertTrue(torch.equal(value, model_b.state_dict()[name]))
        case.assertEqual(len(opt_a.state), len(opt_b.state))
        for state_a, state_b in zip(opt_a.state.values(), opt_b.state.values(), strict=True):
            for key in state_a:
                case.assertTrue(torch.equal(state_a[key], state_b[key]))


class ResumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def test_resume_after_forecast_and_after_update(self) -> None:
        replay = runner()
        replay.forecast(origin(0))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pending.pt"
            save_runner(path, replay)
            restored = load_runner(path, expected_binding=binding())
            self.assertEqual(restored.runtime_costs, replay.runtime_costs)
            with self.assertRaises(FileExistsError):
                save_runner(path, replay)
            wrong = binding()
            wrong["entity_id"] = "other"
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                load_runner(path, expected_binding=wrong)
            replay.arrive(complete(0))
            restored.arrive(complete(0))
            assert_same_replay(self, replay, restored)

            path2 = Path(directory) / "updated.pt"
            save_runner(path2, replay)
            resumed = load_runner(path2, expected_binding=binding())
            self.assertEqual(resumed.runtime_costs, replay.runtime_costs)
            for day in range(1, 14):
                for candidate in (replay, resumed):
                    candidate.forecast(origin(day, skipped=True))
                    candidate.arrive(LabelArrival(f"day-{day}", False))
            replay.finish_block()
            resumed.finish_block()
            replay.forecast(origin(14))
            resumed.forecast(origin(14))
            assert_same_replay(self, replay, resumed)

    def test_resume_with_old_policy_audit_after_switch(self) -> None:
        replay = runner()
        replay.forecast(origin(0))
        replay.arrive(complete(0))
        for day in range(1, 14):
            replay.forecast(origin(day, skipped=True))
            replay.arrive(LabelArrival(f"day-{day}", False))
        forced = Decision(0.1, 0.3, 1, 13, (None, None, 1.0), 0.025, "switch")
        with mock.patch("experiments.hung_sprint2.runner.decide_block", return_value=forced):
            replay.finish_block()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.pt"
            save_runner(path, replay)
            resumed = load_runner(path, expected_binding=binding())
            replay.forecast(origin(14))
            resumed.forecast(origin(14))
            replay.arrive(complete(14))
            resumed.arrive(complete(14))
            assert_same_replay(self, replay, resumed)
            self.assertEqual((replay.audit_steps, resumed.audit_steps), (1, 1))
            self.assertEqual(
                replay.issued[-1]["audit_normalized_mae"],
                resumed.issued[-1]["audit_normalized_mae"],
            )

    def test_legacy_checkpoint_marks_unmeasured_cost_as_incomplete(self) -> None:
        replay = runner()
        replay.forecast(origin(0))
        replay.arrive(complete(0))
        state = replay.state_dict()
        del state["runtime_costs"]
        restored = PrequentialRunner.from_state_dict(state, expected_binding=binding())
        self.assertFalse(restored.runtime_costs["complete"])
        self.assertEqual(restored.runtime_costs["candidate"][0]["update_steps"], 0)
        self.assertEqual(restored.update_steps, [1, 1, 1])

    def test_checkpoint_rejects_inconsistent_cost_counters(self) -> None:
        state = runner().state_dict()
        state["runtime_costs"]["candidate"][0]["update_steps"] = 1
        with self.assertRaisesRegex(ValueError, "counters disagree"):
            PrequentialRunner.from_state_dict(state, expected_binding=binding())


if __name__ == "__main__":
    unittest.main()
