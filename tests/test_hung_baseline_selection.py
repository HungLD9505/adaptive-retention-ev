"""Independent mean-selector expectations and common-runner budget checks."""

import unittest

import torch

from experiments.hung_sprint2.baseline_selection import decide_mean_block
from experiments.hung_sprint2.controller import ControllerConfig, DailyScore
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.retention import frozen_source_reference
from experiments.hung_sprint2.runner import LabelArrival, Origin, PrequentialRunner


def config(*, delta: float = 0.0, minimum: int = 2) -> ControllerConfig:
    return ControllerConfig(
        (0.0, 0.1, 0.2),
        0.1,
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


def runner(rule: str) -> PrequentialRunner:
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
        controller=config(minimum=1),
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


if __name__ == "__main__":
    unittest.main()
