"""Independent mean-selector expectations and common-runner budget checks."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import torch

from experiments.hung_sprint2.baseline_selection import decide_fixed_block, decide_mean_block
from experiments.hung_sprint2.checkpoint import load_runner, save_runner
from experiments.hung_sprint2.controller import ControllerConfig, DailyScore
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.retention import frozen_source_reference
from experiments.hung_sprint2.runner import LabelArrival, Origin, PrequentialRunner


def config(*, delta: float = 0.0, minimum: int = 2, initial: float = 0.1) -> ControllerConfig:
    return ControllerConfig(
        (0.0, 0.1, 0.2),
        initial,
        3,
        minimum,
        delta,
        0.05,
        1,
        10,
        7,
        "bonferroni_two",
    )


def score(day: str, errors: tuple[float, float, float] | None) -> DailyScore:
    return DailyScore(day, errors is not None, errors is not None, errors)


def runner(rule: str, *, initial: float = 0.1) -> PrequentialRunner:
    torch.manual_seed(7)
    model = ForecastGRU(ModelConfig(calendar_hidden=8))
    return PrequentialRunner(
        model,
        torch.optim.Adam(model.parameters(), lr=0.01),
        frozen_source_reference(model),
        torch.ones(64),
        binding={
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
        },
        controller=config(minimum=1, initial=initial),
        epsilon=1e-6,
        energy_scale=5.0,
        selection_rule=rule,
    )


class BaselineSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def test_online_best_uses_paired_means_and_tie_prefers_active(self) -> None:
        rows = [score("a", (0.2, 0.3, 0.1)), score("b", (0.4, 0.3, 0.1)), score("c", None)]
        decision = decide_mean_block(
            config(), current_level=0.1, days=rows, rule="online_best_lambda"
        )
        self.assertEqual(decision.selected_level, 0.2)
        self.assertEqual(decision.valid_days, 2)
        self.assertEqual(decision.skipped_days, 1)
        self.assertEqual(decision.lower_bounds, (None, None, None))
        self.assertEqual(decision.selection_statistic, "observed_mean_improvement")
        tied = [score("a", (0.1, 0.1, 0.1)), score("b", (0.2, 0.2, 0.2))]
        keep = decide_mean_block(config(), current_level=0.1, days=tied, rule="online_best_lambda")
        self.assertEqual(keep.selected_level, 0.1)

    def test_without_confidence_keeps_strict_delta_and_insufficient_null(self) -> None:
        rows = [score("a", (0.2, 0.3, 0.1)), score("b", (0.2, 0.3, 0.1))]
        keep = decide_mean_block(
            config(delta=0.2), current_level=0.1, days=rows, rule="without_confidence"
        )
        self.assertEqual(keep.selected_level, 0.1)
        missing = decide_mean_block(
            config(minimum=2),
            current_level=0.1,
            days=[rows[0], score("b", None)],
            rule="online_best_lambda",
        )
        self.assertEqual(missing.reason, "insufficient_days")
        self.assertEqual(missing.observed_mean_improvement, (None, None, None))
        self.assertTrue(all(value is None for value in missing.lower_bounds))

    def test_common_runner_equal_candidate_steps_and_resume_policy(self) -> None:
        adaptive = runner("confidence")
        best = runner("online_best_lambda")
        x = torch.full((1, 24, 7), 0.2)
        calendar = torch.full((1, 24, 5), 0.1)
        for instance in (adaptive, best):
            instance.forecast(Origin("day-0", 0, x, calendar))
            instance.arrive(
                LabelArrival(
                    "day-0", True, torch.full((24,), 0.4), torch.ones(24, dtype=torch.bool)
                )
            )
            for day in (1, 2):
                instance.forecast(
                    Origin(f"day-{day}", day, None, None, "skipped_all_missing_history")
                )
                instance.arrive(LabelArrival(f"day-{day}", False))
            self.assertEqual(instance.update_steps, [1, 1, 1])
            self.assertEqual(
                [item["inference_calls"] for item in instance.runtime_costs["candidate"]],
                [1, 1, 1],
            )
        decision = best.finish_block()
        self.assertEqual(decision.selection_statistic, "observed_mean_improvement")
        restored = PrequentialRunner.from_state_dict(
            best.state_dict(), expected_binding=best.binding, device="cpu"
        )
        self.assertEqual(restored.selection_rule, "online_best_lambda")
        self.assertEqual(restored.update_steps, [1, 1, 1])

    def test_switch_next_block_audit_and_split_resume_for_each_policy(self) -> None:
        x = torch.full((1, 24, 7), 0.2)
        calendar = torch.full((1, 24, 5), 0.1)
        label = LabelArrival(
            "day-0", True, torch.full((24,), 0.7), torch.ones(24, dtype=torch.bool)
        )

        def prepared(rule: str) -> PrequentialRunner:
            instance = runner(rule)
            # Identified synthetic branch separation makes the challenger win by
            # a wide margin; the test exercises runner state flow, not training efficacy.
            with torch.no_grad():
                for index, bias in enumerate((-3.0, 3.0, 0.0)):
                    head = instance.candidates[index][0].forecast_head[0]
                    head.weight.zero_()
                    head.bias.fill_(bias)
            return instance

        def first_block(instance: PrequentialRunner) -> None:
            instance.forecast(Origin("day-0", 0, x, calendar))
            self.assertIsNone(instance.issued[0]["normalized_mae"])
            instance.arrive(label)
            for day in (1, 2):
                instance.forecast(
                    Origin(f"day-{day}", day, None, None, "skipped_all_missing_history")
                )
                instance.arrive(LabelArrival(f"day-{day}", False))
            trained = instance.candidates[2][0].forecast_head[0].bias.detach().clone()
            decision = instance.finish_block()
            self.assertEqual(decision.selected_level, 0.2)
            self.assertTrue(decision.switched)
            self.assertEqual(decision.valid_days, 1)
            self.assertEqual(decision.skipped_days, 2)
            self.assertTrue(torch.equal(instance.active_model.forecast_head[0].bias, trained))
            self.assertIsNotNone(instance.audit)
            self.assertEqual(instance.audit[0], 0.1)
            self.assertEqual(instance.update_steps, [1, 1, 1])

        def finish(instance: PrequentialRunner) -> None:
            instance.arrive(
                LabelArrival(
                    "day-3", True, torch.full((24,), 0.7), torch.ones(24, dtype=torch.bool)
                )
            )
            for day in (4, 5):
                instance.forecast(
                    Origin(f"day-{day}", day, None, None, "skipped_all_missing_history")
                )
                instance.arrive(LabelArrival(f"day-{day}", False))
            instance.finish_block()

        for rule in ("online_best_lambda", "without_confidence"):
            with self.subTest(rule=rule):
                continuous = prepared(rule)
                split = prepared(rule)
                first_block(continuous)
                first_block(split)
                for instance in (continuous, split):
                    instance.forecast(Origin("day-3", 3, x, calendar))
                    issued = instance.issued[-1]
                    self.assertEqual(issued["active_level"], 0.2)
                    self.assertIsNotNone(issued["audit_forecast"])
                    self.assertIsNone(issued["normalized_mae"])
                    self.assertFalse(torch.equal(issued["forecasts"][2], issued["audit_forecast"]))
                with TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
                    checkpoint = Path(directory) / "runner.pt"
                    save_runner(checkpoint, split)
                    split = load_runner(checkpoint, expected_binding=split.binding)
                self.assertEqual(split.selection_rule, rule)
                self.assertIsNotNone(split.pending)
                finish(continuous)
                finish(split)
                self.assertEqual(continuous.events, split.events)
                self.assertEqual(continuous.decisions, split.decisions)
                self.assertEqual(continuous.update_steps, split.update_steps)
                self.assertEqual(continuous.audit_steps, split.audit_steps)
                self.assertEqual(continuous.runtime_costs["audit"]["update_steps"], 1)
                self.assertIsNotNone(continuous.issued[-1]["audit_mae_kwh"])
                for left, right in zip(
                    continuous.issued[-1]["forecasts"], split.issued[-1]["forecasts"], strict=True
                ):
                    self.assertTrue(torch.equal(left, right))
                self.assertTrue(
                    torch.equal(
                        continuous.issued[-1]["audit_forecast"],
                        split.issued[-1]["audit_forecast"],
                    )
                )
                self.assertEqual(
                    continuous.issued[-1]["audit_mae_kwh"],
                    split.issued[-1]["audit_mae_kwh"],
                )
                for left, right in zip(
                    continuous.active_model.parameters(),
                    split.active_model.parameters(),
                    strict=True,
                ):
                    self.assertTrue(torch.equal(left, right))
                for left_state, right_state in zip(
                    continuous.active_optimizer.state_dict()["state"].values(),
                    split.active_optimizer.state_dict()["state"].values(),
                    strict=True,
                ):
                    for name in left_state:
                        self.assertTrue(torch.equal(left_state[name], right_state[name]))

    def test_fixed_policies_ignore_scores_but_record_coverage(self) -> None:
        rows = [score("a", (0.3, 0.9, 0.1)), score("b", None)]
        for rule, level in (("fixed_retention", 0.1), ("full_finetuning", 0.0)):
            with self.subTest(rule=rule):
                decision = decide_fixed_block(
                    config(initial=level), current_level=level, days=rows, rule=rule
                )
                self.assertEqual(decision.selected_level, level)
                self.assertEqual((decision.valid_days, decision.skipped_days), (1, 1))
                self.assertEqual(decision.reason, "fixed_policy")
                self.assertEqual(decision.selection_statistic, "fixed_level")
                self.assertEqual(decision.lower_bounds, (None, None, None))
                self.assertIsNone(decision.observed_mean_improvement)
        with self.assertRaisesRegex(ValueError, "requires zero"):
            decide_fixed_block(config(), current_level=0.1, days=rows, rule="full_finetuning")

    def test_fixed_policies_keep_trained_state_and_three_candidate_budget(self) -> None:
        x = torch.full((1, 24, 7), 0.2)
        calendar = torch.full((1, 24, 5), 0.1)
        for rule, level in (("fixed_retention", 0.1), ("full_finetuning", 0.0)):
            with self.subTest(rule=rule):
                instance = runner(rule, initial=level)
                for day in range(3):
                    instance.forecast(Origin(f"day-{day}", day, x, calendar))
                    instance.arrive(
                        LabelArrival(
                            f"day-{day}",
                            True,
                            torch.full((24,), 0.4),
                            torch.ones(24, dtype=torch.bool),
                        )
                    )
                selected_index = instance.controller.levels.index(level)
                selected = {
                    name: value.clone()
                    for name, value in instance.candidates[selected_index][0].state_dict().items()
                }
                self.assertEqual(instance.update_steps, [3, 3, 3])
                self.assertEqual(
                    [item["inference_calls"] for item in instance.runtime_costs["candidate"]],
                    [3, 3, 3],
                )
                decision = instance.finish_block()
                self.assertFalse(decision.switched)
                self.assertEqual(instance.current_level, level)
                self.assertIsNone(instance.audit)
                for name, value in selected.items():
                    self.assertTrue(torch.equal(value, instance.active_model.state_dict()[name]))
                restored = PrequentialRunner.from_state_dict(
                    instance.state_dict(), expected_binding=instance.binding, device="cpu"
                )
                self.assertEqual(restored.selection_rule, rule)
                self.assertEqual(restored.current_level, level)
                self.assertEqual(restored.update_steps, [3, 3, 3])
                self.assertEqual(restored.audit_steps, 0)
                state = instance.state_dict()
                state["current_level"] = 0.2 if level == 0.0 else 0.0
                with self.assertRaisesRegex(ValueError, "changed its selected level"):
                    PrequentialRunner.from_state_dict(
                        state, expected_binding=instance.binding, device="cpu"
                    )


if __name__ == "__main__":
    unittest.main()
